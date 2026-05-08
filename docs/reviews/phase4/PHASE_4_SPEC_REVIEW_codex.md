# Phase 4 Build-Spec Review — codex

author: reviewer-codex-gpt-5.5-001
Status: review
Date: 2026-05-08
RFC refs: RFC-0007, RFC-0011, RFC-0018, RFC-0024
Decision refs: D006, D007, D017, D021, D044, D052, D053, D055, D068, D069
Phase refs: PHASE-0004

## Findings

### F001 — `current_beliefs` needs a concrete SQL definition and refresh invariant
Severity: major
Source: BUILD_PHASES.md:238-249; BUILD_PHASES.md:197-219; DECISION_LOG.md#d044; DECISION_LOG.md#d055
Rationale: The Phase 4 row says the view is over `valid_to IS NULL`, while Phase 3 says lifecycle state is separate from fact validity and rebuilds are structurally equivalent rather than ID-stable. The implementation spec must pin the SELECT predicate, indexes, refresh method, and expected behavior during rebuilds so consumers never observe stale or lifecycle-closed rows as current.

### F002 — Entity and edge schemas need uniqueness, rebuild, and privacy rules
Severity: major
Source: BUILD_PHASES.md:232-240; HUMAN_REQUIREMENTS.md:591-616; DECISION_LOG.md#d021
Rationale: `entities` and `entity_edges` are named but not specified. The build needs keys for canonical identity, aliases, source belief/claim ids, confidence, privacy tier, version metadata, active/inactive state, and rebuild semantics; otherwise Phase 4 can create non-rebuildable canonical state that violates the raw-evidence-to-derived-cache model.

### F003 — Recursive CTE acceptance criteria need an index and cycle plan
Severity: major
Source: BUILD_PHASES.md:248-250; DECISION_LOG.md#d007; RFC-0024:143-162
Rationale: D007 accepts relational `entity_edges` for V1, but the Phase 4 row only says 1-2 hop queries should work. The spec should require directional/undirected edge semantics, edge type filters, indexes on both endpoints, recursion depth caps, cycle prevention, and EXPLAIN-backed p50/p95 targets before using the query path in serving code.

### F004 — Review actions must reuse the D052 transition API, not invent direct updates
Severity: major
Source: BUILD_PHASES.md:204-207; BUILD_PHASES.md:242-247; DECISION_LOG.md#d052
Rationale: Phase 3 rejects direct SQL UPDATE unless the transition GUC is set and a matching `belief_audit` row is inserted. Phase 4 review actions are precisely belief lifecycle changes, so the build spec should name the API functions, allowed transitions, request UUID behavior, and audit payloads for `accept`, `reject`, and `promote-to-pinned`.

### F005 — Phase 4 needs a scratch/smoke mode before full-corpus writes
Severity: major
Source: RFC-0024:101-187; DECISION_LOG.md#d074
Rationale: RFC-0024 proposes a Tier 0 smoke, Tier 1 quality/UX gate, and Tier 2 bounded production preflight before full-corpus Phase 4. That ladder should become part of the implementation handoff because entity false merges and review-queue floods are expensive to unwind once materialized.

### F006 — Artifact references are mostly available, but review outputs lack REVIEW IDs
Severity: nit
Source: docs/process/artifact-id-conventions.md:15-23; docs/process/artifact-id-conventions.md:139-160; DECISION_LOG.md#d068
Rationale: D068 gives review documents a `REVIEW-####` family, but this workflow's expected artifacts are unnumbered filenames. That is acceptable for an operational loop, but any long-lived accepted synthesis should either get a registered review ID or remain clearly scoped as an unregistered run artifact.

## Open questions

- What concrete indexes are required for `current_beliefs` and `entity_edges`?
- Are canonical entity rows append-only with active flags, mutable rows with audit, or a hybrid?
- What latency target defines "efficiently" for `current_beliefs` and 1-2 hop queries?
- Does Phase 4 include a CLI-only review surface first, or must the thin web view be built now?

verdict: accept_with_findings
