# RFC 0044 Capability Boundary Evidence
author: operator [self-declared: rfc0044-capability-boundary-tests]

Status: pass with residual notes
Date: 2026-05-13
Job: `job_run_322110269dfb4ec98fc6f7ea818448c0_capability_boundary_tests`

## Scope

Focused local-only validation of the RFC 0044 Engram-side Phase 1 boundary:

- tenant/app isolation and corpus separation;
- Striatum bundle manifest validation and idempotence;
- provenance preservation for raw Striatum captures;
- read-only MCP stdio tool surface;
- default Striatum token denial for personal memory;
- explicit Engram-local grants for cross-boundary reads;
- absence of Striatum runtime dependency and network/cloud/telemetry code in the RFC 0044 runtime surface.

No private corpus content was used. All bundle rows in the manual probe were synthetic.

## Commands Run

Targeted RFC 0044 DB and service tests:

```sh
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest \
  tests/test_migrations.py::test_014_striatum_tenant_corpus_applies \
  tests/test_striatum_ingest.py \
  tests/test_mcp_stdio.py \
  tests/test_augmentation_boundary.py
```

Result:

```text
11 passed in 8.18s
```

Targeted CLI dispatch tests:

```sh
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest \
  tests/test_cli.py::test_ingest_striatum_dispatches_to_ingester \
  tests/test_cli.py::test_phase1_ingest_striatum_dispatches_to_ingester \
  tests/test_cli.py::test_describe_corpus_dispatches_to_memory_service
```

Result:

```text
3 passed in 0.09s
```

Manual synthetic-bundle probe:

```text
manual provenance and cross-corpus capability probe passed
```

The manual probe ingested one synthetic `run_summary` row with provenance keys
`path`, `sha256`, `commit`, `rfc`, `decision`, `run_id`, and `audit`; verified
the stored raw capture remained in `tenant_id='striatum'`,
`corpus_id='striatum'`; verified `raw_payload.provenance`, manifest summary,
`bundle_id`, `content_text`, search, and `fetch_reference` preservation; and
verified `MemoryToken.authorize_read_many` rejects same-tenant multi-corpus
authorization without `memory.read_cross_corpus` and accepts it with that
capability.

Runtime-surface inspection:

```sh
rg -n "requests|httpx|urllib|socket|telemetry|analytics|openai|boto|cloud|http://|https://" \
  src/engram/striatum_ingest.py src/engram/memory.py src/engram/mcp_stdio.py \
  agent-runner/engram-mcp-stdio pyproject.toml
```

Only a non-network docstring use of the word `requests` in the stdio serve loop
matched. No HTTP client, socket, hosted API, telemetry, cloud, or remote
persistence dependency was found in the RFC 0044 runtime surface.

```sh
rg -n "INSERT|UPDATE|DELETE|CREATE|write|mutation|claim|belief|segment|embedding|admin|sql" \
  src/engram/mcp_stdio.py src/engram/memory.py
```

Only stdout framing writes in `mcp_stdio.write_message` matched. No database
write, raw SQL admin, claim/belief mutation, segment/indexing, or embedding
operation is exposed through the MCP/memory serving surface.

## Evidence By Boundary

### Tenant And Corpus Isolation

Passed. `test_014_striatum_tenant_corpus_applies` verifies migration 014 adds
`tenant_id` and `corpus_id` to raw and key derived tables, adds `bundle_id` to
`captures`, and creates `captures_striatum_external_idx`.

Passed. `test_striatum_bundle_ingest_is_idempotent_and_preserves_boundary`
ingests a synthetic bundle twice and verifies the Striatum captures are grouped
only under `tenant_id='striatum'`, `corpus_id='striatum'`,
`source_kind='striatum'`.

### Manifest Validation And Idempotence

Passed. The targeted tests verify:

- idempotent re-ingest: first run inserts, second run skips unchanged rows;
- tampered file rejection on manifest hash mismatch;
- immutable-row conflict rejection when the same Striatum row key has different content.

### Provenance Preservation

Passed for synthetic coverage. The manual probe verified preservation and
serving of provenance fields covering source path, source hash, commit, RFC,
decision, run id, and audit metadata. The implementation stores these in raw
`captures.raw_payload`, exposes row provenance in `MemoryService.search`, and
re-exposes the stored row through `fetch_reference` after boundary
reauthorization.

### MCP Read-Only Surface

Passed. `test_mcp_stdio_exposes_only_rfc0044_read_only_tools` and
`test_mcp_initialize_and_tools_list_shape` verify the tool surface is exactly:

- `engram.search`
- `engram.fetch_reference`
- `engram.describe_corpus`
- `engram.health`

Static inspection found no write/admin/indexing/mutation path in
`src/engram/mcp_stdio.py` or `src/engram/memory.py`.

### Default Personal-Memory Denial

Passed. `test_default_striatum_token_cannot_read_personal_or_fetch_personal_reference`
creates both Striatum and personal raw captures. With the default Striatum
operator token, Striatum search succeeds, personal search raises
`MemoryCapabilityError`, and fetching an encoded personal capture reference
raises `MemoryCapabilityError`. `health()` reports only the visible Striatum
tenant/corpus pair.

### Cross-Boundary Grants

Passed for token-level behavior. `test_cross_corpus_capability_does_not_grant_cross_tenant`
verifies that granting `memory.read_cross_corpus` does not imply
`memory.read_cross_tenant`. The manual probe verifies that same-tenant
multi-corpus authorization requires `memory.read_cross_corpus`.

Phase 1 has only single-corpus search/fetch tools, so there is no MCP
multi-corpus retrieval call to exercise end to end yet.

### Local-Only And No Striatum Runtime Dependency

Passed by focused test and inspection. `test_engram_has_no_runtime_striatum_imports`
found no `import striatum` or `from striatum` in `src/engram`.
`test_pyproject_does_not_depend_on_striatum_orchestrator` verifies the project
does not depend on `striatum-orchestrator`. Runtime inspection found no HTTP,
socket, cloud API, hosted persistence, or telemetry code in the RFC 0044
runtime surface.

## Residual Notes

- These are synthetic focused tests, not a quality smoke over a real Striatum
  export bundle.
- No OS-level no-egress sandbox was exercised in this pass; no-egress evidence
  here is code/test inspection of the RFC 0044 runtime surface.
- MCP stdio tests cover tool-list and framing shape directly; capability
  enforcement is covered through `MemoryService` tests and the manual synthetic
  probe rather than a full subprocess JSON-RPC session against a live database.

## Verdict

RFC 0044 Phase 1 capability-boundary tests pass for the focused local evidence
requested. No blocking capability-boundary regression was found.
