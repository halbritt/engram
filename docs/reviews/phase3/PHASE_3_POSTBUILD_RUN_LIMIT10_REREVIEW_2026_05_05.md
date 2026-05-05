# Phase 3 Post-Build Same-Bound Run After Re-Review: Limit 10

Date: 2026-05-05

## Verdict

`ready_for_next_bound`

The same-model Codex re-review accepted the corrected D063 repair. The
same-bound `pipeline-3 --limit 10` run completed successfully after that
acceptance.

This report is redacted under RFC 0013. It contains commands, counts, status
values, and aggregate proof-query results only. It does not include raw message
text, segment text, prompt payloads, model completions, conversation titles,
claim values, belief values, or corpus-derived summaries.

## Preconditions

- `make test`: `119 passed`
- `bash -n scripts/phase3_tmux_agents.sh`: passed
- `git diff --check`: passed
- home-directory path scan over touched files: no matches
- `scripts/phase3_tmux_agents.sh next`: `complete`
- no-work gate `.venv/bin/python -m engram.cli pipeline-3 --limit 0`: passed

## Command

```bash
.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 10
```

Result: exit code `0`.

CLI summary:

- extract: 0 claims created / 0 segments processed / 0 failed
- consolidate: 10 conversations processed / 0 skipped / 5 beliefs created /
  5 superseded / 5 contradictions

No extractor requests were needed in this same-bound rerun because the selected
segments already had current extracted rows.

## Aggregate Counts

Before the run:

- `claim_extractions`: 38
- `claims`: 388
- `beliefs`: 360
- `belief_audit`: 483
- `contradictions`: 7
- failed extractions: 3
- dropped claims: 63
- failed extractor progress rows: 0
- failed consolidator progress rows: 0
- active beliefs with orphan claim ids: 0

After the run:

- `claim_extractions`: 38
- `claims`: 388
- `beliefs`: 365
- `belief_audit`: 493
- `contradictions`: 12
- failed extractions: 3
- dropped claims: 63
- failed extractor progress rows: 0
- failed consolidator progress rows: 0
- active beliefs with orphan claim ids: 0

## Dropped-Claim Gate

New extraction rows in this run: 0.

Inserted claims in this run: 0.

Dropped claims in this run: 0.

Dropped-claim rate for this run: not applicable because the denominator is 0.

The next bound that performs extraction must report inserted claims, dropped
claims, and dropped-claim rate for that run before any further expansion.

## Next Step

Proceed to the next bounded Phase 3 post-build run at `--limit 50`. Do not
start larger corpus-specific bounds or a full-corpus Phase 3 run unless the
`--limit 50` report is clean under RFC 0013 gates or records a human
checkpoint.
