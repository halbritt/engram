# Phase 2 Span Expansion Audit — 2026-05-04

## Scope

Read-only audit of the active Phase 2 segmentation rows under the production
segmenter (Qwen 35B A3B, prompt `segmenter.v2.d034.enum-ids.tool-placeholders`)
to decide whether they are safe to feed into Phase 3 claim extraction. Triggered
by the Tier 1 early-signal benchmark (`D042` /
`BENCHMARK_SEGMENTATION_EARLY_SIGNAL_RUN_2026_05_04.md`), which rejected the
benchmark output of Qwen 35B on a 90-parent SuperDialseg slice for unordered /
hallucinated `message_ids`. The benchmark slice is a separate run profile;
this audit checks whether the same failure mode is present in the live
production rows.

No writes were performed. No claim extraction was run. No segmenter behavior
was changed. All queries hit the local `engram` database only.

## Repository State

| Field | Value |
| --- | --- |
| Branch | `master` |
| Commit | `822794dd055ccca6006cfc43a816e41d80adecf8` |
| Working tree | clean |
| Production segmenter prompt | `segmenter.v2.d034.enum-ids.tool-placeholders` |
| Production segmenter model | `/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` |

## DB State Summary

| Metric | Value |
| --- | --- |
| Total conversations | 7916 |
| Total messages | 77387 |
| Active `segment_generations` | 7916 |
| Pending generations (`segmented` / `embedding`) | 0 |
| In-flight generations (`segmenting`) | 0 |
| Failed generations (historical) | 119 |
| Active `segments` | 11169 |
| Total `segments` (incl. superseded) | 16125 |
| Active `segment_embeddings` | 11169 |
| `nomic-embed-text:latest` active embeddings | 11169 |
| `consolidation_progress` segmenter scopes — completed | 7913 |
| `consolidation_progress` segmenter scopes — pending | 3 |
| `consolidation_progress` segmenter scopes — failed | 0 |
| Reclassification captures | 0 |
| Invalidated segments | 0 |

Per-source active segment distribution: chatgpt 6735, gemini 4285,
claude 149.

The 3 pending conversations (`003a1e2c…`, `00454dfb…`, `0045e546…`) all hit
`service_unavailable` three times under the production prompt and still have
active segments under the older `segmenter.v2.d034.enum-ids` prompt version
from a prior run. They are not blocking Phase 3 — their prior-prompt rows are
still active — but they should be re-run when the local segmenter service is
healthy.

The historical 119 failed generations are not active and have no live
segments; they are non-load-bearing state.

## Provenance Integrity

A direct check of the 11169 active segments against the underlying
`messages` table:

| Check | Result |
| --- | --- |
| Cross-conversation `message_ids` | **0 segments** |
| `message_ids` containing rows that don't exist in the parent conversation | **0 segments** |
| `message_ids` that violate `messages.sequence_index` ordering | **0 segments** |

The DB-level `validate_conversation_segment_message_ids` `BEFORE INSERT`
trigger from migration 004 is doing its job: every active row's stored
`message_ids` is the ordered set of ids belonging to that single conversation.
The Tier 1 benchmark's "unordered message_ids" failure mode (D042) is **not**
present in the production database.

## Span Expansion Metrics

`raw_payload->'span_expansion_added'` is the per-segment list of message ids
that `expand_message_span` filled in between `min(model_output.message_ids)`
and `max(model_output.message_ids)`. By design (D038) this includes
null-content / tool-placeholder messages inside a covered span; that is the
intended provenance behavior, not a defect.

Aggregate (all 11169 active segments):

| Metric | Value |
| --- | --- |
| Active segments | 11169 |
| Segments with any span expansion | 998 (8.94%) |
| Mean `span_expansion_added` (overall) | 0.49 |
| `span_expansion_added` p50 / p90 / p99 / max | 0 / 0 / 9 / 250 |
| Stored `cardinality(message_ids)` p50 / p90 / p99 / max | 3 / 13 / 62 / 262 |

Among the 998 segments that did expand:

| Metric | Value |
| --- | --- |
| Mean `span_expansion_added` | 5.48 |
| `span_expansion_added` p50 / p90 / p99 | 1 / 11 / 70 |

So expansion is the exception, not the rule. The bulk of active segments either
came back from the model with a complete enumerated `message_ids` list or
spanned a small enough range that filling in the gap added no provenance
weight.

The right tail (p99 = 70 added, max = 250) is concentrated in a small number
of "endpoint-only" segments where the model emitted `message_ids` of length 2
and the expander swept the entire intervening conversation:

