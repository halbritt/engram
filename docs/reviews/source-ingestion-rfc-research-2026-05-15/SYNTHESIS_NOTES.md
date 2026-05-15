---
schema_version: "striatum.synthesis.v1"
artifact_kind: "synthesis"
---

# Source-Ingestion RFC Synthesis Notes

Lane: codex
Role: synthesizer
Date: 2026-05-15
Status: synthesis sidecar to `docs/rfcs/0050-source-ingestion-expansion.md`

## Inputs Consolidated

- `DRAFT_claude.md` — 750-line draft from the claude lane; full ten-section
  proposal including six open questions and an `EG-S00..EG-S31` gate set.
- `DRAFT_codex.md` — 611-line draft from the codex lane; narrower scope,
  argues for accepting the source-contract discipline before more families.
- `DRAFT_gemini.md` — 192-line draft from the gemini lane; introduces the
  "Evidence Lanes" taxonomy and four-gate minimum (`Idempotency`, `Conflict
  Detection`, `Immutability`, `No Egress`).
- `PRIOR_ART_DOSSIER.md` — 590-line codex-researcher dossier mapping current
  `source_kind` enum, importer modules, adjacent RFC coverage (0033-0036,
  0044-0049), Striatum corpus boundary, and open questions.
- `FINDINGS_LEDGER.md` — 137-line codex-ledger ledger normalizing the two
  review verdicts (`accept_with_findings` from both lanes).

## Verdicts Folded In

- `review_privacy_boundary` (claude lane) — `accept_with_findings`. No draft
  introduced an exfiltration path; package structurally sound. Findings
  centered on gate-ID namespace collisions, default privacy tiers for
  health/finance, and projection-family naming convergence.
- `review_project_judgment` (gemini lane) — `accept_with_findings`. Drafts
  convergent on universal contract, ordered rollout, and strict isolation.
  Five findings (`R-001..R-005`) flagged for synthesis.

## Divergence Resolutions

The synthesized RFC text explains each divergence resolution in its
"Synthesis Notes" section. Headline choices:

- **Gate naming**: adopted `EG-SI-NNN` namespace, dropping `EG-S00..` and
  `EG-101..`. Aligns with RFC 0049 style and removes namespace overlap.
- **Privacy defaults**: health and finance default to privacy_tier 3+,
  not 1. The drafts disagreed; reviewers wanted explicit higher floor.
- **Projection-family vocabulary**: kept as closed enum named in the RFC.
  The dossier's evidence-lane taxonomy is preserved as commentary, not
  as schema.
- **Rollout order**: confirmed project/build before chat/comm before
  observation/life. Highest-signal-lowest-egress-risk principle.
- **Scope kept out**: media bodies, cloud APIs, derived memory products,
  third-party communication ingestion all explicitly deferred.

## What This Synthesis Did Not Do

- Did not edit any source draft or dossier.
- Did not edit `DECISION_LOG.md`, `BUILD_PHASES.md`, `ROADMAP.md`,
  `CHANGELOG.md`, or `docs/rfcs/README.md` index.
- Did not write code, migrations, tests, or schema docs.
- Did not record acceptance — RFC 0050 ships at status `proposal` only.

Acceptance is a separate operator decision (not the synthesizer's call).
The RFC is intentionally proposal-status until a human reviews it and
either records acceptance in `DECISION_LOG.md` or asks for revision.

## Workflow Provenance

- Run: `run_740acce08b9c4fa5abcfd0d93d0fef00`
- Branch: `engram/source-ingestion-rfc-research`
- Jobs completed: 8 (4 author drafts, 2 independent reviews, 1 findings
  ledger, 1 synthesis).
- All artifacts published under the operator byline; no fabricated lane
  bylines per `docs/AGENT_CONTEXT_NOTES.md` § 1.
