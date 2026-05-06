# Review Phase 3 Limit-500 Schema Rejection Repair

You are reviewing an uncommitted Phase 3 repair implementation for Engram.
Engram is local-first: do not use or request raw corpus content, prompt
payloads, model completions, conversation titles, claim values, belief values,
private names, or corpus-derived prose summaries. Use code, tests, process
docs, aggregate counts, ids, status values, object-shape diagnostics, and error
classes only.

## Context

The v6 null-object repair fixed the originally failed segment but introduced a
new live failure class during same-bound `pipeline-3 --limit 500` verification:

`claim 0 does not match the schema`

The failures happened before Python could parse model output into claim drafts,
so there were no dropped claims, no validation-repair prior drops, and no
redacted claim-shape diagnostics. A fresh Codex worker implemented the lower
risk repair from P043: remove model-facing `oneOf`, keep local Python
validation authoritative, and bump extractor provenance to v7/v9.

The current worktree contains the uncommitted implementation. Review the diff
against `HEAD`; do not modify source files.

## Review These Files

Finding and prompt context:

- `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_FINDINGS_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_LIVE_RERUN_2026_05_06.md`
- `prompts/P043_fix_phase_3_limit500_schema_rejection.md`

Implementation files:

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`

Useful command:

```bash
git diff -- src/engram/extractor.py tests/test_phase3_claims_beliefs.py
```

## Worker-Reported Verification

The implementing worker reported:

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q`
  - result: `40 passed in 20.06s`
- `make test`
  - result: `125 passed in 46.31s`

You may rerun focused checks or tests if needed, but do not run live corpus
pipeline commands.

## Review Task

Look for correctness, auditability, redaction, and process-gate problems. In
particular:

1. Does the implementation match P043 and the schema-rejection findings?
2. Is model-facing `oneOf` removed from the default request schema?
3. Does the schema still require both `object_text` and `object_json` fields?
4. Are object-channel value types permissive enough for Python parse/salvage to
   see locally invalid null/null shapes?
5. Is strict local exact-one validation preserved?
6. Is null-object validation-repair feedback preserved for full and mixed
   null/null drops?
7. Are validation-repair prior drops still recorded so the expanded
   dropped-claim gate can catch hidden model contract failures?
8. Are tests adequate for default/relaxed schema behavior, null/null parse
   before local drop, redacted repair feedback, provenance, failed repair,
   accepted-empty repair, and salvage preservation?
9. Is this ready for coordinator-controlled live verification of the two new
   failed conversations and then the same-bound limit-500 gate?

Write your review to:

`docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_REPAIR_REVIEW_claude_opus_4_7_2026_05_06.md`

Also write a marker to:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/07_SCHEMA_REJECTION_REPAIR_REVIEW_claude_opus_4_7.ready.md`

If your verdict is `reject_for_revision` or `human_checkpoint`, use the same
marker path but with `.blocked.md` instead of `.ready.md`.

Use one of these verdicts: `accept`, `accept_with_findings`,
`reject_for_revision`, or `human_checkpoint`.

If you find issues, include severity, concrete file references, and the
required fix. Keep the review redacted under the rules above.
