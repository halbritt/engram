# P045 - Review Phase 3 Limit-500 Still-Invalid Problem

You are reviewing a redacted Phase 3 post-build operational problem
description. This is a review-only task.

## Read First

1. `AGENTS.md`
2. `docs/process/multi-agent-review-loop.md`
3. `docs/process/phase-3-agent-runbook.md`
4. `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_2026_05_06.md`
5. `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_REPAIR_RERUN_2026_05_06.md`

## Scope

Review the problem description and policy choice only. Do not edit source code,
run pipeline commands, inspect raw corpus content, or write the repair spec.

The key decision is whether a fully parsed, fully redacted,
all-invalid extraction after validation repair should:

- remain a hard operational failure, or
- become an extracted zero-claim result governed by dropped-claim quality
  accounting, or
- use a hybrid policy.

## Redaction Rules

Follow RFC 0013 discipline:

- Do not include raw message text, segment text, prompt payloads, model
  completions, conversation titles, extracted claim values, belief values,
  private names, or corpus-derived prose summaries.
- You may reference commands, counts, ids, status values, predicate names,
  object-shape diagnostics, and aggregate error classes.
- If you see redaction drift in the problem description, report it as a
  finding.

## Output

Return Markdown only. Do not modify files.

Use this structure:

```markdown
# Phase 3 Limit-500 Still-Invalid Problem Review - <model_slug>

Reviewer: <model_slug>
Date: 2026-05-06
Verdict: <accept | accept_with_findings | reject_for_revision | human_checkpoint>

## Summary

## Findings

### F1 - <severity>: <title>

<rationale, affected section, proposed fix>

## Recommended Policy

<Option A, B, C, or modified policy, with rationale>

## Required Spec Criteria

## Required Tests And Gates

## Redaction Review

## Open Questions
```

Severity should be one of `blocker`, `major`, `moderate`, or `minor`.

Choose `human_checkpoint` if the artifact is adequate for model review but the
next step depends on owner judgment rather than model synthesis alone.
