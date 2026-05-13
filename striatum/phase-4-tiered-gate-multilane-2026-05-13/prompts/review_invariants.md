# Review Phase 4 Audit And Transition Invariants

Review the fresh Tier 0-2 evidence for Engram's append-only and review-action
invariants.

Focus on:

- D017 corrections-as-captures rather than silent mutation;
- D044 no auto-promotion of beliefs to accepted;
- D052 transition API and audit pairing;
- `current_beliefs` filtering for rejected, superseded, closed, and invalid
  rows;
- accept, reject, pin, and correction action auditability;
- entity/edge rebuild idempotency and provenance completeness.

Lead with findings ordered by severity. Use `accept_with_findings` if the
evidence is useful but promotion remains blocked. Use `needs_revision` for any
silent mutation, unaudited transition, or auto-promotion claim.

Write `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/REVIEW_invariants.md`
with the exact lowercase `author:` line from the work packet.

