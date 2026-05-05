# Phase 2 Qwen 27B Umbrella A/B - 2026-05-05

## Scope

Targeted 5-parent A/B run from
`prompts/P020_phase_2_qwen27b_umbrella_ab.md`. The run re-segmented five
overlap-affected ChatGPT conversations with Qwen 27B Q5_K_M under the existing
production prompt:

`segmenter.v2.d034.enum-ids.tool-placeholders`

The run created new `segment_generations` rows at `status='segmented'`.
Inserted `segments` are `is_active=false`; no embeddings were created and no
retrieval-visible cutover was performed.

## Prompt Review Notes

- The original prompt draft had the final two challenge-parent labels swapped
  relative to the live database. The committed prompt now matches the live
  titles: `ce42c24a-a687-4e9e-a5f8-eda384dcda3d` is `Dust collector filter
  upgrade`; `e013fb48-7998-4b9f-860b-c0b23e53feed` is `PSU to CPU cable
  issue`.
- The original run prompt's decision criteria caught overlap, endpoint-pair
  shortcuts, and over-fragmentation, but did not include an
  under-fragmentation / mega-segment guard. That gap matters here: Qwen 27B
  produced one 232-message PSU/cable segment even though it did not overlap
  with siblings.
- The restoration commands started `openclaw-gateway.service` even though it
  was already inactive before this run. The prompt was followed as written.

## Repository State

| Field | Value |
| --- | --- |
| Branch | `master` |
| Commit | `822794dd055ccca6006cfc43a816e41d80adecf8` |
| Working tree before run | untracked `docs/reviews/v1/PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04.md`; untracked prompt file |
| Report artifact | `docs/reviews/v1/PHASE_2_QWEN27B_UMBRELLA_AB_2026_05_05.md` |

## Server Handling

The normal systemd services were inactive before the run:

- `ik-llama-server.service`: inactive since 2026-05-04 18:11:24 UTC
- `ik-llama-watchdog.timer`: inactive since 2026-05-02 16:50:48 UTC
- `openclaw-gateway.service`: inactive since 2026-05-02 16:50:48 UTC

The 27B server was launched manually:

```bash
/home/halbritt/git/ik_llama.cpp/build/bin/llama-server \
  --model /home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf \
  --host 127.0.0.1 \
  --port 8081 \
  --gpu-layers 99 \
  --ctx-size 49152 \
  --flash-attn on \
  --threads 8 \
  --parallel 1 \
  --batch-size 2048 \
  --ubatch-size 256 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --jinja
```

Pre-run 27B checks passed:

| Check | Result |
| --- | --- |
| `/v1/models` | `/home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf`, `max_model_len=49152` |
| `/props` | `model_path=/home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf`, `n_ctx=49152` |
| JSON-schema smoke | `choices[0].message.content == {"ok":true}` |

Post-run 27B smoke also passed with `choices[0].message.content == {"ok":true}`.

After the run, the manual 27B server was stopped and the normal services were
started. Restored 35B checks passed:

| Check | Result |
| --- | --- |
| `/v1/models` | `/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf`, `max_model_len=49152` |
| JSON-schema smoke | `choices[0].message.content == {"ok":true}` |
| systemd services | `ik-llama-server.service`, `ik-llama-watchdog.timer`, and `openclaw-gateway.service` active |

## Generations Created

```text
                  id                  |              parent_id               |  status   | segs
--------------------------------------+--------------------------------------+-----------+------
 b4e023e0-8974-4d0c-a343-300ffd4ce529 | 1ffd2141-04fb-48d6-8c0e-dc06a593ab8e | segmented |   10
 b26068a9-281d-4187-92d6-e7eec0e2b4d9 | 3f732fbc-5f7f-4570-962a-6d80fbf76259 | segmented |    6
 1aeba3df-894c-4d7c-9875-3c0f84abc4a4 | 43651f99-93b0-4755-898b-41a4a71cfac9 | segmented |    2
 f92fed2c-62f0-4a75-b841-7417f4a8ec7e | ce42c24a-a687-4e9e-a5f8-eda384dcda3d | segmented |   15
 8384c850-e442-4e48-9db3-0bc6b3efdbf5 | e013fb48-7998-4b9f-860b-c0b23e53feed | segmented |    5
```

## Per-Parent Shape Comparison

