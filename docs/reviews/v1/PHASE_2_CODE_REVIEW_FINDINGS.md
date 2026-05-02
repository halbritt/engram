# Phase 2 Code Review Findings

Date: 2026-05-01
Consistency pass: 2026-05-02T00:20:16Z

This document consolidates findings from reviewing the Phase 2 implementation
(`src/engram/segmenter.py`) and pipeline test logs. The initial review stated
that the implementation failed several D027 criteria; later sections verify,
narrow, or supersede those claims.

Reading guide: the opening review and log review are retained as historical
input. Later verification sections adjudicate those claims. Claims that were
later not reproduced are struck through in place; narrowed claims remain
visible with an inline note rather than being deleted. New review entries should
use UTC ISO-8601 timestamps, not date-only headings.

## Code Review (`src/engram/segmenter.py`)

### 1. ~~Missing Schema for `segment_generations`~~ — not reproduced later
The `segmenter.py` script heavily utilizes a `segment_generations` table (e.g., in `create_generation`, `find_existing_generation`, `mark_generation_failed`) to track the batch status of segmentation runs. It also inserts `generation_id` into the `segments` table. However, neither the `segment_generations` table nor the `generation_id` column on `segments` are defined in the `prompts/phase_2_segments_embeddings.md` schema. This discrepancy will cause immediate `UndefinedTable` and `UndefinedColumn` errors upon execution against a strict schema.

### 2. Missing D027 Poison-Pill Avoidance Filter — narrowed later
While `segment_conversation` correctly calls `upsert_progress(..., increment_error=True)` when encountering a `SegmenterRequestTimeout` or general `Exception`, the `fetch_pending_conversations` query does **not** filter out rows where `p.error_count >= 3`. As a result, ~~the `segment_pending` batcher will enter an infinite loop of retrying and failing on poison-pill conversations, entirely defeating the D027 fix~~ later verification narrowed the loop risk to `service_unavailable` and explicit `pending` requeue paths.

### 3. ~~D027 Reclassification Invalidation is Dead Code~~ — not reproduced later
The script includes `apply_reclassification_invalidations(...)` which correctly maps `reclassification` captures to their parent conversations/notes and invalidates the related segments. However, this function is **never called** in the main execution path. It needs to be invoked at the start of `segment_pending` (or explicitly scheduled) so that affected sources are re-queued before the pending fetch runs.

### 4. ~~Non-Existent Columns in Privacy Invalidation~~ — not reproduced later
In the `invalidate_parent_segments` function, the query attempts to record metadata about the privacy invalidation:
```sql
UPDATE segments
SET is_active = false,
    invalidated_at = now(),
    invalidation_reason = %s
WHERE id = ANY(%s::uuid[])
```
The columns `invalidated_at` and `invalidation_reason` are not defined in the `segments` schema and will crash the privacy tier recalculation. The schema either needs these columns added, or the update should be simplified to `SET is_active = false`.

### 5. ~~Incomplete `is_active` Deprecation Logic~~ — not reproduced later
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

### 3. ~~The Poison-Pill Loop is Active~~ — narrowed later
Because the D027 poison-pill skip logic (`error_count >= 3`) is missing from the query implementation, ~~the batch script is continually hitting these failing conversations. It waits 3 minutes for them to time out, fails, and then restarts the loop, preventing the ingestion pipeline from making progress on the rest of the corpus~~ later verification found most non-service failures were self-limiting; the actionable loop risk was retryable service-unavailable and explicit pending requeue paths.

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
1. Update `fetch_pending_conversations` in `segmenter.py` to filter out `error_count >= 3` where retryable paths can loop. Scope later narrowed and implemented.
2. ~~Reconcile the undocumented `segment_generations` table dependency.~~ Not reproduced.
3. ~~Hook up the `apply_reclassification_invalidations` call into the batcher loop.~~ Not reproduced.
4. ~~Implement the `is_active = false` deprecation logic for re-segmentation runs.~~ Not reproduced; activation cutover handles this.

---

## Verification (Opus 4.7, 2026-04-30, timestamp not recorded)

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

## Verification (Codex, 2026-05-01T17:20:31Z)

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

---

## Implemented Follow-Up (Codex, 2026-05-01T18:08:52Z)

The operational fixes selected from these findings landed in the Phase 2 branch:

