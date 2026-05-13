# Review RFC 0029 Bench Triage Workbench

Review `docs/rfcs/0029-bench-triage-workbench.md` against Engram's local-first
requirements and the operator problem it is meant to solve.

## Checklist

1. Does the RFC materially reduce cognitive overhead compared with the current
   Markdown review artifacts?
2. Is the local-first/privacy posture complete: loopback-only, no CDN, no
   telemetry, no cloud dependency, no raw private text in tracked exports?
3. Is scratch-local SQLite review state the right v1 boundary, and does it keep
   production tables immutable?
4. Are queue classifications precise enough to drive review: zeroed,
   count-changed, predicate-mix, high-drop, provenance, unchanged?
5. Is the route surface sufficient without drifting into a general dashboard?
6. Are CLI commands coherent with existing phase-scoped command names?
7. Is the export contract strict enough to prevent accidental private-data
   publication?
8. Is the implementation plan small and testable?
9. Are acceptance criteria specific enough for a later implementation workflow?
10. Are there conflicts with RFC 0017, RFC 0019, RFC 0024, RFC 0027, or RFC
    0028?

Write to the exact path in the packet. Use this structure:

```md
# RFC 0029 Bench Triage Workbench Review - <lane>
author: <packet author line>

Status: review
Date: 2026-05-13
RFC refs: RFC-0029
Decision refs: D020, D074
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### F001 - <title>
Severity: <blocking | major | minor | nit>
Source: <path:line or section>
Rationale: <paragraph>

## Open questions

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Do not modify files outside the path specified by the job packet.
