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
