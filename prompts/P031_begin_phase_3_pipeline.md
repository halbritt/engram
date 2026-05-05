# P031: Begin Phase 3 Pipeline

> Prompt ordinal: P031. Introduced: pending first commit. Source commit: pending.

## Role

Preferred model: Codex GPT-5.5.

You are the Phase 3 pipeline operator. Start only a bounded local smoke run
unless the owner explicitly approves a full-corpus run.

## Wait For

Wait until:

```text
docs/reviews/phase3/markers/10_BUILD_REVIEW_SYNTHESIS.ready.md
```

exists.

## Read First

1. `docs/reviews/phase3/markers/10_BUILD_REVIEW_SYNTHESIS.ready.md`
2. `docs/reviews/phase3/PHASE_3_BUILD_REVIEW_SYNTHESIS_2026_05_05.md`
3. `docs/claims_beliefs.md`
4. `prompts/P028_build_phase_3_claims_beliefs.md`
5. `docs/segmentation.md`
6. `ROADMAP.md`
7. `BUILD_PHASES.md`

## Task

Begin Phase 3 with the smallest useful local run:

1. Confirm worktree state and current commit.
2. Run migrations.
3. Run relevant tests.
4. Run local LLM health smoke using the Phase 3 request profile.
5. Run a bounded extraction/consolidation smoke slice using the CLI described
   by the implemented Phase 3 build.
6. Verify claims, beliefs, audit rows, contradiction behavior where applicable,
   progress rows, and failure diagnostics.
7. Stop before any full-corpus run unless the owner explicitly approves.

Write:

```text
docs/reviews/phase3/PHASE_3_PIPELINE_START_2026_05_05.md
```

Include exact commands, counts, failures, timings, and whether the system is
ready for a larger run.

## Constraints

- Local only.
- No cloud APIs, telemetry, hosted services, or external persistence.
- Do not author the gold set.
- Do not start Phase 4.
- Do not run full corpus without explicit owner approval.

## Output

Write:

- pipeline start report
- marker `docs/reviews/phase3/markers/11_PIPELINE_STARTED.ready.md`

