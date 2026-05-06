---
loop: postbuild
issue_id: 20260506_limit500_run
family: schema_rejection_findings
scope: phase3 pipeline-3 limit500 schema rejection findings
bound: limit500
state: ready
gate: ready_for_repair
classes: [prompt_or_model_contract_failure, downstream_partial_state, data_repair_needed]
created_at: 2026-05-06T04:25:00Z
linked_report: docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_FINDINGS_2026_05_06.md
corpus_content_included: none
---

# Phase 3 Limit-500 Schema Rejection Findings Ready

The limit-500 repair verification exposed a new schema-level failure class:

- `claim 0 does not match the schema`

The finding is recorded here:

- `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_FINDINGS_2026_05_06.md`

This marker does not supersede:

- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`
- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/05_REPAIR_VERIFICATION.blocked.md`

Next expected step:

Implement a schema-rejection repair, then rerun the targeted failed
conversations and the same-bound limit-500 gate before any full-corpus Phase 3
run.
