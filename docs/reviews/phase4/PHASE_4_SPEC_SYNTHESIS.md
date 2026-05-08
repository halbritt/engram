# Phase 4 Build-Spec Synthesis

author: synthesizer-claude-opus-001
Status: synthesis
Date: 2026-05-08
RFC refs: RFC-0007, RFC-0011, RFC-0018, RFC-0024
Decision refs: D006, D007, D017, D020, D021, D023, D044, D052, D055, D068, D069, D074
Phase refs: PHASE-0004

## Findings outcome

| ID | Outcome | Reason |
|----|---------|--------|
| F001 | accepted | The build spec must define `current_beliefs` as status-aware, transition-aware, and refreshable after belief lifecycle changes. |
| F002 | accepted | Entity rows and edges need provenance, privacy, versioning, audit, uniqueness, and rebuild semantics before implementation. |
| F003 | accepted | Local-LLM entity tiebreaks may exist only as bounded, local-only, auditable decisions. |
| F004 | accepted | Review queue actions must be routed through D052 transition APIs and correction-as-capture lifecycle rules. |
| F005 | accepted | Advisory audit cascade signals should be exposed as review metadata without becoming gates. |
| F006 | accepted | The workflow/source-list drift should be fixed by adding RFC-0024 to future root-review packet inputs. |
| F007 | accepted | Recursive CTE entity-neighborhood queries need explicit endpoint indexes, cycle handling, and latency checks. |
| F008 | accepted | RFC-0024's smoke and bounded preflight ladder should gate any full-corpus Phase 4 run. |
| F009 | accepted | The review queue must show enough evidence, confidence, stability, contradiction, and action context for trusted HITL review. |
| F010 | accepted | `correct` must expose a pending/reprocessed lifecycle rather than implying immediate memory repair. |
| F011 | accepted | Privacy tier labels, reclassification behavior, and redacted reporting are required for review and entity outputs. |
| F012 | deferred | REVIEW IDs are useful for promoted review artifacts, but not required to build Phase 4. |
| F013 | accepted | Future Striatum review runs need local reviewer lanes or explicit owner-approved export; this run stayed local by not launching network adapters. |

## Open decisions

### O001 — What should `current_beliefs` expose?
- Option A — Accepted-only rows with `valid_to IS NULL`.
- Option B — All lifecycle-active rows with `valid_to IS NULL` and `status IN ('candidate','provisional','accepted')`.
- Option C — A status-aware base materialized view plus consumer-specific filters for review and serving.
- Recommended: C
- Rationale: Phase 4 needs reviewable candidates, while Phase 5 must avoid false precision. A status-aware base projection keeps currentness and lifecycle visible, and later serving can filter or label by status without redefining the storage contract.

### O002 — How should entity canonicalization remain auditable?
- Option A — Mutable `entities` rows plus an `entity_audit` table.
- Option B — Append-only entity resolution events with active projections.
- Option C — Mutable active rows for query speed, backed by append-only merge/split/alias events and rebuild tests.
- Recommended: C
- Rationale: Query paths need boring relational tables, but canonicalization mistakes must be reversible and explainable. Active rows plus append-only events preserves operability without turning entity resolution into an opaque mutable cache.

### O003 — What is the contract for local-LLM entity tiebreaks?
- Option A — No LLM tiebreaks in Phase 4.
- Option B — Deterministic candidate generation with optional local-LLM advisory tiebreaks stored as audit metadata.
- Option C — Local-LLM tiebreaks directly write canonical entity decisions.
- Recommended: B
- Rationale: O003 already keeps deterministic plus LLM tiebreak on the table, but D020 and the local-first principle require bounded evidence, local runtime only, request/profile metadata, and an explicit human-reviewable audit trail before any tiebreak becomes load-bearing.

### O004 — How should review queue actions transition belief state?
- Option A — Direct SQL updates from the queue.
- Option B — All actions call the D052 transition API; `correct` creates a capture and queues reprocessing.
- Option C — Queue actions only record intents and a separate worker applies them later.
- Recommended: B
- Rationale: D052 is already the accepted transition invariant. Phase 4 should not introduce a second lifecycle path. `correct` is special because D017 makes the correction itself raw evidence; the UI should record the capture immediately and show replacement belief derivation as pending.

### O005 — What gate precedes full-corpus Phase 4 execution?
- Option A — Full-corpus run after unit tests pass.
- Option B — RFC-0024 ladder: Tier 0 smoke, Tier 1 bounded quality/UX, Tier 2 bounded production preflight.
- Option C — Tier 0 smoke only, then full corpus.
- Recommended: B
- Rationale: Entity false merges and review queue floods are operationally expensive. RFC-0024 gives the right shape: prove schema/workflow first, then quality/UX, then bounded production, and only then consider full corpus.

### O006 — How should future Striatum review lanes satisfy local-first?
- Option A — Use hosted CLIs because review artifacts are low risk.
- Option B — Use local reviewer lanes by default; require an explicit owner decision before any hosted lane sees corpus-derived input.
- Option C — Keep hosted lane names but rely on `STRIATUM_NETWORK_POLICY=forbidden`.
- Recommended: B
- Rationale: Striatum's process adapter can only make network constraints advisory for arbitrary child CLIs. The local-first contract requires either local-only reviewers or a recorded export decision.

## Recommendation

author-spec

The findings support authoring a Phase 4 implementation spec before writing production code, not opening a new proposal-stage RFC and not revising `BUILD_PHASES.md` first. The existing decisions already fix the load-bearing architecture: no graph backend, corrections as captures, no auto-acceptance, D052 transition gates, advisory audits, and Striatum state as the workflow authority. The implementation spec should bind the missing details: entity tables and audit/event model, `current_beliefs` definition and refresh path, review-queue commands and transitions, recursive CTE indexes and latency smoke checks, local-only tiebreak boundaries, privacy/redaction rules, and RFC-0024 smoke/bounded gates.

The first build should be a Tier 0 smoke implementation: migrations, deterministic entity scaffolding, `current_beliefs`, queue transition commands or CLI hooks, and aggregate/redacted smoke checks. It should not run a full-corpus Phase 4 pipeline until the smoke and bounded preflight gates pass.

## Risks the synthesis carries

- The recommendation chooses `author-spec` even though there are nine major findings. This is justified because they are implementation contract gaps, not conflicting architectural decisions.
- The synthesis recommends a hybrid active-row plus append-only-event entity model; the ledger did not explicitly choose that design, but it is the narrowest way to satisfy query speed and auditability together.
- The synthesis treats RFC-0024 as the practical gate shape even though it is still marked proposal; implementation should either promote the relevant gate decision or keep the first run bounded and reversible.
- The synthesis resolves the review harness no-egress issue operationally for this run by not launching network adapters; future runs still need a cleaner lane configuration.
