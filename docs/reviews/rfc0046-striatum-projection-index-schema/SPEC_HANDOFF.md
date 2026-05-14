# RFC 0046 Projection/Index Schema Handoff
author: operator [self-declared: roadmap-rfc-author-c]

Status: handoff
Date: 2026-05-14
RFC: RFC-0046
Run ID: run_500d0f049ea04038b0e19d6045daf918
Workflow job ID: rfc0046_projection_schema_handoff
Job ID: job_run_500d0f049ea04038b0e19d6045daf918_rfc0046_projection_schema_handoff
Session ID: sess_20b274b092054c97930649045d67d880
Lease ID: lease_a5659967b906432da08aa222867f8d7d

## Summary

RFC 0046 has been moved from scaffold to reviewable schema proposal. The revised
RFC defines Striatum projection families, common provenance/privacy columns,
generation and activation state, exact/structured/lexical/vector index
requirements, rebuild and invalidation behavior, validation fixtures,
acceptance criteria, and downstream dependencies.

The RFC remains a proposal. No code, migrations, generated schema docs, tests,
Striatum exporter changes, MCP expansion, or decision-log updates were made.

## Changed Files

- `docs/rfcs/0046-striatum-projection-index-schema.md`
- `docs/reviews/rfc0046-striatum-projection-index-schema/SPEC_HANDOFF.md`

## Context Read

Required context was read before editing:

- `AGENTS.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `STRIATUM_MEMORY_ROADMAP.md`
- `docs/schema/README.md`
- `docs/rfcs/README.md`
- `docs/process/multi-agent-review-loop.md`
- `docs/process/project-judgment.md`
- `docs/rfcs/0045-striatum-corpus-contract-v2.md`
- `docs/rfcs/0046-striatum-projection-index-schema.md`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/FINAL_SYNTHESIS.md`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/FINDINGS_LEDGER.md`

Read-only native sub-agents were used for independent context gathering across
canonical constraints, RFC 0045 dependency surface, schema/projection/index
implications, and RFC 0044 tenant-isolation review lessons. No delegated writes
were used.

## Design Decisions In The RFC

- Projection implementation targets validated RFC 0045 V2 rows only. RFC 0044 V1
  bundles remain raw-only unless a reviewed compatibility adapter supplies V2
  fields.
- Projection rows are derived caches and carry raw Engram capture IDs plus V2
  `item_id`, `logical_id`, `version_id`, hashes, timestamps, provenance,
  privacy/redaction, visibility, authority, and generation fields.
- Proposed projection families are `striatum_projection_generations`,
  `striatum_items`, `striatum_references`, `striatum_documents`,
  `striatum_runs`, `striatum_agents`, `striatum_artifacts`,
  `striatum_git_refs`, `striatum_issues`, `striatum_links`,
  `striatum_chunks`, and `striatum_chunk_embeddings`.
- Exact and structured indexes are first-class. Vector retrieval is additive,
  pgvector-local, and never the only way to resolve known identifiers.
- Projection jobs inherit Engram corpus-reader constraints: local-only,
  no-egress, no hosted models, no telemetry, no remote persistence.
- Generation activation is atomic: new derived rows become queryable only after
  validation and required local embeddings or explicit skips are complete.
- Privacy reclassification, redaction, tombstones, and rebuilds invalidate stale
  retrieval-visible rows before they can serve lower-scope reads.

## Validation Evidence

Planned docs-only validation:

```sh
git diff --check -- docs/rfcs/0046-striatum-projection-index-schema.md docs/reviews/rfc0046-striatum-projection-index-schema/SPEC_HANDOFF.md
```

No code tests, migrations, schema-doc regeneration, or live model/embedding
runs are appropriate in this documentation-only scope.

## Deferred Questions

1. Generic versus Striatum-specific projection generation table.
2. Composite foreign-key versus trigger/service enforcement for raw
   `source_capture_id` tenant/corpus consistency.
3. PostgreSQL lexical strategy: full-text, trigram, or both.
4. Per-corpus pgvector partial indexes versus shared model/dimension indexes.
5. Privacy handling for git author emails, branch names, and local paths.
6. Whether existing `projection_audits` should be extended or a Striatum-specific
   audit table should be added.
7. Whether semantic/inferred cross-links belong in RFC 0046 follow-up work or a
   separate local reviewer/auditor RFC.

RFC 0045 upstream open decisions are also named in the RFC and remain upstream
blockers for implementation if they alter required V2 fields.

## Review Recommendations

Review as an RFC/spec package, not as implemented behavior.

Recommended lanes:

- schema/migration safety;
- provenance and rebuildability;
- tenant/corpus isolation through actual service/query paths;
- local-only/no-egress and embedding boundaries;
- query ergonomics against realistic Striatum operator questions;
- fixture and RFC 0049 gate readiness.

Blocker bar for review: any schema or rule gap that could permit cross-corpus
reads, stale low-tier retrieval, irrebuildable projections, uncited answers,
silent V1 projection, or hosted-dependency drift should block promotion.
