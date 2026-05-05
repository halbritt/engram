# P026: Review Phase 3 Build Prompt

> Prompt ordinal: P026. Introduced: pending first commit. Source commit: pending.

## Role

Preferred models: Gemini Pro 3.1, Claude Opus 4.7 fresh context, and Codex
GPT-5.5.

You are reviewing the Phase 3 build prompt before implementation starts. Do not
edit the prompt directly.

## Wait For

Wait until:

```text
docs/reviews/phase3/markers/05_BUILD_PROMPT_DRAFT.ready.md
```

exists.

## Read First

1. `prompts/P028_build_phase_3_claims_beliefs.md`
2. `docs/claims_beliefs.md`
3. `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md`
4. `DECISION_LOG.md`
5. `BUILD_PHASES.md`
6. `ROADMAP.md`
7. `docs/schema/README.md`
8. existing Phase 1/2 code and tests only as needed

## Task

Write:

```text
docs/reviews/phase3/PHASE_3_BUILD_PROMPT_REVIEW_<model_slug>_2026_05_05.md
```

Review for:

- missing implementation tasks,
- hidden architecture decisions not settled by the spec,
- unsafe migration or mutation instructions,
- inadequate tests,
- local-first/privacy violations,
- full-corpus run risks,
- ambiguity a fresh implementation context would trip over.

## Constraints

- Do not patch the build prompt.
- Do not implement code.
- Do not start the pipeline.

## Output

Write:

- build prompt review file
- marker `docs/reviews/phase3/markers/06_BUILD_PROMPT_REVIEW_<model_slug>.ready.md`

