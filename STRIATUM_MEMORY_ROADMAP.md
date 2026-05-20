# Striatum Memory Roadmap

Last updated: 2026-05-17

Execution note: this roadmap is historical orientation. The active execution
plan is [`STRIATUM_MEMORY_E2E_BACKLOG.md`](STRIATUM_MEMORY_E2E_BACKLOG.md).
As of 2026-05-17, the working Striatum path has advanced beyond the baseline
below: Layers 1-5 landed, `make e2e-striatum` passes, RFC 0046-RFC 0049 are
accepted as design reference by D083, default Striatum operator-token
authorization is recorded by D085, and the architecture follow-up A0-A9 slice
adds unified retrieval hits, non-capture `fetch_reference`, `context_for`, MCP
serving, context snapshots/feedback, no-egress probes, and central policy
checks, generic exact-reference indexing, and local-only MCP entity grounding.
Generated products remain deferred until a downstream generated-product spec is
accepted. Remote grounding fetches and full entity review UI remain gated.

## Purpose

Engram should become the local memory system for Striatum instances while
preserving Engram's core constraints:

- no cloud dependency;
- no user data leaving the machine unless explicitly requested;
- immutable raw evidence;
- rebuildable derived projections;
- provenance, confidence, stability class, and auditability for every answer.

The target state is that a Striatum instance can retrieve relevant memory from
operator logs, workflow-agent logs, designs, RFCs, reviews, operator reports,
changelogs, git history, issues, blockers, and generated artifacts.

The guiding distinction is:

- ingest everything;
- index everything;
- inject only task-relevant slices into agent context.

Striatum context should not become a giant transcript dump. It should become a
retrieval-backed working memory with citations back to raw evidence.

## Current Baseline

RFC 0044 established the first Engram-side boundary for Striatum memory:

- Striatum memory lives under the local application-memory boundary
  `tenant_id='striatum'`.
- The current default corpus is `corpus_id='striatum'`.
- Engram ingests disk bundles produced outside Engram.
- Engram does not import Striatum or call Striatum commands at runtime.
- The current MCP surface is read-only:
  - `engram.search`;
  - `engram.fetch_reference`;
  - `engram.describe_corpus`;
  - `engram.health`.
- The default Striatum operator token can read Striatum memory and describe
  corpora, but it cannot read personal memory.

This was sufficient for Phase 1 raw retrieval. The current implementation also
has Striatum projections, exact-reference retrieval, packet building/audits,
MCP smoke coverage, and the narrow `context_for` serving path. See the active
backlog for current sequencing and gates.

## Target Memory Coverage

A complete Striatum corpus should include the following local evidence:

- operator-agent logs;
- workflow-agent logs;
- agent prompts, packets, stdout/stderr summaries, outputs, reviews,
  syntheses, and handoffs;
- RFCs, designs, design reviews, implementation notes, and final decisions;
- `OPERATOR_REPORT.md`, `CHANGELOG.md`, decision logs, backlog documents, and
  other operator-maintained status artifacts;
- git commits, branches, tags, diffs, merge history, and relevant working-tree
  state snapshots;
- GitHub issues, blockers, checkpoint state, workflow state, and recovery
  attempts;
- generated artifacts and artifact manifests;
- run and process metadata, including process IDs, lanes, agent roles, status,
  timestamps, dependencies, and verdicts.

Each memory item should carry stable IDs, source kind, timestamps, file path or
logical path, commit SHA when applicable, content hash, provenance, visibility
metadata, and redaction/privacy tier.

## Roadmap

RFC 0045-RFC 0049 now exist as proposal and review provenance. They do not
authorize implementation, default-on Striatum memory, runtime changes, or a
binding architecture contract without a separate recorded project decision or
accepted spec handoff.

### Phase 0: Harden RFC 0044

Finish the known RFC 0044 follow-ups before any projection, retrieval, or
operator-context implementation depends on the RFC 0044 substrate:

- run a local smoke test against a real or committed fixture Striatum export
  bundle;
- make MCP authorization, not-found, and invalid-reference failures uniform;
- add MCP content-length limits and JSON-RPC parse-error responses;
- structurally prevent Striatum source kinds from landing outside the Striatum
  corpus;
- add matching `fetch_reference()` source-kind and tenant/corpus guards;
- validate `--capability` values;
- report schema versions by numeric migration prefix or applied ordering;
- add an optional no-egress sandbox probe;
- record the reciprocal Striatum-side boundary: Striatum may use Engram for
  augmentation, but it must not depend on Engram to run.

### Phase 1: Define The Striatum Corpus Contract V2

Create a durable export contract owned by Striatum and consumed by Engram.

The contract should define:

- bundle manifest shape;
- source kinds;
- required and optional metadata;
- stable item IDs;
- content hashes;
- instance and repository identity;
- privacy/redaction metadata;
- incremental-export watermarks;
- validation rules;
- backward compatibility expectations.

