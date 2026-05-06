# Phase 3 Full-Run Consolidator Null Group-Key Finding

Date: 2026-05-06

## Context

After the `--limit 500` Phase 3 run completed with zero extraction failures
and zero consolidation skips, the unbounded Phase 3 run was started. The run
surfaced one consolidator failure and was stopped for investigation.

## Failure

- Stage: `consolidator`
- Scope: `conversation:10e71cb4-6279-4f51-92e5-e4e814c70884`
- Status: `failed`
- Last error: `active belief conflict retry exhausted`
- Failed predicate class: `relationship_with`
- Cardinality class: `single_current_per_object`
- Object shape: required group key present with JSON null value

No raw claim text, object values, message text, or prompt payloads are recorded
in this artifact.

## Cause

The Python consolidator and the PostgreSQL belief trigger disagreed on JSON
null handling for group-object keys.

- PostgreSQL computes belief `group_object_key` with
  `COALESCE(object_json ->> key_name, '')`.
- Python computed the same key with `str(object_json.get(key, ""))`.

For a required JSON key whose value was JSON null, PostgreSQL used the empty
string while Python used the string form of `None`. The consolidator therefore
looked for an active belief under one group key, found none, then attempted to
insert a belief that PostgreSQL normalized into an already-active group.

## Repair

Python group-key computation now coalesces JSON `None` to `""` before
normalization, matching the database trigger.

Regression coverage was added for two `relationship_with` claims with a JSON
null group-key value. The second consolidation now finds and supersedes the
active belief instead of exhausting unique-conflict retries.

## Verification

- `tests/test_phase3_claims_beliefs.py::test_json_null_group_key_matches_database_trigger`
  passed.
- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_phase3_claims_beliefs.py -q`
  passed with `50 passed`.
- `make test` passed with `144 passed`.
- Targeted live retry:
  `.venv/bin/python -m engram.cli consolidate --conversation-id 10e71cb4-6279-4f51-92e5-e4e814c70884 --batch-size 1 --limit 1`
  completed successfully.

## Current State

After the targeted retry:

- Failed consolidator rows: `0`
- Failed extractor rows for the repaired v8 extractor version: `0`
- The unbounded run was intentionally stopped before restart.
