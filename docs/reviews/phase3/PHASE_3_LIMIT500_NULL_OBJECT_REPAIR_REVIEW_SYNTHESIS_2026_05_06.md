# Phase 3 Limit-500 Null-Object Repair Implementation Review Synthesis

Date: 2026-05-06

Subject implementation files:

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`

Review:
`docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_REVIEW_claude_opus_4_7_2026_05_06.md`

Reviewer verdict: `accept_with_findings`

Synthesis verdict: `accepted_with_minor_repairs`

This synthesis follows RFC 0013. It contains commands, counts, ids, status
values, predicate names, file paths, line references, and aggregate error
classes only. It does not include raw message text, segment text, prompt
payloads, model completions, conversation titles, claim values, belief values,
private names, or corpus-derived prose summaries.

## Summary

Claude Opus accepted the implementation and found no blockers for the live
verification ladder. Four minor findings were accepted and addressed before
live execution. One informational finding was retained as verification
guidance.

## Finding Dispositions

### F1 - Relaxed-mode comment precision

Disposition: `accepted_and_resolved`

The schema comment now states that the shared schema-construction fallback
drops both the message-id enum and the `oneOf` branch, with prompt rules plus
Python validation remaining authoritative in relaxed mode.

### F2 - Cosmetic blank line without null-object section

Disposition: `accepted_and_resolved`

`build_validation_repair_feedback` now renders the null-object diagnostics
section conditionally, avoiding an extra blank line when no null/null drops are
present.

### F3 - Redundant full-sweep guard

Disposition: `accepted_and_resolved`

The redundant `len(redacted) > 0` guard was removed from the full-sweep label
expression. The function still returns before labeling when there are no
null/null drops.

### F4 - Mixed-sweep aggregate-count assertion

Disposition: `accepted_and_resolved`

The mixed-sweep feedback test now asserts that both the null/null exact-one
error count and the non-null-object validation error count remain rendered
alongside the targeted null-object subsection.

### F5 - Live oneOf enforcement not proven by smoke alone

Disposition: `accepted_as_informational`

No code change was required. The strict-schema smoke proves schema construction,
not runtime enforcement of `oneOf` for non-empty claim items. The targeted
selected-scope rerun and same-bound `--limit 500` gate remain the deciding
evidence.

## Current Gate

This synthesis does not supersede the blocked limit-500 run marker:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`

The implementation is ready for the live verification ladder after focused
tests pass on the minor repairs.
