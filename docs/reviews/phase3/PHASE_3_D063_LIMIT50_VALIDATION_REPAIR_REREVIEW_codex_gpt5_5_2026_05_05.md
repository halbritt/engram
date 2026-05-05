# Phase 3 D063 Limit50 Validation-Repair Re-Review

Date: 2026-05-05
Reviewer: Codex GPT-5.5
Verdict: `accept`

This re-review stayed within the redaction boundary: code, tests, process docs,
aggregate counts, status values, ids, and error classes only. I did not inspect
raw corpus content, runtime prompt payloads, model completions, conversation
titles, claim values, or belief values.

## Scope Reviewed

- `docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_REVIEW_codex_gpt5_5_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_REVIEW_SYNTHESIS_2026_05_05.md`
- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/process/phase-3-agent-runbook.md`

## Prior Findings

### Resolved: successful validation repair hid the initial all-invalid response

The revised extractor now carries the failed pre-repair validation diagnostics
forward into successful and failed repair outcomes.

- `src/engram/extractor.py:492` through `src/engram/extractor.py:504` still
  enters validation repair only for the zero-survivor validation-failure case.
- `src/engram/extractor.py:826` through `src/engram/extractor.py:888` now stores
  `validation_repair.prior_dropped_count`, `prior_error_counts`, and redacted
  `prior_dropped_claims` on both repair-call failure and completed repair calls.
- `src/engram/extractor.py:922` through `src/engram/extractor.py:952` redacts the
  prior drops to diagnostics allowed by the boundary: reason/error class, index,
  split path, predicate, stability class, object-channel shape, object JSON keys,
  and evidence-message count. It does not carry subject text, object values,
  evidence ids, rationale, prompt payloads, or model completions.
- `src/engram/extractor.py:974` through `src/engram/extractor.py:980` copies that
  metadata to the root `raw_payload.validation_repair`, so proof queries do not
  need to parse only nested `parse_metadata`.
- `tests/test_phase3_claims_beliefs.py:604` through
  `tests/test_phase3_claims_beliefs.py:718` cover successful empty repair and
  successful valid repair while preserving the redacted prior-drop diagnostics.
- `tests/test_phase3_claims_beliefs.py:719` through
  `tests/test_phase3_claims_beliefs.py:748` covers the still-invalid repair
  path and records `result: still_invalid`.

The reported same-bound gate now includes validation-repair prior drops in the
dropped-claim denominator. The selected-scope proof also reports zero validation
repair attempts for the same-bound rerun, so RFC 0013's prompt/model contract
failure blocker is not implicated by this rerun.

### Resolved: retry count semantics were not pinned for non-default retries

The repair pass now calls `extract_segment_chunks(..., retries=0,
adaptive_split=False)` at `src/engram/extractor.py:839` through
`src/engram/extractor.py:847`. That prevents non-default extractor retry
settings from multiplying repair attempts and prevents adaptive splitting from
turning a repair-call exception into multiple model calls.

`tests/test_phase3_claims_beliefs.py:750` through
`tests/test_phase3_claims_beliefs.py:786` pins the non-default retry case by
calling extraction with extra retries and asserting a repair parse/runtime
failure is not retried.

## New Blockers

None found.

## Watch Item

The process docs still phrase the default dropped-claim blocker generically as
"dropped-claim rate" over inserted plus dropped claims. The synthesis and
reported proof use the correct expanded gate:

```text
final dropped claims + validation-repair prior drops
```

That is sufficient for this re-review. Future run-report templates should keep
that expanded definition explicit so the gate does not drift back to counting
only `raw_payload.dropped_claims`.

## Verification

Locally reran:

```bash
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q
```

Result: `39 passed`.

I also reviewed the reported verification from the synthesis and prompt:
focused tests `39 passed`, full suite `124 passed`, no-work `pipeline-3
--limit 0` exited `0`, targeted extraction rerun exited `0`, and same-bound
`pipeline-3 --limit 50` exited `0` with no failed latest selected-scope
extractions, no missing latest extractions, no failed progress rows, and no
active beliefs with orphan claim ids.
