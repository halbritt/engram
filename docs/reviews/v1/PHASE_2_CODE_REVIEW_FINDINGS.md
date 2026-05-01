# Phase 2 Code Review Findings

Date: 2026-05-01

This document consolidates findings from reviewing the Phase 2 implementation (`src/engram/segmenter.py`) and the pipeline test logs. The implementation currently fails to meet several criteria established during the pre-Phase-2 adversarial review (D027).

## Code Review (`src/engram/segmenter.py`)

### 1. Missing Schema for `segment_generations`
The `segmenter.py` script heavily utilizes a `segment_generations` table (e.g., in `create_generation`, `find_existing_generation`, `mark_generation_failed`) to track the batch status of segmentation runs. It also inserts `generation_id` into the `segments` table. However, neither the `segment_generations` table nor the `generation_id` column on `segments` are defined in the `prompts/phase_2_segments_embeddings.md` schema. This discrepancy will cause immediate `UndefinedTable` and `UndefinedColumn` errors upon execution against a strict schema.

### 2. Missing D027 Poison-Pill Avoidance Filter
While `segment_conversation` correctly calls `upsert_progress(..., increment_error=True)` when encountering a `SegmenterRequestTimeout` or general `Exception`, the `fetch_pending_conversations` query does **not** filter out rows where `p.error_count >= 3`. As a result, the `segment_pending` batcher will enter an infinite loop of retrying and failing on poison-pill conversations, entirely defeating the D027 fix.

### 3. D027 Reclassification Invalidation is Dead Code
The script includes `apply_reclassification_invalidations(...)` which correctly maps `reclassification` captures to their parent conversations/notes and invalidates the related segments. However, this function is **never called** in the main execution path. It needs to be invoked at the start of `segment_pending` (or explicitly scheduled) so that affected sources are re-queued before the pending fetch runs.

### 4. Non-Existent Columns in Privacy Invalidation
In the `invalidate_parent_segments` function, the query attempts to record metadata about the privacy invalidation:
```sql
UPDATE segments
SET is_active = false,
    invalidated_at = now(),
    invalidation_reason = %s
WHERE id = ANY(%s::uuid[])
```
The columns `invalidated_at` and `invalidation_reason` are not defined in the `segments` schema and will crash the privacy tier recalculation. The schema either needs these columns added, or the update should be simplified to `SET is_active = false`.

### 5. Incomplete `is_active` Deprecation Logic
When re-segmenting a conversation (e.g., forced via a new prompt or model version), the script successfully inserts the newly generated segments. However, it entirely fails to deprecate the older generation. There is no query equivalent to `UPDATE segments SET is_active = false WHERE conversation_id = X AND segmenter_prompt_version != Y`. Without this deprecation, multiple overlapping active segments will exist for the same conversation, leading to catastrophic duplicate retrieval.

---

## Log Review (`logs/phase2_segment_embed_loop_bounded_20260501T045146Z.log`)

### 1. Chronic Segmenter Timeouts
The logs show severe generation latency on specific conversations, with operations consistently failing after exactly 180.0 seconds:
```text
segment 1/1 failed conversation=18f0c88e-909d-46a6-9857-137869799dea elapsed=180.0s
segment 1/1 failed conversation=1914312f-f548-41dd-9543-b5cef2e92a23 elapsed=180.0s
segment 1/1 failed conversation=19253250-362e-4863-838c-1264703aa789 elapsed=180.0s
```
This indicates the local `ik-llama` model is hanging, spinning without returning a response, or hitting context-window limits on these large items until the Python client cuts it off via `SegmenterRequestTimeout`.

### 2. Service Unavailability / Connection Resets
The script is repeatedly crashing entirely when trying to connect to the `ik-llama` endpoint (port 8081):
```text
ConnectionResetError: [Errno 104] Connection reset by peer
engram.segmenter.SegmenterServiceUnavailable: local segmenter unavailable: [Errno 104] Connection reset by peer
```
There are also socket-level timeouts occurring during the `probe_segmenter` health check. This indicates the local LLM server is becoming completely unresponsive or crashing/restarting under the load of the timed-out generation requests.

### 3. The Poison-Pill Loop is Active
Because the D027 poison-pill skip logic (`error_count >= 3`) is missing from the query implementation, the batch script is continually hitting these failing conversations. It waits 3 minutes for them to time out, fails, and then restarts the loop, preventing the ingestion pipeline from making progress on the rest of the corpus.

