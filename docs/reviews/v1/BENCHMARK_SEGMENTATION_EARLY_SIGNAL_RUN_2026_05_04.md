# Segmentation Early-Signal Benchmark Run - 2026-05-04

## Scope

This run executed the RFC 0008 / D042 Tier 1 early-signal segmentation
benchmark. It used the local public SuperDialseg validation snapshot plus the
committed synthetic Engram-proxy fixtures. It did not use the private Engram
corpus, did not write the production database, did not alter production
migrations, and does not justify a production model switch by itself.

Thresholds were the committed non-normative example threshold set:
`benchmarks/segmentation/fixtures/early_signal_thresholds.example.json`
(`threshold_set_id=example-non-normative`).

## Repository State

| Field | Value |
| --- | --- |
| Branch | `master` |
| Commit | `56c7237f2f5cbf210c06fb73d9b6c574941b53b9` |
| Scratch root | `.scratch/benchmarks/segmentation/early-signal-20260504T073337Z` |
| Sample plan | `.scratch/benchmarks/segmentation/early-signal-20260504T073337Z/sample-plans/superdialseg-tier1.json` |

## Dataset

| Field | Value |
| --- | --- |
| Manifest | `.scratch/benchmarks/datasets/superdialseg/manifest.json` |
| Dataset | `superdialseg` |
| Source | `huggingface:Coldog2333/super_dialseg` |
| Version | `3adf26a8241078ddd5f8731f778c1e76ca851d2b` |
| Revision | `8bdc3870d3f6efcef380460d282b488a3681745a4b166fe4a5c9dd9f2c0b1e17` |
| Split | `validation` |
| Selected public parents | `80` |
| Synthetic fixture parents | `10` |
| Total scored parents | `90` |

Sample plan shortfalls: `short_dialogue=10`; all other Tier 1 strata met their
target. The selected ids were not the first 80 validation parents.

## Models And Server Handling

| Strategy | Model path | Size bytes | SHA256 |
| --- | --- | ---: | --- |
| `qwen_35b_a3b_iq4_xs_d034` | `~/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` | `18806446400` | not computed |
| `qwen_27b_q5_k_m_d034` | `~/models/Qwen3.6-27B-Q5_K_M.gguf` | `19509790944` | not computed |
| `gemma_26b_a4b_q4_k_m_d034` | `~/models/gemma-4-26B-A4B-it-GGUF/gemma-4-26B-A4B-it-Q4_K_M.gguf` | `16796015136` | not computed |

The existing `ik-llama-server.service` was active on Qwen 35B at the start and
was used for the operational-model run. It was then stopped so Qwen 27B and
Gemma could be launched manually on `127.0.0.1:8081`, one at a time. After the
benchmark, the normal Qwen 35B service was restored and smoke-tested.

Pre-run and post-run checks passed for each local model:

- `GET /v1/models`
- `GET /props`
- tiny D034-style JSON-schema completion

Manual server logs:

- `.scratch/benchmarks/segmentation/early-signal-20260504T073337Z/model-server/qwen_27b_q5_k_m_d034.log`
- `.scratch/benchmarks/segmentation/early-signal-20260504T073337Z/model-server/gemma_26b_a4b_q4_k_m_d034.log`

## Artifacts

| Strategy set | `run.json` |
| --- | --- |
| Deterministic baselines | `.scratch/benchmarks/segmentation/early-signal-20260504T073337Z/results/deterministic/20260504T073400Z.superdialseg.fc323de0/run.json` |
| Qwen 35B | `.scratch/benchmarks/segmentation/early-signal-20260504T073337Z/results/qwen_35b_a3b_iq4_xs_d034/20260504T074344Z.superdialseg.f740c203/run.json` |
| Qwen 27B | `.scratch/benchmarks/segmentation/early-signal-20260504T073337Z/results/qwen_27b_q5_k_m_d034/20260504T082125Z.superdialseg.d93aed2e/run.json` |
| Gemma 26B | `.scratch/benchmarks/segmentation/early-signal-20260504T073337Z/results/gemma_26b_a4b_q4_k_m_d034/20260504T083212Z.superdialseg.0174efcf/run.json` |