```text
           conversation_id            | segs_35b | segs_27b | max_stored_35b | max_stored_27b | endpoint_only_big_35b | endpoint_only_big_27b
--------------------------------------+----------+----------+----------------+----------------+-----------------------+-----------------------
 1ffd2141-04fb-48d6-8c0e-dc06a593ab8e |        9 |       10 |            252 |             88 |                     4 |                     0
 3f732fbc-5f7f-4570-962a-6d80fbf76259 |        5 |        6 |             84 |             39 |                     0 |                     0
 43651f99-93b0-4755-898b-41a4a71cfac9 |        3 |        2 |             65 |             42 |                     0 |                     0
 ce42c24a-a687-4e9e-a5f8-eda384dcda3d |       13 |       15 |             54 |             23 |                     0 |                     0
 e013fb48-7998-4b9f-860b-c0b23e53feed |       11 |        5 |             65 |            232 |                     0 |                     0
```

## Overlap Check

```text
 overlapping_pairs_27b | conversations_with_overlap_27b | total_overlap_messages_27b | max_overlap_27b
-----------------------+--------------------------------+----------------------------+-----------------
                     0 |                              0 |                            |
```

## Endpoint / Heavy-Expansion Classification

```text
 total_27b_segments | endpoint_only_big_27b | endpoint_only_xxl_27b | heavy_expansion_big_27b
--------------------+-----------------------+-----------------------+-------------------------
                 38 |                     0 |                     0 |                       0
```

## 27B Segment Shape

```text
conv                                  seq  min..max  stored model added win  summary
1ffd2141-04fb-48d6-8c0e-dc06a593ab8e   0    0..26      27    27     0   0  Options for hosting large LLMs locally on GPU
1ffd2141-04fb-48d6-8c0e-dc06a593ab8e   1   27..103     77    77     0   0  Comparison table of hardware options
1ffd2141-04fb-48d6-8c0e-dc06a593ab8e   2  104..124     21    21     0   0  Token generation speed analysis
1ffd2141-04fb-48d6-8c0e-dc06a593ab8e   3  125..139     15    15     0   0  Slack summary table and formatting
1ffd2141-04fb-48d6-8c0e-dc06a593ab8e   4  140..145      6     6     0   0  Image request for framework table
1ffd2141-04fb-48d6-8c0e-dc06a593ab8e   5  146..192     47    47     0   0  Initial hardware matrix and corrections
1ffd2141-04fb-48d6-8c0e-dc06a593ab8e   6  193..280     88    88     0   0  Hardware matrix refinements
1ffd2141-04fb-48d6-8c0e-dc06a593ab8e   7  281..343     63    63     0   1  GPU hardware matrix
1ffd2141-04fb-48d6-8c0e-dc06a593ab8e   8  344..352      9     9     0   1  Add dual RTX 3090 NVLink
1ffd2141-04fb-48d6-8c0e-dc06a593ab8e   9  353..378     26    26     0   1  Tokens/sec on dual RTX 3090 pairs
3f732fbc-5f7f-4570-962a-6d80fbf76259   0    0..31      32    32     0   0  PG&E Stream My Data and compatible devices
3f732fbc-5f7f-4570-962a-6d80fbf76259   1   32..36       5     5     0   0  Interest in Rainforest Eagle-200
3f732fbc-5f7f-4570-962a-6d80fbf76259   2   37..42       6     6     0   0  Eagle-200 setup instructions
3f732fbc-5f7f-4570-962a-6d80fbf76259   3   43..76      34    34     0   0  Rainforest product lineup correction
3f732fbc-5f7f-4570-962a-6d80fbf76259   4   77..87      11    11     0   0  EAGLE 3 for Home Assistant
3f732fbc-5f7f-4570-962a-6d80fbf76259   5   88..126     39    39     0   0  Discount code search
43651f99-93b0-4755-898b-41a4a71cfac9   0    0..22      23    23     0   0  Pre-date advice
43651f99-93b0-4755-898b-41a4a71cfac9   1   23..64      42    42     0   0  Post-date debrief and disengagement advice
ce42c24a-a687-4e9e-a5f8-eda384dcda3d   0    0..7        8     8     0   0  Dust collector filter conversion requirements
ce42c24a-a687-4e9e-a5f8-eda384dcda3d   1    8..12       5     5     0   0  Cyclone separator comparison
ce42c24a-a687-4e9e-a5f8-eda384dcda3d   2   13..29      17    17     0   0  HF motor and WEN impeller CFM
ce42c24a-a687-4e9e-a5f8-eda384dcda3d   3   30..38       9     9     0   0  Smaller cyclone vs Super Dust Deputy XL
ce42c24a-a687-4e9e-a5f8-eda384dcda3d   4   39..43       5     5     0   0  Barrel recommendations
ce42c24a-a687-4e9e-a5f8-eda384dcda3d   5   44..58      15    15     0   0  Impeller removal troubleshooting
ce42c24a-a687-4e9e-a5f8-eda384dcda3d   6   59..81      23    22     1   0  Compact rolling two-stage conversion examples
ce42c24a-a687-4e9e-a5f8-eda384dcda3d   7   82..84       3     3     0   0  Compact cart cut list
ce42c24a-a687-4e9e-a5f8-eda384dcda3d   8   85..92       8     8     0   0  Custom compact design
ce42c24a-a687-4e9e-a5f8-eda384dcda3d   9   93..98       6     6     0   0  Expanding blower inlet to 6 inches
ce42c24a-a687-4e9e-a5f8-eda384dcda3d  10   99..112     14    14     0   0  1500 CFM reality check
ce42c24a-a687-4e9e-a5f8-eda384dcda3d  11  113..114      2     2     0   0  Blower outlet adapter
ce42c24a-a687-4e9e-a5f8-eda384dcda3d  12  115..120      6     6     0   1  DIY outlet adapters and plenum design
ce42c24a-a687-4e9e-a5f8-eda384dcda3d  13  122..126      5     5     0   1  Anti-seize and WEN impeller install
ce42c24a-a687-4e9e-a5f8-eda384dcda3d  14  127..131      5     5     0   1  Welding mounting plates square
e013fb48-7998-4b9f-860b-c0b23e53feed   0    0..231    232   232     0   0  PC build, PSU cable, cooler, and GPU compatibility
e013fb48-7998-4b9f-860b-c0b23e53feed   1  232..237      6     6     0   1  Intel Arc framework compatibility
e013fb48-7998-4b9f-860b-c0b23e53feed   2  238..241      4     4     0   1  Multiple RTX 3060 GPUs
e013fb48-7998-4b9f-860b-c0b23e53feed   3  242..248      7     7     0   1  Model parallelism across RTX 3060s
e013fb48-7998-4b9f-860b-c0b23e53feed   4  249..276     28    28     0   1  Low-power 24GB NVIDIA GPU options
```

