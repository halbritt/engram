# Implement RFC 0038 Bench Review UI Slice

Read first:

- `AGENTS.md`
- `ENGRAM_UI_REWORK_HANDOFF.md`
- `docs/rfcs/0038-operator-ui-rework.md`
- `docs/rfcs/0029-bench-triage-workbench.md`

Use the maximum useful number of native sub-agents internally if your runtime
supports them. Keep ownership inside the bench-review slice.

Implement only the bench triage UI rework:

- Update bench-review templates/static and only the route helpers needed for
  queue filters, summary state, segment detail, prior/candidate deltas,
  readiness, decision posture, redaction/unavailable/failed states, and
  responsive behavior.
- Preserve scratch-local review state and production-read-only posture.
- Do not change interview files.
- Do not imply gate approval or production mutation.

Required artifact:

`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/IMPLEMENT_BENCH_HANDOFF.md`

Use this shape:

```md
# RFC 0038 Bench Review UI Handoff
author: <packet author line>

Status: implemented
Date: 2026-05-13
RFC refs: RFC-0038, RFC-0029

## Summary
## Files Changed
## Bench Review Flow Changes
## Truthfulness / Scratch-State Preservation
## Tests Run
## Residual Risk
```
