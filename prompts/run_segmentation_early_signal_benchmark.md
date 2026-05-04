# Run Segmentation Early-Signal Benchmark

> Hand this to a fresh execution agent after the RFC 0008 / D042 Tier 0 and
> Tier 1 benchmark harness implementation and implementation-review fixes have
> landed.
>
> Branch: stay on the current benchmark branch unless the operator asks for a
> new branch. If you create one, do not use a `codex` prefix.
>
> Goal: run a local-only Tier 1 early-signal segmentation benchmark against an
> explicit local public SuperDialseg snapshot plus the synthetic Engram-proxy
> fixtures. Compare deterministic baselines, the current operational model,
> and available challenger models. Do not use the private Engram corpus, do not
> write production database state, and do not make production model-selection
> changes from this run alone.

## Read First

1. `README.md`
2. `HUMAN_REQUIREMENTS.md`
3. `DECISION_LOG.md`, especially D034, D037, D038, D039, D041, and D042.
4. `BUILD_PHASES.md`
5. `ROADMAP.md`
6. `SPEC.md`
7. `docs/schema/README.md`
8. `docs/process/multi-agent-review-loop.md`
9. `docs/rfcs/0006-segmentation-model-benchmark.md`
10. `docs/rfcs/0008-segmentation-benchmark-early-signal.md`
11. `benchmarks/segmentation/README.md`
12. `benchmarks/segmentation/SPEC.md`
13. `docs/reviews/v1/BENCHMARK_SEGMENTATION_SHORT_PUBLIC_MODEL_RUN_2026_05_03.md`
14. `docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_SPEC_SYNTHESIS_2026_05_04.md`
15. `docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_IMPLEMENTATION_REVIEW_2026_05_04.md`
16. `docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_IMPLEMENTATION_REVIEW_SYNTHESIS_2026_05_04.md`

Read `benchmarks/segmentation/*.py` and
`tests/test_benchmark_segmentation.py` before running the benchmark. Do not
refactor production Phase 2 runtime.

## Hard Constraints

- Engram remains local-first. No private user corpus data leaves the machine.
- Do not use the private Engram corpus as benchmark input.
- Do not write the production database.
- Do not alter production migrations.
- Do not change production Phase 2 segmenter behavior.
- Do not add hosted services, cloud APIs, telemetry, or external persistence.
- Do not auto-download public datasets. The harness consumes explicit local
  snapshots and manifests only.
- Keep benchmark outputs under caller-supplied scratch directories.
- Keep public dataset rows and bulky run artifacts out of git.
- Preserve D039: benchmark strategy names and `StrategyKind` values must not
  become production `segments.window_strategy` values.
- Tier 1 is not decision-grade. Do not recommend a production model switch
  unless a later Tier 2 decision run supports it.

## Preconditions

Before running models, confirm:

- The working tree is clean or only contains intentional run-note edits.
- No active production `engram.cli segment`, `make segment`, or
  `make pipeline` process is running.
- The local public SuperDialseg manifest exists. Do not create it by
  downloading data in this task.
- The manifest points to a local snapshot and validates:

```bash
python3 -m benchmarks.segmentation.run_benchmark validate-dataset \
  --manifest .scratch/benchmarks/datasets/superdialseg/manifest.json \
  --split validation
```

- The synthetic fixtures validate:

```bash
python3 -m benchmarks.segmentation.run_benchmark validate-fixtures \
  --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl \
  --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl
```

- The benchmark tests still pass:

```bash
python3 -m py_compile benchmarks/segmentation/*.py
.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -q
```

If the local SuperDialseg manifest is absent, stop and report exactly what is
missing. Do not download it.

## Benchmark Shape

Run Tier 1:

- 60-100 deterministic stratified SuperDialseg validation parents via
  `sample-plan`.
- Full synthetic fixture set:
  `benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl`.
- Deterministic baselines:
  - `fixed_token_windows`
  - `message_groups`