## Spot-Check Notes

1. `1ffd2141...` / LLM hosting options: Qwen 27B removed the 35B umbrella
   segment. The worst 35B row covered 3..254 with endpoint-only provenance;
   27B emitted contiguous, non-overlapping enumerated ranges. Segment count is
   comparable: 10 vs 9.
2. `43651f99...` / Response suggestions for Lexus: Qwen 27B did not reproduce
   the duplicate segment. It emitted two broad but clean segments: pre-date
   advice (0..22) and post-date debrief (23..64).
3. `3f732fbc...` / Smart Meter Data Tracking: Qwen 27B removed the partial
   umbrella. The prior 35B shape had seq 2 swallowing seqs 3 and 4; 27B split
   the device overview, Eagle-200 setup, product correction, EAGLE 3, and
   discount-code search without overlap.
4. `ce42c24a...` / Dust collector filter upgrade: Qwen 27B removed the partial
   umbrella while preserving or improving granularity. The 35B 59..112 segment
   swallowed sub-spans; 27B split that region into 59..81, 82..84, 85..92,
   93..98, and 99..112.
5. `e013fb48...` / PSU to CPU cable issue: Qwen 27B did not produce sibling
   overlap, but it under-segmented badly. The first 27B segment covers 0..231
   and 25,084 content characters, merging CPU power cable troubleshooting,
   cooler install, build-order discussion, short GPU cable recommendations,
   used-GPU shopping, and Intel Arc framework compatibility into one segment.
   This is cleaner structurally than the 35B umbrella-over-subsegments pattern,
   but it is not a good topic unit.

## Decision

Decision: `defer_to_tier2`.

Qwen 27B clearly does not reproduce the specific umbrella-over-subsegments
mechanism on this 5-parent slice:

- 0 overlapping sibling pairs
- 0 endpoint-only-big segments
- 0 heavy-expansion-big segments
- comparable or better granularity on 4 of 5 parents

