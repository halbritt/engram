# Phase 4 Build-Spec Review — claude

author: reviewer-claude-opus-001
Status: review
Date: 2026-05-08
RFC refs: RFC-0007, RFC-0011, RFC-0018, RFC-0024
Decision refs: D006, D007, D017, D020, D021, D044, D052, D068, D069
Phase refs: PHASE-0004

## Findings

### F001 — `current_beliefs` is underspecified as a status-aware projection
Severity: major
Source: BUILD_PHASES.md:238-249; DECISION_LOG.md#d044; DECISION_LOG.md#d048; DECISION_LOG.md#d052
Rationale: PHASE-0004 defines `current_beliefs` as a materialized view over `beliefs` with `valid_to IS NULL`, but Phase 3 explicitly separates fact validity from row lifecycle and keeps new beliefs as `candidate` until HITL review. A view that filters only on `valid_to` can make rejected, superseded, or unreviewed rows look equally current unless the Phase 4 spec pins status filters, refresh timing, and transition-API integration.

### F002 — Entity canonicalization lacks an audit and provenance contract
Severity: major
Source: BUILD_PHASES.md:232-240; HUMAN_REQUIREMENTS.md:591-605; DECISION_LOG.md#d021; RFC-0011#schema
Rationale: Phase 4 adds `entities` and `entity_edges`, but the current row does not say how canonical names, aliases, merges, splits, or edge assertions preserve provenance, prompt/model versions, confidence, privacy tier, or rebuildability from claims and beliefs. Entity decisions will become a second derived layer; without an entity audit trail analogous to `belief_audit`, a false merge is hard to diagnose or reverse.

### F003 — Local-LLM tiebreaks are named but not bounded
Severity: major
Source: BUILD_PHASES.md:235-236; HUMAN_REQUIREMENTS.md:90-102; HUMAN_REQUIREMENTS.md:123-160; RFC-0024:189-218
Rationale: The row permits a local LLM disambiguation tiebreak, but does not define when it may be invoked, what evidence it sees, whether the result is advisory or load-bearing, or what request metadata is persisted. Because local-first and no-egress are load-bearing, Phase 4 needs a deterministic-first canonicalization policy and an auditable local-only tiebreak contract before entity rows become dependencies.

### F004 — Review queue actions are not specified as transition-safe workflows
Severity: major
Source: BUILD_PHASES.md:242-247; DECISION_LOG.md#d006; DECISION_LOG.md#d017; DECISION_LOG.md#d052
Rationale: PHASE-0004 lists `accept`, `reject`, `correct`, and `promote-to-pinned`, but the spec inputs do not define the state transitions, audit rows, idempotency behavior, or concurrent-review conflict handling. `correct` must insert a new `captures` row, but the queue also needs a visible pending/reprocessed state so the user can tell when a correction has actually produced replacement claims and beliefs.

### F005 — Advisory audit signals are not surfaced in the review surface
Severity: minor
Source: RFC-0018:195-201; DECISION_LOG.md#d069; BUILD_PHASES.md:242-249
Rationale: RFC-0018 and D069 keep audit cascade verdicts advisory, which is correct for V1, but Phase 4 is where humans review beliefs. The build spec should say whether queue sort order and detail views expose invalidated-claim counts, audit reasons, and same-family warnings without auto-promoting or auto-demoting beliefs.

### F006 — RFC-0024 is relevant but not in the workflow job inputs
Severity: minor
Source: striatum/phase-4-spec-review/SOURCES.md; striatum/phase-4-spec-review/workflow.json; RFC-0024:75-88
Rationale: The source list includes RFC-0024's Phase 4 benchmark gate, but the workflow packet for root reviewers only lists RFC-0007, RFC-0011, and RFC-0018. Reviewers should treat RFC-0024 as relevant because it directly constrains full-corpus Phase 4 execution, reporting privacy, and smoke/bounded benchmark gates.

## Open questions

- What exact statuses are included in `current_beliefs`, and does Phase 5 consume only `accepted` rows or also `candidate` rows with labels?
- Are entity canonicalization operations stored as append-only merge/split events, an `entity_audit` table, or both?
- Is `promote-to-pinned` a belief status, a queue action, or a separate pinned projection?
- What is the bounded benchmark gate before full-corpus Phase 4 execution, and is RFC-0024 the source of truth?

verdict: accept_with_findings
