# RFC 0025 Command-Names Review — Source List

Status: scaffolded
Date: 2026-05-08

Use this file as the canonical source list each reviewer should verify before
relying on it.

## RFC Under Review

- `docs/rfcs/0025-phase-scoped-command-names.md` — proposed phase-scoped
  command names and fail-closed generic `pipeline` behavior.

## Current Command Surface

- `README.md` — current operator examples.
- `Makefile` — current Make targets.
- `src/engram/cli.py` — current argparse command surface.

## Phase Boundaries

- `BUILD_PHASES.md` § PHASE-0002 — segmentation + embeddings.
- `BUILD_PHASES.md` § PHASE-0003 — claim extraction + bitemporal beliefs.
- `BUILD_PHASES.md` § PHASE-0004 — entity canonicalization + review surface.
- `BUILD_PHASES.md` § PHASE-0005 — `context_for` + serving path.
- `BUILD_PHASES.md` § PHASE-SMOKE — integrated smoke gate.

## Constraints

- `HUMAN_REQUIREMENTS.md` — local-first and raw-evidence constraints.
- `DECISION_LOG.md` — especially D016, D020, D074, and D077.
- `docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md` — Phase 4
  execution gate affected by ambiguous command names.

## Process

- `docs/process/multi-agent-review-loop.md`.
- `docs/process/project-judgment.md`.
- `docs/process/artifact-id-conventions.md`.
