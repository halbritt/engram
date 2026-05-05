# Segmentation And Embeddings

Phase 2 turns immutable raw conversations into topic segments, embeds those
segments, and activates a retrieval-visible generation only after its required
embedding rows exist.

## Run

```bash
make migrate
make segment
make embed
```

`make pipeline` runs `segment` then `embed` with defaults and is the normal
operator path. A standalone `segment` run creates inactive segment generations;
run `engram embed` before expecting retrieval visibility.

Useful CLI forms:

```bash
engram segment --source-id UUID --batch-size 10 --limit 100
engram embed --model-version nomic-embed-text:latest --batch-size 100
engram pipeline --segment-batch-size 10 --embed-batch-size 100
```

For long unattended runs, pin the probed ik-llama model id so every batch does
not need to call `/v1/models`:

```bash
export ENGRAM_SEGMENTER_MODEL=~/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf
make pipeline
```

The Makefile also accepts `SEGMENTER_MODEL=...` for `segment` and `pipeline`.

## Local Preflight

Historical probe observed on 2026-04-30. Treat these values as the last known
baseline, not as a substitute for probing the running local services before a
long run:

- ik-llama `GET /v1/models` exposed model id
  `~/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` with
  `max_model_len=262144`.
- ik-llama `GET /props` reported `n_ctx=262144`. Endpoint defaults include
  streaming and non-zero temperature, so the client overrides them.
- Minimal `POST /v1/chat/completions` returned parseable JSON in
  `choices[0].message.content` with `stream=false`, `temperature=0`, `top_p=1`,
  `chat_template_kwargs={"enable_thinking": false}`, bounded `max_tokens`, and
  `response_format.type="json_schema"`.
- Largest current conversation:
  `0d91a08e-3aa6-4390-a21b-5787ef5c7ec2`, title
  `Performance review writing guide`, 181 messages, 1,018,528 message-text
  characters. A full draft segmentation request was 1,077,862 bytes and timed
  out after 120 seconds, so the implementation uses bounded windowing.
- Ollama `/api/embed` with `nomic-embed-text:latest` returned batch
  embeddings under the `embeddings` key. Probed dimension: 768.
- pgvector version: 0.6.0. HNSW opclasses are available. The migration creates
  a partial expression HNSW index for active `nomic-embed-text:latest`
  768-dimensional segment embeddings, plus a model/dimension/tier filter index.
- Concurrent cache insert probe: two workers embedding identical text under
  `preflight-race-probe-v1` produced one `embedding_cache` row; the losing
  worker followed the SELECT fallback path after `ON CONFLICT DO NOTHING`.

Before any long segmentation or soak run, run P-HEALTH:

1. Pin the current ik-llama model id:

   ```bash
   export ENGRAM_SEGMENTER_MODEL=~/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf
   ```

2. Send a tiny D034-profile `POST /v1/chat/completions` that requires a
   schema-valid JSON object in `choices[0].message.content`. `GET /v1/models`
   and `GET /props` are not enough; they can return 200 while generation is
   wedged.
3. Run a 10-conversation local preflight with OpenClaw quiesced if it shares the
   same GPU/endpoint, and with any blocking `/health` watchdog disabled or
   replaced:

   ```bash
   make pipeline-isolated SEGMENTER_MODEL="$ENGRAM_SEGMENTER_MODEL"
   ```

   For a bounded preflight, call the CLI directly with `--limit 10`.
4. Run the same tiny completion smoke again. If either smoke fails or times out,
   stop the soak and inspect `journalctl --user -u ik-llama-server.service`
   plus the run log before continuing.

## Segmenter Contract

Implementation path: `src/engram/segmenter.py`.

The segmenter calls only the local OpenAI-compatible ik-llama endpoint:

```text
POST http://127.0.0.1:8081/v1/chat/completions
```

Request profile:

```json
{
  "stream": false,
  "temperature": 0,
  "top_p": 1,
  "max_tokens": 16384,
  "chat_template_kwargs": {"enable_thinking": false},
  "response_format": {"type": "json_schema"}
}
```

Runtime version defaults:

- `segmenter_prompt_version`: `segmenter.v2.d034.enum-ids.tool-placeholders`
- `request_profile_version`: `ik-llama-json-schema.d034.v2`

Only `choices[0].message.content` is parsed. `reasoning_content` is diagnostic
only. Empty content, Markdown-fenced JSON, invalid JSON, and schema-invalid
payloads trigger one adaptive retry by default (`ENGRAM_SEGMENTER_RETRIES`, or
`--retries` / `--segment-retries` in the CLI). Truncation-like parse failures
retry the same prompt with a larger output budget, bounded by
`ENGRAM_SEGMENTER_RETRY_MAX_TOKENS` (default `32768`). If the retry budget is
exhausted, the parent/window fails, `segment_generations.status` becomes
`failed`, and `consolidation_progress.last_error` records the failure.
Non-service failed generations are poison pills for the same prompt/model
version: later batches continue past them unless the parent is explicitly
queued or the version changes.

The HTTP request timeout is intentionally conservative and configurable with
`ENGRAM_SEGMENTER_TIMEOUT_SECONDS` because large local windows can legitimately
take minutes. The default is 600 seconds.

