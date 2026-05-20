# Striatum Memory Real-Bundle E2E Runbook

Date: 2026-05-17

This runbook verifies the local Striatum memory path against a real Striatum
corpus export bundle. It uses local files, local Postgres, and MCP stdio only.
No corpus-reading step should require network access.

## Preconditions

- Engram dependencies are installed: `make install`.
- The target database is migrated: `make migrate`.
- A local Striatum corpus export bundle exists on disk.
- `ENGRAM_DATABASE_URL` points at the intended local database when not using
  the Makefile default.

## Ingest And Build Projections

```sh
ENGRAM_DATABASE_URL="${ENGRAM_DATABASE_URL:-postgresql:///engram}" \
  .venv/bin/python -m engram.cli phase1 ingest-striatum --bundle /path/to/striatum-bundle --repo striatum
ENGRAM_DATABASE_URL="${ENGRAM_DATABASE_URL:-postgresql:///engram}" \
  .venv/bin/python -m engram.cli phase-projection run --tenant striatum --corpus striatum
ENGRAM_DATABASE_URL="${ENGRAM_DATABASE_URL:-postgresql:///engram}" \
  .venv/bin/python -m engram.cli evidence refresh-index --tenant striatum --corpus striatum
```

## Smoke The Local Surfaces

```sh
make e2e-striatum
ENGRAM_DATABASE_URL="${ENGRAM_DATABASE_URL:-postgresql:///engram}" \
  .venv/bin/engram describe-corpus striatum
ENGRAM_DATABASE_URL="${ENGRAM_DATABASE_URL:-postgresql:///engram}" \
  .venv/bin/engram-mcp-stdio --tenant striatum --corpus striatum --health-check
```

`make e2e-striatum` uses the committed non-private fixture. The real-bundle
checks above prove the target corpus is visible and the MCP server can start
against the same local database.

## MCP Packet Check

Start the server:

```sh
ENGRAM_DATABASE_URL="${ENGRAM_DATABASE_URL:-postgresql:///engram}" \
  .venv/bin/engram-mcp-stdio --tenant striatum --corpus striatum
```

From an MCP client, call:

- `engram.search` with `tenant="striatum"`, `corpus="striatum"`, and a query
  known to match the exported bundle.
- `engram.build_packet` with the same tenant/corpus and query.
- `engram.fetch_reference` for a reference returned by search or packet
  building.

The expected result is cited local evidence only. Packet output should carry
citations and omission reasons without raw body leakage in audits.

## Failure Interpretation

- `describe-corpus` cannot see `striatum`: re-check bundle ingest and database
  URL.
- Search finds no rows: rerun `phase-projection run` and `evidence refresh-index`
  for `tenant=striatum`, `corpus=striatum`.
- `fetch_reference` returns unauthorized/not found for a returned citation:
  treat as a regression in reference reauthorization or citation rendering.
- Any outbound-network requirement is a bug. Corpus-reading paths must remain
  local-only.
