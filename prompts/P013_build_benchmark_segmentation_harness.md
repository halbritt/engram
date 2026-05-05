# P013: Build Benchmark Segmentation Harness

> Prompt ordinal: P013. Introduced: 2026-05-03T18:56:51+00:00. Source commit: 71efa23.

> Hand this to a coding agent after the benchmark harness skeleton and review
> synthesis have landed.
>
> Branch: create a new non-`codex` branch such as
> `feature/benchmark-segmentation-harness-runner`.
>
> Goal: turn the `benchmarks/segmentation/` skeleton into a runnable,
> local-only, public-first benchmark harness for public dataset snapshot
> validation, deterministic baseline runs, result writing, and scoring. Do not
> run local model benchmarks as part of this task.

## Read First

1. `README.md`
2. `HUMAN_REQUIREMENTS.md`
3. `DECISION_LOG.md`, especially D005, D034, D037, D038, D039, and D041.
4. `BUILD_PHASES.md`
5. `ROADMAP.md`
6. `SPEC.md`
7. `docs/schema/README.md`
8. `docs/rfcs/0006-segmentation-model-benchmark.md`
9. `prompts/benchmark_segmentation_harness_spec.md`
10. `benchmarks/segmentation/README.md`
11. `benchmarks/segmentation/SPEC.md`
12. `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_REVIEW.md`
13. `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_SYNTHESIS_2026_05_03.md`
14. `docs/segmentation.md`

Read `src/engram/segmenter.py` only enough to preserve production boundaries:
structured response shape, provenance validation expectations,
context-budget failure posture, and tool/file placeholder handling. Do not
refactor Phase 2 runtime code.

## Hard Constraints

- No cloud APIs, hosted services, telemetry, or external persistence.
- Do not auto-download public datasets. The harness consumes explicit local
  snapshots and fails clearly when a required snapshot is absent.
- Do not write to the production database.
- Do not alter production migrations or Phase 2 runtime code.
- Do not call ik-llama, Ollama, Hugging Face, or any external service during
  implementation or tests.
- Keep benchmark outputs scratch-only under a user-supplied output directory.
- Do not add heavyweight dependencies. Prefer Python standard library plus the
  repo's existing pytest dev dependency.
- Preserve D039: benchmark strategy names must not become production
  `segments.window_strategy` values.

## Required Implementation

Implement the live harness for **offline deterministic public-dataset benchmark
work** and leave explicit, safe hooks for future local-model strategies.

### 1. Apply Review Synthesis Cleanup

Resolve all accepted findings from
`BENCHMARK_SEGMENTATION_HARNESS_SYNTHESIS_2026_05_03.md`:

- Remove the no-op `--offline` flag, or replace it with a meaningful opt-in
  flag such as `--allow-local-models` defaulting false.
- Add explicit embeddable-vs-provenance handling in fixture schema and example
  fixtures. Preferred field: `embeddable_message_ids` on expected segments.
- Pin claim matching normalization: Unicode NFKC, `casefold()`, whitespace
  collapse, no punctuation stripping.
- Document model SHA256 sidecar manifest policy.
- Document schema version bump discipline.
- Add `benchmarks/__init__.py` and `benchmarks/segmentation/__init__.py`.
- Clarify that `StrategyKind` is benchmark-internal and not production
  `segments.window_strategy`.
- Add backend error classes:
  `connect_refused`, `read_timeout`, `http_5xx`, `grammar_stack_empty`,
  `cuda_oom`, `backend_wedge_post_smoke`, `unknown`.
- Apply D041: SuperDialseg is the first quality dataset, LMSYS-Chat-1M is the
  first optional operational stress dataset, and synthetic fixtures are only
  edge-case/regression tests.

No `DECISION_LOG.md` update is expected unless you discover a new architecture
decision.

### 2. Public Dataset Manifests And Adapters

Add public dataset support, for example:

```text
benchmarks/segmentation/datasets.py
```

It should:

- Load a local public dataset manifest. Do not download data.
- Validate manifest `schema_version`, `dataset_name`, `dataset_source`,
  `dataset_version`, `local_path`, license metadata, and preprocessing version.
- Refuse missing local paths or unaccepted gated-license snapshots with clear
  errors.
- Normalize public rows into the same in-memory parent type used by strategies.
- Support SuperDialseg first:
  - adapter name: `superdialseg`
  - source identifiers: Hugging Face `Coldog2333/super_dialseg` and/or local
    export from the SuperDialseg project repository
  - input fields: `dial_id`, ordered `utterance`, `role`, `turn_id`,
    `topic_id`, `segmentation_label` where available
  - output: parent messages plus labeled boundary positions between utterances