- `service_unavailable` is now parent-scoped in `segment_pending`; it increments
  failure counts and continues instead of aborting and rolling back the batch.
- Pending retry rows are capped by `ENGRAM_SEGMENTER_MAX_ERROR_COUNT` (default
  `3`) unless they were explicitly queued by reclassification.
- `default_segmenter_model_id()` caches the first successful probe in-process,
  and `segment_pending` records probe failures in `consolidation_progress`
  rather than crashing without a trail.
- Default segmenter settings were moved to `segmenter.v2.d034.robust`:
  `ENGRAM_SEGMENTER_MAX_TOKENS=16384`,
  `ENGRAM_SEGMENTER_RETRY_MAX_TOKENS=32768`,
  `ENGRAM_SEGMENTER_WINDOW_CHAR_BUDGET=60000`, and
  `ENGRAM_SEGMENTER_WINDOW_OVERLAP=0`.
- Truncation-like parse failures retry the same prompt with a larger output
  budget instead of prepending a larger retry prompt.
- The Makefile accepts `SEGMENTER_MODEL=...` for `segment` and `pipeline` so
  operators can pin the local model id and avoid repeated `/v1/models` probes.

Verification after the fix: `make test` passed with `42 passed`.

---

## Empirical Findings from Targeted Re-Run (Opus 4.7, 2026-05-01 17:50–17:56 UTC)

After observing that OpenClaw shares the same `ik-llama` endpoint, I ran two bounded experiments with `openclaw-gateway` stopped, `ENGRAM_SEGMENTER_MAX_TOKENS=16384`, and `ENGRAM_SEGMENTER_MODEL` pinned. Three new findings.

### I. `ik-llama-watchdog.timer` is the actual restart-cascade root cause

Discovered while diagnosing why `ik-llama` core-dumped during the test:

```
~/.config/systemd/user/ik-llama-watchdog.service:
  ExecStart=/bin/bash -c '\
    if ! curl -sf --max-time 15 http://127.0.0.1:8081/health > /dev/null 2>&1; then \
      echo "ik-llama-server health check failed — restarting"; \
      systemctl --user restart ik-llama-server.service; \
    fi'
~/.config/systemd/user/ik-llama-watchdog.timer:
  OnUnitActiveSec=5min
```

The watchdog's own comment notes **`/health` blocks when a slot is occupied**. Combined with the 15s curl timeout and 5-minute cadence:
- Any segmenter request whose generation (incl. queued ghost work) is in flight when the watchdog fires causes `curl` to time out.
- The watchdog responds by calling `systemctl restart ik-llama-server`.
- `restart` sends SIGTERM. The model is mid-generation under flash-attention + q8 KV cache; teardown often segfaults. Journal pattern: `Main process exited, code=dumped, status=6/ABRT` → `Failed with result 'core-dump'`.
- engram's in-flight HTTP request gets `Connection reset by peer` (or `Remote end closed connection without response`).

This explains the `stop-sigterm timed out, Killing.` event at 05:02:08 in the original failure log and the identical event observed at 17:55:34 during today's test. **Both failures are the watchdog, not OpenClaw and not engram.** OpenClaw makes it more likely (slot busier more often) but is not the trigger.

**Recommended fixes (in order of preference):**
1. Replace `/health` with a non-blocking probe in the watchdog: `curl -sf --max-time 5 http://127.0.0.1:8081/v1/models` returns instantly regardless of slot state.
2. Raise the watchdog `--max-time` past the longest expected segmenter wall-clock (≥200s for current settings), and increase the timer cadence so the probe is rarer.
3. Mask the watchdog timer for the duration of a segmenting batch: `systemctl --user stop ik-llama-watchdog.timer` before, `start` after.

Without one of these, intermittent `service_unavailable` is a permanent floor on segmenter reliability — the new error-count cap will count it against conversations that are themselves blameless.

### II. Prefix-cache reuse across consecutive engram batches is large and observable

In the OpenClaw-stopped run with `--batch-size 1 --limit 5`, two conversations completed before the wall-clock cap:

| Conversation | Elapsed |
|---|---|
| 1st (cold cache) | 15.4s |
| 2nd (warm) | 3.4s |

