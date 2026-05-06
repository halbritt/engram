---
loop: postbuild
issue_id: 20260506_limit500_run
family: repair_verification
scope: phase3 pipeline-3 limit500 null-object repair live rerun
bound: limit500
state: blocked
gate: blocked_for_expansion
classes: [prompt_or_model_contract_failure, downstream_partial_state, data_repair_needed]
created_at: 2026-05-06T04:20:01Z
linked_report: docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_LIVE_RERUN_2026_05_06.md
corpus_content_included: none
---

# Phase 3 Limit-500 Repair Verification Blocked

The null-object repair passed the no-work gate and the targeted failed-scope
rerun, but the same-bound `pipeline-3 --limit 500` verification hit a new
schema-level extractor failure class and was stopped by the coordinator.

Blocking conditions:

- 2 latest v6 selected-scope extraction failures
- 717 missing latest v6 selected-scope extractions after coordinator stop
- failed extractor progress rows present
- failed consolidator progress row present

Report:

- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_LIVE_RERUN_2026_05_06.md`

This marker does not supersede:

- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`

The pinned ready marker was not written:

- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/05_REPAIR_VERIFIED.ready.md`

Next expected step:

Investigate the strict `oneOf` schema rejection path before another same-bound
limit-500 rerun. Full-corpus Phase 3 remains blocked.
