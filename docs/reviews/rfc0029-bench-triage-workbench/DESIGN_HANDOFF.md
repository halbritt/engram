# RFC 0029 Bench Triage Workbench Design Handoff
author: author-codex-gpt-5.5-002

Status: draft
Date: 2026-05-09
RFC refs: RFC-0029
Decision refs: D020, D074, D-082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Summary

Drafted RFC 0029 as a local-only FastAPI/Jinja2/htmx workbench for reviewing
extraction and re-extraction benchmark deltas. The design targets the immediate
RFC 0028 100-segment bench bottleneck: aggregate metrics passed, but zeroed and
count-changed segments still require human semantic validation.

The proposed UI presents one suspicious segment at a time, with risk chips,
prior/candidate claim structure, local excerpts, verdict controls, keyboard
shortcuts, queue filters, scratch-local progress, and redacted export.

## Files Changed

- `docs/rfcs/0029-bench-triage-workbench.md`
- `docs/rfcs/README.md`
- `striatum/rfc-0029-bench-triage-workbench-design/`
- `docs/reviews/rfc0029-bench-triage-workbench/DESIGN_HANDOFF.md`

## Design Highlights

- V1 is a private operator tool, not canonical data infrastructure.
- Review decisions write to `.scratch/benchmarks/extraction-review/<run-id>/review.sqlite3`.
- Production claim, belief, audit, and raw-evidence tables are read-only from
  this surface.
- Queue classification covers zeroed, newly nonzero, count changed,
  high-drop, predicate-mix changed, provenance anomaly, and unchanged segments.
- Default tracked export is aggregate/redacted and omits segment text, claim
  text, and notes.
- The route and frontend posture mirrors RFC 0027: loopback-only FastAPI,
  Jinja2 templates, vendored htmx, no build pipeline, no CDN.

## Privacy Notes

No private corpus excerpts or raw claim text were copied into tracked design
artifacts. RFC 0029 references the RFC 0028 bench report and scratch artifact
categories but keeps the publication contract redacted by default.

## Tests / Validation Run

- `jq empty striatum/rfc-0029-bench-triage-workbench-design/workflow.json`
- `.venv/bin/striatum workflow validate striatum/rfc-0029-bench-triage-workbench-design/workflow.json`

## Known Open Questions

- Whether review state should remain SQLite-only after v1 or eventually become
  an append-only Postgres artifact.
- Whether the benchmark harness should emit candidate claim text for UI display
  as scratch-only data.
- Whether Phase 4 should get an alias for the bench-review command once the
  pre-full-corpus gate depends on it.
- Whether "safe to promote" should be purely derived or require an explicit
  run-level operator verdict.
