# Phase 4 Benchmark Tier 1 Findings

Status: findings
Date: 2026-05-13
author: operator [self-declared: phase4-tier1-operator-codex]

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

Phase refs:
  - PHASE-0004

## Redaction Boundary

This report contains only aggregate counts, status distributions, command
outcomes, schema relation names, plan summaries, timing summaries, and
test-surface references.

It intentionally omits raw corpus text, model prompts, completions,
conversation titles, belief values, claim values, entity names, relationship
labels, unredacted row ids, and home-directory absolute paths.

## Inputs

Reviewed inputs:

- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER0_SMOKE_REPORT.md`
- `docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md`
- `docs/rfcs/0021-gold-set-interview-curation.md`
- `docs/rfcs/0025-phase-scoped-command-names.md`
- `docs/process/project-judgment.md`
- `migrations/009_phase4_entities_review.sql`
- `src/engram/phase4.py`
- `src/engram/consolidator/transitions.py`
- `src/engram/cli.py`
- `tests/test_phase4_entities_review.py`
- `Makefile`

Tier 0 input status: `findings`, not pass. Tier 0 did not run pytest or a live
Phase 4 smoke command because the project Python environment was absent.

## Commands

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_phase4_entities_review.py
```

Result: failed before test collection because `.venv/bin/python` is absent.

```sh
python3 -m pytest --version
```

Result: failed because system Python does not have `pytest` installed.

```sh
make -n phase4-build-entities LIMIT=200
make -n phase4-smoke LIMIT=200
```

Result: both dry runs passed. The generated command surface is bounded and
phase-scoped:

- `engram.cli phase4 build-entities --limit 200`
- `engram.cli phase4 smoke --limit 200`

The dry runs also show that live Make targets would create/install `.venv`
before executing the bounded Phase 4 command, so live runs were not attempted
under this report-only job.

```sh
make -n pipeline
make -n pipeline-docker
make -n pipeline-isolated
```

Result: dry runs show fail-closed generic pipeline targets with scoped
alternatives. No generic `phase4 run` path is implied.

Read-only aggregate SQL was run with:

```sh
PGOPTIONS='-c default_transaction_read_only=on' psql -d engram ...
```

Result: local aggregate checks and read-only `EXPLAIN ANALYZE` queries
completed.

## Results

### Command Surface

`Makefile` exposes bounded Phase 4 targets for refresh, entity build, and smoke
(`Makefile:198-205`). `src/engram/cli.py` exposes only
`phase4 refresh-current-beliefs`, `phase4 build-entities`, `phase4 smoke`, and
`phase4 review-belief` under the Phase 4 namespace (`src/engram/cli.py:648-681`).
No `phase4 run` command exists under RFC 0025's accepted contract.

### Current Beliefs Status Semantics

The materialized view definition is status-aware:
`current_beliefs` includes only rows with `valid_to IS NULL`,
`closed_at IS NULL`, `superseded_by IS NULL`, and status in
`candidate`, `provisional`, or `accepted`
(`migrations/009_phase4_entities_review.sql:143-180`). The review queue then
narrows that projection to `candidate` and `provisional`
(`migrations/009_phase4_entities_review.sql:183-209`).

Read-only live database status evidence:

| Status | Beliefs | In `current_beliefs` | Excluded |
|---|---:|---:|---:|
| `candidate` | 30700 | 30700 | 0 |
| `rejected` | 4870 | 0 | 4870 |
| `superseded` | 6988 | 0 | 6988 |

Additional exclusion evidence:

| Status | `valid_to` set | `closed_at` set | `superseded_by` set |
|---|---:|---:|---:|
| `rejected` | 0 | 4870 | 0 |
| `superseded` | 3760 | 6988 | 3228 |

The live database currently has no `provisional` or `accepted` rows, so those
inclusion branches are schema-defined and test-surface-covered but not
live-distribution-proven in this Tier 1 run.

### Entity Build Idempotency

