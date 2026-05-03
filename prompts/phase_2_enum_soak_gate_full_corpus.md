# Phase 2 Enum-ID Soak Gate To Full AI-Conversation Corpus

> Hand this to a coding agent on branch `phase-2-segments-embeddings`.
> Goal: finish the current bounded Phase 2 soak, evaluate explicit gates, and
> only proceed to the full AI-conversation corpus if the gates pass. Do not
> change code. Record findings, commit, and push.

## Context

The current soak is testing the enum-constrained segmenter:

- `segmenter_prompt_version = segmenter.v2.d034.enum-ids`
- `request_profile_version = ik-llama-json-schema.d034.v2`
- expected fix: `unknown_message_id` should drop to zero or near-zero
- OpenClaw should remain stopped during segmentation
- ik_llama should remain healthy with stable VRAM

## 1. Let Current `--limit 300` Soak Finish

Monitor until the active soak exits naturally or reaches its timeout.

Track:

```bash
nvidia-smi
journalctl --user -u ik-llama-server.service -n 200 --no-pager
```

After the soak exits, run a post-run P-HEALTH completion smoke:

```bash
curl -sS --max-time 10 \
  http://127.0.0.1:8081/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf",
    "stream": false,
    "temperature": 0,
    "top_p": 1,
    "max_tokens": 32,
    "chat_template_kwargs": {"enable_thinking": false},
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "HealthCheck",
        "strict": true,
        "schema": {
          "type": "object",
          "additionalProperties": false,
          "properties": {"ok": {"type": "boolean"}},
          "required": ["ok"]
        }
      }
    },
    "messages": [{"role": "user", "content": "Return JSON with ok true."}]
  }'
```

Pass requires HTTP 200 and JSON content with `ok: true`.

## 2. Gather Soak Results

Use the soak start timestamp in these queries.

```bash
psql postgresql:///engram -X -c "
  SELECT status, count(*)
  FROM segment_generations
  GROUP BY status
  ORDER BY status;

  SELECT raw_payload->>'failure_kind' AS failure_kind,
         raw_payload->>'last_error' AS last_error,
         count(*)
  FROM segment_generations
  WHERE created_at > '<SOAK_START_UTC>'::timestamptz
    AND status = 'failed'
  GROUP BY 1,2
  ORDER BY count(*) DESC;

  SELECT count(*) AS active_sequence_dupes
  FROM (
    SELECT conversation_id, sequence_index
    FROM segments
    WHERE is_active=true AND conversation_id IS NOT NULL
    GROUP BY 1,2 HAVING count(*) > 1
  ) q;

  SELECT count(*) AS active_empty_message_ids
  FROM segments
  WHERE is_active=true
    AND conversation_id IS NOT NULL
    AND cardinality(message_ids)=0;

  SELECT count(*) AS pending_segment_generations
  FROM segment_generations
  WHERE status IN ('segmented','embedding');
"
```

Also compute/record from the run log:

- parents attempted
- segmented
- failed
- skipped
- segments created
- embeddings created
- generations activated
- cache hits
- elapsed time
- p50 / p90 / max parent elapsed if easy
- failure classes
- `unknown_message_id` count
- VRAM start/end/mid if available
- post-run P-HEALTH result

## 3. Gate Before Full AI-Conversation Corpus

Proceed to the full AI-conversation corpus only if all PASS gates hold.

PASS gates:

- Current `--limit 300` soak completed without supervisor crash.
- Post-run P-HEALTH passed.
- `unknown_message_id` failures = 0, or at most 1 and clearly explained.
- `service_unavailable` = 0.
- `segmenter_timeout` = 0 unless clearly attributable to a manually interrupted
  run.
- No CUDA/cuBLAS/illegal-memory/access errors in ik_llama journal during the
  soak.
- VRAM did not approach the stop threshold; no sustained near-24 GiB condition.
- Active sequence duplicates = 0.
- Active empty `message_ids` = 0.
- Non-runaway failure rate <= 2%.
- Runaway failures are rare and classifiable from `attempt_max_tokens` /
  `decode_counts`.
