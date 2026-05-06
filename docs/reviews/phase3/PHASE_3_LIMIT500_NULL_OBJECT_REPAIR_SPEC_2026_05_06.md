# Phase 3 Limit-500 Null-Object Repair Spec

Date: 2026-05-06

Status: `reviewed_and_amended`

Related artifacts:

- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT500_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_FAILURE_FINDINGS_2026_05_06.md`
- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_REVIEW_claude_opus_4_7_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_SYNTHESIS_2026_05_06.md`

## Redaction Boundary

This spec follows RFC 0013. It may use commands, counts, ids, status values,
aggregate error classes, predicate names, and object-shape diagnostics. It must
not include raw message text, segment text, prompt payloads, model completions,
conversation titles, claim values, belief values, private names, or
corpus-derived prose summaries.

## Problem

The `pipeline-3 --limit 500` run exposed a Phase 3 extractor contract failure.
The local JSON schema requires claim rows to contain both `object_text` and
`object_json` fields, but it currently allows both fields to be null. The
prompt and Python validator carry the stricter exact-one rule.

One selected-scope segment emitted 28 all-invalid claims on the first attempt.
Each dropped claim had:

- error: `exactly one of object_text or object_json is required`
- `object_text_type: null`
- `object_json_type: null`
- one evidence message
- a distinct predicate

The validation-repair retry then failed at JSON parsing, leaving the segment
failed. The broader limit-500 selected-scope diagnostics show the same failure
class at scale:

- selected conversations: 500
- active segments: 723
- latest extracted segments: 593
- latest failed segments: 1
- missing latest extractions after interruption: 129
- latest claim count: 2927
- latest final dropped claims: 824
- latest validation-repair prior drops: 110
- expanded dropped gate: 24.2%
- final drops with exact-one object-channel error: 807
- validation-repair prior drops with exact-one object-channel error: 110

The failure is not a raw-evidence issue and should not be repaired by editing
source evidence or derived rows in place. It is a prompt/schema/model contract
issue with correct downstream quarantine behavior.

## Goals

1. Prevent objectless skeleton claims from being accepted by the model-facing
   request contract when the local JSON-schema backend supports that
   constraint.
2. Make the validation-repair feedback specific enough to recover from
   null-object predicate sweeps without exposing raw corpus content.
3. Preserve strict local validation. Invalid claims must be dropped or fail the
   extraction; they must not be inserted with synthesized or missing objects.
4. Preserve auditability. Existing failed extractions, progress rows, and
   derived rows remain historical evidence of prior attempts.
5. Require a same-bound `pipeline-3 --limit 500` rerun before any full-corpus
   Phase 3 run.

## Non-Goals

- Do not relax the exact-one object-channel validator.
- Do not synthesize `object_text` or `object_json` from the subject, predicate,
  rationale, or evidence ids.
- Do not delete failed `claim_extractions`, `claims`, `beliefs`,
  `belief_audit`, `contradictions`, or progress rows.
- Do not suppress validation-repair prior drops from the dropped-claim gate.
- Do not start a full-corpus Phase 3 run as part of this repair.
- Do not add cloud services, hosted model APIs, telemetry, or external
  persistence.

## Required Repair

### R1 - Bump Extractor Provenance

The repair must use new extractor provenance strings so superseding runs are
queryable without confusing them with the failed limit-500 attempt.

Use names equivalent to:

- `extractor.v6.d063.null-object-repair`
- `ik-llama-json-schema.d034.v8.extractor-8192-null-object-repair`

The exact spelling may change if implementation conventions require it, but
both the prompt version and request-profile version must change. The previous
v5/v7 rows remain audit history.

### R2 - Constrain Object Channels in the Request Schema

The extraction JSON schema should enforce the exact-one object-channel shape at
the claim object level if the local JSON-schema backend supports it.

The preferred construct is `oneOf` at the `properties.claims.items` level,
branching on the object-channel fields while preserving the existing required
fields.

Required strict-schema logical shape:

- text-object claim:
  - `object_text` is a non-empty string
  - `object_json` is null
- JSON-object claim:
  - `object_text` is null
  - `object_json` is an object

The schema change must preserve the existing predicate enum, required fields,
evidence-id typing, and local validator behavior.

Support detection must be explicit:

- A unit test must assert that the non-relaxed generated schema contains the
  chosen `oneOf` construct at the claim-item level.
- A separate unit test must assert the exact expected relaxed-schema behavior.
- A live smoke step must prove the local backend accepts the strict schema
  before the implementation relies on schema-level exact-one enforcement.

