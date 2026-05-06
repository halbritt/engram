# Phase 3 Limit-500 Still-Invalid Repair Review Synthesis

Date: 2026-05-06

Reviewed artifact:

- `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_REPAIR_REVIEW_claude_opus_4_7_2026_05_06.md`

## Summary

Claude returned `accept_with_findings` and recommended proceeding to smoke.
All findings were minor.

## Finding Disposition

| Finding | Disposition | Action |
| --- | --- | --- |
| F1 - default all-invalid `failure_kind` could remain `trigger_violation` if validation-repair metadata were absent | accepted | Updated the default hard-failure kind to `local_validation_failed_post_repair` before review-gate completion. |
| F2 - clean-zero can still represent model-emitted empty output with no drops | accepted as live-run observation | No code change. Targeted and same-bound reports should note clean-zero/accounted-zero counts. |
| F3 - gate helper not wired to selected-scope row reader | accepted as live verification requirement | No code change before smoke. Same-bound report must show the selected-scope query/evidence used for the 10% gate. |

## Decision

The implementation review does not block smoke or live bounded verification.
Proceed with the RFC 0013 ladder:

1. focused tests;
2. full tests;
3. no-work `pipeline-3 --limit 0`;
4. targeted extraction rerun;
5. bounded targeted consolidation;
6. same-bound limit-500 rerun only if prior gates pass.
