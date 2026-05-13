# Implement RFC 0044 Engram Phase 1 Tenant-Aware Memory Integration

Read first:

- `/home/halbritt/git/striatum/ENGRAM_DEVELOPER_REQUEST.md`
- `/home/halbritt/git/striatum/docs/rfcs/0044-engram-phase-1-implementation-spec.md`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/TENANT_TERMINOLOGY_HANDOFF.md`
- Engram canonical docs listed in the workflow context.

Use the maximum useful number of native sub-agents internally if your runtime
supports them. Suggested internal lanes: schema/migration, bundle ingestion,
MCP stdio/capabilities, tests, and docs. Keep file ownership disjoint and do
not revert unrelated dirty work.

Implement only Engram-side Phase 1:

- tenant/app isolation with `tenant_id`, where tenants are local application
  memory systems under the same machine owner and root authority;
- corpus separation with `corpus_id`, where `personal` remains isolated and
  `striatum` is the first application corpus;
- Striatum bundle ingestion from disk, including manifest validation,
  idempotence, bundle/repo identity, sub-kind handling, and preserved
  provenance;
- read-only MCP stdio serving with exactly the Phase 1 tools:
  `engram.search`, `engram.fetch_reference`, `engram.describe_corpus`, and
  `engram.health`;
- Engram-local capability checks for `memory.read_striatum`,
  `memory.describe`, `memory.read_personal`, and `memory.read_cross_corpus`;
- tests proving capability boundaries, tenant/corpus isolation, manifest
  validation, idempotence, no Striatum import/dependency, no cloud/no
  telemetry/no hosted persistence, and no default personal-memory exposure.

Required constraints:

- Do not call Striatum from Engram at runtime. Read exported bundle files only.
- Do not add Striatum as a Python dependency.
- Do not expose raw SQL, write tools, claim creation, belief revision, or
  indexing/admin operations through MCP.
- Do not create claims or beliefs from the Striatum corpus in Phase 1.
- Preserve Engram's no-cloud and no-network-egress posture for corpus-reading
  processes.

Required output:

- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/IMPLEMENTATION_HANDOFF.md`

Use this artifact shape:

```md
# RFC 0044 Engram Phase 1 Implementation Handoff
author: <packet author line>

Status: implemented
Date: 2026-05-13
External Striatum RFC: 0044
Decision refs: D001, D002, D020

## Summary

## Files Changed

## Tenant And Corpus Boundaries

## Bundle Manifest And Provenance Handling

## MCP And Capability Boundary

## Tests / Validation Run

## Residual Risk
```