| Bucket | Active segments |
| --- | --- |
| `model_count = 2` and `stored ≥ 10` | 60 |
| `model_count = 2` and `stored ≥ 20` | 38 |
| `model_count = 2` and `stored ≥ 50` | 14 |
| `added > 0` and `stored ≥ 20` and `model_count ≤ 0.3 * stored` | 56 |
| `added > 0` and `stored ≥ 50` and `model_count ≤ 0.3 * stored` | 20 |

These are the rows where it matters whether the swept span is a coherent topic
or a multi-topic block. The spot checks below answer that.

## Top Outlier Segments

Top 14 active segments by stored `cardinality(message_ids)` where the model
emitted only `[first, last]` endpoints:

| segment_id | conversation | min_seq..max_seq | stored | model_count | summary |
| --- | --- | --- | ---: | ---: | --- |
| `259f96e2…` | `1ffd2141…` "LLM hosting options" | 3..254 | 252 | 2 | Local LLM hosting options for 48GB+ models |
| `fc9dd83d…` | `1ffd2141…` (same) | 193..280 | 88 | 2 | Final hardware matrix excluding non-NVLink consumer cards, adding AMD/Mac |
| `9da2cbfa…` | `26c12aef…` "Live/work rental options" | 40..123 | 84 | 2 | Clarification on residential legality for specific properties |
| `b68ece19…` | `641a5e3f…` "Top Japanese Fountain Pens" | 74..153 | 80 | 2 | Sailor nib identification |
| `2d74d7ed…` | `0685d477…` "Change fan mode" | 103..180 | 78 | 2 | Setting up a fan curve based on water temperature |
| `0d1d0ee6…` | `1ffd2141…` (same) | 27..103 | 77 | 2 | Hardware cost and performance comparison table |
| `edeaf43a…` | `9b44cbbf…` "Sea Kayaking Safety Check" | 3..74 | 72 | 2 | Initial safety cross-check for a clockwise sea kayaking trip around Alameda |
| `c60a0f9b…` | `1ffd2141…` (same) | 130..192 | 63 | 2 | Updated hardware matrix with 50-series and TPS |
| `a3435698…` | `b3977835…` "Fujitsu vs Mitsubishi VRF" | 25..86 | 62 | 2 | Comparison of Fujitsu and Mitsubishi ducted VRF heat pumps |
| `e25a6119…` | `4cceb619…` "ST30 vs GTS 360" | 51..111 | 61 | 2 | Comparison of Alphacool NexXxos ST30 against UT60 and GTS |
| `074a1088…` | `dfb3b6e0…` "Type 100 Lathe Chuck" | 42..100 | 59 | 2 | Bearing choice and chuck recommendation for welding positioner |
| `21b51304…` | `17668b91…` "Heat pump commissioning" | 51..105 | 55 | 2 | Compatible air handlers and expected airflow for 37MUHAQ36AA3 |
| `d0ef1ae2…` | `01612456…` "TIG grinder collet" | 72..126 | 55 | 2 | Finding specific Amazon listings for ER-8 collet sets |
| `0d39e846…` | `26c12aef…` (same) | 124..175 | 52 | 2 | Feasibility of classifying space as purely residential for hobby welding |

Top conversations by total span-expansion volume:

| conversation_id | active segments | total added | max added |
| --- | ---: | ---: | ---: |
| `1ffd2141…` LLM hosting options | 9 | 489 | 250 |
| `0523725b…` Ebonite feed compatibility | 16 | 194 | 111 |
| `ee49013c…` 3090 Cooling Performance Issue | 4 | 181 | 178 |
| `26c12aef…` Live/work rental options | 4 | 172 | 82 |
| `17668b91…` Heat pump commissioning process | 5 | 149 | 53 |
| `0685d477…` Change fan mode | 3 | 135 | 76 |
| `641a5e3f…` Top Japanese Fountain Pens | 4 | 130 | 78 |
| `b3977835…` Fujitsu vs Mitsubishi VRF | 4 | 130 | 60 |
| `01612456…` TIG grinder collet compatibility | 2 | 116 | 63 |
| `4cceb619…` ST30 vs GTS 360 Comparison | 2 | 105 | 59 |

## Active-Segment Overlap Within Parent

A second integrity check: do active segments inside the same conversation
overlap on `message_ids`? Each pair of overlapping active segments means a
single message is cited as evidence for two different segment summaries.

