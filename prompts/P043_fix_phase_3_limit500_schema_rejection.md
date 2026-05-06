# Fix Phase 3 Limit-500 Schema Rejection

You are implementing a Phase 3 repair for Engram. Engram is local-first: do
not use or request raw corpus content, prompt payloads, model completions,
conversation titles, claim values, belief values, private names, or
corpus-derived prose summaries. Use code, tests, process docs, aggregate
counts, ids, status values, object-shape diagnostics, and error classes only.

## Context

The v6 null-object repair fixed the originally failed segment, but the
same-bound limit-500 verification exposed a new schema-level failure class:

`claim 0 does not match the schema`

The failures happen before Python can parse model output into claim drafts, so
there are no dropped claims, no validation-repair prior drops, and no redacted
claim-shape diagnostics.

Read these files first:

1. `AGENTS.md`
2. `README.md`
3. `HUMAN_REQUIREMENTS.md`
4. `DECISION_LOG.md`
5. `BUILD_PHASES.md`
6. `ROADMAP.md`
7. `SPEC.md`
8. `docs/schema/README.md`
9. `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_FINDINGS_2026_05_06.md`
10. `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_LIVE_RERUN_2026_05_06.md`
11. `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_REVIEW_SYNTHESIS_2026_05_06.md`

## Task

Implement the schema-rejection repair.

Primary files:

- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`

Only touch additional files if the repair directly requires it.

You are not alone in the codebase. Do not revert edits made by others, and
adjust your implementation to accommodate current repo state.

## Required Behavior

Prefer the lower-risk repair:

1. Bump extractor provenance again, for example:
   - `extractor.v7.d063.schema-rejection-repair`
   - `ik-llama-json-schema.d034.v9.extractor-8192-schema-rejection-repair`
2. Remove model-facing `oneOf` exact-one enforcement from the default request
   schema, or place it behind a default-off capability flag.
3. Keep both `object_text` and `object_json` required as fields.
4. Keep their value types permissive enough for Python parse/salvage to see
   locally invalid object-channel shapes.
5. Preserve strict local exact-one validation in Python.
6. Preserve the null-object repair feedback for full and mixed null/null drops.
7. Preserve validation-repair prior drops so the expanded dropped-claim gate
   still catches hidden model contract failures.
8. Do not synthesize missing objects.
9. Do not delete historical failed extraction rows or progress rows.

If you believe keeping `oneOf` is safer, stop and document why. That alternative
requires a bounded, redacted parse/schema-failure retry path and stronger proof
that failures remain auditable without storing raw model completions.

## Tests To Add Or Update

Extend existing tests rather than duplicating them.

Required coverage:

- default strict schema no longer includes `oneOf` at `claims.items`, while
  still requiring `object_text` and `object_json`;
- relaxed schema remains limited to message-id enum relaxation and also does
  not include `oneOf`;
- null/null object-channel claims parse to claim drafts and are dropped by
  local validation rather than rejected by schema construction;
- validation repair still records redacted prior drops and can return an empty
  success;
- mixed null-object feedback still includes aggregate error counts and the
  null-object subsection;
- new prompt and request-profile provenance appears on `claim_extractions` and
  derived `claims` rows.

## Verification

Run:

```bash
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q
```

If focused tests pass, run:

```bash
make test
```

Do not run the live limit-500 gate unless the coordinator asks you to.

## Final Response

Return:

- verdict: implemented, partially implemented, or blocked;
- changed file paths;
- key behavior changes;
- tests run and exact results;
- any live-run caveats the coordinator must handle.

Do not commit or push unless the coordinator explicitly asks you to.
