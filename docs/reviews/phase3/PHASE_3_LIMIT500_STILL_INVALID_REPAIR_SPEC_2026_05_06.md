# Phase 3 Limit-500 Still-Invalid Repair Spec

Date: 2026-05-06

Status: `ready_for_builder`

Decision: implement D064, Option C hybrid accounted-zero policy.

Related artifacts:

- `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_REVIEW_claude_opus_4_7_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_PROBLEM_REVIEW_gemini_pro_3_1_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_POLICY_DECISION_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_REPAIR_RERUN_2026_05_06.md`
- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/12_STILL_INVALID_POLICY_ACCEPTED.ready.md`

## Redaction Boundary

This spec follows RFC 0013. It may include commands, counts, ids, status
values, predicate names, object-shape diagnostics, table/column names, error
classes, and aggregate rates. It must not include raw message text, segment
text, prompt payloads, model completions, conversation titles, extracted claim
values, belief values, private names, or corpus-derived prose summaries.

The related tracked artifacts for this repair are:

- this spec;
- the builder marker written with this spec;
- any later implementation review, run report, and repair-verified marker.

All tracked artifacts must keep `corpus_content_included: none` unless the
owner explicitly approves otherwise. Local database `raw_payload.model_response`
may continue to exist under the current Phase 3 debugging contract, but tracked
reports must never quote or summarize it. New persisted dropped-claim accounting
structures introduced by this repair must be redacted at the stored diagnostic
boundary, not only at report-rendering time.

## Accepted Policy

Fully parsed, schema-valid extraction outputs that remain all-invalid after the
single validation-repair attempt may become `claim_extractions.status =
'extracted'` with `claim_count = 0` only when every dropped draft is locally
diagnosed, redacted, and included in dropped-claim accounting.

This terminal state is an accounted zero-claim extraction. It is not an
extractor failure, and it is not a clean no-claim result. It moves a fully
auditable local-validation loss from the hard-failure path into the expanded
dropped-claim quality gate.

Non-goals:

- Do not relax JSON parsing, strict schema validation, local pre-insert
  validation, or database trigger backstops.
- Do not synthesize missing `object_text` or `object_json` values.
- Do not treat parse errors, schema rejections, repair parse failures, missing
  diagnostics, unredacted diagnostics, unknown drop reasons, or unknown error
  classes as zero-claim successes.
- Do not delete historical `claim_extractions`, `claims`, `beliefs`,
  `belief_audit`, `contradictions`, or progress rows.
- Do not change the same-bound expanded dropped-claim threshold. It remains
  10% for the next limit-500 verification run.
- Do not start a full-corpus Phase 3 run as part of this repair.

Prompt/schema hardening for repeated null-object shapes is allowed as a focused
supporting fix, but the core repair is the D064 accounted-zero terminal state.

## Fully Diagnosed Eligibility

An all-invalid post-repair extraction is eligible for accounted-zero only when
all of the following are true:

1. The initial model response parsed successfully from
   `choices[0].message.content`.
2. The parsed response satisfied the extractor response schema before Python
   local validation.
3. Python local validation produced zero valid claim drafts and at least one
   dropped draft.
4. `validation_repair.attempted` is `true`.
5. The validation-repair response also parsed successfully and satisfied the
   extractor response schema.
6. The post-repair state still has zero valid claim drafts and at least one
   dropped draft.
7. `validation_repair.result` is `still_invalid`.
8. Every prior and final drop has a known closed `reason`.
9. Every prior and final drop has a known closed local validation error class.
10. Every prior and final drop has redacted shape diagnostics only:
    `reason`, optional `index`, optional `split_path`, redacted `error` class,
    `predicate` when known, `stability_class` when known,
    `object_text_type`, `object_json_type`, optional `object_json_keys`, and
    `evidence_message_count`.
11. No persisted dropped-claim diagnostic for the accounted-zero row includes a
    raw nested `claim`, `subject_text`, `object_text`, raw `object_json` value,
    rationale, evidence text, message text, segment text, conversation title,
    model completion excerpt, private name, or corpus-derived prose summary.
12. `validation_repair.prior_dropped_count`,
    `validation_repair.final_dropped_count`,
    `validation_repair.prior_error_counts`, and
    `validation_repair.final_error_counts` are populated and match the stored
    redacted drop arrays.

The currently eligible `reason` set is:

- `trigger_violation`

The currently eligible local validation error classes are the bounded,
content-free classes emitted by `validate_claim_draft`, excluding unbounded
model-supplied values:

- `subject_text is empty`
- `stability_class does not match predicate vocabulary`
- `evidence_message_ids is empty`
- `evidence_message_ids must be a subset of segment message_ids`
- `evidence_message_ids must be a subset of chunk message_ids`
- `exactly one of object_text or object_json is required`
- `predicate requires non-empty object_text`
- `predicate requires object_json`
- `object_json missing required key: <vocabulary_key>`

`unknown predicate: <model_value>` is not eligible in its current string form
because it carries unbounded model-supplied content. The builder may introduce a
redacted closed error class such as `unknown predicate` later, but that would
need focused tests proving the raw predicate value is not persisted in tracked
or accounting diagnostics.

Any missing eligibility element above leaves the row `failed`.

## Row Distinction

Two `status='extracted'` rows with `claim_count = 0` must be distinguishable:

- `clean_zero`: no valid claims were emitted, no claims were dropped, and no
  validation-repair prior or final drops exist.
- `accounted_zero`: zero claims were inserted, but one or more prior or final
  drops were diagnosed, redacted, persisted, and counted.

Preferred implementation surface:

- Add a top-level `claim_extractions.raw_payload.extraction_result_kind` with a
  closed value set for extracted rows:
  `populated`, `clean_zero`, `accounted_zero`.
- Set `populated` when `claim_count > 0`, even if some drafts were dropped.
- Set `clean_zero` when `claim_count = 0` and the expanded dropped count for
  the row is zero.
- Set `accounted_zero` when `claim_count = 0` and the expanded dropped count
  for the row is greater than zero.

This keeps the repair narrow and works with the current
`claim_extractions` mutation guard, which already permits `raw_payload`
updates. If the builder instead chooses a first-class column, the migration must
also update the mutation guard, schema preflight, generated schema docs, and
tests. Either implementation must provide a queryable helper or function so
gate/report code does not repeatedly infer clean-zero versus accounted-zero
from ad hoc JSON traversal.

For accounted-zero rows, `raw_payload.failure_kind` must be `null`.
For hard failures, `extraction_result_kind` must be absent or set to a
non-success value not counted as an extracted terminal state.

## Hard Failures

These paths must remain `claim_extractions.status = 'failed'`:

- invalid JSON, markdown-wrapped JSON, empty content, or model output in the
  wrong response channel;
- strict extractor schema rejection;
- local model service failures, timeouts, or retry exhaustion;
- context guard failures;
- validation-repair attempt failure, including repair parse/schema/service
  failure;
- all-invalid post-repair output with missing prior or final drop counts;
- all-invalid post-repair output with missing dropped-claim arrays;
- all-invalid post-repair output with a dropped diagnostic that contains raw
  corpus content or nested raw claim values;
- any drop with an unknown `reason`;
- any drop with an unknown or unbounded local validation error class;
- any mismatch between stored drop arrays and reported prior/final counts;
- any other path that cannot be audited by redacted local diagnostics.

The quality gate is different from row failure. A same-bound run may complete
with accounted-zero rows and still fail the post-run gate if the expanded
dropped-claim rate is above 10%. That blocks the repair-verified marker and any
larger run, but it must not retroactively mark otherwise auditable
accounted-zero rows as extractor failures.

## Failure-Kind Taxonomy

The builder must stop using `failure_kind = 'trigger_violation'` for the
post-repair all-invalid hard-failure class.

Use `trigger_violation` only for the defense-in-depth case where insertion
reaches the database trigger backstop or for per-claim dropped diagnostics whose
`reason` reflects trigger-equivalent local validation.

Add a post-repair hard-failure kind equivalent to:

```text
local_validation_failed_post_repair
```

Use it when the initial and repair responses were parsed/schema-valid enough to
reach local validation, zero claims survived, and the row must remain failed
because the accounted-zero eligibility predicate was not satisfied. The row
should include a redacted secondary diagnostic such as
`accounting_failure_kind` with closed values like `missing_diagnostics`,
`unredacted_diagnostics`, `unknown_drop_reason`, `unknown_error_class`, or
`count_mismatch`.

Parse, schema, service, context guard, retry, manual requeue, and inflight
timeout failures keep their current failure kinds.

## Dropped-Claim Gate

For the selected limit-500 scope, compute the expanded dropped-claim gate over
the latest current-version extraction row for each active selected segment.

Selected scope:

- the ordered 500 conversations selected by `pipeline-3 --limit 500`;
- active AI-conversation segments only;
- current extractor prompt/model/request-profile version after the repair;
- the same first and last selected conversation ids as the blocked run, unless
  a no-ingestion/frozen-scope proof shows why the boundary changed.

Per latest extraction row:

- `inserted_claims = claim_extractions.claim_count`
- `final_drops = validation_repair.final_dropped_count` when validation repair
  exists, otherwise the count of `raw_payload.dropped_claims`
- `prior_drops = validation_repair.prior_dropped_count` when validation repair
  exists, otherwise `0`
- `expanded_drops = final_drops + prior_drops`

Selected-scope formula:

```text
expanded_dropped_claim_rate =
  sum(expanded_drops)
  / (sum(inserted_claims) + sum(expanded_drops))
