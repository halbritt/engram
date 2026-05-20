# Verification

Verify the daemon scaffold without changing source files.

Run focused local checks:

```sh
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -q \
  tests/test_entity_grounding_daemon.py \
  tests/test_entity_grounding_materialization.py \
  tests/test_cli.py

.venv/bin/python -m ruff check \
  src/engram/entity_grounding_daemon.py \
  src/engram/entity_grounding_materialization.py \
  src/engram/cli.py \
  tests/test_entity_grounding_daemon.py \
  tests/test_entity_grounding_materialization.py \
  tests/test_cli.py

.venv/bin/python -m pyright \
  src/engram/entity_grounding_daemon.py \
  src/engram/entity_grounding_materialization.py \
  src/engram/cli.py
```

Also validate the Striatum workflow file if Striatum is installed locally.

Publish `docs/reviews/entity-grounding-broker-daemon-2026-05-19/VERIFICATION.md`
with commands, results, and residual risk.
