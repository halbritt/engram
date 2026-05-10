# Draft RFC 0029 Bench Triage Workbench

Draft or revise `docs/rfcs/0029-bench-triage-workbench.md` and update
`docs/rfcs/README.md` so the RFC is indexed.

The RFC must define a local-only UI that helps the operator validate extraction
benchmark and re-extraction deltas with less cognitive overhead. It must cover:

1. problem statement and goals;
2. non-goals;
3. local-first/privacy constraints;
4. FastAPI/Jinja2/htmx surface following RFC 0027;
5. scratch-local review state;
6. queue/risk classification;
7. routes;
8. CLI commands;
9. redacted export contract;
10. implementation plan;
11. tests and acceptance criteria;
12. open questions and promotion path.

Do not include private corpus excerpts or raw claim text. Private scratch
artifacts may be referenced only by path and aggregate metrics.

Write a design handoff to:

`docs/reviews/rfc0029-bench-triage-workbench/DESIGN_HANDOFF.md`

Use this structure:

```md
# RFC 0029 Bench Triage Workbench Design Handoff
author: <packet author line>

Status: draft
Date: 2026-05-09
RFC refs: RFC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Summary

## Files changed

## Design highlights

## Privacy notes

## Tests / validation run

## Known open questions
```
