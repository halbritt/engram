# Benchmark Segmentation Early-Signal Implementation Review Synthesis

Date: 2026-05-04
Scope: RFC 0008 / D042 Tier 0 + Tier 1 benchmark implementation
Input:
- `docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_IMPLEMENTATION_REVIEW_2026_05_04.md`

## Executive Decision

Accept the review. The implementation delivered the intended Tier 0 / Tier 1
benchmark support, but several run-shape and verdict-routing issues needed to
be fixed before the harness should be treated as merge-ready.

No architecture decision changed. The accepted deltas are benchmark-local and
do not alter production Phase 2 segmenter behavior, migrations, or database
state.

## Synthesis Matrix

| Finding | Disposition | Applied Delta |
| --- | --- | --- |
| 1. Smoke sample-plan crash | accept | Fixed smoke shortfall calculation to use the active target keys, and added smoke sample-plan helper + CLI regression coverage. |
| 2. Deterministic baselines get `longer_run` without thresholds | accept | Deterministic strategies now always return `defer` as comparison anchors, independent of threshold-set availability. |
| 3. Missing deterministic baseline silently yields `defer` | accept | Missing deterministic baselines now surface a hard warning and route challengers to `longer_run`. |
| 4. Sample-plan revision not enforced | accept | Run-time validation now rejects revision mismatch when both plan and manifest revisions are set. Docs clarify that `dataset.revision` records manifest `local_path_sha256` when available. |
| 5. Tier 1 without sample-plan skips stratification | accept | `run --benchmark-tier early_signal` now requires `--sample-plan`. |
| 6. Operational model constant has no override | accept | Added `--operational-model-strategy`, persisted it in result artifacts, and included it in verdict objects/reports. |
| 7. Revision field docs/enforcement | accept | Covered by finding 4 doc and validation changes. |
| 8. Report `not_applicable` formatting | accept | Report metric formatting now renders `not_applicable` consistently as `n/a`. |

## Validation

Regression coverage was added in `tests/test_benchmark_segmentation.py` for
the accepted findings.

Validation commands run after the patch:

```text
python3 -m py_compile benchmarks/segmentation/*.py
.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -q
.venv/bin/python -m pytest -q
python3 -m benchmarks.segmentation.run_benchmark list-strategies
python3 -m benchmarks.segmentation.run_benchmark validate-fixtures --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl
```
