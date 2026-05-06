# Phase 3 Limit-500 Schema Rejection Repair Review (Claude Opus 4.7)

Date: 2026-05-06

Reviewer: Claude Opus 4.7

Subject implementation diff against `HEAD`:

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`

Spec, finding, and prior-review context:

- `prompts/P043_fix_phase_3_limit500_schema_rejection.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_FINDINGS_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_LIVE_RERUN_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_REVIEW_claude_opus_4_7_2026_05_06.md`

Verdict: `accept_with_findings`

This review follows the RFC 0013 redaction boundary. It contains commands,
counts, ids, status values, predicate names, file paths, line numbers,
object-shape diagnostics, and aggregate error classes only. It does not
include raw message text, segment text, prompt payloads, model completions,
conversation titles, claim values, belief values, private names, or
corpus-derived prose summaries.

## Summary

The implementation matches the lower-risk repair direction in P043 and the
schema-rejection findings:

- model-facing claim-item `oneOf` is removed from both default and relaxed
  request schemas;
- both `object_text` and `object_json` remain `required` on the claim item;
- their value types are widened to `["string", "null"]` and `["object", "null"]`
  so a null/null object-channel claim parses to a `ClaimDraft` instead of being
  rejected at schema validation;
- strict local exact-one enforcement is unchanged in `validate_claim_draft`;
- null-object validation-repair feedback (full sweep and mixed sweep) is
  preserved unchanged;
- validation-repair prior drops are still recorded redacted on
  `claim_extractions.raw_payload.validation_repair`, so the expanded
  dropped-claim gate retains a real numerator;
- prompt rule "Exactly one of object_text/object_json must be non-null" remains
  in `build_extraction_prompt`;
- provenance versions are bumped to the values P043 listed.

Worker-reported verification (focused suite and `make test`) was reproduced
locally:

```
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test \
  .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q
40 passed in 22.41s
```

The findings below are minor and do not block coordinator-controlled live
verification of the two new failed conversations and the same-bound
`pipeline-3 --limit 500` gate.

## Answers To Review Questions

1. **P043 match.** R1, R2, R3, R4, R5, R6 are reflected in code and tests.
   R7 (test that schema-level rejection is no longer the primary path for
   null/null) is covered by the new parse-then-local-drop assertion in
   `test_extractor_validation_repair_retry_can_produce_empty_success` at
   `tests/test_phase3_claims_beliefs.py:657-685`. R8 (requeue the two new
   failed conversations) is operational and out of scope for the diff;
   it is correctly deferred to the coordinator per P043.

2. **`oneOf` removed from default request schema.** `extraction_json_schema`
   no longer constructs the strict-mode `oneOf` branch. Default claim item
   structure is built unconditionally at
   `src/engram/extractor.py:282-309` and returned without further mutation
   at `src/engram/extractor.py:310-320`. `grep` confirms no `oneOf` /
   `anyOf` / `allOf` constructs remain anywhere under `src/engram`.

3. **Both object channels still required.** The claim item still lists
   `subject_text, predicate, object_text, object_json, stability_class,
   confidence, evidence_message_ids, rationale` in `required`
   (`src/engram/extractor.py:285-294`). A model that drops one channel
   still fails the parent `required` check.

4. **Object-channel value types are permissive.** `object_text` is
   `{"type": ["string", "null"], "minLength": 1}` and `object_json` is
   `{"type": ["object", "null"], "additionalProperties": True}`
   (`src/engram/extractor.py:298-299`). The JSON Schema `minLength`
   constraint applies only when the value is a string, so a null in
   either field passes schema validation and reaches Python parse and
   local validation. Verified end-to-end by directly calling
   `parse_extraction_response` on a null/null payload at
   `tests/test_phase3_claims_beliefs.py:659-677`, which constructs a
   `ClaimDraft` with both fields `None` rather than raising.

5. **Strict local exact-one validation preserved.**
   `validate_claim_draft` still returns `"exactly one of object_text or
   object_json is required"` when both are null or both are non-null
   (`src/engram/extractor.py:1259-1260`). Predicate-vocabulary
   text/json-only enforcement and required_object_keys checks are
   unchanged at `src/engram/extractor.py:1261-1270`.

