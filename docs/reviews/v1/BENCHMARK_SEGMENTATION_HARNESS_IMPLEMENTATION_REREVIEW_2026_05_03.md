# Benchmark Segmentation Harness Implementation Re-Review

Date: 2026-05-03T21:30:00Z
Reviewer: Codex
Branch: build-benchmark-segmentation-harness
Reviewed commit: `f6215b0` plus prior review artifacts through `5aeb589`
Base: `origin/master` at `85f3fda`

## Findings

No blocking, major, minor, or nit findings in this re-review.

The two previous major findings are resolved:

- `benchmarks/segmentation/scoring.py`: strict and window-tolerant boundary F1
  now return perfect agreement for no-boundary expected/predicted parents.
- `benchmarks/segmentation/datasets.py`: SuperDialseg boundary derivation now
  treats `segmentation_label=1` as a boundary after the labeled turn, avoids a
  final-turn boundary, and uses `topic_id` only when usable segmentation labels
  are absent.

The prior minor/nit findings are also addressed:

- deterministic `schema_valid_rate` reports `not_applicable`;
- benchmark token estimator is aligned to `chars / 2.5` and versioned as v2;
- model SHA256 sidecar wording is explicitly deferred;
- dataset source validation is exact rather than substring-based;
- empty `ENGRAM_SEGMENTER_*` capture is explicit;
- `--allow-local-models` help now states that LLM strategies still raise before
  any model/network call.

## Non-Blocking Notes

- The harness remains isolated from production code paths: no `engram.*`
  imports, no production migrations, no production database access, and no
  model/network calls in the reviewed code path.
- The public-first D041 posture is intact: SuperDialseg remains the quality
  target, LMSYS remains stress-only without labels, and synthetic fixtures are
  regression/shape data.
- I did not validate against a real SuperDialseg snapshot because no local
  snapshot was present and the task forbids downloads. The hand-authored
  SuperDialseg-shaped sample exercised the adapter, scoring, result, score, and
  report paths.

## Validation

Commands run:

```bash
python3 -m py_compile benchmarks/segmentation/*.py
python3 -m benchmarks.segmentation.run_benchmark --help
python3 -m benchmarks.segmentation.run_benchmark list-strategies
.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -v
.venv/bin/python -m pytest -q
```

Results:

- `py_compile`: passed.
- CLI help: passed; commands include `validate-dataset`, `validate-fixtures`,
  `list-strategies`, `run`, `score`, and `report`.
- `list-strategies`: passed; emitted current Qwen, candidate Qwen, Gemma,
  fixed windows, and message groups.
- benchmark-specific tests: 15 passed.
- full `.venv` pytest suite: 29 passed, 38 skipped.

Additional offline end-to-end check:

- created a temporary manifest pointing at
  `benchmarks/segmentation/fixtures/superdialseg_shape.synthetic.jsonl`;
- `validate-dataset` passed with 2 parents;
- `run` wrote `run.json` / `parents.jsonl` for `fixed_token_windows` and
  `message_groups`;
- `score` wrote `score.json`;
- `report` rendered successfully;
- deterministic `schema_valid_rate` was `not_applicable` for both strategies.

## Verdict

Pass. The review-blocking scoring and SuperDialseg adapter defects are fixed,
and the harness is ready for merge from the perspective of the previous review
findings. Residual risk is limited to validating the adapter against a real
local SuperDialseg snapshot once one is available.
