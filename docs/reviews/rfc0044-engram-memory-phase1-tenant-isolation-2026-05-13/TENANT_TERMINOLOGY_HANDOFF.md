# RFC 0044 Tenant Terminology Handoff
author: operator [self-declared: rfc0044-tenant-terminology]

Status: queued
Date: 2026-05-13
External Striatum RFC: 0044
Decision refs: D001, D002, D020

## Terminology

RFC 0044's isolation vocabulary is local isolation under the same machine owner
and root authority. It is not hosted multi-tenancy, cloud tenancy, remote
persistence, telemetry, or a permission model for a service outside the
operator's machine.

Use the terms this way:

| Term | Required meaning |
|---|---|
| `source_kind` | Ingest/parser discriminator. RFC 0044 adds `source_kind='striatum'`; it does not overload `capture` or `future`. |
| `tenant_id` | Application-memory-system boundary on the local Engram instance. It separates `personal`, `striatum`, and future local application memories. |
| `corpus_id` | Workload or dataset boundary inside one `tenant_id`. It does not replace `tenant_id`. |
| `tenant_id='personal'` | Existing Engram personal-life memory. Existing rows backfill here. |
| `tenant_id='striatum'` | First non-personal local application-memory system. It is for Striatum operator memory only. |
| `corpus_id='personal'` | Default corpus inside the personal tenant. |
| `corpus_id='striatum'` | First Striatum workload/dataset inside the Striatum tenant. |
| `memory.read_striatum` | Engram-local capability to read `tenant_id='striatum'` and explicitly allowed Striatum corpora. It is not a Striatum daemon capability. |
| `memory.read_personal` | Engram-local capability required for `tenant_id='personal'`. It is never granted to the default Striatum operator token. |
| `memory.read_cross_tenant` | Engram-local capability required to query more than one tenant or any tenant outside the token's fixed tenant scope. |
| `memory.read_cross_corpus` | Engram-local capability required to query more than one corpus inside an allowed tenant. |

The authorization and query boundary is always the pair
`(tenant_id, corpus_id)`, with capability checks layered on top. A
`corpus_id` value is not globally meaningful without its tenant.

Future local application-memory systems must get their own `tenant_id` values
instead of being squeezed into `tenant_id='striatum'` or
`tenant_id='personal'`. They may have one or more `corpus_id` values inside
that tenant. Striatum is the first validation tenant/corpus, not the only
future local application memory.

## Required RFC Amendment Notes

RFC 0044 mostly carries the corrected terminology. The following wording should
be tightened before implementation prompts quote it as executable contract:

- Goals, "Provide read-only retrieval..." currently says the default token can
  search and fetch only `tenant_id='striatum'` and allowed `corpus_id` rows.
  Tighten to rows matching `tenant_id='striatum'` and an explicitly allowed
  Striatum `corpus_id`.
- Non-Goals, "Personal-life retrieval by default" currently leads with access
  to `corpus_id='personal'`. Rewrite as access to the personal boundary
  `tenant_id='personal', corpus_id='personal'` so implementers do not treat
  `corpus_id` as the primary isolation key.
- Capability Boundary table and Retrieval acceptance criteria describe
  `memory.read_striatum` as reading `tenant_id='striatum'` and allowed Striatum
  `corpus_id` values. Keep the `tenant_id='striatum'` predicate explicit in
  every implementation-facing copy of that rule.
- Any CLI or MCP shorthand such as `corpus="striatum"` or
  `describe-corpus striatum` is only a convenience default for
  `tenant_id='striatum', corpus_id='striatum'`. Handlers, tests, reference IDs,
  search results, and fetch authorization must store and check both fields.
- The older Engram developer request is superseded where it asks only for
  `corpus_id` separation or MCP arguments keyed only by `corpus`. Future agents
  must implement from RFC 0044 plus this handoff, not from the older
  corpus-only phrasing.

Implementation should treat any future sentence that says "allowed corpus" or
"the Striatum corpus" as shorthand only after resolving it to the explicit
tenant/corpus pair.

## Implementation Preconditions

Future implementation agents must read these before coding:

- This handoff.
- `/home/halbritt/git/striatum/ENGRAM_DEVELOPER_REQUEST.md`, only as the
  operator brief; use RFC 0044 and this handoff where terminology differs.
- `/home/halbritt/git/striatum/docs/rfcs/0044-engram-phase-1-implementation-spec.md`,
  especially Engram Local Isolation Model, Engram Ingestion, Engram MCP Stdio
  Server, Capability Boundary, Acceptance Criteria, Open Questions, and Domain
  Modeling.
- Engram canonical docs listed in `AGENTS.md`: `README.md`,
  `HUMAN_REQUIREMENTS.md`, `DECISION_LOG.md`, `BUILD_PHASES.md`, `ROADMAP.md`,
  `SPEC.md`, and `docs/schema/README.md`.
- `docs/rfcs/0012-python-agentic-coding-standard.md` before Python changes.
- `docs/process/multi-agent-review-loop.md` and
  `docs/process/project-judgment.md` before review or synthesis work.

Implementation requirements to preserve:

- D001: the long-term product surface remains `context_for(conversation)`;
  RFC 0044's MCP tools are a Phase 1 read-only retrieval surface, not a
  replacement for Engram's product model.
- D002: immutable raw evidence, then claims, then beliefs. Striatum Phase 1
  must not create claims or beliefs from Striatum artifacts.
- D020: any corpus-reading Engram process has no outbound network egress and
  binds local serving surfaces to loopback/stdio only.
- Existing personal rows backfill to `tenant_id='personal'` and
  `corpus_id='personal'`; Striatum ingest writes `tenant_id='striatum'` and
  `corpus_id='striatum'`.
- The Striatum ingester must not accept an operator-supplied tenant override in
  Phase 1.
- Every search result and fetchable reference must carry enough data to recheck
  `tenant_id`, `corpus_id`, `source_kind`, `sub_kind`, privacy tier, external
  id, and provenance.
- `engram.fetch_reference` must re-authorize against the referenced row's
  stored `tenant_id` and `corpus_id`; opaque reference IDs are not authority.
- Capability checks must prove default Striatum operator access cannot read
  `tenant_id='personal'`, an unknown future tenant, or a second corpus inside
  `tenant_id='striatum'` without explicit Engram-local grants.
- Engram remains augmentation-only for Striatum: no `import striatum`, no
  `striatum-orchestrator` dependency, no Striatum mutation calls, and no writes
  into a target repository's `.striatum/` directory.
- Check the live migration sequence and generated schema docs before choosing
  a migration filename; do not assume RFC 0044's example prefix is still next.

## Non-Goals Preserved

- No cloud dependency, telemetry, hosted retrieval, remote service mode,
  external persistence, or cross-machine sync.
- No default exposure of personal-life memory to Striatum operator sessions.
- No cross-tenant or cross-corpus retrieval without explicit Engram-local
  capability and explicit requested boundaries.
- No write-side dogfood-to-claim flow in Phase 1.
- No claims or beliefs created from the Striatum corpus in Phase 1.
- No raw SQL MCP tool, mutation passthrough, `memory.write`, or admin indexing
  capability through MCP.
- No replacement of Striatum's `.striatum/state.sqlite3`, daemon DB, RFCs,
  decision log, operator reports, run summaries, audit chain, or git history as
  authoritative state.
- No broad redesign of Engram's raw evidence, segmentation, claims, beliefs,
  `predicate_vocabulary`, or `context_for(conversation)` model.
