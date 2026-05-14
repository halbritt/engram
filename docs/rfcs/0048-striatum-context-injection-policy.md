<a id="rfc-0048"></a>

# RFC 0048: Striatum Context Injection Policy

| Field | Value |
|-------|-------|
| RFC | RFC-0048 |
| Title | Striatum Context Injection Policy |
| Status | proposal |
| Implementation | none |
| Created | 2026-05-14 |
| Source | `STRIATUM_MEMORY_ROADMAP.md` |
| Context | RFC 0045, RFC 0046, RFC 0047, `STRIATUM_MEMORY_ROADMAP.md` |

## Summary

This RFC is the scaffold for deciding how retrieved Engram memory enters
Striatum operator and workflow-agent context. The policy should keep Striatum
context useful without turning every prompt into a giant transcript dump.

This scaffold does not choose token budgets, ranking formulas, UI behavior, or
agent-packet formats. It queues the policy work after the retrieval boundary is
defined.

## Roadmap Position

RFC 0048 depends on RFC 0047. Once Striatum may retrieve from Engram without
depending on it, this RFC decides which retrieved slices are eligible for
operator startup summaries, workflow scaffolding, implementation packets,
review packets, blocker investigation, and recovery.

## Goals

1. Define task-relevant memory selection rules.
2. Define per-surface context budgets.
3. Define citation and provenance display requirements.
4. Define freshness, authority, and recency weighting rules.
5. Define when retrieved memory should be summarized, quoted, omitted, or
   escalated to the operator.

## Non-Goals

- No new raw ingestion format.
- No projection schema changes beyond requirements fed back to RFC 0046.
- No write-side memory mutation.
- No implicit personal-memory injection.
- No replacement of current repo files, git history, Striatum state, or
  operator reports as authority.

## Dependencies

- RFC 0045 corpus contract.
- RFC 0046 projections and indexes.
- RFC 0047 retrieval augmentation boundary.

## Scaffolded Workstreams

1. Inventory Striatum contexts that may receive memory.
2. Define authority ordering among current files, accepted syntheses, reviews,
   raw logs, old brainstorms, and generated summaries.
3. Define prompt packet budget rules and truncation behavior.
4. Define citation rendering and reference-fetch behavior.
5. Define operator-visible controls for enabling, disabling, or inspecting
   injected memory.

## Review Requirements

Use the multi-agent review loop before promotion:

- operator ergonomics and context-quality review;
- provenance/truthfulness review;
- safety and privacy-boundary review;
- workflow-agent packet review.

## Acceptance Criteria To Define

- Context injection is bounded per surface.
- Injected memory always carries citations back to raw or accepted evidence.
- Current canonical docs outrank stale brainstorms.
- Accepted syntheses outrank unsynthesized reviews.
- Operators can tell when memory was unavailable, omitted, stale, or disabled.

## Open Questions

1. What is the default memory budget for each packet type?
2. How should conflict between current repo state and retrieved memory be
   surfaced?
3. Which contexts require exact references versus summarized recall?
4. Should memory injection be opt-in per workflow, default-on, or policy based?
