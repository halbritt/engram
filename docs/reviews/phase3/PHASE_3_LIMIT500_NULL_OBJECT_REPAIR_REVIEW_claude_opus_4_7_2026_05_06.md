# Phase 3 Limit-500 Null-Object Repair Implementation Review (Claude Opus 4.7)

Date: 2026-05-06

Reviewer: Claude Opus 4.7

Subject implementation diff against `HEAD`:

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`

Spec and review context:

- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_REVIEW_claude_opus_4_7_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_SYNTHESIS_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_FAILURE_FINDINGS_2026_05_06.md`

Verdict: `accept_with_findings`

This review follows the RFC 0013 redaction boundary. It contains commands,
counts, ids, status values, predicate names, file paths, line numbers, and
aggregate error classes only. It does not include raw message text, segment
text, prompt payloads, model completions, conversation titles, claim values,
belief values, private names, or corpus-derived prose summaries.

## Summary

The implementation matches the amended repair spec: provenance versions are
bumped (R1), the strict request schema branches the object-channel shape with a
`oneOf` construct at the claim-item level (R2), the relaxed schema deliberately
omits the construct so it remains scoped to message-id enum pressure, the
prompt gains the three new additive rules without disturbing audited rules
(R3), the validation-repair feedback now carries a redacted null-object
diagnostics subsection that handles full sweeps and mixed sweeps (R4), salvage
and failure semantics are preserved (R5), validation-repair prior drops remain
recorded redacted on `claim_extractions.raw_payload.validation_repair` so the
expanded dropped-claim gate retains a real numerator (R6), and the new tests
extend the existing validation-repair coverage rather than replacing it.

Worker-reported verification:

- focused tests: `40 passed`
- `make test`: `125 passed`
- local extractor strict-schema health smoke: passed
- `git diff --check`: passed

I reran the focused suite locally and it passes:

```
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test \
  .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q
40 passed in 26.54s
```

The findings below are minor. None block the live verification ladder. The
implementation is ready for `pipeline-3 --limit 0` followed by the targeted
selected-scope rerun and the same-bound `--limit 500` rerun under the existing
acceptance gate.

## Answers To Review Questions

1. **Spec match.** R1 through R6 are reflected in code and tests. R7 and R8
   are operational and out of scope for the diff. Provenance bumps appear at
   `src/engram/extractor.py:31-34` and are asserted on both
   `claim_extractions` and `claims` rows in
   `tests/test_phase3_claims_beliefs.py:558-571`.

2. **Strict schema construct.** `extraction_json_schema` builds a single
   `claim_item` shared by both modes
   (`src/engram/extractor.py:282-309`) and adds the reviewed exact-one
   `oneOf` only in the strict branch
   (`src/engram/extractor.py:310-328`). The branches preserve the existing
   `required` fields and `additionalProperties: False` on the parent claim
   item. Each branch repeats `required: ["object_text", "object_json"]` so a
   model that drops one channel still fails the parent `required` check
   regardless of which `oneOf` arm it tries.

3. **Relaxed schema scope.** `oneOf` is omitted under
   `relaxed_schema=True` and the relaxed unit assertion
   (`tests/test_phase3_claims_beliefs.py:236-244`) verifies both that
   `oneOf` is absent and that the predicate enum and message-id pattern
   relaxation remain otherwise unchanged. The implementation chose F2's
   "strict-only exact-one schema" path and notes the choice in a code
   comment (`src/engram/extractor.py:311-312`).

4. **Null-object repair feedback.** `render_null_object_repair_feedback`
   (`src/engram/extractor.py:935-971`) filters dropped claims using the
   redacted shape (`error == "exactly one of object_text or object_json is
   required"` and both `object_text_type` and `object_json_type` equal to
   `"null"`), labels full sweeps versus mixed sweeps, and emits the
   diagnostics block plus repair and empty-output instructions. The feedback
   is composed from `redact_dropped_claims` output, so subject text, object
   text, object JSON values, rationale text, and evidence-message ids are
   structurally absent from the section.

5. **Prompt narrowness.** `build_extraction_prompt`
   (`src/engram/extractor.py:1577-1579`) adds exactly the three additive
   bullets specified in R3 and leaves every audited rule intact.

