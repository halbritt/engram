# Benchmark Segmentation Harness Implementation Review Synthesis

Date: 2026-05-03
Scope: public-first benchmark harness implementation
Inputs:
- `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_IMPLEMENTATION_REVIEW.md`
- `prompts/build_benchmark_segmentation_harness.md`
- `docs/rfcs/0006-segmentation-model-benchmark.md`
- `DECISION_LOG.md` D041

## Executive Decision

**Proceed after fixing two major scoring/data-adapter defects.**

The implementation respects the important architecture boundaries: no
production database writes, no model/network calls, no private-corpus fallback,
and no Phase 2 runtime/migration changes. The review validated the local-only
posture and the public-first D041 direction.

However, the harness is not yet ready for decision-grade SuperDialseg runs.
Two major issues would corrupt the primary quality metrics:

- perfect no-boundary parents score strict/W-F1 as 0.0 instead of 1.0;
- SuperDialseg boundaries are derived with an off-by-one/double-counting rule
  when `segmentation_label` and `topic_id` both appear.

These are local fixes in `scoring.py` and `datasets.py`; no architectural
decision changes are needed.

## Synthesis Matrix

| Finding | Severity | Disposition | Required Before Public Run | Target |
|---------|----------|-------------|----------------------------|--------|
| 1. Strict/W-F1 return 0.0 for correct no-boundary parents | major | accept | yes | `benchmarks/segmentation/scoring.py`, tests |
| 2. SuperDialseg adapter double-counts/off-by-one boundaries | major | accept | yes | `benchmarks/segmentation/datasets.py`, tests, `SPEC.md` |
| 3. `schema_valid_rate` always 100% for deterministic strategies | minor | accept | no | `scoring.py` |
| 4. Benchmark token estimator diverges from production | minor | accept-with-modification | no | `strategies.py` or `SPEC.md` |
| 5. Model SHA256 policy describes unimplemented sidecar | minor | accept | no | `results.py` or docs |
| 6. Dataset source validation uses permissive substring matching | minor | accept | no | `datasets.py` |
| 7. Empty `ENGRAM_SEGMENTER_*` environment capture is ambiguous | nit | accept | no | `results.py` |
| 8. `--allow-local-models` help understates fail-closed behavior | nit | accept | no | `run_benchmark.py` |

## Required Patch List

1. In strict and window-tolerant boundary F1, return perfect agreement
   (`precision=recall=f1=1.0`) when both expected and predicted boundary sets
   are empty. Add a unit test for `boundary_precision_recall_f1(set(), set())`.
2. Fix SuperDialseg boundary derivation. Prefer `segmentation_label` as the
   primary paper-faithful signal and place the boundary after the labeled turn
   (`sequence_index + 1`) with a final-turn guard. Use `topic_id` only as a
   fallback when segmentation labels are absent. Add a disagreement test where
   `segmentation_label` and `topic_id` would otherwise produce two boundaries.
3. Mark deterministic `schema_valid_rate` as `not_applicable` or otherwise make
   clear that constructed deterministic outputs are not exercising JSON schema
   validity.
4. Align the benchmark token estimator with production `chars / 2.5`, or
   explicitly document that sub-floor counts are benchmark-token units. The
   cleaner fix is estimator alignment plus a version bump.
5. Reword `model_sha256_manifest_policy` to say sidecar capture is deferred
   until local-model strategies are implemented, or add a real sidecar helper.
6. Tighten dataset source validation to exact allowed values or explicit
   allowed prefixes.
7. Make empty `ENGRAM_SEGMENTER_*` environment capture explicit with a note or
   captured-at timestamp.
8. Update `--allow-local-models` help to say LLM strategies still raise
   `NotImplementedError` in this implementation.

## Confirmed Good

- No `engram.*` imports, network calls, model calls, or production DB access.
- Public-first D041 posture is implemented: SuperDialseg quality target,
  LMSYS stress-only target, synthetic fixtures as regression traps.
- LMSYS license acceptance gating works.
- Result files can be re-scored from `parents.jsonl`.
- Tests are offline and passed in review: benchmark-specific 12/12, full
  `.venv` pytest 26 passed / 38 skipped for DB-dependent tests.

## Decision Log Impact

No `DECISION_LOG.md` update is needed. The review found implementation defects
within D041, not a change to the public-first benchmark decision.

## Verdict

**Pass with changes.** Fix findings 1 and 2 before any decision-grade
SuperDialseg run. The minor/nit cleanup can land in the same patch or shortly
after.
