# RFC 0029 Bench Triage Workbench Spec Handoff
author: author-codex-gpt-5.5-001

Status: draft
Date: 2026-05-09
RFC refs: RFC-0029
Spec refs: SPEC-0029
Decision refs: D020, D074, D-082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Summary

Spec 0029 promotes RFC 0029 into a concrete implementation contract for the
Bench Triage Workbench. It defines module boundaries, benchmark artifact input
normalization, scratch SQLite state, CLI commands, local web routes, UX
requirements, redacted export behavior, and required tests.

## Files changed

- `docs/specs/0029-bench-triage-workbench-spec.md`
- `docs/rfcs/0029-bench-triage-workbench.md`
- `docs/rfcs/README.md`
- `CHANGELOG.md`
- `striatum/rfc-0029-bench-triage-workbench-spec/`

## Contract highlights

The spec keeps production PostgreSQL read-only, stores review decisions only in
scratch SQLite, refuses non-loopback serve hosts with exit status 8, disables
strong verdict controls for missing or malformed candidate data, and keeps the
tracked export strictly redacted.

## Privacy notes

Tracked artifacts define field names, aggregate counts, paths, identifiers, and
decisions only. They do not include private segment text, raw claim text,
evidence excerpts, or LLM responses.

## Tests / validation run

Pending Striatum workflow validation and review execution.

## Known open questions

No owner input is required before implementation. The main residual risk is
artifact-shape tolerance across historical benchmark outputs; the spec handles
that by requiring tolerant loaders and metadata-only fallback states.