| Metric | Value |
| --- | --- |
| Overlapping active pairs (within same parent) | 76 |
| Distinct active segments participating in at least one overlap | 59 |
| Conversations with any overlap | 45 (of 7916, ~0.57%) |
| Total overlapping message citations | 813 |
| Max overlap (single pair) | 77 messages |
| Source-kind distribution of overlap pairs | chatgpt 75, claude 1, gemini 0 |

The unique-active-sequence index from migration 004
(`segments_active_conversation_sequence_idx`) only enforces uniqueness on
`(conversation_id, sequence_index)`; it does not detect message overlap
between distinct sequence positions, which is how the umbrella pattern below
gets in.

## Spot-Check Notes

1. **`1ffd2141…` "LLM hosting options" — umbrella pattern, harmful.**
   `259f96e2…` has `model_output.message_ids = [first, last]` covering
   sequence range 3..254 (252 messages) but `content_text` is only ~4900 chars
   and corresponds to a single early assistant response. The same window
   produced five sibling segments (seqs 1–5) covering smaller ranges
   (27–103, 104–120, 125–128, 130–192, 193–280) — and `259f96e2…`'s
   `message_ids` fully contains seq 1–4 and 62/88 messages of seq 5. The
   model emitted both an "umbrella" segment for the whole hardware-discussion
   block and the per-topic sub-segments, and the active-sequence-uniqueness
   constraint did not catch the overlap. Provenance for this conversation is
   over-claimed: a Phase 3 claim extracted from the umbrella's `content_text`
   would be tagged with 252 evidence message_ids, ~247 of which are not
   actually represented in the embedded text.

2. **`43651f99…` "Lexus" conversation — duplicate-segment pattern.**
   Three active segments in the same window: seq 0 covers seqs 0..64
   (model_count 64, stored 65 — fine), but seq 1 and seq 2 are *byte-identical
   summaries* covering seqs 13..64, both with model_count 51 / stored 52.
   The model emitted two copies of the same sub-segment in one window. The
   ordering-uniqueness index allowed both because they have different
   `sequence_index`. Total overlap with seq 0: 52 messages on each duplicate.
   This is a model-side determinism failure on a single parent.

3. **`26c12aef…` "Live/work rental options" — endpoint-only but disjoint.**
   Four active segments covering sequence ranges 3–14, 40–123, 124–175,
   177–208. Each was emitted as `[first, last]` endpoints (model_count 2)
   and span-expanded; the four expanded ranges are disjoint. Each summary
   describes a distinct topic ("initial request," "residential legality,"
   "hobby welding feasibility," "transition space request"). This is the
   intended use of D038 endpoint-pair output: terse provenance markers
   wrapping a coherent topic. The expansion is benign here.

4. **`0523725b…` "Ebonite feed compatibility" — heavy expansion is mostly
   tool placeholders.** Seq 11 has `model_count = 12` and `stored = 123`
   covering sequence range 236..358. Sampling messages in that range shows
   most of the filled-in messages are empty `assistant`/`tool`/`system`
   rows (no `content_text`). D038 explicitly designed the prompt to include
   null-content message ids inside a covered span, so the expander filling
   these in is by design and does not contaminate provenance with off-topic
   content.

5. **`ee49013c…` "3090 Cooling Performance Issue" — long but topically
   coherent.** Seq 0 covers 3..201 (199 messages, model_count 21). The
   summary "Diagnosing high GPU temperatures (88C) on an RTX 3090 with a
   240mm radiator…" matches the entire span. This is a single long
   debugging thread; the expansion sweeps in many empty/tool messages
   between the model-cited turns. Acceptable.

6. **`3f732fbc…` PG&E Smart Meter — partial overlap pattern.** Seq 2
   covers 43..126 (stored 84, model 39), and seq 3 (77..87) and seq 4
   (88..126) are sub-spans inside it. Same shape as `1ffd2141…` but
   smaller scale.

7. **`e013fb48…` Harbor Freight dust collector — same shape, smaller still.**
   Seq 6 covers 59..112 (stored 54, model 24); seq 7 (85..93) and seq 8
   (91..112) are sub-spans inside it.

8. **`ce42c24a…` PSU/build conversation — same shape.** Seq 3 covers
   70..134 (stored 65, model 22); seqs 4, 5, 6 cover sub-spans inside it.

