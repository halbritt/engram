# RFC 0021 Gold-Set Implementation — Source List

Status: scaffolded
Date: 2026-05-08

## Accepted RFC

- `docs/rfcs/0021-gold-set-interview-curation.md` (revised, status
  `accepted`).

## Decision Log

- **D079** — RFC 0021 acceptance + implementation contract.
- **D078** — phase-scoped CLI shape.
- **D077** — `current_beliefs` view (sampler input).
- **D073** — vocabulary-table pattern (verdict + strata vocabularies).
- **D069** — audit cascade advisory in V1 (gold labels are advisory).
- **D052** — Python transition API for belief mutations (gold loader
  must NOT call this).
- **D044** — no auto-promotion to `accepted` in Phase 3 (verdicts do
  NOT flip belief status).
- **D016** — eval gates and gold-set positioning.

## Schema Baselines

- `migrations/006_claims_beliefs.sql` — claims (line 131), beliefs
  (line 178), belief_audit (the version-triple analogue for beliefs).
- `migrations/007_claim_audits.sql` — audit cascade rows.
- `migrations/009_phase4_entities_review.sql` — `current_beliefs` view
  the sampler reads from by default.

## Command Surface

- `src/engram/cli.py` — current argparse with `phase3` subparser.
- `Makefile` — phase-scoped target patterns.
- `tests/test_cli.py` — current CLI test surface.

## Versioning

- `docs/rfcs/0017-extraction-prompt-versioning.md` — prompt template
  version pattern.
- `docs/rfcs/0025-phase-scoped-command-names.md` — phase-scoped CLI.

## Process

- `docs/process/project-judgment.md`.
- `docs/process/multi-agent-review-loop.md`.
