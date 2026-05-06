# P047 - Build Phase 3 Limit-500 Still-Invalid Repair

You are the builder for the Phase 3 limit-500 still-invalid repair. Implement
the accepted spec. This is a code and test task.

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
11. `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_REPAIR_SPEC_2026_05_06.md`

## Task

Implement D064 / Option C hybrid accounted-zero behavior:

- fully parsed, schema-valid extraction outputs that remain all-invalid after
  validation repair become extracted zero-claim rows only when every drop is
  locally diagnosed, redacted, and counted;
- clean-zero and accounted-zero extraction rows must be queryably distinct;
- parse errors, schema rejection, repair failures, missing diagnostics,
  unredacted diagnostics, unknown drop reasons, unknown/unbounded error
  classes, and other unauditable paths remain hard failures;
- accounted-zero rows contribute zero claims to consolidation and must not
  cause skip-due-to-extraction-failure behavior;
- expanded dropped-claim accounting must include validation-repair prior drops
  and final drops according to the spec;
- keep the 10% same-bound dropped-claim gate unchanged.

## Scope

Likely files in scope:

- `src/engram/extractor.py`
- `src/engram/cli.py`
- `src/engram/consolidator/__init__.py`
- `tests/test_phase3_claims_beliefs.py`
- `docs/claims_beliefs.md`

Only add a migration and regenerate schema docs if you choose a first-class
column instead of the preferred `raw_payload.extraction_result_kind` field.
Prefer the `raw_payload` implementation unless source inspection shows it is
not enough.

Do not run live pipeline commands. Live gates happen after implementation
review. You may run local tests.

## Required Implementation Points

1. Bump extractor provenance versions for this repair.
2. Set `raw_payload.extraction_result_kind` to one of:
   - `populated`
   - `clean_zero`
   - `accounted_zero`
3. Ensure mixed valid+invalid extractions with inserted claims are `populated`.
4. Ensure empty extractions with no drops are `clean_zero`.
5. Ensure validation repair that returns empty after prior drops is
   `accounted_zero`.
6. Ensure fully diagnosed `still_invalid` post-repair rows are
   `status='extracted'`, `claim_count=0`, `failure_kind=null`, and
   `extraction_result_kind='accounted_zero'`.
7. Keep hard failures for ineligible still-invalid cases and use a precise
   failure kind such as `local_validation_failed_post_repair`.
8. Add helper logic for eligible/known redacted drop diagnostics rather than
   ad hoc checks at each call site.
9. Add or expose a dropped-claim gate helper matching the spec formula, with
   tests.
10. Preserve RFC 0013 redaction discipline in any new persisted diagnostics.

## Required Tests

Add/update focused tests for:

- fully diagnosed still-invalid -> extracted accounted-zero;
- initial empty extraction -> clean-zero;
- repair returns empty after prior drops -> accounted-zero;
- populated extraction with drops -> populated;
- still-invalid with unknown drop reason -> failed;
- still-invalid with unknown/unbounded error class -> failed;
- still-invalid with missing counts/count mismatch -> failed;
- still-invalid with unredacted diagnostic -> failed;
- parse error remains failed;
- schema rejection remains failed;
- validation-repair parse/schema/service failure remains failed;
- hard-failed post-repair local-validation uses the new failure kind, not
  `trigger_violation`;
- dropped-claim gate helper computes prior/final/inserted counts and rate
  exactly;
- accounted-zero does not increment extractor failed counts;
- pipeline does not skip consolidation solely because of accounted-zero rows;
- targeted consolidation over accounted-zero rows completes with zero
  contribution.

Update the existing all-invalid failure test rather than deleting it.

## Verification

Run at least:

```bash
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q
make test
git diff --check
```

If any command cannot be run, explain why in your final response.

## Completion

Before final response:

- write or update a marker:
  `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/14_STILL_INVALID_REPAIR_BUILT.ready.md`
- marker front matter must include:
  - `loop: postbuild`
  - `issue_id: 20260506_limit500_run`
  - `family: repair_implementation`
  - `scope: phase3 pipeline-3 limit500 validation-repair still-invalid repair`
  - `bound: limit500`
  - `state: ready`
  - `gate: ready_for_implementation_review`
  - `classes: [validation_repair_still_invalid, derived_state_policy_change, quality_gate_unverified]`
  - `linked_spec: docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_REPAIR_SPEC_2026_05_06.md`
  - `supersedes: docs/reviews/phase3/postbuild/markers/20260506_limit500_run/13_STILL_INVALID_REPAIR_SPEC.ready.md`
  - `corpus_content_included: none`

Final response must list:

- files changed;
- tests run and results;
- any deviations from the spec.
