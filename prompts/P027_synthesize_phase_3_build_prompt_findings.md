# P027: Synthesize Phase 3 Build Prompt Findings

> Prompt ordinal: P027. Introduced: pending first commit. Source commit: pending.

## Role

Preferred model: Codex GPT-5.5.

You are the build-prompt synthesis owner. Your job is to make
`P028_build_phase_3_claims_beliefs.md` executable and boring.

## Wait For

Wait for the configured build-prompt review markers:

```text
docs/reviews/phase3/markers/06_BUILD_PROMPT_REVIEW_gemini_pro_3_1.ready.md
docs/reviews/phase3/markers/06_BUILD_PROMPT_REVIEW_codex_gpt5_5.ready.md
docs/reviews/phase3/markers/06_BUILD_PROMPT_REVIEW_claude_opus_4_7.ready.md
```

If the coordinator intentionally used a different reviewer set, record that.

## Read First

1. all `docs/reviews/phase3/PHASE_3_BUILD_PROMPT_REVIEW_*_2026_05_05.md`
2. `prompts/P028_build_phase_3_claims_beliefs.md`
3. `docs/claims_beliefs.md`
4. `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md`

## Task

Create:

```text
docs/reviews/phase3/PHASE_3_BUILD_PROMPT_SYNTHESIS_2026_05_05.md
```

Then update `prompts/P028_build_phase_3_claims_beliefs.md` for accepted
findings.

The synthesis must say whether P028 is ready for a fresh implementation
context.

## Constraints

- Do not implement Phase 3.
- Do not start the pipeline.

## Output

Write:

- build prompt synthesis
- updated P028 build prompt
- marker `docs/reviews/phase3/markers/07_BUILD_PROMPT_SYNTHESIS.ready.md`

