# P033: Review RFC 0013 Operational Issue Loop

You are reviewing an RFC for Engram, a local-first personal memory system.

Read these files first:

1. `AGENTS.md`
2. `docs/rfcs/0013-development-operational-issue-loop.md`
3. `docs/process/multi-agent-review-loop.md`
4. `docs/process/project-judgment.md`
5. `docs/process/phase-3-agent-runbook.md`
6. `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`
7. `DECISION_LOG.md`

Review stance:

- Find process holes, unsafe gates, missing human checkpoints, local-first
  regressions, data-integrity risks, and vague acceptance criteria.
- Do not edit the RFC directly.
- Write one review file under `docs/reviews/phase3/`.
- Write one marker under `docs/reviews/phase3/postbuild/markers/`.
- Use verdict `accept`, `accept_with_findings`, or `reject_for_revision`.

Required review structure:

```markdown
# RFC 0013 Review - <model>

Date: 2026-05-05
Reviewer: <model>
Verdict: <accept|accept_with_findings|reject_for_revision>

## Findings

### <Severity>: <title>

<finding with affected sections and proposed fix>

## Non-Findings

## Checks Run

## Files Read
```

Use the model slug and output paths provided by the coordinator injection below.
