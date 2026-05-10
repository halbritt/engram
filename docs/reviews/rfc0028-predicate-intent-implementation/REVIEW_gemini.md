# RFC 0028 Predicate Intent Implementation Review — gemini
author: reviewer-gemini-3.1-pro-preview-002

Status: review
Date: 2026-05-09
RFC refs: RFC-0028
Decision refs: D082
Phase refs: PHASE-0003, PHASE-0003-FOLLOWON

## Findings

### F001 — Web UI rendering of indented summary lines may collapse whitespace
Severity: nit
Source: `src/engram/interview/templates/question.html:11`
Rationale: The `format_summary_line` helper intentionally adds a two-space indent (e.g., `  intent:` and `  [warning]`) to align the intent and warning lines nicely under the main target summary in the CLI. In the web template, these lines are iterated and rendered inside generic `<div>` tags. Unless the `.summary-line` CSS class includes `white-space: pre` or `white-space: pre-wrap`, standard browser behavior will collapse the leading whitespace, causing a slight visual parity mismatch with the CLI's indented layout. This does not affect functionality but may slightly reduce visual hierarchy in the web UI.

## Open questions

verdict: accept