### 4. Successful Generations
The pipeline is fundamentally sound when the LLM server remains responsive and the payload is tractable:
```text
segment 1/1 done conversation=192795f8-6ba9-46d1-8621-f8b4e06dc218 segments=1 windows=1 skipped=0 elapsed=5.5s
```
When segmentation succeeds, the embedding phase picks it up and successfully caches the vector via Ollama:
```text
embed 1/1 segment=f270254e-3247-4705-8e1b-5fcdcbf82ad8
embed 1/1 done cache_hit=False elapsed=0.1s
```

## Summary Action Items
To stabilize the Phase 2 ingestion pipeline, the following fixes are critical:
1. Update `fetch_pending_conversations` in `segmenter.py` to filter out `error_count >= 3`.
2. Reconcile the undocumented `segment_generations` table dependency.
3. Hook up the `apply_reclassification_invalidations` call into the batcher loop.
4. Implement the `is_active = false` deprecation logic for re-segmentation runs.

---

## Verification (Opus 4.7, 2026-04-30)

I cross-checked each finding against `migrations/004_segments_embeddings.sql`, `src/engram/segmenter.py`, `src/engram/embedder.py`, and `src/engram/cli.py`.

### Finding 1 — Missing Schema for `segment_generations`: **NOT REPRODUCED**
Migration `004_segments_embeddings.sql:11-31` creates `segment_generations`, and `segments.generation_id UUID NOT NULL REFERENCES segment_generations(id)` is at line 47. The prompt file describes both (`prompts/phase_2_segments_embeddings.md:86, 104, 173, 270, 292`). The runtime will not raise `UndefinedTable` / `UndefinedColumn` against the migrated schema. Closing this finding as a documentation observation only.

### Finding 2 — Poison-Pill Filter: **PARTIALLY REPRODUCED — narrower scope than stated**
`fetch_pending_conversations` (`segmenter.py:614-654`) does not gate on `error_count`, but for `segmenter_timeout` and `segmenter_error` the failed `segment_generations` row is created (`mark_generation_failed`, `segmenter.py:399, 411`) with `failure_kind != 'service_unavailable'`. The `NOT EXISTS` clause then excludes that conversation on subsequent batches — those conversations are *not* in an infinite loop.

The actual loop is on `service_unavailable`: the carve-out
```sql
sg.raw_payload->>'failure_kind' IS DISTINCT FROM 'service_unavailable'
```
deliberately re-queues service-unavailable failures so transient ik-llama crashes are retried. Without an `error_count >= 3` ceiling, a chronically flapping endpoint does loop the same conversation. The same is true for the `p.status='pending'` reclassification re-queue path.

The real-world breakdown (DB query, scope='conversation:%'):
- 15 invalid JSON (status=`failed`, kind=`segmenter_error`)
- 10 marked failed after interrupted run
- 6 timeout (status=`failed`, kind=`segmenter_timeout`)

None of those 31 rows are eligible for re-fetch. The "infinite loop" the log appears to show is the supervisor restarting and finding *new* candidates — not the same candidate cycling. The 180s stalls are spread across distinct conversation UUIDs.

### Finding 3 — Reclassification Invalidation is Dead Code: **NOT REPRODUCED**
`cli.py:111` and `cli.py:148` call `apply_reclassification_invalidations(conn)` at the start of the `segment` and `pipeline` commands respectively, before `run_segment_batches`. The function is wired.

### Finding 4 — Non-Existent Columns: **NOT REPRODUCED**
Migration `004_segments_embeddings.sql:63-64` defines both:
```sql
invalidated_at TIMESTAMPTZ NULL,
invalidation_reason TEXT NULL,
```
The immutability trigger (`004_segments_embeddings.sql:134-172`) deliberately omits these from the "must not change" list, allowing `is_active`, `invalidated_at`, `invalidation_reason` to be updated. The privacy reclassification path (`segmenter.py:1232-1241`) is correct against the deployed schema.

### Finding 5 — Incomplete `is_active` Deprecation: **NOT REPRODUCED — deprecation is in `embedder.activate_generation`**
Re-segmentation does not produce overlapping active segments because:
- New segments default to `is_active = false` (`004_segments_embeddings.sql:62`).
- `embedder.activate_generation` (`embedder.py:476-504`) finds the prior `active` generation for the same `(parent_kind, parent_id)`, sets it to `superseded`, and flips its segments and embeddings to `is_active=false` *before* activating the new one — same transaction.
- The partial unique indexes (`segments_active_conversation_sequence_idx WHERE is_active=true`, `004_segments_embeddings.sql:75-77`) enforce that no two active segments share `(conversation_id, sequence_index)` even if a bug tried.
- `segment_generations_active_parent_idx` (`004_segments_embeddings.sql:33-35`) enforces at most one `active` generation per parent.

