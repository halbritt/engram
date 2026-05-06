# P048 - Review Phase 3 Limit-500 Still-Invalid Repair

You are Claude Opus reviewing the implemented Phase 3 limit-500
still-invalid repair. This is a review-only task.

## Read First

1. `AGENTS.md`
2. `docs/process/multi-agent-review-loop.md`
3. `docs/process/phase-3-agent-runbook.md`
4. `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_REPAIR_SPEC_2026_05_06.md`
5. `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/14_STILL_INVALID_REPAIR_BUILT.ready.md`

## Review Scope

Review implementation commit `90aa8b0` relative to its parent. Focus on:

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`
- `docs/claims_beliefs.md`
- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/14_STILL_INVALID_REPAIR_BUILT.ready.md`

Do not edit files. Do not run live pipeline commands. You may inspect source,
tests, docs, and git diffs.

## Required Review Questions

1. Does the implementation faithfully implement D064 / Option C?
2. Are clean-zero and accounted-zero queryably distinct?
3. Are parse/schema/repair-service/missing-diagnostic/unredacted/unknown paths
   still hard failures?
4. Are accounted-zero diagnostics redacted at every persisted diagnostic path,
   including `raw_payload.dropped_claims`, `validation_repair`, and
   `parse_metadata.chunk_dropped_claims`?
5. Does dropped-claim accounting match the repair spec formula?
6. Do accounted-zero rows avoid extractor failure counts and consolidator
   skip behavior?
7. Are tests sufficient for the policy and edge cases?
8. Is the documentation accurate?

## Redaction Rules

Follow RFC 0013. Do not include raw message text, segment text, prompt
payloads, model completions, conversation titles, extracted claim values,
belief values, private names, or corpus-derived prose summaries.

## Output

Return Markdown only, using this structure:

```markdown
# Phase 3 Limit-500 Still-Invalid Repair Review - claude_opus_4_7

Reviewer: claude_opus_4_7
Date: 2026-05-06
Verdict: <accept | accept_with_findings | reject_for_revision>

## Summary

## Findings

### F1 - <severity>: <title>

<rationale, affected file/section, proposed fix>

## Tests Reviewed

## Redaction Review

## Recommendation
```

Severity should be one of `blocker`, `major`, `moderate`, or `minor`.

Use `reject_for_revision` for any finding that should block smoke/live gates.
