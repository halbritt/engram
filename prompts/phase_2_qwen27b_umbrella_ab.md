# Targeted Qwen 27B A/B for the Umbrella-Overlap Pattern

You are running a small, read-mostly A/B segmentation experiment to decide
whether the umbrella-over-sub-segments pattern surfaced in
`docs/reviews/v1/PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04.md` is a model-side
behavior of Qwen 35B A3B IQ4_XS or a prompt-shape issue that any local model
will reproduce.

This is a 5-parent ad-hoc test. It does not change the production segmenter,
does not promote a new default model, and does not violate D042's Tier 2 gate
because it does not perform a corpus-wide model swap. It writes new
`segment_generations` at `status='segmented'` with `is_active=false` segments,
which are invisible to retrieval. No cloud / hosted services.

## Goal

Decide between three follow-ups for the 45 parents flagged in the audit:

- **27B is clean on the worst offenders** → re-segment the 45 parents under
  Qwen 27B Q5_K_M. Phase 3 reads the new generations after embedding +
  cutover (D031). Tier 2 still gates a full-corpus model swap.
- **27B reproduces the umbrella pattern** → it is a prompt-shape issue. Bump
  `SEGMENTER_PROMPT_VERSION` with an explicit no-overlap clause and add a
  post-INSERT validator that rejects sibling segments with
  `message_ids && other.message_ids`. Re-run the 45 under the new prompt.
- **27B over-fragments badly** (matches the benchmark's `longer_run` hint at
  high `segs/expected`, low `endpoint_only_big`, many tiny adjacent segments
  inside one parent) → defer to a wider Tier 2 slice before any change.

## Read First

1. `AGENTS.md`
2. `README.md`
3. `HUMAN_REQUIREMENTS.md`
4. `DECISION_LOG.md`, especially D030, D031, D034, D036, D038, D040, D042
5. `BUILD_PHASES.md`
6. `ROADMAP.md`
7. `src/engram/segmenter.py`
8. `migrations/004_segments_embeddings.sql`
9. `docs/reviews/v1/PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04.md`
10. `docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_RUN_2026_05_04.md`

## Challenge Parents

Five worst-offender parents from the audit. Drop any that no longer have an
active 35B generation, or substitute equivalents from the audit's "top
conversations by total span expansion" table.

| conversation_id | title | observed pattern under 35B |
| --- | --- | --- |
| `1ffd2141-04fb-48d6-8c0e-dc06a593ab8e` | LLM hosting options | umbrella seg covers 252 msgs, swallows 5 sub-segs |
| `43651f99-93b0-4755-898b-41a4a71cfac9` | "Lexus" | duplicate-segment (seq 1 ≡ seq 2 byte-identical) |
| `3f732fbc-5f7f-4570-962a-6d80fbf76259` | PG&E Smart Meter | partial umbrella (seq 2 swallows seqs 3, 4) |
| `e013fb48-7998-4b9f-860b-c0b23e53feed` | Harbor Freight dust collector | partial umbrella |
| `ce42c24a-a687-4e9e-a5f8-eda384dcda3d` | PSU build | partial umbrella |

## Pre-Flight: Server Swap

Same pattern the early-signal benchmark used. Stop the operational stack so
the watchdog cannot SIGTERM mid-generation (per
`docs/reviews/v1/PHASE_2_CODE_REVIEW_FINDINGS.md` Empirical Findings I), then
launch Qwen 27B Q5_K_M manually on `127.0.0.1:8081`.

```bash
systemctl --user stop ik-llama-server.service
systemctl --user stop ik-llama-watchdog.timer
systemctl --user stop openclaw-gateway.service

# Launch Qwen 27B Q5_K_M with the same flags used in the benchmark — see
# .scratch/benchmarks/segmentation/early-signal-20260504T073337Z/model-server/qwen_27b_q5_k_m_d034.log
# Bind to 127.0.0.1:8081.

# Verify model id, context window, and a tiny D034-style structured smoke:
curl -s http://127.0.0.1:8081/v1/models | python3 -m json.tool
curl -s http://127.0.0.1:8081/props   | python3 -m json.tool | head -20
curl -s http://127.0.0.1:8081/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"any","messages":[{"role":"user","content":"reply with {\"ok\":true}"}],
       "stream":false,"temperature":0,"max_tokens":32,
       "chat_template_kwargs":{"enable_thinking":false},
       "response_format":{"type":"json_schema","json_schema":{"name":"Smoke","strict":true,
         "schema":{"type":"object","required":["ok"],"properties":{"ok":{"type":"boolean"}},
                   "additionalProperties":false}}}}'
```

