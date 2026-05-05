# Prompt P036: Re-Review Phase 3 D063 Limit-10 Repair

You are Codex GPT-5.5 performing the same-model re-review required after a
`reject_for_revision` finding.

## Ground Rules

- Do not run `pipeline-3`, `extract`, `consolidate`, or any command that reads
  private corpus content.
- Do not inspect raw database rows, model prompts, model completions, message
  text, conversation titles, claim values, or belief values.
- Do not use network services or hosted APIs.
- Do not patch files. This is a review-only pass.
- Keep all tracked artifacts redacted: counts, file paths, commands, and marker
  names are allowed; private content is not.
- Do not write absolute machine-specific home-directory paths.

## Required Reading

Read these files:

- `AGENTS.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `docs/schema/README.md`
- `docs/process/multi-agent-review-loop.md`
- `docs/process/project-judgment.md`
- `docs/process/phase-3-agent-runbook.md`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/rfcs/0014-operational-artifact-home.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_LIMIT10_REPAIR_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REVIEW_codex_gpt5_5_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REVIEW_claude_opus_4_7_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REVIEW_gemini_pro_3_1_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REVIEW_SYNTHESIS_2026_05_05.md`
- `src/engram/cli.py`
- `src/engram/extractor.py`
- `scripts/phase3_tmux_agents.sh`
- `tests/test_phase3_claims_beliefs.py`
- `tests/test_phase3_tmux_agents.py`

## Review Scope

Review only whether the corrected repair resolves the prior findings:

1. `run_extract_batches` must stop after a failed batch, including a full
   failed batch.
2. Chunked relaxed-schema fallback must preserve chunk-local evidence bounds
   before claims are merged.
3. Post-build marker gating must not allow unrelated ready markers to suppress
   blockers, and must treat blocked gates as blockers.
4. The additional accepted findings may be checked: internal extraction batches
   stop after a failure, recursive split retry budget is bounded, and the next
   report plan includes dropped-claim rate.

## Allowed Checks

You may run static and test commands that do not inspect private content:

- `bash -n scripts/phase3_tmux_agents.sh`
- `git diff --check`
- `scripts/phase3_tmux_agents.sh next`
- `.venv/bin/python -m pytest -q tests/test_phase3_claims_beliefs.py::test_run_extract_batches_stops_after_failed_batch tests/test_phase3_claims_beliefs.py::test_chunked_relaxed_schema_output_is_salvaged_against_chunk_ids tests/test_phase3_claims_beliefs.py::test_extract_pending_claims_stops_internal_batch_after_failure tests/test_phase3_tmux_agents.py`

Do not run broad pipeline commands.

## Required Output

Write the review to:

`docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REREVIEW_codex_gpt5_5_2026_05_05.md`

Write the marker to:

`docs/reviews/phase3/postbuild/markers/20260505_limit10_runtime_repair/08_REPAIR_REREVIEW_codex_gpt5_5.ready.md`

If you accept the corrected repair, the marker front matter must include:

```yaml
state: ready
gate: ready_for_same_bound_rerun
verdict: accept
supersedes: docs/reviews/phase3/postbuild/markers/20260505_limit10_runtime_repair/06_REPAIR_REVIEW_codex_gpt5_5.ready.md
```

If you reject the corrected repair, use:

```yaml
state: ready
gate: blocked
verdict: reject_for_revision
```

The review must include:

- verdict: `accept`, `accept_with_findings`, or `reject_for_revision`;
- whether the next same-bound `--limit 10` post-build run may proceed;
- findings ordered by severity, with file references;
- checks run;
- explicit note that private corpus content was not inspected.
