author: reviewer-codex-gpt-5.5-003

# RFC 0028 Final Review

Status: final_review
Date: 2026-05-09
RFC refs: RFC-0028
Decision refs: D-082
Phase refs: PHASE-0003, PHASE-0003-FOLLOWON

## Findings

No blocking findings.

## Review Notes

Predicate intent metadata is surfaced in both target paths. The extractor
runtime vocabulary carries `description` and `subject_kind_hint`, the prompt
version is bumped to `extractor.v9.d082.predicate-intent`, and
`build_extraction_prompt` renders an `intent:` line for each predicate without
changing the JSON output contract.

The schema change is additive and nullable: migration 012 adds
`predicate_vocabulary.subject_kind_hint`, seeds advisory values, and does not
touch raw evidence, claim, belief, or gold-label contracts. Phase 3 preflight
now treats `description` and `subject_kind_hint` as required vocabulary columns
and skips semantic SELECTs when required columns are absent, so missing RFC
0028 migration state reports as `Phase3SchemaPreflightError`.

CLI and web rendering stay unified through `engram.interview.render`.
`format_summary_line` emits separate summary, intent, and warning lines; the
web template renders those lines and preserves whitespace. The broadened
`false` rationale prompt is shared between CLI and web.

Accepted review findings were handled. L001 and L002 were fixed in code and
tests; L004 and L005 were applied; L003 was intentionally deferred because the
curated substring heuristic is advisory and render-only.

## Verification

Reviewed `IMPLEMENTATION_HANDOFF.md`, `FINDINGS_LEDGER.md`,
`REVISION_SYNTHESIS.md`, `REVISION_HANDOFF.md`, and the final diff for the
touched implementation and test files.

The revision handoff records:

```text
57 passed in 13.54s
git diff --check: passed
```

verdict: accept
