# RFC0055 Broker Authority Handoff

Run: `run_8be1d202659a4fd093998367cf61495d`
Lane: broker authority follow-up
Date: 2026-05-19

## Scope

Addressed the adversarial security finding that
`engram entity-grounding process-approved` should run under broker database
authority rather than normal Engram operator authority.

## Changes

- Added `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` as the CLI-only restricted
  DSN seam for `entity-grounding process-approved`.
- Kept existing defaults working: when the env var is absent or blank, the
  command still uses the normal Engram connection path for local development,
  mocked tests, and backward compatibility.
- Added focused CLI coverage proving the broker DSN is passed to `connect()` and
  is not printed in CLI output.
- Updated RFC0055 to state that routine network-provider runs require broker DB
  authority and that the normal DSN fallback is not sufficient for acceptance.

## Verification

```text
.venv/bin/python -m pytest tests/test_cli.py -q -k "entity_grounding_process_approved"
2 passed, 42 deselected in 0.21s

.venv/bin/python -m ruff check src/engram/cli.py tests/test_cli.py
All checks passed!

git diff --check -- src/engram/cli.py tests/test_cli.py docs/rfcs/0055-grounding-evidence-materialization.md docs/reviews/rfc0054-0055-entity-grounding-workflow/BROKER_AUTHORITY_HANDOFF.md
passed
```

## Striatum Lifecycle

Attempted to inspect the requested existing run with:

```text
striatum --repo /home/halbritt/git/engram status --run-id run_8be1d202659a4fd093998367cf61495d --json
```

The local Striatum state returned `run not found`, so I could not claim,
publish, or complete against that run from this checkout.

## Changed Files

- `src/engram/cli.py`
- `tests/test_cli.py`
- `docs/rfcs/0055-grounding-evidence-materialization.md`
- `docs/reviews/rfc0054-0055-entity-grounding-workflow/BROKER_AUTHORITY_HANDOFF.md`
