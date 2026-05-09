# Synthesize RFC 0030 Review Findings

Read `FINDINGS_LEDGER.md` and the current RFC 0030. Produce concrete
revision instructions for the author.

Output:

`docs/reviews/rfc0030-grounding-claim-extraction/REVISION_SYNTHESIS.md`

## Structure

```md
# RFC 0030 Public-Dataset Entity Grounding Revision Synthesis
author: <packet author line>

Status: synthesis
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Decision

## Accepted findings

## Rejected findings

## Deferred findings

## Required RFC edits

## Position on each design choice
- D-A (starting dataset set):
- D-B (resolver placement):
- D-C (output shape):
- D-D (schema home):
- D-E (snapshot discipline):
- D-F (grant model):
- D-G (extraction prompt impact):
- D-H (eval oracle):

## Position on each open question
- Q1 (smallest deliverable):
- Q2 (interaction with subject_kind_hint):
- Q3 (interaction with PHASE-0004 consolidation):
- Q4 (resolver/operator disagreement):
- Q5 (storage budget):
- Q6 (resolution latency):
- Q7 (no-grants failure mode):

## Required follow-up artifacts

## Decision: ready for spec promotion?
```

## Discipline

- Take a position on every D-A through D-H choice. "Defer to spec" is
  acceptable only if the review surfaced no constraint that forces a
  decision now.
- Take a position on every Q1 through Q7 open question. Same standard.
- For every accepted finding, name the exact RFC section and quote
  the prior text the apply_findings job will replace.
- Do not include private corpus excerpts.

Do not apply changes in this job.
