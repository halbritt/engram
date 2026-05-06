# Phase 3 Limit-500 Schema Rejection Repair Rerun

Date: 2026-05-06

Related prior findings:

- `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_FINDINGS_2026_05_06.md`

Related review:

- `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_REPAIR_REVIEW_claude_opus_4_7_2026_05_06.md`

Related marker:

- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/08_SCHEMA_REJECTION_REPAIR_RERUN.blocked.md`

## Redaction Boundary

This report follows RFC 0013. It contains commands, ids, status values,
counts, object-shape diagnostics, and aggregate error classes only. It does
not include raw message text, segment text, prompt payloads, model completions,
conversation titles, claim values, belief values, private names, or
corpus-derived prose summaries.

## Summary

The schema-rejection repair was committed and pushed, then the same-bound
limit-500 Phase 3 gate was started.

The run no longer failed in the model-facing strict schema path. Instead, it
hit the next blocker: a schema-valid extraction response reached Python local
validation, validation repair was attempted, and the repair response still left
all extracted claims locally invalid. The coordinator stopped the run at the
first hard extraction failure.

Full-corpus Phase 3 remains blocked.

## What Passed Before This Rerun

No-work gate:

```bash
.venv/bin/python -m engram.cli pipeline-3 --limit 0
```

Result:

- extract: 0 claims created / 0 segments processed / 0 failed
- consolidate: 0 conversations processed / 0 skipped / 0 beliefs created /
  0 superseded / 0 contradictions

Targeted schema-rejection reruns:

```bash
.venv/bin/python -m engram.cli extract --requeue --conversation-id 0030fb7d-d9a2-48e2-9a70-c19281cbb520 --batch-size 5
.venv/bin/python -m engram.cli extract --requeue --conversation-id 00394f4c-0794-4807-9853-b3117385e82e --batch-size 5
```

Result:

- conversation `0030fb7d-d9a2-48e2-9a70-c19281cbb520`: 1 segment processed,
  6 claims created, 0 failed
- conversation `00394f4c-0794-4807-9853-b3117385e82e`: 1 segment processed,
  1 claim created, 0 failed

Bounded targeted consolidation:

```bash
.venv/bin/python -m engram.cli consolidate --conversation-id 0030fb7d-d9a2-48e2-9a70-c19281cbb520 --batch-size 1 --limit 1
.venv/bin/python -m engram.cli consolidate --conversation-id 00394f4c-0794-4807-9853-b3117385e82e --batch-size 1 --limit 1
```

Result:

- conversation `0030fb7d-d9a2-48e2-9a70-c19281cbb520`: 1 group processed,
  6 beliefs created, 1 superseded, 1 contradiction
- conversation `00394f4c-0794-4807-9853-b3117385e82e`: 1 group processed,
  1 belief created, 0 superseded, 0 contradictions

## What Failed

Same-bound rerun command:

```bash
.venv/bin/python -m engram.cli pipeline-3 \
  --extract-batch-size 5 \
  --consolidate-batch-size 5 \
  --limit 500
