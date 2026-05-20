# RFC 0054/0055 Verification

Run: `run_8be1d202659a4fd093998367cf61495d`  
Lane: `codex_verification`  
Role: reviewer  
Date: 2026-05-19

## Summary

Focused RFC 0054/0055 entity-grounding workflow, materialization, and CLI tests
passed. The runtime e2e gate passed when rerun against an isolated test database
cloned from the pre-provisioned `engram_test` database.

The verification is not fully clean: broad ruff over touched Python files fails
on an import-order issue in an adjacent touched test file, and pyright over the
relevant touched source/test set fails on existing environment/type issues
including missing `uvicorn`/`pytest` imports and test typing errors. The
RFC0054/0055-specific ruff subset and core source pyright subset passed.

## Commands And Results

### Striatum Lifecycle

- `STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 .venv/bin/striatum --repo . register-session --run-id run_8be1d202659a4fd093998367cf61495d --lane codex_verification --role reviewer --capability review --fresh --json`
  - Result: passed; registered session `sess_3aa3648e67364b8b95746dd268f7958a`.
- `STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 .venv/bin/striatum --repo . claim-next --session-id sess_3aa3648e67364b8b95746dd268f7958a --lease-seconds 3600 --json`
  - Result: passed; claimed job `job_run_8be1d202659a4fd093998367cf61495d_verification`, lease `lease_8a4e7fb80036488a937ca48d3dd50a6d`.
- `STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 .venv/bin/striatum --repo . ack --session-id sess_3aa3648e67364b8b95746dd268f7958a --message-id msg_1478662239464c1aa41d6964e9e38d0d --lease-id lease_8a4e7fb80036488a937ca48d3dd50a6d --json`
  - Result: passed; job acked.

### Focused Entity-Grounding Workflow And Materialization Tests

- `ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test" .venv/bin/python -m pytest -vv tests/test_entity_grounding_workflow.py tests/test_entity_grounding_materialization.py`
  - Result: passed, `13 passed in 16.40s`.
  - Coverage notes: deterministic draft selection, local-hit no-network-grant path, network-miss request/draft grant persistence, idempotent rerun, no socket/adapters in draft flow, approved-grant materialization, non-latest grant refusal, duplicate provider-row reuse, evidence-attach-only review action, and sanitized provider failure.

### CLI Entity-Grounding Subset

- `ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test" .venv/bin/python -m pytest -vv tests/test_cli.py -k "entity_grounding or claim_grounding"`
  - Result: passed, `4 passed, 39 deselected in 2.20s`.
  - Covered `claim-grounding entity`, grant lifecycle CLI rows, `entity-grounding draft`, and `entity-grounding process-approved` secret redaction.

### Runtime E2E Gate

- `make e2e-claim-grounding-runtime`
  - Result: failed on shared `postgresql:///engram_test`, `6 failed, 76 passed, 5 errors in 78.88s`.
  - Failure mode: database reset contention/partial schema state. Representative errors included `psycopg.errors.DeadlockDetected`, `duplicate key value violates unique constraint "pg_type_typname_nsp_index"`, `relation "claim_grounding_grants" does not exist`, and `relation "entity_grounding_evidence" does not exist`.
  - Interpretation: this result is consistent with another DB-resetting process using the shared `ENGRAM_TEST_DATABASE_URL`; it does not isolate implementation behavior.
- `createdb engram_test_rfc0054_verification`
  - Result: passed, but the database lacked the pre-created `vector` extension.
- `make e2e-claim-grounding-runtime TEST_DATABASE_URL=postgresql:///engram_test_rfc0054_verification`
  - Result: failed, `52 passed, 35 errors in 2.86s`.
  - Failure mode: `psycopg.errors.InsufficientPrivilege: permission denied to create extension "vector"`.
- `dropdb engram_test_rfc0054_verification`
  - Result: passed.
- `createdb -T engram_test engram_test_rfc0054_verification`
  - Result: passed; cloned from the pre-provisioned test DB so `vector` was available.
- `make e2e-claim-grounding-runtime TEST_DATABASE_URL=postgresql:///engram_test_rfc0054_verification`
  - Result: passed, `87 passed in 75.90s`.

### Ruff