Do not proceed if the smoke completion does not return schema-valid JSON
inside `choices[0].message.content`.

## The A/B Run

Save this script as `.scratch/ab_27b_test.py`:

```python
"""Targeted A/B: re-segment 5 worst-offender parents under Qwen 27B.

Inserts new segment_generations at status='segmented' (is_active=false), so
production retrieval is unaffected. ik-llama must be running Qwen 27B on
127.0.0.1:8081 before invoking this script.
"""
from __future__ import annotations

from engram.db import connect
from engram.segmenter import segment_conversation


CHALLENGE_PARENTS = [
    ("1ffd2141-04fb-48d6-8c0e-dc06a593ab8e", "LLM hosting options"),
    ("43651f99-93b0-4755-898b-41a4a71cfac9", "Lexus"),
    ("3f732fbc-5f7f-4570-962a-6d80fbf76259", "PG&E Smart Meter"),
    ("e013fb48-7998-4b9f-860b-c0b23e53feed", "Harbor Freight dust collector"),
    ("ce42c24a-a687-4e9e-a5f8-eda384dcda3d", "PSU build"),
]

# Pin model_version explicitly so the segment_generations row clearly
# attributes its output to 27B regardless of what the ik-llama probe reports.
MODEL_VERSION = "/home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf"


def main() -> int:
    with connect() as conn:
        for parent_id, label in CHALLENGE_PARENTS:
            print(f"\n=== {label}  ({parent_id}) ===", flush=True)
            try:
                result = segment_conversation(
                    conn,
                    parent_id,
                    model_version=MODEL_VERSION,
                )
            except Exception as exc:
                print(f"  FAILED: {type(exc).__name__}: {exc}", flush=True)
                continue
            print(
                "  generation_id="
                f"{result.generation_id} status={result.status} "
                f"segments_inserted={result.segments_inserted} "
                f"windows={result.windows_processed} "
                f"skipped_windows={result.skipped_windows} noop={result.noop}",
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Invoke:

```bash
mkdir -p .scratch
ENGRAM_DATABASE_URL="postgresql:///engram" .venv/bin/python .scratch/ab_27b_test.py 2>&1 \
  | tee .scratch/ab_27b_test.log
```

`segment_conversation` keeps the existing `SEGMENTER_PROMPT_VERSION`
(`segmenter.v2.d034.enum-ids.tool-placeholders`) and switches only
`segmenter_model_version`. `find_existing_generation` returns `None` for the
(prompt, 27B-model) tuple, so a fresh `segment_generations` row is created at
`status='segmenting'` and transitions to `'segmented'` at the end of the run.
Its segments land at `is_active=false` per D031, so production retrieval is
not disturbed.

## Inspection SQL

```sql
-- A. Confirm the new generations exist and inserted segments
SELECT g.id::text, g.parent_id::text, g.status,
       (SELECT count(*) FROM segments s WHERE s.generation_id = g.id) AS segs
FROM segment_generations g
WHERE g.segmenter_prompt_version = 'segmenter.v2.d034.enum-ids.tool-placeholders'
  AND g.segmenter_model_version  = '/home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf'
  AND g.parent_id IN (
    '1ffd2141-04fb-48d6-8c0e-dc06a593ab8e',
    '43651f99-93b0-4755-898b-41a4a71cfac9',
    '3f732fbc-5f7f-4570-962a-6d80fbf76259',
    'e013fb48-7998-4b9f-860b-c0b23e53feed',
    'ce42c24a-a687-4e9e-a5f8-eda384dcda3d'
  )
ORDER BY g.parent_id;