```

If the denominator is zero after every selected active segment has a latest
completed extraction, the rate is defined as 0%. If any selected active segment
is missing a latest completed extraction, the gate is unverifiable and blocked.

Dedup rule:

- Count each dropped draft once per model attempt phase.
- Count prior validation-repair drops and final post-repair drops separately;
  repeated emission of the same invalid shape in the repair response is a new
  model-attempt drop and remains counted.
- Do not count duplicate copies of the same drop stored in both
  `raw_payload.validation_repair` and `raw_payload.parse_metadata`.
- Do not add `len(raw_payload.dropped_claims)` on top of
  `validation_repair.final_dropped_count` when both represent the same final
  post-repair drop set.

Threshold:

- The same-bound repair verification passes this gate only when the expanded
  dropped-claim rate is at or below 10%.
- The prior partial 15.7% rate is a risk signal, not final evidence, because
  the run stopped on a hard failure.

## Consolidator Behavior

Accounted-zero rows are successful extraction rows with zero claim
contribution.

Required behavior:

- `pipeline-3` must not increment `extract_failed` for an accounted-zero row.
- `pipeline-3` must not write a consolidator skip row for a conversation solely
  because it contains an accounted-zero segment.
- Targeted consolidation for a conversation containing accounted-zero rows must
  complete normally, creating zero beliefs from those rows.
- `fetch_active_claims` and Decision Rule 0 continue to see no claims from the
  accounted-zero row; no synthetic claim or belief is created.
- If a conversation has no active claims after all selected segments extract to
  clean-zero/accounted-zero, targeted consolidation may complete with zero
  groups and zero created/superseded/contradiction counts.

The accounted-zero row's audit value is in `claim_extractions` and the
dropped-claim gate, not in downstream beliefs.

## Requeue And Idempotence

Known failed conversation for targeted verification:

- `06dd9815-2298-488a-b544-39a08311dae3`

Known failed segment for diagnostic proof:

- `1b8a501f-1828-4bdf-9073-1c6279e452f1`

Expected repair behavior:

- Requeue the known failed conversation through the existing `extract --requeue
  --conversation-id` path or an equivalent reviewed requeue path.
- Do not delete the historical failed v7 row.
- The repaired extraction must create a newer latest row under updated
  extractor provenance.
- If the model produces valid claims after the repair, the row is
  `status='extracted'`, `claim_count > 0`, and
  `extraction_result_kind='populated'`.
- If the model repeats the fully diagnosed still-invalid shape, the row is
  `status='extracted'`, `claim_count = 0`,
  `extraction_result_kind='accounted_zero'`,
  `validation_repair.attempted=true`,
  `validation_repair.result='still_invalid'`, and the prior/final drops are
  redacted and counted.
- If the model response or diagnostics take any unauditable path, the row
  remains `failed` with the new local-validation failure kind or the applicable
  existing parse/schema/service kind.

Rerunning the same requeue after a completed extracted latest row must be
idempotent under the existing active extraction selection rule: unchanged
current-version extracted rows are no-ops unless `--requeue` or a new
provenance version deliberately supersedes them.

## Accepted Review Findings

Accepted from Claude Opus 4.7:

- F1: define the fully diagnosed eligibility predicate explicitly.
- F2: distinguish clean-zero from accounted-zero rows.
- F3: pin the expanded dropped-claim gate formula and 10% threshold.
- F4: replace misleading post-repair `trigger_violation` failure-kind usage.
- F5: acknowledge that prior-version extraction history is a prompt/schema
  regression signal; policy is the operational floor, not a substitute for
  focused prompt/schema hardening.
- F7: keep validation-repair depth to one attempt for this repair.
- F8: specify targeted requeue end-state expectations.

Accepted with modification:

- F6: first hard failures still stop the batch. This spec does not introduce a
  failure budget; Option C reduces hard failures only for fully auditable
  accounted-zero rows.

Accepted from Gemini Pro 3.1:

- F1: preserve the 10% same-bound dropped-claim gate and allow focused
  prompt/schema hardening for repeated null-object shapes.
- F2: enumerate eligible local-validation classes and keep unknown or
  unredacted paths hard-failed.
- Required gates: focused tests, full tests, no-work gate, targeted extraction,
  targeted consolidation, and same-bound limit-500 verification.

Rejected:

- Tuning the 10% threshold for this repair. The owner accepted holding the
  threshold unchanged for the next limit-500 verification run.

## Tests Required

The builder must add or update focused tests before live reruns:

- fully diagnosed `validation_repair.result='still_invalid'` with all drops
  redacted and known becomes `status='extracted'`, `claim_count=0`,
  `extraction_result_kind='accounted_zero'`, and no failed extractor progress;
- initial empty extraction with no drops becomes `clean_zero`;
- validation repair that returns an empty list after prior drops becomes
  `accounted_zero`, not `clean_zero`, and prior drops are counted;
- populated extraction with valid claims and prior/final drops remains
  `populated` and keeps drop accounting;
- still-invalid with unknown drop reason remains `failed`;
- still-invalid with unknown or unbounded error class remains `failed`;
- still-invalid with missing prior/final counts or count mismatch remains
  `failed`;
- still-invalid with any unredacted dropped diagnostic remains `failed`;
- parse error remains `failed`;
- schema rejection remains `failed`;
- validation-repair parse/schema/service failure remains `failed`;
- hard-failed post-repair local-validation row uses
  `local_validation_failed_post_repair` or the chosen equivalent, not
  `trigger_violation`;
- dropped-claim gate helper computes numerator, denominator, prior drops,
  final drops, and dedup behavior exactly as specified;
- accounted-zero rows do not make `run_extract_batches` increment `failed`;
- `pipeline-3` does not skip consolidation solely because a conversation has
  accounted-zero rows;
- targeted consolidation over a conversation with accounted-zero rows completes
  with zero contribution from those rows;
- existing test
  `test_extractor_validation_repair_still_invalid_remains_failed` is updated
  rather than deleted, preserving hard-failure coverage for ineligible
  still-invalid diagnostics.

If a schema column is added instead of the preferred `raw_payload` field, add
migration, mutation-guard, schema-preflight, and schema-doc tests.

## Live Verification Ladder

The builder must not run live pipeline commands until after implementation and
focused tests are ready. Before a repair-verified ready marker can be written,
the implementation must pass this ladder:

1. Focused Phase 3 tests for this repair pass.
2. Full test suite passes.
3. Live no-model/no-work gate:

   ```bash
   .venv/bin/python -m engram.cli pipeline-3 --limit 0
   ```

4. Requeue and targeted extraction for the known failed conversation:

   ```bash
   .venv/bin/python -m engram.cli extract --requeue --conversation-id 06dd9815-2298-488a-b544-39a08311dae3 --batch-size 5
   ```

   The result must be zero hard extraction failures and one of the expected
   end states in the Requeue And Idempotence section.

5. Bounded targeted consolidation for the same conversation:

   ```bash
   .venv/bin/python -m engram.cli consolidate --conversation-id 06dd9815-2298-488a-b544-39a08311dae3 --batch-size 1 --limit 1
   ```

   It must not write skip-due-to-extraction-failure progress for accounted-zero
   rows.

6. Same-bound limit-500 rerun:

   ```bash
   .venv/bin/python -m engram.cli pipeline-3 \
     --extract-batch-size 5 \
     --consolidate-batch-size 5 \
     --limit 500
   ```

7. Fresh redacted run report and repair-verified marker.

The same-bound run must prove all of the following:

- selected conversations: 500;
- selected-scope boundary recorded with first and last selected conversation
  ids and no-ingestion/frozen-scope proof;
- missing latest selected-scope extractions: 0;
- latest selected-scope extraction failures: 0;
- failed extractor progress rows in selected scope: 0;
- selected-scope consolidation skips: 0;
- failed consolidator progress rows in selected scope: 0;
- active beliefs with orphan claim ids: 0;
- expanded dropped-claim rate at or below 10%;
- tracked diagnostics remain RFC 0013-safe.

If any step fails, write or update a blocked marker and do not proceed to a
larger bound.

## Builder Handoff

Likely files in scope for the builder:

- `src/engram/extractor.py`
- `src/engram/cli.py`
- `src/engram/consolidator/__init__.py`
- `tests/test_phase3_claims_beliefs.py`
- `docs/claims_beliefs.md`
- optionally a new migration under `migrations/` only if the builder chooses a
  first-class column instead of the preferred `raw_payload` field
- `docs/schema/README.md` only via `make schema-docs` if a migration changes
  generated schema docs

Acceptance criteria:

- Option C is implemented exactly: only fully diagnosed, redacted, accounted
  all-invalid post-repair rows become accounted-zero extractions.
- Clean-zero and accounted-zero are queryably distinct.
- Hard-failure paths remain failed and use precise failure kinds.
- Accounted-zero rows do not feed claims or beliefs and do not cause
  consolidator skip/failure behavior.
- Expanded dropped-claim accounting includes validation-repair prior drops and
  final drops with the dedup rule above.
- The known failed conversation can be requeued and rerun to an auditable
  terminal state.
- The same-bound limit-500 rerun passes both operational gates and the 10%
  expanded dropped-claim gate before any repair-verified ready marker or larger
  run.
