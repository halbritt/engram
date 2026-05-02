# Phase 2 Soak Test (2-hour bounded run)

> Hand this to a coding agent on the `phase-2-segments-embeddings` branch.
> Goal: a bounded operational soak of `segment` + `embed` over a real
> slice, producing empirical findings appended to
> [PHASE_2_CODE_REVIEW_FINDINGS.md](../docs/reviews/v1/PHASE_2_CODE_REVIEW_FINDINGS.md).
>
> This is **not** the eval smoke gate (Phase 5), **not** P-FRAG
> (depends on Phase 3), and **not** a corpus-wide run.

## Read first
1. [PHASE_2_CODE_REVIEW_FINDINGS.md](../docs/reviews/v1/PHASE_2_CODE_REVIEW_FINDINGS.md) — known failure modes A–VI; do not re-discover them. Findings V (watchdog stable) and VI (runaway-generation class) drive the budget below.
2. [phase_2_segments_embeddings.md](phase_2_segments_embeddings.md) — Phase 2 contract.
3. [Makefile](../Makefile) — `pipeline-isolated` target. Confirm it accepts argument pass-through; if it doesn't (`grep -n PIPELINE_ARGS Makefile`), invoke `python -m engram.cli pipeline ...` directly with the watchdog timer manually stopped.

## Pre-run

1. Services responsive:
   - `curl -s http://127.0.0.1:8081/v1/models` returns Qwen3.6-35B.
   - `curl -s http://127.0.0.1:11434/api/tags` returns `nomic-embed-text`.
   - `psql "$ENGRAM_DATABASE_URL" -c '\dt'` works.
2. `make migrate` (idempotent).
3. **Pin** `ENGRAM_SEGMENTER_MODEL` to the literal id from `/v1/models` so the per-batch probe is skipped (finding J).
4. Confirm operational profile from `segmenter.v2.d034.enum-ids`:
   `ENGRAM_SEGMENTER_MAX_TOKENS=16384`,
   `ENGRAM_SEGMENTER_RETRY_MAX_TOKENS=32768`,
   `ENGRAM_SEGMENTER_WINDOW_OVERLAP=0`.
5. Snapshot start state and capture the output for the findings entry:
   ```sql
   SELECT status, count(*) FROM segment_generations GROUP BY status;
   SELECT count(*) FROM segments WHERE is_active=true;
   SELECT count(*) FROM segment_embeddings WHERE is_active=true;
   SELECT failure_kind, count(*) FROM segment_generations
     WHERE status='failed' GROUP BY failure_kind;
   ```
6. `nvidia-smi --query-gpu=memory.used,memory.free --format=csv` — record.

## The run

```bash
mkdir -p logs
ts=$(date -u +%Y%m%dT%H%M%SZ)
make pipeline-isolated \
  PIPELINE_ARGS="--limit 150 --segment-batch-size 1 --embed-batch-size 100" \
  2>&1 | tee logs/phase2_soak_${ts}.log
```

Why these flags:
- `--limit 150` — at the validated post-Finding-II throughput (~5–10 conv/min) plus 1–2 expected runaway victims @ ~7.8 min each (Finding VI), 150 fits in roughly 30–60 min, leaving 60–90 min for windowed parents, embed, idempotency re-run, and analysis. Historical runaway base rate is 15/3437 ≈ 0.4% so 0–1 victims expected.
- `--segment-batch-size 1` — `service_unavailable` on parent N must not roll back parents 1..N-1 (finding I).
- `pipeline-isolated` — defense in depth. With Finding V validated, the watchdog isn't the critical mitigation, but quiescing it removes one variable from the diagnosis if anything goes wrong.

## Monitor (separate terminals)

- `tail -f logs/phase2_soak_${ts}.log` — `SegmenterRequestTimeout`, `SegmenterServiceUnavailable`, `JSONDecodeError`, `Connection reset`.
- `nvidia-smi -l 30` — flag if VRAM pins above 23.5/24 GB sustained (finding M).
- Live state:
  ```sql
  SELECT status, count(*) FROM segment_generations GROUP BY status;
  SELECT failure_kind, count(*) FROM segment_generations
    WHERE status='failed' AND created_at > now() - interval '2 hours'
    GROUP BY failure_kind;
  ```

### Runaway-victim handling

A parent stuck on its first attempt past ~30s of decode is likely a Finding-VI runaway. It will burn the full `MAX_TOKENS` (~146s decode), retry to `RETRY_MAX_TOKENS` (~311s decode), and finally fail at ~469s wall-clock. Do not retry it manually. If you are tight on budget and a runaway is in flight, SIGINT is acceptable to save ~5 min — record the parent UUID and the decision in the findings.

## Post-run: append a section to PHASE_2_CODE_REVIEW_FINDINGS.md

`## Soak Run <UTC date> (Opus 4.7 / coding agent)`. Include:

- Run window, `--limit`, isolation state.
- Conversations attempted / segmented / failed / skipped.
- Failure breakdown by `failure_kind`. For `segmenter_error` rows, separate **runaway** (last attempt's decode count == `max_tokens` *and* `last_error` matches `Unterminated string`) from **other** parse failures.
- Elapsed per parent: mean, p50, p90, p99. Bucket runaway victims separately.
- Embed cache hit rate.
- VRAM trend (start, mid, end).
- New failure modes not in findings A–VI. (If none, say so.)
- Active-sequence uniqueness check — expected zero rows:
  ```sql
  SELECT conversation_id, sequence_index, count(*) FROM segments
    WHERE is_active=true AND conversation_id IS NOT NULL
    GROUP BY 1,2 HAVING count(*) > 1;
  ```
- Idempotency check — re-run the same `--limit 150` with same versions. Expected zero new active segments. Record actual.
- `expand_message_span` invocation rate (count of segments where `raw_payload->'expanded_message_ids'` is non-empty vs total active in the run). Per finding IV.

## Pass / fail

PASS — all of:
- Supervisor never aborts; every batch iteration commits or rolls back ≤ 1 parent.
- **Non-runaway failure rate ≤ 2%** across attempted parents. Runaway victims (Finding VI) are reported separately and do not count against this threshold.
- Zero active-sequence violations.
- Zero `message_ids` integrity violations on active rows.
- Re-run is a no-op (zero new active segments).

FAIL — any of:
- Supervisor crash that drops committed work.
- Active-sequence or `message_ids` integrity violation on active rows.
- `service_unavailable` rate > 5% (engram is the load problem).
- Re-run produces new active segments under unchanged versions.
- A new failure mode not explainable by findings A–VI appears at > 1% rate.

Either way, append findings, commit, push.

## When wedged

If the supervisor stalls > 10 min with no progress events and no in-flight runaway:
1. Capture `nvidia-smi`, `journalctl --user -u ik-llama-server -n 100`, last 200 log lines.
2. SIGINT the `make` process — the EXIT trap restores the quiesced services.
3. Record the observation. Do not retry without diagnosis.

## When in doubt

Phase 2's failure modes are well-characterized through Finding VI. If something looks new, treat it as new — append a Finding VII with evidence rather than forcing it into an existing bucket.
