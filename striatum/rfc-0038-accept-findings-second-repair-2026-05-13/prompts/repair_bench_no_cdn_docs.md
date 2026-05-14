# RFC 0038 Bench No-CDN Generated Docs Repair

You are the implementer for the bench lane. You are not alone in this codebase:
other lanes may be editing disjoint paths. Do not revert or overwrite unrelated
changes. Use the maximum useful number of sub-agents supported by your runtime
for investigation or implementation, while keeping final writes inside your
allowed paths.

## Goal

Close AC001 from
`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_accept_findings_correctness_codex.md`.

The bench FastAPI app must not expose generated `/docs`, `/redoc`, or
`/openapi.json` routes that reference CDN assets. Preserve the local-first and
no-CDN posture from RFC 0038.

## Required Work

- Read `AGENTS.md`, `ENGRAM_UI_REWORK_HANDOFF.md`,
  `docs/rfcs/0038-operator-ui-rework.md`, and the AC001 finding.
- Modify only `src/engram/bench_review/web.py`,
  `tests/test_bench_review.py`, and your required handoff artifact.
- Disable bench generated docs/openapi routes at app construction.
- Add focused tests asserting `/docs`, `/redoc`, and `/openapi.json` are not
  exposed for the bench app.
- Run focused bench tests and any quick static checks needed to support your
  handoff.

## Handoff Artifact

Write
`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/SECOND_REPAIR_BENCH_HANDOFF.md`
with:

- Summary of source changes.
- Tests/commands run and outcomes.
- Explicit statement of AC001 status.
- Any residual risk or environment limitations.

Do not edit `CHANGELOG.md`, `OPERATOR_REPORT.md`, RFC files, migration files,
or interview/shared surfaces.
