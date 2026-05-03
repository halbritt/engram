# Fix Benchmark Segmentation Harness Review Findings

> Hand this to a coding agent on the
> `build-benchmark-segmentation-harness` branch.
>
> Goal: fix the accepted findings from the benchmark harness implementation
> review, with priority on the two major correctness defects that block
> decision-grade SuperDialseg runs.

## Read First

1. `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_IMPLEMENTATION_REVIEW.md`
2. `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_IMPLEMENTATION_SYNTHESIS_2026_05_03.md`
3. `prompts/build_benchmark_segmentation_harness.md`
4. `docs/rfcs/0006-segmentation-model-benchmark.md`
5. `DECISION_LOG.md`, especially D041.
6. `benchmarks/segmentation/README.md`
7. `benchmarks/segmentation/SPEC.md`
8. `tests/test_benchmark_segmentation.py`

Read `docs/segmentation.md` and `src/engram/segmenter.py` only if needed to
confirm production estimator or placeholder semantics. Do not refactor Phase 2
runtime code.

## Hard Constraints

- Do not call ik-llama, Ollama, Hugging Face, or any external service.
- Do not download public datasets.
- Do not write to the production database.
- Do not alter production migrations or Phase 2 runtime code.
- Do not use the private Engram corpus as a fallback benchmark substrate.
- Keep all benchmark outputs scratch-only.

## Required Fixes

Implement all accepted findings from the synthesis unless a fix becomes
obviously wrong during implementation. If you defer any item, explain why in
the final summary.

### 1. No-Boundary F1 Correctness - Major

File: `benchmarks/segmentation/scoring.py`

Fix strict and window-tolerant boundary scoring so a perfect no-boundary parent
scores as perfect agreement:

```python
boundary_precision_recall_f1(set(), set())["f1"] == 1.0
window_tolerant_boundary_f1(set(), set(), tolerance=1)["f1"] == 1.0
```

Expected behavior:

- expected empty, predicted empty -> precision/recall/F1 all `1.0`.
- expected empty, predicted non-empty -> precision/recall/F1 reflect false
  positives, not perfect.
- expected non-empty, predicted empty -> recall/F1 fail as before.
- P_k and WindowDiff behavior should not regress.

Add unit tests for these cases.

### 2. SuperDialseg Boundary Derivation - Major

File: `benchmarks/segmentation/datasets.py`

Fix SuperDialseg adapter boundary derivation:

- Prefer `segmentation_label` when any usable segmentation labels are present.
- Interpret `segmentation_label=1` as "the boundary is after this turn", so add
  `sequence_index + 1`, not `sequence_index`.
- Do not add a boundary after the final turn.
- Use `topic_id` change only as a fallback when segmentation labels are absent
  from the parent.
- Keep boundary positions as positions between message sequence indexes.

Add a unit test where:

- turn N has `segmentation_label=1` and `topic_id=A`;
- turn N+1 has `segmentation_label=0` and `topic_id=B`;
- expected boundaries contain exactly `N+1`, not both `N` and `N+1`.

Update `benchmarks/segmentation/SPEC.md` to document the chosen rule.

### 3. Deterministic Schema Validity Metric - Minor

File: `benchmarks/segmentation/scoring.py`

For deterministic constructed outputs, make `schema_valid_rate` report
`"not_applicable"` or otherwise clearly distinguish it from LLM JSON/schema
validity. Keep `provenance_valid_rate` meaningful because deterministic
strategies can still cite bad ids.

Add/adjust tests so this behavior is pinned.

### 4. Benchmark Token Estimator Calibration - Minor

File: `benchmarks/segmentation/strategies.py`

Align the benchmark estimator with production's default conservative estimate:
`ceil(chars / 2.5)`, matching `ENGRAM_SEGMENTER_CONTEXT_GUARD_CHARS_PER_TOKEN`
default. Bump the estimator version string.

Update docs if they mention token-estimator units.

### 5. Model SHA256 Policy Wording - Minor

File: `benchmarks/segmentation/results.py` or docs.

Do not imply that a model SHA256 sidecar manifest is implemented if it is not.
Reword the `model_sha256_manifest_policy` field to state that model SHA256
capture is deferred until local-model strategies exist, with the planned
sidecar policy described as future work.

### 6. Dataset Source Validation - Minor

File: `benchmarks/segmentation/datasets.py`

Replace permissive substring matching with exact allowed values or explicit
allowed prefixes. A value like `local:superdialseg-personal-fork` should not
pass just because it contains `local:superdialseg`.

Add/adjust tests.

### 7. Empty Environment Capture - Nit

File: `benchmarks/segmentation/results.py`

Make an empty `ENGRAM_SEGMENTER_*` environment capture explicit, for example:

```json
{"_note": "no ENGRAM_SEGMENTER_* env vars set"}
```

or add a captured-at timestamp plus an empty dict. Prefer the note for
readability.

### 8. `--allow-local-models` Help Text - Nit

File: `benchmarks/segmentation/run_benchmark.py`

Clarify that even when the flag is passed, this implementation still raises
`NotImplementedError` for LLM strategies before any model/network call.

## Validation Commands

Run:

```bash
python3 -m py_compile benchmarks/segmentation/*.py
python3 -m benchmarks.segmentation.run_benchmark --help
python3 -m benchmarks.segmentation.run_benchmark list-strategies
.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -v
.venv/bin/python -m pytest -q
```

If `.venv` is unavailable, use `python3 -m pytest` for the benchmark-specific
tests and say what could not be run. Do not start model services.

Also run a local end-to-end command against the hand-authored SuperDialseg shape
sample if the tests do not already cover it. Do not use real public dataset
snapshots unless they already exist locally and require no network access.

## Deliverable Summary

At the end, summarize:

- Files changed.
- Which review findings were resolved.
- Exact validation commands and results.
- Any residual risk before a real SuperDialseg snapshot run.

No `DECISION_LOG.md` update is expected unless you discover a new architecture
decision.