The 4× speedup on the 2nd conversation matches the engram system prompt + JSON schema being identical across requests. ik-llama's `cache_ram_similarity` was 0.50 in earlier journal samples — under engram-only load it should saturate near 1.0 for the prefix.

**Implication for sizing:** the 5-conversation/200s estimate that fits the previous failure-log cadence is wrong. With the watchdog fixed and OpenClaw quiesced, throughput is closer to 5–10 conversations/minute — depending on conversation size, the V1 corpus (~2K conversations) finishes in 3–7 hours, not days. Segmenting overnight under a paused watchdog is realistic.

### III. `ENGRAM_SEGMENTER_MAX_TOKENS=16384` validated against a known parse-failed conversation

Targeted re-run of `01612456-5420-4199-a58a-ea2c575ab5bb` (previously failed with `Unterminated string starting at: line 1 column 4866 (char 4865)` — the classic 4096-output-token wall):

| Metric | Previous | This run |
|---|---|---|
| Result | `segmenter returned invalid JSON` | `status=segmented` |
| Elapsed | n/a (failed before parsing) | 23.2s |
| Segments produced | 0 | 2 (seq_index 0 and 1) |
| Combined `content_text` length | n/a | 6420 chars |
| Combined `message_ids` cardinality | n/a | 124 |

The output exceeded the prior 4865-char truncation point cleanly, and the 23.2s wall-clock leaves ample headroom under a 200s deadline. No retry was needed. The bump does not introduce new latency pressure.

**Caveat:** this is one conversation. The full parse-failure class (15 conversations) should be re-run to confirm the rate goes to zero before raising it as a closed-out finding.

### IV. The `expand_message_span` semantic gap is observable in the output

Segment 0 of the rerun cites 69 message_ids; segment 1 cites 55; total = 124. If the conversation has exactly 124 messages, that means `expand_message_span` was a no-op (or the LLM cited contiguous spans naturally). If it has fewer, then `expand_message_span` filled in messages that the LLM did not produce content_text for. The current schema has no way to distinguish "LLM cited" vs "expanded" in `raw_payload` beyond `model_output.message_ids`. **Suggested:** add an explicit `expanded_message_ids` array to `raw_payload` so future evidence-tracing can tell which message_ids contributed to content_text vs which were swept in by span expansion.

---

## Empirical Findings from Post-Upgrade Validation Run (Opus 4.7, 2026-05-01 18:18–18:27 UTC)

