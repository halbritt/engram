# RFC 0038 Second Repair Correctness Review

You are a fresh correctness reviewer. Do not edit implementation or tests.
Review the second repair against RFC 0038, the failed accept-findings
correctness review, the new handoffs, and `SECOND_REPAIR_EVIDENCE.md`.

## Required Focus

- AC001: bench must not expose CDN-backed generated docs/openapi routes.
- AC002: interview must accept configured IPv6 loopback same-origin POSTs
  without weakening origin enforcement.
- The prior accept-with-findings fixes must not regress.
- Evidence must be current and must cover the actual generated route behavior,
  not just template/static files.

## Artifact

Write
`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_second_repair_correctness_codex.md`.

Use a Striatum finding artifact format with a clear verdict:

- `accept` if there are no blocking/major correctness issues.
- `accept_with_findings` if only non-blocking residuals remain.
- `needs_revision` if AC001/AC002 remain open or a new blocker/major
  correctness regression is introduced.

Include findings with severity, affected files, verification commands, and
not-run items.
