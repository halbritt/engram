# Phase 4 Benchmark Tier 0 Findings

Status: findings
Date: 2026-05-13
author: operator [self-declared: phase4-tier0-operator-codex]

RFC refs:
  - RFC-0024
  - RFC-0021
  - RFC-0025

Decision refs:
  - D006
  - D007
  - D017
  - D044
  - D052
  - D069
  - D077
  - D078

## Redaction Boundary

This report contains aggregate counts, command outcomes, schema relation names,
test-surface coverage notes, and query-plan timing summaries only.

It intentionally omits raw corpus text, model prompts, completions,
conversation titles, belief values, claim values, entity names, relationship
labels, and home-directory absolute paths.

## Inputs

Reviewed inputs:

- `docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md`
- `docs/rfcs/0021-gold-set-interview-curation.md`
- `docs/rfcs/0025-phase-scoped-command-names.md`
- `docs/process/project-judgment.md`
- `migrations/009_phase4_entities_review.sql`
- `src/engram/phase4.py`
- `tests/test_phase4_entities_review.py`
- `tests/test_cli.py`
- `Makefile`

The local PostgreSQL service answered readiness checks. The project Python
environment was not present in this worktree, so Python-based tests and the
live Phase 4 smoke command could not be run without creating `.venv` and
installing dependencies. Because this job's write scope is report-only, no
environment installation was performed.

## Commands

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_phase4_entities_review.py
```

Result: failed before test collection because `.venv/bin/python` was absent
from the worktree.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_cli.py -k phase4
```

Result: failed before test collection because `.venv/bin/python` was absent
from the worktree.

```sh
python3 --version
python3 -m pytest --version
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests/test_phase4_entities_review.py
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests/test_cli.py -k phase4
```

Result: `python3` was available as 3.12.3, but system Python did not have
`pytest` installed, so fallback pytest commands failed before test collection.

```sh
make -n phase4-smoke LIMIT=25
```

Result: passed as a dry run. The target resolves to environment setup followed
by the bounded command:

```sh
ENGRAM_DATABASE_URL="postgresql:///engram" .venv/bin/python -m engram.cli phase4 smoke --limit 25
```

The live `make phase4-smoke LIMIT=25` command was not run because the needed
project Python environment was absent and invoking the target would create
`.venv` before reaching the bounded smoke path.

```sh
pg_isready -q && echo ready || echo not-ready
```

Result: local PostgreSQL reported ready.

Read-only SQL preflight was run with:

```sh
PGOPTIONS='-c default_transaction_read_only=on' psql -d engram ...
```

Result: the upgraded local database had the Phase 4 schema relations and
required indexes present, and aggregate-only projection counts were collected.

## Results

Schema preflight on the upgraded local database:

| Check | Result |
|---|---:|
| Applied migrations | 14 |
| `009_phase4_entities_review.sql` applied | yes |
| Latest applied migration filename | `013_interview_active_learning_state.sql` |
| Required Phase 4 relations present with expected relkind | 7 / 7 |
| Required Phase 4 indexes present | 4 / 4 |

Required relation check:

| Relation | Expected | Observed |
|---|---|---|
| `belief_review_actions` | table | table |
| `belief_review_queue` | view | view |
| `current_beliefs` | materialized view | materialized view |
| `entities` | table | table |
| `entity_edges` | table | table |
| `entity_resolution_events` | table | table |
| `pinned_beliefs` | table | table |

Aggregate read-only local database counts:

| Metric | Count |
|---|---:|
| `current_beliefs` rows | 30700 |
| `belief_review_queue` rows | 30700 |
| Active `entities` rows | 281 |
| Active `entity_edges` rows | 200 |
| `belief_review_actions` rows | 0 |
| `pinned_beliefs` rows | 0 |
| Duplicate active entity keys | 0 |
| Duplicate active entity edges | 0 |

`current_beliefs` status distribution:

| Status | Count |
|---|---:|
| `candidate` | 30700 |

Read-only query timing summaries:

| Query | Summary |
|---|---|
| `SELECT count(*) FROM current_beliefs` | Index-only scan on `current_beliefs_status_stability_idx`; execution time 2.731 ms. |
| 2-hop recursive neighborhood query from one active entity | Returned aggregate depths 1 and 2 with one row at each depth; execution time 0.354 ms on the current local active-edge scale. |

No live smoke write was performed, so no new Tier 0 smoke build counts are
claimed from this run.

## Findings

Finding 1: Tier 0 is blocked from a full local execution in this worktree by
missing Python test/runtime dependencies. The preferred `.venv/bin/python`
commands cannot start because `.venv` is absent, and system Python lacks
`pytest`. This is an environment blocker, not a Phase 4 schema finding.

Finding 2: The upgraded local database passes read-only Phase 4 schema
presence checks. The Phase 4 tables, `current_beliefs` materialized view,
`belief_review_queue` view, and required preflight indexes are present.

Finding 3: Static test-surface inspection indicates core Tier 0 semantics are
covered by tests, but not all edge cases are directly exercised. The tests
cover `current_beliefs` refresh/inclusion, accept/reject review actions,
correction-as-capture, pinned promotion idempotency, deterministic entity build
idempotency, `phase4 smoke --limit` CLI dispatch, and absence of `phase4 run`.
Gaps remain for direct `valid_to` / `closed_at` / `superseded_by` exclusion
cases, non-smoke Phase 4 CLI dispatch, append-only trigger failure paths,
schema-preflight failure paths, inactive-edge filtering, invalid depth guards,
and a fixture that proves an actual two-hop traversal rather than only calling
the query with `max_depth=2`.

Finding 4: The deterministic entity rebuild path is structurally idempotent in
code and in the targeted test fixture. The live database also has zero
duplicate active canonical keys and zero duplicate active edges in the
aggregate read-only check.

Finding 5: Review-action semantics align with D017 and D052 in the inspected
implementation. Accept, reject, and promote-to-pinned route through the Phase 3
transition API and insert `belief_review_actions`; correction inserts a new
`captures` row with `capture_type = 'user_correction'` and records the review
action as queued for reprocessing. The direct D052 GUC-guard rejection path is
covered in Phase 3 tests rather than reasserted in the Phase 4 test file.

## Recommendation

Tier 0 should remain in `findings` status until the preferred pytest commands
and `make phase4-smoke LIMIT=25` run in an initialized local Python
environment.

The read-only evidence is favorable for schema presence and bounded command
shape, but it is not a substitute for executing the Tier 0 smoke command.
Tier 0 does not authorize full-corpus Phase 4.

## Evidence Artifacts

No private scratch artifacts were published. Evidence is the aggregate command
output summarized above and the expected report artifact at this path.
