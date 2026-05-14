# Striatum Memory Roadmap RFC Queue

Status: queued scaffold only
Date: 2026-05-14

This packet queues the RFC work named by `STRIATUM_MEMORY_ROADMAP.md`. It does
not implement Engram code, implement Striatum exporter code, settle design
choices, or start a Striatum run.

The operator-created RFC shells are:

- `docs/rfcs/0045-striatum-corpus-contract-v2.md`
- `docs/rfcs/0046-striatum-projection-index-schema.md`
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md`
- `docs/rfcs/0048-striatum-context-injection-policy.md`
- `docs/rfcs/0049-striatum-evaluation-gates.md`

The workflow packet records the dependency order for future authoring,
implementation, and review work:

1. RFC 0044 hardening cleanup can proceed immediately.
2. RFC 0045 is the first new design dependency.
3. RFC 0046 and RFC 0047 can begin after RFC 0045 is concrete enough.
4. RFC 0048 depends on the retrieval boundary from RFC 0047.
5. RFC 0049 depends on the contract, projection, retrieval, and context policy
   RFCs.

Future implementor agents should use the maximum useful number of native
sub-agents internally, with disjoint ownership and explicit handoff artifacts.

## Guardrails

- Preserve local-only operation: no cloud dependency, telemetry, hosted
  persistence, or outbound network requirement.
- Preserve raw evidence immutability and rebuildable derived projections.
- Treat Striatum as the near-term application-memory use case while personal
  memory work remains deferred.
- Keep Striatum independent of Engram at runtime; Engram may augment Striatum
  context but must not become a required workflow dependency.
- Keep personal memory outside the default Striatum operator capability set.
