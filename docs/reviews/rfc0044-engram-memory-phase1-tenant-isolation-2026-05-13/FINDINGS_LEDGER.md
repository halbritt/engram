# RFC 0044 Engram Memory Phase 1 Findings Ledger
author: operator [self-declared: rfc0044-findings-ledger]

Status: ledger
Date: 2026-05-14
External Striatum RFC: 0044
Scope: Deduplicates only the review and evidence inputs named in the work
packet. Later repair artifacts in this directory are not used as inputs here.

Sources:
  - REVIEW_boundary_claude.md
  - REVIEW_correctness_codex.md
  - REVIEW_operator_gemini.md
  - CAPABILITY_BOUNDARY_EVIDENCE.md

## Findings

### F001 - Single-pair serving reads bypass cross-boundary capability checks
Severity: blocking
Classification: blocking for Phase 1 acceptance
Sources: [codex F001, codex F002, boundary open questions, capability evidence]
Affects:
  - src/engram/memory.py:64
  - src/engram/memory.py:144
  - src/engram/memory.py:208
  - src/engram/mcp_stdio.py:110
  - tests/test_striatum_ingest.py
  - tests/test_mcp_stdio.py
Rationale: `MemoryToken.authorize_read()` is the wired serving-path check for
`MemoryService.search()` and `MemoryService.fetch_reference()`, but the reviewed
implementation only enforced cross-tenant and cross-corpus grants in
`authorize_read_many()`. `engram-mcp-stdio --allow-pair` could build a token
with another visible Striatum corpus or a personal pair, and the single-pair
service path could read that pair when the tenant-specific read capability was
present even without `memory.read_cross_corpus` or `memory.read_cross_tenant`.
The capability evidence covered helper-level multi-pair behavior, not the
actual service/MCP path. This violates the tenant terminology handoff's rule
that crossing the token's fixed scope requires the explicit Engram-local
cross-boundary capability.
Required resolution: make the single-pair service path enforce the token's
fixed/primary scope, and add regression tests through `MemoryService.search()`,
`MemoryService.fetch_reference()`, and at least one MCP handler path using the
same token shape that the CLI constructs.
merged_from:
  - REVIEW_correctness_codex.md F001
  - REVIEW_correctness_codex.md F002
  - CAPABILITY_BOUNDARY_EVIDENCE.md "Cross-Boundary Grants" residual coverage
  - REVIEW_boundary_claude.md open question on future `authorize_read_many`
    wiring

### F002 - `describe-corpus` CLI shorthand collapses tenant and corpus
Severity: minor
Classification: minor/nit follow-up
Sources: [claude F001]
Affects:
  - src/engram/cli.py:196
  - src/engram/cli.py:738
Rationale: `engram describe-corpus <corpus>` dispatches to
`tenant_id = args.tenant or args.corpus`, which turns the positional corpus
argument into a tenant when `--tenant` is omitted. That is harmless for the
sanctioned `striatum/striatum` convenience default, but it weakens the explicit
two-key operator model and can mask whether an operator is inspecting a tenant
or a corpus. The MCP stdio surface keeps `--tenant` and `--corpus` independent.
Phase 1 block: no.
Recommended resolution: either require `--tenant` outside the `striatum`
convenience case, or special-case only positional `striatum` as
`tenant_id='striatum', corpus_id='striatum'`.
merged_from:
  - REVIEW_boundary_claude.md F001

### F003 - MCP/reference errors expose weak existence and authorization distinctions
Severity: minor
Classification: minor/nit follow-up
Sources: [claude F002]
Affects:
  - src/engram/memory.py:55
  - src/engram/memory.py:181
  - src/engram/mcp_stdio.py:160
Rationale: Tool-call errors distinguish visible-but-not-readable,
not-visible, missing capability, malformed reference, and reference-not-found
cases. No content crosses the boundary, but a probing MCP client can learn weak
metadata such as whether a reference id resolves to a row outside its access
scope. In Phase 1 the operator owns both ends of the local stdio session, so
this is defense-in-depth rather than a blocker.
Phase 1 block: no.
Recommended resolution: collapse unauthorized and not-found reference failures
to a uniform message at the MCP boundary.
merged_from:
  - REVIEW_boundary_claude.md F002

