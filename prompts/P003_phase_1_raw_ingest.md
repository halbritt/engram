# P003: Phase 1 Prompt — Raw Evidence Layer

> Prompt ordinal: P003. Introduced: 2026-04-28T03:55:54+00:00. Source commit: dfbd654.

> Hand this to a coding agent (Claude Code, Codex, or equivalent) to
> build Phase 1 per [BUILD_PHASES.md](../BUILD_PHASES.md). Read
> BUILD_PHASES.md for the phase-plan context; this file is the
> operational handoff.

## Read first, in order

1. [HUMAN_REQUIREMENTS.md](../HUMAN_REQUIREMENTS.md) — load-bearing
   principles. Especially: "Why local-first is load-bearing," "Why
   corpus access and network egress are kept separate," "Why raw
   data is sacred."
2. [V1_ARCHITECTURE_DRAFT.md](../docs/design/V1_ARCHITECTURE_DRAFT.md) — schema
   primitives, build order, vector index policy.
3. [DECISION_LOG.md](../DECISION_LOG.md) — accepted decisions; do
   not re-litigate. Binding for this phase: D002 (three-tier
   separation), D013 (V1 sources), D019 (privacy_tier default
   Tier 1), D020 (no network egress).
4. [BUILD_PHASES.md](../BUILD_PHASES.md) — Phase 1 row,
   cross-cutting concerns.

## Scope

Phase 1 only — raw evidence layer. Do not build segmentation,
embeddings, extraction, beliefs, entity canonicalization, or
`context_for`. Each is a separate phase prompt.

## Build

1. **Postgres (current LTS) + pgvector baseline.** Local instance,
   bound to 127.0.0.1. Schema changes go through reproducible
   migrations (pick a tool — sqitch, alembic, plain sql files;
   document the choice in `docs/` or `README`).

2. **Raw evidence schema.** Tables: `sources`, `conversations`,
   `messages`, `notes`, `captures`.
   - Immutable after insert. Enforce with a row-level trigger that
     blocks UPDATE/DELETE on these tables.
   - Provenance: every row carries `source_id`, `source_kind`
     (`chatgpt | obsidian | capture | future`), `external_id` (the
     source's own id, used for dedup), `imported_at`.
   - Preserve the full original payload as JSONB (`raw_payload`).
   - `privacy_tier int NOT NULL DEFAULT 1` on `captures`, `messages`,
     and `conversations` (per D019).
   - `captures.capture_type` enum: `observation | task | idea |
     reference | person_note | user_correction`.
   - `captures.corrects_belief_id UUID NULL` (no FK yet — beliefs
     table lands in Phase 3; add the FK then).

3. **ChatGPT export ingestion.** A CLI tool (Python 3.11+ unless
   the repo is opinionated otherwise) that:
   - Reads a ChatGPT export directory (`conversations.json` +
     `chat.html` structure).
   - Writes one row per conversation, one per message.
   - Idempotent: re-running on the same export produces zero new
     rows. Dedup key is `(source_id, external_id)`.
   - On conflict where content differs from the existing row: raise.
     Do not overwrite. Raw is immutable.
   - Records the export's filesystem path and content hash in
     `sources` so re-ingestion of the same export is detectable.

4. **Control table: `consolidation_progress`.** Empty in Phase 1;
   Phase 2+ writes to it for resumability. Phase 1 creates and
   migrates the table — nothing in Phase 1 writes rows.
   - Minimum columns: `id` (PK), `stage` (text — values like
     `segmenter | embedder | extractor | consolidator |
     entity_canonicalizer`; downstream phases extend the value set),
     `scope` (text — identifier for the batch this row tracks, e.g.
     a `source_id` or a date range), `status` (enum:
     `pending | in_progress | completed | failed`), `started_at`,
     `updated_at`, `position` (JSONB — stage-specific checkpoint
     payload; downstream phases define the shape).
   - Not subject to the raw-immutability trigger. Rows update as
     batches progress.
   - Index on `(stage, scope)` for cheap status lookup.

## Constraints (load-bearing — do not relax)

- Local only. No outbound network calls from any code path in this
  phase. No telemetry. No cloud DB.
- Postgres binds to 127.0.0.1.
- No mutation of raw rows after insert (enforced at the trigger
  level, not just discipline).
- Migrations are reproducible from an empty database.

## Acceptance criteria

- `make migrate` (or equivalent) brings up the schema from empty.
- `make ingest-chatgpt PATH=<export-dir>` ingests end-to-end.
- Re-running ingestion is a no-op (zero new rows, no errors).
- A test demonstrates the immutability trigger blocks UPDATE/DELETE
  on a raw-tables row and surfaces a clear error.
- A test demonstrates idempotent re-ingest (count before == count
  after on a second run).
- `docs/ingestion.md` (or equivalent) covers: how to run, what gets
  ingested, what doesn't (e.g., system messages — document the
  choice), dedup strategy.
- `consolidation_progress` table migrated and queryable, with zero
  rows after a fresh ingest run (Phase 1 doesn't write to it).

## Non-goals (do not build in this phase)

- Topic segmentation, embeddings, claim extraction, belief
  consolidation, entity canonicalization, `current_beliefs` view,
  `context_for`, MCP exposure, review queue, `context_feedback`.
  Each is a separate prompt.
- Obsidian or capture ingestion. Same pipeline shape, separate
  prompts.
- The `contradictions` or `belief_audit` tables. They land with
  their consumers.

## When in doubt

Prefer the smallest change that satisfies the principles and the
acceptance criteria. Reach for DECISION_LOG and V1_ARCHITECTURE_DRAFT
before inventing.
