# P005: Phase 1.5 Prompt — Claude.ai Export Ingestion

> Prompt ordinal: P005. Introduced: 2026-04-28T05:45:48+00:00. Source commit: 618b5bc.

> Hand this to a coding agent to add Claude.ai conversation export
> ingestion under the same schema and conventions as Phase 1's
> ChatGPT loader. Mirrors [P003_phase_1_raw_ingest.md](P003_phase_1_raw_ingest.md)
> but scoped to a new source.

## Read first

1. [P003_phase_1_raw_ingest.md](P003_phase_1_raw_ingest.md) — Phase 1's
   structure that this prompt mirrors.
2. [src/engram/chatgpt_export.py](../src/engram/chatgpt_export.py) —
   the implementation pattern to mirror (dataclasses,
   `validate_unique_payloads`, atomic source upsert,
   `ingest_<source>_export` entry point).
3. [migrations/001_raw_evidence.sql](../migrations/001_raw_evidence.sql)
   — schema this writes against (no migration changes expected).
4. [docs/ingestion.md](../docs/ingestion.md) — docs structure to extend.
5. [DECISION_LOG.md](../DECISION_LOG.md) D024 — current V1 sources.

## Scope

Add Claude.ai conversation export ingestion as a new source under the
existing `raw_evidence` schema. Same shape as ChatGPT ingestion: parser
+ ingest function + CLI subcommand + tests + docs.

## Build

1. **Investigate the actual export format first.** Claude.ai's export
   structure changes across versions. Look at the user's actual export
   directory (path supplied via `--path`) and write the parser against
   what's there. Do not assume the format from external documentation
   that may be stale.

2. **`src/engram/claude_export.py`.** Mirror `chatgpt_export.py`
   structure:
   - Dataclasses: `ClaudeMessage`, `ClaudeConversation`, results.
   - `IngestConflict` raised on payload-changed re-ingest.
   - `ingest_claude_export(conn, path) -> IngestResult` entry point.
   - Source row in `sources` with `source_kind='claude'` and a stable
     `external_id` derived from the export root path + content hash.
   - Idempotent: re-running on the same export produces zero new rows.
     Dedup key is `(source_kind, external_id)` per conversation/message.
   - On payload conflict for an existing row: raise `IngestConflict`.
   - Preserve full original payload as JSONB in `raw_payload`.
   - All message types (system, tool, user, assistant) are ingested
     per Phase 1's stance: preserve raw evidence; downstream phases
     decide what to segment.

3. **CLI subcommand.** Add `engram ingest-claude --path <export-dir>`
   to `cli.py`, parallel to `ingest-chatgpt`.

4. **Tests.** In `tests/test_phase1_raw.py` (or a parallel file
   `test_phase1_claude.py`), add coverage for:
   - End-to-end Claude ingest from a synthetic export fixture matching
     the format observed in step 1.
   - Idempotent re-ingest (count before == count after on second run).
   - `IngestConflict` raised when re-ingest sees a payload-changed row.
   - Internal dedup conflict (duplicate IDs with different payload
     hashes within one export).

5. **Docs.** Extend `docs/ingestion.md` with a Claude section: how to
   run, what gets ingested, dedup strategy, what's deferred (e.g.,
   file attachments — only metadata in `raw_payload`, mirroring the
   ChatGPT decision).

## Constraints

- Local only. No outbound network calls.
- The immutability trigger remains in force; raw rows are inserted,
  never updated.
- Postgres bound to 127.0.0.1.

## Acceptance criteria

- `make migrate` (no migration changes expected; this is parser +
  module work).
- `make ingest-claude PATH=<export-dir>` ingests end-to-end.
- Re-running ingestion is a no-op (zero new rows, no errors).
- `make test` passes; new tests fail when the underlying parser is
  removed.
- `docs/ingestion.md` has a Claude section.

## Non-goals

- No segmentation, embeddings, claim extraction, beliefs, etc.
- No schema changes (`raw_evidence` schema is source-agnostic;
  `source_kind` discriminates).
- No Gemini ingestion. Same pattern, separate prompt
  ([P006_phase_1_5_gemini_ingest.md](P006_phase_1_5_gemini_ingest.md)).
- No file-attachment blob ingestion. Mirror Phase 1's stance:
  metadata stays in `raw_payload`; blobs are out of scope for V1.
