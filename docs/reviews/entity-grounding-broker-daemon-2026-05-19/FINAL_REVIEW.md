author: operator

# Final Review

Run: `run_ecf126b2e6234ae3b54958d8471e5e56`  
Date: 2026-05-19

## Findings

No blocking findings.

Non-blocking residuals:

- Crash-before-commit can still duplicate provider dispatch if the process dies
  after adapter I/O but before committing the prepared dispatch row
  (`src/engram/entity_grounding_materialization.py:198`,
  `src/engram/entity_grounding_daemon.py:205`). This is documented as a retry
  caveat and requires a stronger durable claim boundary to eliminate.
- Direct concurrent callers of `process_approved_grounding_grants` can still race
  outside the daemon lock. The intended daemon path uses a transaction advisory
  lock (`src/engram/entity_grounding_daemon.py:194`), while direct materializer
  calls rely on existing dispatch rows and the unique attempt index.
- `entity-grounding process-approved` retains the normal DB fallback when
  `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` is unset; `broker-daemon`
  correctly refuses to start without that env var
  (`src/engram/cli.py:1813`, `src/engram/cli.py:1828`). RFC0055 and runbooks
  state the fallback is for local development/mocked verification only.
- Production user-service packaging, bounded retry/cooldown policy, richer review
  UI, and claim-affecting grounding use remain future work, not blockers for this
  daemon scaffold.

## Verdict

Accept with findings. The scaffold satisfies the requested broker-daemon slice:
restricted-DSN CLI path, local daemon loop, transaction advisory locking,
existing-dispatch skip behavior, provider-output filtering, secret-redacted JSON
output, Makefile target, runbooks, and focused gate coverage are present.

## Verification

- `.venv/bin/python -m pytest tests/test_entity_grounding_daemon.py tests/test_grounding_broker_provisioning.py tests/test_cli.py -q -k "broker_daemon or grounding_broker"`:
  `7 passed, 44 deselected`.
- `.venv/bin/python -m ruff check src/engram/entity_grounding_daemon.py src/engram/entity_grounding_materialization.py src/engram/cli.py tests/test_entity_grounding_daemon.py tests/test_entity_grounding_materialization.py tests/test_cli.py tests/test_grounding_broker_provisioning.py scripts/check_grounding_broker_role.py scripts/provision_grounding_broker_role.py`:
  `All checks passed!`
- `make -n grounding-broker-daemon` prints the expected
  `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` guard and daemon command.
