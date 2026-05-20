# CLI Operator Surface Handoff

Run: `run_ecf126b2e6234ae3b54958d8471e5e56`
Job: `cli_operator_surface`

## Scope

Inspected:

- `src/engram/cli.py`
- `Makefile`
- `tests/test_cli.py`

Changed by this lane:

- `docs/reviews/entity-grounding-broker-daemon-2026-05-19/CLI_OPERATOR_HANDOFF.md`

No source or test files were edited by this lane.

## Verification

Commands run:

```sh
.venv/bin/python -m pytest -q tests/test_cli.py -k 'entity_grounding or makefile'
```

Result: `6 passed, 40 deselected in 0.20s`.

```sh
.venv/bin/python -m compileall -q src/engram/cli.py
```

Result: passed with no output.

```sh
make -n grounding-broker-daemon
```

Result: dry-run prints the expected environment guard for
`ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL`, then dispatches:

```sh
.venv/bin/python -m engram.cli entity-grounding broker-daemon --tenant "personal" --corpus "personal" --limit "20" --interval "10"
```

## Findings

No blocking issue found.

The CLI surface currently provides:

- `engram entity-grounding draft`
- `engram entity-grounding process-approved`
- `engram entity-grounding broker-daemon`
- `make provision-grounding-broker`
- `make check-grounding-broker`
- `make grounding-broker-daemon`
- `make e2e-entity-grounding`

The broker-daemon path refuses to run without
`ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL`, uses that DSN through
`connect(url=...)`, accepts tenant/corpus/limit/interval/target-adapter/max-iterations
operator controls, and redacts secret-shaped output fields.

## Residual Risks

- `entity-grounding process-approved` uses `connect(url=entity_grounding_broker_database_url())`; when the env var is unset this falls through to the default DB connection. That may be intentional for local/manual materialization, but it is less fail-closed than `broker-daemon`.
- `make grounding-broker-daemon` only checks that the restricted DSN env var is set; actual privilege separation depends on `provision-grounding-broker` / `check-grounding-broker` and database role configuration.
- Verification here was CLI-focused. It did not run the daemon core or live database privilege checks.
