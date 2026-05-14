# RFC 0044 Engram Phase 1 Implementation Review - claude
author: operator [self-declared: rfc0044-review-boundary]

Status: review
Date: 2026-05-13
External Striatum RFC: 0044
Decision refs: D001, D002, D020

## Scope

Independent security-focused review of the RFC 0044 Phase 1 surface as
implemented on master. Boundary surfaces inspected:

- `migrations/014_striatum_tenant_corpus.sql`
- `src/engram/striatum_ingest.py`
- `src/engram/memory.py`
- `src/engram/mcp_stdio.py`
- `src/engram/cli.py` (RFC 0044 dispatch and CLI shorthand)
- `agent-runner/engram-mcp-stdio`
- `pyproject.toml`
- `tests/test_striatum_ingest.py`
- `tests/test_mcp_stdio.py`
- `tests/test_augmentation_boundary.py`
- `tests/test_migrations.py` (RFC 0044 portion)

I did not re-execute the test suite; I read the test bodies and verified
they enforce the claims in `CAPABILITY_BOUNDARY_EVIDENCE.md` and
`IMPLEMENTATION_HANDOFF.md`. No write was made outside the declared review
path. Read-only inspection used `Read` and `Grep`.

## Summary

Phase 1 tenant/corpus boundary enforcement, local-only posture,
manifest/provenance handling, the four-tool read-only MCP surface, and the
augmentation-not-dependency rule all look correctly implemented and
test-covered for the cases RFC 0044 names as boundary acceptance criteria.
The default Striatum operator token cannot read personal memory, cannot
read an unknown future tenant, and cannot read a second corpus inside the
Striatum tenant without explicit Engram-local grants. `fetch_reference`
re-authorizes against the stored row's `tenant_id` / `corpus_id` rather
than trusting the opaque reference. The RFC 0044 runtime surface contains
no HTTP client, socket, hosted persistence, telemetry, or Striatum runtime
import.

No blocking or major findings. The findings below are minor or nit-level
defense-in-depth observations.

## Findings

### F001 - `describe-corpus` CLI synthesizes `tenant_id` from the positional `corpus` argument
Severity: minor
Source: `src/engram/cli.py:738-746`, `src/engram/cli.py:196-210`

`engram describe-corpus <corpus>` accepts an optional `--tenant`. When the
flag is omitted, the dispatcher does `tenant_id = args.tenant or args.corpus`,
so the positional `corpus` value is also used as the tenant. This works for
the convenience default `striatum/striatum`, but it generalizes the shorthand
beyond the case the tenant terminology handoff sanctions: the handoff (and
RFC 0044) says corpus shorthand is only a convenience default for
`tenant_id='striatum', corpus_id='striatum'`, and that handlers must store
and check both fields. The MCP path (`engram-mcp-stdio`) takes `--tenant`
and `--corpus` as independent flags with the correct defaults and does not
have this collapse. The current authorization model still rejects arbitrary
shorthand because the default token's `allowed_pairs` is
`{striatum/striatum}`, so this is not a boundary bypass — it is just a CLI
shape that contradicts the explicit two-key requirement and could mask the
distinction during operator triage. Consider making `--tenant` required, or
only synthesizing `striatum/striatum` from positional `striatum`.

### F002 - MCP tool errors distinguish "not allowed" vs "not visible" vs "not found" vs missing-capability text
Severity: minor
Source: `src/engram/memory.py:55-79`, `src/engram/memory.py:181-208`,
`src/engram/mcp_stdio.py:160-181`

`MemoryToken.authorize_describe`, `authorize_read`, and `fetch_reference`
return distinct error strings: `tenant/corpus "x/y" is not visible`,
`tenant/corpus "x/y" is not allowed`, `missing capability
"memory.read_personal"`, `reference not found "..."`, and `malformed
reference_id`. The MCP handler returns these as `isError: true` text in the
tool call result. This gives a probing client three weakly distinct
signals: "this pair exists in the schema but my token can't see it", "this
opaque reference points at a real row but it is in a tenant I cannot
read", and "this reference does not resolve". For the RFC 0044 default
Striatum operator session, this is a side channel that lets the operator
agent learn whether a reference id points at a real personal row. The
boundary still holds — no content is returned — but a uniform "not
authorized for this reference" string would be more conservative.
Acceptable in Phase 1 because the operator owns both the Engram daemon and
the MCP client and reference ids are not handed to remote parties.

