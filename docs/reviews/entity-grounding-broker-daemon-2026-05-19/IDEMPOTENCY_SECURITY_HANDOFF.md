author: operator

# Idempotency Security Handoff

Run: `run_ecf126b2e6234ae3b54958d8471e5e56`  
Job: `idempotency_security`  
Lane: `codex_security`  
Date: 2026-05-19

## Changed / Verified Files

- Verified: `src/engram/entity_grounding_materialization.py`
- Verified: `migrations/024_claim_grounding_runtime.sql`
- Verified: `tests/test_entity_grounding_materialization.py`
- Wrote: `docs/reviews/entity-grounding-broker-daemon-2026-05-19/IDEMPOTENCY_SECURITY_HANDOFF.md`

No source, migration, or test files were edited by this lane turn.

## Review Notes

- The materializer now excludes approved grants that already have a dispatch row
  for the same request/grant/target adapter with status `prepared`,
  `dispatched`, `succeeded`, or `failed`.
- `tests/test_entity_grounding_materialization.py` includes
  `test_approved_grant_is_not_processed_twice`, which proves a second
  materializer pass does not invoke the adapter again after the first pass.
- Existing checks still preserve the important security invariants in this
  slice: minimized adapter payload, no `source_refs` or local context in
  dispatch, provider URL filtering, review-action privacy tier carry-through,
  and sanitized provider failures.
- Migration 024 provides append-only sidecars and a unique
  `(request_id, grant_id, target_adapter, attempt_number)` dispatch index. The
  new retry policy is application-level: a retry requires a new approved grant,
  not another pass over the same grant.

## Commands / Results

- `STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 .venv/bin/striatum --repo . ack --session-id sess_7d0666f1e3a94fc591f1f242a56305b1 --message-id msg_7344ceccc1e44f6b964c6bdaf28fe96d --lease-id lease_24eaa84225534306a197b4ab0cd7a524 --json`
  - Result: passed.
- `DB=engram_test_idempotency_security_$$; createdb -T engram_test "$DB" && ENGRAM_TEST_DATABASE_URL="postgresql:///$DB" .venv/bin/python -m pytest -vv tests/test_entity_grounding_materialization.py; rc=$?; dropdb "$DB" >/dev/null 2>&1 || true; exit $rc`
  - Result: passed, `16 passed in 33.64s`.
- `.venv/bin/python -m ruff check src/engram/entity_grounding_materialization.py tests/test_entity_grounding_materialization.py`
  - Result: passed, `All checks passed!`.

## Residual Risks

- Crash durability is still weaker than the logical idempotency rule. The
  `prepared` dispatch row and provider call are in the caller-owned transaction;
  if the daemon calls the provider and crashes before commit, the audit row can
  roll back and a later daemon pass can dispatch the same approved grant again.
- Concurrency is mostly protected by daemon-level advisory locking plus the
  dispatch attempt unique index, but `process_approved_grounding_grants` itself
  has no explicit `FOR UPDATE SKIP LOCKED` claim. Direct concurrent callers may
  block or raise on the unique attempt insert rather than returning a clean
  skipped result.
- Failed or stale `prepared` rows block retry forever for that grant, by design.
  Operator docs should state that retry requires issuing a new approved grant
  and should describe how to inspect old `prepared` / `failed` audit rows.