```

The coordinator stopped the run after the first hard extraction failure.

Selected-scope boundary:

- selected conversations: 500
- first selected conversation id:
  `0014d635-f280-4e68-a762-6a8e5b5920ef`
- last selected conversation id:
  `1140b58f-ff3b-4bde-8df2-7a6c1a949360`
- active segments in selected scope: 723

Latest v7 selected-scope state after stop:

- latest v7 rows: 334
- latest v7 extracted: 333
- latest v7 failed: 1
- missing latest v7 extractions: 389
- latest v7 claim count: 1221
- latest v7 final dropped claims: 225
- latest v7 validation-repair prior drops: 2
- in-flight claim extractions after stop: 0
- active beliefs with orphan claim ids: 0

The partial expanded dropped-claim rate at stop was 227 / 1448, or about
15.7%. Because the run stopped on a hard extraction failure, this is not final
same-bound quality evidence.

Failed v7 extraction row:

- segment `1b8a501f-1828-4bdf-9073-1c6279e452f1`
  - conversation `06dd9815-2298-488a-b544-39a08311dae3`
  - status: `failed`
  - failure kind: `trigger_violation`
  - last error: `all extracted claims failed pre-validation`
  - extraction prompt version:
    `extractor.v7.d063.schema-rejection-repair`
  - request profile:
    `ik-llama-json-schema.d034.v9.extractor-8192-schema-rejection-repair`
  - dropped claims: 1
  - validation-repair prior drops: 2
  - model response stored as a string; length: 694
  - source kind: `chatgpt`
  - segment sequence index: 4
  - message count: 24
  - summary length: 181
  - content length: 4281
  - privacy tier: 1

Prior extraction history for the same segment:

- latest v7: `failed`, claim count 0
- prior v5: `extracted`, claim count 7

Failed progress rows:

- extractor `conversation:06dd9815-2298-488a-b544-39a08311dae3`
  - error count: 1
  - last error: `all extracted claims failed pre-validation`
  - position segment id: `1b8a501f-1828-4bdf-9073-1c6279e452f1`
- consolidator `conversation:06dd9815-2298-488a-b544-39a08311dae3`
  - error count: 1
  - last error: `skipped after 1 extraction failure(s)`

## Redacted Failure Diagnostics

Validation repair summary:

- attempted: true
- result: `still_invalid`
- prior dropped count: 2
- final dropped count: 1
- prior error counts:
  - `exactly one of object_text or object_json is required`: 2
- final error counts:
  - `exactly one of object_text or object_json is required`: 1

Prior dropped-claim shapes:

- predicate: `has_name`
  - stability class: `identity`
  - object_text type: `null`
  - object_json type: `null`
  - evidence message count: 1
- predicate: `has_name`
  - stability class: `identity`
  - object_text type: `null`
  - object_json type: `null`
  - evidence message count: 1

Final dropped-claim shape:

- predicate: `has_name`
  - stability class: `identity`
  - object_text type: `null`
  - object_json type: `null`
  - evidence message count: 1

## Findings

### F1 - Blocker: schema rejection is repaired, but fully accounted local validation failure still blocks the run

The v7 repair moved the failure out of strict model-facing schema rejection.
The application now parses the model response, performs local validation,
records redacted drop diagnostics, and attempts validation repair.

That is progress, but the run still stops when the repair response remains
all-invalid. The observed failure is a `validation_repair.result =
still_invalid` case, not the earlier `claim 0 does not match the schema` class.

### F2 - Blocker: current policy treats all-invalid, fully diagnosed repair output as an operational failure

The current implementation intentionally marks an extraction as `failed` when
no valid claims survive and at least one dropped claim remains after validation
repair. The test suite encodes that behavior.

In a full-corpus run, that means one schema-valid but locally invalid claim can
halt the whole pipeline, even though the failure is fully redacted and
accounted for. This protects against silent data loss, but it also makes the
operational gate brittle unless the repair retry can reliably produce either
valid claims or an empty extraction.

### F3 - Major: the repair prompt did not reliably force empty output

The repair feedback already instructs the model to omit unsupported invalid
claims and return `{"claims":[]}` if no valid claims remain. In this live case,
the model still returned another null-object `has_name` claim.

This suggests the next repair should not rely only on prompt wording. The
pipeline needs a clearer policy for fully diagnosed, schema-valid, all-invalid
outputs.

### F4 - Major: the dropped-claim quality gate is still unproven

At coordinator stop, the partial expanded dropped-claim rate was about 15.7%,
above the 10% same-bound acceptance gate. Since the run stopped early, that is
not final evidence, but it is a risk signal.

The next same-bound run must pass both gates:

- no extractor or consolidator failures;
- expanded dropped-claim rate at or below 10%.

## Recommended Repair Direction

Write a repair spec before changing code. The spec should make an explicit
policy decision for schema-valid, locally invalid, all-invalid outputs after
validation repair.

Two options:

1. Keep `still_invalid` as a hard operational failure. If so, improve the
   repair path enough to prove the model reliably returns valid claims or an
   empty extraction on targeted and same-bound evidence.
2. Treat fully parsed, fully redacted, all-invalid outputs as an extracted
   zero-claim result, with the final drops and validation-repair prior drops
   counted by the expanded dropped-claim gate. This would move these cases
   from operational failure to quality-gate accounting.

The second option is probably more practical for full-corpus operation, but it
changes current behavior and must be reviewed.

Required verification after repair:

1. Focused Phase 3 tests.
2. Full test suite.
3. No-work live gate.
4. Requeue and targeted extraction for conversation
   `06dd9815-2298-488a-b544-39a08311dae3`.
5. Bounded targeted consolidation for conversation
   `06dd9815-2298-488a-b544-39a08311dae3`.
6. Same-bound limit-500 gate.

The pinned ready marker may be written only if the same-bound limit-500 gate
passes.

## Current Gate

Full-corpus Phase 3 remains blocked by:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`
