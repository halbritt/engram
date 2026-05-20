# Grounding Review Surface And Claim-use Gate

Specify the product/review surface required before network grounding can affect
claims, beliefs, or entity identity decisions.

Required outcome:

- Add `docs/specs/grounding-review-surface-and-claim-use-gate-v1.md`.
- Define the review UI/product surface, operator actions, audit/provenance
  fields, privacy-tier display, and distinction between evidence attachment and
  identity/claim mutation.
- Define the gate for claim-affecting use: required eval evidence, review
  actions, rollback behavior, and refusal modes.
- Keep LLM claim creation and network grounding separated by the broker/MCP
  boundary.
- State which parts require a future RFC before implementation.

Do not implement product UI code in this lane.

Publish
`docs/reviews/entity-grounding-broker-daemon-followups-2026-05-19/GROUNDING_REVIEW_SURFACE_GATE_HANDOFF.md`.