- Support an LMSYS-Chat-1M manifest and adapter skeleton:
  - adapter name: `lmsys_chat_1m`
  - source identifier: Hugging Face `lmsys/lmsys-chat-1m`
  - no quality labels by default; boundary/claim metrics that require labels
    must report `not_applicable`
  - no redistribution of rows, no committed sample rows from the dataset
- Include a tiny hand-authored public-shaped sample file for tests if needed,
  clearly marked as synthetic shape data and not copied from the public
  datasets.

Do not add `datasets`, `huggingface_hub`, `pyarrow`, or `pandas` unless the
task is explicitly expanded. For this pass, prefer JSON/JSONL/parquet-free
local exports that can be prepared outside the harness.

### 3. Fixture Loading And Validation

Add a fixture module, for example:

```text
benchmarks/segmentation/fixtures.py
```

It should:

- Load JSONL files with a required first-line header.
- Validate `fixture_version` and `schema_version`.
- Validate fixture records, messages, expected segments, and expected claims.
- Validate UUID syntax and parent-local message id references.
- Validate expected segment `message_ids` are ordered and parent-local.
- Validate `embeddable_message_ids` are a subset of `message_ids`.
- Validate expected claim evidence message ids and expected segment ids.
- Report all validation errors clearly, not just the first one.
- Return typed dataclasses or simple immutable structures for the runner.

Do not add `pydantic` or other schema libraries.

Synthetic fixtures are not the primary benchmark dataset. They are regression
tests for edge cases public datasets do not isolate well.

### 4. Strategies

Make `benchmarks/segmentation/strategies.py` executable for deterministic
strategies:

- `fixed_token_windows`
  - Inputs: `target_tokens`, `overlap_messages`, estimator config.
  - Preserve message order.
  - Do not split a single message; if one message exceeds target, emit it as a
    single segment and record that in raw metadata.
  - Generate `content_text` from embeddable message content only.
- `message_groups`
  - Group contiguous messages up to `target_tokens`, preserving natural
    message order.
  - Keep adjacent user/assistant turns together when possible under budget.
  - Generate `content_text` from embeddable message content only.
- LLM strategies (`current_qwen_d034`, `qwen_candidate_d034`,
  `gemma_candidate_d034`)
  - Keep them registered.
  - They must refuse to run unless an explicit local-model opt-in flag/config is
    provided.
  - For this task, it is acceptable for them to raise a clear
    `NotImplementedError` or `StrategyUnavailable` before any network access.

Add a local benchmark token estimator with an explicit version string. Keep it
simple and deterministic; do not import production segmenter code just to count
tokens.

### 5. Result Writing

Add result support, for example:

```text
benchmarks/segmentation/results.py
```

The runner should write scratch artifacts under:

```text
<output-dir>/<run_id>/
  run.json
  parents.jsonl
```

Result metadata must include:

- git commit
- dataset manifest/schema version
- public dataset name/source/snapshot/version
- fixture version/schema version when synthetic fixtures are included
- expected-claims schema version when synthetic claims are included
- strategy name/kind/config/version
- scoring implementation version
- benchmark token estimator version
- relevant `ENGRAM_SEGMENTER_*` environment variables
- dataset kind/name/snapshot
- created_at UTC timestamp

For model fields that are unavailable because local-model strategies were not
run, write explicit `null` values or `"not_run"` markers rather than omitting
the keys.

### 6. Scoring

Implement `benchmarks/segmentation/scoring.py` enough to score deterministic
baseline outputs against SuperDialseg-style labeled public parents and
synthetic regression fixtures:

- Provenance validation:
  - unknown message ids
  - cross-parent ids if an id is known in another fixture
  - unordered ids
  - empty embeddable segment text
- Operational metrics:
  - schema-valid rate for strategy outputs
  - provenance-valid rate
  - empty embeddable segment count
  - sub-floor fragment counts at 50, 100, 200 estimated tokens
  - parent throughput for deterministic strategies
  - timeout/runaway/backend error counts as zero or `not_applicable` for
    deterministic strategies
- Segmentation metrics:
  - segment count per parent
  - p10/p50/p90 segment estimated token length
  - strict boundary precision/recall/F1
  - window-tolerant F1 at +/-1 and +/-2 message positions
  - P_k
  - WindowDiff
  - boundary over-split and under-split counts