### F003 - Migration 014 does not enforce `tenant_id='striatum' ⇒ source_kind='striatum'` at the DB layer
Severity: minor
Source: `migrations/014_striatum_tenant_corpus.sql:5-35,103-111`

The migration adds `tenant_id` / `corpus_id` with `DEFAULT 'personal'`,
adds non-empty CHECKs on those columns, and adds a unique index on
`(tenant_id, corpus_id, source_kind, external_id) WHERE tenant_id =
'striatum' AND corpus_id = 'striatum'`. It does not add a CHECK forbidding
`tenant_id='striatum'` rows that have a non-`striatum` `source_kind`, and
does not forbid `source_kind='striatum'` rows under a non-Striatum
`tenant_id/corpus_id`. The Phase 1 ingester only writes
`tenant_id='striatum', corpus_id='striatum', source_kind='striatum'` and
existing personal pipelines do not touch the striatum tenant, so this is
not currently violated. As a defense-in-depth measure, a CHECK like
`CHECK ((tenant_id = 'striatum') = (source_kind::text = 'striatum'))` on
`captures` and `sources` would make the boundary structurally enforceable
rather than relying on application discipline.

### F004 - `fetch_reference` does not pin `source_kind` to the request's tenant
Severity: minor
Source: `src/engram/memory.py:181-224`

`fetch_reference` decodes the reference id, requires `table == 'captures'`,
loads the row by primary key, then re-authorizes against the row's stored
`tenant_id` / `corpus_id`. This is the correct re-authorization pattern.
It does not, however, cross-check that `source_kind` is consistent with
the tenant (for example, refusing to return a `source_kind='capture'` row
when `tenant_id='striatum'`). Combined with F003, this means that if a
future bug inserts a personal-typed row under the Striatum tenant, a
default Striatum operator token could read it through `fetch_reference`.
Phase 1 has no such code path. Optional hardening: have `fetch_reference`
require `(tenant_id, source_kind)` to be in a small allow set keyed off
the token's capabilities.

### F005 - `engram-mcp-stdio --capability` accepts arbitrary strings
Severity: nit
Source: `src/engram/mcp_stdio.py:108-118,234-243`

`build_token` adds any string passed as `--capability` to the token's
capability set without checking against the known `memory.*` set. A typo
such as `--capability memory.read_persoanl` would be silently accepted as
a non-matching capability and never satisfy any check, so the failure mode
is "operator thought they granted access but did not", not over-grant.
Still worth a small allow-list check or warning.

### F006 - `engram-mcp-stdio` `read_message` does not cap `Content-Length`
Severity: nit
Source: `src/engram/mcp_stdio.py:185-207`

`read_message` parses `Content-Length` directly into `int(...)` and then
reads that many bytes from stdin. A malformed peer could declare an
oversized length and force a large allocation, or could send junk that
fails JSON parsing and crashes the server (header errors and JSON errors
both raise `ValueError` and bubble up out of `serve_stdio`, terminating
the process). For a local stdio server with an operator-controlled client
the blast radius is one MCP session. Optional: bound the length and wrap
parse errors in a JSON-RPC `-32700` parse-error response instead of an
unhandled exception.

### F007 - Augmentation-boundary test is repository-scoped only on the Engram side
Severity: minor (open question)
Source: `tests/test_augmentation_boundary.py:1-23`

`test_engram_has_no_runtime_striatum_imports` and
`test_pyproject_does_not_depend_on_striatum_orchestrator` are sufficient
to enforce the Engram half of the augmentation rule (no
`import striatum`, no `striatum-orchestrator` dependency). RFC 0044
Section 8 ("Augmentation-Not-Dependency Enforcement") also requires that
no Striatum CLI module imports an Engram client library, that no Striatum
daemon RPC method references Engram, and that Engram unavailability
degrades gracefully. Those guarantees live on the Striatum side and were
not in this review's input set. The Engram-side review covers the half of
the contract that the Engram repo can actually own; the other half should
be verified independently inside the Striatum repo.

