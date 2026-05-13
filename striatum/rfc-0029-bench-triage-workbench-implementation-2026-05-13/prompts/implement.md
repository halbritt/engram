# Implement RFC 0029 Bench Triage Workbench

Implement Spec 0029:

`docs/specs/0029-bench-triage-workbench-spec.md`

Required outputs:

This is a fresh provenance run after RFC 0032. Do not rely on quarantined
review artifacts as authoritative evidence. Treat the existing implementation
as code to audit and repair against the fresh draft spec, not as accepted
architecture. If your runtime supports sub-agents, delegate implementation,
security, CLI/export, web/UX, and tests to the maximum useful number of
sub-agents, with disjoint file ownership and no reverts of other agents' work.

- `src/engram/bench_review/` modules, templates, and static assets.
- `engram phase3 bench-review serve|status|export` CLI commands.
- Focused tests covering the spec's required behavior.
- `CHANGELOG.md` update.
- `docs/reviews/rfc0029-bench-triage-workbench-implementation-2026-05-13/IMPLEMENTATION_HANDOFF.md`.

The handoff must use:

```md
# RFC 0029 Bench Triage Workbench Implementation Handoff
author: <packet author line>

Status: implemented
Date: 2026-05-13
RFC refs: RFC-0029
Spec refs: SPEC-0029 (draft unless promoted by fresh review)
Decision refs: D020, D074
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Summary

## Files changed

## Implementation notes

## Tests / validation run

## Residual risk
```

Do not write private corpus text into tracked artifacts.
