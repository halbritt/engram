# RFC 0044 Capability Boundary Test Evidence

Read the implementation handoff and run focused checks only. Do not broaden
into unbounded corpus execution or hosted service behavior.

Verify:

- tenant/app isolation and corpus separation;
- Striatum bundle manifest validation and idempotence;
- provenance fields for source path, hash, commit, RFC, decision, run, and
  audit metadata where applicable;
- read-only MCP stdio tools only;
- default Striatum token cannot read `tenant_id='personal'` or
  `corpus_id='personal'`;
- cross-tenant and cross-corpus retrieval requires explicit Engram-local
  capabilities;
- no cloud, telemetry, hosted persistence, or Striatum runtime dependency.

Required output:

- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/CAPABILITY_BOUNDARY_EVIDENCE.md`

Use aggregate test evidence. Do not commit private corpus content.
