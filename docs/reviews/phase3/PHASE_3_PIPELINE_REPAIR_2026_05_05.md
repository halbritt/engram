# Phase 3 Pipeline Repair

Date: 2026-05-05
Operator: Codex GPT-5.5 (`codex_gpt5_5`)
Worktree: `~/git/engram`

## Summary

The bounded Phase 3 smoke failure recorded in
`PHASE_3_PIPELINE_START_2026_05_05.md` was repaired.

Two issues were fixed:

1. The live corpus DB had a stale Phase 3 schema while
   `schema_migrations` already recorded `006_claims_beliefs.sql`.
2. The extractor parser rejected a whole model response when one claim had
   both `object_text` and `object_json`, preventing the per-claim salvage
   diagnostics path from recording the bad claim.

No full-corpus Phase 3 run was started.

## Code Changes

- `src/engram/migrations.py`
  - Adds SHA-256 checksums to `schema_migrations`.
  - Records checksums for newly applied migrations.
  - Backfills checksums for pre-existing rows when no checksum exists.
  - Raises `MigrationDriftError` if an applied migration file later changes.
- `src/engram/cli.py`
  - Adds a Phase 3 schema preflight before `pipeline-3` extractor health smoke
    or local LLM work.
  - Fails closed if migration checksums or required Phase 3 tables/columns are
    missing or mismatched.
- `src/engram/extractor.py`
  - Allows object-channel exclusivity errors to reach per-claim salvage.
  - The validator still rejects the bad claim and records `dropped_claims`.
- `tests/test_migrations.py`
  - Covers checksum recording and drift detection.
- `tests/test_phase3_claims_beliefs.py`
  - Covers malformed object-channel output being persisted as a salvage
    diagnostic instead of a whole-response parse failure.
  - Covers `pipeline-3` preflight stopping before extractor/model work.
- `DECISION_LOG.md`
  - Adds D059 to make migration checksums, migration immutability, and Phase 3
    preflight fail-closed behavior binding.
- `migrations/004_source_kind_gemini.sql`
  - Restored the historical Gemini migration filename. Existing live DBs had
    this filename recorded, and its SQL is identical to
    `005_source_kind_gemini.sql`.

## Live DB Repair

The repair touched only Phase 3 derived tables and Phase 3 progress rows.
Raw evidence, segments, embeddings, captures, notes, messages, conversations,
and sources were not dropped or rewritten.

The repair guarded against deleting non-empty Phase 3 claim/belief data:

```text
claims: 0
beliefs: 0
belief_audit: 0
contradictions: 0
```

Then it:

- removed Phase 3 extractor/consolidator progress rows,
- dropped stale Phase 3 derived tables,
- dropped stale Phase 3 trigger/helper functions,
- removed `006_claims_beliefs.sql` from `schema_migrations`,
- reran `make migrate`.

`make migrate` reapplied:

```text
006_claims_beliefs.sql
```

Post-repair schema checks:

```text
predicate_vocabulary_exists|t
claims.extraction_id|t
belief_audit.evidence_message_ids|t
beliefs.subject_normalized|t
schema_migrations.checksum|t
```

Post-repair empty Phase 3 state:

```text
claim_extractions|0
claims|0
beliefs|0
belief_audit|0
contradictions|0
extractor_progress|0
consolidator_progress|0
```

## Bounded Smoke Rerun

Command:

```text
.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 1 --consolidate-batch-size 1 --limit 1
```

Result:

```text
extract segment=567c77ce-b09e-498e-ad50-a129d971129a
extract segment=567c77ce-b09e-498e-ad50-a129d971129a done claims=3 elapsed=7.6s
consolidate conversation=0014d635-f280-4e68-a762-6a8e5b5920ef
consolidate conversation=0014d635-f280-4e68-a762-6a8e5b5920ef done created=3 superseded=0 contradictions=0 elapsed=0.0s
extract: 3 claims created / 1 segments processed (0 failed)
consolidate: 1 conversations processed / 3 beliefs created / 0 superseded / 0 contradictions
```

Post-smoke counts:

```text
claim_extractions|1
claims|3
beliefs|3
belief_audit|3
contradictions|0
extractor_progress|1
consolidator_progress|1
```

Extracted predicates:

```text
prefers|quality over value||candidate|quality over value
uses_tool|Compute Module 5||candidate|compute module 5
uses_tool|Home Assistant Yellow||candidate|home assistant yellow
```

## Verification

Focused tests:

```text
env ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_migrations.py tests/test_phase3_claims_beliefs.py -q
20 passed
```

Full tests:

```text
make test
101 passed in 33.48s
```

Schema docs:

```text
make schema-docs
wrote ~/git/engram/docs/schema/README.md
```

Preflight no-work check:

```text
.venv/bin/python -m engram.cli pipeline-3 --limit 0
extract: 0 claims created / 0 segments processed (0 failed)
consolidate: 0 conversations processed / 0 beliefs created / 0 superseded / 0 contradictions
```

Final full test after adding D059/preflight:

```text
make test
101 passed in 36.17s
```

## Readiness

Ready for a larger Phase 3 run: **not yet by default**.

The bounded smoke now succeeds, but the next prudent step is a small
operator-approved slice larger than one conversation, not a full-corpus run.
Suggested next slice:

```text
.venv/bin/python -m engram.cli pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 10
```

Do not start a full-corpus Phase 3 run without explicit owner approval.