The doc's claim of "catastrophic duplicate retrieval" does not match the as-built code. There is no observable bug here under the current activation path.

---

## Additional Findings

### A. `max_tokens=4096` is the dominant failure cause, not endpoint instability
All 15 "segmenter returned invalid JSON" rows are `json.JSONDecodeError: Unterminated string starting at` with character offsets 4865–19000 — the model is being cut off mid-string by `max_tokens` (`segmenter.py:28`, `DEFAULT_MAX_TOKENS=4096`). Under `response_format=json_schema strict=true` constrained sampling on a 180k-char window (`DEFAULT_WINDOW_CHAR_BUDGET=180000`), 4096 output tokens is not enough to emit a `content_text` field that summarizes the window. **Fix:** raise `ENGRAM_SEGMENTER_MAX_TOKENS` to ≥16384 (Qwen3.6-35B has the headroom in a 256K context with single-slot serving).

### B. `default_segmenter_model_id()` probes `/v1/models` on every batch and turns transient connection resets into batch crashes
`segmenter.py:145-149` falls through to `probe_segmenter()` if `ENGRAM_SEGMENTER_MODEL` is unset. `segment_pending:514` and `segment_conversation:305` both call this. A `ConnectionResetError` on the probe (line 1278 in the log traceback) raises `SegmenterServiceUnavailable` *before* `create_generation`, so:
- No `segment_generations` row exists for the conversation.
- The `mark_parent_segmenting_generations_failed` call in `segment_pending`'s `except` handler updates zero rows.
- No conversation-scope progress upsert happens (we never entered the body of `segment_conversation` past the probe).
- The exception propagates and crashes the whole batch under `SegmenterServiceUnavailable`.

**Fix:** set `ENGRAM_SEGMENTER_MODEL` to the exact id from `/v1/models` so probing is skipped, OR cache the probe result for the lifetime of the process. Even better: when probing fails, fall back to a configured-or-cached id rather than aborting.

### C. `retry_segmenter_prompt` amplifies the truncation it claims to fix
`segmenter.py:752-768` builds the retry prompt by *prepending* an instruction block to the original prompt. The combined input is strictly larger than the first attempt, leaving fewer tokens before the same `max_tokens` ceiling. When the original failure was JSON truncation, the retry is *more* likely to truncate, not less. The instruction "Keep each segment `content_text` concise" is advisory — strict-schema sampling will not respect it. **Fix:** on parse failures, either bump `max_tokens` for the retry, shrink the window, or both. Distinguish parse-failure retries from transport-failure retries — the current single retry strategy treats them identically.

### D. `SIGALRM` deadline is main-thread-only and silently no-ops elsewhere
`segmenter_request_deadline` (`segmenter.py:728-749`) uses `signal.setitimer(ITIMER_REAL)`. Per CPython, signal handlers can only be installed from the main thread; `signal.signal` raises `ValueError` from worker threads. If the segmenter is ever invoked from a thread (e.g., a future supervisor with concurrent batches), the deadline is unenforceable. **Fix:** either document the main-thread requirement explicitly, or replace with a per-request `socket` timeout passed through `urllib.request.urlopen(timeout=...)` (already done — `segmenter.py:194` passes `SEGMENTER_REQUEST_TIMEOUT_SECONDS` to `http_json`). The `SIGALRM` wrapper is redundant once the urlopen timeout is set, and the redundancy is what makes the thread-safety hazard load-bearing.

### E. `expand_message_span` silently turns sparse citations into dense spans
`segmenter.py:1060-1074` takes whatever `message_ids` the LLM cites, picks `min`/`max` sequence_index, and returns *every* message in `[min, max]`. The trigger `validate_conversation_segment_message_ids` accepts this because the expanded list is contiguous and ordered. Consequence: a segment whose `content_text` was generated from `[m1, m5, m10]` ends up associated with `m1..m10`. Privacy reclassification on `m3` invalidates this segment even though `m3` did not contribute to `content_text`; conversely, a future evidence-trace that expects `message_ids` to mean "messages that produced this content" is wrong. The behavior is asserted in `test_phase2_segments.py::test_privacy_tier_inherits_parent_and_covered_raw_rows`, so it appears intentional — but the semantic gap should be documented in the prompt and in `prompts/phase_2_segments_embeddings.md`.

