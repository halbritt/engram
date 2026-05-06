---
loop: postbuild
issue_id: 20260506_limit500_run
family: repair_spec
scope: phase3 pipeline-3 limit500 null-object repair spec
bound: limit500
state: ready
gate: ready_for_review
classes: [prompt_or_model_contract_failure, downstream_partial_state, data_repair_needed]
created_at: 2026-05-06T02:13:04Z
linked_report: docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_2026_05_06.md
corpus_content_included: none
---

# Phase 3 Limit-500 Null-Object Repair Spec Ready

The repair spec for the limit-500 prompt/schema/model contract blocker is ready
for review.

Spec:

- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_2026_05_06.md`

Review prompt:

- `prompts/P041_review_phase_3_limit500_null_object_repair_spec.md`

This marker does not supersede the blocked run marker:

- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`

Next expected step:

Run the repair-spec review. The full-corpus Phase 3 run remains blocked until
an implemented repair passes a same-bound `pipeline-3 --limit 500` rerun.
