# 06_BUILD_PROMPT_REVIEW_claude_opus_4_7.ready

Prompt: P026 — Review Phase 3 Build Prompt
Model / agent: claude_opus_4_7 (fresh context for this pass)
Started:   2026-05-05T16:33Z
Completed: 2026-05-05T16:48Z

## Verdict

`accept_with_findings` — see review file for the full findings list.

## Files written

- `docs/reviews/phase3/PHASE_3_BUILD_PROMPT_REVIEW_claude_opus_4_7_2026_05_05.md`
  — full review with 20 findings (3 P0, 9 P1, 5 P2, 3 P3) plus a
  privacy / full-corpus risk summary and a list of pinned items the
  P027 build-prompt synthesis should fold in.
- `docs/reviews/phase3/markers/06_BUILD_PROMPT_REVIEW_claude_opus_4_7.ready.md`
  — this marker.

## Inputs read

- `prompts/P028_build_phase_3_claims_beliefs.md` (the build prompt under
  review).
- `docs/claims_beliefs.md` (binding spec, build-ready after P024
  synthesis).
- `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md`.
- `DECISION_LOG.md` (D048–D058).
- `BUILD_PHASES.md` (Phase 3 acceptance block).
- `ROADMAP.md` (Step 4C).
- `docs/schema/README.md` (current Phase 2 schema).
- `docs/reviews/phase3/markers/05_BUILD_PROMPT_DRAFT.ready.md`.
- Existing in-flight scaffolding (file sizes only, not read line-by-line):
  `src/engram/extractor.py`, `src/engram/consolidator.py`,
  `migrations/006_claims_beliefs.sql`,
  `tests/test_phase3_claims_beliefs.py`.

## Constraints honored

- Did not patch the build prompt.
- Did not implement code.
- Did not start the pipeline.
- Ran `git status --short` before writing; only added the review file
  and this marker. The dirty worktree was already dirty from earlier
  Phase 3 review-loop work and was not touched.

## Top-3 P0 findings

1. **F1 — `request_profile_version` suffix is a hidden architecture
   choice.** Build prompt locks `ik-llama-json-schema.d034.v2.extractor-8192`
   but the spec leaves the suffix open. The string is forensically
   load-bearing.
2. **F2 — GUC scoping is permissive.** "Clear or scope the GUC" allows a
   session-scoped `SET` that survives commit/rollback and bypasses the
   audit-pairing invariant. Should be `SET LOCAL` with a test asserting
   GUC absence after the transition.
3. **F3 — Direct SQL INSERT on `beliefs` is not gated.** Trigger blocks
   DELETE and UPDATE-without-GUC, but INSERT can bypass the API and
   produce un-audited belief rows. Build prompt should make the choice
   explicit (gate INSERT with GUC, or document the gap).

## Next expected marker

The remaining model reviewers (Codex GPT-5.5 and Gemini Pro 3.1) write
their own `06_BUILD_PROMPT_REVIEW_<slug>.ready.md` markers. After all
three reviews land, the synthesis produces

```text
docs/reviews/phase3/markers/07_BUILD_PROMPT_SYNTHESIS.ready.md
```

which is the gate the implementer of P028 waits for.
