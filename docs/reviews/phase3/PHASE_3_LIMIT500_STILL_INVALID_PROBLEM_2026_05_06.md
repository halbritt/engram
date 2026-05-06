# Phase 3 Limit-500 Still-Invalid Repair Problem

Date: 2026-05-06

Status: `problem_description_for_review`

Issue classes:

- `validation_repair_still_invalid`
- `derived_state_policy_change`
- `quality_gate_unverified`

Related run report:

- `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_REPAIR_RERUN_2026_05_06.md`

Related marker:

- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/08_SCHEMA_REJECTION_REPAIR_RERUN.blocked.md`

## Redaction Boundary

This problem description follows RFC 0013. It contains commands, ids, status
values, aggregate counts, object-shape diagnostics, error classes, and policy
questions only. It does not include raw message text, segment text, prompt
payloads, model completions, conversation titles, claim values, belief values,
private names, or corpus-derived prose summaries.

## Problem Statement

The Phase 3 limit-500 same-bound gate is blocked by an extraction that is no
longer a model-facing JSON schema rejection and no longer an unobservable
parse failure.

The latest blocker is a fully parsed, fully redacted local-validation failure:

1. The model returned schema-valid JSON.
2. Python parsed the extraction into claim drafts.
3. Local validation rejected all drafts.
4. Validation repair was attempted.
5. The repair response still left all extracted drafts invalid.
6. The extractor marked the row `failed`.
7. The pipeline skipped consolidation for that conversation and stopped.

The observed `validation_repair.result` was `still_invalid`.

This is a policy problem, not just a prompt problem. The current behavior
protects against silent data loss by treating an all-invalid extraction as an
operational failure. That makes sense for early pipeline hardening, but it may
be too brittle for full-corpus operation when the failure is already parsed,
redacted, counted, and auditable.

## Current Evidence

Same-bound command that hit the blocker:

```bash
.venv/bin/python -m engram.cli pipeline-3 \
  --extract-batch-size 5 \
  --consolidate-batch-size 5 \
  --limit 500
