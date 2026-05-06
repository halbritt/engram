# Phase 3 Limit-500 Schema Rejection Findings

Date: 2026-05-06

Related run report:

- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_LIVE_RERUN_2026_05_06.md`

Related marker:

- `docs/reviews/phase3/postbuild/markers/20260506_limit500_run/05_REPAIR_VERIFICATION.blocked.md`

## Redaction Boundary

This findings document follows RFC 0013. It contains commands, counts, ids,
status values, object-shape diagnostics, and aggregate error classes only. It
does not include raw message text, segment text, prompt payloads, model
completions, conversation titles, claim values, belief values, private names,
or corpus-derived prose summaries.

## Summary

The null-object repair fixed the originally blocked segment, but the same-bound
limit-500 repair verification exposed a new failure class caused by
model-facing strict schema rejection.

The repaired v6 extractor added a strict `oneOf` branch at the claim-item
schema level. In live execution, the local backend rejected two early model
outputs before Python could parse them into claim drafts. Because parsing
failed before local salvage, the system recorded no dropped claims and no
validation-repair prior drops.

This blocks expansion. It also means the stricter schema prevents the redacted
diagnostics path from seeing the invalid claim shape.

## What Passed

No-work gate:

- `pipeline-3 --limit 0` passed
- extract: 0 claims created / 0 segments processed / 0 failed
- consolidate: 0 conversations processed / 0 skipped / 0 beliefs created /
  0 superseded / 0 contradictions

Targeted original failed scope:

- segment `7bf2896a-00ab-4f75-a0ed-1ae684a2b4e9`
- conversation `0488c023-1b5a-44b6-8a8d-454283fb3b07`
- latest v6 status: `extracted`
- latest v6 claim count: 0
- targeted extraction failures: 0
- bounded targeted consolidation processed 1 group with 0 changes

The original all-invalid null-object failure is therefore no longer the active
blocker for that known segment.

## What Failed

Same-bound rerun command:

```bash
.venv/bin/python -m engram.cli pipeline-3 \
  --extract-batch-size 5 \
  --consolidate-batch-size 5 \
  --limit 500
