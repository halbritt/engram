# P035: Review Phase 3 Limit-10 Repair

> Prompt ordinal: P035. Introduced: 2026-05-05. Source commit: pending.

## Role

You are a fresh post-build repair reviewer for Engram, a local-first personal
memory system. Your job is to review the D063 / limit-10 repair before the next
larger bounded Phase 3 post-build run.

## Read First

1. `AGENTS.md`
2. `README.md`
3. `HUMAN_REQUIREMENTS.md`
4. `DECISION_LOG.md`
5. `BUILD_PHASES.md`
6. `docs/process/multi-agent-review-loop.md`
7. `docs/process/project-judgment.md`
8. `docs/process/phase-3-agent-runbook.md`
9. `docs/rfcs/0013-development-operational-issue-loop.md`
10. `docs/rfcs/0014-operational-artifact-home.md`
11. `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`
12. `docs/reviews/phase3/PHASE_3_POSTBUILD_LIMIT10_REPAIR_2026_05_05.md`
13. `docs/reviews/phase3/postbuild/markers/03_LIMIT10_RUN.blocked.md`
14. `docs/reviews/phase3/postbuild/markers/20260505_limit10_runtime_repair/05_REPAIR_VERIFIED.ready.md`
15. `src/engram/extractor.py`
16. `src/engram/cli.py`
17. `scripts/phase3_tmux_agents.sh`
18. `tests/test_phase3_claims_beliefs.py`

## Review Scope

Review the recent D063 / limit-10 repair for:

- correctness of bounded/adaptive Phase 3 extraction;
- whether chunking can create false provenance or duplicate/fragmented claims;
- retry behavior after a failed extraction batch;
- whether failed/old derived rows remain auditable and cannot poison active
  beliefs;
- marker precedence and `supersedes:` handling in `scripts/phase3_tmux_agents.sh`;
- RFC 0013 compliance, including redaction, no raw corpus content in tracked
  artifacts, old-marker provenance, and gates before expansion;
- test coverage gaps and operational blind spots;
- whether the next bounded post-build run may proceed.

Do not review unrelated Phase 3 implementation unless it directly affects this
repair.

## Constraints

- Do not patch code or docs.
- Do not run `pipeline-3`, `extract`, or `consolidate`.
- Do not inspect raw private corpus content or database rows.
- Do not call external services.
- Do not move files into a proposed `docs/operations/` area; RFC 0013 is only a
  proposal for later review.
- Run `git status --short` before writing.
- Do not include machine-specific absolute paths, home-directory names, raw
  message text, segment text, prompt payloads, model completions, claim values,
  belief values, private names, exact conversation titles, or corpus-derived
  summaries in the review.

## Output

Write one review file under `docs/reviews/phase3/` and one marker under
`docs/reviews/phase3/postbuild/markers/20260505_limit10_runtime_repair/`.

Use the output paths provided by the coordinator injection. Use this structure:

```markdown
# Phase 3 Limit-10 Repair Review - <model>

Date: 2026-05-05
Reviewer: <model>
Verdict: <accept|accept_with_findings|reject_for_revision>
Bounded post-build runs may proceed: <yes|no|only after findings addressed>

## Findings

### <Severity>: <title>

<finding with file/line references where possible and a proposed fix>

## Non-Findings

## Checks Run

## Files Read
```

The marker must include:

- verdict;
- review file path;
- files read;
- checks run;
- next expected step.
