Lane: codex_cli_docs
Role: implementer

# CLI/Docs Handoff: RFC 0054/0055 Entity Grounding

## Summary

Wired the operator-facing command names for the RFC 0054/0055 entity-grounding
workflow:

- `engram entity-grounding draft`
- `engram entity-grounding process-approved`
- `make e2e-entity-grounding`

The CLI uses lazy implementation-module dispatch so it can call the dedicated
worker lanes while keeping `src/engram/cli.py` importable. Output goes through a
recursive sanitizer that redacts secret-shaped fields before JSON is printed.

## Files Changed

- `src/engram/cli.py`
- `tests/test_cli.py`
- `Makefile`
- `CHANGELOG.md`
- `ROADMAP.md`
- `docs/rfcs/0054-entity-grounding-batch-workflow.md`
- `docs/rfcs/0055-grounding-evidence-materialization.md`
- `docs/rfcs/README.md`
- `docs/AGENT_CONTEXT_NOTES.md`
- `docs/reviews/rfc0054-0055-entity-grounding-workflow/CLI_DOCS_HANDOFF.md`

## Verification

Passed:

```sh
ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test" .venv/bin/python -m pytest -q tests/test_cli.py -k "entity_grounding or makefile_has_phase_scoped_targets"
.venv/bin/python -m py_compile src/engram/cli.py
make -n e2e-entity-grounding
```

One full-module CLI run passed after restoring the local test DB extension
state:

```sh
ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test" .venv/bin/python -m pytest -q tests/test_cli.py
```

After the worker modules landed and the CLI seam was adjusted to their actual
signatures, a subsequent full-module CLI rerun hit the same intermittent local
test DB catalog issue during DB-backed fixture setup:

```text
41 passed, 2 errors
psycopg.errors.UniqueViolation: duplicate key value violates unique constraint "pg_type_typname_nsp_index"
Key (typname, typnamespace)=(schema_migrations, ...)
```

Coordinator integration resolved the worker/materializer follow-up after this
lane completed. Current focused status:

```sh
ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test" .venv/bin/python -m pytest -q tests/test_entity_grounding_workflow.py tests/test_entity_grounding_materialization.py
# 13 passed
```

## Notes

- The initial requested `striatum session register` command was not supported by
  the installed Striatum CLI. I used the supported lifecycle sequence:
  `register-session`, `claim-next`, and `ack`.
- Session: `sess_2fcb7a406ffc4c32ba2c7a5f30ac43dd`.
- Job: `job_run_8be1d202659a4fd093998367cf61495d_cli_docs`.
- Lease: `lease_44566722f4ce47e09e72a41226842318`.
