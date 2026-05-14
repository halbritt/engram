# RFC 0044 Engram Phase 1 Implementation Handoff
author: operator [self-declared: rfc0044-implement-phase1]

Status: implemented
Date: 2026-05-13
External Striatum RFC: 0044
Decision refs: D001, D002, D020

## Summary

Implemented the Engram-side RFC 0044 Phase 1 surface: Striatum corpus bundles
can be ingested from disk into a local `tenant_id='striatum'`,
`corpus_id='striatum'` boundary, queried via a read-only memory service, and
served through `engram-mcp-stdio` with exactly the four Phase 1 MCP tools.

No Striatum runtime import or dependency was added. The integration is
augmentation-only: Engram reads exported files, preserves them as raw captures,
and never calls Striatum or writes into a target repository `.striatum/`
directory.

## Files Changed

- `migrations/014_striatum_tenant_corpus.sql`
- `src/engram/striatum_ingest.py`
- `src/engram/memory.py`
- `src/engram/mcp_stdio.py`
- `src/engram/cli.py`
- `agent-runner/engram-mcp-stdio`
- `pyproject.toml`
- `Makefile`
- `tests/test_striatum_ingest.py`
- `tests/test_mcp_stdio.py`
- `tests/test_augmentation_boundary.py`
- `tests/test_cli.py`
- `tests/test_migrations.py`
- `README.md`
- `SPEC.md`
- `CHANGELOG.md`
- `docs/schema/README.md`

## Tenant And Corpus Boundaries

Migration 014 adds `source_kind='striatum'` and `tenant_id` / `corpus_id`
columns with default `personal` backfill semantics across raw and key derived
tables. It also refreshes immutability guard functions so tenant/corpus fields
cannot drift through allowed lifecycle updates.

The Striatum ingester is fixed to `tenant_id='striatum'` and
`corpus_id='striatum'`; there is no operator-supplied tenant override in
Phase 1. Existing personal rows continue to default to
`tenant_id='personal', corpus_id='personal'`.

## Bundle Manifest And Provenance Handling

`engram ingest-striatum --bundle <dir> [--repo <name>]` reads `manifest.json`
and the nine RFC 0044 JSONL files from disk. It verifies manifest schema,
declared source kind, file hashes, byte counts, row counts, row sub-kind/file
placement, duplicate `(sub_kind, external_id)` rows, and optional
`bundle_sha256` if present.

Each corpus row is written as an immutable raw `captures` row with
`source_kind='striatum'`, `capture_type='reference'`, `bundle_id`, row content,
observed timestamp, repo label, manifest summary, row hash, and source
provenance. Re-ingesting the same rows is a no-op; same tenant/corpus row key
with different content raises `IngestConflict`.

## MCP And Capability Boundary

`engram-mcp-stdio` is a standalone console script and local wrapper under
`agent-runner/`. It uses stdio framing only; no hosted service, sockets, raw SQL
tool, write tool, claim creation, belief mutation, or indexing/admin operation
is exposed.

The only MCP tools are:

- `engram.search`
- `engram.fetch_reference`
- `engram.describe_corpus`
- `engram.health`

Default access grants `memory.read_striatum` and `memory.describe` for the
configured Striatum tenant/corpus pair. Personal memory requires
`memory.read_personal`; multi-tenant and multi-corpus requests require explicit
Engram-local grants. `fetch_reference` decodes the opaque reference, loads the
stored row, and rechecks the row's own `tenant_id` and `corpus_id`.

## Tests / Validation Run

- Targeted RFC 0044 DB tests:
  `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_migrations.py::test_014_striatum_tenant_corpus_applies tests/test_striatum_ingest.py tests/test_mcp_stdio.py tests/test_augmentation_boundary.py`
  -> `11 passed`
- Full suite after the final migration/index changes:
  `make test` -> `538 passed in 256.37s`
- Targeted lint/format:
  `.venv/bin/python -m ruff check ...` and
  `.venv/bin/python -m ruff format --check ...` on touched Python files -> pass
- Targeted type check:
  `.venv/bin/python -m pyright --pythonpath .venv/bin/python ...` on new RFC
  0044 modules/tests -> `0 errors`
- `make schema-docs DATABASE_URL=postgresql:///engram_test` regenerated
  `docs/schema/README.md`.
- `git diff --check` -> pass.
- Full-repo `make lint` was attempted but remains blocked by pre-existing
  unrelated Ruff debt in `benchmarks/`, `agent-runner/`, and older Phase 3
  tests. No unrelated lint rewrites were made.

## Residual Risk

Search is deterministic lexical retrieval over raw Striatum captures, not a
Phase 2 segment/vector retrieval path. That is intentional for Phase 1 and
keeps claims/beliefs out of scope, but smoke quality should still be measured
against a real Striatum export bundle before V1 acceptance.

The migration adds boundary columns broadly with `personal` defaults, while
existing derived workers mostly continue to rely on defaults. That preserves
current behavior and satisfies Phase 1 isolation, but future non-personal
derived pipelines should explicitly propagate tenant/corpus values when they
start producing segments, claims, or beliefs outside the personal tenant.