- Pending segmented backlog is either zero or can be drained with embed-only
  before full AI-conversation corpus.

FAIL / STOP gates:

- Any `unknown_message_id` cluster > 1%.
- Any backend wedge: `/v1/models` works but chat completion fails/hangs.
- Any CUDA/cuBLAS error in journal.
- Repeated `service_unavailable`.
- Active sequence duplicate > 0.
- Active empty `message_ids` > 0.
- Non-runaway failure rate > 2%.
- New unclassified failure class > 1%.

If any FAIL gate trips, do not run the full AI-conversation corpus. Record
findings, commit, push, and stop.

## 4. Drain Embeddings If Needed

If soak passes but leaves pending `segmented` / `embedding` generations, run
embed-only before full AI-conversation corpus.

Use `prompts/phase_2_embed_drain.md`.

Short form:

```bash
restore() {
  systemctl --user start openclaw-gateway.service 2>/dev/null || true
}
trap restore EXIT INT TERM
systemctl --user stop openclaw-gateway.service 2>/dev/null || true

export ENGRAM_DATABASE_URL=postgresql:///engram

mkdir -p logs
ts=$(date -u +%Y%m%dT%H%M%SZ)

.venv/bin/python -m engram.cli embed \
  --batch-size 1000 \
  2>&1 | tee "logs/phase2_embed_drain_${ts}.log"
```

Repeat until pending generations are drained as far as `engram embed` can drain
them.

## 5. If Gates Pass, Run Full AI-Conversation Corpus

This run covers ChatGPT, Claude, and Gemini conversations only. It excludes
Obsidian notes, live captures, and any other non-conversation source types.

Keep OpenClaw stopped during the run. Stop the watchdog if the current soak
protocol does so.

```bash
cd ~/git/engram

restore() {
  systemctl --user start openclaw-gateway.service 2>/dev/null || true
  systemctl --user start ik-llama-watchdog.timer 2>/dev/null || true
}
trap restore EXIT INT TERM

systemctl --user stop openclaw-gateway.service 2>/dev/null || true
systemctl --user stop ik-llama-watchdog.timer 2>/dev/null || true

export ENGRAM_DATABASE_URL=postgresql:///engram
export ENGRAM_SEGMENTER_MODEL=/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf
export ENGRAM_SEGMENTER_MAX_TOKENS=16384
export ENGRAM_SEGMENTER_RETRY_MAX_TOKENS=32768
export ENGRAM_SEGMENTER_WINDOW_OVERLAP=0

mkdir -p logs
ts=$(date -u +%Y%m%dT%H%M%SZ)

.venv/bin/python -m engram.cli pipeline \
  --segment-batch-size 1 \
  --embed-batch-size 1000 \
  --segment-retries 1 \
  2>&1 | tee "logs/phase2_full_corpus_${ts}.log"
```

Monitor:

```bash
nvidia-smi -l 30
journalctl --user -u ik-llama-server.service -f
```

Stop full AI-conversation corpus if:

- backend wedges
- CUDA/cuBLAS error appears
- VRAM pins near 24 GiB with no progress
- repeated `service_unavailable`
- repeated new failure class appears

## 6. Record Findings

Append to:

```text
docs/reviews/v1/PHASE_2_CODE_REVIEW_FINDINGS.md
```

For the bounded soak, add a section with UTC timestamp and:

- command
- start/end
- branch commit
- runtime versions
- pass/fail gate result
- counts
- failure classes
- `unknown_message_id` result
- backend health
- VRAM trend
- embed status
- recommendation

If full corpus runs, append another section with the same structure.

Then:

```bash
git status --short
git add docs/reviews/v1/PHASE_2_CODE_REVIEW_FINDINGS.md
git commit -m "Record Phase 2 enum-id soak findings"
git push origin phase-2-segments-embeddings
```

If full corpus also completes and findings are included, use:

```bash
git commit -m "Record Phase 2 full corpus findings"
```

## Final Response

Report:

- whether bounded soak passed gates
- whether full corpus was started
- if full corpus was not started, which gate failed
- log paths
- commit hash pushed
