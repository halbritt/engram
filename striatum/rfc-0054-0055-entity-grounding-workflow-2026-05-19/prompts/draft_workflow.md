# Draft Entity Grounding Workflow Slice

Implement the RFC 0054 draft-only entity grounding batch workflow.

Required:

1. Add `src/engram/entity_grounding_workflow.py`.
2. Add focused tests in `tests/test_entity_grounding_workflow.py`.
3. Select active `entity_kind='unknown'` rows deterministically by tenant,
   corpus, privacy tier, confidence, created time, and id.
4. Run local lookup first through `search_grounding_evidence`.
5. For local hits, append `entity_identity_review_actions` rows with
   `action_kind='grounding_evidence_attach'`; do not create network grants.
6. For local misses, persist a valid RFC 0053 request plus draft grant. The
   request must use opaque `claims` source refs from `entities.source_claim_ids`;
   do not invent an `entities` source-ref target table.
7. Keep draft ids deterministic and reruns idempotent.
8. Keep raw claim, belief, message, segment, capture, and context text out of
   all draft and grant payloads.
9. Drafting must not call the network or instantiate configured network
   adapters.

Use maximum safe parallelism for file inspection and tests. You are not alone in
the codebase; stay inside the declared write scope and do not revert other
lanes.

Write `docs/reviews/rfc0054-0055-entity-grounding-workflow/DRAFT_WORKFLOW_HANDOFF.md`.