### F. Window overlap creates legitimate cross-segment `message_ids` collisions
`WINDOW_OVERLAP_MESSAGES=1` (`segmenter.py:36`, `build_windows:995`). Two consecutive windows share their last/first message. Each window is segmented independently; both can produce a segment that cites the overlapping message. The partial unique indexes on `(conversation_id, sequence_index)` *do not* catch this — they constrain `sequence_index`, not `message_ids` membership. Result: the same raw message is cited by two active segments → double-counted in retrieval, double-invalidated under privacy reclassification. **Fix:** either deduplicate at activation time (drop one of the overlapping segments, or re-number `sequence_index` to leave a gap), or reduce overlap to zero and accept boundary-cut risk.

### G. Probe failure leaves no progress trail
Following from B: when `default_segmenter_model_id()` raises `SegmenterServiceUnavailable`, no `consolidation_progress` row is upserted for the conversation, and no `segment_generations` row is created. The `error_count` mechanism is therefore blind to repeated probe failures. If finding 2's filter is added later, it must also cover the probe-failure path or those conversations will never be classified as poisonous. **Fix:** wrap the probe call so any `SegmenterServiceUnavailable` *before* the main try-block still upserts conversation-scope progress with `increment_error=True`.

### H. `IK_LLAMA_BASE_URL` resolves at import time and `ensure_local_base_url` is checked twice
`segmenter.py:22` reads the env var at module import. `IkLlamaSegmenterClient.__init__` accepts a `base_url` argument that defaults to that frozen value, then re-validates with `ensure_local_base_url`. If a test or alternate config changes `ENGRAM_IK_LLAMA_BASE_URL` after import, the default still points at the old URL. Minor; flagged for future refactor only.

---

## Revised Action Items

1. **Raise `ENGRAM_SEGMENTER_MAX_TOKENS` to 16384** (or higher) — this single change eliminates ~half of current failures.
2. **Pin `ENGRAM_SEGMENTER_MODEL`** to the literal model id and stop probing per batch — eliminates the connection-reset cascade.
3. **Add `error_count >= 3` filter** scoped to the `service_unavailable` carve-out and the `p.status='pending'` clause; the rest of the failure modes are already self-limiting.
4. **Mark conversation as failed when probe fails** — wrap `default_segmenter_model_id()` in `segment_conversation` so probe failures still upsert conversation progress with `increment_error=True`.
5. **On parse-failure retry, increase `max_tokens` or shrink the window** rather than prepending more text to the prompt.
6. **Document `expand_message_span` semantics** explicitly so consumers don't assume citation-fidelity.
7. **Decide on window overlap policy**: dedupe at activation or set `WINDOW_OVERLAP_MESSAGES=0`.
8. **Drop the redundant `SIGALRM` wrapper** in favor of the existing urlopen timeout, or document the main-thread requirement.

Items 2 and 4 are not in the doc above this section but are the immediate ops fix.

---

## Verification (Codex, 2026-05-01)

Checked against current branch `phase-2-segments-embeddings` after commits
`01d77c3` and `02292d2`.

### Top-Level Findings

1. **Missing `segment_generations` schema: NOT REPRODUCED.**
   `migrations/004_segments_embeddings.sql` creates `segment_generations`
   and `segments.generation_id` (`lines 11-47`). This is present in both
   the migration and runtime DB.

2. **Missing poison-pill avoidance: PARTIALLY REPRODUCED.**
   `fetch_pending_conversations` does not enforce any `error_count` ceiling
   (`segmenter.py:614-654`). However, non-service failures are self-limiting
   because failed generations with `failure_kind != 'service_unavailable'`
   block re-fetch under the `NOT EXISTS` clause. The real loop risk is
   `service_unavailable` and explicit `p.status='pending'` queues. Also note:
   the current `LEFT JOIN` only joins progress rows where `p.status='pending'`,
   so an `error_count` cap cannot be implemented correctly by simply adding
   `p.error_count < 3` to the existing join.

3. **Reclassification invalidation dead code: NOT REPRODUCED.**
   `cli.py` calls `apply_reclassification_invalidations(conn)` in both
   `segment` and `pipeline` before segment batches run (`cli.py:109-149`).

4. **Missing invalidation columns: NOT REPRODUCED.**
   `segments.invalidated_at` and `segments.invalidation_reason` exist in the
   migration (`lines 62-64`), and the segment immutability trigger permits
   those metadata updates (`lines 134-172`).

