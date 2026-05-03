# Benchmark Segmentation Harness Spec Prompt

You are working in the Engram repo.

Task: turn RFC 0006 into a concrete benchmark harness skeleton and
implementation specification. Do **not** implement the live benchmark runner
yet.

## Read First

1. `docs/rfcs/0006-segmentation-model-benchmark.md`
2. `DECISION_LOG.md`, especially D005, D034, D037, D039
3. `docs/segmentation.md`
4. `src/engram/segmenter.py` only enough to understand reusable validation,
   prompt, and provenance boundaries

## Goal

Create a reviewable skeleton under:

```text
benchmarks/
  segmentation/
```

## Expected Outputs

1. `benchmarks/segmentation/README.md`
   - Explain purpose, non-goals, local-only constraint, and how this benchmark
     relates to Phase 2 without mutating production state.
   - State that initial work is spec/skeleton only.

2. `benchmarks/segmentation/SPEC.md`
   - Fixture schema
   - Expected-claims schema
   - Result schema
   - Strategy interface
   - CLI shape
   - Scoring plan
   - Failure-mode handling
   - Reproducibility metadata requirements
   - Public dataset handling rules
   - Open questions for review

3. `benchmarks/segmentation/fixtures/`
   - Add placeholder/example fixture files only, enough to show the intended
     shape.
   - Do not create a large fixture set.
   - Include a header object with `fixture_version`.

4. Optional lightweight stubs if useful:
   - `benchmarks/segmentation/strategies.py`
   - `benchmarks/segmentation/scoring.py`
   - `benchmarks/segmentation/run_benchmark.py`

## Constraints

- Do not call ik-llama, Ollama, Hugging Face, or any external service.
- Do not alter production migrations or Phase 2 runtime code.
- Do not write to the production database.
- Do not add heavyweight dependencies.
- Keep all benchmark outputs inactive / scratch-only by design.
- Preserve D039: P-FRAG is deferred and must not redefine the deployed Phase 2
  schema.
- Prefer clear specifications over premature implementation.

## Design Expectations

The harness must be able to compare:

- current Qwen profile
- another Qwen candidate
- Gemma candidate if configured
- fixed N-token windows with overlap
- message-group segmentation

Metrics must include:

- valid JSON/schema/provenance rates
- unknown/cross-parent message id counts
- empty embeddable segment count
- sub-floor fragment counts at 50/100/200 estimated tokens
- timeout/runaway count
- throughput/VRAM/backend error classes
- strict boundary precision/recall
- window-tolerant F1
- P_k
- WindowDiff
- claim precision/recall under a fixed benchmark-only extractor prompt

Reproducibility metadata must include:

- git commit
- model path/id and SHA256
- endpoint version/properties
- request profile and prompt versions
- context window/max tokens/retry max tokens/batch/ubatch
- sampling params
- CUDA/driver versions
- fixture version
- public dataset snapshot/version if used
- relevant `ENGRAM_SEGMENTER_*` environment variables

## Deliverable Style

- Keep the skeleton small and reviewable.
- Use concrete JSONL examples where helpful.
- Include enough detail that another robot can implement from the spec after
  review.
- At the end, summarize files created/changed and list the main open questions
  you want reviewers to answer.
