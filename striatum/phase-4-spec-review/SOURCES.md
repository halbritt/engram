# Phase 4 Spec Review — Source List

Status: scaffolded
Date: 2026-05-08

Use this file as the canonical source list each reviewer should
verify is current before relying on it. Prefer in-repo authoritative
docs over memory or prior conversation state.

## Phase Boundary

- `BUILD_PHASES.md` § PHASE-0004 — current Phase 4 acceptance
  criteria; the row each reviewer pressure-tests adversarially.
- `BUILD_PHASES.md` § PHASE-0003 / PHASE-0005 — neighboring phases;
  Phase 4 inherits Phase 3 outputs and feeds Phase 5.

## Project Constraints

- `HUMAN_REQUIREMENTS.md` — load-bearing principles (refusal of
  false precision, local-first, no-egress, immutable raw evidence).
- `AGENTS.md` — project boundaries; no hosted services, no
  telemetry without explicit approval.

## Decision Log

Most relevant decisions for Phase 4 (see each row in `DECISION_LOG.md`):

- `D006` — belief review queue accept/reject/correct/promote-to-pinned
  semantics.
- `D007` — recursive CTE for 1–2 hop neighborhood queries; no graph
  backend.
- `D017` — `correct` writes a new `captures` row; do not mutate
  beliefs in place.
- `D044` — entity canonicalization tiebreak.
- `D052` — bitemporal belief schema.
- `D053` — phase 4 review surface.
- `D055` — HITL queue ordering.
- `D068` — entity edge schema.
- `D074` — SQLite as authoritative; no separate state file.

## RFCs

- `docs/rfcs/0007-artifact-id-conventions.md`.
- `docs/rfcs/0011-phase-3-bitemporal-belief-schema.md`.
- `docs/rfcs/0018-audit-cascade.md`.
- `docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md` —
  benchmark gate that precedes the spec.

## Operational Context (For Reviewers)

- `docs/process/multi-agent-review-loop.md` — how this exact
  workflow runs.
- `docs/process/artifact-id-conventions.md` — citation format
  reviewers must use (`RFC-NNNN`, `D###`, `PHASE-####`,
  `REVIEW-####`).
- `striatum/phase-4-spec-review/roles/*.md` — per-role guidance.
- `striatum/phase-4-spec-review/prompts/*.md` — per-job prompts the
  runner serves.

## Schema (For Specificity)

- `docs/schema/README.md` — current Postgres schema overview; Phase
  4 adds `entities`, `entity_edges`, and the `current_beliefs`
  materialized view.
- `migrations/` — concrete SQL; Phase 4 will add new migrations.

## What Reviewers Should Treat As Out Of Scope

- Phase 5 design (`context_for`, ranking, MCP, feedback). Note
  cross-cutting risks but do not propose Phase 5 changes.
- Pre-Phase-2 adversarial gate (D026); already complete.
- Engram repo restructuring proposals beyond what Phase 4 scope
  requires.
