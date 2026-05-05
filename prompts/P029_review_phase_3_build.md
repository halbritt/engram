# P029: Review Phase 3 Build

> Prompt ordinal: P029. Introduced: pending first commit. Source commit: pending.

## Role

Preferred models: Codex GPT-5.5 for code review, Gemini Pro 3.1 for broad
consistency, and Claude Opus 4.7 for architecture/evidence review.

You are reviewing the completed Phase 3 implementation. Do not patch code
directly unless the coordinator explicitly asks.

## Wait For

Wait until:

```text
docs/reviews/phase3/markers/08_BUILD_COMPLETE.ready.md
```

exists.

## Read First

1. `docs/reviews/phase3/markers/08_BUILD_COMPLETE.ready.md`
2. `prompts/P028_build_phase_3_claims_beliefs.md`
3. `docs/claims_beliefs.md`
4. `DECISION_LOG.md`
5. `BUILD_PHASES.md`
6. `docs/schema/README.md`
7. implementation diff
8. relevant tests

## Task

Write:

```text
docs/reviews/phase3/PHASE_3_BUILD_REVIEW_<model_slug>_2026_05_05.md
```

Review for:

- schema/spec mismatches,
- provenance or evidence bugs,
- raw immutability violations,
- destructive re-derivation behavior,
- missing audit rows,
- local LLM request contract drift,
- retry/resumability bugs,
- privacy-tier propagation gaps,
- insufficient tests,
- operator hazards before pipeline start.

## Constraints

- Do not start the Phase 3 pipeline.
- Do not write fixes unless assigned.
- Do not call hosted services.

## Output

Write:

- build review file
- marker `docs/reviews/phase3/markers/09_BUILD_REVIEW_<model_slug>.ready.md`

