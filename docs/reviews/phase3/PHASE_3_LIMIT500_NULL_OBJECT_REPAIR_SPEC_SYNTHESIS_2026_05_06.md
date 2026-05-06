# Phase 3 Limit-500 Null-Object Repair Spec Review Synthesis

Date: 2026-05-06

Subject:
`docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_2026_05_06.md`

Review:
`docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_REVIEW_claude_opus_4_7_2026_05_06.md`

Reviewer verdict: `accept_with_findings`

Synthesis verdict: `accepted_with_amendments`

This synthesis follows RFC 0013. It contains commands, counts, ids, status
values, predicate names, file paths, and aggregate error classes only. It does
not include raw message text, segment text, prompt payloads, model completions,
conversation titles, claim values, belief values, private names, or
corpus-derived prose summaries.

## Summary

Claude Opus accepted the repair direction and raised two major findings about
schema implementation precision, plus minor findings about mixed-pattern
feedback, test-scope clarity, marker details, prompt-change scope, and
selected-scope stability.

The major findings were accepted. The spec has been amended before source-code
implementation so the repair cannot silently hide backend schema limitations or
lose RFC 0013 marker semantics.

## Finding Dispositions

### F1 - JSON Schema construct and support detection

Disposition: `accepted`

The spec now names `oneOf` as the preferred strict-schema construct at the
claim-item level and requires explicit support detection:

- non-relaxed schema assertion;
- relaxed-schema assertion;
- live backend smoke step before relying on schema-level enforcement.

### F2 - Relaxed-schema fallback interaction

Disposition: `accepted`

The spec now requires the implementation to choose and test either:

- strict-only exact-one schema, where relaxed mode deliberately omits `oneOf`
  and relies on prompt plus Python validation; or
- a separate fallback class for exact-one schema rejection.

The existing message-id relaxed-schema fallback must not silently mask new
schema regressions.

### F3 - Mixed null-object sweeps

Disposition: `accepted_with_modification`

The original spec triggered targeted feedback only when all drops shared the
null/null shape. The amended spec now requires a null-object subsection whenever
any null/null exact-one drops are present. Full sweeps and mixed sweeps are
labeled separately.

### F4 - Test scope clarity

Disposition: `accepted`

The test section now says existing validation-repair tests should be extended
rather than duplicated. It also adds the missing strict-vs-relaxed schema
assertion and same-bound provenance proof requirement.

### F5 - Superseding marker schema

Disposition: `accepted`

The spec now pins the post-rerun marker path:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/05_REPAIR_VERIFIED.ready.md`

It also pins `family: repair_verified`, `gate:
ready_for_full_corpus_gate`, and the `supersedes:` field pointing to the
existing blocked marker.

### F6 - Prompt change scope

Disposition: `accepted`

The prompt section now distinguishes existing rules to retain from new additive
rules to add, reducing unnecessary prompt churn.

### F7 - Selected-scope stability

Disposition: `accepted`

The same-bound acceptance gate now requires a no-ingestion assertion and
records the ordered first and last selected conversation ids for the rerun. If
the selected-scope boundary may have shifted, the result must go to human
checkpoint or frozen-scope proof.

### F8 - Predicate names in repair feedback

Disposition: `accepted`

The spec now states that predicate names are fixed vocabulary metadata, not
corpus content, while preserving the ban on subject values, object values, and
evidence text.

## Current Gate

The review and synthesis do not supersede the blocked limit-500 run marker.
The full-corpus Phase 3 run remains blocked by:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`

Next step is source-code implementation of the amended repair spec, followed
by the verification ladder and same-bound `pipeline-3 --limit 500` gate.