However, the PSU/cable parent produced a 232-message mega-segment. That is a
quality failure in the opposite direction and was not covered by the original
run prompt's decision rubric. The evidence is strong enough to say the 35B
umbrella pattern is likely model-side, not merely prompt-shape, but not strong
enough to replace the 45 affected production parents with Qwen 27B output.

Recommended follow-up before any targeted 45-parent swap:

- Add an explicit under-fragmentation guard to the Tier 2 / targeted rerun
  rubric, for example `max_stored_27b <= max(100, 1.5 * max_stored_35b)` or a
  manually reviewed exception.
- Include these five parents in the Tier 2 Engram-proxy slice.
- Do not change `SEGMENTER_PROMPT_VERSION`, embed, activate, or cut over the
  27B generations from this run.

## Artifacts

```text
.scratch/ab_27b_test.py
.scratch/ab_27b_test.log
.scratch/ab_qwen27b_server.log
.scratch/ab_qwen27b_models.json
.scratch/ab_qwen27b_props.json
.scratch/ab_qwen27b_smoke_pre.json
.scratch/ab_qwen27b_smoke_post.json
.scratch/ab_qwen35b_models_restored.json
.scratch/ab_qwen35b_smoke_restored.json
.scratch/ab_query_a_generations.txt
.scratch/ab_query_b_shape.txt
.scratch/ab_query_c_overlap.txt
.scratch/ab_query_d_endpoint.txt
.scratch/ab_query_e_side_by_side.txt
.scratch/ab_27b_spot_detail.txt
```

## Commands And SQL Run

```bash
sed -n '1,220p' README.md
sed -n '1,260p' HUMAN_REQUIREMENTS.md
sed -n '261,520p' HUMAN_REQUIREMENTS.md
sed -n '521,900p' HUMAN_REQUIREMENTS.md
sed -n '1,260p' DECISION_LOG.md
sed -n '1,320p' BUILD_PHASES.md
sed -n '1,260p' ROADMAP.md
sed -n '1,340p' SPEC.md
sed -n '1,360p' docs/schema/README.md
sed -n '1,220p' AGENTS.md
git status --short
rg -n "def segment_conversation|class Segment|SEGMENTER_PROMPT_VERSION|find_existing_generation|status='segmented'|status = 'segmented'|segmenter_model_version|is_active|span_expansion|window_strategy|model_version" src/engram/segmenter.py
rg -n "CREATE TABLE segment_generations|CREATE TABLE segments|segment_generation_status|CONSTRAINT|CREATE TRIGGER|is_active|segmenter_model_version|window_strategy|message_ids|DELETE|status" migrations/004_segments_embeddings.sql
sed -n '1,220p' docs/reviews/v1/PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04.md
sed -n '221,520p' docs/reviews/v1/PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04.md
sed -n '1,260p' docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_RUN_2026_05_04.md
sed -n '480,780p' src/engram/segmenter.py
sed -n '780,1120p' src/engram/segmenter.py
sed -n '1360,1545p' src/engram/segmenter.py
sed -n '1,320p' migrations/004_segments_embeddings.sql
systemctl --user status ik-llama-server.service ik-llama-watchdog.timer openclaw-gateway.service --no-pager
systemctl --user cat ik-llama-server.service --no-pager
ls -l /home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf /home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf
ss -ltnp '( sport = :8081 )'
systemctl --user stop ik-llama-server.service ik-llama-watchdog.timer openclaw-gateway.service
mkdir -p .scratch
/home/halbritt/git/ik_llama.cpp/build/bin/llama-server --model /home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf --host 127.0.0.1 --port 8081 --gpu-layers 99 --ctx-size 49152 --flash-attn on --threads 8 --parallel 1 --batch-size 2048 --ubatch-size 256 --cache-type-k q8_0 --cache-type-v q8_0 --jinja 2>&1 | tee .scratch/ab_qwen27b_server.log
curl -s http://127.0.0.1:8081/v1/models | tee .scratch/ab_qwen27b_models.json | python3 -m json.tool
curl -s http://127.0.0.1:8081/props | tee .scratch/ab_qwen27b_props.json | python3 -m json.tool
curl -s http://127.0.0.1:8081/v1/chat/completions -H 'content-type: application/json' -d '{"model":"any","messages":[{"role":"user","content":"reply with {\"ok\":true}"}],"stream":false,"temperature":0,"max_tokens":32,"chat_template_kwargs":{"enable_thinking":false},"response_format":{"type":"json_schema","json_schema":{"name":"Smoke","strict":true,"schema":{"type":"object","required":["ok"],"properties":{"ok":{"type":"boolean"}},"additionalProperties":false}}}}' | tee .scratch/ab_qwen27b_smoke_pre.json | python3 -m json.tool
ENGRAM_DATABASE_URL="postgresql:///engram" .venv/bin/python .scratch/ab_27b_test.py 2>&1 | tee .scratch/ab_27b_test.log
curl -s http://127.0.0.1:8081/v1/chat/completions -H 'content-type: application/json' -d '{"model":"any","messages":[{"role":"user","content":"reply with {\"ok\":true}"}],"stream":false,"temperature":0,"max_tokens":32,"chat_template_kwargs":{"enable_thinking":false},"response_format":{"type":"json_schema","json_schema":{"name":"Smoke","strict":true,"schema":{"type":"object","required":["ok"],"properties":{"ok":{"type":"boolean"}},"additionalProperties":false}}}}' | tee .scratch/ab_qwen27b_smoke_post.json | python3 -m json.tool
systemctl --user start ik-llama-server.service ik-llama-watchdog.timer openclaw-gateway.service
curl -s http://127.0.0.1:8081/v1/models | tee .scratch/ab_qwen35b_models_restored.json | python3 -m json.tool
curl -s http://127.0.0.1:8081/v1/chat/completions -H 'content-type: application/json' -d '{"model":"any","messages":[{"role":"user","content":"reply with {\"ok\":true}"}],"stream":false,"temperature":0,"max_tokens":32,"chat_template_kwargs":{"enable_thinking":false},"response_format":{"type":"json_schema","json_schema":{"name":"Smoke","strict":true,"schema":{"type":"object","required":["ok"],"properties":{"ok":{"type":"boolean"}},"additionalProperties":false}}}}' | tee .scratch/ab_qwen35b_smoke_restored.json | python3 -m json.tool
systemctl --user is-active ik-llama-server.service ik-llama-watchdog.timer openclaw-gateway.service
```

