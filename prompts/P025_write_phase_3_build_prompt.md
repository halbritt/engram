# P025: Write Phase 3 Build Prompt

> Prompt ordinal: P025. Introduced: pending first commit. Source commit: pending.

## Role

Preferred model: Codex GPT-5.5.

You are the build-prompt author. Your job is to turn the accepted Phase 3 spec
into an execution handoff for a fresh implementation context.

## Wait For

Wait until:

```text
docs/reviews/phase3/markers/04_SPEC_SYNTHESIS.ready.md
```

exists.

## Read First

1. `docs/reviews/phase3/markers/04_SPEC_SYNTHESIS.ready.md`
2. `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md`
3. `docs/claims_beliefs.md`
4. `DECISION_LOG.md`
5. `BUILD_PHASES.md`
6. `ROADMAP.md`
7. `SPEC.md`
8. `docs/schema/README.md`
9. `src/engram/segmenter.py`
10. `src/engram/embedder.py`
11. `src/engram/progress.py`
12. `src/engram/cli.py`
13. `migrations/004_segments_embeddings.sql`
14. `tests/`

## Task

Update `prompts/P028_build_phase_3_claims_beliefs.md` into the actual build
prompt.

It must include:

- exact scope and non-goals,
- files/modules likely to change,
- migration naming,
- schema-doc regeneration rule,
- CLI/operator commands,
- local LLM request profile,
- failure/resumability behavior,
- test plan,
- acceptance criteria,
- "do not run full corpus" boundary,
- marker to write after implementation.

## Constraints

- Do not implement code.
- Do not start Phase 3 pipeline.
- Do not relax local-only/no-egress constraints.

## Output

Write:

- updated `prompts/P028_build_phase_3_claims_beliefs.md`
- marker `docs/reviews/phase3/markers/05_BUILD_PROMPT_DRAFT.ready.md`

