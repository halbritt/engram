# P049 - Bounded Review Phase 3 Limit-500 Still-Invalid Repair

You are Claude Opus reviewing the implemented Phase 3 limit-500
still-invalid repair. This is a bounded review-only task.

The broader P048 review prompt caused local CLI hangs before returning output,
so this prompt deliberately narrows the context.

## Inspect

Use only these inputs:

1. `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_REPAIR_SPEC_2026_05_06.md`
2. implementation commit `90aa8b0` relative to parent `050a372`
3. build marker
   `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/14_STILL_INVALID_REPAIR_BUILT.ready.md`

Suggested commands:

```bash
git show --stat 90aa8b0
git show --unified=80 90aa8b0 -- src/engram/extractor.py tests/test_phase3_claims_beliefs.py docs/claims_beliefs.md docs/reviews/phase3/postbuild/markers/20260506_limit500_run/14_STILL_INVALID_REPAIR_BUILT.ready.md
```

Do not run tests. Do not run live pipeline commands. Do not edit files.

## Review Questions

1. Does the implementation faithfully implement D064 / Option C?
2. Are clean-zero and accounted-zero queryably distinct?
3. Are parse/schema/repair-service/missing-diagnostic/unredacted/unknown paths
   still hard failures?
4. Are accounted-zero diagnostics redacted at persisted diagnostic paths,
   including `raw_payload.dropped_claims`, `validation_repair`, and
   `parse_metadata.chunk_dropped_claims`?
5. Does dropped-claim accounting match the repair spec formula?
6. Do accounted-zero rows avoid extractor failure counts and consolidator skip
   behavior?
7. Are tests sufficient to proceed to smoke/live gates?

## Output

Return Markdown only:

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

Use `reject_for_revision` for any finding that should block smoke/live gates.
