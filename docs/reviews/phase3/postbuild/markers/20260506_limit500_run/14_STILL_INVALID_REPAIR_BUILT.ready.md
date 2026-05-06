---
loop: postbuild
issue_id: 20260506_limit500_run
family: repair_implementation
scope: phase3 pipeline-3 limit500 validation-repair still-invalid repair
bound: limit500
state: ready
gate: ready_for_implementation_review
classes: [validation_repair_still_invalid, derived_state_policy_change, quality_gate_unverified]
created_at: 2026-05-06T07:04:11Z
linked_spec: docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_REPAIR_SPEC_2026_05_06.md
supersedes: docs/reviews/phase3/postbuild/markers/20260506_limit500_run/13_STILL_INVALID_REPAIR_SPEC.ready.md
corpus_content_included: none
---

# Phase 3 Limit-500 Still-Invalid Repair Built

D064 Option C accounted-zero behavior has been implemented for Phase 3 claim
extraction and covered by focused tests.

Files changed:

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`
- `docs/claims_beliefs.md`
- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/14_STILL_INVALID_REPAIR_BUILT.ready.md`

Verification performed:

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q`
- `make test`
- `PYTHONPATH=src python3 -m py_compile src/engram/extractor.py src/engram/cli.py src/engram/consolidator/__init__.py tests/test_phase3_claims_beliefs.py`
- `git diff --check`

Coordinator review fix before implementation review:

- tightened accounted-zero eligibility to require redacted object-shape fields;
- redacted `parse_metadata.chunk_dropped_claims` for all-invalid accounted-zero
  and hard-failure rows before persistence;
- reran focused Phase 3 tests and full tests after the fix.

Live pipeline commands were not run in this build step.
