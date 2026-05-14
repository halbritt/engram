# RFC 0044 Capability Boundary Repair Handoff
author: operator [self-declared: rfc0044-repair-capability-boundary]

Status: implemented
Date: 2026-05-13
Job: `job_run_1aadc5c6bc00434497bc6d9754358a62_repair_capability_boundary`

## Summary

Repaired the single-pair serving authorization gap identified in
`REVIEW_correctness_codex.md` finding F001.

`MemoryToken` now carries an explicit `primary_pair` fixed scope. Single-pair
read authorization still requires the requested pair to be visible, but also
requires:

- `memory.read_cross_corpus` before reading any non-primary corpus inside the
  same tenant;
- `memory.read_cross_tenant` before reading any non-primary tenant;
- the existing tenant-specific read capability such as `memory.read_striatum`
  or `memory.read_personal`.

`engram-mcp-stdio` now sets `primary_pair` from the primary `--tenant` /
`--corpus` arguments before adding extra `--allow-pair` visibility entries.
This preserves the intended distinction between pair visibility and elevated
cross-boundary read authority.

## Files Changed

- `src/engram/memory.py`
- `src/engram/mcp_stdio.py`
- `tests/test_striatum_ingest.py`
- `tests/test_mcp_stdio.py`
- `CHANGELOG.md`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/REPAIR_CAPABILITY_HANDOFF.md`

## Regression Coverage

Added service-path tests proving:

- a token with visible pairs `striatum/striatum` and `striatum/secondary`,
  but without `memory.read_cross_corpus`, cannot search or fetch the secondary
  Striatum corpus;
- the same token succeeds only after `memory.read_cross_corpus` is added;
- a token with visible pairs `striatum/striatum` and `personal/personal`, and
  with `memory.read_personal` but without `memory.read_cross_tenant`, cannot
  search or fetch personal rows;
- the same token succeeds only after `memory.read_cross_tenant` is added.

Added MCP-handler coverage proving a token built with the same shape as the
CLI `--allow-pair striatum/secondary` path returns MCP tool errors for both
`engram.search` and `engram.fetch_reference` until cross-corpus capability is
present.

## Commands Run

Focused service and MCP tests:

```sh
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_striatum_ingest.py tests/test_mcp_stdio.py
```

Result:

```text
11 passed in 9.02s
```

RFC 0044 target set:

```sh
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_migrations.py::test_014_striatum_tenant_corpus_applies tests/test_striatum_ingest.py tests/test_mcp_stdio.py tests/test_augmentation_boundary.py tests/test_cli.py::test_ingest_striatum_dispatches_to_ingester tests/test_cli.py::test_phase1_ingest_striatum_dispatches_to_ingester tests/test_cli.py::test_describe_corpus_dispatches_to_memory_service
```

Result:

```text
17 passed in 9.96s
```

Targeted lint / format:

```sh
.venv/bin/python -m ruff format src/engram/memory.py src/engram/mcp_stdio.py tests/test_striatum_ingest.py tests/test_mcp_stdio.py
.venv/bin/python -m ruff check src/engram/memory.py src/engram/mcp_stdio.py tests/test_striatum_ingest.py tests/test_mcp_stdio.py
```

Result:

```text
4 files left unchanged
All checks passed!
```

Targeted type check:

```sh
.venv/bin/python -m pyright --pythonpath .venv/bin/python src/engram/memory.py src/engram/mcp_stdio.py tests/test_striatum_ingest.py tests/test_mcp_stdio.py
```

Result:

```text
0 errors, 0 warnings, 0 informations
```

Full suite:

```sh
make test
```

Result:

```text
541 passed in 270.21s (0:04:30)
```

## Notes

An attempted parallel run of two database-backed pytest commands against the
same `engram_test` database produced fixture-reset races and was discarded as
invalid. The same commands were rerun serially and passed.

## Residual Risk

The repair covers the current RFC 0044 single-pair serving paths:
`MemoryService.search`, `MemoryService.fetch_reference`, and MCP `tools/call`
dispatch. Future multi-pair retrieval tools must continue using the same
primary-scope semantics and should keep explicit service-path tests rather than
testing only `MemoryToken.authorize_read_many()`.