5. **Old active rows not deactivated: NOT REPRODUCED.**
   `embedder.activate_generation` deactivates prior active generation rows and
   their `segments` / `segment_embeddings` before activating the new generation
   (`embedder.py:476-524`). The partial unique indexes also enforce active
   parent/sequence uniqueness.

### Service Instability Diagnosis

The evidence points to two separate causes:

1. **Invalid JSON failures are mostly output truncation.**
   The DB currently has 25 `segmenter_error` failed generations. Fifteen of
   those are real local-LLM parse failures with
   `JSONDecodeError: Unterminated string...`; ten were cleanup rows from the
   earlier interrupted run. That makes `max_tokens=4096` plus large windows the
   dominant content-level failure mode.

2. **Endpoint instability is likely llama-server memory/long-request pressure.**
   The live server is:
   ```text
   llama-server ... --model Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf
     --gpu-layers 99 --ctx-size 262144 --batch-size 2048
     --cache-type-k q8_0 --cache-type-v q8_0 --parallel 1
   ```
   On the RTX 3090 it was using about `23532 MiB` of `24576 MiB` VRAM, while
   Ollama used another `518 MiB`. That leaves very little VRAM headroom. The
   run logs then show exactly the symptoms expected from a server under long
   generation / memory pressure: 180s request deadline failures, `/v1/models`
   socket timeouts, `RemoteDisconnected`, and `ConnectionResetError`.

This is not caused by the Ollama embedder. Embedding remained fast and stable;
the failures are all on `http://127.0.0.1:8081` chat/probe calls.

### Additional Findings

#### I. `service_unavailable` still rolls back successful work from the current batch

Timeouts are now parent-level failures, but `SegmenterServiceUnavailable` still
re-raises from `segment_pending` (`segmenter.py:550-561`). `run_segment_batches`
commits only after `segment_pending` returns (`cli.py:214-222`). Therefore a
connection reset on parent N rolls back any successful parents earlier in that
same batch and the next supervisor loop repeats them. This was observed in the
run logs around iteration 14/16.

**Fix:** treat `service_unavailable` as a parent-level retryable failure with
progress/error accounting, or commit each parent independently. For long
operator runs, use `--limit 1` until this is fixed.

#### J. Probe failures happen before any conversation progress can be recorded

`segment_pending` resolves `model_id = model_version or default_segmenter_model_id()`
before fetching candidates (`segmenter.py:514`). If `/v1/models` times out or
resets, there is no selected conversation and no conversation-scoped progress
row can be updated. This makes probe instability invisible to per-parent
`error_count`.

**Fix:** pin `ENGRAM_SEGMENTER_MODEL` in the runtime environment and cache probe
results inside the process. Probe failures should update batch-level progress
with enough detail to diagnose service health.

#### K. Window-boundary merge is not implemented

D029 asks for overlapping windows and boundary merge when overlap shows the same
topic. `build_windows` creates overlapping windows (`segmenter.py:962-996`), but
`segment_conversation` inserts each window's drafts independently; there is no
adjacent-boundary comparison or merge step before insert. This can produce
adjacent segments that duplicate the overlap message or split one topic across
the boundary.

**Fix:** add a post-window normalization step before insert, or set overlap to
zero until merge semantics are implemented.

#### L. The retry prompt increases input size after truncation failures

`retry_segmenter_prompt` prepends more instructions to the original prompt
(`segmenter.py:752-768`). For invalid JSON caused by output truncation, this is
unlikely to help and can make the request more expensive. The retry should
instead shrink the input window, raise `max_tokens`, or request summary-only
content before retrying.

#### M. The current server launch is too aggressive for a long unattended pass

Given observed VRAM use, a safer operational profile is:

- pin `ENGRAM_SEGMENTER_MODEL` to avoid repeated probes;
- increase output budget for parse failures (`ENGRAM_SEGMENTER_MAX_TOKENS=16384`
  is the next experiment);
- reduce `ENGRAM_SEGMENTER_WINDOW_CHAR_BUDGET` materially before raising the
  context/server load further;
- restart llama-server with a smaller `--ctx-size` or lower GPU offload/KV cache
  footprint if endpoint resets continue.

The most likely immediate cause of "service instability" is the combination of
huge context (`262144`), full offload of a 35B model, q8 KV cache, and large
segmentation requests on a nearly full 24GB GPU.
