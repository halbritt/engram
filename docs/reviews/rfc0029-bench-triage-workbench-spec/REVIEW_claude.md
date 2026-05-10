# Spec 0029 Bench Triage Workbench Review - Claude
author: reviewer-claude-opus-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0029
Spec refs: SPEC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### F001 - Rationale handling needs a stronger private-text invariant
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md § Scratch SQLite State; § Redacted Export
Rationale: The spec correctly avoids raw segment and claim text columns, but the free-form `rationale` fields can still receive pasted private excerpts. The contract should define a shared sanitizer, a length cap, and a storage/export invariant that no automatic path copies segment text, claim text, evidence excerpts, or LLM responses into review state or tracked artifacts.

### F002 - Data-state precedence should be explicit
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md § Data Availability
Rationale: Several data states can overlap unless the spec defines precedence. For example, a zero-claim candidate with prior data could be interpreted as `candidate_zero` or `complete`, and a missing prior can overlap with malformed candidate data. The implementation needs a single precedence ladder so queue ordering and disabled controls are deterministic.

### F003 - Read-only production access is stated but not mechanically tested
Severity: minor
Source: docs/specs/0029-bench-triage-workbench-spec.md § Boundaries; § Tests
Rationale: The spec says production PostgreSQL is read-only for this feature, but the test list does not require an import or storage-boundary check that prevents the web/storage modules from writing production claim, belief, audit, or evidence tables. A focused test should pin the no-production-write boundary.

## Open questions

No owner input is required. The findings can be handled during the revision pass.

verdict: accept_with_findings
