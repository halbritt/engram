# RFC 0038 Second Repair Evidence

You are the tester for the RFC 0038 second repair. Do not edit implementation
files. Use the maximum useful number of sub-agents supported by your runtime for
parallel inspection or verification, but publish one evidence artifact.

## Goal

Verify that AC001 and AC002 are closed and that the prior accept-with-findings
repairs remain intact.

## Required Inputs

- `SECOND_REPAIR_BENCH_HANDOFF.md`
- `SECOND_REPAIR_INTERVIEW_HANDOFF.md`
- `ACCEPT_FINDINGS_EVIDENCE.md`
- `REVIEW_accept_findings_correctness_codex.md`

## Required Checks

Run focused checks sufficient to cover:

- Bench `/docs`, `/redoc`, and `/openapi.json` are not exposed.
- Interview same-origin POST protection accepts configured `::1` loopback
  origin and still rejects mismatched/untrusted origins.
- Focused interview and bench route tests remain green.
- Shared UI substrate tests remain green where touched by prior follow-ups.
- No-CDN scans include framework-generated routes or explicit route probes.
- `py_compile`, Ruff check/format where practical, `git diff --check`, and
  `make check-refs`.

Use the already-local user-site `PYTHONPATH` workaround for `httpx` if the
active virtualenv still lacks it. Do not install dependencies or use network.

## Evidence Artifact

Write
`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/SECOND_REPAIR_EVIDENCE.md`
with:

- Verdict: pass/fail.
- Environment notes, especially `httpx` availability.
- Exact commands and outcomes.
- AC001 and AC002 status.
- Not-run items and residual risk.

Do not edit source, tests, RFCs, changelog, or operator report.
