# Phase 1 Ingestion

Phase 1 creates the raw evidence layer only. It does not segment, embed,
extract claims, consolidate beliefs, canonicalize entities, expose MCP tools,
or write `consolidation_progress` rows.

## Database

Migrations are plain SQL files in `migrations/`, applied in filename order by
`engram migrate`. Applied filenames are recorded in `schema_migrations`.

The normal target is the system PostgreSQL cluster. The default connection URLs
use local socket auth:

```text
postgresql:///engram
postgresql:///engram_test
```

One-time setup must be done with whatever local Postgres admin role is available
on the machine:

```bash
createuser halbritt
createdb -O halbritt engram
createdb -O halbritt engram_test
psql -d engram -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d engram_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

If `createuser` or `createdb` fails because the current OS user is not a
Postgres admin, run the same commands through the local admin path, for example
`sudo -u postgres ...` on systems that use a `postgres` OS account.

Docker is available only as an optional local bootstrap path:

```bash
make db-up
```

The Docker Compose port binding is `127.0.0.1:54329:5432`, so that optional
database is not published on a public interface.

Apply migrations:

```bash
make migrate
```

Use a different database with:

```bash
make migrate DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/engram
```

Use the optional Docker database explicitly with:

```bash
make migrate-docker
make ingest-chatgpt-docker PATH=/home/halbritt/chatgpt-export
make ingest-claude-docker PATH=/home/halbritt/Downloads/data-<uuid>-...-batch-0000.zip
make ingest-gemini-docker PATH=/home/halbritt/Downloads/Takeout
make test-docker
```

## ChatGPT Export

Ingest a local export:

```bash
make ingest-chatgpt PATH=/home/halbritt/chatgpt-export
```

The importer accepts both known ChatGPT export shapes:

- Classic export: `conversations.json` with optional `chat.html`.
- Split export: `conversation-index.json`, `json/*.json`, and
  `projects/*/json/*.json`.

For the split export, the importer reads each per-conversation JSON file.
Attachments under `files/` are not imported as file blobs in Phase 1; attachment
metadata and asset pointers remain preserved inside each message's
`raw_payload`.

## Claude.ai Export

Claude.ai delivers each export as a zip archive, e.g.
`data-<uuid>-<timestamp>-<batch>-batch-0000.zip`. The importer accepts either
the zip directly or a directory the user has already extracted:

```bash
make ingest-claude PATH=/home/halbritt/Downloads/data-<uuid>-...-batch-0000.zip
make ingest-claude PATH=/home/halbritt/claude-export
```

The relevant payload files are `conversations.json`, `users.json`,
`projects.json`, and `memories.json`. Phase 1.5 only ingests
`conversations.json`; the other files are hashed into the source manifest so
they participate in change detection but are otherwise preserved as-is on
disk. File attachments referenced by `chat_messages[].files` are not imported
as blobs in V1, mirroring the ChatGPT decision; the `{file_uuid, file_name}`
metadata stays inside each message's `raw_payload`.

The importer writes:

- One `sources` row per export archive or directory, with the resolved
  filesystem path, a SHA-256 manifest hash, and the manifest JSON as
  `raw_payload`.
- One `conversations` row per Claude conversation (using `uuid` as the
  external id and `name` as the title).
- One `messages` row per `chat_messages` entry. `role` is the Claude
  `sender` field (`human` or `assistant`), `sequence_index` follows the
  array order in the export, and `content_text` is assembled from
  `content[]` (preferring concatenated `text` parts, with markers like
  `[tool_use:<name>]` and `[tool_result:<name>]` for non-text parts) and
  falls back to the message-level `text` field.

All sender types are ingested. Tool use and tool result content parts are
preserved inside `messages.raw_payload`; downstream phases decide what to
segment.

### Dedup

The Claude source dedup key is `(source_kind='claude', external_id)`, where
`external_id` is the resolved zip path or directory path. The manifest hash
covers the bytes of all four export JSON files. Re-running the same export
path with the same content reuses the existing source row; running with the
same path but different content raises an `IngestConflict`.

Conversation dedup uses the Claude `uuid`. Message dedup uses
`<conversation-uuid>:<message-uuid>` to stay safe against the (unlikely)
case of a Claude message uuid colliding across conversations. The original
message uuid is preserved inside `raw_payload`. Re-running the same export
is a no-op.

## Gemini Takeout

Gemini is exported by Google Takeout under the My Activity layout observed at:

```text
Takeout/My Activity/Gemini Apps/MyActivity.json
```

Ingest the extracted Takeout directory:

```bash
make ingest-gemini PATH=/home/halbritt/Downloads/Takeout
```

The CLI also accepts the subcommand form directly:

```bash
engram ingest-gemini --path /home/halbritt/Downloads/Takeout
```

The importer intentionally ignores non-Gemini Takeout categories such as
Search, YouTube, and Photos. It reads only Gemini Apps `MyActivity.json`.

The observed Gemini My Activity format is an array of activity records rather
than a threaded conversation export. Phase 1.5 maps each activity record to one
raw `conversations` row:

- The conversation external id is the activity `time` when present, falling
  back to a SHA-256 hash of the raw activity payload.
- The conversation `raw_payload` is the full original activity record.
- A user `messages` row is created when `title` starts with `Prompted `.
- An assistant `messages` row is created when `safeHtmlItem[].html` is present;
  the HTML is converted to plain text for `content_text`.
- Activity records such as `Used an Assistant feature` that have no prompt or
  response still land as raw conversations with zero messages.

Adjacent files in `My Activity/Gemini Apps/` include images, PDFs, audio, and
other uploaded/generated blobs. V1 does not ingest those blobs. Their filenames
and metadata remain preserved when Google includes them in the activity
`raw_payload` fields such as `attachedFiles` or `imageFile`.

### Dedup

The Gemini source dedup key is `(source_kind='gemini', external_id)`, where
`external_id` is the resolved Takeout directory path. The source manifest hash
covers `MyActivity.json`. Re-running the same Takeout path with the same
content reuses the existing source row; running with the same path but changed
content raises an `IngestConflict`.

Conversation dedup uses the activity `time` value, falling back to a payload
hash only if `time` is absent. Message dedup uses `<conversation-id>:user` and
`<conversation-id>:assistant`. Re-running the same export is a no-op.

## What Gets Stored

The importer writes:

- One `sources` row for the export directory, with filesystem path, a SHA-256
  manifest hash, and the manifest JSON as `raw_payload`.
- One `conversations` row per ChatGPT conversation JSON object.
- One `messages` row for every mapping node with a non-null `message`.

System, hidden, tool/context, user, and assistant messages are all ingested.
That is intentional for the raw layer: Phase 1 preserves evidence; downstream
phases decide what to segment or ignore.

Each raw row keeps the original payload in `raw_payload`. Convenience columns
such as `title`, `role`, timestamps, and `content_text` are projections for
inspection and later pipeline stages, not replacements for raw data.

## Dedup And Conflicts

The source dedup key is `(source_kind, external_id)`, where `external_id` is the
resolved export directory path. The importer records a manifest hash over the
conversation JSON and index files. Re-running the same export path with the
same content reuses the existing source row.

Conversation and message dedup keys are `(source_id, external_id)`.
Conversations use the ChatGPT conversation id. Messages use
`<conversation-id>:<message-id>` because ChatGPT message ids are not guaranteed
to be globally unique across a full export. The original message id remains in
the message `raw_payload`. Re-running the same export is a no-op.

If the same export path later has a different manifest hash, ingestion raises
an error and does not overwrite. The importer also rejects duplicate
conversation or message dedup keys with different JSON inside a single export.
Raw evidence tables are protected by database triggers that block `UPDATE` and
`DELETE`.

## Control Table

`consolidation_progress` is created in Phase 1 for later resumable stages. The
ChatGPT importer does not write to it, so it remains empty after a fresh ingest.

## Reclassification Vocabulary

D023 adds `reclassification` to `captures.capture_type`. Phase 1.5 only adds
the enum value so later review surfaces can record tier promotions or redaction
requests as immutable captures. No Phase 1.5 code writes reclassification
captures, and raw rows remain protected by the immutability trigger.
