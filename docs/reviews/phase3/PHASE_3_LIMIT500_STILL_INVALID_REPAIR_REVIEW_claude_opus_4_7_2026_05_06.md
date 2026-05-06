# Phase 3 Limit-500 Still-Invalid Repair Review - claude_opus_4_7

Reviewer: claude_opus_4_7
Date: 2026-05-06
Verdict: accept_with_findings

## Summary

The implementation in `src/engram/extractor.py` faithfully implements D064
Option C: a narrow accounted-zero terminal state behind an eligibility
predicate, with redacted-at-storage diagnostics, a closed accounting-failure
taxonomy, and gate-accounting helpers. Prompt/profile versions bumped to
`v8.d064.accounted-zero` / `v10.extractor-8192-accounted-zero`. Test additions
cover the primary success path, ineligibility branches, and
pipeline/consolidator integration. Two minor observations and one
documentation/coverage gap follow; none should block the smoke gate.

## Findings

### F1 - minor: `failure_kind` default of `trigger_violation` survives if `validation_repair` is ever absent in the all-invalid path

In `extract_claims_from_segment`, the all-invalid block initializes
`payload["failure_kind"] = "trigger_violation"` before consulting
validation-repair state. The spec's failure-kind taxonomy says
`trigger_violation` is reserved for the database trigger backstop or per-drop
reasons, not for the post-repair all-invalid hard-failure class.

In current control flow, `retry_after_trigger_violation` always populates
`parse_metadata.validation_repair`, so the still-invalid or failed branches
overwrite the default. However, a future flag or refactor could persist the
wrong failure kind.

Suggested fix: change the default to
`local_validation_failed_post_repair` or assert `repair is not None`.

### F2 - minor: Initial-attempt all-invalid with no dropped diagnostics becomes clean-zero

If `dropped` is empty after the initial attempt, the retry guard is skipped and
the row persists as `clean_zero`. This matches the spec: clean-zero means zero
inserted claims and zero counted drops.

No change requested. Reviewers should verify during the live run that this does
not hide a third class where the model emits an empty list despite expected
claims.

### F3 - minor: Gate helper is unit-tested but not wired to a selected-scope row reader

The new gate helper is unit-tested arithmetically, but no test demonstrates an
end-to-end selected-scope reader that loads the latest current-version rows for
active selected segments and computes the rate.

This is acceptable for this commit because the repair scope is row-level
behavior plus accounting primitives. The same-bound verification report should
make clear how selected-scope gate evidence was computed.

## Verified Spec Compliance

- Eligibility predicate requires `attempted=true`, `result='still_invalid'`,
  required counts/arrays, count parity, error-count parity, closed reason, and
  closed error class.
- Redacted drop keys match the spec boundary, and
  `parse_metadata.chunk_dropped_claims` is recursively redacted for
  all-invalid accounted-zero and hard-failure rows.
- `extraction_result_kind` distinguishes `populated`, `clean_zero`, and
  `accounted_zero` for extracted rows.
- Accounted-zero rows have `failure_kind=null` and supersede older extracted
  rows in the same transaction.
- Ineligible post-repair local-validation failures use
  `local_validation_failed_post_repair` plus closed `accounting_failure_kind`
  values.
- Dropped-claim accounting reads validation-repair counts when present and does
  not double-count final drops.
- Accounted-zero rows do not increment extractor failed counts and do not cause
  pipeline consolidation skip behavior.

## Tests Reviewed

Reviewed coverage includes:

- fully diagnosed still-invalid extraction to accounted-zero;
- unknown reason, count mismatch, unredacted diagnostics, missing diagnostics,
  and unknown error class remaining failed;
- repair parse/schema/service failures remaining failed;
- initial schema rejection remaining failed;
- empty extraction becoming clean-zero;
- repair-empty-after-prior-drop becoming accounted-zero;
- dropped-claim gate arithmetic;
- accounted-zero not counted as extractor failure;
- pipeline not skipping consolidation for accounted-zero;
- targeted consolidation over accounted-zero rows completing with zero
  contribution.

Reported verification:

- focused Phase 3 tests passed;
- full test suite passed;
- `git diff --check` passed.

## Redaction Review

No redaction drift found in tracked diagnostics. The implementation stores
redacted drop shape diagnostics for accounted-zero and all-invalid hard-failure
rows, including the previously risky `parse_metadata.chunk_dropped_claims`
path.

## Recommendation

Proceed to the smoke gate after addressing F1 or accepting it as a minor
follow-up. F2 and F3 should be observed during the targeted and same-bound
verification reports.