The current single `corpus_id='striatum'` is adequate for Phase 1. The next
contract should support per-instance corpora, for example:

```text
tenant_id = striatum
corpus_id = striatum:<repo-or-instance-id>
```

This lets one machine host multiple local application memories without mixing
separate Striatum projects.

### Phase 2: Implement Full Striatum Export

Striatum should emit the bundle. Engram should continue to read the bundle from
disk without importing Striatum or invoking Striatum commands at runtime.

The exporter should support:

- full export;
- incremental export;
- deterministic manifests;
- validation mode;
- local-only operation;
- graceful omission of unavailable optional sources;
- explicit redaction/privacy tiers;
- stable references from exported records back to source files, runs, commits,
  issues, and artifacts.

### Phase 3: Add Engram Striatum Projections

Raw captures stay append-only. Derived tables and projections remain
rebuildable.

Add Striatum-aware projections for:

- runs;
- workflows;
- agents;
- artifacts;
- RFCs, designs, reviews, and syntheses;
- commits and diffs;
- issues and blockers;
- reports and changelogs;
- cross-links among all of the above.

This enables structured queries such as "show prior failed RFC 0044 repair
attempts touching MCP authorization" without depending only on free-text search.

### Phase 4: Build Layered Retrieval

Retrieval should combine:

- lexical search for exact identifiers, file paths, issue IDs, artifact IDs,
  run IDs, and commit SHAs;
- vector search for semantic recall over logs, markdown, reviews, and design
  artifacts;
- structured filters for repository, corpus, workflow, agent role, source kind,
  timestamp, commit, RFC, issue, and artifact type;
- source-specific chunking for logs, diffs, markdown, reports, and changelogs;
- recency and authority weighting;
- provenance-preserving result references.

Canonical current docs should outrank old brainstorms. Accepted syntheses should
outrank draft reviews. Raw logs should remain citeable evidence.

### Phase 5: Integrate With Striatum Context

Striatum should use Engram as a read-only augmentation source in these
workflows:

- operator startup summaries;
- workflow scaffolding;
- agent-packet preparation;
- review-cycle preparation;
- blocker and recovery investigation;
- UI and CLI memory search;
- "related prior work" retrieval for RFCs, designs, commits, and issue trails.

If Engram is unavailable, Striatum must degrade gracefully and continue running.
Engram should augment Striatum context, not become a runtime dependency.

### Phase 6: Produce Derived Memory Products

After raw ingestion, projections, retrieval, and the generic evidence/reference
index are reliable, add generated memory products:

- known-friction ledger;
- prior-decisions index;
- reusable implementation-pattern index;
- open-blocker and stale-risk summary;
- agent-performance notes;
- project-trajectory summary;
- RFC lineage map.

These products are derived artifacts. They must cite raw evidence and must not
replace the evidence they summarize. D089 keeps them retrieval-invisible until
a downstream generated-product specification is accepted.

### Phase 7: Add Evaluation Gates

Before routine operator use, add gates for:

- real Striatum bundle smoke testing;
- golden queries with expected references;
- tenant and corpus isolation;
- no-egress behavior;
- retrieval quality;
- stale-index detection;
- operator-startup latency;
- agent-packet augmentation latency.

## Execution Backlog

Historical recommended follow-up order:

1. RFC alignment cleanup for the RFC 0047, RFC 0046, RFC 0048, and RFC 0049
   follow-up findings carried by the final synthesis.
2. RFC 0044 hardening and EG-000 evidence before projection, retrieval, or
   operator-context implementation depends on the current Phase 1 substrate.
3. A separate recorded project decision or accepted spec handoff before
   implementation treats RFC 0045-RFC 0049 as binding contracts.
4. Striatum exporter implementation lanes.
5. Engram ingestion and projection implementation lanes.
6. Striatum UI, CLI, and operator-context integration lanes.
7. Multi-lane review with an added ergonomics/context-quality review.

## Open Decisions

These decisions should be made before implementation proceeds beyond the export
contract:

- how Striatum instance identity is represented;
- whether `corpus_id` names should be human-readable, UUID-based, or both;
- which log streams are mandatory versus optional;
- how much git diff content is exported by default;
- what redaction tiers Striatum can guarantee before export;
- where incremental-export watermarks are stored;
- how Striatum records Engram availability without creating a runtime
  dependency;
- how much retrieved memory may be injected into each agent packet by default.

## Immediate Next Step

Use [`STRIATUM_MEMORY_E2E_BACKLOG.md`](STRIATUM_MEMORY_E2E_BACKLOG.md) for
execution. The next Striatum-memory work is incremental hardening and operator
documentation: keep the real-bundle runbook current, complete remaining Layer 4
hardening gates only where still valuable, defer vector retrieval, keep
generated products behind the downstream spec required by D089, and choose any
RFC 0050 Stage 3+ source family from real `context_for` eval failures.
