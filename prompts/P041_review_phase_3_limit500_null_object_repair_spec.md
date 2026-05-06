# Review Phase 3 Limit-500 Null-Object Repair Spec

You are reviewing a proposed Phase 3 operational repair spec for Engram.
Engram is local-first: do not use or request raw corpus content, prompt
payloads, model completions, conversation titles, claim values, belief values,
private names, or corpus-derived prose summaries. Use code, tests, process
docs, aggregate counts, ids, status values, predicate names, object-shape
diagnostics, and error classes only.

## Context

The bounded `pipeline-3 --limit 500` run is blocked. The blocker is a
prompt/schema/model contract failure, not an infrastructure failure.

Selected-scope facts:

- selected conversations: 500
- active segments: 723
- latest extracted segments: 593
- latest failed segments: 1
- missing latest extractions after coordinator interruption: 129
- latest claim count: 2927
- latest final dropped claims: 824
- latest validation-repair prior drops: 110
- expanded dropped gate: 24.2%
- final drops with exact-one object-channel error: 807
- validation-repair prior drops with exact-one object-channel error: 110

The failed selected-scope segment produced 28 all-invalid first-pass claims.
All had `object_text` null and `object_json` null. The validation-repair retry
then failed with invalid JSON, so the segment remained failed and downstream
consolidation correctly skipped the conversation.

## Review These Files

- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_FAILURE_FINDINGS_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT500_2026_05_06.md`
- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/process/phase-3-agent-runbook.md`

Do not modify source files or the spec. If you inspect prompt-construction code,
do not quote runtime prompt payloads or corpus-derived content.

## Review Task

Look for correctness, auditability, and operational gate problems. In
particular:

1. Does the spec preserve strict exact-one object-channel validation?
2. Does it avoid hiding model contract failures behind successful empty
   repairs?
3. Is the proposed schema repair safe given possible local JSON-schema backend
   limitations?
4. Is the null-object-sweep repair feedback specific enough while remaining
   redacted?
5. Are the test requirements sufficient for the known failure mode and likely
   regressions?
6. Does the same-bound acceptance gate prevent premature full-corpus expansion?
7. Are there missing operational steps for superseding failed rows, progress
   rows, or markers without deleting audit history?

Write your review to:

`docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_REVIEW_claude_opus_4_7_2026_05_06.md`

Also write a marker to:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/03_REPAIR_SPEC_REVIEW_claude_opus_4_7.ready.md`

If your verdict is `reject_for_revision` or `human_checkpoint`, use the same
marker path but with `.blocked.md` instead of `.ready.md`.

Use one of these verdicts: `accept`, `accept_with_findings`,
`reject_for_revision`, or `human_checkpoint`.

If you find issues, include severity, concrete file references, and the
required fix. Keep the review redacted under the rules above.
