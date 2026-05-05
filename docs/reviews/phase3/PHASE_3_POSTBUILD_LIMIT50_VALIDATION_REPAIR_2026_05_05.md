# Phase 3 Post-Build Limit-50 Validation Repair

Date: 2026-05-05

Related blocker:
`docs/reviews/phase3/postbuild/markers/20260505_limit50_run/01_RUN.blocked.md`

Related blocked run report:
`docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT50_2026_05_05.md`

Related review artifacts:

- `docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_REVIEW_codex_gpt5_5_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_REVIEW_SYNTHESIS_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_REREVIEW_codex_gpt5_5_2026_05_05.md`

## Verdict

`ready_for_owner_checkpoint`

The limit-50 operational blocker has a verified repair. The same-bound
`pipeline-3 --limit 50` rerun exited `0`, all latest selected-scope extractions
are successful, consolidation completed without skips, the dropped-claim gate is
below the RFC 0013 default blocker threshold, and the required same-model
re-review returned `accept`.

This report is redacted under RFC 0013. It contains commands, counts, ids,
status values, and aggregate error classes only. It does not include raw
message text, segment text, prompt payloads, model completions, conversation
titles, claim values, belief values, private names, or corpus-derived prose
summaries.

## Issue Classes

- `prompt_or_model_contract_failure`
- `downstream_partial_state`
- `data_repair_needed`

## Repairs Applied

Code and process changes:

- `src/engram/extractor.py`
  - records validation-repair prior-drop diagnostics in redacted form;
  - exposes those diagnostics at `raw_payload.validation_repair` for run-gate
    proof queries;
  - constrains the validation-repair pass to one local feedback attempt without
    adaptive split amplification;
  - preserves failed repair attempts as failed extraction rows.
- `tests/test_phase3_claims_beliefs.py`
  - covers empty successful repair, valid successful repair, still-invalid
    repair, and non-default retry behavior.
- `scripts/phase3_tmux_agents.sh`
  - preserves historical markers and only treats an explicit ready superseder
    as resolving a prior blocked operational marker.

Raw evidence was not modified. Historical failed extraction rows were retained
as audit history; no `claim_extractions`, `claims`, `beliefs`, `belief_audit`,
or `contradictions` rows were deleted.

## Same-Bound Rerun

Command:

```bash
.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 50
```

Result: exit code `0`.

CLI summary:

- extract: 410 claims created / 66 segments processed / 0 failed
- consolidate: 50 conversations processed / 0 skipped / 383 beliefs created /
  22 superseded / 22 contradictions

## Aggregate Counts

Before the same-bound rerun:

- `claim_extractions`: 225
- `claims`: 1379
- `beliefs`: 1324
- `belief_audit`: 2284
- `contradictions`: 104
- failed extractions: 8
- dropped claims: 172
- validation-repair prior drops: 0
- failed extractor progress rows: 0
- failed consolidator progress rows: 0
- active beliefs with orphan claim ids: 0

After the same-bound rerun:

- `claim_extractions`: 291
- `claims`: 1789
- `beliefs`: 1707
- `belief_audit`: 3050
- `contradictions`: 126
- failed extractions: 8
- dropped claims: 214
- validation-repair prior drops: 0
- failed extractor progress rows: 0
- failed consolidator progress rows: 0
- active beliefs with orphan claim ids: 0

Run deltas:

- `claim_extractions`: +66
- `claims`: +410
- `beliefs`: +383
- `belief_audit`: +766
- `contradictions`: +22
- failed extractions: +0
- dropped claims: +42
- validation-repair prior drops: +0

## Dropped-Claim Gate

Inserted claims in this run: 410.

Final dropped claims in this run: 42.

Validation-repair prior drops in this run: 0.

Expanded dropped-claim gate:

```text
(final dropped claims + validation-repair prior drops)
/ (inserted claims + final dropped claims + validation-repair prior drops)
```

Result: 42 / (410 + 42 + 0) = 9.3%.

This is below the RFC 0013 default blocker threshold of 10%.

Latest selected-scope final drop reasons:

- exactly one of `object_text` or `object_json` is required: 39
- predicate requires `object_json`: 2
- predicate requires non-empty `object_text`: 1

No validation-repair prior drops occurred in the latest selected-scope rerun.

## Selected-Scope Proof Query

For the first 50 active AI-conversation conversations:

- selected conversations: 50
- active segments: 67
- latest extracted segments: 67
- latest failed segments: 0
- missing latest extractions: 0
- latest claim count: 410
- latest dropped claims: 42
- latest validation-repair prior drops: 0
- latest v5 segments: 67
- validation-repair attempts: 0
- failed extractor progress rows: 0
- failed consolidator progress rows: 0
- active beliefs with orphan claim ids: 0

## Review Outcome

The initial Codex review returned `reject_for_revision` with two findings:

- successful validation repair hid the initial all-invalid response from the
  dropped-claim gate;
- repair retry count semantics were not pinned for non-default retries.

Both findings were accepted in synthesis and addressed in code and tests. The
same-model re-review returned `accept` with no blockers.

## Verification

- Focused Phase 3 tests:
  `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q`
  passed with `39 passed`
- Full test suite: `make test` passed with `124 passed`
- Live no-work gate:
  `.venv/bin/python -m engram.cli pipeline-3 --limit 0` passed
- Targeted failed-segment extraction rerun passed
- Same-bound rerun:
  `.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 50`
  passed
- Same-model re-review returned `accept`

## Current Gate

The original limit-50 blocked marker is superseded by:

`docs/reviews/phase3/postbuild/markers/20260505_limit50_run/05_REPAIR_VERIFIED.ready.md`

The repair is ready by RFC 0013 run diagnostics, but the Phase 3 runbook
requires an owner checkpoint after `pipeline-3 --limit 50`. Expansion remains
blocked by:

`docs/reviews/phase3/postbuild/markers/20260505_limit50_owner_checkpoint/01_RUN.human_checkpoint.md`

Do not proceed to a larger bound or full-corpus Phase 3 run until the owner
resolves that checkpoint.
