# RFC 0038 Second Repair Security Review

You are a fresh local-first/security reviewer. Do not edit implementation or
tests. Review the second repair against AGENTS.md, RFC 0038,
`ENGRAM_UI_REWORK_HANDOFF.md`, the failed correctness review, and
`SECOND_REPAIR_EVIDENCE.md`.

## Required Focus

- No cloud, CDN, telemetry, hosted auth, or external persistence.
- Bench generated docs/openapi routes must not create a no-CDN escape hatch.
- Interview IPv6 loopback origin support must not broaden accepted hosts beyond
  local loopback/operator-approved origins.
- CSRF/same-origin enforcement, bind validation, Tier 1 ceiling, and audit copy
  must remain intact.

## Artifact

Write
`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_second_repair_security_claude.md`.

Use a Striatum finding artifact format with a clear verdict:

- `accept` if the security posture is clean.
- `accept_with_findings` for non-blocking residual security observations.
- `needs_revision` for local-first, no-CDN, origin/CSRF, bind, privacy-tier, or
  provenance regressions.

Include verification performed and not-run items.
