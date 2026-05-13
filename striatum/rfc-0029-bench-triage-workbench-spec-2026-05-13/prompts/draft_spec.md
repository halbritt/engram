# Draft Spec 0029 Bench Triage Workbench

Draft or revise `docs/specs/0029-bench-triage-workbench-spec.md` from RFC 0029
and its fresh legitimate design review. Update `docs/rfcs/0029-bench-triage-workbench.md`
and `docs/rfcs/README.md` only if needed to point future build work at the spec.

The spec must define:

This is a fresh provenance run after RFC 0032. Do not rely on quarantined
review artifacts as authoritative evidence. Treat existing spec text as draft
input only. If your runtime supports sub-agents, use the maximum useful number
of sub-agents for independent route, storage, security, UX, and test-contract
checks, with disjoint document ownership.

1. implementation modules;
2. artifact input contracts;
3. data-availability states;
4. classification tags and queue ordering;
5. scratch SQLite schema;
6. CLI commands;
7. web routes;
8. loopback and cross-origin protection;
9. UX wording requirements;
10. redacted export contract;
11. tests and acceptance criteria.

Do not include private corpus excerpts or raw claim text.

Write a spec handoff to:

`docs/reviews/rfc0029-bench-triage-workbench-spec-2026-05-13/SPEC_HANDOFF.md`

Use this structure:

```md
# RFC 0029 Bench Triage Workbench Spec Handoff
author: <packet author line>

Status: draft
Date: 2026-05-13
RFC refs: RFC-0029
Spec refs: SPEC-0029 (draft unless promoted by fresh review)
Decision refs: D020, D074
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Summary

## Files changed

## Contract highlights

## Privacy notes

## Tests / validation run

## Known open questions
```
