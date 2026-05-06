---
loop: postbuild
issue_id: 20260506_limit500_run
family: human_checkpoint
scope: phase3 pipeline-3 limit500 validation-repair still-invalid policy
bound: limit500
state: human_checkpoint
gate: blocked_for_owner_policy_choice
classes: [validation_repair_still_invalid, derived_state_policy_change, quality_gate_unverified]
created_at: 2026-05-06T06:20:11Z
linked_problem: docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_2026_05_06.md
linked_reviews:
  - docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_REVIEW_claude_opus_4_7_2026_05_06.md
  - docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_REVIEW_gemini_pro_3_1_2026_05_06.md
corpus_content_included: none
---

# Phase 3 Limit-500 Still-Invalid Human Policy Checkpoint

Independent reviews are complete.

Verdicts:

- Claude Opus 4.7: `accept_with_findings`
- Gemini Pro 3.1: `human_checkpoint`

Both reviewers recommend Option C, the hybrid policy:

- convert fully parsed, fully redacted, fully diagnosed post-repair
  all-invalid outputs into extracted zero-claim rows;
- keep hard failure for parse errors, schema rejection, missing diagnostics,
  unredacted diagnostics, unknown drop reasons, or any unauditable path;
- continue to enforce the 10% same-bound dropped-claim quality gate.

Owner decision required before Codex synthesis:

1. Confirm or amend Option C as the repair policy.
2. Decide whether the spec must introduce an explicit clean-zero versus
   accounted-zero indicator.
3. Decide whether to hold the 10% dropped-claim gate unchanged for the next
   same-bound run.
4. Decide whether prompt/schema tightening for the repeated `has_name`
   null-object shape is in scope for this repair or a follow-up.

Codex synthesis and builder execution remain blocked until this checkpoint is
resolved.