```

The coordinator stopped the run after gate failure was already observed.

Selected-scope boundary:

- selected conversations: 500
- first selected conversation id:
  `0014d635-f280-4e68-a762-6a8e5b5920ef`
- last selected conversation id:
  `1140b58f-ff3b-4bde-8df2-7a6c1a949360`
- active segments in selected scope: 723

Latest v6 selected-scope state after stop:

- latest v6 rows: 6
- latest v6 extracted: 4
- latest v6 failed: 2
- missing latest v6 extractions: 717
- latest v6 claim count: 0
- latest v6 final dropped claims: 0
- latest v6 validation-repair prior drops: 0
- in-flight claim extractions after stop: 0
- active beliefs with orphan claim ids: 0

Failed v6 extraction rows:

- segment `012134de-6554-4241-be24-0e3c64d5b1e5`
  - conversation `0030fb7d-d9a2-48e2-9a70-c19281cbb520`
  - status: `failed`
  - failure kind: `retry_exhausted`
  - last error: `claim 0 does not match the schema`
  - attempts: 1
  - attempt max tokens: 8192
  - dropped claims: 0
  - validation-repair prior drops: 0
  - model response stored as JSON null
  - source kind: `chatgpt`
  - segment sequence index: 0
  - message count: 7
  - summary length: 393
  - content length: 6657
  - privacy tier: 1
- segment `19ba6674-6166-456a-b740-52175a8a4ba5`
  - conversation `00394f4c-0794-4807-9853-b3117385e82e`
  - status: `failed`
  - failure kind: `retry_exhausted`
  - last error: `claim 0 does not match the schema`
  - attempts: 1
  - attempt max tokens: 8192
  - dropped claims: 0
  - validation-repair prior drops: 0
  - model response stored as JSON null
  - source kind: `gemini`
  - segment sequence index: 0
  - message count: 2
  - summary length: 78
  - content length: 57
  - privacy tier: 1

Failed progress rows:

- extractor `conversation:0030fb7d-d9a2-48e2-9a70-c19281cbb520`
  - error count: 1
  - last error: `claim 0 does not match the schema`
- consolidator `conversation:0030fb7d-d9a2-48e2-9a70-c19281cbb520`
  - error count: 1
  - last error: `skipped after 1 extraction failure(s)`
- extractor `conversation:00394f4c-0794-4807-9853-b3117385e82e`
  - error count: 1
  - last error: `claim 0 does not match the schema`

## Findings

### F1 - Blocker: strict claim-item `oneOf` turns recoverable invalid claims into unrecoverable parse failures

The v6 repair moved exact-one object-channel enforcement into the
model-facing strict JSON schema. That prevents some malformed claim outputs
from reaching Python parse, salvage, redaction, and validation repair.

Impact:

- no `ClaimDraft` objects exist for the failed attempts;
- no dropped-claim records exist;
- validation repair does not run;
- the expanded dropped-claim gate has no prior-drop numerator for the failure;
- the only retained error is `claim 0 does not match the schema`;
- the exact invalid field shape is not available through the current stored
  diagnostics.

This is less diagnosable than the previous null-object failure path, where
Python validation could drop invalid claims and record redacted object-shape
diagnostics.

### F2 - Blocker: the same-bound gate still fails after the original segment is repaired

The known original failed segment now succeeds under v6, but expansion remains
blocked because the same-bound selected scope has:

- latest v6 extraction failures: 2
- missing latest v6 extractions: 717
- failed extractor progress rows: 2
- failed consolidator progress rows: 1

The correct next live run is another same-bound `--limit 500` after repair,
not full corpus.

### F3 - Major: strict-schema smoke did not exercise non-empty claim-item `oneOf`

The extractor health smoke uses an empty claim list. That proves schema
construction, but it does not prove runtime enforcement behavior for a
non-empty `claims` array. This limitation was noted during implementation
review and was confirmed by the live run.

Impact:

- a health smoke pass is not sufficient evidence that strict `oneOf` is safe;
- targeted segment reruns and same-bound reruns remain the load-bearing
  evidence.

## Likely Root Cause

The model/backend can produce a claim object that is close enough to be useful
for Python salvage but not accepted by the stricter model-facing schema. The
current strict schema rejects that object before the application can redact and
reason about the failure.

This suggests the model-facing schema became too strict for this local backend
and corpus mix. Local Python validation is still the correct authoritative
validator because it can preserve auditability and redacted diagnostics.

## Recommended Repair Direction

Prefer moving exact-one enforcement back out of the model-facing schema while
keeping it in:

- prompt rules;
- Python validation;
- redacted validation-repair feedback;
- dropped-claim gate accounting.

Concretely:

1. Bump extractor provenance again, for example:
   - `extractor.v7.d063.schema-rejection-repair`
   - `ik-llama-json-schema.d034.v9.extractor-8192-schema-rejection-repair`
2. Remove `oneOf` from the model-facing request schema, or disable it behind a
   default-off capability flag with tests proving the default runtime shape has
   no `oneOf`.
3. Keep both `object_text` and `object_json` required as fields.
4. Keep their values permissive enough that Python can parse and salvage
   schema-valid but locally invalid object-channel shapes.
5. Keep strict local exact-one validation unchanged.
6. Keep null-object repair feedback for full and mixed null/null drops.
7. Add tests proving schema-level rejection is no longer the primary path for
   null/null or otherwise locally invalid object-channel shapes.
8. Requeue the two new failed conversations before targeted reruns:
   - `0030fb7d-d9a2-48e2-9a70-c19281cbb520`
   - `00394f4c-0794-4807-9853-b3117385e82e`

If the implementation instead keeps `oneOf`, it must add a bounded,
redacted parse/schema-failure retry path and prove that failures remain
auditable without storing raw model completions. That path is higher risk than
removing model-facing `oneOf`.

## Verification Required

Run, in order:

1. Focused Phase 3 tests:

   ```bash
   ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q
   ```

2. Full tests:

   ```bash
   make test
   ```

3. No-work live gate:

   ```bash
   .venv/bin/python -m engram.cli pipeline-3 --limit 0
   ```

4. Targeted reruns for the two new failed conversations after requeue:

   ```bash
   .venv/bin/python -m engram.cli extract --requeue --conversation-id 0030fb7d-d9a2-48e2-9a70-c19281cbb520 --batch-size 5
   .venv/bin/python -m engram.cli extract --requeue --conversation-id 00394f4c-0794-4807-9853-b3117385e82e --batch-size 5
   ```

5. Bounded targeted consolidation for each repaired conversation:

   ```bash
   .venv/bin/python -m engram.cli consolidate --conversation-id 0030fb7d-d9a2-48e2-9a70-c19281cbb520 --batch-size 1 --limit 1
   .venv/bin/python -m engram.cli consolidate --conversation-id 00394f4c-0794-4807-9853-b3117385e82e --batch-size 1 --limit 1
   ```

6. Same-bound limit-500 gate:

   ```bash
   .venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 500
   ```

The pinned ready marker may be written only if the same-bound gate passes.

## Current Gate

Full-corpus Phase 3 remains blocked by:

`docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`
