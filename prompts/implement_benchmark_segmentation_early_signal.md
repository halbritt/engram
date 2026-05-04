# Implement Segmentation Benchmark Early Signal

> Hand this to a fresh implementation agent after the early-signal spec review
> synthesis has landed.
>
> Branch: stay on the current benchmark branch unless the operator asks for a
> new branch. If you create one, do not use a `codex` prefix.
>
> Goal: implement RFC 0008 / D042 Tier 0 and Tier 1 benchmark support in the
> local-only segmentation benchmark harness: deterministic sample plans,
> benchmark-tier metadata, fragmentation metrics, structured early-signal
> verdicts, and report tables. Do not run a long model benchmark as part of
> this task.

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
13. `docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_SPEC_REVIEW_2026_05_04.md`
14. `docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_SPEC_SYNTHESIS_2026_05_04.md`
15. `docs/reviews/v1/BENCHMARK_SEGMENTATION_SHORT_PUBLIC_MODEL_RUN_2026_05_03.md`

Read `benchmarks/segmentation/*.py` and
`tests/test_benchmark_segmentation.py` before editing. Read
`src/engram/segmenter.py` only if needed to preserve D034/D037/D038
boundaries; do not refactor production Phase 2 runtime.

## Hard Constraints

- Engram remains local-first. No private user corpus data leaves the machine.
- Do not use the private Engram corpus as benchmark input.
- Do not write the production database.
- Do not alter production migrations.
- Do not change production Phase 2 segmenter behavior.
- Do not add hosted services, cloud APIs, telemetry, or external persistence.
- Do not auto-download public datasets. The harness consumes explicit local
  snapshots and manifests only.
- Do not call ik-llama, Ollama, Hugging Face, or any external service in tests.
- Keep benchmark outputs under caller-supplied scratch directories.
- Keep public dataset rows and bulky run artifacts out of git.
- Preserve D039: benchmark strategy names and `StrategyKind` values must not
  become production `segments.window_strategy` values.

## Current Context

The existing harness can:

- validate local public dataset manifests;
- load SuperDialseg-shaped JSONL and LMSYS-shaped JSONL;
- run deterministic baselines and benchmark-local model strategies;
- write `run.json` / `parents.jsonl`;
- score boundary, provenance, operational, and existing fragment metrics;
- write Markdown and HTML reports.

The 2026-05-03 10-parent run is Tier 0 / `smoke_only`. It is not backfilled.
Do not modify existing scratch result JSON in this task.

The review synthesis accepted these clarifications:

- separate implemented harness behavior from planned RFC 0008 / D042 behavior;
- record threshold sets in result artifacts;
- make `early_signal_verdict.metric_reasons` structured JSON, not
  `key=value` strings;
- define the Tier 1 stratum-shortfall rule;
- add a near-term D042 revisit trigger;
- mark RFC 0006 specified and cross-link RFC 0008 / D042.

## Required Implementation

### 1. Benchmark Tier Metadata

Add benchmark-tier metadata to new result artifacts.

Supported tiers:

```text
smoke
early_signal
decision
```

For this task, implement executable support for:

- `smoke`
- `early_signal`

Do not implement decision-grade model switching logic. Tier 2 can be accepted
as metadata only or rejected with a clear "pending implementation" error.

`run.json` must include:

```json
{
  "benchmark_tier": "smoke",
  "selection_caveat": "smoke_only"
}
```

Tier caveats:

- `smoke` -> `smoke_only`
- `early_signal` -> `early_signal_not_decision_grade`
- `decision` -> `decision_grade` only when Tier 2 is actually implemented

CLI requirements:

- Add `--benchmark-tier {smoke,early_signal,decision}` to `run`.
- Default existing behavior to `smoke` when `--limit 10` is used and no sample
  plan is provided, so current workflows keep working.
- Add `--selection-caveat` only if a manual override is genuinely useful; the
  default tier mapping should be enough.
- Unknown or unsupported tier combinations must fail with clear errors.

Tests:

