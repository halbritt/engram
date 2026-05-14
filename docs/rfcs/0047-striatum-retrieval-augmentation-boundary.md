<a id="rfc-0047"></a>

# RFC 0047: Striatum Retrieval Augmentation Boundary

| Field | Value |
|-------|-------|
| RFC | RFC-0047 |
| Title | Striatum Retrieval Augmentation Boundary |
| Status | proposal |
| Implementation | none |
| Created | 2026-05-14 |
| Source | `STRIATUM_MEMORY_ROADMAP.md` |
| Context | RFC 0044, RFC 0045, RFC 0046, `STRIATUM_MEMORY_ROADMAP.md` |

## Summary

This RFC is the scaffold for the Striatum/Engram runtime boundary. Striatum may
use Engram as an optional local read-only augmentation source, but Striatum must
continue to run when Engram is unavailable.

This scaffold records the boundary that later implementation must preserve. It
does not add daemon RPC calls, import Engram into Striatum, expand MCP tools, or
change Striatum's authoritative workflow state.

## Roadmap Position

RFC 0047 follows the corpus contract and begins the integration path for
retrieval-backed operator support. It feeds RFC 0048, which decides how much of
retrieved memory may enter operator and workflow-agent context.

## Goals

1. Define the augmentation-not-dependency contract for Striatum.
2. Define allowed invocation surfaces for Engram retrieval.
3. Define graceful degradation behavior when Engram is absent, unhealthy, or
   stale.
4. Define capability and tenant/corpus boundaries for Striatum operator use.
5. Define citation requirements for retrieved memory.

## Non-Goals

- No Striatum daemon dependency on Engram.
- No Striatum state transition that requires Engram to succeed.
- No write-side memory mutation from Striatum to Engram.
- No personal-memory access by default.
- No broad transcript dumping into agent prompts.

## Dependencies

- RFC 0044 Engram-side Phase 1.
- RFC 0045 corpus contract.
- The reciprocal Striatum-side boundary artifact from the RFC 0044 follow-up
  queue.

## Scaffolded Workstreams

1. Inventory Striatum startup, workflow scaffolding, packet preparation,
   review, blocker, and recovery surfaces that could call Engram.
2. Define which surfaces may retrieve memory and which must remain independent.
3. Define failure-mode behavior for missing, stale, unauthorized, or malformed
   Engram responses.
4. Define how retrieved references are shown in operator-facing artifacts.
5. Produce cross-repo review evidence before implementation.

## Review Requirements

Use the multi-agent review loop before promotion:

- Striatum runtime independence review;
- Engram capability-boundary review;
- operator contract/truthfulness review;
- recovery-path review.

## Acceptance Criteria To Define

- Striatum can prepare, start, run, review, and recover workflows without
  Engram.
- Engram retrieval failures are visible but non-fatal.
- Retrieved memory is cited and distinguishable from current repo state.
- Capability defaults cannot expose personal memory to Striatum.
- Cross-repo tests or artifacts prove no runtime import/dependency regression.

## Open Questions

1. Should Striatum call Engram through MCP stdio, a CLI wrapper, or an operator
   sidecar process?
2. Where should Engram availability and freshness be recorded?
3. Which Striatum commands should show memory status?
4. How should an operator disable retrieval for a run?