9. **Old-prompt stragglers.** 11 active segments across 3 conversations
   (`003a1e2c…`, `00454dfb…`, `0045e546…`) are still on
   `segmenter.v2.d034.enum-ids` (no tool-placeholder D038 fix). These were
   marked pending under the new prompt but hit `service_unavailable` three
   times. Provenance integrity for these 11 rows is clean (the same DB
   trigger validated them on insert). Phase 3 can read them, but they
   should be backfilled under the production prompt the next time the
   local service is healthy, for prompt-version consistency.

10. **Adaptive split is healthy.** 228 active segments came from
    `adaptive_split_depth > 0` (max depth 2). The window-bisection failure
    recovery (D037 / D038 era) is working as designed and is not a source
    of provenance issues here.

## Interpretation

The Tier 1 benchmark's rejection of Qwen 35B targeted a benchmark scoring
profile, on raw unordered `message_ids` output before validation. The
production rows in the local DB are protected by:

- the `validate_conversation_segment_message_ids` insert trigger
  (rejects unordered / cross-conversation / unknown ids), and
- `expand_message_span`, which converts whatever the model emits into the
  ordered, contiguous, in-conversation message list for the cited span.

Both are working: 0 / 11169 active rows fail any provenance integrity check.

The remaining risk is **semantic over-claim**, not structural breakage. The
"umbrella over sub-segments" pattern is concentrated in ~5 ChatGPT
conversations where the model emitted both a full-window `[first, last]`
segment and the per-topic sub-segments. In total, 76 overlapping pairs
across 45 conversations, 813 message-citations of overlap. Phase 3 can read
these segments, but claims grounded against an umbrella's full `message_ids`
will have weak per-message support, hurting evidence-attribution precision
on those specific parents.

The *typical* heavy-expansion segment (and the bulk of the right tail) is
benign: D038 by design includes null/tool placeholder messages inside a
covered span as provenance, and most expanded segments are sweeping those
into a single coherent topic, not joining unrelated topics.

## Recommendation

**`proceed_with_caveats`.**

Phase 3 (claim extraction + bitemporal beliefs) can begin against the
current active Phase 2 generations, with the following caveats:

1. **Targeted re-segmentation of the 45 overlap-affected parents is
   recommended before Phase 3 runs over them**, but is not blocking for
   the corpus as a whole (≈0.6% of conversations, all but 1 in ChatGPT).
   The pipeline is non-destructive (D002 / P4): bumping the segmenter
   prompt version on those 45 parents and re-running produces a new
   generation that supersedes the current one only after the new
   embeddings exist (D031). The current rows stay retrievable until
   cutover.
2. **The 3 pending old-prompt parents (`003a1e2c…`, `00454dfb…`,
   `0045e546…`) should be re-run under the production prompt** the next
   time `ik-llama-server.service` is healthy. Their existing rows are
   provenance-clean; this is prompt-version consistency, not a
   correctness fix.
