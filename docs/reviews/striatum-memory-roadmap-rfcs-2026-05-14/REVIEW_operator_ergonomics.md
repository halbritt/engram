# Review: Striatum Memory Roadmap Operator Ergonomics
author: operator [self-declared: roadmap-review-operator-ergonomics]

Verdict: accept_with_findings

## Summary

This review assesses the operator ergonomics of the Striatum memory roadmap, specifically focusing on RFC 0047 (Retrieval Augmentation Boundary) and RFC 0048 (Context Injection Policy). The proposed architecture demonstrates a high degree of maturity in its approach to citation ergonomics, graceful degradation, and the preservation of operator authority. The strict separation between "current authority" and "retrieved memory" successfully mitigates the risk of hallucinated instructions while providing high-signal context.

## Findings

| ID | Severity | Affected Section | Rationale | Proposed Fix |
|----|----------|------------------|-----------|--------------|
| ERGO-001 | minor | RFC 0048 § 7 | The mandatory multi-line status header for every memory section may introduce "packet noise" in high-frequency interactions when no memory is selected (`no_data`). | Allow a collapsed, single-line status format when no memory items are selected (e.g., `memory: no_data [tenant=striatum corpus=striatum purpose=...]`). |
| ERGO-002 | minor | RFC 0048 § 9 | The "Conflict Warning" mechanism identifies *that* a contradiction occurred but does not explicitly require naming the "Current Authority" item that caused the omission. This increases operator decision cost when debugging why a known memory was excluded. | Explicitly require that Conflict Warnings cite both the `logical_id` of the omitted memory item and the `logical_id` or `path` of the contradicting current authority item. |
| ERGO-003 | nit | RFC 0047 § 9.1 | A 2000ms timeout for `search` may be too aggressive for the initial `operator_startup` search on systems with cold caches or mechanical disks, potentially leading to a `timeout` status on the most context-heavy turn. | Add a recommendation for a larger timeout (e.g., 5000ms) or asynchronous pre-fetch for the `operator_startup` purpose. |
| ERGO-004 | nit | RFC 0048 § 11 | The disable controls are robust, but the "session" scope behavior is not explicitly defined regarding persistence across daemon restarts. | Clarify that `session` scope disablement is transient and does not persist in `.striatum/state.sqlite3` across daemon restarts unless promoted to a `run` or operator-config level. |

## Operator Ergonomics Notes

### Operator Decision Cost
The architecture minimizes operator decision cost by defaulting to a "fail-silent but status-visible" posture. The operator does not need to adjudicate every retrieval failure; the system continues with baseline authority. The decision cost is shifted from "fixing retrieval" to "reviewing citations," which is appropriately aligned with a supervisor-agent relationship.

### Memory Status Visibility
Visibility is excellent. The inclusion of explicit omission reasons (e.g., `unauthorized`, `stale_rejected`, `over_budget`) ensures the operator knows exactly why context is missing.

### Citation Ergonomics
The citation model is exhaustive. By requiring `logical_id` and `version_id` alongside path/line data, the system ensures that citations remain durable across index rebuilds and repository moves.

### Disable Controls
The three-tiered disable model (run, session, packet) provides the necessary granularity for an operator to "silence" the memory lane during sensitive or high-noise tasks without losing the feature for the entire run.

### Graceful Degradation
The robust status vocabulary in RFC 0047 ensures that every failure mode has a non-fatal representation. The "Augmentation-Not-Dependency" boundary is the load-bearing feature of this architecture.

### Packet Noise
Token budgets and truncation rules are well-defined. The 25% budget cap prevents memory from overwhelming the current task context.

### Manual-vs-Automatic Defaults
The mapping of "Purpose" to automatic injection behavior provides a clear contract. The distinction that `ui_search` and `manual_search` never inject into packets automatically is a correct safety property.

## Residual Risks
- **Inductive Bias:** As with all RAG systems, the quality of "Context Quality" depends on the underlying embedding and segmentation models (Phase 2/3). If these degrade, the "Quality" of injected context may suffer despite robust ergonomics.
- **Dependency Drift:** While RFC 0047 forbids it, future developers may be tempted to use `memory: available` as a proxy for workflow readiness. This must be guarded against in implementation reviews.

## Suggested Follow-up
- Validate the "Conflict Warning" ergonomics with a synthetic fixture where a stale RFC is overridden by a current decision log.
- Perform a "cold-start" latency benchmark to tune the `operator_startup` timeout.

## Validation Evidence
```sh
git diff --check -- docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_operator_ergonomics.md
```
(No trailing whitespace or conflict markers detected).
