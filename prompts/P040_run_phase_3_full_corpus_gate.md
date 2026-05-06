# P040: Run Phase 3 Full-Corpus Gate

This prompt is recorded for continuity but is inactive until the coordinator
confirms that `P039` produced a clean `pipeline-3 --limit 500` report under RFC
0013 gates.

Read before running:

1. `AGENTS.md`
2. `docs/process/phase-3-agent-runbook.md`
3. `docs/rfcs/0013-development-operational-issue-loop.md`
4. `docs/reviews/phase3/PHASE_3_POST_LIMIT50_EXPANSION_PLAN_2026_05_05.md`
5. the accepted `--limit 500` run report and marker

## Scope

Run the full-corpus Phase 3 pipeline only after coordinator authorization. Do
not edit source code. Do not delete or rewrite historical markers or run
reports.

This is a redacted operational run. You may report commands, counts, ids,
status values, and aggregate error classes. Do not include raw message text,
segment text, prompt payloads, model completions, conversation titles, claim
values, belief values, private names, or corpus-derived prose summaries.

## Commands

Run a no-work gate immediately before the full run:

```bash
.venv/bin/python -m engram.cli pipeline-3 --limit 0
```

Then run the full corpus:

```bash
.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5
```

## Required Status Output

Report status after:

- the no-work gate;
- the full-corpus command starts;
- periodic progress checks during the run;
- the full-corpus command exits.

When the command exits, return the same metric set required by `P039`, expanded
to the full active AI-conversation corpus.

If any gate fails, stop and return the blocker details. Do not attempt repair
without a coordinator instruction.
