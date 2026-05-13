# Phase 4 Benchmark Tier 2 Preflight Scaffold

Status: scaffold
Date: 2026-05-13
author: operator [self-declared: phase4-tier2-operator-codex]

RFC refs:
  - RFC-0024
  - RFC-0021
  - RFC-0025

Decision refs:
  - D006
  - D007
  - D017
  - D020
  - D021
  - D044
  - D052
  - D069
  - D077
  - D078

Phase refs:
  - PHASE-0004

## Redaction Boundary

This scaffold contains only command shapes, local dry-run outcomes, aggregate
check plans, relation and command names, expected timing fields, and gate
blockers.

It intentionally omits raw corpus text, model prompts, completions,
conversation titles, belief values, claim values, entity names, relationship
labels, unredacted row ids, and home-directory absolute paths.

## Inputs

Reviewed inputs:

- `AGENTS.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `docs/schema/README.md`
- `docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md`
- `docs/rfcs/0021-gold-set-interview-curation.md`
- `docs/rfcs/0025-phase-scoped-command-names.md`
- `docs/process/project-judgment.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER0_SMOKE_REPORT.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER1_NONHUMAN_REPORT.md`
- `Makefile`
- `src/engram/cli.py`
- `src/engram/phase4.py`
- `migrations/009_phase4_entities_review.sql`
- `tests/test_phase4_entities_review.py`
- `tests/test_cli.py`

Tier 0 input status is `findings`, not pass. Tier 1 input status is
`findings`, not pass. This scaffold preserves both statuses as blockers.

## Commands

Required dry-run checks were run locally.

```sh
make -n phase4-smoke LIMIT=500
```

Result: passed as a dry run. The target resolves to bounded setup followed by:

```sh
ENGRAM_DATABASE_URL="postgresql:///engram" .venv/bin/python -m engram.cli phase4 smoke --limit 500
```

```sh
make -n phase4-build-entities LIMIT=500
```

Result: passed as a dry run. The target resolves to bounded setup followed by:

```sh
ENGRAM_DATABASE_URL="postgresql:///engram" .venv/bin/python -m engram.cli phase4 build-entities --limit 500
```

```sh
.venv/bin/python -m engram.cli phase4 smoke --help
.venv/bin/python -m engram.cli phase4 build-entities --help
.venv/bin/python -m engram.cli phase4 run
```

Result: all three failed before CLI parsing because `.venv/bin/python` is
absent in this worktree. This is the same runtime blocker recorded by Tier 0
and Tier 1. It means the `phase4 run` command absence could not be re-proven
from the requested executable command in this worktree.

Additional argparse fallback checks were attempted with system Python and
`PYTHONPATH=src`. They also failed before parsing because the system Python
environment lacks project dependencies. Static command-surface inspection
therefore remains the local evidence for `phase4 run` absence:

- `Makefile` exposes `phase4-refresh`, `phase4-build-entities`,
  `phase4-smoke`, and `phase4-smoke-docker`; no `phase4-run` target exists.
- `src/engram/cli.py` registers `phase4 refresh-current-beliefs`,
  `phase4 build-entities`, `phase4 smoke`, and `phase4 review-belief`; it does
  not register `phase4 run`.
- `tests/test_cli.py` includes a test asserting `phase4 run` is not a command,
  but tests did not execute in this worktree.

## Bounded Command Plan

Tier 2 must run only after an initialized local Python environment exists and
the Tier 0/Tier 1 blockers are either cleared or carried forward explicitly.
The bounded production preflight plan is:

1. Record the repo commit, RFC refs, command lines, database URL class, and
   local model endpoint/profile in an aggregate-only report.
2. Run the Phase 4 test surface in the initialized environment before any
   bounded production write:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_phase4_entities_review.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_cli.py -k phase4
```

3. Run a bounded projection/entity preflight against the intended production
   database shape:

```sh
make phase4-smoke LIMIT=500
make phase4-build-entities LIMIT=500
```

4. Do not run `engram phase4 run`. RFC 0025 intentionally keeps that command
   absent until RFC 0024 gates accept a full Phase 4 execution contract.
5. Do not run any unbounded Phase 4 entity/review command. Tier 2 scope is
   `--limit 500` or an equivalent fixed bounded slice.

## Production Assumptions

Tier 2 must use the same local production database and model endpoint intended
for the eventual full Phase 4 run, but it must not make full-run authorization
implicit.

Required assumptions:

- The Engram-reading process has no network egress.
- PostgreSQL is local, operator-controlled, and reachable through the normal
  Engram database configuration.
