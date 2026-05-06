# P039: Run Phase 3 Limit-500 Gate

You are operating the Phase 3 post-limit-50 bounded expansion run.

Read before running:

1. `AGENTS.md`
2. `docs/process/phase-3-agent-runbook.md`
3. `docs/rfcs/0013-development-operational-issue-loop.md`
4. `docs/reviews/phase3/PHASE_3_POST_LIMIT50_EXPANSION_PLAN_2026_05_05.md`
5. `docs/reviews/phase3/PHASE_3_POSTBUILD_LIMIT50_VALIDATION_REPAIR_2026_05_05.md`

## Scope

Run only the no-work gate and the `--limit 500` bounded Phase 3 pipeline. Do not
start a full-corpus run. Do not edit source code. Do not delete or rewrite
historical markers or run reports.

This is a redacted operational run. You may report commands, counts, ids,
status values, and aggregate error classes. Do not include raw message text,
segment text, prompt payloads, model completions, conversation titles, claim
values, belief values, private names, or corpus-derived prose summaries.

## Commands

First confirm that the post-limit-50 owner checkpoint is superseded:

```bash
scripts/phase3_tmux_agents.sh next
```

Then run the no-work gate:

```bash
.venv/bin/python -m engram.cli pipeline-3 --limit 0
```

Then run the bounded gate:

```bash
.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 500
```

## Required Status Output

Report status after:

- the owner-checkpoint marker check;
- the no-work gate;
- the bounded command starts;
- the bounded command exits.

When the bounded command exits, return:

- command exit code;
- CLI summary lines;
- before/after global counts for `claim_extractions`, `claims`, `beliefs`,
  `belief_audit`, `contradictions`, failed extractions, dropped claims,
  validation-repair prior drops, failed extractor progress rows, failed
  consolidator progress rows, and active beliefs with orphan claim ids;
- selected-scope proof for the first 500 active AI conversations: selected
  conversations, active segments, latest extracted segments, latest failed
  segments, missing latest extractions, latest claim count, latest dropped
  claims, latest validation-repair prior drops, validation-repair attempts,
  failed extractor progress rows, failed consolidator progress rows, active
  beliefs with orphan claim ids;
- expanded dropped-claim gate:

  ```text
  (final dropped claims + validation-repair prior drops)
  / (inserted claims + final dropped claims + validation-repair prior drops)
  ```

If any gate fails, stop and return the blocker details. Do not attempt repair
without a coordinator instruction.