Each run directory also contains `score.json`, `report.md`, and `report.html`.

## Metrics

| Strategy | Schema valid | Provenance valid | Segments | Parent/s | Strict F1 | W-F1 +/-1 | W-F1 +/-2 | Pk | WindowDiff | Seg/expected | No-boundary FS | <100 frag | Adj tiny | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `fixed_token_windows` | n/a | `1.000` | `253` | `12933.352` | `0.185` | `0.477` | `0.539` | `0.467` | `0.467` | `0.969` | `0.632` | `0.166` | `0.000` | `defer` |
| `message_groups` | n/a | `1.000` | `253` | `12921.407` | `0.193` | `0.477` | `0.539` | `0.462` | `0.462` | `0.969` | `0.632` | `0.166` | `0.000` | `defer` |
| `qwen_35b_a3b_iq4_xs_d034` | `1.000` | `0.956` | `226` | `0.170` | `0.447` | `0.466` | `0.508` | `0.327` | `0.331` | `0.952` | `0.526` | `0.358` | `0.235` | `reject` |
| `qwen_27b_q5_k_m_d034` | `1.000` | `1.000` | `266` | `0.041` | `0.628` | `0.628` | `0.661` | `0.238` | `0.243` | `0.981` | `0.316` | `0.395` | `0.216` | `longer_run` |
| `gemma_26b_a4b_q4_k_m_d034` | `1.000` | `1.000` | `345` | `0.155` | `0.640` | `0.662` | `0.718` | `0.301` | `0.308` | `1.437` | `0.632` | `0.519` | `0.322` | `longer_run` |

Notes:

- `qwen_35b_a3b_iq4_xs_d034` failed the hard provenance gate with five
  unordered-message-id failures, producing the per-run `reject` verdict.
- `qwen_27b_q5_k_m_d034` had the best Pk and WindowDiff, perfect schema and
  provenance validity, and much better boundary F1 than the operational model,
  but it was very slow and still exceeded the non-normative no-boundary
  false-split threshold.
- `gemma_26b_a4b_q4_k_m_d034` had the strongest raw boundary F1 and good
  throughput, but fragmented much more aggressively: 345 segments, 1.437
  predicted/expected segment ratio, and 14 parents above 2x expected segment
  count.
- Per-run challenger verdicts are `longer_run` partly because the current
  harness scores one `run.json` at a time. The comparison anchors were run in
  separate directories as required to isolate model-server state.

## Interpretation

Tier 1 is not decision-grade. No production model-selection change should be
made from this run.

The useful early signal is:

- reject the current Qwen 35B benchmark output for this run shape because it
  failed provenance validity;
- keep Qwen 27B as the best balanced Tier 2 candidate despite its throughput
  cost;
- keep Gemma in a Tier 2 comparison only if over-fragmentation is explicitly
  treated as the risk under test;
- do not treat raw SuperDialseg boundary F1 alone as sufficient evidence.

Next action: schedule a Tier 2 decision run for Qwen 27B against the current
operational profile, with Gemma included as an over-fragmentation challenger
if compute budget allows. Do not change production Phase 2 behavior before
Tier 2.

## Validation

Completed before and after the benchmark as applicable:

```text
python3 -m benchmarks.segmentation.run_benchmark validate-dataset --manifest .scratch/benchmarks/datasets/superdialseg/manifest.json --split validation
python3 -m benchmarks.segmentation.run_benchmark validate-fixtures --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl
python3 -m py_compile benchmarks/segmentation/*.py
.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -q
python3 -m benchmarks.segmentation.run_benchmark score --results <each run.json>
python3 -m benchmarks.segmentation.run_benchmark report --results <each run.json> --format both --max-parents 25
```

All local-model pre-run and post-run smoke checks passed. The normal Qwen 35B
service was restored and smoke-tested after the manual model runs.