-- B. Per-parent segment shape under 27B (compare to the audit's per-parent listings)
SELECT s.conversation_id::text AS conv,
       s.sequence_index,
       (SELECT min(m.sequence_index) FROM messages m WHERE m.id = ANY(s.message_ids)) AS min_seq,
       (SELECT max(m.sequence_index) FROM messages m WHERE m.id = ANY(s.message_ids)) AS max_seq,
       cardinality(s.message_ids) AS stored,
       jsonb_array_length(s.raw_payload->'model_output'->'message_ids') AS model_count,
       COALESCE(jsonb_array_length(s.raw_payload->'span_expansion_added'), 0) AS added,
       s.raw_payload->>'window_index' AS win,
       left(s.summary_text, 110) AS summary
FROM segments s
JOIN segment_generations g ON g.id = s.generation_id
WHERE g.segmenter_prompt_version = 'segmenter.v2.d034.enum-ids.tool-placeholders'
  AND g.segmenter_model_version  = '/home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf'
ORDER BY s.conversation_id, s.sequence_index;

-- C. Overlap check on the new (27B) segments — same shape as the audit
WITH new_segs AS (
  SELECT s.*
  FROM segments s
  JOIN segment_generations g ON g.id = s.generation_id
  WHERE g.segmenter_prompt_version = 'segmenter.v2.d034.enum-ids.tool-placeholders'
    AND g.segmenter_model_version  = '/home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf'
),
pairs AS (
  SELECT a.conversation_id, a.sequence_index AS a_seq, b.sequence_index AS b_seq,
         (SELECT count(*) FROM unnest(a.message_ids) ma JOIN unnest(b.message_ids) mb ON ma = mb) AS overlap_count
  FROM new_segs a JOIN new_segs b
    ON a.conversation_id = b.conversation_id
   AND a.sequence_index < b.sequence_index
   AND a.message_ids && b.message_ids
)
SELECT count(*) AS overlapping_pairs_27b,
       count(DISTINCT conversation_id) AS conversations_with_overlap_27b,
       sum(overlap_count) AS total_overlap_messages_27b,
       max(overlap_count) AS max_overlap_27b
FROM pairs;

-- D. Endpoint-only / heavy-expansion classification on the new run
WITH new_ratios AS (
  SELECT cardinality(s.message_ids) AS stored,
         jsonb_array_length(s.raw_payload->'model_output'->'message_ids') AS model_count,
         COALESCE(jsonb_array_length(s.raw_payload->'span_expansion_added'),0) AS added
  FROM segments s
  JOIN segment_generations g ON g.id = s.generation_id
  WHERE g.segmenter_prompt_version = 'segmenter.v2.d034.enum-ids.tool-placeholders'
    AND g.segmenter_model_version  = '/home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf'
)
SELECT count(*) AS total_27b_segments,
       count(*) FILTER (WHERE model_count = 2 AND stored >= 10) AS endpoint_only_big_27b,
       count(*) FILTER (WHERE model_count = 2 AND stored >= 50) AS endpoint_only_xxl_27b,
       count(*) FILTER (WHERE added > 0 AND stored >= 20 AND model_count <= 0.3 * stored) AS heavy_expansion_big_27b
FROM new_ratios;

-- E. Side-by-side per-parent: 35B (active) vs 27B (new generation)
WITH per_parent AS (
  SELECT s.conversation_id,
         g.segmenter_model_version AS model,
         count(*) AS segs,
         max(cardinality(s.message_ids)) AS max_stored,
         max(COALESCE(jsonb_array_length(s.raw_payload->'span_expansion_added'),0)) AS max_added,
         count(*) FILTER (
           WHERE jsonb_array_length(s.raw_payload->'model_output'->'message_ids') = 2
             AND cardinality(s.message_ids) >= 20
         ) AS endpoint_only_big
  FROM segments s
  JOIN segment_generations g ON g.id = s.generation_id
  WHERE s.conversation_id IN (
    '1ffd2141-04fb-48d6-8c0e-dc06a593ab8e',
    '43651f99-93b0-4755-898b-41a4a71cfac9',
    '3f732fbc-5f7f-4570-962a-6d80fbf76259',
    'e013fb48-7998-4b9f-860b-c0b23e53feed',
    'ce42c24a-a687-4e9e-a5f8-eda384dcda3d'
  )
  AND (
    g.status = 'active'
    OR g.segmenter_model_version = '/home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf'
  )
  GROUP BY s.conversation_id, g.segmenter_model_version
)
SELECT conversation_id::text,
       max(segs)              FILTER (WHERE model LIKE '%35B%') AS segs_35b,
       max(segs)              FILTER (WHERE model LIKE '%27B%') AS segs_27b,
       max(max_stored)        FILTER (WHERE model LIKE '%35B%') AS max_stored_35b,
       max(max_stored)        FILTER (WHERE model LIKE '%27B%') AS max_stored_27b,
       max(endpoint_only_big) FILTER (WHERE model LIKE '%35B%') AS endpoint_only_big_35b,
       max(endpoint_only_big) FILTER (WHERE model LIKE '%27B%') AS endpoint_only_big_27b
FROM per_parent
GROUP BY conversation_id
ORDER BY conversation_id;
```

## Decision Criteria

For each parent, judge the 27B generation on three axes:

1. **Overlap pairs (query C).**
   - Zero overlap pairs across all 5 parents → 27B does not reproduce the
     umbrella pattern.
   - Same number of pairs as the 35B audit (5 worst-offenders contributed
     ~13 pairs there) → it is a prompt-shape issue, not a model issue.

2. **Endpoint-only-big segments (query D).**
   - `endpoint_only_big_27b ≤ 1` per parent and
     `endpoint_only_xxl_27b = 0` overall → 27B emits enumerated `message_ids`
     instead of `[first, last]` summary endpoints, removing the dominant
     umbrella mechanism.
   - Otherwise → 27B is also taking the endpoint-pair shortcut.

3. **Fragmentation (query E).**
   - `segs_27b` within ~1.5× `segs_35b` per parent → comparable granularity.
   - `segs_27b ≫ 2 × segs_35b` with many small `max_stored_27b` → matches the
     benchmark's over-fragmentation hint; widen Tier 2 before changing
     anything in production.

## Restoration

```bash
# Stop the manually-launched 27B ik-llama process.
systemctl --user start ik-llama-server.service
systemctl --user start ik-llama-watchdog.timer
systemctl --user start openclaw-gateway.service

# Smoke the restored 35B service the same way as before:
curl -s http://127.0.0.1:8081/v1/models
curl -s http://127.0.0.1:8081/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{"model":"any","messages":[{"role":"user","content":"reply with {\"ok\":true}"}],
       "stream":false,"temperature":0,"max_tokens":32,
       "chat_template_kwargs":{"enable_thinking":false},
       "response_format":{"type":"json_schema","json_schema":{"name":"Smoke","strict":true,
         "schema":{"type":"object","required":["ok"],"properties":{"ok":{"type":"boolean"}},
                   "additionalProperties":false}}}}'
