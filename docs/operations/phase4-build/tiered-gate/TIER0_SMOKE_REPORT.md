# Phase 4 Tier 0 Smoke Report
author: operator-codex-gpt-5.5-001

Status: findings
Date: 2026-05-09
RFC refs: RFC-0024
Decision refs: D020, D044, D052, D074, D077
Phase refs: PHASE-0004

## Summary

Ran the RFC 0024 Tier 0 schema/workflow smoke checks over a bounded local slice.
The live `phase4 smoke --limit 25` command completed successfully and did not
authorize full-corpus Phase 4.

## Commands Run

```text
.venv/bin/python -m pytest tests/test_phase4_entities_review.py
```

Result: 4 skipped. The tests require `ENGRAM_TEST_DATABASE_URL`; that isolated
test database URL is not configured in this shell.

```text
.venv/bin/python -m pytest tests/test_phase4_entities_review.py -rs
```

Result: 4 skipped with explicit skip reason:
`ENGRAM_TEST_DATABASE_URL is required for database tests`.

```text
.venv/bin/python -m pytest tests/test_cli.py -k phase4
```

Result: 2 passed, 23 deselected.

```text
make -n phase4-smoke LIMIT=25
```

Result: dry-run command expansion:

```text
ENGRAM_DATABASE_URL="postgresql:///engram" .venv/bin/python -m engram.cli phase4 smoke --limit 25
```

```text
make phase4-smoke LIMIT=25
```

Result:

```text
phase4 smoke: current_beliefs=30700 review_queue_items=30700 beliefs_processed=25 entities_created=0 entities_reused=50 edges_created=0 edges_reused=25 neighborhood_rows=1
```

## Aggregate Smoke Counts

| Metric | Value |
| --- | ---: |
| current beliefs | 30,700 |
| review queue items | 30,700 |
| bounded beliefs processed | 25 |
| entities created | 0 |
| entities reused | 50 |
| edges created | 0 |
| edges reused | 25 |
| neighborhood rows | 1 |

## Coverage Notes

- Schema preflight passed inside `phase4 smoke`; otherwise the command would
  have failed before producing counts.
- `current_beliefs` refresh succeeded and produced a non-empty projection.
- Review queue count matched current belief count for this local corpus state.
- Entity build idempotency has a positive signal: this run reused existing
  entities and edges for the bounded slice and created no new ones.
- The 1-2 hop neighborhood query path returned 1 row for the first active
  entity.
- The isolated database tests for current-belief semantics, review actions,
  correction capture, and bounded smoke did not run because
  `ENGRAM_TEST_DATABASE_URL` is not configured.

## Gate Statement

Tier 0 smoke evidence is sufficient to proceed to the non-human Tier 1 evidence
collection job. It does not authorize full-corpus Phase 4, and it does not
replace human-labeled entity precision/recall or review-queue UX validation.