- `.venv/bin/python -m ruff check scripts/authority_lint.py src/engram/claim_grounding.py src/engram/claim_grounding_broker.py src/engram/claim_grounding_integration.py src/engram/claim_grounding_network.py src/engram/claim_grounding_runtime.py src/engram/cli.py src/engram/context.py src/engram/context_eval.py src/engram/entity_grounding.py src/engram/entity_grounding_materialization.py src/engram/entity_grounding_workflow.py src/engram/events.py src/engram/evidence.py src/engram/extractor.py src/engram/mcp_stdio.py src/engram/memory.py src/engram/no_egress.py src/engram/phase4.py src/engram/policy.py src/engram/web/tier.py tests/conftest.py tests/context_eval_synthetic_harness.py tests/test_authority_lint.py tests/test_claim_grounding.py tests/test_claim_grounding_broker.py tests/test_claim_grounding_integration.py tests/test_claim_grounding_network.py tests/test_claim_grounding_runtime.py tests/test_claim_grounding_security.py tests/test_claim_grounding_synthetic_e2e.py tests/test_cli.py tests/test_context_eval.py tests/test_context_eval_synthetic_e2e.py tests/test_context_for.py tests/test_entity_grounding_materialization.py tests/test_entity_grounding_workflow.py tests/test_events.py tests/test_evidence_index.py tests/test_interview_cli.py tests/test_mcp_stdio.py tests/test_memory_exact_refs_project_execution.py tests/test_memory_packet.py tests/test_migrations.py tests/test_no_egress.py tests/test_phase4_entities_review.py tests/test_policy.py tests/test_web_ui_shared.py`
  - Result: failed.
  - Finding: `I001 Import block is un-sorted or un-formatted` in `tests/test_memory_exact_refs_project_execution.py:3`.
- `.venv/bin/python -m ruff check src/engram/entity_grounding_workflow.py src/engram/entity_grounding_materialization.py src/engram/cli.py tests/test_entity_grounding_workflow.py tests/test_entity_grounding_materialization.py tests/test_cli.py`
  - Result: passed, `All checks passed!`.

### Pyright

- `.venv/bin/python -m pyright src/engram/claim_grounding.py src/engram/claim_grounding_broker.py src/engram/claim_grounding_integration.py src/engram/claim_grounding_network.py src/engram/claim_grounding_runtime.py src/engram/cli.py src/engram/entity_grounding.py src/engram/entity_grounding_materialization.py src/engram/entity_grounding_workflow.py tests/test_claim_grounding.py tests/test_claim_grounding_broker.py tests/test_claim_grounding_integration.py tests/test_claim_grounding_network.py tests/test_claim_grounding_runtime.py tests/test_claim_grounding_security.py tests/test_claim_grounding_synthetic_e2e.py tests/test_cli.py tests/test_entity_grounding_materialization.py tests/test_entity_grounding_workflow.py`
  - Result: failed, `38 errors, 1 warning`.
  - Representative issues: unresolved imports for `pytest` and `uvicorn`, optional-subscript errors in `tests/test_claim_grounding_integration.py`, fake-opener signature/type issues in `tests/test_claim_grounding_network.py`, nullable `ENGRAM_TEST_DATABASE_URL` passed to `psycopg.connect`, and one `psycopg` `LiteralString` query typing issue.
- `.venv/bin/python -m pyright src/engram/entity_grounding_workflow.py src/engram/entity_grounding_materialization.py src/engram/claim_grounding.py src/engram/claim_grounding_runtime.py src/engram/claim_grounding_network.py src/engram/cli.py`
  - Result: failed, `1 error, 1 warning`.
  - Issue: `src/engram/cli.py:3420:16 - error: Import "uvicorn" could not be resolved`; warning that `src/engram/cli.py:578` is too complex to analyze.
- `.venv/bin/python -m pyright src/engram/entity_grounding_workflow.py src/engram/entity_grounding_materialization.py src/engram/claim_grounding.py src/engram/claim_grounding_runtime.py src/engram/claim_grounding_network.py`
  - Result: passed, `0 errors, 0 warnings, 0 informations`.

### Diff And Authority Checks

- `git diff --check`
  - Result: passed.
- `.venv/bin/python scripts/authority_lint.py`
  - Result: passed, `authority lint passed`.

## Residual Risk

- The default `make e2e-claim-grounding-runtime` target is unsafe to run while
  another lane is resetting the same `postgresql:///engram_test` schema. The
  isolated rerun passed, but the shared-DB failure is real operational risk for
  parallel Striatum verification unless lanes use distinct pre-provisioned test
  databases or a test fixture lock.
- Broad touched-file ruff is red due `tests/test_memory_exact_refs_project_execution.py`
  import ordering. The RFC0054/0055 subset passed ruff.
- Pyright is not clean on the broader touched source/test set. The core
  RFC0054/0055 source modules passed pyright, but `src/engram/cli.py` still
  reports unresolved optional `uvicorn`, and tests report unresolved `pytest`
  plus several typing issues.
