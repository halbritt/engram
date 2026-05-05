# Phase 1 Build Status

Status: implemented; Phase 1.5 multi-source ingestion applied and verified on system Postgres
Date: 2026-04-30

## Database

Initial verification used the Dockerized Postgres instance defined in
`docker-compose.yml`. After review, the repo defaults were changed so normal
`make migrate`, source ingest targets, and `make test` target system Postgres
through local socket URLs by default.

System Postgres defaults:

- Database URL: `postgresql:///engram`
- Test database URL: `postgresql:///engram_test`
- System Postgres version: PostgreSQL 16.13
- pgvector installed version: `0.6.0`

Optional Docker target:

- Image: `pgvector/pgvector:pg17`
- Container: `engram-postgres`
- Bind address: `127.0.0.1:54329`
- Database URL: `postgresql://engram:engram@127.0.0.1:54329/engram`

System cluster setup completed on 2026-04-28:

- Created Postgres role: `halbritt`
- Created database: `engram`
- Created test database: `engram_test`
- Created required extensions in both databases as the `postgres` superuser:
  `vector`, `pgcrypto`
- Ran migrations and full ingest as the local `halbritt` role.

## Implemented

- Plain SQL migrations with `schema_migrations` tracking.
- PostgreSQL + pgvector baseline.
- Raw evidence tables: `sources`, `conversations`, `messages`, `notes`,
  `captures`.
- `consolidation_progress` control table.
- Raw immutability trigger blocking `UPDATE` and `DELETE` on raw tables.
- ChatGPT export ingestion CLI.
- Claude.ai export ingestion CLI.
- Gemini Takeout ingestion CLI.
- Support for classic `conversations.json` exports and the newer split export
  format with `json/*.json` and `projects/*/json/*.json`.
- Support for Claude.ai `conversations.json` exports from zip archives or
  extracted directories.
- Support for Gemini Google Takeout's observed My Activity layout:
  `Takeout/My Activity/Gemini Apps/MyActivity.json`.
- Idempotent ingest using source and row dedup keys.
- Conflict detection for changed export content.
- Documentation in `docs/ingestion.md`.
- Tests for idempotent re-ingest, immutability, and conflict handling.
- Phase 1.5 cleanup:
  - Split ChatGPT export test coverage.
  - Internal duplicate conversation/message conflict test coverage.
  - Atomic source insert with `ON CONFLICT DO NOTHING RETURNING id`.
  - `captures.capture_type='reclassification'` enum value per D023.
  - `source_kind='claude'` enum value.
  - `source_kind='gemini'` enum value.

## Verification

Commands run successfully:

```bash
make migrate
make ingest-chatgpt PATH=~/chatgpt-export
make ingest-claude PATH=~/Downloads/data-840f283f-c304-49fc-b413-ae09939ac048-1777360228-dd8e408f-batch-0000.zip
make ingest-gemini PATH=~/Downloads/Takeout
make test
```

These verification commands now run against system Postgres by default.

ChatGPT ingest result:

```text
conversations: 3437 inserted / 3437 seen
messages: 67949 inserted / 67949 seen
```

Claude ingest result:

```text
conversations: 78 inserted / 78 seen
messages: 1037 inserted / 1037 seen
```

Gemini ingest result:

```text
conversations: 4401 inserted / 4401 seen
messages: 8401 inserted / 8401 seen
```

Second ingest result for each source:

```text
0 conversations inserted
0 messages inserted
```

Final conversation counts:

```text
chatgpt                3437
claude                   78
gemini                 4401
```

Final message counts:

```text
chatgpt               67949
claude                 1037
gemini                 8401
```

Control table:

```text
consolidation_progress 0
```

Test result:

```text
16 passed
```

Current `capture_type` values:

```text
observation
task
idea
reference
person_note
user_correction
reclassification
```

Current `source_kind` values:

```text
chatgpt
obsidian
capture
future
claude
gemini
```

## Notes

Attachments are not imported as file blobs in Phase 1. Their metadata and asset
pointers remain preserved in source-specific `raw_payload` fields.

System, hidden, tool/context, user, assistant, and source-specific activity
records are ingested where present because Phase 1 preserves raw evidence.
Downstream phases decide what to segment or ignore.
