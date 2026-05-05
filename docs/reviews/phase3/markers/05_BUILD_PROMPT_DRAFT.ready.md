# 05_BUILD_PROMPT_DRAFT.ready

Prompt: P025 - Write Phase 3 Build Prompt
Model / agent: codex_gpt5_5
Started:   2026-05-05T16:20Z
Completed: 2026-05-05T16:32Z

## Files written or modified

- `prompts/P028_build_phase_3_claims_beliefs.md` - replaced the placeholder
  with the Phase 3 implementation handoff drafted from the accepted
  `docs/claims_beliefs.md` spec and P024 synthesis.
- `docs/reviews/phase3/markers/05_BUILD_PROMPT_DRAFT.ready.md` - this marker.

## Verification performed

- Confirmed
  `docs/reviews/phase3/markers/04_SPEC_SYNTHESIS.ready.md` exists.
- Also confirmed the later same-model synthesis re-review ready marker,
  `docs/reviews/phase3/markers/04_SPEC_SYNTHESIS_REVIEW_codex_gpt5_5.ready.md`,
  exists, and read the rerun review's `accept_with_findings` handoff.
- Ran `git status --short` before writing and observed an already-dirty
  worktree. Writes were limited to the requested prompt and this marker.
- Read the P024 synthesis marker, synthesis document, accepted Phase 3 spec,
  canonical decision/phase/roadmap/spec/schema docs, Phase 2 segmenter,
  embedder, progress and CLI code, migration `004_segments_embeddings.sql`,
  Makefile/operator patterns, and tests.
- Checked existing in-flight Phase 3 files enough to call out their known
  divergence from the amended spec in the build prompt.
- Did not implement code.
- Did not start the Phase 3 pipeline.
- Did not run the full corpus.

## Next expected marker

`06_BUILD_PROMPT_REVIEW_<model_slug>.ready.md` from the build-prompt review
fan-out.