If the backend rejects or ignores the needed construct, the implementation must
make that limitation explicit in tests or comments and must not silently weaken
the rest of the schema. In that case, prompt rules plus local validation remain
the authoritative enforcement path, and R3/R4 become mandatory compensating
controls.

The existing relaxed-schema fallback must not silently mask failures introduced
by the new exact-one construct. The relaxed path currently exists for
message-id enum pressure. The implementation must choose and test one of these
behaviors:

- strict-only exact-one schema: `oneOf` is present only when
  `relaxed_schema=False`; relaxed mode deliberately drops the construct and
  relies on prompt plus Python validation; or
- separate fallback handling: exact-one schema rejection is detected as its own
  backend limitation and does not reuse the message-id relaxed-schema fallback.

In either case, relaxing message-id constraints must not accidentally remove
predicate enum constraints, required fields, or local validation.

### R3 - Strengthen Prompt Emission Rules

The extractor prompt should be revised narrowly. Existing audited rules should
be retained unless the implementation has a specific reason to alter them.

Existing rules to retain:

- Never emit a claim with both `object_text` and `object_json` null.
- Emit only directly evidenced claims with a stated object.
- If the object cannot be stated, omit the claim.
- For text predicates, use a non-empty `object_text` and null `object_json`.
- For JSON predicates, use null `object_text` and a populated `object_json`
  with the predicate's required keys.

New additive rules:

- Do not enumerate the predicate vocabulary.
- Do not create skeleton claims to show possible predicates.
- If no valid claims remain, return exactly an empty claim list.

The prompt may include synthetic shape examples, but it must not include raw
corpus text or values from the failed segment.

### R4 - Add Null-Object-Sweep Validation Feedback

Validation repair should detect the null-object pattern whenever any dropped
claims from the first pass share:

- error `exactly one of object_text or object_json is required`
- redacted object shape `object_text_type: null`
- redacted object shape `object_json_type: null`

For that case, the repair feedback must include redacted diagnostics sufficient
for the model to understand the failure class:

- total dropped count
- distinct predicate count
- predicate names
- object-shape class `object_text=null, object_json=null`
- instruction to either provide directly evidenced objects or omit the claims
- instruction to return an empty claim list if no valid claims remain

If all dropped claims have the null/null exact-one shape, label the feedback as
a full null-object sweep. If null/null drops are mixed with other validation
errors, include a dedicated null-object subsection alongside the aggregate
error counts. Do not fall back to aggregate counts alone when null/null drops
are present.

Predicate names are fixed vocabulary metadata, not corpus content. Listing
predicate names in this redacted feedback is allowed, but subject values,
object values, and evidence text remain prohibited.

The feedback must not include subject values, object values, rationale text,
raw evidence text, model output text, conversation titles, or any
corpus-derived prose summary.

The validation-repair retry remains bounded:

- one repair attempt
- no adaptive split amplification
- no multi-turn repair loop
- failure remains failed if the repair output is invalid JSON or still has no
  valid claims while validation errors remain

### R5 - Preserve Salvage and Failure Semantics

The existing per-claim salvage rule remains:

- valid claims may be inserted even if sibling claims are dropped;
- an extraction fails only when zero claims survive and validation errors
  remain after the bounded repair path;
- a repair that returns a parseable empty claim list may succeed with zero
  claims, but its prior drops remain recorded as validation-repair prior drops;
- failed repair metadata must include the redacted last error and prior drops.

The implementation must not reclassify a prompt/model contract failure as a
clean success unless the final parse and validation state support that result.

### R6 - Preserve Gate Visibility

Post-run proof must continue to count both final dropped claims and
validation-repair prior drops:

```text
(final dropped claims + validation-repair prior drops)
/ (inserted claims + final dropped claims + validation-repair prior drops)
```

The same-bound repair is blocked if this expanded dropped-claim rate remains
above the RFC 0013 default blocker threshold, even when every extraction row is
successful.

The same-bound repair is also blocked by:

- latest selected-scope extraction failures;
- missing latest selected-scope extractions;
- selected-scope consolidation skips;
- failed extractor or consolidator progress rows;
- active beliefs with orphan claim ids.

### R7 - Keep Historical State Immutable

Existing partial derived state from the interrupted limit-500 run remains
auditable. The repair should produce superseding rows under the new provenance
version rather than deleting failed rows.

If any manual requeue or progress-row cleanup is required for execution, it
must be documented as a derived-state operational step. It must not modify raw
evidence and must not erase the historical failed extraction row.

### R8 - Pin the Superseding Marker

