# Durable Dispatch Boundary

Close the crash-before-commit and direct-concurrency residuals from the daemon
final review.

Required outcome:

- Introduce a durable local claim/lease/dispatch-preparation boundary before
  provider I/O so a daemon crash after network I/O cannot silently erase the
  fact that the approved grant was attempted.
- Preserve append-only audit semantics. Do not update raw evidence or provider
  evidence rows in place.
- Make direct concurrent materializer callers return a clean skipped/claimed
  result or otherwise avoid noisy unique-index failures.
- Preserve the restricted broker role authority; new tables/functions must be
  covered by provisioning and security tests if privileges change.
- Add deterministic DB-backed tests. No live network calls.

Suggested surfaces:

- `migrations/025_claim_grounding_dispatch_claims.sql`
- `src/engram/claim_grounding_runtime.py`
- `src/engram/entity_grounding_materialization.py`
- `src/engram/entity_grounding_daemon.py`
- `tests/test_claim_grounding_runtime.py`
- `tests/test_entity_grounding_materialization.py`
- `tests/test_entity_grounding_daemon.py`

Publish
`docs/reviews/entity-grounding-broker-daemon-followups-2026-05-19/DURABLE_DISPATCH_BOUNDARY_HANDOFF.md`.
