# Benchmark Segmentation Early-Signal Spec Review Synthesis

Date: 2026-05-04
Scope: RFC 0008 / D042 early-signal benchmark specification
Input:
- `docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_SPEC_REVIEW_2026_05_04.md`

## Executive Decision

Accept the review. The early-signal specification is directionally correct,
but it needed clearer separation between implemented harness behavior and
planned RFC 0008 / D042 behavior before implementation starts.

No architecture decision changed. The synthesis clarifies status,
reproducibility, and schema shape so the next implementation pass does not
infer missing details.

## Synthesis Matrix

| Finding | Disposition | Applied Delta |
| --- | --- | --- |
| 1. SPEC.md mixes implemented and planned behavior | accept | Added planned-status markers, qualified the Principles tier/run-field language, and split current vs planned `run.json` / report fields. |
| 2. Verdict thresholds are "configured" without a configuration locus | accept | Added threshold-set requirements and explicitly tied unset defaults to RFC 0008 Open Question 1. |
| 3. `metric_reasons` is stringly typed | accept | Changed the verdict example to include `schema_version`, object-shaped `metric_reasons`, and a recorded `threshold_set`. |
| 4. Tier 1 undersized-stratum behavior is unspecified | accept | Added the shortfall rule: take all available, record actual stratum sizes and shortfalls, and fail only if the total falls below 60. |
| 5. D042 revisit trigger waits on Phase 3 | accept | Added a near-term revisit hook for the first Tier 1 run if verdict gates produce no useful separation. |
| 6. RFC 0006 status remains `proposal` | accept | Marked RFC 0006 `specified`, updated the RFC index, and added a promotion/refinement breadcrumb. |
| 7. README.md cites only RFC 0006 | accept | Added RFC 0008 / D042 cross-references in the opening and tier section. |

## Source Artifact Updates

- `benchmarks/segmentation/SPEC.md`
- `benchmarks/segmentation/README.md`
- `DECISION_LOG.md`
- `docs/rfcs/0006-segmentation-model-benchmark.md`
- `docs/rfcs/README.md`

The review artifact remains unchanged as provenance.

## Implementation Notes For The Next Pass

- Existing scratch `run.json` artifacts are not backfilled.
- Tier 1 implementation must emit the threshold set into result artifacts, not
  only apply thresholds internally.
- Early-signal verdict consumers should treat `metric_reasons` as structured
  JSON, not parse `key=value` strings.
- Tier 1 sample-plan validation must expose actual stratum sizes and any
  shortfalls.

## Validation

Documentation-only synthesis. Ran:

```text
git diff --check
```
