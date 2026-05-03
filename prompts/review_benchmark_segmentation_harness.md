# Review Benchmark Segmentation Harness

> Hand this to another coding/review agent on the
> `codex/benchmark-segmentation-harness` branch.
>
> Goal: review the benchmark segmentation harness skeleton added under
> `benchmarks/segmentation/`. Write findings to
> `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_REVIEW.md`.

## Read First

1. `prompts/benchmark_segmentation_harness_spec.md` - original task.
2. `docs/rfcs/0006-segmentation-model-benchmark.md` - benchmark RFC.
3. `DECISION_LOG.md`, especially D005, D034, D037, and D039.
4. `docs/segmentation.md` - deployed Phase 2 contract.
5. `benchmarks/segmentation/README.md`
6. `benchmarks/segmentation/SPEC.md`
7. `benchmarks/segmentation/fixtures/*.jsonl`
8. `benchmarks/segmentation/strategies.py`
9. `benchmarks/segmentation/scoring.py`
10. `benchmarks/segmentation/run_benchmark.py`

Read `src/engram/segmenter.py` only enough to verify that the skeleton respects
the production validation, prompt, provenance, context-budget, and placeholder
boundaries. Do not review unrelated Phase 2 runtime behavior unless the
benchmark skeleton contradicts it.

## Review Scope

Review the skeleton/specification work only:

```text
benchmarks/segmentation/
```

Use `git diff master...HEAD -- benchmarks/segmentation prompts/review_benchmark_segmentation_harness.md`
to orient yourself. The expected current shape is:

```text
benchmarks/segmentation/
  README.md
  SPEC.md
  fixtures/
    synthetic_parents.example.jsonl
    expected_claims.example.jsonl
  strategies.py
  scoring.py
  run_benchmark.py
```

## Constraints

- Do not call ik-llama, Ollama, Hugging Face, or any external service.
- Do not download public datasets.
- Do not write to the production database.
- Do not alter production migrations or Phase 2 runtime code.
- Do not implement the live benchmark runner.
- Do not expand the fixture set beyond placeholder/example shape.
- Preserve D039: P-FRAG remains deferred and must not redefine the deployed
  Phase 2 schema.

Local validation commands are allowed if they remain offline and scratch-only,
for example:

```bash
python3 -m py_compile benchmarks/segmentation/*.py
python3 -m benchmarks.segmentation.run_benchmark --help
```

You may also parse the JSONL fixtures with the standard library.

## What To Check

Prioritize bugs, spec contradictions, and missing review-critical detail:

- Does `README.md` clearly state purpose, non-goals, local-only constraint, and
  Phase 2 relationship?
- Does `SPEC.md` include all required sections from the original prompt:
  fixture schema, expected-claims schema, result schema, strategy interface,
  CLI shape, scoring plan, failure-mode handling, reproducibility metadata,
  public dataset handling rules, and open questions?
- Are all required metrics from RFC 0006 represented?
- Does the strategy interface cover current Qwen, candidate Qwen, optional
  Gemma, fixed N-token windows with overlap, and message-group segmentation?
- Do fixture examples include a header object with `fixture_version` and enough
  shape to exercise provenance, topic boundaries, tool placeholders, privacy,
  and UUID-like text traps?
- Are benchmark artifacts explicitly inactive/scratch-only by design?
- Does the spec avoid implying writes to production `segment_generations`,
  `segments`, `segment_embeddings`, or `embedding_cache`?
- Does it preserve the deployed Phase 2 `whole` / `windowed` contract instead
  of smuggling in P-FRAG schema changes?
- Are reproducibility fields complete: git commit, model path/id and SHA256,
  endpoint properties, request/prompt versions, context/max/retry/batch/ubatch,
  sampling params, CUDA/driver versions, fixture version, public dataset
  snapshot/version, and relevant `ENGRAM_SEGMENTER_*` variables?
- Are public dataset handling rules strong enough to prevent redistribution or
  production-corpus mixing?
- Do the Python stubs stay side-effect free and accurately reflect the spec?
- Are there naming, importability, packaging, or command-shape issues that will
  block a later implementation?

## Deliverable

Create or replace:

```text
docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_REVIEW.md
```

Use this structure:

```markdown
# Benchmark Segmentation Harness Review

Date: <UTC timestamp>
Reviewer: <model / agent name>
Branch: codex/benchmark-segmentation-harness

## Findings

### 1. <severity>: <title>
File/line: `<path>:<line>`

<Finding with concrete risk and why it matters.>

Recommendation:
<Specific suggested fix or clarification.>

## Non-Blocking Notes

<Optional observations that are useful but not findings.>

## Validation

<Commands run and results. If none, say why.>

## Verdict

<Pass / pass with changes / fail, with one short rationale.>
```

Severity values: `blocking`, `major`, `minor`, `nit`.

If there are no issues, say so clearly under `## Findings` and still include
residual risk or test gaps under `## Validation` / `## Verdict`.

Do not make implementation fixes in the review pass unless explicitly asked.