After upgrading `ik_llama.cpp` past the `aae9b8d2` revert of the "Faster prompt processing on CUDA" commit (#1687) and rebuilding `llama-server`, I ran `engram.cli segment --limit 5 --batch-size 5` with `openclaw-gateway` quiesced. The watchdog timer was left running to validate the prior `/v1/models` fix under load.

### V. New ik-llama build is stable; watchdog fix held under a 311-second generation

| # | Conversation | Result | Elapsed |
|---|---|---|---|
| 1 | `003a1e2c-3a8b-4550-b695-f88d0377c576` | failed | 469.2s |
| 2 | `00454dfb-5861-4ad1-9158-5e33288edc95` | done, 1 segment | 20.7s |
| 3 | `0045e546-9fd6-40ed-87ee-2bdf439c8b69` | done, 1 segment | 11.2s |
| 4 | `0055ca11-e960-483d-9be1-991c50e3ae58` | done, 1 segment | 12.8s |
| 5 | `0065ecb2-c786-4766-9126-1a1a3e1f347b` | done, 1 segment | 5.1s |

`llama-server` PID held constant across the run — no SIGTERM cascades, no core dumps, no `Restart=on-failure` events in the journal — even though conv 1's retry attempt held the slot for **311 seconds of decode** (`eval time = 311342.85 ms / 32768 tokens`). The watchdog timer fired during that window and returned 200 against `/v1/models` without disturbing the in-flight slot. Finding I's fix is operationally validated.

The 4× prefix-cache speedup from Finding II reproduces (20.7 → 11.2 → 12.8 → 5.1s) on a different five-conversation sample, confirming the pattern is not specific to the previous test set.

### VI. `RETRY_MAX_TOKENS=32768` is not a universal escape hatch — some conversations exhaust both budgets

Conv 1 (`003a1e2c`) hit the max-tokens ceiling on **both** attempts:

| Attempt | `max_tokens` | Decoded tokens | Decode time | Outcome |
|---|---|---|---|---|
| First | 16384 | **16384/16384** | 146.6s | Truncated JSON → parse failure → retry |
| Retry | 32768 | **32768/32768** | 311.3s | Truncated JSON → parse failure |
| Total wall-clock | — | — | 469.2s | `failed`, segmenter request deadline exhausted |

Both responses returned `200 OK` with `truncated=false` and `n_decoded == max_tokens` — the model burned the entire budget producing tokens that did not close the JSON object. This is a runaway-generation pattern (likely repetition trap), not a "needs more headroom" pattern. Doubling `RETRY_MAX_TOKENS` again would consume more wall clock without changing the outcome.

**Implication for the parse-failure class:** the 15-conversation re-run proposed in Finding III's caveat will likely split into two populations:
1. *Insufficient headroom* — fits in 16384 with sane content. Already fixed by D034.
2. *Runaway generation* — exhausts any budget. Needs a different mitigation.

**Mitigation candidates for the runaway class:**
- Detect `n_decoded == max_tokens` server-side and treat the response as `service_unavailable`-equivalent rather than retrying with a larger budget. Saves 311s of decode on a foregone conclusion.
- Add a soft repetition penalty (`repeat_penalty` ≈ 1.05–1.10, `repeat_last_n` ≈ 256) for the segmenter request profile only. D034 currently keeps sampling deterministic; this would need a documented exception.
- Try a different segmentation prompt for these conversations (smaller windows, simpler schema). They may be ones that segmentation is structurally unsuited to.

The conv 1 outlier is stage-2 information; it does not block phase-2 progress, but it should be tracked so re-derivation runs don't keep paying the 469s tax per affected conversation.

## Phase 2 Bounded Soak (Opus 4.7 / coding agent, 2026-05-01 18:55–23:47 UTC)

Bounded soak per `prompts/phase_2_soak_test.md`. Run was cut short by an ik-llama backend wedge unrelated to engram; surfaces below as Finding VII. The supervisor itself handled the wedge cleanly.

### Run setup

- Branch `phase-2-segments-embeddings` @ `c1494f5`, working tree clean.
- Invocation: `python -m engram.cli pipeline --limit 150 --segment-batch-size 1 --embed-batch-size 100`. The `pipeline-isolated` Makefile target does **not** accept `PIPELINE_ARGS` pass-through (`grep -n PIPELINE_ARGS Makefile` is empty), so the spec's fallback applied: direct python invocation with `openclaw-gateway.service` and `ik-llama-watchdog.timer` stopped via a hand-rolled trap that mirrors the Makefile pattern.
- Operational profile: `segmenter.v2.d034.robust` defaults from `segmenter.py:28-37` (`MAX_TOKENS=16384`, `RETRY_MAX_TOKENS=32768`, `WINDOW_OVERLAP=0`); `ENGRAM_SEGMENTER_MODEL` pinned to the `/v1/models` literal id.
- Run window: 18:55:35Z → 23:47:28Z (4h 51m wall, far past spec's 2h budget — the wedge stretched it). Terminated via SIGTERM; trap cleanly restored both quiesced units.

### Counts (run window only)

| Phase | Count |
|---|---|
| Conversations started | 86 |
| Segmenter passes (`segmented`, awaiting embed) | 52 |
| Segmenter failures (`failed`) | 33 |
| In-flight at SIGTERM | 1 |
| Active activations from this run | 0 |
| Embed-phase invocations | 0 (never reached) |

### Failures by `failure_kind`

| `failure_kind` | Count | Phase |
|---|---|---|
| `segmenter_error` | 7 | Pre-wedge — actual Phase 2 failure modes |
| `segmenter_timeout` | 26 | Post-wedge — every request hit the 600s client deadline |

### Elapsed per parent

Successes (n=52, all pre-wedge): `mean=15.2s, min=1.6s, p50=7.0s, p90=32.4s, p99/max=144.7s`. p99 is one outlier (`0533c804`, 13 segments / 2 windows).

Failures by elapsed bucket (heuristic — `last_error` is not in `raw_payload`; see Finding VIII):

| Bucket | Count | Interpretation |
|---|---|---|
| `<146s` | 4 (9.0, 39.6, 89.7, 111.9) | Non-runaway — short parse / validation failures |
| `~146–250s` | 1 (158.4) | Boundary — possible first-attempt-runaway just past decode budget |
| `~300–400s` | 2 (334.4, 336.8) | Retry-runaway, tightly clustered (cf. Finding VI) |
| `=600.0s` | 26 | Client timeout after the wedge (Finding VII) |

**Pre-wedge non-runaway rate: 4 / 58 ≈ 6.9%** — above the 2% PASS threshold, but n=58 is undersized for a confident verdict (run intended n=150).

### VRAM trend

| Checkpoint | used | free | util |
|---|---|---|---|
| Pre-soak | 22365 MiB | 1767 MiB | 0% |
| Mid-run (~47 min in) | 24131 MiB | 1 MiB | 0% |
| At SIGTERM | 24131 MiB | 1 MiB | 0% |

Saturated by mid-run; the dead CUDA context (Finding VII) never released its 23594 MiB allocation in `llama-server` PID 3716256.

### Spec-mandated checks

- Active-sequence uniqueness — **0 violations** ✓
- `message_ids` integrity on the 97 segments produced this run — **0 NULL or empty** ✓
- `expand_message_span` invocation rate (computed on `segmented`-status rows since `active` count is 0) — **97/97 = 100%** carry non-empty `expanded_message_ids`
- Embed cache hit rate — **N/A** (embed never ran)
- Idempotency re-run — **NOT TESTED** (ik-llama wedged; defer to next soak)

### VII. ik-llama cuBLAS error wedges inference; supervisor handles it cleanly

`journalctl --user -u ik-llama-server.service` at 19:27:16Z (31:41 into the soak):

```text
CUDA error: an unsupported value or parameter was passed to the function
  current device: 0, in function ggml_cuda_op_mul_mat_cublas at ggml-cuda.cu:1647
  cublasSgemm_v2(ctx.cublas_handle(id), CUBLAS_OP_T, CUBLAS_OP_N, ...)
ggml-cuda.cu:132: CUDA error
```

The server **did not crash**. Process 3716256 stayed alive, kept holding 23594 MiB of GPU memory, kept serving `/v1/models` with 200. Inference was permanently broken — every subsequent `/v1/chat/completions` sat in a hung slot until the python client cut it off at 600s. Journal shows `srv stop: cancel task` on each cancelled request; no automatic recovery.

**Phase 2 supervisor behaviour across this fault was clean**:
- 26 consecutive `segmenter_timeout` failures committed cleanly with populated rows.
- Zero supervisor crashes across ~4h 20m of consecutive failures.
- No partial activations, no orphaned segments, no rolled-back parents.
- Active-sequence and `message_ids` integrity preserved end-to-end.

This is a **positive signal for Phase 2** — the supervisor is robust to a severe backend wedge. The fix belongs at the inference-runtime layer:

- `ik-llama-server.service` needs `Restart=on-failure` plus a journal-based detector for `CUDA error` log lines (or equivalent), since the process did not exit on its own.
- The existing watchdog probes `/v1/models`, which returned 200 throughout the wedge — so it would not have caught this case even if it had been running. A health probe that exercises actual inference (a tiny prompt) would.

Quiescing the watchdog during `pipeline-isolated` runs (per the Makefile comment) is correct for normal generation, but it removes the recovery path entirely if ik-llama wedges. Consider a "soak-mode" watchdog that probes inference instead of `/v1/models`.

### VIII. Failure payload diagnostics insufficient for the spec's runaway-classification rule

Current `failure_kind=segmenter_error` payload:

```json
{
  "max_tokens": 16384,
  "failure_kind": "segmenter_error",
  "window_count": 1,
  "window_char_budget": 60000,
  "request_profile_version": "ik-llama-json-schema.d034.v1"
}
```

The spec's runaway-classification rule (Finding VI: *"last attempt's decode count == `max_tokens` AND `last_error` matches `Unterminated string`"*) cannot be applied — `last_error`, `attempts`, and decode counts are not persisted. Heuristic elapsed-time bucketing was used instead, but it disagrees on boundary cases (the 158.4s failure here is unclassifiable).

**Recommended changes to `mark_generation_failed` in `segmenter.py`** — persist:

- `last_error`: the last attempt's exception message or parse-error text.
- `attempts`: count of attempts made.
- `decode_counts`: per-attempt list of decoded-token counts (to evaluate `last decode == max_tokens` mechanically).
- `attempt_max_tokens`: per-attempt list (since `retry_max_tokens` may grow per Finding VI).

This is the minimum to apply the runaway rule without guessing from wall clock.

### PASS / FAIL

**Inconclusive.** The supervisor passed every supervisor-level criterion the spec defines (no aborts, zero integrity violations across two checks). The non-runaway failure rate trended toward FAIL at 4/58 ≈ 6.9% — directional read only, sample undersized. Embed-phase criteria are untested.

### Recommended next steps

1. **Restart `ik-llama-server.service`** (fresh CUDA context). Handed off.
2. ~~**Implement Finding VIII** before re-running, so the next soak can apply the runaway rule mechanically.~~ Implemented in the follow-up below.
3. **Investigate pre-wedge short failures** — 4 in 58 is meaningful even with the small sample. Specific parents to inspect: `053fc988` (9.0s — suspiciously fast), `040c3803` (39.6s), `02302711` (89.7s), `01c3f1c8` (111.9s).
4. **Re-run the soak** post-restart, post-Finding-VIII, then immediately re-run `--limit 150` again to validate idempotency.
5. ~~**Consider a 10-conversation pre-flight smoke** before each soak (~5 min) to catch backend wedges before burning the 2-hour budget.~~ Promoted into P-HEALTH / D035 in the follow-up below.

---

## Implemented Follow-Up (Codex, 2026-05-02T00:14:48Z–00:17:00Z)

The bounded-soak findings produced two Phase 2 branch commits:

- `4ef1000 Add Phase 2 health preflight diagnostics`
- `9c2da6d Document Phase 2 health preflight`

Implemented changes:

- Finding VIII is implemented in `src/engram/segmenter.py`: failed
  `segment_generations.raw_payload` now records `failure_kind`, `last_error`,
  `attempts`, `attempt_max_tokens`, `decode_counts` when the endpoint exposes
  them, and `attempt_errors`.
- P-HEALTH is added to `prompts/phase_2_segments_embeddings.md`: a tiny
  D034-profile completion smoke before and after a 10-conversation preflight,
  with the instruction to stop the soak if either smoke fails.
- D035 is added to `DECISION_LOG.md` to make inference-level health checks and
  per-attempt diagnostics an accepted operational invariant for long local-LLM
  runs.
- `docs/segmentation.md` now documents the P-HEALTH operator flow and the
  failure-diagnostic payload fields.

Verification:

- `.venv/bin/python -m compileall -q src`
- `.venv/bin/python -m pytest tests/test_phase2_segments.py -q` → `6 passed,
  16 skipped`
- `.venv/bin/python -m pytest -q` → `12 passed, 32 skipped`
- `git diff --check` clean

Still open after this follow-up:

- Restart or otherwise recover `ik-llama-server.service` before the next soak.
- Re-run the 150-conversation soak with P-HEALTH and the new diagnostics.
- Investigate the four pre-wedge short failures if they reproduce with the new
  diagnostic payload.

## Phase 2 Bounded Soak Round 2 (Opus 4.7 / coding agent, 2026-05-02 04:44:55Z–06:26:48Z UTC, --limit 300)

Post-CUDA-upgrade re-run on a freshly rebuilt `ik_llama.cpp` (sm_86, CUDA
12.8.93, driver 595.71.05, kernel 6.8.0-111-generic). Increased from runbook
default `--limit 150` to `--limit 300` per operator request to amortize
warm-up and broaden the failure-class sample.

### Run setup

- Branch tip at start: `8a0cb98` (Finding VIII outer-handler fix; see below).
- Pre-run inference smoke: PASS (`{"ok": true}`, ~70 ms decode).
- Pre-soak idempotency probe (`--limit 10` × 2): PASS — 20 distinct parents
  across both runs, zero overlap, zero duplicate generations at this version.
- Operational profile: `MAX_TOKENS=16384`, `RETRY_MAX_TOKENS=32768`,
  `WINDOW_OVERLAP=0`, `--segment-batch-size 1`, `--embed-batch-size 100`,
  `--segment-retries 1`, `timeout --foreground 3h`.
- Isolation: `openclaw-gateway.service` and `ik-llama-watchdog.timer` stopped
  via hand-rolled trap (Makefile `pipeline-isolated` does not pass through
  `PIPELINE_ARGS`); both restored on EXIT.

### Counts

| metric                          | value |
|---------------------------------|-------|
| Parents attempted               | 300   |
| Segmented                       | 280   |
| Failed                          | 20    |
| Skipped                         | 0     |
| Segments created                | 477   |
| Segments embedded (this run)    | 300   |
| Embed cache hits                | 28    |
| Generations activated           | 166   |
| `segmented` waiting for embed   | 211   |
| Pipeline rc                     | 1 (clean — non-zero only because segment step had failures; embed step rc=0) |

The 211-`segmented`/166-`active` gap is mechanical: with `--limit 300` and
`--embed-batch-size 100`, the embed step processes the first 300 segments
across all 280 successful parents, then exits at `--limit`. The remaining
177 segments (and the 114 generations that own them) wait for the next run.
Not a bug; an interaction between `--limit` and `--embed-batch-size` worth
keeping in mind.

### Failure classification (mechanically applied via Finding VIII)

| failure_class        | count | pattern |
|----------------------|------:|---------|
| `unknown_message_id` | 19    | Single attempt; `last_error` matches `segmenter returned unknown message id: <X>`; no retry |
| `runaway_unterminated` | 1   | Two attempts, `attempt_max_tokens=[16384, 32768]`, `decode_counts` hit each ceiling, `last_error` matches `Unterminated string` (Finding VI signature) |

Runaway count (1/300 = 0.33%) is consistent with Finding VI base rate
(15/3437 ≈ 0.4%).

### Elapsed per parent

| group                    | n   | mean   | p50  | p90   | p99    | max    |
|--------------------------|----:|-------:|-----:|------:|-------:|-------:|
| Successful (segmented)   | 280 | 15.6 s | 8.7 s | 32.4 s | 62.5 s | 583.7 s |
| Failed (`unknown_message_id`) | 19 | 69.3 s | 35.5 s | 299.5 s | 318.5 s | 318.5 s |
| Failed (`runaway`)       |   1 | 394.6 s | — | — | — | — |

The single 583.7 s success is a long multi-window or multi-segment parent
that completed cleanly — not a runaway. `unknown_message_id` failures span
9.7 s to 318.5 s; the long tail represents parents where the model took
many tokens to produce JSON that then failed validation, distinct from
runaways which decode to `attempt_max_tokens` and timeout/abort.

### VRAM trend

- Start (model loaded, idle): 19475 MiB / 24576 MiB
- End (model loaded, idle):   19513 MiB / 24576 MiB
- Drift over 1h42m soak:       +38 MiB
- Mid-run snapshots:            ~19500 MiB (stable, GPU util 86–90 %)

Never approached the 23.5 GiB stop-condition threshold. The cuBLAS wedge
class (Finding VII) did not reproduce.

### Spec-mandated checks

- Active-sequence uniqueness: **0** duplicates ✓
- `message_ids` integrity: **0** NULL, **0** empty across 535 active segments ✓
- `expand_message_span` invocation rate: 110/110 (100 %) on segments created
  in this run — Finding IV pattern preserved.
- Idempotency invariant: **0** of soak's 300 parents are eligible for
  re-pickup by `fetch_pending_conversations` at the same prompt+model
  version; **0** parents have multiple generations at this version. The
  candidate selector correctly enforces "process once per
  (parent, prompt+model version)."

### Code change made during this run

`8a0cb98 Thread error diagnostics through outer segmenter failure handler` —
shipped between the first short validation and the soak. The original
Finding VIII patch (`4ef1000`) instrumented the per-window inner handler
(`segmenter.py:472`) but missed the outer per-conversation handler
(`segmenter.py:662`) which calls `mark_parent_segmenting_generations_failed`
without an `error` argument. The first short validation produced a failure
with empty diagnostics (`last_error`/`attempts`/`attempt_max_tokens` all
NULL), exposing the gap. Fix: thread `error: BaseException | None = None`
through `mark_parent_segmenting_generations_failed`, route through
`segmenter_failure_payload(failure_kind, error)` instead of the bare
`{"failure_kind": ...}` literal, and pass `error=exc` from the caller.

This soak's failures all carry `last_error` correctly. The runaway carries
full retry diagnostics (`attempts`, `attempt_max_tokens`, `decode_counts`).
The `unknown_message_id` class lacks `attempt_max_tokens`/`decode_counts`
because the exception fires after the segmenter call returned valid JSON
(no retries to record); only `last_error` is meaningful for that class,
which is sufficient for mechanical classification.

### IX. Model output produces non-existent `message_id` references at >1 % rate

Across 300 parents, 19 (6.3 %) failed validation in
`segment_conversation`'s draft-processing loop with `last_error` matching
`segmenter returned unknown message id: <X>`. Sample `<X>` values from this
run:

- Plain integers outside the window: `10`, `12`, `24`, `100`
- Hallucinated full UUIDs that don't appear in the conversation:
  `7fc0499c-5f08-4ee-9496-ce9a8708acbc`, `e61a2888-85b9-4a76-861b-cdf3d8926b11`
- Malformed UUIDs (wrong group lengths or extra hyphens):
  `14ff171a-0cbd-4d15-8560c497c342` (16-char group 4 instead of 4-12),
  `941e3a9b-e203-4615-91d9-41a3-bf69-fe41b8b6f720` (7 groups instead of 5),
  `7e9af114-43b0-b3c7-775f217799a8` (4 groups), `redacted`
  (free-form text in the id field).

The supervisor handles each cleanly: the parent is marked `failed` with
diagnostics, no integrity violation, no impact on subsequent parents. This
is **not** a Phase 2 supervisor bug — it is a model output quality issue
under the current prompt + JSON-schema constraints. The JSON schema does
not pin `message_id` to a regex matching the conversation's actual ids,
so the strict-mode constraint accepts any string and we catch the
inconsistency only at draft-processing time.

The 6.3 % rate trips two runbook FAIL conditions:

- "Non-runaway failure rate ≤ 2 %" — actual 6.3 %.
- "A new failure mode not explainable by findings A–VI appears at > 1 %
  rate" — `unknown_message_id` is not in A–VI.

Possible mitigations (not implemented this run):

- Tighten the JSON schema: enumerate `message_id` candidates per window so
  the model is constrained at decode time. Highest signal-to-noise option;
  may run into schema-size limits on `--parallel 1` ik-llama.
- Soft-recover: if the returned `message_id` doesn't match exactly, attempt
  a fuzzy match (Levenshtein ≤ 1, prefix match, etc.) before failing.
  Lower-priority; trades validation strictness for recovery.
- Sampling: bump temperature slightly to see if it changes the rate
  (current is `temperature=0`).

### PASS / FAIL

PASS criteria:

- ✅ Supervisor never aborts; every batch iteration commits or rolls back ≤ 1
  parent.
- ❌ Non-runaway failure rate 6.3 % (>2 %).
- ✅ Zero active-sequence violations.
- ✅ Zero `message_ids` integrity violations.
- ✅ Idempotency invariant holds (zero re-pickup eligibility, zero
  duplicate generations).

FAIL conditions:

- ✅ No supervisor crash that drops committed work.
- ✅ No active-sequence or `message_ids` integrity violation.
- ✅ `service_unavailable` rate 0 % (≤ 5 %).
- ✅ Idempotency: re-run would not produce new active segments for soak's
  300 parents.
- ❌ A new failure mode (`unknown_message_id`) appears at > 1 % rate.

**Net: FAIL on PASS criteria due to Finding IX, but the supervisor itself
is healthy.** All five integrity/stability invariants hold; the failure
mode is upstream of Phase 2 (model output quality) rather than in the
supervisor's contract.

### Recommended next steps

1. Decide on Finding IX mitigation strategy (schema tightening vs. soft
   match vs. retry-on-validation-failure). Open a P-FRAG-style probe to
   estimate likely effectiveness before changing the prompt path.
2. Drain the 211 `segmented` rows by running an embed-only pass (e.g.
   re-run with a higher `--embed-batch-size` or a separate `embed`
   subcommand if available) so the corpus reaches a consistent state.
3. Investigate the 19 failed parents under a larger `WINDOW_OVERLAP` or
   higher `MAX_TOKENS` profile — operator's noted post-soak idea — to see
   if those parents segment cleanly with more context budget. Their
   `parent_id`s are recorded in `segment_generations.status='failed'` for
   easy slicing.
