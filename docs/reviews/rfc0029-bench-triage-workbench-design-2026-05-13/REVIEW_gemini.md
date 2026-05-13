# RFC 0029 Bench Triage Workbench Review - gemini
author: operator [self-declared: rfc0029-design-review-gemini-trusted]

Status: review
Date: 2026-05-13
RFC refs: RFC-0029
Decision refs: D020, D074
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### F001 - Read-Only Postgres Role Provisioning Mechanism
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md: Open Questions 3
Rationale: The RFC mandates mechanical read-only access (connecting with a read-only role and/or `SET TRANSACTION READ ONLY`), but defers the provisioning path of the role. Forcing the implementation agent to invent a database role management strategy during implementation risks diverging from the established Engram database setup patterns. The follow-on spec must freeze whether role creation happens in a migration, in a setup script, or is gracefully degraded to just transaction-level guards in v1.

### F002 - Missing Batch "Exclude Unchanged" Capability
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md: Classification Model
Rationale: The RFC notes that v1 does not provide batch decisions, but limits potential batching to "exclude unchanged items". If a benchmark has thousands of unchanged segments, forcing the operator to manually press `x` for each unchanged item defeats the ergonomic goals of the workbench. The spec must define a first-class batch action to exclude unchanged items, or automatically mark `unchanged` segments as excluded from review obligations by default, so the operator can focus strictly on the deltas.

### F003 - Keyboard Ergonomics for Confidence Adjustments
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md: Screen Design
Rationale: The UI mandates a confidence control (low/medium/high, default medium) and states that "decision keys submit the currently selected confidence". This implies keyboard operators must use the mouse or Tab navigation to change confidence before pressing a decision shortcut like `r` (flag regression). To preserve the pace-of-reading goal, the spec should consider adding a keyboard shortcut (e.g., `c`) to cycle the confidence level without losing focus.

### F004 - Friction with Redacted Benchmark Artifacts
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md: Screen Design (Promotion readiness)
Rationale: The RFC correctly blocks readiness on semantic changes for `candidate_redacted` items because the private text is missing. However, since the default extraction bench policy is redacted (as seen in RFC 0028), operators will frequently load redacted artifacts and immediately hit a wall on their first semantic delta. The CLI `serve` command should parse the run's metadata at startup and emit a console warning if the loaded artifact is redacted but contains semantic deltas, prompting the operator to run a `--include-claim-text` scratch benchmark before they start triaging.

## Open questions

1. Should the SQLite review state include the schema version or migration version of the workbench, to support future backwards compatibility if the tool evolves?
2. Does the `SET TRANSACTION READ ONLY` guard apply broadly enough to cover implicit framework connections if the implementation uses a connection pool?

verdict: accept_with_findings
