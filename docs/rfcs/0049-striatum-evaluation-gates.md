<a id="rfc-0049"></a>

# RFC 0049: Striatum Evaluation, No-Egress, And Retrieval-Quality Gates

| Field | Value |
|-------|-------|
| RFC | RFC-0049 |
| Title | Striatum Evaluation, No-Egress, And Retrieval-Quality Gates |
| Status | proposal |
| Implementation | none |
| Created | 2026-05-14 |
| Source | `STRIATUM_MEMORY_ROADMAP.md` |
| Context | RFC 0044, RFC 0045, RFC 0046, RFC 0047, RFC 0048 |

## Summary

This RFC is the scaffold for the gates required before Engram-backed Striatum
memory becomes routine operator infrastructure. The gates should test real
bundle ingestion, tenant/corpus isolation, no-egress behavior, retrieval
quality, stale-index detection, and operator latency.

This scaffold does not define the final benchmark set or acceptance thresholds.
It queues those decisions after the contract, projections, retrieval boundary,
and context policy are specific enough to test.

## Roadmap Position

RFC 0049 closes the Striatum-first roadmap loop. It defines the evidence needed
before Engram memory is treated as reliable for Striatum operator sessions and
workflow-agent packets.

## Goals

1. Define real Striatum bundle smoke testing.
2. Define golden queries with expected references.
3. Define tenant and corpus isolation tests.
4. Define no-egress evidence requirements.
5. Define retrieval-quality, stale-index, and latency gates.
6. Define what evidence is required before routine operator use.

## Non-Goals

- No corpus contract design.
- No exporter or ingester implementation.
- No context-injection policy.
- No personal-memory evaluation gates.
- No hosted benchmark service, telemetry, or cloud dependency.

## Dependencies

- RFC 0044 hardening cleanup.
- RFC 0045 corpus contract.
- RFC 0046 projections and indexes.
- RFC 0047 retrieval augmentation boundary.
- RFC 0048 context injection policy.

## Scaffolded Workstreams

1. Define a fixture or non-private real Striatum export bundle smoke test.
2. Define golden query sets and expected reference assertions.
3. Define no-egress probe requirements and acceptable evidence forms.
4. Define isolation, stale-index, and latency gates.
5. Define evidence export and review requirements for final acceptance.

## Review Requirements

Use the multi-agent review loop before promotion:

- no-egress and local-only evidence review;
- retrieval-quality review;
- operator-latency and ergonomics review;
- isolation and regression coverage review.

## Acceptance Criteria To Define

- Real or committed fixture Striatum bundles pass end-to-end smoke tests.
- Golden queries return expected cited references and reject out-of-corpus
  reads.
- No-egress evidence is structural or explicitly scoped.
- Stale indexes are detectable.
- Operator startup and packet augmentation latency are bounded.

## Open Questions

1. Which golden queries best cover Striatum memory usefulness?
2. What latency budget is acceptable for operator startup and workflow-packet
   augmentation?
3. What is the minimum no-egress evidence before routine use?
4. How should failed gates be recorded in Striatum and Engram artifacts?