### F004 - Striatum tenant/source-kind consistency is not structurally enforced
Severity: minor
Classification: minor/nit follow-up
Sources: [claude F003, claude F004]
Affects:
  - migrations/014_striatum_tenant_corpus.sql:5
  - migrations/014_striatum_tenant_corpus.sql:103
  - src/engram/memory.py:181
Rationale: Migration 014 adds tenant/corpus columns and Striatum indexes, but
does not add a database check tying `tenant_id='striatum'` to
`source_kind='striatum'`, nor the inverse. `fetch_reference()` re-authorizes
against the stored tenant/corpus pair but does not reject inconsistent
`source_kind` values. The current ingester writes the expected
`striatum/striatum/source_kind='striatum'` shape and search filters
`source_kind='striatum'`, so the reviewed implementation has no known Phase 1
miswrite path. The hardening value is structural drift prevention.
Phase 1 block: no.
Recommended resolution: add database checks or equivalent guardrails tying the
Striatum tenant to Striatum source rows, and have `fetch_reference()` validate
tenant/source-kind consistency before returning content.
merged_from:
  - REVIEW_boundary_claude.md F003
  - REVIEW_boundary_claude.md F004

### F005 - `engram-mcp-stdio --capability` accepts arbitrary strings
Severity: nit
Classification: minor/nit follow-up
Sources: [claude F005]
Affects:
  - src/engram/mcp_stdio.py:108
  - src/engram/mcp_stdio.py:234
Rationale: The MCP stdio CLI appends arbitrary `--capability` strings to the
token. A typo does not over-grant, because unknown strings satisfy no checks,
but it can make an operator believe access was granted when it was not.
Phase 1 block: no.
Recommended resolution: warn on or reject capabilities outside the known
`memory.*` set.
merged_from:
  - REVIEW_boundary_claude.md F005

### F006 - MCP stdio frame reader has no size cap or parse-error response path
Severity: nit
Classification: minor/nit follow-up
Sources: [claude F006]
Affects:
  - src/engram/mcp_stdio.py:185
  - src/engram/mcp_stdio.py:207
Rationale: `read_message()` trusts `Content-Length` and raises on malformed
headers or invalid JSON, which can terminate the local stdio process. The
blast radius is one operator-controlled MCP session, but a bounded read and
JSON-RPC parse-error response would be more robust.
Phase 1 block: no.
Recommended resolution: cap `Content-Length` and translate framing/JSON parse
failures into JSON-RPC parse errors where possible.
merged_from:
  - REVIEW_boundary_claude.md F006

### F007 - Striatum-side augmentation-not-dependency checks are outside this evidence set
Severity: major
Classification: major but follow-up acceptable
Sources: [claude F007, capability evidence]
Affects:
  - tests/test_augmentation_boundary.py
  - external Striatum repository checks, outside this work packet
Rationale: The Engram-side tests verify no `import striatum` and no
`striatum-orchestrator` dependency in this repository. RFC 0044 also requires
the reciprocal Striatum-side guarantees: no Striatum CLI module imports an
Engram client library, no Striatum daemon RPC method references Engram, and
Engram unavailability degrades gracefully. Those checks cannot be completed
from this Engram-only review packet.
Phase 1 block: no for Engram-side Phase 1 acceptance; yes before claiming the
full cross-repo RFC 0044 augmentation contract is independently verified.
Recommended resolution: run a separate Striatum-repo review/test artifact for
the reciprocal augmentation boundary.
merged_from:
  - REVIEW_boundary_claude.md F007

### F008 - `health()` reports schema version with lexicographic migration order
Severity: nit
Classification: minor/nit follow-up
Sources: [claude F008]
Affects:
  - src/engram/memory.py:295
Rationale: `health()` reports the maximum migration filename as
`schema_version`. This is stable under the current zero-padded migration
convention, but it will misorder a future non-zero-padded filename.
Phase 1 block: no.
Recommended resolution: order by numeric prefix or `applied_at` instead of
lexicographic filename max.
merged_from:
  - REVIEW_boundary_claude.md F008

### F009 - Malformed decoded reference UUIDs can bypass reference-error wrapping
Severity: nit
Classification: minor/nit follow-up
Sources: [claude F009]
Affects:
  - src/engram/memory.py:181
  - src/engram/memory.py:399
