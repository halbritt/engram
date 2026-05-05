# P030: Synthesize Phase 3 Build Review Findings

> Prompt ordinal: P030. Introduced: pending first commit. Source commit: pending.

## Role

Preferred model: Codex GPT-5.5.

You are the implementation review synthesis owner. Your job is to decide which
build review findings block pipeline start, apply accepted fixes, and produce a
clean handoff for the pipeline operator.

## Wait For

Wait for configured build review markers:

```text
docs/reviews/phase3/markers/09_BUILD_REVIEW_gemini_pro_3_1.ready.md
docs/reviews/phase3/markers/09_BUILD_REVIEW_codex_gpt5_5.ready.md
docs/reviews/phase3/markers/09_BUILD_REVIEW_claude_opus_4_7.ready.md
```

If the coordinator intentionally used a different reviewer set, record that.

## Read First

1. all `docs/reviews/phase3/PHASE_3_BUILD_REVIEW_*_2026_05_05.md`
2. `docs/reviews/phase3/markers/08_BUILD_COMPLETE.ready.md`
3. `docs/claims_beliefs.md`
4. `prompts/P028_build_phase_3_claims_beliefs.md`
5. implementation diff and tests

## Task

Create:

```text
docs/reviews/phase3/PHASE_3_BUILD_REVIEW_SYNTHESIS_2026_05_05.md
```

Then apply accepted blocking fixes. If a finding is deferred, record why and
whether pipeline start is still allowed.

Run the relevant test suite and schema-doc regeneration if migrations changed.

## Constraints

- Do not start the Phase 3 pipeline.
- Do not hide failing tests.
- Do not expand scope into Phase 4.

## Output

Write:

- build review synthesis
- accepted fixes
- marker `docs/reviews/phase3/markers/10_BUILD_REVIEW_SYNTHESIS.ready.md`