- Current operational model strategy:
  - default: `qwen_35b_a3b_iq4_xs_d034`
- Challenger model strategies if locally runnable:
  - `qwen_27b_q5_k_m_d034`
  - `gemma_26b_a4b_q4_k_m_d034`

Use the same sample plan and threshold set for every strategy. If a challenger
model is unavailable, record that fact and continue with the available
strategies. Do not silently omit the current operational model from a model
comparison run; if it cannot run, verdicts for challengers must remain
`longer_run`, not `candidate`.

## Threshold Set

RFC 0008 leaves real Engram thresholds open. The checked-in threshold file is
non-normative example data:

```text
benchmarks/segmentation/fixtures/early_signal_thresholds.example.json
```

For this run, either:

- use that file and label the report as a non-normative threshold run; or
- create a scratch-only threshold file under `.scratch/benchmarks/segmentation/`
  with an explicit `threshold_set_id`, `source`, and `created_at`.

Do not commit scratch threshold files unless the operator explicitly asks.

## Scratch Paths

Use a dated scratch root:

```bash
RUN_ROOT=.scratch/benchmarks/segmentation/early-signal-$(date -u +%Y%m%dT%H%M%SZ)
MANIFEST=.scratch/benchmarks/datasets/superdialseg/manifest.json
SAMPLE_PLAN="$RUN_ROOT/sample-plans/superdialseg-tier1.json"
RESULT_ROOT="$RUN_ROOT/results"
THRESHOLDS=benchmarks/segmentation/fixtures/early_signal_thresholds.example.json
```

Create the sample plan:

```bash
python3 -m benchmarks.segmentation.run_benchmark sample-plan \
  --dataset-manifest "$MANIFEST" \
  --split validation \
  --benchmark-tier early_signal \
  --sample-seed 42 \
  --target-size 80 \
  --output "$SAMPLE_PLAN"
```

Inspect the plan before running models:

- selected parent count is 60-100;
- `stratum_shortfalls` are recorded;
- dataset name/source/version/revision match the manifest;
- selected ids are not simply the first N parents.

## Deterministic Baseline Run

Run deterministic baselines first. This validates sample-plan replay, scoring,
reports, and threshold/verdict plumbing before any model server work.

```bash
python3 -m benchmarks.segmentation.run_benchmark run \
  --dataset-manifest "$MANIFEST" \
  --benchmark-tier early_signal \
  --sample-plan "$SAMPLE_PLAN" \
  --early-signal-thresholds "$THRESHOLDS" \
  --operational-model-strategy qwen_35b_a3b_iq4_xs_d034 \
  --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl \
  --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl \
  --strategy fixed_token_windows \
  --strategy message_groups \
  --output-dir "$RESULT_ROOT/deterministic" \
  --target-tokens 200
```

Then score and report:

```bash
RUN_JSON=<path printed by run command>
python3 -m benchmarks.segmentation.run_benchmark score --results "$RUN_JSON"
python3 -m benchmarks.segmentation.run_benchmark report \
  --results "$RUN_JSON" \
  --format both \
  --max-parents 25
```

If deterministic scoring/reporting fails, stop and fix the harness or record
the failure. Do not proceed to model runs against a broken reporting path.

## Local Model Runs

Local-model strategies require `--allow-local-models` and a loopback
OpenAI-compatible endpoint. They must refuse non-loopback URLs.

Recommended run style:

- Run one model strategy per result directory so a backend wedge or manual
  server restart cannot contaminate another model's metadata.
- For each model, start the appropriate local `llama-server` on
  `127.0.0.1:8081`, then run only that strategy.
- Before each model run, confirm `GET /v1/models`, `GET /props`, and a tiny
  D034 JSON-schema completion smoke succeed. Do not rely on GET endpoints
  alone.
- After each model run, run another tiny completion smoke. If it fails, record
  the server logs and mark the model run as suspect.