```

Selected-scope boundary:

- selected conversations: 500
- active segments in selected scope: 723
- first selected conversation id:
  `0014d635-f280-4e68-a762-6a8e5b5920ef`
- last selected conversation id:
  `1140b58f-ff3b-4bde-8df2-7a6c1a949360`

State at coordinator stop:

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
- source kind: `chatgpt`
- segment sequence index: 4
- message count: 24
- summary length: 181
- content length: 4281
- privacy tier: 1

Progress rows:

- extractor `conversation:06dd9815-2298-488a-b544-39a08311dae3`
  - status: `failed`
  - error count: 1
  - last error: `all extracted claims failed pre-validation`
- consolidator `conversation:06dd9815-2298-488a-b544-39a08311dae3`
  - status: `failed`
  - error count: 1
  - last error: `skipped after 1 extraction failure(s)`

Note: ids are diagnostic handles, not policy requirements.

## Redacted Failure Shape

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

## Current Behavior

The current extractor policy is:

- If valid claims survive, insert them and mark the extraction `extracted`.
- If no valid claims survive and no dropped claims remain, mark the extraction
  `extracted` with zero claims.
- If no valid claims survive and dropped claims remain after validation repair,
  mark the extraction `failed`.

That last rule is the active blocker.

## Decision To Review

Should a fully parsed, fully redacted, all-invalid extraction after validation
repair remain a hard operational failure, or should it become an extracted
zero-claim row whose loss is governed by the expanded dropped-claim quality
gate?

The decision must preserve these constraints:

- no raw corpus content in tracked diagnostics;
- no silent dropping of claims;
- no downstream consolidation on failed extraction rows;
- no full-corpus expansion until the same-bound limit-500 gate passes;
- dropped-claim accounting includes final drops and validation-repair prior
  drops;
- requeue and targeted reruns remain possible and auditable.

## Candidate Policies

### Option A - Keep `still_invalid` as a hard operational failure

Behavior:

- Keep marking all-invalid post-repair outputs as `failed`.
- Improve repair prompting and/or add a second targeted repair attempt.
- Require targeted rerun proof that the known failed conversation resolves.

Benefits:

- Strongest protection against silent extraction loss.
- Preserves the current test expectation and failure semantics.
- Keeps operator attention on every all-invalid extraction.

Risks:

- One unsupported or malformed claim can stop an otherwise healthy
  full-corpus run.
- The model may continue to repeat the invalid null-object shape despite
  repair feedback.
- The pipeline may spend most repair effort making the model say
  `{"claims":[]}` rather than improving derived-data safety.

### Option B - Treat fully diagnosed `still_invalid` as extracted zero-claim output

Behavior:

- If the response parsed successfully and all drops are redacted/accounted,
  mark the extraction `extracted` with `claim_count = 0`.
- Preserve `dropped_claims`, `validation_repair`, and error counts in
  `raw_payload`.
- Count final drops and validation-repair prior drops in the expanded
  dropped-claim quality gate.
- Let consolidation run for that conversation with zero claims from that
  segment.

Benefits:

- Moves fully diagnosed model weakness from an operational failure to a quality
  gate.
- Keeps the run bounded by the dropped-claim threshold instead of failing on
  the first all-invalid row.
- Preserves auditability without storing private content.

Risks:

- Changes current behavior and tests.
- If the quality gate is too permissive or incorrectly computed, real
  extraction loss could be normalized.
- Downstream consumers must be able to distinguish a clean zero-claim
  extraction from a zero-claim extraction with accounted drops.

### Option C - Hybrid policy

Behavior:

- Mark all-invalid post-repair outputs as `extracted` zero-claim only when all
  failure classes are locally validated, redacted, and included in dropped
  accounting.
- Keep hard failure for parse errors, schema rejections, missing diagnostics,
  unredacted diagnostics, unknown drop reasons, or quality-gate overflow.

Benefits:

- Keeps hard failure for unobservable or unauditable problems.
- Allows bounded progress for fully diagnosable model behavior.
- Makes the policy explicit rather than relying on prompt compliance.

Risks:

- More code and test surface than Option B.
- Requires clear definitions of "fully diagnosed" and "quality-gate counted."

## Review Questions

Reviewers should answer:

1. Which option should become the repair spec, and why?
2. Is the problem description missing any blocker, invariant, or hidden
   downstream consequence?
3. Is the redaction boundary sufficient?
4. What acceptance criteria must the repair spec include?
5. What tests must change or be added?
6. What live verification ladder must pass before full-corpus expansion?
7. Should the partial 15.7% dropped-claim rate affect the policy decision, or
   should it remain separate same-bound quality evidence?

## Expected Human Checkpoint

After independent Claude and Gemini reviews, a human should choose or amend the
policy direction before Codex synthesizes the repair spec. This is a semantic
pipeline policy decision, not merely an implementation detail.

## Non-Goals

This problem description does not ask reviewers to:

- inspect raw corpus content;
- modify code;
- change the predicate vocabulary;
- weaken local-first constraints;
- start a new live run;
- write the final repair spec.

## Required Verification After Any Repair

The eventual repair must pass, in order:

1. Focused Phase 3 tests.
2. Full test suite.
3. No-work live gate:

   ```bash
   .venv/bin/python -m engram.cli pipeline-3 --limit 0
   ```

4. Targeted extraction rerun after requeue for conversation
   `06dd9815-2298-488a-b544-39a08311dae3`.
5. Bounded targeted consolidation for the same conversation:

   ```bash
   .venv/bin/python -m engram.cli consolidate \
     --conversation-id 06dd9815-2298-488a-b544-39a08311dae3 \
     --batch-size 1 \
     --limit 1
   ```

6. Same-bound limit-500 gate.

The pinned ready marker may be written only if the same-bound limit-500 gate
passes all operational and dropped-claim quality criteria.
