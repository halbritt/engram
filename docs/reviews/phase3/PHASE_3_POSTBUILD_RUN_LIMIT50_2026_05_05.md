# Phase 3 Post-Build Runtime Slice: Limit 50

Date: 2026-05-05

## Verdict

`blocked_for_expansion`

The `--limit 50` bounded run completed its selected scope but exited with code
`1`. It found three extraction failures and skipped consolidation for those
three conversations. It also exceeded the RFC 0013 dropped-claim-rate gate.

This report is redacted under RFC 0013. It contains commands, counts, ids,
status values, and aggregate error classes only. It does not include raw
message text, segment text, prompt payloads, model completions, conversation
titles, claim values, belief values, or corpus-derived summaries.

## Command

```bash
.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 50
```

Result: exit code `1`.

CLI summary:

- extract: 174 claims created / 49 segments processed / 3 failed
- consolidate: 47 conversations processed / 3 skipped / 177 beliefs created /
  23 superseded / 22 contradictions

## Aggregate Counts

Before the run:

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

After the run:

- `claim_extractions`: 87
- `claims`: 562
- `beliefs`: 542
- `belief_audit`: 692
- `contradictions`: 34
- failed extractions: 6
- dropped claims: 107
- failed extractor progress rows: 3
- failed consolidator progress rows: 3
- active beliefs with orphan claim ids: 0

Run deltas:

- `claim_extractions`: +49
- `claims`: +174
- `beliefs`: +177
- `belief_audit`: +199
- `contradictions`: +22
- failed extractions: +3
- dropped claims: +44

## Dropped-Claim Gate

Inserted claims in this run: 174.

Dropped claims in this run: 44.

Dropped-claim rate: 44 / (174 + 44) = 20.2%.

This exceeds the RFC 0013 default blocker threshold of 10%, so expansion beyond
this bound is blocked even aside from the extraction failures.

## Failure Summary

Three latest extraction rows in the selected limit-50 scope failed. All three
were `trigger_violation` failures where every emitted claim was dropped during
pre-insert validation.

Failed segment summaries:

- segment `0d73fb33-f016-4ac7-bf87-57787ffbcdcc`: 4 dropped claims; all were
  stability-class mismatches with the predicate vocabulary.
- segment `bff26d7a-c222-4ce0-bea3-b696c4d443e8`: 2 dropped claims; both had
  invalid object-channel shape.
- segment `4b901131-f618-4c6e-ad94-b466e1e2dcf1`: 8 dropped claims; all were
  stability-class mismatches with the predicate vocabulary.

Aggregate dropped-claim reasons for the failed rows:

- stability-class mismatch with predicate vocabulary: 12
- invalid object-channel shape: 2

## Selected-Scope Proof Query

For the first 50 active AI-conversation conversations:

- selected conversations: 50
- active segments: 67
- latest extracted segments: 64
- latest failed segments: 3
- missing latest extractions: 0
- latest extracted claim count: 441

Global active beliefs with orphan claim ids after the run: 0.

## Current Gate

Do not proceed to larger bounds or full-corpus Phase 3. The next step is a
repair loop for extraction validation/salvage behavior, followed by same-bound
re-run at `--limit 50`.