- Existing deterministic run tests must still pass.
- Add a test asserting `run.json` includes `benchmark_tier` and
  `selection_caveat`.
- Add a test that historical result reading/scoring remains backward
  compatible when these fields are absent.

### 2. Deterministic Sample Plans

Add sample-plan support under `benchmarks/segmentation/`, for example
`sample_plan.py`.

Sample plan schema version:

```text
segmentation-benchmark-sample-plan.v1
```

A sample plan records:

- `schema_version`
- `benchmark_tier`
- dataset name/source/version/revision
- split
- sample seed
- target sample size
- selected parent ids in run order
- stratum assignment per selected parent
- expected boundary count distribution
- message count distribution
- stratum target sizes
- stratum actual sizes
- stratum shortfalls
- sample-plan implementation version

Tier 1 SuperDialseg strata:

- `no_boundary`
- `boundaries_1_2`
- `boundaries_3_5`
- `high_boundary_count`
- `short_dialogue`
- `medium_dialogue`
- `long_dialogue`
- `mixed_role_pattern`

Shortfall rule:

- If a stratum has fewer parents than its target quota, take all available
  parents from that stratum.
- Record actual stratum sizes and shortfalls in the sample plan.
- Fail validation only if the total Tier 1 sample falls below 60 parents.

Selection rules:

- Deterministic for dataset revision, split, seed, tier, target size, and
  implementation version.
- Must not be "first N parents".
- Must preserve the selected parent order in the run.
- Parent ids must be stable and recorded.

CLI requirements:

Add a command such as:

```bash
python3 -m benchmarks.segmentation.run_benchmark sample-plan \
  --dataset-manifest .scratch/benchmarks/datasets/superdialseg/manifest.json \
  --split validation \
  --benchmark-tier early_signal \
  --sample-seed 42 \
  --target-size 80 \
  --output .scratch/benchmarks/segmentation/sample-plans/superdialseg-tier1.json
```

Update `run` to accept:

```text
--sample-plan <path>
```

When a sample plan is supplied, `run` must select exactly those public parents,
in plan order, before adding fixtures. It must validate that the plan matches
the manifest dataset name/source/version and split.

Tests:

- Deterministic sample plan output for synthetic SuperDialseg-shaped fixture
  data.
- Same inputs produce the same parent order.
- Different seeds can produce different order when enough parents exist.
- Shortfall metadata is recorded.
- Tier 1 validation fails if total selected parents falls below 60, unless the
  test explicitly calls a lower-level helper that does not enforce Tier 1.
- `run --sample-plan` respects selected parent order.

### 3. Fragmentation Metrics

Add RFC 0008 fragmentation metrics to scoring while preserving existing metric
shape where possible.

Required metrics:

- predicted/expected segment-count ratio for labeled parents;
- absolute segment-count distance from expected;
- no-boundary false split count and rate;
- sub-50, sub-100, and sub-200 estimated-token fragment rates;
- adjacent tiny-fragment rate;
- duplicate or near-duplicate adjacent summary/content rate;
- count of parents with more than twice the expected segment count.

Keep existing metrics:

- segment count by parent;
- average segment count;
- p10/p50/p90 estimated segment token length;
- strict boundary precision/recall/F1;
- window-tolerant F1;
- P_k;
- WindowDiff;
- over-split and under-split counts;
- operational/provenance metrics.

Implementation guidance:

- Put new metrics under a clear `fragmentation` object in `MetricBundle` and
  serialized score/run output.
- If a dataset is unlabeled, label-dependent fragmentation metrics report
  `not_applicable`, not zero.
- Duplicate or near-duplicate adjacent content can use deterministic local
  text normalization; do not use a model or embedding similarity.
- Adjacent tiny-fragment rate should be deterministic and explain its token
  floor in metadata or field names.
- Do not break report rendering for old result files without `fragmentation`.

Tests:

- no-boundary parent split into multiple segments increments false split
  metrics;
