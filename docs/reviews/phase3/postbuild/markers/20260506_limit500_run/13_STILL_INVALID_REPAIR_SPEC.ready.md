---
loop: postbuild
issue_id: 20260506_limit500_run
family: repair_spec
scope: phase3 pipeline-3 limit500 validation-repair still-invalid repair
bound: limit500
state: ready
gate: ready_for_builder
classes: [validation_repair_still_invalid, derived_state_policy_change, quality_gate_unverified]
created_at: 2026-05-06T06:46:39Z
linked_spec: docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_REPAIR_SPEC_2026_05_06.md
supersedes: docs/reviews/phase3/postbuild/markers/20260506_limit500_run/12_STILL_INVALID_POLICY_ACCEPTED.ready.md
corpus_content_included: none
---

# Phase 3 Limit-500 Still-Invalid Repair Spec Ready

The D064 Option C hybrid accounted-zero repair spec is ready for the builder.

Builder execution remains limited to the spec handoff. A repair-verified marker
requires focused tests, full tests, no-work gate, targeted rerun, targeted
consolidation, same-bound limit-500 rerun, and a redacted run report proving the
10% expanded dropped-claim gate.
