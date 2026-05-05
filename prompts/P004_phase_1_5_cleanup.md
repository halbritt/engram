# P004: Phase 1.5 Prompt — Phase 1 Cleanup

> Prompt ordinal: P004. Introduced: 2026-04-28T05:19:06+00:00. Source commit: 1430f77.

> Hand this to a coding agent (Claude Code, Codex, or equivalent) to
> close the findings from [PHASE_1_REVIEW_FINDINGS.md](../docs/phases/PHASE_1_REVIEW_FINDINGS.md)
> and land the schema addition required by D023. Non-blocking for
> Phase 2 design; should land before Phase 2 implementation begins.

## Read first

1. [PHASE_1_REVIEW_FINDINGS.md](../docs/phases/PHASE_1_REVIEW_FINDINGS.md) —
   the findings driving items 1–3.
2. [DECISION_LOG.md](../DECISION_LOG.md) D023 — the schema decision
   driving item 4.
3. [prompts/phase_1_raw_ingest.md](phase_1_raw_ingest.md) — context
   on what Phase 1 built.

## Tasks

1. **Test coverage for split export format.** Add a fixture that
   generates a synthetic split export (`conversation-index.json` +
   `json/*.json`, plus the `projects/*/json/*.json` subdirectory)
   and a test that verifies `load_conversations` parses it correctly
   and that re-ingest is idempotent.

2. **Test coverage for internal dedup conflict.** Add a test that
   constructs an export containing duplicate conversation or message
   IDs with different payload hashes (within a single export run)
   and verifies `IngestConflict` is raised by `validate_unique_payloads`
   (or wherever the check lives).

3. **Atomic source upsert.** Replace `get_or_create_source`'s
   SELECT-then-INSERT pattern with `INSERT INTO sources (...)
   VALUES (...) ON CONFLICT (source_kind, external_id) DO NOTHING
   RETURNING id`. If no row is returned, SELECT the existing row by
   the unique key.

4. **Add `reclassification` to `captures.capture_type`.** Per D023.
   If `capture_type` is implemented as a Postgres enum, the migration
   adds the enum value; if implemented as text with a check
   constraint, the migration updates the check. No code yet writes
   reclassification captures — Phase 4 (review surface) is the
   natural place to land the read/write path. This migration only
   adds the value to the schema vocabulary so it's available when
   needed.

## Acceptance criteria

- All four items merged.
- `make test` passes. New tests fail when the underlying fix or
  feature is reverted (verify the tests actually exercise the path).
- The new `capture_type` value is queryable via `pg_type` or
  equivalent introspection.
- No raw rows mutated; the immutability trigger remains in force.

## Non-goals

- Do not add the read-side effective-tier computation. That lands
  with tier filtering in Phase 4 or Phase 5.
- Do not add a reclassification CLI or write path. Same reasoning.
- Do not refactor the ingestion module beyond items 1–3.
