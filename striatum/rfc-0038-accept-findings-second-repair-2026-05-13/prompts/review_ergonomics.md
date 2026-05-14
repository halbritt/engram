# RFC 0038 Second Repair Ergonomics Review

You are a fresh ergonomics design reviewer. Do not edit implementation or
tests. Review the second repair against RFC 0038,
`ENGRAM_UI_REWORK_HANDOFF.md`, the accepted ergonomics review, and
`SECOND_REPAIR_EVIDENCE.md`.

## Required Focus

- The repair must preserve the shared chrome, cross-surface navigation,
  keyboard behavior, status-banner semantics, and first-time operator flow
  accepted by the prior ergonomics review.
- Disabling generated docs/openapi should not remove operator-facing UI
  affordances promised by the handoff.
- IPv6 loopback support should not create confusing copy or misleading audit
  footer behavior.
- Carry-forward polish findings may remain non-blocking if they are unchanged
  and honestly tracked.

## Artifact

Write
`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_second_repair_ergonomics_claude.md`.

Use a Striatum finding artifact format with a clear verdict:

- `accept` if the ergonomics posture is preserved.
- `accept_with_findings` for non-blocking polish items.
- `needs_revision` for regressions that materially confuse the operator or
  break accepted cross-surface affordances.

Include verification performed and not-run items.