6. **Null-object validation-repair feedback preserved.**
   `render_null_object_repair_feedback` still labels full vs mixed
   sweeps (`src/engram/extractor.py:918-953`), is invoked from
   `build_validation_repair_feedback`
   (`src/engram/extractor.py:899-915`), and is exercised by both
   `test_extractor_validation_repair_retry_can_produce_empty_success`
   and `test_extractor_validation_repair_feedback_includes_mixed_null_object_section`.

7. **Validation-repair prior drops still recorded.** The accept and
   still-invalid branches of `retry_after_trigger_violation` continue
   to write `prior_dropped_count`, `prior_error_counts`, and
   `prior_dropped_claims` (redacted) into `parse_metadata`
   (`src/engram/extractor.py:855-885`). The failed-repair branch
   writes the same prior-drop fields plus `last_error`. Tests assert
   the redacted shape persists into `claim_extractions.raw_payload`
   (`tests/test_phase3_claims_beliefs.py:711-731`,
   `tests/test_phase3_claims_beliefs.py:783-787`,
   `tests/test_phase3_claims_beliefs.py:907-914`).

8. **Test coverage assessment.**

   | Required coverage from P043                                  | Test                                                                                              | Status |
   | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- | ------ |
   | Default schema has no `oneOf` and still requires both fields | `test_predicate_vocabulary_and_extractor_schema_parity` (lines 222-235)                           | met    |
   | Relaxed schema has no `oneOf`                                | `test_predicate_vocabulary_and_extractor_schema_parity` (lines 236-251)                           | met    |
   | Live request payload has no `oneOf`                          | `test_extractor_request_shape_parse_rejections_and_salvage` (lines 534-539)                       | met    |
   | Null/null parses to claim drafts and is dropped locally      | `test_extractor_validation_repair_retry_can_produce_empty_success` (lines 659-688)                | met    |
   | Validation repair records redacted prior drops               | `test_extractor_validation_repair_retry_can_produce_empty_success` (lines 711-731), and the preserve-when-valid-survive case | met    |
   | Validation repair can return empty success                   | `test_extractor_validation_repair_retry_can_produce_empty_success` (lines 685-721)                | met    |
   | Mixed null-object feedback subsection                        | `test_extractor_validation_repair_feedback_includes_mixed_null_object_section`                    | met    |
   | Failed-repair (still_invalid and exception) preserves drops  | `test_extractor_validation_repair_still_invalid_remains_failed`, `..._uses_one_attempt_even_with_extra_retries` | met    |
   | New provenance on `claim_extractions` and `claims`           | `test_extractor_request_shape_parse_rejections_and_salvage` (lines 567-580)                       | met    |
   | Salvage preservation when valid claims survive               | `test_extractor_validation_repair_preserves_prior_drops_when_valid_claims_survive`                | met    |

   See findings F1 and F2 for two minor coverage notes that do not block
   the live ladder.

9. **Live verification readiness.** The implementation is ready for the
   coordinator-controlled ladder in
   `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_FINDINGS_2026_05_06.md`
   "Verification Required": no-work `pipeline-3 --limit 0`, requeue plus
   targeted reruns for `0030fb7d-d9a2-48e2-9a70-c19281cbb520` and
   `00394f4c-0794-4807-9853-b3117385e82e`, then the same-bound
   `pipeline-3 --limit 500` gate. No source changes are required prior
   to that ladder.

## Findings

### F1 - Minor: no parse-then-local-drop test for the inverse exact-one violation

The new direct-parse assertion confirms that null/null object-channel claims
now reach a `ClaimDraft` and are caught by Python validation. There is no
matching test that proves a schema-valid claim with **both** `object_text`
and `object_json` non-null also reaches a `ClaimDraft` and is then either
normalized or dropped by Python.

The vocabulary-derivable normalization path
(`test_extractor_normalizes_vocab_derivable_claim_fields`) and the
`bad_shape` salvage path
(`test_extractor_request_shape_parse_rejections_and_salvage` lines 582-605)
together cover the predicate-vocabulary cases, but they construct
`ClaimDraft` objects directly rather than driving them through
`parse_extraction_response`. With model-facing `oneOf` removed, the
"both populated" shape is now a permitted parse output too.

Severity: minor.

