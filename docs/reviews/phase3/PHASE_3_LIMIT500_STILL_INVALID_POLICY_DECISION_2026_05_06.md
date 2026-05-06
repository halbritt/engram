# Phase 3 Limit-500 Still-Invalid Policy Decision

Date: 2026-05-06

Status: `owner_accepted`

Decision: accept Option C, the hybrid policy.

Related artifacts:

- `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_REVIEW_claude_opus_4_7_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_REVIEW_gemini_pro_3_1_2026_05_06.md`
- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/11_STILL_INVALID_HUMAN_POLICY_CHECKPOINT.human_checkpoint.md`

## Redaction Boundary

This decision follows RFC 0013. It contains policy, status values, aggregate
error classes, and artifact paths only. It does not include raw message text,
segment text, prompt payloads, model completions, conversation titles, claim
values, belief values, private names, or corpus-derived prose summaries.

## Owner Decision

The owner accepted Option C from the reviewed problem statement.

For the repair spec, this means:

- fully parsed, schema-valid extraction outputs that remain all-invalid after
  validation repair may become extracted zero-claim rows only when every drop
  is locally diagnosed, redacted, and included in dropped-claim accounting;
- the repair must add an explicit clean-zero versus accounted-zero distinction;
- parse errors, schema rejections, missing diagnostics, unredacted diagnostics,
  unknown drop reasons, and any other unauditable path remain hard failures;
- accounted-zero rows contribute zero claims to consolidation and must not be
  treated as extraction failures;
- the same-bound expanded dropped-claim quality gate remains 10% for the next
  limit-500 verification run;
- prompt/schema hardening for repeated null-object shapes may be specified as
  a focused supporting fix, but the core accepted policy is the hybrid
  accounted-zero terminal state.

## Binding Decision Log Entry

Recorded as:

- `D064`

## Required Next Step

Start a fresh Codex context to synthesize the repair spec from:

- the problem description;
- Claude and Gemini reviews;
- this owner decision;
- RFC 0013 and the Phase 3 post-build operational loop.

Builder execution remains blocked until the synthesized repair spec exists.