`build_deterministic_entities` reads `current_beliefs` in stable `ORDER BY id`
order, looks up active canonical entity rows before insert, and looks up active
entity edges before insert (`src/engram/phase4.py:350-427`). The schema adds
unique active-key and active-edge indexes
(`migrations/009_phase4_entities_review.sql:1-84`).

The Phase 4 test surface asserts first-run create counts and second-run reuse
counts for deterministic entity build
(`tests/test_phase4_entities_review.py:150-178`), but the test was not executed
because the local Python test environment is absent.

Read-only live database aggregate evidence:

| Metric | Count |
|---|---:|
| Active entities | 281 |
| Active entity edges | 200 |
| Duplicate active entity keys | 0 |
| Duplicate active entity edges | 0 |
| Entity rows with empty source belief ids | 0 |
| Entity rows with empty evidence ids | 0 |
| Edge rows with empty source belief ids | 0 |
| Edge rows with empty evidence ids | 0 |
| Entity confidence out of range | 0 |
| Edge confidence out of range | 0 |
| Entity privacy tier out of range | 0 |
| Edge privacy tier out of range | 0 |
| Missing edge source entities | 0 |
| Missing edge target entities | 0 |
| Self-edges | 0 |

### Review Actions And Audit Semantics

`belief_review_actions` stores `accept`, `reject`, `correct`, and
`promote_to_pinned` actions with `applied`, `recorded`, or
`queued_reprocessing` status
(`migrations/009_phase4_entities_review.sql:86-108`). Append-only triggers are
present for `entity_resolution_events`, `belief_review_actions`, and
`pinned_beliefs` (`migrations/009_phase4_entities_review.sql:118-141`), and
the live database has those triggers plus `fn_phase4_append_only()`.

Accept, reject, and promote-to-pinned call the D052 transition API and then
insert a review action (`src/engram/phase4.py:129-218`,
`src/engram/phase4.py:294-347`). The transition API performs the status update
through the audited path and inserts `belief_audit` on changed status
transitions (`src/engram/consolidator/transitions.py:130-177`,
`src/engram/consolidator/transitions.py:342-360`).

The Phase 4 test surface verifies candidate inclusion, accept-to-accepted,
`belief_audit` creation for accept, review action creation for accept,
correction-as-capture, rejected exclusion from `current_beliefs`, pinned
promotion, pinned idempotency, and smoke execution
(`tests/test_phase4_entities_review.py:57-190`). The tests were not executed
in this worktree.

Live aggregate review-action evidence is empty:

| Metric | Count |
|---|---:|
| `belief_review_actions` rows | 0 |
| Correction actions | 0 |
| Queued reprocessing actions | 0 |
| `pinned_beliefs` rows | 0 |

Because there are no live review actions, this Tier 1 run has static and
test-surface evidence for review behavior, not live latency or live action
outcome evidence.

### Correction As Capture

`correct_belief` inserts a raw `captures` row with
`capture_type = 'user_correction'`, carries the corrected belief's privacy tier,
links `corrects_belief_id`, and then records a `belief_review_actions` row with
`action_status = 'queued_reprocessing'` (`src/engram/phase4.py:221-291`).

There is no separate Phase 4 reprocessing queue table write in this
implementation. The downstream queue implication is represented by the raw
correction capture plus the queued review-action status.

### Query Plan Evidence

Read-only `current_beliefs` count query:

| Query | Plan summary | Execution time |
|---|---|---:|
| `SELECT count(*) FROM current_beliefs` | index-only scan on `current_beliefs_status_stability_idx`, 0 heap fetches | 1.662 ms |

Read-only recursive CTE evidence:

`entity_neighborhood` limits depth to 1 or 2, follows only active edges in
either direction, tracks a path array to avoid cycles, and returns distinct
non-root entities ordered by depth (`src/engram/phase4.py:430-473`). The Phase
4 test surface calls it with `max_depth=2`, though that fixture proves a
one-hop result (`tests/test_phase4_entities_review.py:150-178`).

