# Phase 3 D063 Limit50 Validation-Repair Review

Date: 2026-05-05
Reviewer: Codex GPT-5.5
Verdict: `reject_for_revision`

This review stayed within the redaction boundary: code, tests, process docs,
aggregate counts, status values, ids, and error classes only. I did not inspect
raw corpus content, runtime prompt payloads, model completions, conversation
titles, claim values, or belief values.

## Scope Reviewed

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/process/phase-3-agent-runbook.md`
- Marker behavior only as needed to answer the requested ready-marker question.

## Findings

### Major: successful validation repair hides the initial all-invalid response from the dropped-claim gate

`src/engram/extractor.py:492` through `src/engram/extractor.py:504` correctly
detects the D058 full-salvage-failure case and enters validation repair only
when zero claims survived and local validation errors exist. The repair path at
`src/engram/extractor.py:860` through `src/engram/extractor.py:879` then
returns only the repaired attempt's surviving claims and repaired-attempt drops.
On success, `src/engram/extractor.py:543` through `src/engram/extractor.py:548`
persists `raw_payload.dropped_claims` from the repaired attempt only.

The new test pins that behavior: `tests/test_phase3_claims_beliefs.py:638`
through `tests/test_phase3_claims_beliefs.py:647` asserts an empty successful
repair has `dropped_claims == []` and stores the initial validation failures
only as aggregate `validation_repair.prior_*` counts.

That is enough to explain a local repair, but it is not enough for D058/RFC 0013
auditability. D058 says invalid emitted claims are dropped with structured
diagnostics, and RFC 0013 makes prompt/model contract failures and dropped-claim
rate default blockers (`docs/rfcs/0013-development-operational-issue-loop.md:281`
through `docs/rfcs/0013-development-operational-issue-loop.md:289`). If
operational proof queries count only `raw_payload.dropped_claims`, a repaired
all-invalid first response no longer contributes to the dropped-claim gate. That
can make repeated model contract failures disappear from the selected-scope
rate even though the local model needed repair retries to pass.

Required fix:

- Persist repair-attempt diagnostics in a queryable, redacted-safe shape. Either
  carry initial-attempt drops into `raw_payload.dropped_claims` with an
  `attempt`/`phase` field, or add a dedicated
  `raw_payload.validation_repair.prior_dropped_claims`/redacted equivalent that
  preserves per-claim error class, index, predicate, object-channel shape, and
  evidence id count without claim object values.
- Update the selected-scope dropped-claim gate/report query to count validation
  repair prior drops, or add a separate reported validation-repair attempt
  count/rate that is explicitly considered by the RFC 0013 gate.
- Update tests so successful empty repair and successful valid repair both
  preserve/query the initial validation-failure diagnostics. Also assert the
  still-invalid repair path records `result: still_invalid` and remains failed.

This does not require relaxing the validator. The retry can still return valid
claims or an empty claim list, and the extraction can still be `extracted` when
the repaired final output has no remaining validation errors. The missing piece
is retaining and counting the contract failure that triggered the repair.

### Minor: retry count semantics are not pinned for non-default extractor retries

The intended repair is "call the local extractor once more." The current repair
path passes `retries=max(0, retries - 1)` at `src/engram/extractor.py:832`
through `src/engram/extractor.py:839`; because the lower-level retry loop runs
`retries + 1` attempts, non-default `ENGRAM_EXTRACTOR_RETRIES` values can make
the validation-repair pass perform more than one repair attempt per chunk. The
default setting still produces one extra attempt, and the existing test at
`tests/test_phase3_claims_beliefs.py:626` through
`tests/test_phase3_claims_beliefs.py:629` covers that default case.

Required fix:

- If the contract is exactly one validation-repair attempt, pass `retries=0` for
  the repair pass and add a test with `retries > 1` proving the repair is not
  retried after a repair-specific parse/runtime failure.
- If transport retries are intentionally allowed inside the repair pass, document
  that distinction in the extractor comments or runbook and record successful
  repair-attempt retry diagnostics so operational review can see that the repair
  was not a single clean pass.

## Answers To Review Questions

1. D058 salvage semantics are mostly preserved for final insertion: partial
   salvage still commits valid claims, zero valid claims plus errors still
   fails, and an originally invalid extraction can become a successful empty
   extraction after repair. The audit trail is incomplete for successful repair
   because initial dropped-claim diagnostics are not persisted as dropped claims.

2. Yes, as written it can hide repaired model contract failures from RFC 0013
   gates that count only latest `dropped_claims`. The raw row has aggregate
   repair metadata, but the gate/report contract needs that data counted.

3. Retry diagnostics are close but insufficient for redacted operational review.
   `prior_dropped_count`, `prior_error_counts`, `final_dropped_count`, and
   `final_error_counts` are useful. Redacted per-claim diagnostics or an
   explicit repair-attempt gate are still needed to audit what was repaired
   without exposing claim values.

4. Tests cover default empty-success repair and existing failure behavior, but
   they do not cover successful valid repair, still-invalid repair metadata,
   repair parse/runtime failure metadata, or non-default retry-count semantics.

5. It is not safe to supersede the prior limit50 blocked marker yet because the
   dropped-claim/process gate is not fully auditable. After the finding above is
   fixed, verified, and rerun, a ready marker can supersede the blocked marker
   only if it uses the same `issue_id` and `family` as the blocked marker and
   explicitly names
   `docs/reviews/phase3/postbuild/markers/20260505_limit50_run/01_RUN.blocked.md`
   in `supersedes`, per RFC 0013 marker precedence
   (`docs/rfcs/0013-development-operational-issue-loop.md:194` through
   `docs/rfcs/0013-development-operational-issue-loop.md:198`). That marker
   should not be treated as authorization for a larger corpus run; the runbook
   still requires an owner checkpoint after `pipeline-3 --limit 50`
   (`docs/process/phase-3-agent-runbook.md:220` through
   `docs/process/phase-3-agent-runbook.md:233`).

## Verification Reviewed

I reviewed the reported verification results:

- Phase 3 focused tests: `36 passed`
- Full test suite: `121 passed`
- targeted extraction rerun: exit `0`, no failed segments
- `pipeline-3 --limit 0`: exit `0`
- same-bound `pipeline-3 --limit 50`: exit `0`
- selected-scope proof: no latest failed segments, no missing latest
  extractions, no failed progress rows, no active orphan claim ids, reported
  latest dropped-claim rate below 10%

Those results are promising, but the reported dropped-claim gate must include
validation-repair prior drops before the marker can safely move to ready.
