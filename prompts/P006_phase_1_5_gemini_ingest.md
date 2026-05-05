# P006: Phase 1.5 Prompt — Gemini Takeout Ingestion

> Prompt ordinal: P006. Introduced: 2026-04-28T05:45:48+00:00. Source commit: 618b5bc.

> Hand this to a coding agent to add Gemini Takeout ingestion under
> the same schema and conventions as Phase 1's ChatGPT loader.
> Mirrors [phase_1_raw_ingest.md](phase_1_raw_ingest.md) but scoped
> to a new source.

## Read first

1. [prompts/phase_1_raw_ingest.md](phase_1_raw_ingest.md) — Phase 1's
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

Add Gemini Takeout ingestion as a new source under the existing
`raw_evidence` schema. Same shape as ChatGPT and Claude ingestion:
parser + ingest function + CLI subcommand + tests + docs.

## Build

1. **Investigate the actual export format first.** Google Takeout's
   Gemini structure has shifted across versions (HTML records vs.
   JSON, MyActivity layout vs. dedicated Gemini directories). Look at
   the user's actual Takeout archive and write the parser against
   what's there. Do not assume the format from external documentation
   that may be stale.

2. **`src/engram/gemini_export.py`.** Mirror `chatgpt_export.py`
   structure:
   - Dataclasses: `GeminiMessage`, `GeminiConversation`, results.
   - `IngestConflict` raised on payload-changed re-ingest.
   - `ingest_gemini_export(conn, path) -> IngestResult` entry point.
   - Source row in `sources` with `source_kind='gemini'` and a stable
     `external_id` derived from the Takeout archive identity (export
     root path + content hash).
   - Idempotent: re-running on the same export produces zero new rows.
     Dedup key is `(source_kind, external_id)` per conversation/message.
   - On payload conflict for an existing row: raise `IngestConflict`.
   - Preserve full original payload as JSONB in `raw_payload`.

3. **CLI subcommand.** Add `engram ingest-gemini --path <takeout-dir>`
   to `cli.py`, parallel to `ingest-chatgpt` and `ingest-claude`.

4. **Tests.** Add coverage in `tests/` (parallel file or extend
   existing) for:
   - End-to-end Gemini ingest from a synthetic export fixture matching
     the format observed in step 1.
   - Idempotent re-ingest (count before == count after).
   - `IngestConflict` raised when re-ingest sees a payload-changed row.
   - Internal dedup conflict (duplicate IDs with different payload
     hashes within one export).

5. **Docs.** Extend `docs/ingestion.md` with a Gemini section: how to
   run, what gets ingested, dedup strategy, what's deferred (e.g.,
   image generations, file attachments — metadata in `raw_payload`,
   blobs out of V1 scope).

## Constraints

- Local only. No outbound network calls.
- The immutability trigger remains in force; raw rows are inserted,
  never updated.
- Postgres bound to 127.0.0.1.

## Acceptance criteria

- `make migrate` (no migration changes expected; this is parser +
  module work).
- `make ingest-gemini PATH=<takeout-dir>` ingests end-to-end.
- Re-running ingestion is a no-op (zero new rows, no errors).
- `make test` passes; new tests fail when the underlying parser is
  removed.
- `docs/ingestion.md` has a Gemini section.

## Non-goals

- No segmentation, embeddings, claim extraction, beliefs, etc.
- No schema changes (`raw_evidence` schema is source-agnostic;
  `source_kind` discriminates).
- No Claude ingestion. Same pattern, separate prompt
  (`prompts/phase_1_5_claude_ingest.md`).
- No ingestion of non-Gemini Takeout content (Search history, YouTube,
  Photos, etc.). If the Takeout archive contains those, ignore them
  in this phase. Other Takeout categories may be future ingestion
  paths but are out of V1 scope.
