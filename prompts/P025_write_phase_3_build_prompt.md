# P025: Write Phase 3 Build Prompt

> Prompt ordinal: P025. Introduced: pending first commit. Source commit: pending.

## Role

Preferred model: Codex GPT-5.5.

You are the build-prompt author. Your job is to turn the accepted Phase 3 spec
into an execution handoff for a fresh implementation context.

## Wait For

Wait until:

```text
docs/reviews/phase3/markers/04_SPEC_SYNTHESIS_REVIEW_codex_gpt5_5.ready.md
```

exists.

## Read First

1. `docs/reviews/phase3/markers/04_SPEC_SYNTHESIS.ready.md`
2. `docs/reviews/phase3/markers/04_SPEC_SYNTHESIS_REVIEW_codex_gpt5_5.ready.md`
3. `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md`
4. the review file named by the synthesis re-review ready marker
5. `docs/claims_beliefs.md`
6. `DECISION_LOG.md`
7. `BUILD_PHASES.md`
8. `ROADMAP.md`
9. `SPEC.md`
10. `docs/schema/README.md`
11. `src/engram/segmenter.py`
12. `src/engram/embedder.py`
13. `src/engram/progress.py`
14. `src/engram/cli.py`
15. `migrations/004_segments_embeddings.sql`
16. `tests/`

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
