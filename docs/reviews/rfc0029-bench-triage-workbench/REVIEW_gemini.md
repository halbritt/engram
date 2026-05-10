# RFC 0029 Bench Triage Workbench Review — gemini
author: reviewer-gemini-3.1-pro-preview-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### F001 — Keyboard Shortcut Conceptual Collision with RFC 0027
Severity: minor
Source: Screen design
Rationale: The proposed keyboard shortcut `f` is bound to "needs follow-up", while in the RFC 0027 Interview Web UI, `f` is bound to "false". An operator context-switching between gold-label interviewing and benchmark triage might reflexively press `f` intending a negative verdict ("regression") but accidentally trigger "needs follow-up". Consider binding "needs follow-up" to `u` (unsure/unresolved) or another key to avoid this muscle-memory collision, or explicitly accept the context boundary.

### F002 — Export Command Output Path Specification
Severity: nit
Source: CLI commands
Rationale: The text states `export` writes to a "caller-supplied tracked path" and refuses paths outside `docs/reviews/` unless `--allow-outside-reviews` is passed. It should be made explicit whether the path is a positional argument (e.g., `engram phase3 bench-review export <run-id> <path>`) or a named flag (e.g., `--output <path>`) to align with existing CLI conventions.

### F003 — Run-Level Promotion Verdict
Severity: minor
Source: Open Questions (Question 4)
Rationale: Regarding whether "safe to promote" should be derived or explicit: The 11 zeroed segments from the RFC 0028 benchmark run highlight that the overall run's viability isn't merely the sum of independent segment verdicts, but an operator's synthesis of the *types* of regressions found. Implementing an explicit run-level "Safe to Promote" toggle or button on the landing page/summary page would permanently capture the operator's final synthesis in the SQLite review database.

### F004 — Fallback for Missing Prior-Run Artifacts
Severity: nit
Source: Shape
Rationale: The workbench loads "optional prior-run benchmark artifacts for direct run-to-run comparison." The specification should ensure that the UI gracefully degrades (e.g., querying production Postgres for prior state instead, or omitting the delta column) if the prior artifact is not provided, rather than crashing or rendering blank columns.

## Open questions

1. Should the `skip` decision on a segment exclude it from the "reviewed count" progress header, or does skipping count as a completed operator action for the sake of queue burn-down?
2. If an operator updates their decision (e.g., changing from `needs_followup` to `good_drop`), does the `decided_at` timestamp in the `segment_reviews` table overwrite the original, or should the table support an append-only history of decisions for a single segment?

verdict: accept