- Claim utility:
  - Implement normalization and expected-claim matching helpers.
  - Do not invent a fake LLM extractor.
  - If no benchmark extractor is run, emit claim utility metrics as
    `not_run` with denominators. Keep the interface ready for a later local
    extractor.

Boundary metrics should operate on boundary positions between message sequence
indexes. Macro-average by parent where appropriate and report denominators.
For LMSYS-Chat-1M or any unlabeled public dataset, label-dependent metrics
must report `not_applicable`, never zero.

### 7. CLI

Make `python3 -m benchmarks.segmentation.run_benchmark` support:

```bash
python3 -m benchmarks.segmentation.run_benchmark validate-dataset \
  --manifest .scratch/benchmarks/datasets/superdialseg/manifest.json

python3 -m benchmarks.segmentation.run_benchmark validate-fixtures \
  --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl \
  --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl

python3 -m benchmarks.segmentation.run_benchmark list-strategies

python3 -m benchmarks.segmentation.run_benchmark run \
  --dataset-manifest .scratch/benchmarks/datasets/superdialseg/manifest.json \
  --strategy fixed_token_windows \
  --strategy message_groups \
  --output-dir .scratch/benchmarks/segmentation

python3 -m benchmarks.segmentation.run_benchmark score \
  --results .scratch/benchmarks/segmentation/<run_id>/run.json
```

The `run` command should:

- Validate the public dataset manifest first.
- Run each requested deterministic strategy over the selected public dataset
  split or bounded slice.
- Write scratch results.
- Print the output run path.
- Exit nonzero on dataset/fixture validation errors or unknown strategies.
- Refuse LLM strategies unless explicitly enabled, and even then do not make
  network calls in this implementation unless the task has been explicitly
  expanded.

It may also accept optional synthetic fixtures in the same run for regression
coverage, but the default example run should be SuperDialseg-based.

### 8. Tests

Add focused tests, for example:

```text
tests/test_benchmark_segmentation.py
```

Cover:

- Public dataset manifest validation.
- SuperDialseg adapter behavior on a tiny hand-authored public-shaped sample.
- LMSYS adapter refusal/not-applicable behavior without labels.
- Fixture and expected-claim JSONL validation.
- Invalid UUID / unknown message id / bad claim reference errors.
- `embeddable_message_ids` subset validation.
- Deterministic `fixed_token_windows` and `message_groups` behavior.
- Boundary metric calculations on simple known cases.
- P_k and WindowDiff on at least one known boundary vector.
- Claim normalization behavior.
- CLI `validate-fixtures`, `list-strategies`, `run`, and `score` on example
  public-shaped sample data and synthetic fixtures.
- LLM strategy refusal path without network access.

Tests must not require Postgres, ik-llama, Ollama, network, or GPU.

## Documentation Updates

Update:

- `benchmarks/segmentation/README.md`
- `benchmarks/segmentation/SPEC.md`

Reflect the implemented CLI shape, deterministic strategy support, scratch
result layout, public-first dataset order, current `not_run` claim-utility
behavior, and all synthesis cleanup decisions.

Do not edit generated schema docs.

## Validation Commands

Run:

```bash
python3 -m py_compile benchmarks/segmentation/*.py
python3 -m benchmarks.segmentation.run_benchmark --help
python3 -m benchmarks.segmentation.run_benchmark validate-dataset \
  --manifest <local-superdialseg-manifest>
python3 -m benchmarks.segmentation.run_benchmark validate-fixtures \
  --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl \
  --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl
python3 -m benchmarks.segmentation.run_benchmark list-strategies
python3 -m benchmarks.segmentation.run_benchmark run \
  --dataset-manifest <local-superdialseg-manifest> \
  --strategy fixed_token_windows \
  --strategy message_groups \
  --output-dir .scratch/benchmarks/segmentation
python3 -m benchmarks.segmentation.run_benchmark score \
  --results .scratch/benchmarks/segmentation/<run_id>/run.json
make test
```

If `.venv` is required for `make test`, use the repo Makefile. Do not start
model services.

If no local SuperDialseg snapshot exists on the machine, run the unit tests
against the tiny hand-authored public-shaped sample and report that full public
dataset validation was not run. Do not fall back to the private Engram corpus.

## Deliverable Summary

At the end, summarize:

- Files changed.
- Which synthesis findings were resolved.
- How D041 public-first dataset order was implemented.
- Exact validation commands and results.
- Any deliberately deferred local-model or benchmark-extractor work.
- The scratch result path from the example deterministic run.
