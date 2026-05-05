# Phase 3 Limit50 Validation-Repair Review Synthesis

Date: 2026-05-05

## Source Review

- `docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_REVIEW_codex_gpt5_5_2026_05_05.md`

Codex returned `reject_for_revision`.

## Findings

### Major: successful validation repair hides the initial all-invalid response from the dropped-claim gate

Disposition: `accepted`.

Fix applied:

- `src/engram/extractor.py` now persists redacted prior-attempt diagnostics in
  `raw_payload.validation_repair.prior_dropped_claims`.
- The redacted entries keep error class, drop index, predicate, stability class,
  object-channel shape, object JSON keys, and evidence-message count. They omit
  subject text, object values, evidence message IDs, rationale, model response,
  and raw prompt content.
- Gate queries now count both `raw_payload.dropped_claims` and
  `raw_payload.validation_repair.prior_dropped_claims`.

### Minor: retry count semantics are not pinned for non-default extractor retries

Disposition: `accepted`.

Fix applied:

- Validation repair now calls the local extractor with `retries=0`.
- Validation repair disables adaptive splitting for repair-call exceptions, so
  a repair-specific parse/runtime failure remains one repair attempt rather than
  a recursive split-and-retry sequence.
- Tests cover non-default extractor retries.

## Provenance

The extractor prompt/profile identity was bumped after the accepted fixes:

- `extractor.v5.d063.validation-repair-audited`
- `ik-llama-json-schema.d034.v7.extractor-8192-validation-repair-audited`

## Verification

- Focused tests: `39 passed`
- Full tests: `124 passed`
- No-work gate: `pipeline-3 --limit 0` exited `0`
- Targeted failed-segment rerun exited `0`
- Same-bound `pipeline-3 --limit 50` exited `0`

Same-bound v5 summary:

- extraction: 410 claims created / 66 segments processed / 0 failed
- consolidation: 50 conversations processed / 0 skipped / 383 beliefs created /
  22 superseded / 22 contradictions

Selected-scope v5 proof:

- selected conversations: 50
- active segments: 67
- latest extracted segments: 67
- latest failed segments: 0
- missing latest extractions: 0
- latest claim count: 410
- latest dropped claims: 42
- latest validation-repair prior drops: 0
- latest v5 segments: 67
- validation repair attempts: 0
- failed extractor progress rows: 0
- failed consolidator progress rows: 0
- active beliefs with orphan claim IDs: 0

Dropped-claim gate including validation-repair prior drops:

- final dropped claims: 42
- validation-repair prior drops: 0
- denominator: 410 + 42 + 0 = 452
- rate: 42 / 452 = 9.3%

## Gate

The Codex rejection requires same-model re-review before a ready marker can
supersede the limit50 blocked marker.
