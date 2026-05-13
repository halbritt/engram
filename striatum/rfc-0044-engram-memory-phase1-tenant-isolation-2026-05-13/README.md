# RFC 0044 Engram Memory Phase 1 Tenant Isolation Queue

Status: queued scaffold only
Date: 2026-05-13

This packet queues future Engram-side work for Striatum RFC 0044. It does not
start a Striatum run, implement the ingester, implement the MCP server, or
review the design. The current operator pass only records the future workflow
shape and the source constraints future implementors must read.

## Source Docs

Future agents must read these external Striatum docs before touching Engram
implementation files:

- `/home/halbritt/git/striatum/ENGRAM_DEVELOPER_REQUEST.md`
- `/home/halbritt/git/striatum/docs/rfcs/0044-engram-phase-1-implementation-spec.md`

Future agents must also read the normal Engram canonical docs listed in
`workflow.json`, especially `HUMAN_REQUIREMENTS.md`, `DECISION_LOG.md`,
`BUILD_PHASES.md`, `SPEC.md`, and `docs/schema/README.md`.

## Queue Scope

The queued workflow has four dependency bands:

1. A tenant terminology and RFC-amendment handoff must be produced first.
2. Engram Phase 1 implementation may start only after that handoff exists and
   has been read.
3. Capability-boundary tests and independent implementation reviews run only
   after implementation.
4. Final synthesis runs only after the independent reviews and findings ledger.

The implementation prompt asks future implementors to use the maximum useful
number of native sub-agents internally, with disjoint file ownership where the
runtime supports it.

## Future Implementation Scope

Future implementation may add the Engram-side Phase 1 adapter only:

- tenant/app isolation and corpus separation for local application memories;
- Striatum bundle ingestion from disk, with manifest validation and preserved
  provenance;
- read-only MCP stdio serving for Striatum-memory retrieval;
- Engram-local memory capabilities and tests proving personal memory is not
  exposed by default;
- docs and changelog updates required by the implementation.

The tenant vocabulary is local isolation under the same machine owner and root
authority. It is not hosted multi-tenancy. `tenant_id` separates application
memory systems such as `personal`, `striatum`, and future local apps.
`corpus_id` separates workloads or datasets inside a tenant.

## Non-Goals

This packet does not authorize:

- cloud APIs, telemetry, hosted persistence, remote sync, or hosted retrieval;
- default exposure of the personal-life corpus to Striatum operator sessions;
- Striatum runtime dependency on Engram;
- write-side dogfood-to-claim flow;
- claim or belief creation from the Striatum corpus in Phase 1;
- replacing Striatum artifacts, git history, or `.striatum/` state as
  authority.
