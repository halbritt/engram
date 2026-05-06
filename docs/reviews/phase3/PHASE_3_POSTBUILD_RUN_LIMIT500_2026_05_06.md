# Phase 3 Post-Build Runtime Slice: Limit 500

Date: 2026-05-06

## Verdict

`blocked_for_expansion`

The `--limit 500` bounded run reached a prompt/model contract failure before it
completed. One latest selected-scope extraction failed with `trigger_violation`
after all emitted claims failed pre-insert validation, and the corresponding
conversation was skipped by consolidation. The selected-scope dropped-claim
gate also exceeded the RFC 0013 default blocker threshold.

The coordinator interrupted the still-running command after observing the gate
failure. The terminal process exit therefore records as an interrupt, but the
blocking condition predates that interruption.

This report is redacted under RFC 0013. It contains commands, counts, ids,
status values, and aggregate error classes only. It does not include raw
message text, segment text, prompt payloads, model completions, conversation
titles, claim values, belief values, private names, or corpus-derived prose
summaries.

## Commands

Owner-checkpoint marker check:

```bash
scripts/phase3_tmux_agents.sh next
```

Result: exit code `0`; output status `complete`.

No-work gate:

```bash
.venv/bin/python -m engram.cli pipeline-3 --limit 0
```

Result: exit code `0`.

CLI summary:

- extract: 0 claims created / 0 segments processed / 0 failed
- consolidate: 0 conversations processed / 0 skipped / 0 beliefs created /
  0 superseded / 0 contradictions

Bounded run:

```bash
.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 500
```

Result: interrupted by coordinator after gate failure was observed.

Final CLI summary lines were not produced.

## Issue Classes

- `prompt_or_model_contract_failure`
- `downstream_partial_state`
- `data_repair_needed`

## Aggregate Counts

Before the run:

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

After interruption:

- `claim_extractions`: 818
- `claims`: 4306
- `beliefs`: 4197
- `belief_audit`: 5760
- `contradictions`: 346
- failed extractions: 9
- dropped claims: 996
- validation-repair prior drops: 110
- failed extractor progress rows: 1
- failed consolidator progress rows: 1
- active beliefs with orphan claim ids: 0

Observed deltas:

- `claim_extractions`: +527
- `claims`: +2517
- `beliefs`: +2490
- `belief_audit`: +2710
- `contradictions`: +220
- failed extractions: +1
- dropped claims: +782
- validation-repair prior drops: +110
- failed extractor progress rows: +1
- failed consolidator progress rows: +1

## Selected-Scope Proof Query

For the first 500 active AI-conversation conversations:

- selected conversations: 500
- active segments: 723
- latest extracted segments: 593
- latest failed segments: 1
- missing latest extractions: 129
- latest claim count: 2927
- latest dropped claims: 824
- latest validation-repair prior drops: 110
- validation-repair attempts: 3
- failed extractor progress rows: 1
- failed consolidator progress rows: 1
- active beliefs with orphan claim ids: 0

Failed latest extraction:

- segment id: `7bf2896a-00ab-4f75-a0ed-1ae684a2b4e9`
- extraction id: `00a1b0a8-6e73-4738-92d5-9b94d4e4c22d`
- failure kind: `trigger_violation`
- final dropped claims: 28
- validation-repair prior drops: 28
- validation-repair result: `failed`

Failed progress rows:

- extractor scope `conversation:0488c023-1b5a-44b6-8a8d-454283fb3b07`:
  `all extracted claims failed pre-validation`
- consolidator scope `conversation:0488c023-1b5a-44b6-8a8d-454283fb3b07`:
  `skipped after 1 extraction failure(s)`

## Dropped-Claim Gate

Expanded dropped-claim gate:

```text
(final dropped claims + validation-repair prior drops)
/ (inserted claims + final dropped claims + validation-repair prior drops)
```

Selected-scope result:

```text
(824 + 110) / (2927 + 824 + 110) = 24.2%
```

This exceeds the RFC 0013 default blocker threshold of 10%.

Latest selected-scope final drop reasons:

- exactly one of `object_text` or `object_json` is required: 807
- predicate requires `object_json`: 15
- predicate requires non-empty `object_text`: 2

Latest selected-scope validation-repair prior drop reasons:

- exactly one of `object_text` or `object_json` is required: 110

## Current Gate

Do not proceed to a full-corpus Phase 3 run.

The next step is a repair loop for extraction validation/prompt behavior at the
limit-500 blocker, followed by same-bound rerun at `--limit 500`.