```sql
-- Existing 27B generation check, before the run.
SELECT g.id::text, g.parent_id::text, g.status, count(s.id) AS segs
FROM segment_generations g
LEFT JOIN segments s ON s.generation_id = g.id
WHERE g.segmenter_prompt_version = 'segmenter.v2.d034.enum-ids.tool-placeholders'
  AND g.segmenter_model_version = '/home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf'
GROUP BY g.id, g.parent_id, g.status
ORDER BY g.parent_id;

-- Challenge parent existence and live titles.
SELECT id::text, title, source_kind,
       (SELECT count(*) FROM messages m WHERE m.conversation_id = c.id) AS messages
FROM conversations c
WHERE id IN (
  '1ffd2141-04fb-48d6-8c0e-dc06a593ab8e',
  '43651f99-93b0-4755-898b-41a4a71cfac9',
  '3f732fbc-5f7f-4570-962a-6d80fbf76259',
  'e013fb48-7998-4b9f-860b-c0b23e53feed',
  'ce42c24a-a687-4e9e-a5f8-eda384dcda3d'
)
ORDER BY id;

-- Active 35B generation check.
SELECT g.parent_id::text, g.status, g.segmenter_model_version, count(s.id) AS active_segments
FROM segment_generations g
JOIN segments s ON s.generation_id = g.id
WHERE g.status = 'active'
  AND g.parent_id IN (
    '1ffd2141-04fb-48d6-8c0e-dc06a593ab8e',
    '43651f99-93b0-4755-898b-41a4a71cfac9',
    '3f732fbc-5f7f-4570-962a-6d80fbf76259',
    'e013fb48-7998-4b9f-860b-c0b23e53feed',
    'ce42c24a-a687-4e9e-a5f8-eda384dcda3d'
  )
GROUP BY g.parent_id, g.status, g.segmenter_model_version
ORDER BY g.parent_id;

-- Query A: generations created.
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

-- Query B: 27B shape.
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

-- Query C: overlap check.
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

-- Query D: endpoint / heavy-expansion classification.
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

-- Query E: side-by-side 35B active vs 27B test generations.
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