Structured requests also fail closed before they can reach the model's context
boundary. The segmenter probes the ik-llama context window and estimates
`prompt_tokens + max_tokens + ENGRAM_SEGMENTER_CONTEXT_GUARD_MARGIN_TOKENS`
before each D034 `json_schema` call. If the request would reach context shift,
the parent/window fails locally instead of letting ik-llama shift context while
grammar-constrained. The default margin is `1024` tokens; the heuristic token
estimate uses `ENGRAM_SEGMENTER_CONTEXT_GUARD_CHARS_PER_TOKEN`, default `2.5`.
If the probed context is smaller than the configured window budget assumes, the
conversation is split into smaller windows up front and the generation metadata
records both `window_char_budget` and `effective_window_char_budget`.

The required response object is:

```json
{
  "segments": [
    {
      "message_ids": ["uuid"],
      "summary": "string or null",
      "content_text": "non-empty string",
      "raw": {}
    }
  ]
}
```

For each conversation/window, the JSON schema constrains
`message_ids.items.enum` to the exact message UUIDs shown in that window. This
prevents schema-valid but evidence-invalid outputs such as integer IDs,
malformed UUIDs, or UUIDs from another conversation. The database trigger still
validates the final expanded span at insert time.

`content_text` is the text fed to the embedder. Marker-only image/tool lines are
stripped before insertion and hashing. Tool-role message bodies are treated as
non-embeddable artifacts in Phase 2: the raw table still keeps the exact tool or
file-extraction payload, but the segmenter prompt sees only a bounded
placeholder such as `[tool artifact omitted: chars=106276,
markers=tool,filecite,urls]`. Null-content and omitted-tool messages inside a
covered span remain in `message_ids` for provenance, but the segmenter is
instructed not to copy placeholders into `content_text`.

## Windowing

The default per-window budget is `ENGRAM_SEGMENTER_WINDOW_CHAR_BUDGET`, default
`60000` characters. Over-budget parents are split into deterministic message
windows. The default `ENGRAM_SEGMENTER_WINDOW_OVERLAP` is `0` until boundary
merge/dedupe semantics are implemented; operators can raise it explicitly when
they want overlap and accept possible duplicate boundary coverage. Windowed
segments record:

- `window_strategy='windowed'`
- `window_index`
- window-boundary/truncation details in `raw_payload`

The current migration, code, and Phase 2 handoff use `whole` / `windowed`.
P-FRAG's possible schema extension to `topic`, `windowed_overlap`, and
`message_group` is deferred by D039; update this doc only if that later
migration lands so operator-facing values continue to match the deployed
schema.

Progress is stored in `consolidation_progress` with scopes such as
`conversation:<uuid>` and positions like:

```json
{"conversation_id": "...", "window_index": 3}
```

The CLI also prints per-parent segment progress and throttled embedding
progress, including elapsed seconds. This is the normal way to monitor long
full-corpus runs without querying the database.

Service-unavailable failures are parent-scoped and retryable. They mark the
conversation progress row `pending` and increment `error_count`; once
`ENGRAM_SEGMENTER_MAX_ERROR_COUNT` is reached (default `3`), the pending retry
queue stops selecting that parent until it is manually requeued or the relevant
progress row is reset. This prevents one unstable local-model request from
rolling back a whole batch.

Failed `segment_generations.raw_payload` rows include `failure_kind`,
`last_error`, `attempts`, `attempt_max_tokens`, `decode_counts` when exposed by
the local endpoint, and `attempt_errors`. These fields are intentionally
operator-facing: they let a soak distinguish insufficient output budget from
runaway schema-constrained generation or a wedged inference process without
guessing from elapsed time alone.

## Versioning And Supersession

Segments are grouped by `segment_generations`.

Re-running the same `segmenter_prompt_version` and `segmenter_model_version` is
a no-op once a generation is `segmented`, `embedding`, or `active`.

Changing the prompt/model inserts a new generation and inactive segment rows.
The old active generation remains retrieval-visible until `engram embed`
creates all required `segment_embeddings` for the new generation. Activation
then supersedes the prior generation and flips old segment/vector rows
inactive in one transaction.

## Embedding Cache

Implementation path: `src/engram/embedder.py`.

The embedder calls only local Ollama:

```text
POST http://127.0.0.1:11434/api/embed
```

The cache key is SHA256 over the exact UTF-8 bytes of the canonicalized
embedded text plus `embedding_model_version`. Cache writes use:

```sql
INSERT ... ON CONFLICT (input_sha256, embedding_model_version)
DO NOTHING
RETURNING id
```

If another worker wins the race, the loser selects the existing row by the
unique key. No no-op UPDATE is used because `embedding_cache` is immutable.

## Privacy

Segment `privacy_tier` is:

```text
max(parent conversation/note/capture tier, covered raw-row tiers)
```

The same tier is copied onto `segment_embeddings` so retrieval can filter by
`is_active=true` and `privacy_tier <= allowed_tier` before returning candidates.
Reclassification captures invalidate active affected segment/vector rows and
queue only the affected parent for reprocessing.

## Deferred

This phase does not extract claims, create beliefs, canonicalize entities,
serve `context_for`, segment Obsidian notes, or segment capture rows. Re-embed
of existing active generations under a new embedding model is operator-driven
via `engram embed --model-version ...`; it is not automatically run by
`engram segment`.
