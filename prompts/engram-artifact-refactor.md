# Engram Artifact Refactor: Independent IDs + Subrefs

You are operating inside the Engram repository. You are familiar with its structure and workflow:

- RFCs: `docs/rfcs/`
- Reviews: `docs/reviews/`
- Phases: `docs/phases/`
- Decision log: `DECISION_LOG.md`
- Agent guidance: `AGENTS.md` (create if missing)

---

## Objective

Introduce **independent artifact IDs + subrefs** across RFCs, decisions, reviews, and phases, and propagate this model consistently across the repo.

This is a refactor + forward-compatible system upgrade. Do not break existing content; extend it.

---

## Core Rules

1. Artifact IDs increment independently:
   - RFC-####
   - DEC-####
   - REVIEW-####
   - PHASE-####

2. Relationships are expressed via **typed references**, not shared numbering.

3. Subrefs (anchors) are required for precision:
   - Format: `<ARTIFACT>#<slug>`
   - Example: `DEC-0012#rfc-0005-accept-event-trigger-model`

4. One artifact may reference many others:
   - RFC → multiple decisions
   - Decision → multiple RFCs
   - Phase → derived from RFC + decision

---

## Tasks

### 1. Normalize RFC headers

For every file in `docs/rfcs/`:

Ensure it has a header block at the top:

```md
# RFC-XXXX <title>

Status: <Proposed | Accepted | Superseded>
Decision refs:
  - DEC-XXXX#<slug>
Review refs:
  - REVIEW-XXXX#<slug>
Phase refs:
  - PHASE-XXXX#<slug>
