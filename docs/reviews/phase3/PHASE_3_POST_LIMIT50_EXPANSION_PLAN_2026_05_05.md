# Phase 3 Post-Limit-50 Expansion Plan

Date: 2026-05-05

## Decision

The owner approved continuing beyond the `pipeline-3 --limit 50` human
checkpoint with an additional bounded run before any full-corpus execution.

The expansion sequence is:

1. Record this plan and the worker prompts.
2. Supersede the post-limit-50 human-checkpoint marker.
3. Run the no-work gate:

   ```bash
   .venv/bin/python -m engram.cli pipeline-3 --limit 0
   ```

4. Run the next bounded corpus gate:

   ```bash
   .venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 500
   ```

5. Stop and write a redacted report/marker for the `--limit 500` result.
6. Start a full-corpus Phase 3 run only if the `--limit 500` report is clean
   under RFC 0013 gates.

This plan does not relax Engram's local-first constraint. No corpus content may
leave the machine. Reports and markers remain redacted: commands, counts, ids,
status values, and aggregate error classes are allowed; raw message text,
segment text, prompt payloads, model completions, conversation titles, claim
values, belief values, private names, and corpus-derived prose summaries are
not allowed.

## Gate Criteria

The `--limit 500` run is clean only if all of these are true:

- command exit code is `0`;
- latest selected-scope extraction failures are `0`;
- missing latest selected-scope extractions are `0`;
- selected-scope consolidation skips are `0`;
- failed extractor progress rows are `0`;
- failed consolidator progress rows are `0`;
- active beliefs with orphan claim ids are `0`;
- expanded dropped-claim rate is at or below 10%:

  ```text
  (final dropped claims + validation-repair prior drops)
  / (inserted claims + final dropped claims + validation-repair prior drops)
  ```

If any gate fails, write a blocked marker and do not start full-corpus Phase 3.

## Prompt Artifacts

- `prompts/P039_run_phase_3_limit500_gate.md`
- `prompts/P040_run_phase_3_full_corpus_gate.md`

`P039` is active immediately. `P040` is recorded for continuity but remains
inactive until the coordinator verifies a clean `--limit 500` report.

## Expected Artifacts

For `--limit 500`:

- report:
  `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT500_2026_05_06.md`
- marker directory:
  `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/`

The limit-500 run started after UTC midnight, so its actual run artifacts use
the 2026-05-06 run date.

For full corpus, if authorized after the `--limit 500` gate:

- report:
  `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_FULL_2026_05_05.md`
- marker directory:
  `docs/reviews/phase3/postbuild/markers/20260505_full_run/`

## Current Scale

Before expansion:

- active AI conversations: 7777
- active AI segments: 11169
- latest extracted active segments: 67
- missing latest active extractions: 11102
- latest extracted claim count: 410

The `--limit 500` gate is intentionally one order of magnitude larger than the
proved `--limit 50` repair run, but still materially smaller than the full
corpus.
