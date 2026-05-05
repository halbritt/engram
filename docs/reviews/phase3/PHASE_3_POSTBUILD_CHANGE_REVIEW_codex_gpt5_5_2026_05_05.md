# Phase 3 Post-Build Change Review

Date: 2026-05-05
Reviewer: Codex GPT-5.5 (`codex_gpt5_5`)
Prompt ordinal: P032

## Summary Verdict

`accept_with_findings`

Bounded post-build runs may proceed: yes, for small operator-approved
`pipeline-3` slices. Do not proceed to a full-corpus Phase 3 run from this
review alone.

## Findings

### Medium: Phase 3 preflight can still false-negative on semantic schema drift

`src/engram/cli.py:365`-`423` checks migration integrity plus presence of a
small set of Phase 3 tables and columns. That catches the exact stale live-DB
failure recorded in `PHASE_3_PIPELINE_START_2026_05_05.md` because the live
schema was missing columns such as `claims.extraction_id` and
`belief_audit.evidence_message_ids`.

It does not check the schema invariants that make Phase 3 safe: the active
extraction unique index in `migrations/006_claims_beliefs.sql:120`-`126`, the
claim validation and insert-only triggers at `migrations/006_claims_beliefs.sql:330`-`486`,
the belief transition GUC guard at `migrations/006_claims_beliefs.sql:488`-`593`,
or the append-only audit trigger at `migrations/006_claims_beliefs.sql:595`-`609`.
Because `engram migrate` backfills missing checksums from the current files
(`src/engram/migrations.py:83`-`99`), an existing DB with a partially stale
Phase 3 draft could be stamped with current checksums and then pass preflight
as long as the selected columns exist.

This is not blocking for the current repaired corpus DB, which passes the new
preflight and the full test suite. It is a guard-depth gap: before treating the
preflight as a general D059 drift detector, add assertions for the `006` ledger
row, key constraints/indexes/triggers/functions, and either a vocabulary row
count/hash or explicit predicate-vocabulary checks.

### Low: Preflight test coverage only proves call ordering, not malformed DB detection

`tests/test_phase3_claims_beliefs.py:1009`-`1035` monkeypatches
`phase3_schema_preflight` to raise and verifies `pipeline-3` stops before model
work. That is useful, but it does not exercise the real preflight against an
actual malformed schema. `tests/test_migrations.py:10`-`35` covers checksum
recording and mismatch for a newly applied migration, but not the important
compatibility cases: checksum backfill over an already-applied changed file,
missing applied migration files, or a Phase 3 schema with required columns but
missing triggers/indexes.

Add focused tests for the real preflight before relying on it as the only
runtime guard for larger slices.

## Non-Findings

- Restoring `migrations/004_source_kind_gemini.sql` while
  `migrations/005_source_kind_gemini.sql` exists is compatible with live DBs.
  Both files contain the same idempotent `ALTER TYPE ... ADD VALUE IF NOT
  EXISTS 'gemini'` statement, have the same SHA-256, and lexicographic ordering
  is deterministic. The duplicate ledger entries are untidy but not a runtime
  or data-loss risk.
- I found no repair-change path that mutates raw evidence. The checksum runner
  updates only `schema_migrations`; the preflight is read-only; extractor
  salvage writes only Phase 3 derived rows (`claim_extractions`, `claims`).
- The object-channel salvage repair is consistent with D058. Parser output can
  now carry both/neither object channels into `salvage_claims`, where
  `src/engram/extractor.py:764`-`787` drops the bad individual claim and
  records diagnostics while valid claims commit.

## Checks Run

- `git status --short` before writing this review.
- `env ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_migrations.py tests/test_phase3_claims_beliefs.py -q`
  - Result: `21 passed`.
- `make test`
  - Result: `101 passed in 36.10s`.
- Direct live-DB preflight call, without invoking `pipeline-3`:
  - `.venv/bin/python -c "from engram.db import connect; from engram.cli import phase3_schema_preflight; conn=connect(); phase3_schema_preflight(conn); conn.close(); print('phase3_schema_preflight=ok')"`
  - Result: `phase3_schema_preflight=ok`.
- Live migration ledger spot check:
  - `004_source_kind_gemini.sql`, `005_source_kind_gemini.sql`, and
    `006_claims_beliefs.sql` all have non-null recorded checksums.
- `sha256sum migrations/004_source_kind_gemini.sql migrations/005_source_kind_gemini.sql migrations/006_claims_beliefs.sql`
  - `004_source_kind_gemini.sql` and `005_source_kind_gemini.sql` match.

## Files Read

- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `docs/schema/README.md`
- `docs/claims_beliefs.md`
- `docs/reviews/phase3/PHASE_3_PIPELINE_START_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_PIPELINE_REPAIR_2026_05_05.md`
- `src/engram/migrations.py`
- `src/engram/cli.py`
- `src/engram/extractor.py`
- `src/engram/segmenter.py`
- `migrations/README.md`
- `migrations/004_source_kind_gemini.sql`
- `migrations/005_source_kind_gemini.sql`
- `migrations/006_claims_beliefs.sql`
- `tests/conftest.py`
- `tests/test_migrations.py`
- `tests/test_phase3_claims_beliefs.py`

## Next Expected Step

Run a small bounded post-build slice, such as the repair report's suggested
10-conversation `pipeline-3` slice, then record its results before expanding
the runtime envelope.
