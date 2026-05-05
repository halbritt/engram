# Benchmark Segmentation Harness Review Synthesis

Date: 2026-05-03
Scope: `benchmarks/segmentation/` skeleton
Inputs:
- `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_REVIEW.md`
- `prompts/P011_benchmark_segmentation_harness_spec.md`
- `docs/rfcs/0006-segmentation-model-benchmark.md`

## Executive Decision

**Proceed with the skeleton after small spec/CLI clarifications.**

The review found no blockers and no production-boundary violations. The
benchmark skeleton preserves the local-only constraint, does not touch
production migrations/runtime code, keeps benchmark artifacts scratch-only, and
does not smuggle P-FRAG values into the deployed Phase 2 `whole` / `windowed`
contract.

The findings are all minor or nit-level. They should be resolved before a live
runner lands because they affect reproducibility, scorer consistency, and CLI
clarity. None require `DECISION_LOG.md` updates because they do not change
Engram architecture or accepted project decisions.

## Synthesis Matrix

| Finding | Severity | Disposition | Target | Rationale |
|---------|----------|-------------|--------|-----------|
| 1. `--offline` is a permanent no-op | minor | accept | `run_benchmark.py`, `SPEC.md` | The flag currently carries no information because it defaults true and can only set true. Offline should either be implicit or replaced by a future explicit opt-in flag such as `--allow-local-models`. |
| 2. Fixture spec does not distinguish embeddable vs provenance-only ids | minor | accept | `SPEC.md`, fixtures | Production keeps placeholder/tool/null message ids for provenance while excluding bodies from embeddable text. The benchmark schema must make that rule explicit for scoring. |
| 3. `match_aliases` normalization undefined | minor | accept | `SPEC.md`, `scoring.py` later | Claim precision/recall is not reproducible unless text normalization is pinned. Use NFKC, `casefold()`, whitespace collapse, and no punctuation stripping unless later review changes it. |
| 4. Model SHA256 capture policy absent | minor | accept | `SPEC.md` | The SHA256 field is required, but hashing large GGUF files every run is expensive. The spec should require a scratch sidecar manifest keyed by absolute path, mtime, and size. |
| 5. `schema_version` bump policy unspecified | minor | accept | `SPEC.md` | Fixture/result schema labels need compatibility meaning. Breaking JSON shape changes bump schema version; backward-compatible additions do not. |
| 6. Missing `__init__.py` may surprise tooling | nit | accept | `benchmarks/__init__.py`, `benchmarks/segmentation/__init__.py` | PEP 420 works today, but explicit packages reduce tooling variance for pytest, mypy, docs, and future imports. |
| 7. `StrategyKind` overlaps with deferred P-FRAG vocabulary | nit | accept | `strategies.py`, `SPEC.md` | Internal benchmark classifiers must be clearly distinct from production `segments.window_strategy` and from deferred P-FRAG schema names. |
| 8. Backend error taxonomy implicit | nit | accept | `SPEC.md` | "Grouped by class" needs a starter taxonomy so runs bucket endpoint/backend failures consistently. |

## Accepted Patch List

Apply these before implementing the live runner:

1. Remove `--offline` from the CLI skeleton, or replace it with a future opt-in
   flag that defaults false. The spec should match the chosen shape.
2. Add `embeddable_message_ids` or an explicit scorer derivation rule for
   provenance-only placeholder/tool/null/image messages. The invariant should
   be `message_ids` contains `embeddable_message_ids`.
3. Pin claim matching normalization: Unicode NFKC, `casefold()`, collapse
   whitespace runs, and preserve punctuation.
4. Add model SHA256 manifest policy for large local model files.
5. Add schema version discipline for fixture, expected-claims, and result JSON.
6. Add package marker files or document intentional namespace packages.
7. Clarify that `StrategyKind` is benchmark-internal and not a production
   `window_strategy`.
8. Add initial backend error classes: `connect_refused`, `read_timeout`,
   `http_5xx`, `grammar_stack_empty`, `cuda_oom`, `backend_wedge_post_smoke`,
   and `unknown`.

## Non-Blocking Confirmations

- The skeleton imports no `engram.*` modules and has no network, model, or
  production database side effects.
- Required RFC 0006 metrics are represented in `SPEC.md`, including valid
  JSON/schema/provenance rates, sub-floor fragment counts at 50/100/200,
  strict boundary precision/recall, W-F1, P_k, WindowDiff, and benchmark-only
  claim precision/recall.
- The required strategy set is represented: current Qwen, candidate Qwen,
  optional Gemma, fixed N-token windows with overlap, and message-group
  segmentation.
- Fixture examples are intentionally small and review-shaped, not a real
  benchmark set.
- Public dataset handling rules are strong enough for the skeleton stage:
  local-only, no redistribution, no production-corpus mixing, and snapshot
  metadata required.

## Decision Log Impact

Original review impact: no `DECISION_LOG.md` update was needed because the
review confirmed existing decisions D005, D034, D037, D038, and D039 rather
than changing them.

Later update: D041 supersedes the skeleton's dataset-order assumption. The
benchmark now starts with public datasets for portability: SuperDialseg first
for labeled quality, LMSYS-Chat-1M for optional operational stress, and
synthetic fixtures as regression traps.

## Verdict

**Pass with changes.** The benchmark skeleton is architecturally safe and
reviewable. The accepted changes are specification and CLI hygiene that should
land before any live runner work begins.
