# P046 - Synthesize Phase 3 Limit-500 Still-Invalid Repair Spec

You are a fresh Codex synthesis context. This is a spec-writing task, not a
code implementation task.

## Read First

1. `AGENTS.md`
2. `README.md`
3. `HUMAN_REQUIREMENTS.md`
4. `DECISION_LOG.md`
5. `BUILD_PHASES.md`
6. `ROADMAP.md`
7. `SPEC.md`
8. `docs/schema/README.md`
9. `docs/process/multi-agent-review-loop.md`
10. `docs/process/phase-3-agent-runbook.md`
11. `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_2026_05_06.md`
12. `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_REVIEW_claude_opus_4_7_2026_05_06.md`
13. `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_REVIEW_gemini_pro_3_1_2026_05_06.md`
14. `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_POLICY_DECISION_2026_05_06.md`

## Task

Synthesize the accepted repair spec for the Phase 3 limit-500
`validation_repair.result = still_invalid` blocker.

The owner accepted Option C, the hybrid policy:

- fully parsed, schema-valid extraction outputs that remain all-invalid after
  validation repair may become extracted zero-claim rows only when every drop
  is locally diagnosed, redacted, and included in dropped-claim accounting;
- the repair must add an explicit clean-zero versus accounted-zero
  distinction;
- parse errors, schema rejections, missing diagnostics, unredacted diagnostics,
  unknown drop reasons, and any other unauditable path remain hard failures;
- accounted-zero rows contribute zero claims to consolidation and must not be
  treated as extraction failures;
- the same-bound expanded dropped-claim quality gate remains 10% for the next
  limit-500 verification run;
- prompt/schema hardening for repeated null-object shapes may be specified as
  a focused supporting fix, but the core accepted policy is the hybrid
  accounted-zero terminal state.

## Scope

Write only these files:

1. `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_REPAIR_SPEC_2026_05_06.md`
2. `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/13_STILL_INVALID_REPAIR_SPEC.ready.md`

Do not edit source code, tests, migrations, prompts, or decision logs. Do not
run live pipeline commands. You may inspect source and tests to make the spec
precise.

## Required Spec Content

The repair spec must include:

1. Redaction boundary and related artifacts.
2. Accepted policy summary and non-goals.
3. Precise definition of "fully diagnosed" eligible all-invalid output.
4. Explicit clean-zero versus accounted-zero row distinction, including the
   preferred implementation surface.
5. Hard-failure paths that must remain `failed`.
6. Failure-kind taxonomy update for post-repair local-validation hard failures.
7. Dropped-claim quality-gate formula, including numerator, denominator,
   validation-repair prior/final drops, dedup rule, selected-scope boundary,
   and 10% threshold.
8. Consolidator behavior for accounted-zero rows.
9. Requeue/idempotence behavior for the known failed conversation.
10. Tests the builder must add or update.
11. Live verification ladder before the pinned ready marker can be written.
12. A concise builder handoff section listing files likely in scope and
    acceptance criteria.

## Redaction Rules

Follow RFC 0013:

- Do not include raw message text, segment text, prompt payloads, model
  completions, conversation titles, extracted claim values, belief values,
  private names, or corpus-derived prose summaries.
- You may include commands, counts, ids, status values, predicate names,
  object-shape diagnostics, and aggregate error classes.

## Marker

Write `13_STILL_INVALID_REPAIR_SPEC.ready.md` with front matter including:

- `loop: postbuild`
- `issue_id: 20260506_limit500_run`
- `family: repair_spec`
- `scope: phase3 pipeline-3 limit500 validation-repair still-invalid repair`
- `bound: limit500`
- `state: ready`
- `gate: ready_for_builder`
- `classes: [validation_repair_still_invalid, derived_state_policy_change, quality_gate_unverified]`
- `linked_spec: docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_REPAIR_SPEC_2026_05_06.md`
- `supersedes: docs/reviews/phase3/postbuild/markers/20260506_limit500_run/12_STILL_INVALID_POLICY_ACCEPTED.ready.md`
- `corpus_content_included: none`

## Completion

In your final response, list only:

- files written;
- any review findings accepted into the spec;
- whether you ran `git diff --check`.
