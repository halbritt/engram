# RFC 0049 Gate Repair Handoff

Date: 2026-05-14
Repair implementor: Codex
Scope: RFC 0049 proposal text only; no code, tests, migrations, schema docs,
decision log, changelog, operator report, or upstream RFC writes.

## Summary

This repair updates RFC 0049 so the evaluation-gate contract cannot promote
default-on automatic Striatum memory ahead of its upstream contracts. The patch
adds explicit Level 2 traceability, defines per-gate failure actions, tightens
transitive no-egress evidence, requires a machine-readable golden-query
manifest, and extends packet audit reconstruction to candidate-level
row/chunk/lane/rank/score evidence.

It also folds relevant privacy and operator findings into gate traceability:
identity/citation leak omission reasons, unauthorized-pair audit redaction,
loopback Postgres binding proof, generated memory product blocking, conflict
warnings that cite current authority, and cold-start latency evidence for
`operator_startup`.

## Accepted Findings Addressed

- CC-005: Level 3 routine default-on automatic injection now explicitly
  requires accepted/promoted successors for RFC 0045, RFC 0046, RFC 0047, and
  RFC 0048. Dependent gates report `blocked_upstream` until those contracts are
  accepted.
- CC-008: The gate matrix now includes Level 2 experimental automatic injection
  and a per-gate failure-action column covering `fail`, `blocked_upstream`, and
  `accepted_with_scope_limit`.
- CC-009: EG-020 now treats no-egress scope as transitive across local model,
  embedding, reviewer/evaluator, and loopback helper runtimes that receive
  corpus text.
- CC-010: EG-070 now requires a machine-readable golden-query manifest with
  fixture hashes, lane/projection/purpose coverage, and minimum counts. EG-110
  now requires candidate-level audit fields for projection row id, chunk id,
  chunk hash, retrieval lane, generation, score, rank, and omission reason.
- PB-006/PB-010: EG-030/EG-040/EG-110 now require reference-replay coverage and
  unauthorized or pair-mismatch audit redaction so hidden corpus inventory does
  not leak through errors or audit views.
- PB-009: EG-020 now requires proof that Engram PostgreSQL is bound to loopback
  or a local socket, plus a probe that non-loopback PostgreSQL access fails.
- PB-011: EG-060 and EG-080 now name `identity_leak` and `citation_leak`
  omission reasons for path, label, and citation payload leaks.
- PB-012: EG-140 now blocks generated memory products from Level 2 or Level 3
  injection until a separate accepted privacy-inheritance and audit gate/RFC
  exists.
- ERGO-002: EG-050, EG-090, and EG-110 now require conflict warnings and
  conflict omissions to cite both the omitted memory item and the current
  authority item.
- ERGO-003: EG-100 now requires cold-start and warm-cache `operator_startup`
  latency measurements and keeps Level 3 blocked if cold-start behavior cannot
  stay within the total automatic packet budget.

## Changed Sections

- Summary and Roadmap Position: added explicit upstream promotion dependency
  language and `blocked_upstream` behavior.
- Promotion Levels: clarified Level 2 evidence reporting and made Level 3
  depend on accepted/promoted RFC 0045-0048 successors.
- Gate Matrix: added Level 2 and per-gate failure-action traceability.
- EG-020: added transitive runtime no-egress scope and loopback Postgres proof.
- EG-030 and EG-040: added unauthorized metadata redaction and reference-replay
  coverage.
- EG-050 and EG-090: added cite-current-authority requirements for conflict
  warnings and omissions.
- EG-060 and EG-080: added identity/citation leak fixtures and omission codes.
- EG-070: added machine-readable golden-query manifest requirements.
- EG-100: added cold-start latency evidence for `operator_startup`.
- EG-110: added candidate-level packet audit fields and lower-tier audit
  redaction rules.
- EG-140: added generated memory product privacy/audit placeholder gate.
- Evidence Packet, Review Requirements, Acceptance Criteria, and Deferred
  Questions: updated to reflect the repaired gate contract.

## Validation Evidence

Required whitespace validation:

```sh
git diff --check -- docs/rfcs/0049-striatum-evaluation-gates.md docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REPAIR_RFC0049_GATES.md
```

Result: passed with no output.

Additional new-file whitespace probe:

```sh
git diff --check --no-index -- /dev/null docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REPAIR_RFC0049_GATES.md
```

Result: no whitespace output; command exits nonzero because the file differs
from `/dev/null`.

Read-only context gathering used native sub-agents for contract coherence,
upstream RFC dependency terms, privacy boundary findings, and operator
ergonomics findings. No writes were delegated.

## Deferred Questions

- RFC 0045, RFC 0046, RFC 0047, and RFC 0048 are still proposal surfaces until
  accepted/promoted successors exist; Level 3 remains blocked meanwhile.
- A separate generated memory product privacy-inheritance and audit gate/RFC
  still needs an owner and accepted contract before generated products can be
  injected.
- The reference hardware profile and final latency timeout values remain open.
- The durable location and schema for long-lived Striatum memory gate reports
  remains open.
- A fresh contract-coherence re-review is still required before resuming the
  original Striatum run.