Single-seed read-only `EXPLAIN ANALYZE` on the current local active-edge scale:

| Query | Plan summary | Execution time |
|---|---|---:|
| One-hop recursive neighborhood | recursive union over active edges | 0.272 ms |
| Two-hop recursive neighborhood | recursive union over active edges | 0.143 ms |

The same two-hop query returned aggregate depth counts of 1 row at depth 1 and
1 row at depth 2 for the selected seed.

Server-side timing over the first 50 active entities, using a read-only
statement and `clock_timestamp()` inside the database:

| Depth | Samples | p50 ms | p95 ms | Min ms | Max ms | Neighbor rows counted |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 50 | 1.979 | 2.969 | 0.081 | 3.129 | 161 |
| 2 | 50 | 1.998 | 3.011 | 0.107 | 3.145 | 1962 |

This is favorable at the current local active-edge scale, but it is not a
synthetic large-scale graph benchmark.

## Findings

Finding 1: Non-human Tier 1 evidence is favorable but incomplete. The schema,
command surface, static implementation, read-only aggregate checks, and query
plans align with RFC 0024, but the preferred test commands still cannot run in
this worktree because the project Python environment is absent.

Finding 2: `current_beliefs` has the correct status-aware predicate in schema
and live evidence excludes rejected and superseded beliefs. Live data does not
exercise provisional or accepted inclusion, and direct Phase 4 tests for
`valid_to`, `closed_at`, and `superseded_by` exclusion are still gaps.

Finding 3: Deterministic entity build has good idempotency controls: stable
input ordering, lookup-before-insert behavior, unique active-key/edge indexes,
targeted idempotency tests, and zero duplicate active keys/edges in the live
aggregate check. Because tests did not execute and no live rebuild was run,
this is not full rebuild proof.

Finding 4: Review-action semantics align with D017 and D052 in code. Accept,
reject, and promote-to-pinned route through the transition API; correction
inserts raw capture evidence and records queued reprocessing. Live review
action latency, audit completeness across all four action kinds, and queue
outcome distributions remain unmeasured because there are no live review
actions in the database and tests could not run.

Finding 5: Recursive CTE evidence is non-pathological at the current local
active-edge scale. The query is bounded to 1-2 hops and cycle-safe in code, and
read-only timing over 50 active seeds produced low p50/p95 values. RFC 0024's
realistic synthetic scale benchmark remains a separate non-human gap.

Finding 6: The generic pipeline command surface remains fail-closed by dry-run
inspection, and Phase 4 remains scoped to explicit verbs. This supports RFC
0025 and avoids implying full-corpus Phase 4 authorization.

## Deferred RFC 0021 Gaps

The following Tier 1 evidence is `deferred_until_rfc0021` and cannot be
claimed by this non-human gate:

- Human-labeled same-entity/different-entity precision.
- Human-labeled same-entity/different-entity recall.
- Zero-false-merge validation on a labeled entity set.
- False-split reviewability validation on a labeled entity set.
- Human/operator review-queue UX feedback.
- Review action outcome quality over approximately 50 human-reviewed queue
  items.
- Human judgment on whether queue volume and distribution are operable.

## Recommendation

Do not promote Phase 4 beyond Tier 1 on this report.

Non-human evidence supports continuing bounded Phase 4 investigation, but Tier
1 does not pass because RFC 0021 human-label evidence is intentionally deferred
and local test execution is blocked by the missing project Python environment.

Before any Tier 2 bounded production preflight, run the preferred pytest
surface in an initialized project environment, add or execute direct coverage
for provisional/accepted inclusion and closed/superseded exclusion, run a
bounded deterministic rebuild check, collect review-action latency/audit
evidence across all four action kinds, and add a synthetic 1-2 hop graph scale
test with p50/p95 timing.

## Evidence Artifacts

No private scratch artifacts were published. Evidence is the aggregate command
output summarized above and this report artifact.
