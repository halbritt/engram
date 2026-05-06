---
loop: postbuild
issue_id: 20260506_limit500_run
family: repair_implementation_review
scope: phase3 pipeline-3 limit500 null-object repair implementation review
bound: limit500
state: ready
gate: ready_for_live_verification_ladder
classes: [prompt_or_model_contract_failure, downstream_partial_state, data_repair_needed]
created_at: 2026-05-06T04:00:00Z
linked_report: docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_REVIEW_claude_opus_4_7_2026_05_06.md
corpus_content_included: none
---

# Phase 3 Limit-500 Null-Object Repair Implementation Review (Claude Opus 4.7)

Verdict: `accept_with_findings`.

The uncommitted Phase 3 null-object repair implementation matches the amended
spec. Provenance is bumped, the strict request schema gains the reviewed
exact-one `oneOf` construct at the claim-item level, the relaxed schema
deliberately omits the construct under the strict-only path, the
validation-repair feedback adds a redacted null-object subsection that handles
both full sweeps and mixed sweeps, and the existing salvage and failure
semantics are preserved. New and extended tests cover strict-vs-relaxed schema
shape, full and mixed null-object feedback, provenance on extractions and
claims, failed repair, accepted-empty repair, and salvage preservation.

Worker-reported and locally re-confirmed verification:

- `tests/test_phase3_claims_beliefs.py`: 40 passed
- `make test`: 125 passed
- local extractor strict-schema health smoke: passed
- `git diff --check`: passed

Findings (all minor or informational):

- F1: relaxed-mode comment understates the chosen strict-only contract.
- F2: cosmetic blank line when no null-object section is rendered.
- F3: redundant guard in the full-sweep label expression.
- F4: mixed-sweep test does not assert the aggregate error counts still
  render.
- F5: informational - live `oneOf` enforcement is not proven by the smoke
  alone; same-bound rerun is the deciding evidence.

Review:

- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_REVIEW_claude_opus_4_7_2026_05_06.md`

This marker does not supersede:

- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`

Next expected step:

Run the live verification ladder, starting with `pipeline-3 --limit 0`,
then targeted selected-scope rerun for segment
`7bf2896a-00ab-4f75-a0ed-1ae684a2b4e9` or conversation
`0488c023-1b5a-44b6-8a8d-454283fb3b07`, then the same-bound
`pipeline-3 --limit 500` gate. The full-corpus Phase 3 run remains blocked
until the same-bound rerun passes the acceptance gate and a
`05_REPAIR_VERIFIED.ready.md` superseding marker is written.
