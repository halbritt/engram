# Approved Grant Materialization Slice

Implement the RFC 0055 approved-grant processor.

Required:

1. Add `src/engram/entity_grounding_materialization.py`.
2. Add focused tests in `tests/test_entity_grounding_materialization.py`.
3. Consume only latest approved persisted RFC 0053 grants, with no later denied,
   revoked, or expired lifecycle row.
4. Verify the persisted grant before adapter invocation.
5. Record a dispatch audit row before provider I/O and a terminal dispatch audit
   row after success or sanitized failure where existing helpers allow it.
6. Invoke only an injected/configured `ClaimGroundingConfiguredSearchAdapter`;
   tests must use a mocked adapter and no live network.
7. Materialize sanitized provider rows into `entity_grounding_evidence` before
   recording a `claim_grounding.response.v1`.
8. Response candidates must cite real local `entity_grounding_evidence.id`
   values, not provider row ids.
9. Append `entity_identity_review_actions` only as
   `grounding_evidence_attach`; never merge, alias, split, or attach external
   ids automatically.
10. Keep provider secrets and private corpus text out of DB JSON, exceptions,
    and output.

Use maximum safe parallelism for file inspection and tests. You are not alone in
the codebase; stay inside the declared write scope and do not revert other
lanes.

Write `docs/reviews/rfc0054-0055-entity-grounding-workflow/MATERIALIZATION_HANDOFF.md`.

