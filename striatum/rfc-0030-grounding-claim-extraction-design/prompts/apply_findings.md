# Apply RFC 0030 Review Findings

Apply accepted findings from `REVISION_SYNTHESIS.md` to
`docs/rfcs/0030-public-dataset-entity-grounding.md` and
`docs/rfcs/README.md` as needed.

Then write:

`docs/reviews/rfc0030-grounding-claim-extraction/REVISION_HANDOFF.md`

## Discipline

- Use the synthesis's "Position on D-A through D-H" and "Position on
  Q1 through Q7" sections as the authoritative source of revision
  intent. Any change you make beyond those positions must be flagged
  explicitly in the handoff.
- For every revision, the handoff must show: section name, the prior
  text (quoted), and the new text. The reader should be able to
  reconstruct the revised RFC from the handoff alone.
- Update RFC status / Decision refs / phase refs in the table at top
  of `0030-public-dataset-entity-grounding.md` if synthesis directs.
- If `docs/rfcs/README.md` needs a status or implementation column
  update, do that here too.
- Do not introduce new design choices that were not present in the
  synthesis. If a needed decision is missing, write that to
  "Open carryover for spec" in the handoff and leave the RFC with the
  prior placeholder.

## Handoff structure

```md
# RFC 0030 Public-Dataset Entity Grounding Revision Handoff
author: <packet author line>

Status: revised
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Changes made
For each: section, prior text (quoted), new text (quoted), source finding.

## Findings addressed

## Findings deferred

## Open carryover for spec

## Validation
- The RFC reads consistently end-to-end after the changes.
- Decision refs and phase refs in the front-matter remain accurate.
- No private corpus excerpts have been added.

## Residual risk
```

Do not modify implementation files (`src/engram/`, `tests/`,
`migrations/`). Do not modify `DECISION_LOG.md` directly — record the
intent in this handoff for the operator to apply.