```

## Cleanup of the test rows

The 27B generations sit at `status='segmented'` with `is_active=false`
segments — invisible to retrieval, harmless to leave as an audit artifact. If
you want them out of the way:

```sql
UPDATE segment_generations
SET status = 'failed',
    raw_payload = raw_payload || '{"failure_kind":"ab_test_discarded"}'::jsonb
WHERE segmenter_prompt_version = 'segmenter.v2.d034.enum-ids.tool-placeholders'
  AND segmenter_model_version  = '/home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf';
```

Do not `DELETE` — the migration 004 trigger forbids it. Marking the
generation `failed` is the documented exit path (`segmenter.py:982`).

## Report

Write a concise report under:

`docs/reviews/v1/PHASE_2_QWEN27B_UMBRELLA_AB_2026_05_05.md`

Include:

- branch / commit
- ik-llama server invocation and pre-/post- smoke results
- generations created (query A output)
- per-parent shape comparison (query E output)
- overlap count under 27B (query C output)
- endpoint-only / heavy-expansion classification (query D output)
- 5 spot-check notes (one per challenge parent), comparing the new 27B
  segments to the audit's per-parent listings for that same conversation
- decision: `model_swap_45_parents`, `bump_prompt_no_swap`,
  `defer_to_tier2`, or `proceed_unchanged`
- exact SQL/commands run

Do not commit unless asked. Do not change `SEGMENTER_PROMPT_VERSION`. Do not
embed or activate the 27B generations as part of this prompt's scope —
promotion is a separate, follow-on prompt once the decision is made.
