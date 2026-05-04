# Audit Phase 2 Span Expansion Before Claim Extraction

You are auditing the completed/current Phase 2 segmentation run for provenance
precision after the Tier 1 benchmark rejected Qwen 35B on raw unordered
`message_ids`.

## Goal

Determine whether the active segmentation rows are safe enough to use for
Phase 3 claim extraction, or whether some parents should be rerun first.

This is a read-only audit. Do not mutate the production DB, do not run claim
extraction, do not change segmenter behavior, and do not use cloud/hosted
services.

## Read First

1. `AGENTS.md`
2. `README.md`
3. `HUMAN_REQUIREMENTS.md`
4. `DECISION_LOG.md`, especially D030, D034, D036, D040, and D042 if present
5. `BUILD_PHASES.md`
6. `ROADMAP.md`
7. `src/engram/segmenter.py`
8. `migrations/004_segments_embeddings.sql`
9. `docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_RUN_2026_05_04.md`,
   if present in the current branch

## Audit Questions

Answer these:

1. How many active segments have non-empty
   `raw_payload->'span_expansion_added'`?
2. What is the distribution of expansion size: p50, p90, p99, max?
3. Which parent conversations have the largest total span expansion?
4. Do the largest expanded spans look harmless, or do they sweep unrelated
   messages into provenance?
5. Are there any active segments whose stored `message_ids` violate ordering or
   same-conversation integrity?
6. Should Phase 3 proceed, proceed with caveats, or pause for targeted reruns /
   Tier 2 model work?

## Suggested SQL

Start with these, adjusting only if the local schema requires it.

```sql
SELECT
  count(*) AS active_segments,
  count(*) FILTER (
    WHERE COALESCE(jsonb_array_length(raw_payload->'span_expansion_added'), 0) > 0
  ) AS expanded_segments,
  round(
    100.0 * count(*) FILTER (
      WHERE COALESCE(jsonb_array_length(raw_payload->'span_expansion_added'), 0) > 0
    ) / NULLIF(count(*), 0),
    2
  ) AS expanded_pct,
  max(COALESCE(jsonb_array_length(raw_payload->'span_expansion_added'), 0)) AS max_added
FROM segments
WHERE is_active = true;
```

```sql
WITH expansion AS (
  SELECT
    id,
    conversation_id,
    sequence_index,
    COALESCE(jsonb_array_length(raw_payload->'span_expansion_added'), 0) AS added_count,
    cardinality(message_ids) AS stored_message_count,
    jsonb_array_length(raw_payload->'model_output'->'message_ids') AS model_message_count
  FROM segments
  WHERE is_active = true
)
SELECT
  percentile_disc(0.50) WITHIN GROUP (ORDER BY added_count) AS p50_added,
  percentile_disc(0.90) WITHIN GROUP (ORDER BY added_count) AS p90_added,
  percentile_disc(0.99) WITHIN GROUP (ORDER BY added_count) AS p99_added,
  max(added_count) AS max_added,
  avg(added_count)::numeric(10,2) AS avg_added
FROM expansion;
```

```sql
SELECT
  s.id,
  s.conversation_id,
  c.title,
  s.sequence_index,
  COALESCE(jsonb_array_length(s.raw_payload->'span_expansion_added'), 0) AS added_count,
  cardinality(s.message_ids) AS stored_message_count,
  jsonb_array_length(s.raw_payload->'model_output'->'message_ids') AS model_message_count,
  left(s.content_text, 500) AS content_preview
FROM segments s
JOIN conversations c ON c.id = s.conversation_id
WHERE s.is_active = true
ORDER BY added_count DESC, stored_message_count DESC
LIMIT 25;
```

For the top 10-20 expanded segments, inspect the surrounding messages and
compare:

- `raw_payload->'model_output'->'message_ids'`
- `raw_payload->'expanded_message_ids'`
- `raw_payload->'span_expansion_added'`
- stored `content_text`
- actual message text between min/max sequence

## Report

Write a concise audit report under:

`docs/reviews/v1/PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04.md`

Include:

- branch / commit
- DB state summary: active generations, active segments, active embeddings,
  pending segmented generations
- metric table
- top outlier table
- 5-10 spot-check notes
- recommendation: `proceed`, `proceed_with_caveats`, `targeted_rerun`, or
  `pause_for_tier2`
- exact SQL/commands run

Do not commit unless asked.
