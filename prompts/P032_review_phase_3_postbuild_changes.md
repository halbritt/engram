# P032: Review Phase 3 Post-Build Guard and Repair Changes

> Prompt ordinal: P032. Introduced: 2026-05-05. Source commit: pending.

## Role

Preferred model: Codex GPT-5.5, fresh context.

You are a post-build reviewer. Your job is to review the coordinator's recent
Phase 3 repair and guard changes before larger post-build runtime slices.

## Read First

1. `README.md`
2. `HUMAN_REQUIREMENTS.md`
3. `DECISION_LOG.md`
4. `BUILD_PHASES.md`
5. `docs/claims_beliefs.md`
6. `docs/reviews/phase3/PHASE_3_PIPELINE_START_2026_05_05.md`
7. `docs/reviews/phase3/PHASE_3_PIPELINE_REPAIR_2026_05_05.md`
8. `src/engram/migrations.py`
9. `src/engram/cli.py`
10. `src/engram/extractor.py`
11. `migrations/README.md`
12. `migrations/004_source_kind_gemini.sql`
13. `migrations/005_source_kind_gemini.sql`
14. `migrations/006_claims_beliefs.sql`
15. `tests/test_migrations.py`
16. `tests/test_phase3_claims_beliefs.py`

## Review Scope

Review the recent changes for:

- migration checksum correctness and compatibility with existing live DBs,
- Phase 3 schema preflight false positives or false negatives,
- risk from restoring `004_source_kind_gemini.sql` while `005_source_kind_gemini.sql` exists,
- extractor salvage behavior for malformed individual claims,
- data-loss or raw-evidence mutation risk,
- test coverage gaps,
- whether bounded post-build runs can proceed safely after the guard changes.

Do not review unrelated Phase 3 implementation unless it directly affects
these changes.

## Constraints

- Do not patch code or docs.
- Do not run `pipeline-3`.
- Do not start a full-corpus run.
- Do not call external services.
- Run `git status --short` before writing.

## Output

Write:

```text
docs/reviews/phase3/PHASE_3_POSTBUILD_CHANGE_REVIEW_codex_gpt5_5_2026_05_05.md
```

Use this format:

- Summary verdict: `accept`, `accept_with_findings`, or `reject_for_revision`.
- Findings first, ordered by severity, with file/line references where
  possible.
- Explicit statement whether bounded post-build runs may proceed.
- Tests or checks you ran.

Then write marker:

```text
docs/reviews/phase3/postbuild/markers/01_CHANGE_REVIEW_codex_gpt5_5.ready.md
```

The marker must include verdict, review file path, files read, and next
expected step.
