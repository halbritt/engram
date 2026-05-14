# Author Striatum Memory Roadmap RFC Work

Read `SOURCES.md`, the assigned RFC, `STRIATUM_MEMORY_ROADMAP.md`, RFC 0044
final synthesis, and the RFC 0044 findings ledger before editing.

You are not alone in the codebase. Do not revert unrelated dirty work. Use the
maximum useful number of native sub-agents internally if your runtime supports
them, with disjoint write scopes and explicit handoffs.

Your job is to move only the assigned RFC or hardening lane from scaffold to a
reviewable handoff. Preserve the constraints:

- local-only operation;
- no telemetry, cloud API, hosted persistence, or outbound-network dependency;
- immutable raw evidence;
- rebuildable derived projections;
- explicit provenance, confidence, stability class, and auditability;
- Striatum uses Engram as optional augmentation, not a runtime dependency;
- personal memory remains unavailable to Striatum by default.

Write the expected handoff artifact named in `workflow.json`. Include changed
files, validation commands, unresolved decisions, and downstream dependencies.
