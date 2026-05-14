# RFC 0044 Repair Capability Evidence
author: operator [self-declared: rfc0044-repair-boundary-tests]

Status: pass
Date: 2026-05-13
Job: `job_run_1aadc5c6bc00434497bc6d9754358a62_repair_boundary_tests`

## Scope

Focused local-only validation after the RFC 0044 capability-boundary repair.
This pass targeted the single-pair service and MCP authorization paths that
previously bypassed cross-corpus / cross-tenant capability checks.

No private corpus content was used. No hosted service or network test was run.

## Commands Run

Focused service and MCP tests:

```sh
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_striatum_ingest.py tests/test_mcp_stdio.py
```

Result:

```text
11 passed in 9.33s
```

Adjacent RFC 0044 target tests:

```sh
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_migrations.py::test_014_striatum_tenant_corpus_applies tests/test_augmentation_boundary.py tests/test_cli.py::test_ingest_striatum_dispatches_to_ingester tests/test_cli.py::test_phase1_ingest_striatum_dispatches_to_ingester tests/test_cli.py::test_describe_corpus_dispatches_to_memory_service
```

Result:

```text
6 passed in 1.17s
```

Runtime-surface inspection:

```sh
rg -n "requests|httpx|urllib|socket|telemetry|analytics|openai|boto|cloud|http://|https://" src/engram/striatum_ingest.py src/engram/memory.py src/engram/mcp_stdio.py agent-runner/engram-mcp-stdio pyproject.toml
```

Result:

```text
src/engram/mcp_stdio.py:224:    """Serve MCP requests until stdin closes."""
```

Read-only serving-surface inspection:

```sh
rg -n "INSERT|UPDATE|DELETE|CREATE|write|mutation|claim|belief|segment|embedding|admin|sql" src/engram/mcp_stdio.py src/engram/memory.py
```

Result:

```text
src/engram/mcp_stdio.py:215:def write_message(stdout: BinaryIO, payload: dict[str, Any]) -> None:
src/engram/mcp_stdio.py:218:    stdout.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
src/engram/mcp_stdio.py:219:    stdout.write(body)
src/engram/mcp_stdio.py:231:            write_message(stdout, response)
```

Striatum runtime dependency inspection:

```sh
rg -n "import striatum|from striatum|striatum-orchestrator" src/engram pyproject.toml
```

Result: no matches.

## Evidence By Boundary

### Service Path Cross-Corpus Enforcement

Passed. `tests/test_striatum_ingest.py` includes
`test_service_search_and_fetch_require_cross_corpus_for_secondary_striatum_corpus`.
It verifies a token with visible pairs `striatum/striatum` and
`striatum/secondary`, but without `memory.read_cross_corpus`, cannot
`search()` or `fetch_reference()` the secondary Striatum corpus. The same
service calls succeed only after `memory.read_cross_corpus` is added.

### Service Path Cross-Tenant Enforcement

Passed. `tests/test_striatum_ingest.py` includes
`test_service_search_and_fetch_require_cross_tenant_for_personal_pair`. It
verifies a token with visible pairs `striatum/striatum` and
`personal/personal`, even with `memory.read_personal`, cannot `search()` or
`fetch_reference()` personal rows without `memory.read_cross_tenant`. The same
service calls succeed only after `memory.read_cross_tenant` is added.

### MCP `--allow-pair` Enforcement

Passed. `tests/test_mcp_stdio.py` includes
`test_mcp_allow_pair_does_not_bypass_cross_corpus_for_search_or_fetch`. It
constructs the same token shape as the CLI `--allow-pair striatum/secondary`
path and verifies both `engram.search` and `engram.fetch_reference` return MCP
tool errors containing `memory.read_cross_corpus` until the cross-corpus
capability is present.

### Adjacent RFC 0044 Coverage

Passed. The adjacent target set confirmed migration 014 application,
augmentation-boundary tests, and CLI dispatch for `ingest-striatum`,
`phase1 ingest-striatum`, and `describe-corpus`.

### Local-Only And Read-Only Surface

Passed by focused static inspection. No HTTP client, socket, cloud API,
telemetry, hosted persistence, or Striatum runtime import/dependency was found
in the RFC 0044 runtime surface. The only read-only scan matches were stdio
response writes in `mcp_stdio.write_message`; no MCP/database mutation, raw SQL
admin path, claim/belief mutation, segment/indexing, or embedding operation was
found in `src/engram/mcp_stdio.py` or `src/engram/memory.py`.

## Residual Notes

- This pass did not run the full test suite; the repair handoff already
  reported a full-suite pass, and this job was scoped to focused repair
  evidence.
- No OS-level no-egress sandbox was exercised. Local-only evidence here is
  static inspection plus the stdio-only test surface.
- No real Striatum export bundle was used; the targeted tests use synthetic
  local fixtures.

## Verdict

The RFC 0044 repair boundary tests pass. The previously reviewed
single-pair service/MCP capability gap is covered through the actual
`MemoryService.search`, `MemoryService.fetch_reference`, and MCP `tools/call`
paths, with explicit denial before cross-boundary capability grants and success
after the required grants.
