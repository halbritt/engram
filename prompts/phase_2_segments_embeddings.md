# Phase 2 Prompt — Segmentation + Embeddings

> Hand this to a coding agent (Claude Code, Codex, or equivalent) to
> build Phase 2 per [BUILD_PHASES.md](../BUILD_PHASES.md). Read
> BUILD_PHASES.md for the phase-plan context; this file is the
> operational handoff.

> Precondition: D026's pre-Phase-2 adversarial review has run and any
> accepted deltas have already landed. If not, stop and run/synthesize
> [ADVERSARIAL_PROMPTS.md](../docs/design/ADVERSARIAL_PROMPTS.md)
> before implementing this prompt.

## Read first, in order

1. [HUMAN_REQUIREMENTS.md](../HUMAN_REQUIREMENTS.md) — load-bearing
   principles. Especially: "Why local-first is load-bearing," "Why
   corpus access and network egress are kept separate," "Why raw
   data is sacred," "Why model portability is a first-class concern."
2. [V1_ARCHITECTURE_DRAFT.md](../docs/design/V1_ARCHITECTURE_DRAFT.md) —
   schema primitives, vector index policy (segments + accepted beliefs
   only; no raw turns), embedding dimension policy, build order steps
   3–4.
3. [DECISION_LOG.md](../DECISION_LOG.md) — accepted decisions; do not
   re-litigate. Binding for this phase: D005 (segments are the main
   embedding/extraction unit), D009 (vector index policy), D019
   (`privacy_tier` carry/inheritance on retrieval-visible derived
   units), D020 (no network egress), D021 (derivation versioning
   across the pipeline — `segmenter_version`, `embedding_model_version`),
   D026 (pre-Phase-2 adversarial review before implementation), D027
   (denormalized vector index and `is_active` flag), D028
   (privacy reclassification invalidates retrieval-visible derived rows),
   D029 (bounded windowed segmentation), D030 (segment provenance and
   active-ordering integrity), D031 (generation activation), D032
   (privacy inheritance / invalidation scope), D033 (dimension-flexible
   embedding storage), D034 (deterministic structured local-LLM calls).
4. [BUILD_PHASES.md](../BUILD_PHASES.md) — Phase 2 row, cross-cutting
   concerns (`consolidation_progress` checkpoints, raw immutability,
   privacy_tier carry, derivation versioning).
5. [src/engram/chatgpt_export.py](../src/engram/chatgpt_export.py) and
   [src/engram/claude_export.py](../src/engram/claude_export.py) —
   the conventions to mirror (idempotent batch ingest, atomic source
   upsert, dataclasses, `IngestConflict`, dedup via natural keys).

## Scope

Phase 2 only — topic segmentation of raw messages/notes and embedding
of the resulting segments. No claim extraction, no beliefs, no entity
canonicalization, no `context_for`. Each is a separate phase prompt.

## Build

