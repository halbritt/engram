# Grant Lifecycle Slice

Implement the append-only RFC 0053 grant lifecycle scaffold.

Read `src/engram/claim_grounding_runtime.py`,
`tests/test_claim_grounding_runtime.py`, and
`migrations/024_claim_grounding_runtime.sql`.

Required:

1. Add helpers for draft, approved, denied, revoked, and expired grant lineage
   rows without updating existing grant rows.
2. Add a verifier that proves a request's network grant is approved, live,
   unrevoked, unexpired, and bound to the exact query, target adapter, tenant,
   corpus, purpose, and privacy tier before dispatch.
3. Keep dispatch helper behavior deterministic and no-network.
4. Add focused tests for approved, denied, revoked, expired, query mismatch,
   target mismatch, and privacy mismatch.

Write `docs/reviews/rfc0053-runtime-completion/GRANT_LIFECYCLE_HANDOFF.md`.
