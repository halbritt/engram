# RFC 0044 Capability Boundary Repair Review - codex
author: operator [self-declared: rfc0044-repair-correctness-review]

Status: review
Date: 2026-05-13
External Striatum RFC: 0044
Prior review: `REVIEW_correctness_codex.md`

## Findings

No findings.

## Prior Findings Recheck

### F001 - Single-pair reads bypass cross-tenant and cross-corpus capabilities

Status: resolved.

`MemoryToken` now carries an explicit `primary_pair`, and
`MemoryToken.authorize_read()` calls `_authorize_cross_boundary()` before
tenant-specific read grants are accepted. A visible but non-primary same-tenant
corpus now requires `memory.read_cross_corpus`; a visible non-primary tenant now
requires `memory.read_cross_tenant`.

The actual serving methods still authorize through the single-pair path:
`MemoryService.search()` calls `authorize_read()` for the requested pair, and
`MemoryService.fetch_reference()` decodes the opaque reference, loads the stored
row, and re-authorizes the row's own `tenant_id` / `corpus_id` before returning
content. The prior bypass through `--allow-pair` is closed because
`engram-mcp-stdio` builds the token with `primary_pair` from the primary
`--tenant` / `--corpus` arguments, while extra `--allow-pair` values only add
visibility.

### F002 - Cross-boundary tests cover the helper path, not the serving path

Status: resolved.

The repair adds service-path regressions for both prior bypass shapes:

- `test_service_search_and_fetch_require_cross_corpus_for_secondary_striatum_corpus`
  verifies both `MemoryService.search()` and `MemoryService.fetch_reference()`
  deny a secondary Striatum corpus until `memory.read_cross_corpus` is present,
  then allow the same calls after the grant.
- `test_service_search_and_fetch_require_cross_tenant_for_personal_pair`
  verifies both serving methods deny a visible personal pair until
  `memory.read_cross_tenant` is present, even when `memory.read_personal` is
  already granted.
- `test_mcp_allow_pair_does_not_bypass_cross_corpus_for_search_or_fetch`
  exercises `mcp_stdio.handle_request()` with the same token shape produced by
  CLI `--allow-pair striatum/secondary` and verifies both `engram.search` and
  `engram.fetch_reference` return MCP tool errors before the cross-corpus grant.

These tests target the previously failing service and MCP handler paths rather
than only `MemoryToken.authorize_read_many()`.

## Verification

Reviewed:

- `src/engram/memory.py`
- `src/engram/mcp_stdio.py`
- `tests/test_striatum_ingest.py`
- `tests/test_mcp_stdio.py`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/REPAIR_CAPABILITY_HANDOFF.md`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/REPAIR_CAPABILITY_EVIDENCE.md`

Ran focused local tests:

```sh
PYTHONDONTWRITEBYTECODE=1 ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test \
  .venv/bin/python -m pytest -p no:cacheprovider \
  tests/test_striatum_ingest.py::test_service_search_and_fetch_require_cross_corpus_for_secondary_striatum_corpus \
  tests/test_striatum_ingest.py::test_service_search_and_fetch_require_cross_tenant_for_personal_pair \
  tests/test_mcp_stdio.py::test_mcp_allow_pair_does_not_bypass_cross_corpus_for_search_or_fetch
```

Result:

```text
3 passed in 3.25s
```

I did not rerun the full suite in this review pass; the repair evidence reports
the focused repair target set passing, and the repair handoff reports
`make test` passing with 541 tests.

## Verdict

verdict: accept
