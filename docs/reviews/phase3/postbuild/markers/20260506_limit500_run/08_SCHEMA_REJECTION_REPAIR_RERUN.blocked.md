---
loop: postbuild
issue_id: 20260506_limit500_run
family: repair_verification
scope: phase3 pipeline-3 limit500 schema rejection repair live rerun
bound: limit500
state: blocked
gate: blocked_for_expansion
classes: [validation_repair_still_invalid, downstream_partial_state, quality_gate_unverified]
created_at: 2026-05-06T05:56:16Z
linked_report: docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_REPAIR_RERUN_2026_05_06.md
corpus_content_included: none
---

# Phase 3 Limit-500 Schema Rejection Repair Rerun Blocked

The schema-rejection repair passed local tests, review, no-work live gating,
and targeted reruns of the prior schema-failed conversations.

The same-bound `pipeline-3 --limit 500` rerun was stopped after a new hard
extraction failure:

- latest v7 selected-scope extraction failures: 1
- failed extractor progress rows: 1
- failed consolidator progress rows: 1
- missing latest v7 selected-scope extractions after coordinator stop: 389

Report:

- `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_REPAIR_RERUN_2026_05_06.md`

This marker does not supersede:

- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`

The pinned ready marker was not written:

- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/05_REPAIR_VERIFIED.ready.md`

Next expected step:

Specify and review a repair for `validation_repair.result = still_invalid`
cases before another same-bound limit-500 rerun. Full-corpus Phase 3 remains
blocked.