Required fix: not required to unblock the live ladder. Optional follow-up:
extend the existing direct-parse pattern to a both-populated payload and
assert that local validation either normalizes (text or json predicate
vocabulary) or drops it as `"exactly one of object_text or object_json is
required"`. Suggested location: extend
`test_extractor_validation_repair_retry_can_produce_empty_success` or add a
sibling test next to it in `tests/test_phase3_claims_beliefs.py`.

### F2 - Minor: schema parity assertion mutates one schema in place to compare

`test_predicate_vocabulary_and_extractor_schema_parity` at
`tests/test_phase3_claims_beliefs.py:242-248` constructs a fresh strict
schema, mutates its `evidence_message_ids.items` in place to match the
relaxed pattern variant, and then asserts the mutated strict claim item
equals the relaxed claim item.

This is a correct way to prove the two schemas now differ only in
`evidence_message_ids.items` (and not in any reintroduced `oneOf` or
shape divergence), and the mutation is on a freshly constructed local
copy so it cannot leak across tests. It is functional today but reads as
slightly indirect.

Severity: minor.

Required fix: not required. Optional follow-up: replace the in-place
mutation with explicit subkey comparisons (assert strict has `enum` and
relaxed has `pattern` on `evidence_message_ids.items`, then assert all
other claim-item keys are equal between strict and relaxed). This makes
the intent of the parity test more obvious to a future reader.

### F3 - Info: empty-string `object_text` is now rejected at schema level rather than at Python

With `"type": ["string", "null"], "minLength": 1`, a model output of
`"object_text": ""` is rejected before parse, similar to how the prior
`oneOf` branch rejected null/null. Empty-string `object_text` would also
be caught by `validate_claim_draft` (`object_text.strip()` falsiness for
text predicates), so the asymmetry between the null and the empty-string
cases is harmless but worth noting in case a future failure surfaces a
`"claim 0 does not match the schema"` error tied to that shape.

Severity: informational only.

Required fix: none. If a future live run shows an `"object_text"` empty-
string schema rejection, dropping `minLength: 1` from `object_text` (and
relying on Python `strip()` validation) would be the symmetric repair.

## Redaction And Auditability

The diff does not introduce any new code path that stores or emits raw
model output, prompt payloads, conversation titles, segment text, or
private subjects. `redact_dropped_claims` and `redacted_claim_shape`
remain the single chokepoint for what the validation-repair feedback
exposes, and the existing tests assert that subjects, evidence message
ids, rationales, and concrete object values are excluded from
`prior_dropped_claims` and from the rendered repair feedback string
(`tests/test_phase3_claims_beliefs.py:698-732`,
`tests/test_phase3_claims_beliefs.py:835-839`,
`tests/test_phase3_claims_beliefs.py:909-913`).

The extraction prompt-version and request-profile-version bumps will
cause new `claim_extractions` and `claims` rows to be written under
`extractor.v7.d063.schema-rejection-repair` and
`ik-llama-json-schema.d034.v9.extractor-8192-schema-rejection-repair`,
matching the values listed in the schema-rejection findings and P043.
Older v6 rows are not deleted; they are superseded on insert per the
existing `claim_extractions` superseded path
(`src/engram/extractor.py:564-578`).

## Process Gate

Ready for the coordinator to run, in order:

1. `.venv/bin/python -m engram.cli pipeline-3 --limit 0`
2. `.venv/bin/python -m engram.cli extract --requeue --conversation-id 0030fb7d-d9a2-48e2-9a70-c19281cbb520 --batch-size 5`
3. `.venv/bin/python -m engram.cli extract --requeue --conversation-id 00394f4c-0794-4807-9853-b3117385e82e --batch-size 5`
4. `.venv/bin/python -m engram.cli consolidate --conversation-id 0030fb7d-d9a2-48e2-9a70-c19281cbb520 --batch-size 1 --limit 1`
5. `.venv/bin/python -m engram.cli consolidate --conversation-id 00394f4c-0794-4807-9853-b3117385e82e --batch-size 1 --limit 1`
6. `.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 500`

The pinned ready marker for this review is
`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/07_SCHEMA_REJECTION_REPAIR_REVIEW_claude_opus_4_7.ready.md`.

The pinned ready marker
`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/05_REPAIR_VERIFIED.ready.md`
remains unwritten and may only be added if the same-bound limit-500 gate
passes.
