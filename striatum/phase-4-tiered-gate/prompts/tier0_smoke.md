# Tier 0 Phase 4 Smoke

Run or dry-run the RFC 0024 Tier 0 schema/workflow smoke. Do not ask for human
input. Do not run full corpus.

Prefer these checks:

```sh
.venv/bin/python -m pytest tests/test_phase4_entities_review.py
.venv/bin/python -m pytest tests/test_cli.py -k phase4
make -n phase4-smoke LIMIT=25
```

If the local database is available and migrated, run:

```sh
make phase4-smoke LIMIT=25
```

If the live smoke cannot be run safely, record why and keep the report focused
on deterministic tests and dry-run evidence.

Write `docs/operations/phase4-build/tiered-gate/TIER0_SMOKE_REPORT.md`.
Include:

- exact commands run and results;
- aggregate-only smoke counts, if any;
- whether migrations/schema preflight passed;
- whether current-belief and review-action semantics are covered by tests;
- whether entity rebuild idempotency and 1-2 hop query coverage exist;
- explicit statement that Tier 0 does not authorize full-corpus Phase 4.