### F008 - `health()` schema_version uses `max(filename)` on `schema_migrations`
Severity: nit
Source: `src/engram/memory.py:295-333`

`health()` returns the lexicographically maximum migration filename as
`schema_version`. RFC 0044 names "schema/adapter versions" as part of
`engram.describe_corpus`. The current implementation uses lexicographic
ordering of filename strings, which is fine for the zero-padded
`NNN_*.sql` convention but breaks if a future migration is added with a
non-zero-padded prefix. Recommend ordering by the numeric prefix or by
`applied_at`.

### F009 - `decode_reference_id` propagates JSON shape errors as `MemoryReferenceError`, but Postgres errors are not wrapped
Severity: nit
Source: `src/engram/memory.py:399-412`, `src/engram/memory.py:181-208`

`decode_reference_id` wraps base64 / JSON failures into `MemoryReferenceError`.
If the decoded `id` is a syntactically valid string but not a UUID, the
`WHERE id = %s` parameter binding hands Postgres a malformed UUID and
raises `psycopg.errors.InvalidTextRepresentation`, which is not caught
here and not in the MCP error-translation list either, so it bubbles up
the JSON-RPC `tools/call` path as an unhandled exception. Defense-in-
depth: validate the decoded `id` is a UUID before issuing the query, or
catch the Postgres error and rewrap as `MemoryReferenceError`.

## Boundary Checklist Result

| Check | Result |
|---|---|
| Tenant/app isolation enforced in code and tests | yes |
| Corpus separation enforced and stored with provenance | yes |
| Personal corpus refusal at search and fetch | yes (`test_default_striatum_token_cannot_read_personal_or_fetch_personal_reference`) |
| Cross-corpus capability does not imply cross-tenant | yes (`test_cross_corpus_capability_does_not_grant_cross_tenant`) |
| No cloud dep / telemetry / outbound network | yes (no HTTP/socket/cloud imports in RFC 0044 runtime surface; pyproject only psycopg + dev/serve deps) |
| Bundle manifest hashes, byte counts, row counts validated | yes (`load_jsonl_file`, `validate_manifest_counts`) |
| Idempotent ingest with conflict on content drift | yes (`test_striatum_bundle_ingest_is_idempotent_and_preserves_boundary`, `test_striatum_bundle_conflicting_row_content_raises`) |
| MCP surface is exactly the four read-only tools | yes (`tool_definitions`, `test_mcp_stdio_exposes_only_rfc0044_read_only_tools`) |
| No write/admin/raw SQL exposure | yes (handler restricted to `initialize`, `tools/list`, `tools/call`, `notifications/initialized`) |
| No `import striatum` or `striatum-orchestrator` dependency | yes (`test_engram_has_no_runtime_striatum_imports`, `test_pyproject_does_not_depend_on_striatum_orchestrator`) |
| Phase 1 does not create claims or beliefs from the Striatum corpus | yes (ingester writes only `sources` and `captures`) |
| `fetch_reference` re-authorizes against stored row boundary | yes (`MemoryService.fetch_reference` rebuilds `TenantCorpus` from stored columns) |

## Open Questions

- Striatum-side augmentation guarantees (no Engram client import in
  Striatum CLI, no `memory.*` capability in Striatum daemon RPC, "Engram
  off" degradation) are claimed by RFC 0044 §8 but not exercised by any
  test that ships in this Engram repo. They need a separate check inside
  `~/git/striatum/` before final Phase 1 acceptance.
- Recommend confirming that the pre-existing `prevent_raw_evidence_mutation`
  trigger on `captures` (migration 001) treats the new `tenant_id`,
  `corpus_id`, and `bundle_id` columns as immutable post-insert (the
  migration 014 update of `prevent_segment_mutation` and friends sets the
  pattern but does not extend to the captures trigger).
- `MemoryToken.authorize_read_many` is well-tested in `MemoryService`
  unit-level paths but is not yet invoked by any Phase 1 MCP tool. When
  Phase 2 adds multi-pair retrieval, the call site should add an explicit
  test that the wired path exercises `authorize_read_many` rather than a
  loop over `authorize_read`.

verdict: accept_with_findings
