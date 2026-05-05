# Review Phase 3 Limit50 Validation-Repair Patch

You are reviewing a Phase 3 post-build repair for Engram. Engram is local-first:
do not use or request raw corpus content, prompt payloads, model completions,
conversation titles, claim values, or belief values. Use code, tests, process
docs, aggregate counts, ids, status values, and error classes only.

## Context

The previous bounded `pipeline-3 --limit 50` run was blocked by one latest
failed extraction. The failed row had `failure_kind=trigger_violation`; both
dropped claims were predicate `has_name` with `object_text=null` and
`object_json=null`. A prompt v3 repair had already reduced the selected-scope
dropped-claim rate below the RFC 0013 threshold, but the single failed segment
still blocked expansion.

The current patch adds a narrow validation-repair retry:

- Keep the validator strict.
- If a model response is schema-valid but all emitted claims fail local
  pre-insert validation, call the local extractor once more with a redacted
  validation-feedback section that lists error classes and counts.
- The retry must produce valid claims or an empty claim list. If it is still
  invalid, the extraction remains failed.
- Bump extractor provenance to:
  - `extractor.v4.d063.validation-repair`
  - `ik-llama-json-schema.d034.v6.extractor-8192-validation-repair`

Review these files:

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/process/phase-3-agent-runbook.md`

## Verification Already Run

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q`
  - result: `36 passed`
- `make test`
  - result: `121 passed`
- `.venv/bin/python -m engram.cli extract --segment-id 0ba65036-8546-4f14-b661-57dbf069defc`
  - result: exit `0`; `0 claims created / 1 segments processed / 0 failed`
- `.venv/bin/python -m engram.cli pipeline-3 --limit 0`
  - result: exit `0`; no work
- `.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 50`
  - result: exit `0`
  - extraction summary: `410 claims created / 66 segments processed / 0 failed`
  - consolidation summary: `50 conversations processed / 0 skipped / 383 beliefs created / 22 superseded / 22 contradictions`

Selected-scope proof for the first 50 active AI-conversation conversations after
the same-bound rerun:

- selected conversations: 50
- active segments: 67
- latest extracted segments: 67
- latest failed segments: 0
- missing latest extractions: 0
- latest claim count: 410
- latest dropped claims: 42
- latest v4 segments: 67
- failed extractor progress rows: 0
- failed consolidator progress rows: 0
- active beliefs with orphan claim IDs: 0
- selected-scope latest dropped-claim rate: 42 / (410 + 42) = 9.3%

Latest dropped-claim reason counts:

- `exactly one of object_text or object_json is required`: 39
- `predicate requires object_json`: 2
- `predicate requires non-empty object_text`: 1

## Review Task

Look for correctness, auditability, and process-gate problems. In particular:

1. Does the validation-repair retry preserve D058 per-claim salvage semantics
   and the "failed only when zero claims survive and errors remain" rule?
2. Does it risk hiding model contract failures that RFC 0013 should block?
3. Are retry diagnostics enough for redacted operational review?
4. Are the tests adequate for the new behavior?
5. Is it safe to allow a superseding ready marker for the prior limit50 blocked
   marker if no findings remain?

Write your review to:

`docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_REVIEW_codex_gpt5_5_2026_05_05.md`

Use one of these verdicts: `accept`, `accept_with_findings`,
`reject_for_revision`, or `human_checkpoint`.

If you find issues, include severity, concrete file references, and the required
fix. Do not modify source files.
