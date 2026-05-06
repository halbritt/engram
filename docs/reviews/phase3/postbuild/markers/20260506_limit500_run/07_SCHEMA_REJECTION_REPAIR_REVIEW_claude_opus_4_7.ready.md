---
loop: postbuild
issue_id: 20260506_limit500_run
family: schema_rejection_repair_review
scope: phase3 pipeline-3 limit500 schema rejection repair review
bound: limit500
state: ready
gate: ready_for_live_verification_ladder
classes: [prompt_or_model_contract_failure, downstream_partial_state, data_repair_needed]
created_at: 2026-05-06T05:05:00Z
linked_report: docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_REPAIR_REVIEW_claude_opus_4_7_2026_05_06.md
corpus_content_included: none
---

# 07 - Schema Rejection Repair Review (Claude Opus 4.7) - ready

Date: 2026-05-06

Reviewer: Claude Opus 4.7

Verdict: `accept_with_findings`

Review document:

- `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_REPAIR_REVIEW_claude_opus_4_7_2026_05_06.md`

Reviewed implementation:

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`

Spec, finding, and prior context:

- `prompts/P043_fix_phase_3_limit500_schema_rejection.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_FINDINGS_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_LIVE_RERUN_2026_05_06.md`

Local verification reproduced:

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q` -> `40 passed in 22.41s`

Findings (none blocking):

- F1 minor: no parse-then-local-drop test for the inverse exact-one
  (both-populated) violation. Optional follow-up.
- F2 minor: schema parity assertion uses in-place mutation to compare
  strict vs relaxed. Functionally correct; optional refactor for
  readability.
- F3 info: empty-string `object_text` is now rejected at schema level
  rather than at Python validation. Caught either way; documented for
  future-failure context.

Next coordinator-controlled step: requeue and rerun the two newly failed
conversations (`0030fb7d-d9a2-48e2-9a70-c19281cbb520`,
`00394f4c-0794-4807-9853-b3117385e82e`), then run the same-bound
`pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 500`
gate per the verification ladder in the schema-rejection findings.

The pinned ready marker
`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/05_REPAIR_VERIFIED.ready.md`
remains unwritten and may only be added if the same-bound limit-500 gate
passes.