6. **Test coverage.** The schema test extends
   `test_predicate_vocabulary_and_extractor_schema_parity` with a strict
   `oneOf` assertion and a relaxed-mode absence assertion
   (`tests/test_phase3_claims_beliefs.py:217-244`). The full sweep
   feedback path is covered by
   `test_extractor_validation_repair_retry_can_produce_empty_success`
   (`tests/test_phase3_claims_beliefs.py:648-722`) including label,
   counts, predicate listing, shape class, and four explicit redaction
   assertions (`subject_text`, `object_text`, message id, rationale).
   The mixed sweep is covered by the new
   `test_extractor_validation_repair_feedback_includes_mixed_null_object_section`
   (`tests/test_phase3_claims_beliefs.py:773-820`). Failed repair extends
   `test_extractor_validation_repair_uses_one_attempt_even_with_extra_retries`
   with redacted-shape assertions on the persisted prior drops
   (`tests/test_phase3_claims_beliefs.py:887-895`). Salvage preservation
   extends
   `test_extractor_validation_repair_preserves_prior_drops_when_valid_claims_survive`
   with the same redacted-shape assertions
   (`tests/test_phase3_claims_beliefs.py:766-770`). Provenance is asserted
   on `claim_extractions` and `claims` rows produced under the new prompt
   and request-profile versions
   (`tests/test_phase3_claims_beliefs.py:550-571`).

7. **No hidden contract failures.** The salvage path (`extract_claims_from_segment`,
   `src/engram/extractor.py:512-554`) still triggers the bounded validation
   repair only on all-invalid first attempts, and still records a `failed`
   extraction when the repair returns invalid JSON or no valid claims
   alongside remaining errors. Both `accepted` and `failed` repair outcomes
   write redacted `prior_dropped_claims` to
   `validation_repair`, so the expanded dropped-claim gate keeps the
   prior-drop numerator on accepted-empty repairs.

8. **Live ladder readiness.** The diff is internally consistent, all unit
   tests pass, and the worker reported a successful local strict-schema
   smoke. The next acceptable live step is `pipeline-3 --limit 0`, followed
   by the targeted selected-scope rerun and the same-bound `--limit 500`
   gate.

## Findings

### F1 - Minor: relaxed-mode comment understates the chosen strict-only contract

`src/engram/extractor.py:311-312` reads:

```
# Relaxed mode is reserved for message-id enum pressure; exact-one stays
# enforced by the prompt plus Python validator if the backend needs it.
```

The amended spec made the choice explicit: under the strict-only path the
relaxed schema deliberately omits `oneOf`, so backend `oneOf` rejection (or
silent ignore) falls through to prompt plus Python enforcement. The comment
captures the spirit but elides the fact that the existing
`is_schema_construction_error` fallback at `src/engram/extractor.py:661-683`
will trigger on any grammar/schema-construction error, so an
unrelated schema rejection downgrades to relaxed mode (no `oneOf` and no
message-id enum). This is the documented compromise of the strict-only path
but a future reader will likely have to retrace it from `is_schema_construction_error`.

Severity: minor (documentation precision).

Suggested fix: extend the comment to say something like "the existing
`is_schema_construction_error` fallback covers exact-one rejections; both
`oneOf` and the message-id enum drop together because the path is shared,
and prompt plus Python validation remains authoritative." No code change is
required.

### F2 - Minor: cosmetic blank line when no null-object section is rendered

`build_validation_repair_feedback` (`src/engram/extractor.py:911-932`) places
`{null_sweep_section}` on its own line. When the section is empty
(`render_null_object_repair_feedback` returns `""`), the rendered string
contains an extra blank line between the rendered error counts and the
trailing instructions. This is purely cosmetic and never reaches a model
call, since the empty-section path implies no null/null drops; existing
non-null-object repair tests still pass.

Severity: minor (cosmetic).

Suggested fix or accept-as-is: optionally guard the blank line by inlining
the section conditionally, or accept the cosmetic gap. Not required for the
verification ladder.

### F3 - Minor: redundant guard in the full-sweep label expression

`render_null_object_repair_feedback`
(`src/engram/extractor.py:955-959`) reads:

```
label = (
    "full null-object sweep"
    if len(null_drops) == len(redacted) and len(redacted) > 0
    else "mixed null-object drops"
)
```

The function returns early when `null_drops` is empty
(`src/engram/extractor.py:944-945`). When this expression runs, both
`len(null_drops) >= 1` and therefore `len(redacted) >= 1`. The
`len(redacted) > 0` guard is therefore unreachable as a discriminator. It is
not incorrect, only redundant.

Severity: minor (dead branch).

Suggested fix or accept-as-is: drop the redundant clause or keep it as
defense-in-depth. No correctness impact.

### F4 - Minor: mixed-sweep test does not assert the aggregate error counts still render

