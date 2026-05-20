# RFC 0053 Credential Security Handoff

## Summary

Added `tests/test_claim_grounding_security.py`, a PostgreSQL role-scoped
security regression for a future broker credential. The test role can read only
minimized claim-grounding requests/grants, insert only bounded dispatch,
grant-use, and grounding-evidence rows, and cannot read raw corpus tables such
as `messages`, `segments`, `claims`, or `beliefs`.

The test skips when the local database user cannot create or switch roles.

## Verification

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -q tests/test_claim_grounding_security.py`
- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -q tests/test_claim_grounding_security.py tests/test_claim_grounding_runtime.py tests/test_claim_grounding_broker.py`
