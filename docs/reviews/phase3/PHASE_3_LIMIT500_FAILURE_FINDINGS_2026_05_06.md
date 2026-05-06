# Phase 3 Limit-500 Failure Findings

Date: 2026-05-06

Related report:
`docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT500_2026_05_06.md`

Related marker:
`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`

## Scope

This investigation reviewed the failed `pipeline-3 --limit 500` bounded run
using redacted database diagnostics, extractor code, prompt construction, and
process artifacts.

This document follows the RFC 0013 redaction boundary. It contains commands,
counts, ids, status values, aggregate error classes, predicate names, and object
shape diagnostics only. It does not include raw message text, segment text,
prompt payloads, model completions, conversation titles, claim values, belief
values, private names, or corpus-derived prose summaries.

## Summary

The limit-500 blocker is a real prompt/model contract failure, not an
infrastructure failure.

The failed selected-scope segment produced 28 locally invalid claims on the
first attempt. Every prior dropped claim had both `object_text` and
`object_json` null. The validation-repair retry then failed to produce parseable
JSON, so the segment remained failed and consolidation correctly skipped the
conversation.

The broader selected-scope diagnostics show the same object-channel failure
class at scale. The dropped-claim gate was 24.2%, well above the RFC 0013 10%
threshold.

## Findings

### F1 - Blocker: object-channel null sweep evades request schema and dominates drops

The extractor request schema requires both fields to exist, but permits each to
be null:

- `object_text`: string or null
- `object_json`: object or null

The exact-one rule is currently carried by prompt text and Python validation,
not by the request schema. A model response can therefore be schema-valid while
setting both object channels to null. Python salvage then drops those claims
with:

`exactly one of object_text or object_json is required`

For the failed segment:

- segment id: `7bf2896a-00ab-4f75-a0ed-1ae684a2b4e9`
- extraction id: `00a1b0a8-6e73-4738-92d5-9b94d4e4c22d`
- source kind: `gemini`
- segment message count: 2
- segment content length: 3609
- first attempt prior drops: 28
- final failed extraction drops: 28
- every prior drop had `object_text_type: null` and `object_json_type: null`
- every prior drop cited 1 evidence message
- the prior drops spanned 28 distinct predicates

This pattern is a predicate sweep with missing object payloads. It is not a
single malformed object key or predicate-specific shape error.

Limit-500 selected-scope evidence:

- latest extracted segments: 593
- latest failed segments: 1
- missing latest extractions after interruption: 129
- latest final dropped claims: 824
- validation-repair prior drops: 110
- expanded dropped gate: `(824 + 110) / (2927 + 824 + 110) = 24.2%`
- final drops with `exactly one of object_text or object_json is required`: 807
- validation-repair prior drops with the same error: 110
- segments with final drops: 85
- maximum final drops on one selected-scope segment: 52

Impact:

- Full-corpus Phase 3 would amplify invalid skeleton-claim output.
- Salvage prevents invalid rows from entering `claims`, but the high drop rate
  means the model is spending substantial work on unusable claims.
- One all-invalid segment blocked extraction and forced downstream
  consolidation skip as designed.

### F2 - Blocker: validation repair is not robust for all-invalid null-object sweeps

Validation repair worked for two selected-scope segments by returning no final
claims, but it failed for the blocking segment:

- validation repair attempts in selected scope: 3
- accepted repairs: 2
- failed repairs: 1
- failed repair error class: invalid JSON
- failed repair error summary:
  `extractor returned invalid JSON: Unterminated string`

The current repair feedback gives aggregate validation error counts and asks
for a complete corrected extraction. It does not include the redacted shape of
the failed response that would tell the model it emitted a broad null-object
predicate sweep.

Impact:

- The repair attempt can fail at the parse layer before Python validation can
  evaluate whether the corrected extraction is usable.
- A single failed repair keeps the segment failed and blocks the bound, which
  is the correct conservative behavior.
- The current repair path is useful as a bounded recovery mechanism, but it is
  not enough to authorize expansion when the main failure class appears across
  many selected-scope segments.

### F3 - Major: the partial limit-500 derived state is auditable but cannot advance

The interrupted run left derived rows from successful earlier scopes and one
failed selected scope.

After interruption:

- `claim_extractions`: 818
- `claims`: 4306
- `beliefs`: 4197
- `belief_audit`: 5760
- `contradictions`: 346
- failed extractions: 9
- failed extractor progress rows: 1
- failed consolidator progress rows: 1
- active beliefs with orphan claim ids: 0

Failed progress rows:

- extractor scope `conversation:0488c023-1b5a-44b6-8a8d-454283fb3b07`:
  `all extracted claims failed pre-validation`
- consolidator scope `conversation:0488c023-1b5a-44b6-8a8d-454283fb3b07`:
  `skipped after 1 extraction failure(s)`

Impact:

- Raw evidence remains untouched.
- No active belief orphan claim ids were found.
- The selected scope is incomplete and blocked by RFC 0013 gates.
- The next acceptable live run is a same-bound `--limit 500` rerun after
  repair, not a full-corpus run.

### F4 - Minor: worker reporting treated the terminal interrupt as the main failure

The worker reported the terminal command status as `KeyboardInterrupt`. That is
mechanically true, but the coordinator interrupted the command only after the
run had already failed the P039 gate.

Impact:

- The authoritative blocker is the prompt/model contract failure and dropped
  gate, not the interrupt.
- Future worker prompts should require post-failure metric collection when a
  coordinator-directed stop happens after a gate failure is observed.

## Likely Root Cause

The root cause is the gap between schema-level validity and local claim
validity:

1. The JSON schema allows `object_text=null` and `object_json=null`.
2. The prompt tells the model exactly one must be non-null, but larger corpus
   slices show the model still emits null-object skeleton claims.
3. Python validation correctly drops those claims.
4. Validation repair sometimes recovers by returning an empty extraction, but
   the failed segment's repair produced invalid JSON.

The failure is therefore a prompt/schema/model-contract problem, with correct
downstream quarantine behavior.

## Recommended Repair Direction

1. Strengthen the extractor request schema so the model is constrained toward
   exactly one object channel when supported by the local JSON-schema backend.
   If the backend does not support the needed schema construct, add a test that
   documents the limitation and keep the enforcement in Python.

2. Add a targeted null-object-sweep repair path. When all dropped claims share
   `exactly one of object_text or object_json is required` and all redacted
   object shapes are null/null, the repair feedback should explicitly say that
   the prior response emitted objectless skeleton claims and must either fill
   directly evidenced objects or return `{"claims":[]}`.

3. Add unit tests for:
   - schema generation or request-profile behavior for object-channel
     exclusivity;
   - redacted repair feedback for null/null object sweeps;
   - failed repair preserving the prompt/model contract failure as the blocker;
   - dropped-gate proof including validation-repair prior drops.

4. After the repair, rerun the specific failed segment or conversation first,
   then rerun `pipeline-3 --limit 500`. Do not start full corpus until the
   same-bound report is clean.

## Current Gate

`blocked_for_expansion`

Full-corpus Phase 3 remains blocked by:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`
