# Phase 1 Build Status

Status: implemented; Phase 1.5 cleanup applied and verified on system Postgres
Date: 2026-04-28

## Database

Initial verification used the Dockerized Postgres instance defined in
`docker-compose.yml`. After review, the repo defaults were changed so normal
`make migrate`, `make ingest-chatgpt`, and `make test` target system Postgres
through local socket URLs.

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
- Support for classic `conversations.json` exports and the newer split export
  format with `json/*.json` and `projects/*/json/*.json`.
- Idempotent ingest using source and row dedup keys.
- Conflict detection for changed export content.
- Documentation in `docs/ingestion.md`.
- Tests for idempotent re-ingest, immutability, and conflict handling.
- Phase 1.5 cleanup:
  - Split ChatGPT export test coverage.
  - Internal duplicate conversation/message conflict test coverage.
  - Atomic source insert with `ON CONFLICT DO NOTHING RETURNING id`.
  - `captures.capture_type='reclassification'` enum value per D023.

## Verification

Commands run successfully:

```bash
make migrate
make ingest-chatgpt PATH=/home/halbritt/chatgpt-export
make test
```

These verification commands now run against system Postgres by default.

Full export ingest result:

```text
conversations: 3437 inserted / 3437 seen
messages: 67949 inserted / 67949 seen
```

Second ingest result:

```text
conversations: 0 inserted / 3437 seen
messages: 0 inserted / 67949 seen
```

Final row counts:

```text
sources                  1
conversations         3437
messages             67949
consolidation_progress   0
```

Test result:

```text
6 passed
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

## Notes

Attachments are not imported as file blobs in Phase 1. Their metadata and asset
pointers remain preserved in message `raw_payload`.

System, hidden, tool/context, user, and assistant messages are all ingested
because Phase 1 preserves raw evidence. Downstream phases decide what to
segment or ignore.
