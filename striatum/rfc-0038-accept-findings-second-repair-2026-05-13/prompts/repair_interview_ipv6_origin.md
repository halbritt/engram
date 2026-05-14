# RFC 0038 Interview IPv6 Loopback Origin Repair

You are the implementer for the interview lane. You are not alone in this
codebase: other lanes may be editing disjoint paths. Do not revert or overwrite
unrelated changes. Use the maximum useful number of sub-agents supported by
your runtime for investigation or implementation, while keeping final writes
inside your allowed paths.

## Goal

Close AC002 from
`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_accept_findings_correctness_codex.md`.

The interview app already accepts `::1` as a loopback bind host. Mutating POST
routes must accept same-origin browser requests from `http://[::1]:<port>` when
the app is configured for an IPv6 loopback bind, without weakening loopback-only
binding, allowed-origin policy, or local-first constraints.

## Required Work

- Read `AGENTS.md`, `ENGRAM_UI_REWORK_HANDOFF.md`,
  `docs/rfcs/0038-operator-ui-rework.md`, and the AC002 finding.
- Modify only `src/engram/interview/web.py`, `tests/test_interview_web.py`,
  and your required handoff artifact.
- Add or derive `::1` support for the interview origin allowlist in the
  configured loopback bind path.
- Add focused regression tests for IPv6 loopback Origin behavior. Include a
  negative check if needed to prove the change does not become a broad origin
  bypass.
- Run focused interview tests and any quick static checks needed to support
  your handoff.

## Handoff Artifact

Write
`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/SECOND_REPAIR_INTERVIEW_HANDOFF.md`
with:

- Summary of source changes.
- Tests/commands run and outcomes.
- Explicit statement of AC002 status.
- Any residual risk or environment limitations.

Do not edit `CHANGELOG.md`, `OPERATOR_REPORT.md`, RFC files, migration files,
or bench/shared surfaces.
