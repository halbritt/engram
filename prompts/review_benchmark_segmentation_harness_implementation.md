# Review Benchmark Segmentation Harness Implementation

> Hand this to another coding/review agent on the
> `build-benchmark-segmentation-harness` branch.
>
> Goal: review the runnable public-first segmentation benchmark harness
> implementation. Write findings to
> `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_IMPLEMENTATION_REVIEW.md`.

## Read First

1. `README.md`
2. `HUMAN_REQUIREMENTS.md`
3. `DECISION_LOG.md`, especially D005, D034, D037, D038, D039, and D041.
4. `docs/rfcs/0006-segmentation-model-benchmark.md`
5. `prompts/build_benchmark_segmentation_harness.md`
6. `benchmarks/segmentation/README.md`
7. `benchmarks/segmentation/SPEC.md`
8. `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_REVIEW.md`
9. `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_SYNTHESIS_2026_05_03.md`
10. `docs/segmentation.md`

Read `src/engram/segmenter.py` only enough to verify boundary compatibility:
structured response shape, provenance expectations, context-budget failure
posture, and tool/file placeholder handling. Do not review unrelated Phase 2
runtime behavior.

## Review Scope

Review the implementation work only:

```text
benchmarks/
  __init__.py
  segmentation/
    __init__.py
    README.md
    SPEC.md
    datasets.py
    fixtures.py
    reporting.py
    results.py
    run_benchmark.py
    scoring.py
    strategies.py
    fixtures/*.jsonl
tests/test_benchmark_segmentation.py
.gitignore
```

Start with:

```bash
git status --short --branch
git diff --stat
git diff -- benchmarks tests .gitignore
git ls-files --others --exclude-standard
```

If the implementation is still uncommitted in the shared checkout, include
both tracked diffs and untracked files in the review. Ignore `__pycache__`
files except to flag if they would be committed.

## Hard Constraints

- Do not call ik-llama, Ollama, Hugging Face, or any external service.
- Do not download public datasets.
- Do not write to the production database.
- Do not alter production migrations or Phase 2 runtime code.
- Do not use the private Engram corpus as a fallback benchmark substrate.
- Do not implement fixes during this review pass unless explicitly asked.

## What To Check

Prioritize bugs, data-leak risks, correctness gaps, and missing tests.

### Public-First Data Boundary

- SuperDialseg is the first quality target per D041.
- LMSYS-Chat-1M is operational-stress only unless labels are separately
  authored.
- Dataset adapters consume explicit local snapshots/manifests and never
  download data.
- Missing snapshots or missing license acceptance fail clearly and do not fall
  back to private data.
- Committed sample rows are hand-authored shape data, not copied public
  dataset rows.
- Public dataset rows are never mixed into production tables or committed
  fixtures.

### Fixture And Dataset Validation

- JSON/JSONL loaders validate headers, schema versions, UUIDs/stable ids,
  parent-local references, expected segment spans, expected claims, and
  `embeddable_message_ids` subset rules.
- Validation reports all useful errors rather than stopping at the first
  avoidable failure.
- SuperDialseg boundary derivation from `segmentation_label` / `topic_id` is
  deterministic and correct at message-boundary positions.
- LMSYS unlabeled parents propagate `expected_boundaries=None` so
  label-dependent metrics become `not_applicable`, not zero.

### Strategies

- `fixed_token_windows` preserves message order, handles oversize single
  messages, respects overlap semantics, and only uses embeddable message text.
- `message_groups` keeps adjacent user/assistant turns together when possible
  without violating token caps or order.
- LLM strategies are registered but refuse safely before any model/network
  call, even if `--allow-local-models` is passed in this implementation.
- `StrategyKind` remains benchmark-internal and does not become production
  `segments.window_strategy`.

### Scoring

- Provenance validation catches unknown ids, cross-parent ids, unordered ids,
  and empty embeddable text.
- Boundary metrics use positions between message sequence indexes.
- Strict precision/recall/F1, window-tolerant F1, P_k, WindowDiff,
  over-split, and under-split are implemented correctly on simple known cases.
- Macro averaging and denominators are explicit and stable.
- Sub-floor counts at 50/100/200 use the documented estimator.
- Claim normalization is exactly NFKC, `casefold()`, whitespace collapse, and
  no punctuation stripping.
- Claim utility reports `not_run` with denominators unless a real
  benchmark-only extractor is explicitly implemented later.
- Operational metrics for deterministic strategies use `not_applicable` where
  appropriate rather than misleading zeroes.

### Result Artifacts

- Results write only under caller-supplied output directories.
- `run.json`, `parents.jsonl`, and `score.json` are reproducible enough to
  re-score without the original in-memory objects.
- Result metadata includes git commit, dataset manifest/source/snapshot,
  preprocessing version, strategy config/version, scoring version, token
  estimator version, relevant `ENGRAM_SEGMENTER_*` environment variables, and
  explicit model `not_run` markers.
- Model SHA256 sidecar manifest policy is documented and not faked for
  deterministic runs.

### CLI And Tests

- CLI commands match docs:
  `validate-dataset`, `validate-fixtures`, `list-strategies`, `run`, `score`.
- CLI exits nonzero on validation errors, unknown strategies, and refused LLM
  strategies.
- Tests do not require Postgres, model services, network, GPU, public dataset
  downloads, or private corpus access.
- Tests cover failure cases, not only happy paths.
- `.gitignore` excludes scratch result output and cache artifacts without
  hiding source files that should be reviewed.

## Suggested Validation

Run only local/offline checks:

```bash
python3 -m py_compile benchmarks/segmentation/*.py
python3 -m benchmarks.segmentation.run_benchmark --help
python3 -m benchmarks.segmentation.run_benchmark list-strategies
python3 -m pytest tests/test_benchmark_segmentation.py
make test
```

If `make test` requires local Postgres for unrelated tests and is unavailable,
record that limitation and run the benchmark-specific pytest file instead.

If the branch includes a tiny local public-shaped manifest in tests, validate
that path through the CLI. Do not use a real SuperDialseg/LMSYS snapshot unless
it already exists locally and no download/network call is needed.

## Deliverable

Create or replace:

```text
docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_IMPLEMENTATION_REVIEW.md
```

Use this structure:

```markdown
# Benchmark Segmentation Harness Implementation Review

Date: <UTC timestamp>
Reviewer: <model / agent name>
Branch: build-benchmark-segmentation-harness
Base: <base commit or branch reviewed against>

## Findings

### 1. <severity>: <title>
File/line: `<path>:<line>`

<Finding with concrete risk and why it matters.>

Recommendation:
<Specific suggested fix or clarification.>

## Non-Blocking Notes

<Optional observations that are useful but not findings.>

## Validation

<Commands run and results. If a command was skipped, say why.>

## Verdict

<Pass / pass with changes / fail, with one short rationale.>
```

Severity values: `blocking`, `major`, `minor`, `nit`.

If there are no issues, say so clearly under `## Findings` and still include
residual risk or test gaps under `## Validation` / `## Verdict`.
