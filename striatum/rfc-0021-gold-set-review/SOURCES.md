# RFC 0021 Gold-Set Interview Curation Review — Source List

Status: scaffolded
Date: 2026-05-08

Use this file as the canonical source list each reviewer should verify before
relying on it.

## RFC Under Review

- `docs/rfcs/0021-gold-set-interview-curation.md` — proposed agent-driven
  interview loop, `gold_labels` schema, sampler design, and CLI v1 surface.

## Upstream RFCs

- `docs/rfcs/0011-phase-3-claims-beliefs.md` — `claims` and `beliefs`
  schemas the gold-set labels join onto.
- `docs/rfcs/0017-extraction-prompt-versioning.md` — `*_template_id` and
  `*_template_version` versioning convention RFC 0021 says interview
  prompts should follow.
- `docs/rfcs/0018-evidence-to-claim-audit-cascade.md` — audit cascade
  reviewer that gold labels feed (advisory only per D069).

## Schema Baseline

- `migrations/006_claims_beliefs.sql` — `claims` (line 131) and `beliefs`
  (line 178) schema RFC 0021 joins onto.
- `migrations/007_claim_audits.sql` — claim audit cascade rows.
- `migrations/008_claim_extractions_request_profile_unique.sql`,
  `migrations/009_phase4_entities_review.sql` — already-landed migrations
  that mean the next gold-labels migration number is **010**, not the
  `008` named in the RFC.

## Constraints

- `HUMAN_REQUIREMENTS.md` — local-first, privacy-tier, gold-set authorship,
  append-only constraints.
- `DECISION_LOG.md` — especially **D016** (eval gates), **D040** (gold-set
  authoring deferred until claims/beliefs exist), **D044** (no
  auto-promotion in Phase 3), **D069** (audit cascade advisory in V1),
  **D074** (Striatum SQLite is authoritative), **F010** (deferred
  cross-model judge), **O008** (open: gold-set authorship model).

## Phase Boundaries

- `BUILD_PHASES.md` § PHASE-0003 — claim extraction + bitemporal beliefs.
  RFC 0021 lands as Phase 3 follow-on / Step 5 substrate.
- `ROADMAP.md` Step 5 — gold-set authoring positioning.

## Process

- `docs/process/multi-agent-review-loop.md`.
- `docs/process/project-judgment.md`.
- `docs/process/artifact-id-conventions.md`.

## Current Command Surface

- `src/engram/cli.py` — current argparse command surface; where
  `engram interview` would land.
- `Makefile` — current Make targets.
- `README.md` — current operator-facing examples.
