# Phase 4 Implementation Spec

Status: specified
Date: 2026-05-08
Context: Phase 4 Tier 0 build after the Striatum spec-review gate.
Decision refs:
  - D006
  - D007
  - D017
  - D020
  - D021
  - D044
  - D052
  - D069
  - D077
Review refs:
  - none
Phase refs:
  - PHASE-0004
RFC refs:
  - RFC-0024

## Scope

Phase 4 begins with a bounded Tier 0 build, not a full-corpus run. The first
implementation adds status-aware current-belief projection, deterministic
entity scaffolding, relational entity edges, append-only entity resolution
events, and belief review actions.

The build is local-only and does not call hosted models, web services, or
telemetry. Optional local-LLM entity tiebreaks remain out of the Tier 0 path.

## Schema Contract

`current_beliefs` is a materialized view over lifecycle-active beliefs:
`valid_to IS NULL`, `closed_at IS NULL`, `superseded_by IS NULL`, and
`status IN ('candidate', 'provisional', 'accepted')`. It preserves `status`
so review and future serving consumers can filter or label uncertainty rather
than treating all current rows as accepted facts.

`entities` and `entity_edges` are active query tables backed by append-only
`entity_resolution_events`. Tier 0 creates deterministic `unknown` entities
from current belief subjects and objects; later tiers may add richer entity
kinds and local-LLM tiebreaks.

`belief_review_actions` records `accept`, `reject`, `correct`, and
`promote_to_pinned`. `accept`, `reject`, and `promote_to_pinned` use the D052
belief transition API. `correct` inserts a raw `captures` row with
`capture_type='user_correction'` and records the action as
`queued_reprocessing`.

## Smoke Gate

`engram phase4-smoke --limit N` refreshes `current_beliefs`, builds
deterministic entity/edge rows for a bounded slice, and runs a cycle-safe
1-2 hop recursive CTE query against the resulting graph. It commits only
local derived rows and emits aggregate counts.

Passing Tier 0 does not authorize a full-corpus run. Per D077/RFC-0024, Tier 1
must still validate entity precision/recall and review-queue UX, and Tier 2
must run a bounded production preflight before full-corpus Phase 4.
