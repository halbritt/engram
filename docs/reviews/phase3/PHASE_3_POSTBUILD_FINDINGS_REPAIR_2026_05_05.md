# Phase 3 Post-Build Findings Repair

Date: 2026-05-05

Source review:
`docs/reviews/phase3/PHASE_3_POSTBUILD_CHANGE_REVIEW_codex_gpt5_5_2026_05_05.md`

## Summary

The post-build change review returned `accept_with_findings`. The findings were
addressed before starting any bounded post-build runtime slice.

## Corrections

- Tightened `phase3_schema_preflight` so `pipeline-3` checks:
  - `006_claims_beliefs.sql` is recorded in `schema_migrations`.
  - Phase 3 required tables and columns exist.
  - `predicate_vocabulary` exactly matches the extractor predicate vocabulary.
  - Phase 3 active-row uniqueness indexes exist, are unique, valid, and have the
    expected table/definition shape.
  - Phase 3 normalization and trigger functions exist.
  - Phase 3 safety triggers exist, are enabled, call the expected functions, and
    are attached to the expected tables.
- Added real-schema tests that mutate a freshly migrated test DB and verify the
  preflight catches missing `006`, vocabulary drift, missing indexes, missing
  triggers, and missing trigger functions.

## Verification

- `env ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_migrations.py tests/test_phase3_claims_beliefs.py -q`
  - Result: `27 passed`.
- `make test`
  - Result: `107 passed`.
- `.venv/bin/python -c "from engram.db import connect; from engram.cli import phase3_schema_preflight; conn=connect(); phase3_schema_preflight(conn); conn.close(); print('phase3_schema_preflight=ok')"`
  - Result: `phase3_schema_preflight=ok`.
- `make migrate`
  - Result: `No migrations to apply.`
- `.venv/bin/python -m engram.cli pipeline-3 --limit 0`
  - Result: `0 claims created`, `0 conversations processed`, exit code `0`.

## Marker Policy

Existing Phase 3 build markers under `docs/reviews/phase3/markers/` were left
in place as audit history. Post-build review and runtime markers are written
under `docs/reviews/phase3/postbuild/markers/`.

## Next Step

Run the first bounded post-build runtime slice with `pipeline-3 --limit 10`,
inspect derived-row counts and diagnostics, then decide whether to expand to a
larger bounded slice.