- parent with more than twice expected segment count is counted;
- unlabeled parent reports `not_applicable`;
- duplicate adjacent segment text is counted deterministically;
- existing scoring tests still pass.

### 4. Early-Signal Threshold Set

Do not invent permanent Engram thresholds in code.

Implement threshold-set plumbing with an explicit schema:

```text
segmentation-benchmark-early-signal-thresholds.v1
```

A threshold set must include:

- `schema_version`
- `threshold_set_id`
- `source`
- `created_at` or `status`
- hard gate thresholds that are specified today:
  - `schema_valid_rate_min`
  - `provenance_valid_rate_min`
  - `forbidden_backend_error_kinds`
- fragmentation thresholds that are still provisional:
  - `no_boundary_false_split_rate_max`
  - `segment_count_ratio_max`
  - `sub_100_fragment_rate_max`
  - `adjacent_tiny_fragment_rate_max`
  - `duplicate_adjacent_rate_max`

Because RFC 0008 Open Question 1 is still open, the CLI must require an
explicit threshold-set file when producing a Tier 1 verdict. Do not silently
use hidden defaults for provisional thresholds.

Add a tiny benchmark-local example threshold file only for tests or examples,
clearly marked as non-normative, for example:

```text
benchmarks/segmentation/fixtures/early_signal_thresholds.example.json
```

CLI requirements:

```text
--early-signal-thresholds <path>
```

Behavior:

- `early_signal` runs without thresholds may still score, but must not emit a
  `candidate` verdict. Prefer failing only the verdict-generation step with a
  clear error if implementation shape makes that cleaner.
- If a threshold file is supplied, copy the threshold set into `run.json` and
  `score.json`.
- Record threshold source and any overrides in the verdict object.

Tests:

- invalid threshold schema fails validation with clear errors;
- valid threshold set is copied into result metadata;
- absence of thresholds prevents a Tier 1 `candidate` verdict.

### 5. Structured Early-Signal Verdict

Add structured early-signal verdicts for Tier 1 strategy outputs.

Verdict schema version:

```text
segmentation-benchmark-early-signal-verdict.v1
```

Object shape:

```json
{
  "schema_version": "segmentation-benchmark-early-signal-verdict.v1",
  "strategy_name": "qwen_27b_q5_k_m_d034",
  "verdict": "longer_run",
  "selection_caveat": "early_signal_not_decision_grade",
  "summary": "Short human-readable reason.",
  "hard_warnings": [],
  "blocking_failures": [],
  "metric_reasons": {
    "schema_valid_rate": {"value": 1.0, "threshold": 1.0, "passed": true},
    "provenance_valid_rate": {"value": 1.0, "threshold": 1.0, "passed": true}
  },
  "threshold_set": {
    "schema_version": "segmentation-benchmark-early-signal-thresholds.v1",
    "threshold_set_id": "example"
  }
}
```

Allowed verdicts:

- `reject`
- `defer`
- `longer_run`
- `candidate`

Rules:

- Schema/provenance safety failures are blocking.
- Backend wedge, CUDA OOM, and runaway completion are blocking.
- No-boundary false splits and fragmentation threshold failures create hard
  warnings or blocking failures depending on the threshold set.
- A challenger cannot receive `candidate` unless it beats deterministic
  baselines and the current operational model after fragmentation checks.
- If the current operational model strategy is absent from the run, the
  verdict must say comparison-to-operational-model is unavailable and avoid
  `candidate`.
- Tier 0 never emits `candidate`.
- Tier 2 decision recommendations are out of scope for this task.

Implementation guidance:

- Keep verdict logic deterministic and inspectable.
- Do not introduce a local LLM judge.
- Do not parse `key=value` strings.
- Make verdict generation re-runnable from existing result artifacts when
  possible, or document why it requires original in-memory metrics.

Tests:

- schema/provenance failure yields `reject`;
- valid but not improving yields `defer`;
- promising but missing operational-model comparison yields `longer_run`, not
  `candidate`;
- threshold failure is represented in `hard_warnings` or
  `blocking_failures`;
