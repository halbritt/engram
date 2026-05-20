# RFC 0053 Grant Lifecycle Handoff

## Summary

Implemented append-only grant lifecycle helpers in
`src/engram/claim_grounding_runtime.py`:

- `record_claim_grounding_draft_grant`
- `record_claim_grounding_approved_grant`
- `record_claim_grounding_denied_grant`
- `record_claim_grounding_revoked_grant`
- `verify_claim_grounding_grant_for_dispatch`

Dispatch recording now verifies the latest persisted grant row is approved,
unexpired, target-authorized, and bound to the exact request/query/privacy
lineage before inserting an outbound-attempt audit row.

## Verification

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_claim_grounding_runtime.py`
- `.venv/bin/python -m py_compile src/engram/claim_grounding_runtime.py tests/test_claim_grounding_runtime.py`