- Stop the manual server cleanly before launching the next model.
- Restore the normal local model service state after the benchmark.

Do not run model benchmarks if another process is using the same GPU/server in
a way that could affect the run or production segmentation.

Template command for a single local-model strategy:

```bash
python3 -m benchmarks.segmentation.run_benchmark run \
  --dataset-manifest "$MANIFEST" \
  --benchmark-tier early_signal \
  --sample-plan "$SAMPLE_PLAN" \
  --early-signal-thresholds "$THRESHOLDS" \
  --operational-model-strategy qwen_35b_a3b_iq4_xs_d034 \
  --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl \
  --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl \
  --strategy qwen_35b_a3b_iq4_xs_d034 \
  --output-dir "$RESULT_ROOT/qwen_35b_a3b_iq4_xs_d034" \
  --allow-local-models \
  --local-model-base-url http://127.0.0.1:8081 \
  --local-model-timeout-seconds 600 \
  --local-model-max-tokens 4096
```

Repeat with:

```text
qwen_27b_q5_k_m_d034
gemma_26b_a4b_q4_k_m_d034
```

Score and report each `run.json`:

```bash
python3 -m benchmarks.segmentation.run_benchmark score --results "$RUN_JSON"
python3 -m benchmarks.segmentation.run_benchmark report \
  --results "$RUN_JSON" \
  --format both \
  --max-parents 25
```

## Combined Comparison

The current harness scores one `run.json` at a time. After individual runs:

1. Collect the key metrics from each `score.json`:
   - schema-valid rate;
   - provenance-valid rate;
   - backend error counts;
   - parent throughput;
   - strict boundary F1;
   - window-tolerant F1;
   - P_k;
   - WindowDiff;
   - predicted/expected segment-count ratio;
   - no-boundary false split rate;
   - sub-100 fragment rate;
   - adjacent tiny-fragment rate;
   - duplicate adjacent rate;
   - verdict and hard warnings.
2. Compare against the deterministic baseline run and the current operational
   model run.
3. Treat any challenger without both comparison anchors as `longer_run`, not
   `candidate`.

If you create a comparison summary script or notebook, keep it under
`.scratch/` unless the operator explicitly asks to commit it.

## Review Artifact

Write a dated run report under `docs/reviews/v1/`, for example:

```text
docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_RUN_2026_05_04.md
```

Include:

- branch and commit;
- dataset manifest path, dataset name/source/version/revision, split, and
  selected parent count;
- sample-plan path and stratum shortfalls;
- threshold-set id/source and whether it is non-normative;
- strategy list, model paths, model sizes, and SHA256 status;
- server handling notes, smoke checks, and any backend logs;
- artifact paths for each `run.json`, `score.json`, `report.md`, and
  `report.html`;
- metrics table across strategies;
- verdict table and interpretation;
- explicit statement that Tier 1 is not decision-grade;
- next action: reject, defer, run longer Tier 1, or schedule Tier 2.

Do not paste bulky per-parent JSON into the review artifact. Link scratch paths
instead.

## Validation Minimum

Run before final response:

```bash
python3 -m py_compile benchmarks/segmentation/*.py
.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -q
python3 -m benchmarks.segmentation.run_benchmark validate-fixtures \
  --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl \
  --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl
```

For every `run.json` produced:

```bash
python3 -m benchmarks.segmentation.run_benchmark score --results <run.json>
python3 -m benchmarks.segmentation.run_benchmark report \
  --results <run.json> \
  --format both \
  --max-parents 25
```

If any validation cannot run because of local environment constraints, record
the exact command, failure, and why it is acceptable.

## Final Response

Report:

- commands run and outcomes;
- which strategies ran and which were skipped;
- review artifact path;
- scratch artifact paths;
- key metrics and verdicts;
- whether any result justifies Tier 2 scheduling;
- any environment caveats that make the run suspect.

Do not commit or push unless the operator asks.