1. **Investigate the actual local LLM stack first.** Per
   [SPEC.md](../SPEC.md#infrastructure) the stack is `nomic-embed-text`
   via Ollama at `http://127.0.0.1:11434` and `qwen3.6-35b-a3b` via
   ik-llama at `http://127.0.0.1:8081/v1` (OpenAI-compatible). Probe
   both before assuming — confirm models, dimensions, and endpoint
   shapes. Do not assume from external documentation that may be
   stale; read the running services.

   Preflight probes before full implementation:
   - Probe ik-llama with `GET /v1/models`, `GET /props`, and a minimal
     `POST /v1/chat/completions` request. Record the exact model id,
     context window, response shape, and the request parameters required
     to return parseable JSON in `choices[0].message.content`.
   - Find the largest conversation by total message text length and
     run the draft segmenter prompt against it. Record whether it fits,
     truncates, errors, or needs windowing (D029).
   - Probe the embedder through Ollama's current batch embedding endpoint
     and record model identity plus returned vector dimension. Probe
     pgvector version and confirm the index strategy for the active
     model/dimension before writing DDL (D033).
   - Simulate two concurrent cache inserts for identical text and
     verify the intended conflict path (see Embedder below).

2. **Schema migration** (`migrations/004_segments_embeddings.sql`).
   Derived/control schema additions plus one raw-schema backfill:
   add `notes.privacy_tier INT NOT NULL DEFAULT 1` if it does not
   already exist. Do not mutate raw evidence rows.

   `consolidation_progress` changes (D027):
   - Add `error_count INT NOT NULL DEFAULT 0`
   - Add `last_error TEXT NULL`
   - `position JSONB` must support intra-parent progress, e.g.
     `{conversation_id, window_index}` for windowed segmentation.

   `segment_generations` (D031):
   - `id UUID PK`
   - `parent_kind TEXT NOT NULL CHECK (parent_kind IN ('conversation',
     'note', 'capture'))`
   - `parent_id UUID NOT NULL`
   - `segmenter_prompt_version TEXT NOT NULL`
   - `segmenter_model_version TEXT NOT NULL`
   - `status TEXT NOT NULL CHECK (status IN ('segmenting', 'segmented',
     'embedding', 'active', 'superseded', 'failed'))`
   - `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
   - `activated_at TIMESTAMPTZ NULL`
   - `superseded_at TIMESTAMPTZ NULL`
   - `raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb`
   - Partial unique index for active generation per parent:
     `(parent_kind, parent_id) WHERE status = 'active'`

   `segments`:
   - `id UUID PK`
   - `generation_id UUID NOT NULL REFERENCES segment_generations(id)`
   - `source_id UUID NOT NULL REFERENCES sources(id)`
   - `source_kind source_kind NOT NULL` — segments inherit the kind
     of their source row.
   - `conversation_id UUID NULL REFERENCES conversations(id)` — set
     for segments derived from messages; NULL for note/capture
     segments.
   - `note_id UUID NULL REFERENCES notes(id)` and
     `capture_id UUID NULL REFERENCES captures(id)` — for the future
     non-conversation paths; NULL for now. (The columns land now so
     downstream phases don't need a migration; nothing in this phase
     populates them.)
   - `message_ids UUID[] NOT NULL` — the raw messages this segment
     spans (in order). Empty array allowed only for note/capture
     segments.
   - `sequence_index INT NOT NULL` — order of this segment within
     its parent conversation/note.
   - `content_text TEXT NOT NULL` — the segment text fed to the
     embedder, with role/source markers as the segmenter chose.
   - `summary_text TEXT NULL` — optional segmenter-emitted topic
     label or short summary, if it produces one.
   - `window_strategy TEXT NOT NULL DEFAULT 'whole' CHECK
     (window_strategy IN ('whole', 'windowed'))` — D029.
   - `window_index INT NULL` — set for windowed segmentation.
   - `segmenter_prompt_version TEXT NOT NULL`
   - `segmenter_model_version TEXT NOT NULL`
   - `is_active BOOLEAN NOT NULL DEFAULT false` — retrieval-visible
     only after the generation activation cutover (D031).
   - `invalidated_at TIMESTAMPTZ NULL`
   - `invalidation_reason TEXT NULL`
   - `privacy_tier INT NOT NULL DEFAULT 1` — D032:
     `max(parent privacy_tier, covered raw-row privacy_tiers)`. For
     conversation segments, parent = `conversations.privacy_tier` and
     covered rows = `messages.privacy_tier`.
   - `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
   - `raw_payload JSONB NOT NULL` — the segmenter's raw output for
     this segment, including any rationales or scores it emits.
   - Subject to the immutability trigger in the same shape as raw
     tables: UPDATE allowed only for generation activation /
     deactivation (`is_active`) and invalidation metadata
     (`invalidated_at`, `invalidation_reason`); DELETE blocked.
   - Indexes: unique active ordering per parent:
     `(conversation_id, sequence_index)` partial WHERE
     `is_active = true AND conversation_id IS NOT NULL`, plus
     analogous note/capture indexes. GIN on `message_ids`.
   - INSERT trigger validates conversation `message_ids` (D030):
     non-empty for conversation segments, all UUIDs exist in
     `messages`, all belong to `segments.conversation_id`, and array
     order matches `messages.sequence_index`.

   `embedding_cache`:
   - `id UUID PK`
   - `input_sha256 TEXT NOT NULL` — SHA256 over the exact embedded
     UTF-8 byte string sent to the embedder after canonicalization
     (not the segment id — the cache is content-keyed so beliefs in
     Phase 3 can share it).
   - `embedding_model_version TEXT NOT NULL`
   - `embedding_dimension INT NOT NULL`
   - `embedding vector NOT NULL` — dimension-flexible storage per
     D033; row dimension must equal `embedding_dimension`.
   - Check constraint: `vector_dims(embedding) = embedding_dimension`.
   - `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
   - `UNIQUE (input_sha256, embedding_model_version)` — same input
     can have multiple model rows; same input + model is unique.
   - Fully immutable (no UPDATE, no DELETE — same trigger as raw
     tables).

   `segment_embeddings`:
   - `segment_id UUID NOT NULL REFERENCES segments(id)`
   - `generation_id UUID NOT NULL REFERENCES segment_generations(id)`
   - `embedding_cache_id UUID NOT NULL REFERENCES embedding_cache(id)`
   - `embedding vector NOT NULL` — copied from cache (D027 / D033).
   - `embedding_model_version TEXT NOT NULL`
   - `embedding_dimension INT NOT NULL`
   - Check constraint: `vector_dims(embedding) = embedding_dimension`.
   - `is_active BOOLEAN NOT NULL DEFAULT false` — activated only in
     the generation cutover transaction and deactivated with the
     parent segment.
   - `privacy_tier INT NOT NULL` — copied from the parent segment so
     retrieval can filter before returning candidates.
   - `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
   - `PRIMARY KEY (segment_id, embedding_model_version)` — multiple
     model versions can coexist on one segment (D021).
   - HNSW indexes are per active `(embedding_model_version,
     embedding_dimension)` using a pgvector-supported
     dimension-specific partial/expression index, e.g. casting to the
     active dimension when required. Retrieval queries must also
     filter `is_active = true` and `privacy_tier <= :allowed_tier`.
     Add tier-specific partial indexes only if EXPLAIN / smoke
     retrieval shows privacy filtering collapses recall. Verify the
     pgvector version supports the chosen HNSW strategy; if not,
     document the ivfflat fallback parameters. (D009, D027, D033.)

3. **Segmenter** (`src/engram/segmenter.py`).
   - `segment_conversation(conn, conversation_id) -> SegmentationResult`.
     Pulls the conversation + ordered messages, builds the prompt,
     calls ik-llama, parses the structured response into 1..N
     segments. Short conversations may return a single segment
     (D005).
   - Long-conversation handling (D029): probe the effective local
     model context window, reserve margin for instructions/output, and
     set a per-parent budget. If a parent exceeds budget, segment
     overlapping message windows, record `window_strategy='windowed'`
     and `window_index`, and merge adjacent boundary segments only
     when the overlap shows they cover the same topic. Window-boundary
     uncertainty belongs in `raw_payload`.
   - Message canonicalization: include NULL-content messages in
     `message_ids` when they are within the segment span, but exclude
     non-text placeholders from the embedded text unless they carry
     semantic content. Strip high-frequency tool/image markers from
     `content_text` before embedding; changes to this policy require a
     new `segmenter_prompt_version`. Do not create an embeddable
     segment with empty `content_text`; if a parent/window has no
     embeddable text, record the skip in generation/progress metadata.
   - Qwen / ik-llama request contract (D034): use the OpenAI-compatible
     `POST http://127.0.0.1:8081/v1/chat/completions` endpoint with the
     exact probed model id. The current local probe returned
     `/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf`; do not
     hardcode that path without checking the running service. Set
     `stream=false`, `temperature=0`, `top_p=1`, and
     `chat_template_kwargs={"enable_thinking": false}`. Set bounded
     `max_tokens` from configuration; the starting default is 4096 per
     parent/window unless the largest-conversation probe justifies a
     different cap. Parse only `choices[0].message.content`; treat
     `reasoning_content` as
     diagnostic output, never as the segment payload. Record the exact
     model id, probed context size, prompt version, and request-profile
     version in `segmenter_model_version` / `segmenter_prompt_version`
     metadata so re-derivation is reproducible.
   - Structured output contract (D034): require
     `response_format={"type":"json_schema", ...}` with a schema named
     `SegmentationResult`. The response content must be a single JSON
     object with this shape:

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

     The schema must require `segments`, `message_ids`, `content_text`,
     and `raw`; allow `summary` to be `null`; set
     `additionalProperties=false` at the response and segment levels;
     and allow `raw` to carry model-specific diagnostic fields. Reject
     empty `segments` unless the whole parent/window is explicitly
     recorded as skipped in generation/progress metadata. Do not accept
     Markdown fences or explanatory text as the normal path. Invalid JSON
     or schema violations fail the parent/window and are recorded in
     `consolidation_progress.last_error`.
   - `segment_pending(conn, batch_size, model_version) ->
     BatchResult`. Drives segmentation across all conversations
     with no active or pending generation under the current
     (`segmenter_prompt_version`, `segmenter_model_version`), plus
     parents explicitly queued by invalidation.
     Resumable per `consolidation_progress` (`stage='segmenter'`,
     `scope` = `conversation:<uuid>`, `note:<uuid>`,
     `capture:<uuid>`, or batch identifier; `position` records the
     last completed parent and, for windowed parents, window index).
   - Re-segmentation under a new prompt/model version inserts new
     rows under a new `segment_generations` row. New rows remain
     `is_active=false` until the required embedding rows exist and
     the generation is activated (D031). Re-running with the **same**
     versions is a no-op.
   - Reclassification captures (D023 / D028) that change effective
     tier for any raw row covered by an active segment must deactivate
     that segment and its `segment_embeddings` rows, set
     `invalidated_at` / `invalidation_reason`, then queue only the
     affected parent conversation, note, or capture for
     re-segmentation and re-embedding (D032).

4. **Embedder** (`src/engram/embedder.py`).
   - `embed_text(text, model_version) -> EmbeddingResult` — hashes
     exactly the UTF-8 byte string sent to the embedder after
     canonicalization. Cache hit returns the existing row id; cache
     miss calls Ollama, then inserts with
     `INSERT ... ON CONFLICT (input_sha256, embedding_model_version)
     DO NOTHING RETURNING id`; if no row is returned, SELECT the
     existing row by the unique key. Do not use no-op UPDATE, because
     `embedding_cache` is immutable.
   - `embed_pending_segments(conn, batch_size, model_version) ->
     BatchResult`. Drives embedding across segments in pending
     generations (`segment_generations.status IN ('segmented',
     'embedding')`) lacking a `segment_embeddings` row for the current
     model version.
     Explicitly copies the vector payload and dimension from
     `embedding_cache` into `segment_embeddings`, and copies
     `privacy_tier` from the parent segment (D027 / D033). Resumable
     per `consolidation_progress` (`stage='embedder'`).
   - Generation activation (D031): after all required
     `segment_embeddings` rows exist for a generation, activate the new
     generation in one transaction: mark its generation, segments, and
     segment_embeddings active, then mark the prior active generation
     and its retrieval-visible rows inactive. Before that transaction,
     the prior generation remains retrieval-visible.
   - Multiple `embedding_model_version` rows can coexist on one
     segment. Re-embedding with a new model version is additive,
     not destructive.

5. **CLI subcommands** in `cli.py`:
   - `engram segment [--source-id ID] [--batch-size N] [--limit N]`
   - `engram embed [--model-version V] [--batch-size N] [--limit N]`
   - `engram pipeline` — convenience: run `segment` then `embed` with
     defaults. `pipeline` is the normal path and must leave no
     completed segment generation without required embeddings. A
     standalone `segment` run that creates inactive generations should
     warn that `engram embed` is required before retrieval visibility.

6. **Makefile targets** parallel to existing ingest targets:
   `segment`, `embed`, `pipeline`, plus `-docker` variants.

7. **Tests** (`tests/test_phase2_segments.py`,
   `tests/test_phase2_embeddings.py`):
   - Segmenter end-to-end against a stubbed ik-llama response
     (mock the HTTP client at the boundary; do not call the real
     model in tests).
   - Segmenter client request-shape test: the ik-llama boundary sends
     `stream=false`, `temperature=0`, bounded `max_tokens`,
     `chat_template_kwargs.enable_thinking=false`, and
     `response_format.type='json_schema'`; it parses
     `choices[0].message.content` and rejects payloads that are only in
     `reasoning_content`, Markdown-fenced, or schema-invalid (D034).
   - Idempotent re-segmentation under the same versions: count
     before == count after.
   - Version bump produces new active rows, supersedes prior rows
     via `is_active=false`, and prior rows are no longer
     `is_active=true`.
   - Generation cutover: after `segment` but before `embed`, the prior
     generation remains retrieval-visible; after `embed` completes,
     the new generation becomes active and the old generation becomes
     inactive.
   - Long conversation over the configured budget uses windowed
     segmentation, records `window_strategy='windowed'`, and resumes
     from a window checkpoint after interruption.
   - Active sequence uniqueness rejects two active segments with the
     same `(parent, sequence_index)`.
   - `message_ids` validation rejects unknown message ids,
     cross-conversation message ids, empty arrays for conversation
     segments, and arrays ordered differently from message sequence.
   - NULL/tool/image-only message windows do not produce empty
     embeddable segments, but their skip is recorded.
   - Immutability trigger blocks UPDATE on segment columns other
     than allowed activation/invalidation fields; DELETE blocked
     outright.
   - Embedder cache hit on identical input + model version (one
     model call, one cache row, two `segment_embeddings` rows).
   - Concurrent cache miss for identical input + model version creates
     one cache row and all expected `segment_embeddings` rows without
     UNIQUE violations.
   - Two distinct `embedding_model_version` rows coexist on the
     same segment.
   - Resumability: simulate a mid-batch interrupt by raising after
     N segments; re-running picks up at the recorded
     `consolidation_progress` position with no duplicates.
   - `privacy_tier` on segments inherits the max tier across the
     parent row and constituent raw rows.
   - Reclassification capture against any constituent raw row
     deactivates affected segments and `segment_embeddings` rows and
     queues only the affected parent conversation/note/capture for
     reprocessing (D028 / D032).

8. **Docs** (`docs/segmentation.md`, sibling to
   `docs/ingestion.md`): how to run, what the segmenter prompt and
   local request profile look like (in-repo paths), what counts as a
   segment, how versioning works, how supersession works, what's
   deferred (re-embedding existing rows is operator-driven; no
   automatic re-embed on segment supersession in this phase).

## Constraints (load-bearing — do not relax)

- Local only. No outbound network calls. Both LLM endpoints on
  127.0.0.1 (D020).
- Postgres binds to 127.0.0.1 (already enforced in Phase 1).
- Raw tables remain immutable. Segments are *also* immutable except
  for generation activation/deactivation and invalidation metadata.
- Re-derivation is non-destructive: new rows + supersession, never
  in-place UPDATE.
- `privacy_tier` carries onto segments and segment embeddings (D019).
  Reclassification captures invalidate retrieval-visible derived rows
  before they can serve stale lower-tier vectors (D028 / D032).
- Every derived row records its `*_prompt_version` /
  `*_model_version` (D021).
- Local LLM calls use deterministic structured request contracts, not
  endpoint defaults (D034).
- Retrieval-visible segment generations activate only after required
  embeddings exist (D031).
- Embedding storage is dimension-flexible; ANN indexes are per active
  model/dimension (D033).
- `consolidation_progress` checkpoints make both stages resumable.
  Phase 1 created the empty table; Phase 2 is the first writer.

## Acceptance criteria

- `make migrate` brings up the new tables from a Phase-1.5 schema.
- `make segment` segments all conversations end-to-end. Re-running
  with the same versions is a no-op (zero new rows).
- The segmenter ik-llama client uses the D034 request profile and
  fails clearly on non-JSON, fenced JSON, `reasoning_content`-only, or
  schema-invalid responses.
- `make embed` embeds all pending-generation segments end-to-end and
  activates completed generations. Re-running with the same model
  version is a no-op.
- Bumping `segmenter_prompt_version` produces new active segments
  only after the new generation's required embeddings exist; the prior
  generation remains retrieval-visible until cutover.
- Over-budget parents use windowed segmentation and can resume at a
  window checkpoint.
- Conversation segments enforce `message_ids` integrity and active
  sequence uniqueness at the database boundary.
- Embedding cache writes are race-safe under concurrent workers.
- The vector schema accepts the probed embedding dimension and records
  per-row `embedding_dimension`; the active ANN index is scoped to
  that model/dimension.
- `consolidation_progress` has rows for `stage='segmenter'` and
  `stage='embedder'` after a run; `status='completed'` on a clean
  finish.
- All Phase 1 tests still pass; new tests cover the criteria
  above.
- HNSW (or ivfflat fallback) index exists and a similarity query
  returns sensible neighbors on the smoke subset.

## Non-goals (do not build in this phase)

- Claim extraction, beliefs, contradictions, `belief_audit` (Phase
  3).
- Entity canonicalization, `current_beliefs` view, review queue
  (Phase 4).
- `context_for`, ranking, MCP, `context_feedback` (Phase 5).
- Embedding raw turns or full conversations (D009 — segments only).
- Embedding beliefs (Phase 3 — beliefs don't exist yet).
- LLM cross-encoder reranker (F003 — deferred).
- Auto-re-embed inside `segment`. A standalone segment run may create
  inactive generations, but retrieval visibility requires the
  subsequent `embed` / `pipeline` activation step.
- Obsidian / capture segmentation. Same pipeline shape, separate
  phase or follow-up prompt; the schema columns are present but
  unused here.

## When in doubt

Prefer the smallest change that satisfies the principles and the
acceptance criteria. Reach for DECISION_LOG and V1_ARCHITECTURE_DRAFT
before inventing. If a question isn't answered there, stop and ask
rather than guessing — Phase 2 is where model-version variance
enters the pipeline, and the wrong default propagates everywhere
downstream.
