# Re-Review Phase 3 Limit50 Validation-Repair Patch

You are Codex GPT-5.5 re-reviewing a revised Phase 3 post-build repair after
your prior `reject_for_revision`.

Stay within the redaction boundary: code, tests, process docs, aggregate counts,
status values, ids, and error classes only. Do not inspect or include raw corpus
content, runtime prompt payloads, model completions, conversation titles, claim
values, or belief values.

## Prior Review

Read:

- `docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_REVIEW_codex_gpt5_5_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_REVIEW_SYNTHESIS_2026_05_05.md`

Your prior findings were:

1. Major: successful validation repair hid the initial all-invalid response from
   the dropped-claim gate.
2. Minor: validation-repair retry count semantics were not pinned for
   non-default extractor retry settings.

## Revised Patch

Review:

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/process/phase-3-agent-runbook.md`

Changes since the rejected version:

- Extractor provenance now uses:
  - `extractor.v5.d063.validation-repair-audited`
  - `ik-llama-json-schema.d034.v7.extractor-8192-validation-repair-audited`
- Successful and failed validation repairs now copy repair metadata to
  `raw_payload.validation_repair`.
- `raw_payload.validation_repair.prior_dropped_claims` stores redacted
  per-claim diagnostics for the failed pre-repair attempt: error class, index,
  predicate, stability class, object-channel shape, object JSON keys, and
  evidence-message count. It omits subject text, object values, evidence IDs,
  rationale, prompt payloads, and model completions.
- Validation repair now passes `retries=0`.
- Validation repair disables adaptive splitting for repair-call exceptions, so
  the repair pass remains one model attempt if the repair call itself fails.
- Tests now cover:
  - successful empty repair with redacted prior-drop diagnostics;
  - successful valid repair with redacted prior-drop diagnostics;
  - still-invalid repair remains failed and records `result: still_invalid`;
  - non-default extractor retries do not cause multiple repair attempts.

## Verification Already Run

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q`
  - result: `39 passed`
- `make test`
  - result: `124 passed`
- `.venv/bin/python -m engram.cli pipeline-3 --limit 0`
  - result: exit `0`
- `.venv/bin/python -m engram.cli extract --segment-id 0ba65036-8546-4f14-b661-57dbf069defc`
  - result: exit `0`; `0 claims created / 1 segments processed / 0 failed`
- `.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 50`
  - result: exit `0`
  - extraction summary: `410 claims created / 66 segments processed / 0 failed`
  - consolidation summary: `50 conversations processed / 0 skipped / 383 beliefs created / 22 superseded / 22 contradictions`

Selected-scope v5 proof after the same-bound rerun:

- selected conversations: 50
- active segments: 67
- latest extracted segments: 67
- latest failed segments: 0
- missing latest extractions: 0
- latest claim count: 410
- latest dropped claims: 42
- latest validation-repair prior drops: 0
- latest v5 segments: 67
- validation repair attempts: 0
- failed extractor progress rows: 0
- failed consolidator progress rows: 0
- active beliefs with orphan claim IDs: 0

Dropped-claim gate including validation-repair prior drops:

- final dropped claims: 42
- validation-repair prior drops: 0
- rate: 42 / (410 + 42 + 0) = 9.3%

## Re-Review Task

Determine whether the two prior findings are resolved and whether any new
blocker exists.

Write your re-review to:

`docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_REREVIEW_codex_gpt5_5_2026_05_05.md`

Use one of these verdicts: `accept`, `accept_with_findings`,
`reject_for_revision`, or `human_checkpoint`.

Do not modify source files.
