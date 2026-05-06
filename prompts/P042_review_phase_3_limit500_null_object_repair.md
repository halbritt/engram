# Review Phase 3 Limit-500 Null-Object Repair Implementation

You are reviewing an uncommitted Phase 3 repair implementation for Engram.
Engram is local-first: do not use or request raw corpus content, prompt
payloads, model completions, conversation titles, claim values, belief values,
private names, or corpus-derived prose summaries. Use code, tests, process
docs, aggregate counts, ids, status values, predicate names, object-shape
diagnostics, and error classes only.

## Context

The bounded `pipeline-3 --limit 500` run is blocked by a prompt/schema/model
contract failure around null object channels. The reviewed repair spec has been
accepted with amendments and is ready for implementation.

The current worktree contains an uncommitted implementation from a fresh Codex
worker. Review the implementation diff against `HEAD`; do not modify source
files.

## Review These Files

Spec and review context:

- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_REVIEW_claude_opus_4_7_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_SYNTHESIS_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_FAILURE_FINDINGS_2026_05_06.md`

Implementation files:

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`

Useful commands:

```bash
git diff -- src/engram/extractor.py tests/test_phase3_claims_beliefs.py
```

## Worker-Reported Verification

The implementing worker reported:

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q`
  - result: `40 passed`
- `make test`
  - result: `125 passed`
- local extractor strict-schema health smoke: passed
- `git diff --check`: passed

You may rerun focused static checks or tests if needed, but do not run
long-running live corpus pipeline commands.

## Review Task

Look for correctness, auditability, redaction, and process-gate problems. In
particular:

1. Does the implementation match the amended repair spec?
2. Does strict schema generation use the reviewed exact-one `oneOf` shape?
3. Does relaxed schema behavior stay deliberate and limited to the reviewed
   fallback semantics?
4. Does null-object repair feedback cover full and mixed null/null drops while
   staying redacted?
5. Are prompt changes narrow and consistent with the reviewed additions?
6. Do the tests cover strict-vs-relaxed schema behavior, provenance, redacted
   repair feedback, failed repair, accepted empty repair, and salvage
   preservation?
7. Is any source behavior likely to hide model contract failures from the
   expanded dropped-claim gate?
8. Is the implementation ready for the live verification ladder, starting with
   `pipeline-3 --limit 0`, or must it be revised first?

Write your review to:

`docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_REVIEW_claude_opus_4_7_2026_05_06.md`

Also write a marker to:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/04_REPAIR_IMPLEMENTATION_REVIEW_claude_opus_4_7.ready.md`

If your verdict is `reject_for_revision` or `human_checkpoint`, use the same
marker path but with `.blocked.md` instead of `.ready.md`.

Use one of these verdicts: `accept`, `accept_with_findings`,
`reject_for_revision`, or `human_checkpoint`.

If you find issues, include severity, concrete file references, and the
required fix. Keep the review redacted under the rules above.