- `metric_reasons` is an object with values, thresholds, and pass/fail state.

### 6. Report Updates

Update Markdown and HTML reports to include:

- benchmark tier and selection caveat;
- sample-plan summary when present;
- fragmentation table;
- early-signal verdict table when present;
- threshold-set id/source when present.

Report behavior:

- Existing old `run.json` files without the new fields must still render.
- `report` must not rerun strategies, load datasets unnecessarily, call
  models, or touch production state.
- Keep per-parent detail bounded by `--max-parents`.

Tests:

- report generation succeeds for an old-style result file;
- report generation includes tier/caveat for new result files;
- report generation includes verdict and fragmentation tables for Tier 1
  result files.

### 7. Fixture Expansion

Expand the synthetic fixture set enough to support Tier 1 Engram-proxy checks.
Fixtures must remain public, synthetic, and hand-authored.

Cover at least:

- long coding/debugging thread;
- topic re-entry after interruption;
- repeated or near-duplicate facts;
- quiet durable preference inside noisy conversation;
- tool/file artifact placeholders;
- null/image/tool-only messages;
- privacy-tier mixed spans;
- JSON-looking content;
- one-segment conversation;
- near context-guard conversation.

Guidance:

- Keep each fixture small except the near-context-guard fixture, which can use
  synthetic repeated text but should not be huge in git.
- Preserve `message_ids` as provenance and `embeddable_message_ids` as the
  embeddable subset.
- Update expected claims only when needed by existing fixture validation; do
  not implement a claim extractor.

Tests:

- fixture validation passes for the expanded set;
- tool/file placeholders remain provenance-only in expected fixture data;
- privacy-tier mixed fixture validates.

### 8. Documentation

Update docs as needed:

- `benchmarks/segmentation/README.md`
- `benchmarks/segmentation/SPEC.md`
- `docs/rfcs/0008-segmentation-benchmark-early-signal.md` only if the
  implementation reveals a spec gap
- `DECISION_LOG.md` only if you make a new architectural decision

Do not rewrite generated schema docs by hand.

## Suggested File Targets

Likely code files:

- `benchmarks/segmentation/run_benchmark.py`
- `benchmarks/segmentation/datasets.py`
- `benchmarks/segmentation/fixtures.py`
- `benchmarks/segmentation/scoring.py`
- `benchmarks/segmentation/results.py`
- `benchmarks/segmentation/reporting.py`
- `benchmarks/segmentation/strategies.py` only if needed for metadata helpers
- new `benchmarks/segmentation/sample_plan.py`
- new `benchmarks/segmentation/early_signal.py`
- `tests/test_benchmark_segmentation.py`

Likely fixture files:

- `benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl`
- `benchmarks/segmentation/fixtures/expected_claims.example.jsonl`
- optional `benchmarks/segmentation/fixtures/early_signal_thresholds.example.json`

## Validation Minimum

Run:

```bash
python3 -m py_compile benchmarks/segmentation/*.py
.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -q
.venv/bin/python -m pytest -q
python3 -m benchmarks.segmentation.run_benchmark list-strategies
python3 -m benchmarks.segmentation.run_benchmark validate-fixtures \
  --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl \
  --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl
```

Also add a small synthetic or shape-data end-to-end run that exercises:

- `sample-plan`;
- `run --benchmark-tier early_signal --sample-plan ...`;
- `score`;
- `report --format both`.

Keep that output under `.scratch/benchmarks/segmentation/` and out of git.

If a validation command cannot run because of local environment constraints,
record the exact command, failure, and why it is acceptable.

## Deliverables

- Code and tests implementing Tier 0/Tier 1 early-signal support.
- Updated docs that distinguish implemented behavior from planned Tier 2
  behavior.
- Scratch-only sample run artifacts proving the flow works on synthetic or
  local public-shape data.
- Final summary listing:
  - changed files;
  - validation commands and results;
  - scratch artifact paths;
  - any deferred RFC 0008 open questions still not answered.

Do not commit or push unless the operator asks.
