<a id="rfc-0045"></a>

# RFC 0045: Striatum Corpus Contract V2

| Field | Value |
|-------|-------|
| RFC | RFC-0045 |
| Title | Striatum Corpus Contract V2 |
| Status | proposal |
| Implementation | none |
| Created | 2026-05-14 |
| Source | `STRIATUM_MEMORY_ROADMAP.md` |
| Context | RFC 0044, `STRIATUM_MEMORY_ROADMAP.md`, `SPEC.md`, `docs/schema/README.md` |

## Summary

This RFC is the scaffold for the next Striatum memory contract. It should turn
the current RFC 0044 Phase 1 bundle into a durable V2 corpus contract owned by
Striatum and consumed by Engram.

This is a proposal scaffold only. It records the work boundary, dependencies,
review expectations, and open questions. It does not settle the bundle schema,
implement an exporter, implement an ingester, or authorize runtime coupling
between Striatum and Engram.

## Roadmap Position

RFC 0045 is the dependency for the rest of the Striatum-first Engram roadmap.
The contract should be clear enough that later RFCs can target projection
schema, retrieval augmentation, context injection, and evaluation gates without
reopening the export format on every pass.

## Goals

1. Define the V2 bundle manifest shape.
2. Define the source-kind and sub-kind vocabulary Striatum exports.
3. Define required and optional metadata for every exported item.
4. Define stable item IDs, content hashes, instance identity, repository
   identity, timestamps, privacy metadata, and redaction tiers.
5. Define incremental export watermarks and compatibility expectations.
6. Preserve Engram's local-only posture and immutable raw-evidence boundary.

## Non-Goals

- No Engram ingestion implementation.
- No Striatum exporter implementation.
- No context-injection policy.
- No derived projections or index schema beyond fields required by the export
  contract.
- No hosted service, cloud sync, telemetry, or remote persistence.
- No personal-memory corpus exposure to Striatum by default.

## Dependencies

- RFC 0044 Engram Phase 1 acceptance with findings.
- RFC 0044 hardening cleanup, especially real-bundle smoke coverage and
  structural tenant/source-kind checks.
- The Striatum-side reciprocal boundary artifact that proves Striatum degrades
  gracefully when Engram is unavailable.

## Scaffolded Workstreams

1. Inventory the current RFC 0044 V1 bundle fields and known review findings.
2. Draft the V2 manifest, item, and validation vocabulary.
3. Define instance and corpus identity rules for multiple Striatum instances on
   one local Engram installation.
4. Define backwards-compatibility and migration expectations.
5. Produce a contract review packet before implementation starts.

## Review Requirements

Use the multi-agent review loop before promotion:

- local-first/privacy boundary review;
- corpus contract coherence review;
- Striatum operator ergonomics review;
- implementation-readiness review for both repositories.

## Acceptance Criteria To Define

- A V2 fixture bundle can be validated without live network or model calls.
- The contract names required and optional source streams.
- The contract names stable identity rules for `tenant_id`, `corpus_id`,
  instance identity, repository identity, and exported item IDs.
- The contract defines redaction/privacy metadata without requiring cloud
  services.
- The contract states how older V1 bundles are handled or rejected.

## Open Questions

1. Should `corpus_id` be human-readable, UUID-based, or both?
2. Which Striatum log streams are mandatory for a valid V2 bundle?
3. Where should incremental-export watermarks live?
4. How much git diff content belongs in the default export?
5. Which redaction tiers can Striatum guarantee before export?
