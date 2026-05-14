# RFC 0044 Engram Phase 1 Implementation Review - codex
author: operator [self-declared: rfc0044-review-correctness]

Status: review
Date: 2026-05-13
External Striatum RFC: 0044
Decision refs: D001, D002, D020

## Findings

### F001 - Single-pair reads bypass cross-tenant and cross-corpus capabilities
Severity: blocking
Source: src/engram/memory.py:64
Rationale: `MemoryToken.authorize_read()` authorizes one requested
`TenantCorpus` by checking only that the pair is in `allowed_pairs` plus the
tenant-specific read capability. It does not enforce `memory.read_cross_tenant`
when the token can read more than one tenant, and it does not enforce
`memory.read_cross_corpus` when the token can read a second corpus inside the
same tenant. The stricter logic exists only in `authorize_read_many()`, but the
actual serving methods call `authorize_read()` for `search()` and
`fetch_reference()` (`src/engram/memory.py:144`,
`src/engram/memory.py:208`). `engram-mcp-stdio` can build such a multi-pair
token via `--allow-pair` while retaining the default `memory.read_striatum`
capability (`src/engram/mcp_stdio.py:110`). I verified locally that a token with
allowed pairs `striatum/striatum` and `striatum/secondary`, but without
`memory.read_cross_corpus`, allows `authorize_read(striatum/secondary)`;
likewise a token with `memory.read_personal` but without
`memory.read_cross_tenant` allows a personal pair. That violates the terminology
handoff's requirement that `memory.read_cross_tenant` is required to query more
than one tenant or outside the fixed tenant scope, and
`memory.read_cross_corpus` is required to query more than one corpus inside an
allowed tenant. Fix by making the single-pair service path aware of the token's
fixed/primary scope, or by requiring the cross-boundary capability whenever a
requested pair is outside that scope; add service or MCP-path tests for the
same-tenant second-corpus and personal-second-tenant cases.

### F002 - Cross-boundary tests cover the helper path, not the serving path
Severity: major
Source: tests/test_striatum_ingest.py:199
Rationale: The focused tests do not exercise the failing service path above.
`test_cross_corpus_capability_does_not_grant_cross_tenant` proves only that
`memory.read_cross_corpus` does not imply `memory.read_cross_tenant`, and the
capability evidence says the same-tenant multi-corpus probe used
`MemoryToken.authorize_read_many()`. The MCP and `MemoryService.search()` paths
never call `authorize_read_many()`, so the test suite can pass while the actual
single-corpus `engram.search` call reads a second allowed corpus without
`memory.read_cross_corpus`. Add regression tests through `MemoryService.search`
and, ideally, `mcp_stdio.handle_request()` or a framed stdio call using a token
constructed the way the CLI constructs it.

## Open Questions

- Should `--allow-pair` mean metadata visibility only until the matching
  `memory.read_*` and `memory.read_cross_*` capabilities are present, or should
  it be renamed/documented as an explicit read grant? The handoff currently
  treats capabilities, not pair visibility alone, as the read boundary.

## Reviewed Areas Without Additional Findings

- Local-only posture: no HTTP client, socket serving path, hosted persistence,
  telemetry, or cloud dependency was found in `src/engram/striatum_ingest.py`,
  `src/engram/memory.py`, `src/engram/mcp_stdio.py`, the wrapper script, or
  `pyproject.toml`.
- Augmentation boundary: no `import striatum`, no `striatum-orchestrator`
  dependency, and no Engram-side writes into Striatum state were found.
- Phase discipline: Striatum ingest writes raw `captures`; extraction and
  consolidation still filter to ChatGPT/Claude/Gemini conversation segments.
- MCP surface: the advertised tool list is exactly `engram.search`,
  `engram.fetch_reference`, `engram.describe_corpus`, and `engram.health`, with
  no write/admin/raw-SQL tool exposed.

## Verification

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_migrations.py::test_014_striatum_tenant_corpus_applies tests/test_striatum_ingest.py tests/test_mcp_stdio.py tests/test_augmentation_boundary.py tests/test_cli.py::test_ingest_striatum_dispatches_to_ingester tests/test_cli.py::test_phase1_ingest_striatum_dispatches_to_ingester tests/test_cli.py::test_describe_corpus_dispatches_to_memory_service`
  passed: 14 tests.
- Local capability probe confirmed the F001 bypass for a same-tenant secondary
  corpus and for a personal second tenant when `memory.read_personal` is present
  but `memory.read_cross_tenant` is absent.

verdict: needs_revision