- The local model endpoint, if any entity-disambiguation tiebreak path is used,
  is the current conservative `ik_llama` profile from RFC 0024:
  `ctx-size 49152`, `parallel 1`, `batch-size 2048`, `ubatch-size 512`, `q8_0`
  KV cache.
- Tier 2 does not promote `ubatch=2048`, parallel serving, vLLM, sglang,
  hosted inference, web search, telemetry, or external persistence.
- No prompts, completions, raw corpus text, titles, belief values, claim
  values, entity names, or relationship labels are written to committed
  artifacts.
- Any scratch output with private content stays outside committed artifacts and
  is summarized only through aggregate redacted findings.

## Required Checks

Tier 2 completion checks must include all RFC 0024 bounded production preflight
items:

| Check | Required evidence |
|---|---|
| Striatum state | No failed or in-flight Phase 4 jobs after completion. |
| Duplicate active entities | Zero duplicate active canonical entities for the same canonical key. |
| Entity provenance | No entity or edge row loses `source_belief_ids`, `source_claim_ids` where applicable, `evidence_ids`, `privacy_tier`, `resolution_method`, or `resolution_version`. |
| `current_beliefs` refresh | Refresh completes cleanly after the bounded run; rejected, superseded, closed, and historical rows remain excluded. |
| Review queue operability | Queue size and status/action distribution are reported as aggregate counts and are human-operable. |
| Correction actions | `correct` inserts raw `captures` evidence and records `belief_review_actions.action_status = 'queued_reprocessing'`; no silent mutation is accepted. |
| Review actions | `accept`, `reject`, and `promote_to_pinned` route through the D052 transition API and produce audit/review-action evidence. |
| Entity query latency | p50 and p95 timings are reported for one-hop and two-hop recursive CTE neighborhood queries. |
| Projection latency | p50 and p95 timings are reported for `current_beliefs` refresh/query paths. |
| Error classes | Any failures are summarized by class only, with private content redacted. |

The no-failed/no-in-flight check should be the final operational gate before
publishing the Tier 2 report. A non-empty failed or in-flight set blocks Tier 2.

## Aggregate Report Shape

The Tier 2 report should be committed under:

```text
docs/operations/phase4-build/<loop_id>/reports/
```

Required sections:

```md
# Phase 4 Benchmark Tier 2 Findings

Status: findings
Date: YYYY-MM-DD
RFC refs:
  - RFC-0024
Decision refs:
  - D006
  - D007
  - D017
  - D044
  - D052
  - D069
Phase refs:
  - PHASE-0004

## Redaction Boundary
## Inputs
## Commands
## Results
## Findings
## Recommendation
## Evidence Artifacts
```

The `Results` section should include only aggregate tables, such as:

- command outcomes and exit statuses;
- test outcome counts;
- Phase 4 job status counts;
- current-belief status distributions;
- review-queue item counts by status, action, and stability class;
- entity and edge create/reuse counts;
- duplicate active canonical-key and active-edge counts;
- provenance-missing counts;
- correction capture and queued-reprocessing counts;
- `current_beliefs` refresh/query p50 and p95 timings;
- one-hop and two-hop recursive CTE p50 and p95 timings;
- error classes and redacted ids only where needed for reproducibility.

## Preserved Blockers

Tier 2 preparation does not erase these blockers from Tier 0 and Tier 1:

- Tier 0 has not passed because pytest and live `make phase4-smoke LIMIT=25`
  did not run in an initialized project environment.
- Tier 1 has not passed because it is non-human evidence only, Tier 0 is still
  non-passing input, and RFC 0021 human-label evidence is deferred.
- Human-labeled same-entity/different-entity precision and recall remain
  unclaimed.
- Zero-known-false-merge validation on a labeled entity set remains unclaimed.
- False-split reviewability on a labeled entity set remains unclaimed.
- Human/operator review-queue UX feedback and queue-operability judgment remain
  unclaimed.
- Live review-action latency and audit completeness across all four action
  kinds remain unmeasured.
- The realistic synthetic graph scale benchmark remains unrun.

## Recommendation

This scaffold prepares the Tier 2 bounded production preflight shape only. It
does not recommend promotion beyond Tier 1, and it does not authorize
full-corpus Phase 4.

Before running Tier 2, initialize the project Python environment, execute the
Phase 4 tests, preserve the RFC 0021 human-label gaps as blockers, and run only
bounded Phase 4 commands with aggregate-only reporting.

## Evidence Artifacts

No private scratch artifacts were published for this scaffold. Evidence is the
local dry-run command output, static command-surface inspection, the Tier 0 and
Tier 1 aggregate reports, and this handoff artifact.
