---
schema_version: striatum.decision.v1
decision_id: "dec_ebb9faef92ac4e39b1a5f7f7c8d3773c"
run_id: "run_500d0f049ea04038b0e19d6045daf918"
artifact_kind: decision
owner: human
outcome: accepted_with_follow_up
follow_up_required: true
title: "Route contract-coherence needs-revision to repair cycle"
created_at: "2026-05-14T14:57:44Z"
---

# Route contract-coherence needs-revision to repair cycle

Decision ID: `dec_ebb9faef92ac4e39b1a5f7f7c8d3773c`
Run ID: `run_500d0f049ea04038b0e19d6045daf918`
Outcome: `accepted_with_follow_up`

## Rationale

The contract-coherence reviewer found blocking RFC coherence issues. Do not override the review; launch a bounded repair cycle against RFC 0045, RFC 0046, and RFC 0049, then rerun contract-coherence review before resuming the original Striatum run.

## Follow-Up

Run parallel repair workers for RFC 0045 contract identity/lifecycle fields, RFC 0046 projection generation/invalidation semantics, and RFC 0049 upstream/Level 2/no-egress/golden-query traceability; then run a fresh contract-coherence re-review and use accepted re-review evidence to resolve the checkpoint.