If the same-bound rerun passes all gates, the repair report must create a
superseding marker at:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/05_REPAIR_VERIFIED.ready.md`

Required front matter:

- `loop: postbuild`
- `issue_id: 20260506_limit500_run`
- `family: repair_verified`
- `scope: phase3 pipeline-3 limit500 null-object repair`
- `bound: limit500`
- `state: ready`
- `gate: ready_for_full_corpus_gate`
- `supersedes: docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`
- `corpus_content_included: none`

Before relying on automation to treat the blocker as superseded, verify that
`scripts/phase3_tmux_agents.sh` recognizes this marker family and supersedes
relationship. If it does not, fix the automation or record a human checkpoint.

## Test Requirements

Add focused tests before rerunning the live bound. Do not duplicate existing
validation-repair tests; extend them where they already cover the behavior.

1. Schema shape:
   - Assert the request schema enforces exact-one object channel when supported,
     or assert/document the backend limitation and verify the fallback does not
     remove existing schema constraints.
   - Assert strict and relaxed schema variants separately, including whether
     the exact-one construct is present or deliberately omitted.
2. Null-object-sweep feedback:
   - Given redacted dropped claims with null/null object shapes across multiple
     predicates, feedback includes aggregate count, predicate names, and object
     shape class.
   - Given mixed null/null and non-null-object validation errors, feedback still
     includes the null-object subsection.
   - Feedback excludes subject values, object values, rationale text, raw
     evidence text, and evidence ids.
3. Failed repair:
   - If the first pass is all-invalid and the repair returns invalid JSON, the
     extraction remains failed and records the redacted last error plus prior
     drops. Extend the existing invalid-repair coverage rather than replacing
     it.
4. Accepted empty repair:
   - If repair returns a parseable empty claim list, the extraction can succeed
     with zero claims, but prior drops remain available for the expanded gate.
     Extend the existing empty-repair coverage rather than replacing it.
5. Salvage preservation:
   - Mixed valid and invalid claims still insert valid claims and drop invalid
     siblings without invoking all-invalid failure behavior. Preserve the
     existing salvage tests.
6. Provenance:
   - New prompt and request-profile versions are present in created extraction
     rows.
   - Same-bound proof can attribute latest claims and beliefs to the superseding
     extraction provenance.

## Verification Ladder

After implementation, verify in this order:

1. Focused Phase 3 tests:

   ```bash
   ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q
   ```

2. Full test suite:

   ```bash
   make test
   ```

3. Live no-work gate:

   ```bash
   .venv/bin/python -m engram.cli pipeline-3 --limit 0
   ```

4. Targeted rerun for the failed selected-scope segment or its conversation,
   using the existing CLI-supported requeue path if progress rows require it.
   The failed segment id is:

   `7bf2896a-00ab-4f75-a0ed-1ae684a2b4e9`

   The related conversation scope id is:

   `0488c023-1b5a-44b6-8a8d-454283fb3b07`

5. Same-bound rerun:

   ```bash
   .venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 500
   ```

6. Redacted selected-scope proof for the first 500 active AI-conversation
   conversations.

7. Repair report and superseding ready marker only if all gates pass.

## Same-Bound Acceptance Gate

The repair may supersede the blocked limit-500 marker only when the same-bound
rerun proves all of the following:

- selected conversations: 500
- selected-scope boundary is stable, proven by a no-ingestion assertion since
  the blocked run and by recording the ordered first and last selected
  conversation ids for the rerun;
- latest selected-scope extraction failures: 0
- missing latest selected-scope extractions: 0
- selected-scope consolidation skips: 0
- failed extractor progress rows: 0
- failed consolidator progress rows: 0
- active beliefs with orphan claim ids: 0
- expanded dropped-claim gate is at or below 10%
- report contains only RFC 0013-safe diagnostics
- review findings, if any, are either resolved or explicitly routed to a human
  checkpoint

If ingestion may have changed the first-500 active AI-conversation boundary
between the blocked run and rerun, do not treat the result as a clean
same-bound proof without a human checkpoint or an explicit frozen-scope proof.

## Open Risks

- The local llama JSON-schema backend may not support the schema construct
  needed for exact-one enforcement. The implementation must prove support
  before relying on it.
- A stricter schema may increase model refusal or invalid-output behavior. The
  bounded repair feedback should reduce that risk, but the same-bound gate is
  the deciding evidence.
- Empty successful repairs can remove extraction failures while still leaving a
  high prior-drop rate. The expanded dropped-claim gate must remain the control
  against hiding that failure mode.
- Partial rows from prior runs can make global counts noisy. Acceptance must be
  based on latest selected-scope proof, not raw global totals alone.

## Current Gate

The Phase 3 full-corpus run remains blocked by:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`

This spec does not supersede that marker. It defines the reviewed repair for
implementation.