`test_extractor_validation_repair_feedback_includes_mixed_null_object_section`
(`tests/test_phase3_claims_beliefs.py:773-820`) asserts the new null-object
diagnostics block and several redaction negatives, but it does not assert
that the existing aggregate error counts (the
`exactly one of object_text or object_json is required: 1` line and the
`object_json missing required key: status: 1` line) still appear in the
mixed feedback. The amended spec wording in R4 says "include a dedicated
null-object subsection alongside the aggregate error counts," and the
implementation does keep both sections, but the test would not fail if a
future change accidentally dropped the aggregate counts in the mixed
branch.

Severity: minor (test tightening).

Suggested fix or accept-as-is: add two `assert` lines to the mixed-sweep
test that look for the existing rendered-count lines, or accept that the
adjacent full-sweep behavior already exercises the rendered-count path. Not
required for the verification ladder.

### F5 - Informational: live `oneOf` enforcement is not proven by the smoke alone

`run_extractor_health_smoke` (`src/engram/extractor.py:618-633`) sends the
prompt `Health check only. Return exactly one schema-valid JSON object:
{"claims":[]}.` Under the strict schema this exercises the JSON-schema
construction path but not the `oneOf` arm validation, since `claims` is an
empty array and `oneOf` is at the items level. So a backend that accepts
the schema construct but does not enforce `oneOf` at runtime will still pass
the smoke. The amended spec accepts this: the load-bearing evidence is the
prompt plus Python validator under the same-bound rerun, gated by the
expanded dropped-claim gate.

Severity: informational (no fix required; documented contingency in the
spec).

Suggested next step: the targeted selected-scope rerun on
`7bf2896a-00ab-4f75-a0ed-1ae684a2b4e9` (segment) or
`0488c023-1b5a-44b6-8a8d-454283fb3b07` (conversation) is the first place
the runtime behavior of the strict schema can be observed. The same-bound
`--limit 500` is the deciding evidence.

## Cross-Cutting Observations

- The validation-repair retry remains bounded as required: one repair
  attempt (`call_extractor_with_retries` with `retries=0` inside
  `retry_after_trigger_violation`, `src/engram/extractor.py:858-867`),
  no adaptive split (explicit `adaptive_split=False`), and a clean
  failed/still_invalid/accepted result tag.

- The redaction boundary in `render_null_object_repair_feedback` is
  enforced structurally: it iterates only over the output of
  `redact_dropped_claims` (`src/engram/extractor.py:983-996`), and that
  helper drops `subject_text`, `object_text`, `object_json` (values),
  `rationale`, and `evidence_message_ids` (the actual ids), keeping only
  the predicate, stability class, type-shape strings,
  `object_json_keys` (when present), and `evidence_message_count`. The
  tests assert all five raw-value paths are not present in feedback for
  both the full-sweep and mixed-sweep cases.

- Provenance bump is comprehensive: not only does
  `EXTRACTION_PROMPT_VERSION` change, the `EXTRACTION_REQUEST_PROFILE_VERSION`
  changes too, and `ChunkExtractor` records `request_profile_version`
  on each `claim_extractions` row. The provenance test verifies this is
  reflected on derived `claims` rows. Existing failed v5/v7 rows remain
  audit history because the dedup logic in `find_existing_extraction`
  is keyed on the prompt version.

- The `dropped_claims` field on `claim_extractions.raw_payload`
  (`src/engram/extractor.py:529, 567`) still stores raw drops including
  the original claim values. That is internal audit storage, not
  prompt-bound, and outside the redaction boundary that applies to the
  repair feedback. No change required.

- `test_relaxed_schema_fallback_is_reactive`
  (`tests/test_phase3_claims_beliefs.py:939-946`) still passes; the
  reactive fallback continues to fire on grammar-state errors and the
  resulting relaxed call now also produces a schema without `oneOf` as
  the tests assert.

## Recommendation

`accept_with_findings`. The implementation is consistent with the amended
spec, all 40 focused tests and the full 125-test suite pass, the new tests
cover both the full and mixed null-object feedback shapes with explicit
redaction negatives, and provenance is asserted end to end. F1 through F4
are low-effort polish that may be deferred or addressed alongside the
live verification ladder; F5 is informational and documented in the spec.

The implementation is ready to advance to the live verification ladder,
starting with `pipeline-3 --limit 0`. The same-bound `pipeline-3 --limit
500` gate remains the load-bearing evidence before the
`05_REPAIR_VERIFIED.ready.md` superseding marker can be written.