3. **Phase 3 evidence-grounding evals should treat span-expanded
   segments as a known-imprecise category.** Specifically, segments
   where `model_count ≤ 0.3 * stored` and `stored ≥ 20` (56 rows) are
   most likely to over-claim evidence; segments where `model_count = 2`
   and `stored ≥ 50` (14 rows) are the worst offenders. A simple
   diagnostic on Phase 3 output ("how often is the cited message
   actually in the segment's `content_text`?") will surface this if it
   matters in practice.
4. **The Tier 1 benchmark verdict (`reject` for Qwen 35B) does not
   propagate to the production rows.** The benchmark failure mode
   (unordered / hallucinated `message_ids`) is structurally blocked at
   insert. The Tier 2 decision-grade run for Qwen 27B / Gemma vs Qwen
   35B remains the right path for any future model swap, but it does
   not block Phase 3 starting against the current corpus.

If the project prefers a stricter posture, the alternative recommendation
is **`targeted_rerun`** of the 45 overlap-affected parents before Phase 3
starts. That is cheap (45 conversations under the existing prompt+model)
and would remove the umbrella-segment caveat entirely. It does not require
Tier 2 model work.

`pause_for_tier2` is not justified by this audit: nothing about the
production rows requires a model swap before Phase 3 can read them.

## Exact SQL / Commands Run

All queries were issued via `PGDATABASE=engram psql -X -c '…'` against the
local Postgres instance.

```sql
-- DB state summary
SELECT
  (SELECT count(*) FROM segment_generations WHERE status = 'active') AS active_generations,
  (SELECT count(*) FROM segment_generations WHERE status IN ('segmented','embedding')) AS pending_generations,
  (SELECT count(*) FROM segment_generations WHERE status = 'segmenting') AS segmenting_generations,
  (SELECT count(*) FROM segment_generations WHERE status = 'failed') AS failed_generations,
  (SELECT count(*) FROM segments WHERE is_active = true) AS active_segments,
  (SELECT count(*) FROM segments) AS total_segments,
  (SELECT count(*) FROM segment_embeddings WHERE is_active = true) AS active_embeddings,
  (SELECT count(*) FROM segment_embeddings) AS total_embeddings,
  (SELECT count(*) FROM segment_embeddings
    WHERE is_active = true AND embedding_model_version = 'nomic-embed-text:latest') AS nomic_active,
  (SELECT count(*) FROM consolidation_progress
    WHERE stage = 'segmenter' AND scope LIKE 'conversation:%' AND status = 'pending') AS pending_segmenter_progress,
  (SELECT count(*) FROM consolidation_progress
    WHERE stage = 'segmenter' AND scope LIKE 'conversation:%' AND status = 'completed') AS completed_segmenter_progress,
  (SELECT count(*) FROM consolidation_progress
    WHERE stage = 'segmenter' AND scope LIKE 'conversation:%' AND status = 'failed') AS failed_segmenter_progress,
  (SELECT count(*) FROM conversations) AS total_conversations,
  (SELECT count(*) FROM messages) AS total_messages;

-- Generation distribution by version/status
SELECT segmenter_prompt_version, segmenter_model_version, status, count(*)
FROM segment_generations
GROUP BY 1,2,3 ORDER BY 4 DESC;

-- Segment distribution by version/active state
SELECT is_active, segmenter_prompt_version, segmenter_model_version, count(*)
FROM segments
GROUP BY 1,2,3 ORDER BY 4 DESC;

-- Span expansion summary
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

-- Expansion distribution (overall and stored cardinality)
WITH expansion AS (
  SELECT
    COALESCE(jsonb_array_length(raw_payload->'span_expansion_added'), 0) AS added_count,
    cardinality(message_ids) AS stored_message_count
  FROM segments
  WHERE is_active = true
)
SELECT
  percentile_disc(0.50) WITHIN GROUP (ORDER BY added_count) AS p50_added,
  percentile_disc(0.90) WITHIN GROUP (ORDER BY added_count) AS p90_added,
  percentile_disc(0.99) WITHIN GROUP (ORDER BY added_count) AS p99_added,
  max(added_count) AS max_added,
  avg(added_count)::numeric(10,2) AS avg_added,
  percentile_disc(0.50) WITHIN GROUP (ORDER BY stored_message_count) AS p50_stored,
  percentile_disc(0.90) WITHIN GROUP (ORDER BY stored_message_count) AS p90_stored,
  percentile_disc(0.99) WITHIN GROUP (ORDER BY stored_message_count) AS p99_stored,
  max(stored_message_count) AS max_stored
FROM expansion;

-- Distribution among only the expanded segments
WITH expanded AS (
  SELECT COALESCE(jsonb_array_length(raw_payload->'span_expansion_added'),0) AS added_count
  FROM segments
  WHERE is_active = true
    AND COALESCE(jsonb_array_length(raw_payload->'span_expansion_added'),0) > 0
)
SELECT
  count(*) AS expanded,
  percentile_disc(0.50) WITHIN GROUP (ORDER BY added_count) AS p50_added_among_expanded,
  percentile_disc(0.90) WITHIN GROUP (ORDER BY added_count) AS p90_added_among_expanded,
  percentile_disc(0.99) WITHIN GROUP (ORDER BY added_count) AS p99_added_among_expanded,
  avg(added_count)::numeric(10,2) AS avg_added_among_expanded
FROM expanded;

-- Top conversations by total span expansion
SELECT
  s.conversation_id::text AS conv_id,
  count(*) AS segment_count,
  sum(COALESCE(jsonb_array_length(s.raw_payload->'span_expansion_added'), 0)) AS total_added,
  max(COALESCE(jsonb_array_length(s.raw_payload->'span_expansion_added'), 0)) AS max_added_in_conv
FROM segments s
WHERE s.is_active = true
GROUP BY s.conversation_id
ORDER BY total_added DESC
LIMIT 15;

-- Top expanded segments
SELECT
  s.id::text, s.conversation_id::text, c.title, c.source_kind::text,
  s.sequence_index,
  COALESCE(jsonb_array_length(s.raw_payload->'span_expansion_added'), 0) AS added_count,
  cardinality(s.message_ids) AS stored_message_count,
  jsonb_array_length(s.raw_payload->'model_output'->'message_ids') AS model_message_count,
  s.raw_payload->>'window_index' AS window_index,
  s.window_strategy
FROM segments s
JOIN conversations c ON c.id = s.conversation_id
WHERE s.is_active = true
ORDER BY added_count DESC, stored_message_count DESC
LIMIT 25;

-- Provenance integrity checks (ordering, same-conversation, message existence)
WITH msg_seq AS (
  SELECT s.id, s.conversation_id, s.message_ids,
         (SELECT array_agg(m.sequence_index ORDER BY m.sequence_index)
            FROM messages m WHERE m.id = ANY(s.message_ids)) AS seqs,
         (SELECT count(DISTINCT m.conversation_id)
            FROM messages m WHERE m.id = ANY(s.message_ids)) AS distinct_convs,
         (SELECT count(*) FROM messages m WHERE m.id = ANY(s.message_ids)) AS messages_present
  FROM segments s
  WHERE s.is_active = true
)
SELECT
  count(*) AS total_active,
  count(*) FILTER (WHERE distinct_convs <> 1) AS cross_conversation_segments,
  count(*) FILTER (WHERE messages_present <> cardinality(message_ids)) AS missing_message_segments,
  count(*) FILTER (WHERE NOT seqs = (SELECT array_agg(x ORDER BY x) FROM unnest(seqs) x)) AS unordered_segments
FROM msg_seq;

-- Active-segment overlap within parent
WITH pairs AS (
  SELECT a.id AS a_id, a.conversation_id, a.sequence_index AS a_seq, b.sequence_index AS b_seq,
         cardinality(a.message_ids) AS a_size,
         cardinality(b.message_ids) AS b_size,
         (SELECT count(*) FROM unnest(a.message_ids) ma JOIN unnest(b.message_ids) mb ON ma = mb) AS overlap_count
  FROM segments a JOIN segments b
    ON a.conversation_id = b.conversation_id
   AND a.is_active AND b.is_active
   AND a.sequence_index < b.sequence_index
   AND a.message_ids && b.message_ids
)
SELECT count(*) AS overlapping_pairs,
       count(DISTINCT a_id) AS distinct_segments_with_overlap_partner,
       count(DISTINCT conversation_id) AS conversations_with_overlap,
       sum(overlap_count) AS total_overlap_messages,
       max(overlap_count) AS max_overlap_count
FROM pairs;

-- Heavy-expansion classification
WITH ratios AS (
  SELECT cardinality(s.message_ids) AS stored,
         jsonb_array_length(s.raw_payload->'model_output'->'message_ids') AS model_count,
         COALESCE(jsonb_array_length(s.raw_payload->'span_expansion_added'),0) AS added
  FROM segments s WHERE s.is_active = true
)
SELECT
  count(*) FILTER (WHERE model_count = 2 AND stored >= 10) AS endpoint_only_big,
  count(*) FILTER (WHERE model_count = 2 AND stored >= 20) AS endpoint_only_xl,
  count(*) FILTER (WHERE model_count = 2 AND stored >= 50) AS endpoint_only_xxl,
  count(*) FILTER (WHERE added > 0 AND stored >= 20 AND model_count <= 0.3 * stored) AS heavy_expansion_big,
  count(*) FILTER (WHERE added > 0 AND stored >= 50 AND model_count <= 0.3 * stored) AS heavy_expansion_xl
FROM ratios;

-- Per-conversation overlap detail (used for spot-checks)
SELECT s.sequence_index,
       (SELECT min(m.sequence_index) FROM messages m WHERE m.id = ANY(s.message_ids)) AS min_seq,
       (SELECT max(m.sequence_index) FROM messages m WHERE m.id = ANY(s.message_ids)) AS max_seq,
       cardinality(s.message_ids) AS stored,
       jsonb_array_length(s.raw_payload->'model_output'->'message_ids') AS model_count,
       s.raw_payload->>'window_index' AS win,
       s.summary_text
FROM segments s
WHERE s.is_active = true AND s.conversation_id = '<conversation_uuid>'
ORDER BY s.sequence_index;
```

## What This Audit Did Not Do

- Did not run claim extraction.
- Did not change segmenter behavior, prompts, or migrations.
- Did not write to the production DB.
- Did not exercise public-dataset benchmark code or model-comparison runs.
- Did not call out to any cloud / hosted service.
