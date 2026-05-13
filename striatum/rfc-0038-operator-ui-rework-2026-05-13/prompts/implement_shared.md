# Implement RFC 0038 Shared Web Substrate

Read first:

- `AGENTS.md`
- `ENGRAM_UI_REWORK_HANDOFF.md`
- `docs/rfcs/0038-operator-ui-rework.md`
- `docs/rfcs/0027-interview-web-ui.md`
- `docs/rfcs/0029-bench-triage-workbench.md`

Use the maximum useful number of native sub-agents internally if your runtime
supports them. Keep ownership inside the shared substrate slice.

Implement only the shared web substrate for RFC 0038:

- `src/engram/web/` shared package for UI tokens, small Jinja partials, static
  asset helpers, local-only audit footer copy, future-slot rendering, status
  chip semantics, and no-CDN checks.
- Package/test support needed for the shared substrate.
- Do not modify interview or bench-review domain behavior.
- Do not add cloud, telemetry, hosted auth, remote asset, or JS build pipeline.

Required artifact:

`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/IMPLEMENT_SHARED_HANDOFF.md`

Use this shape:

```md
# RFC 0038 Shared Web Substrate Handoff
author: <packet author line>

Status: implemented
Date: 2026-05-13
RFC refs: RFC-0038

## Summary
## Files Changed
## Shared Components
## No-CDN / Local-Only Checks
## Tests Run
## Residual Risk
```