Rationale: `decode_reference_id()` wraps base64 and JSON shape failures, but a
decoded `id` that is syntactically a string and not a UUID can reach the
Postgres `WHERE id = %s` query and raise a database UUID-cast error outside the
`MemoryReferenceError` path. That can surface as an unhandled MCP tool-call
exception instead of a clean reference error.
Phase 1 block: no.
Recommended resolution: validate decoded row ids as UUIDs before querying, or
catch and rewrap the relevant Postgres UUID error.
merged_from:
  - REVIEW_boundary_claude.md F009

### F010 - No OS-level no-egress sandbox was exercised in this evidence pass
Severity: minor
Classification: minor/nit follow-up
Sources: [capability evidence residual notes]
Affects:
  - CAPABILITY_BOUNDARY_EVIDENCE.md
  - D020 no-egress acceptance evidence
Rationale: The evidence pass inspected the RFC 0044 runtime surface and found
no HTTP client, socket, hosted API, telemetry, cloud, or remote-persistence
code. It did not run the code under an OS-level no-egress sandbox. This does
not contradict the local-only code evidence, but it should limit the claim to
code/test inspection rather than structural D020 enforcement.
Phase 1 block: no.
Recommended resolution: if final acceptance needs D020 structural evidence,
record a sandboxed execution probe or explicitly scope the RFC 0044 Phase 1
evidence to no-egress-by-code-inspection.
merged_from:
  - CAPABILITY_BOUNDARY_EVIDENCE.md residual notes

### F011 - Capability and manifest evidence is synthetic, not a real-bundle smoke
Severity: minor
Classification: minor/nit follow-up
Sources: [capability evidence residual notes, gemini review]
Affects:
  - CAPABILITY_BOUNDARY_EVIDENCE.md
  - tests/test_striatum_ingest.py
Rationale: The reviewed tests and manual probe used synthetic bundle rows. That
is appropriate for deterministic unit and boundary tests and was enough for the
operator review to accept manifest/provenance handling, but it is not evidence
that a real Striatum export bundle has been smoke-tested end to end.
Phase 1 block: no.
Recommended resolution: add a separate local smoke artifact against a
non-private or fixture Striatum export bundle before relying on RFC 0044 for
routine operator workflows.
merged_from:
  - CAPABILITY_BOUNDARY_EVIDENCE.md residual notes
  - REVIEW_operator_gemini.md bundle manifest/provenance acceptance context

## Rejected Or Not Carried

### R001 - Captures trigger may not make new tenant/corpus/bundle columns immutable
Disposition: rejected as a finding
Sources: [boundary open questions]
Rationale: Inspection shows `migrations/001_raw_evidence.sql` defines
`captures_immutable` as a `BEFORE UPDATE OR DELETE ON captures` trigger
executing `prevent_raw_evidence_mutation()`. Because the trigger rejects any
update to the row, columns added later by migration 014 are covered without a
trigger change.

### R002 - "No critical issues found" from the operator review
Disposition: not carried as an acceptance conclusion
Sources: [gemini review]
Rationale: The operator review found no issues in its manifest/provenance,
ergonomics, and augmentation-not-dependency scope, but the correctness review
identified the serving-path capability bypass in F001. The ledger therefore
preserves the positive operator review as evidence for non-blocking areas but
does not carry its overall "no critical issues" conclusion.

### R003 - Full MCP subprocess coverage is required for every Phase 1 capability test
Disposition: rejected as a blanket requirement
Sources: [capability evidence residual notes, codex F002]
Rationale: Unit-level `MemoryService` tests are sufficient for many boundary
rules. The rejected part is the blanket requirement that every capability rule
must be re-tested through a subprocess. F001 still requires at least one MCP
handler or framed-path regression because the bug involved the CLI-constructed
token shape and the wired service path, not just token helper semantics.

## Acceptance Blocker Summary

- Blocking findings: 1
- Major follow-up findings: 1
- Minor findings: 5
- Nit findings: 4
- Rejected/not-carried items: 3

Phase 1 acceptance is blocked by F001 until the single-pair service/MCP read
paths require `memory.read_cross_corpus` for secondary corpora and
`memory.read_cross_tenant` for non-primary tenants, with regressions that
exercise the serving path rather than only `authorize_read_many()`.
