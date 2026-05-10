author: codex

# RFC 0028 100-Segment Re-Extraction Bench

Date: 2026-05-09
RFC refs: RFC-0028
Decision refs: D082

## Summary

Ran the RFC 0028 bounded extraction bench over a balanced 100-segment active
slice using the local-only extraction benchmark harness. This benchmark uses
the production extractor prompt and parser with
`extractor.v9.d082.predicate-intent`, but writes only scratch artifacts; it
does not insert `claim_extractions`, `claims`, or `beliefs` rows.

Result: the 100-segment run completed with zero segment failures,
100% schema-valid segment outputs, and 100% provenance-clean segment outputs.

## Commands

```text
ENGRAM_DATABASE_URL=postgresql:///engram .venv/bin/python -m benchmarks.extraction.run_benchmark sample-slice --target-size 100 --seed 19 --output .scratch/benchmarks/extraction-backend/slices/rfc0028-predicate-intent-seed19-100.json
```

```text
.venv/bin/python -m benchmarks.extraction.run_benchmark smoke --allow-local-models --base-url http://127.0.0.1:8081 --context-window 49152
```

```text
ENGRAM_DATABASE_URL=postgresql:///engram .venv/bin/python -m benchmarks.extraction.run_benchmark run --allow-local-models --slice .scratch/benchmarks/extraction-backend/slices/rfc0028-predicate-intent-seed19-100.json --backend-name rfc0028-predicate-intent-100 --base-url http://127.0.0.1:8081 --context-window 49152 --concurrency 1 --output-dir .scratch/benchmarks/extraction-backend
```

## Scratch Artifacts

```text
.scratch/benchmarks/extraction-backend/slices/rfc0028-predicate-intent-seed19-100.json
.scratch/benchmarks/extraction-backend/20260509T045641Z.rfc0028-predicate-intent-100.d01f44fd/run.json
.scratch/benchmarks/extraction-backend/20260509T045641Z.rfc0028-predicate-intent-100.d01f44fd/segments.jsonl
```

`segments.jsonl` was written with the default redaction policy:
`segments_jsonl_contains_claim_text=false`.

## Environment

| Field | Value |
| --- | --- |
| endpoint | `http://127.0.0.1:8081/v1/chat/completions` |
| model | `/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` |
| context window | 49152 |
| max tokens | 8192 |
| retries | 1 |
| concurrency | 1 |
| chat template kwargs | `{"enable_thinking": false}` |

## Slice

| Field | Value |
| --- | --- |
| target size | 100 |
| actual size | 100 |
| seed | 19 |
| source kinds | all |
| stratification | `source_kind_x_size_bucket` |

Bucket counts:

| Bucket | Segments |
| --- | ---: |
| `chatgpt:long` | 12 |
| `chatgpt:medium` | 11 |
| `chatgpt:short` | 11 |
| `claude:long` | 11 |
| `claude:medium` | 11 |
| `claude:short` | 11 |
| `gemini:long` | 11 |
| `gemini:medium` | 11 |
| `gemini:short` | 11 |

## Aggregate Metrics

| Metric | Value |
| --- | ---: |
| segments total | 100 |
| segments completed | 100 |
| segments failed | 0 |
| segment completion rate | 1.0 |
| schema-valid rate | 1.0 |
| provenance-clean segment rate | 1.0 |
| claim count | 475 |
| dropped claim count | 84 |
| dropped claim rate | 0.1503 |
| wall clock seconds | 1331.50 |
| throughput segments/sec | 0.0751 |
| throughput claims/sec | 0.3567 |
| prompt tokens | 567,393 |
| completion tokens | 87,333 |
| total tokens | 654,726 |

Latency:

| Metric | Seconds |
| --- | ---: |
| min | 0.61 |
| p50 | 3.82 |
| mean | 13.31 |
| p95 | 78.89 |
| max | 182.81 |

Dropped claims were all local trigger violations:

| Drop reason | Count |
| --- | ---: |
| `trigger_violation` | 84 |

## Predicate Distribution

| Predicate | Count |
| --- | ---: |
| `uses_tool` | 149 |
| `has_name` | 55 |
| `wants_to` | 33 |
| `believes` | 31 |
| `feels` | 26 |
| `owns_repo` | 24 |
| `is_related_to` | 20 |
| `lives_at` | 16 |
| `plans_to` | 14 |
| `prefers` | 14 |
| `works_with` | 12 |
| `must_do` | 11 |
| `project_status_is` | 11 |
| `talked_about` | 11 |
| other predicates | 59 |

## Prior Prompt Comparison

For the same 100 segment IDs, existing DB claims under the prior live prompt
version `extractor.v8.d064.accounted-zero` totaled 600. The RFC 0028 bench
produced 475 claims over the same slice, a delta of -125 claims.

| Metric | Value |
| --- | ---: |
| prior prompt claim count | 600 |
| RFC 0028 bench claim count | 475 |
| delta | -125 |
| prior segments with claims | 62 |
| RFC 0028 segments with claims | 51 |
| prior-positive / RFC0028-zero segments | 11 |
| prior-zero / RFC0028-positive segments | 0 |

Bucket-level comparison:

| Bucket | Prior claims | RFC 0028 claims | Delta |
| --- | ---: | ---: | ---: |
| `chatgpt:long` | 65 | 66 | +1 |
| `chatgpt:medium` | 18 | 12 | -6 |
| `chatgpt:short` | 15 | 7 | -8 |
| `claude:long` | 204 | 187 | -17 |
| `claude:medium` | 81 | 50 | -31 |
| `claude:short` | 32 | 21 | -11 |
| `gemini:long` | 92 | 80 | -12 |
| `gemini:medium` | 37 | 32 | -5 |
| `gemini:short` | 56 | 20 | -36 |

## Notes And Limitations

This was a non-mutating benchmark harness run, not a production
`engram re-extract` write into `claim_extractions` / `claims`.

The run intentionally used the default redacted artifact policy. Because claim
text, object text, and rationales were not written to `segments.jsonl`, this
report does not include a manual subject-kind mismatch spot check. Running a
local-only spot check would require either a separate small
`--include-claim-text` scratch run or direct interactive review of model
outputs; do not commit those raw artifacts.

The aggregate signal is favorable for the promotion gate on stability and
schema safety: zero failed segments, no schema-invalid segment outputs, and no
provenance failures. The material claim-count reduction versus
`extractor.v8.d064.accounted-zero` should be reviewed before full-corpus
re-extraction, especially the 11 segments that had prior claims and produced
zero claims under the RFC 0028 prompt.
