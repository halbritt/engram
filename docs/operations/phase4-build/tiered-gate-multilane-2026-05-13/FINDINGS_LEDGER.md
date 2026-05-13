# Phase 4 Gate Findings Ledger
author: operator [self-declared: phase4-findings-ledger-codex]

Status: ledger
Date: 2026-05-13

## Scope

This ledger normalizes the independent Phase 4 gate reviews into one
promotion-impact record. It does not decide the final gate outcome and does
not authorize full-corpus Phase 4 execution.

Source reviews:

- `REVIEW_entity_quality.md` - `phase4-review-entity-quality-claude`
- `REVIEW_invariants.md` - `phase4-review-invariants-codex`
- `REVIEW_privacy_provenance.md` - `phase4-review-privacy-provenance-gemini-trusted`

Redaction boundary: this ledger contains only aggregate counts, schema and
artifact names, command shapes, and review findings. It omits raw corpus text,
belief values, claim values, entity names, relationship labels, conversation
titles, prompts, completions, private paths, and unredacted row ids.

## Normalized Findings

### P4-GATE-L001 - Phase 4 promotion remains blocked

Stable id: P4-GATE-L001

Severity: critical

Source review: `REVIEW_entity_quality.md` F1 and verdict;
`REVIEW_invariants.md` "Tier 0-2 evidence does not promote Phase 4";
`REVIEW_privacy_provenance.md` Finding 2 and verdict.

Evidence: Tier 0 and Tier 1 are recorded as non-passing findings, not pass
reports. Tier 2 is a bounded scaffold, not an executed preflight. The reviews
agree that missing runtime/test evidence, deferred human-label evidence, and
preserved blockers prevent promotion.

Disposition recommendation: accepted.

Promotion impact: blocks promotion beyond the current findings/scaffold state
and blocks any full-corpus Phase 4 claim until RFC 0024 Tier 0, Tier 1, and
Tier 2 gates pass with their blockers resolved or explicitly carried by an
operator decision.

### P4-GATE-L002 - Python environment and live smoke execution are missing

Stable id: P4-GATE-L002

Severity: major

Source review: `REVIEW_entity_quality.md` F6; `REVIEW_invariants.md` "Tier
0-2 evidence does not promote Phase 4".

Evidence: The Tier reports state that `.venv/bin/python` is absent, system
Python lacks `pytest`, the preferred Phase 4 pytest surface did not run, and
no live `make phase4-smoke LIMIT=25` write was performed. Dry-run command
checks are favorable but do not substitute for executable Tier 0 evidence.

Disposition recommendation: accepted.

Promotion impact: blocks Tier 0 pass and any Tier 2 production preflight
claim until the project environment is initialized, targeted Phase 4 tests run,
and bounded live smoke execution is recorded.

### P4-GATE-L003 - Human-label entity quality substrate is absent

Stable id: P4-GATE-L003

Severity: critical

Source review: `REVIEW_entity_quality.md` F1, F2, F3, F5; `REVIEW_invariants.md`
verdict.

Evidence: RFC 0024 requires hand-labeled same-entity/different-entity
precision and recall, false-merge counts, false-split reviewability, and a
fixed slice covering identity, preference, project status, task, relationship,
and event-shaped predicates. The Tier reports explicitly defer RFC 0021
human-label evidence and do not report populated label rows or a labeled
entity slice.

Disposition recommendation: accepted.

Promotion impact: blocks Tier 1 promotion on the entity-quality axis. Structural
aggregates can remain useful preflight evidence, but they cannot satisfy the
zero-known-false-merge or false-split gates.

### P4-GATE-L004 - Structural duplicate checks must not be treated as semantic entity quality

Stable id: P4-GATE-L004

Severity: high

Source review: `REVIEW_entity_quality.md` F2 and F3.

Evidence: The reports show zero duplicate active entity keys and zero duplicate
active edges, backed by schema indexes and aggregate checks. The source review
correctly distinguishes these from semantic false-merge and false-split
evidence: one incorrect canonical key can merge distinct entities without
creating a duplicate, and one real entity can be split across multiple
apparently valid keys.

Disposition recommendation: accepted.

Promotion impact: blocks any promotion narrative that equates structural
idempotency with entity precision. Future Tier 1/Tier 2 reports must publish
labeled false-merge and false-split evidence separately.

### P4-GATE-L005 - Review queue actionability is unmeasured

Stable id: P4-GATE-L005

Severity: high

Source review: `REVIEW_entity_quality.md` F4 and F6; `REVIEW_invariants.md`
"Review-action invariants are favorable in code, but not live-proven".

Evidence: The reports record `current_beliefs` and `belief_review_queue` at
30,700 rows, all candidate in the reported distribution, with zero
`belief_review_actions`, zero correction actions, zero queued reprocessing
actions, and zero pinned rows. RFC 0024's Tier 1 scope calls for about 50
review-queue items with human/operator feedback and measured action outcomes.

Disposition recommendation: accepted.

Promotion impact: blocks Tier 1 review-queue operability and blocks Tier 2
review-action readiness until live accept, reject, correct, and
promote-to-pinned actions produce latency, outcome, and audit-completeness
evidence.

### P4-GATE-L006 - Review-action invariants are code-favorable but not live-proven

Stable id: P4-GATE-L006

Severity: major

Source review: `REVIEW_invariants.md` "Review-action invariants are favorable
in code, but not live-proven"; `REVIEW_entity_quality.md` F6.

Evidence: Static inspection shows accept, reject, and promote-to-pinned route
through the D052 transition API and record `belief_review_actions`; correction
inserts raw `captures` evidence and records queued reprocessing. The tests
that should exercise these paths did not run in this worktree, and the live
database has no review-action rows.

Disposition recommendation: accepted.

Promotion impact: blocks claiming D017/D052 operational enforcement at Tier 2
until all four review actions are executed in an initialized environment and
the resulting audit/review rows are verified.

### P4-GATE-L007 - `current_beliefs` is status-aware but incompletely exercised

Stable id: P4-GATE-L007

Severity: major

Source review: `REVIEW_invariants.md` "`current_beliefs` semantics are
schema-correct but incompletely exercised"; `REVIEW_entity_quality.md` F6.

Evidence: The migration defines `current_beliefs` with `valid_to IS NULL`,
`closed_at IS NULL`, `superseded_by IS NULL`, and status in `candidate`,
`provisional`, or `accepted`. Live aggregate evidence supports exclusion of
`rejected` and `superseded` rows, but the corpus has no reported provisional
or accepted rows, and the unexecuted Phase 4 tests do not directly exercise
`valid_to`, `closed_at`, or `superseded_by` exclusion edge cases.

Disposition recommendation: accepted-with-modification: accept the
status-aware schema claim, but keep the exercised-behavior gap as a promotion
blocker.

Promotion impact: blocks full Tier 1/Tier 2 projection-semantics readiness
until accepted/provisional inclusion and lifecycle-field exclusion are tested
or otherwise measured.

### P4-GATE-L008 - Candidate beliefs become active graph state without status labeling

Stable id: P4-GATE-L008

Severity: major

Source review: `REVIEW_invariants.md` "Entity build consumes candidate current
beliefs without carrying belief status into the graph surface".

Evidence: The entity builder reads from `current_beliefs`, which intentionally
includes `candidate`, `provisional`, and `accepted`, and can create active
`entities` and `entity_edges` from candidate beliefs. The graph rows do not
carry the source belief status, so downstream graph consumers cannot see that
some load-bearing graph state is derived from unaccepted beliefs.

Disposition recommendation: accepted.

Promotion impact: blocks broader graph-readiness claims until Phase 4 either
filters the entity build to intended statuses or carries source belief status
into entity/edge provenance and any downstream graph consumer.

### P4-GATE-L009 - Pending corrections are not visible on current/review surfaces

Stable id: P4-GATE-L009

Severity: major

Source review: `REVIEW_invariants.md` "Pending corrections are not surfaced in
`current_beliefs` or `belief_review_queue`".

Evidence: Correction records are append-only raw captures and review-action
rows with `action_status = 'queued_reprocessing'`, which preserves D017. The
`current_beliefs` materialized view and `belief_review_queue` view do not join
or annotate those pending correction actions, so a corrected belief can remain
current and reviewable without an inline warning until reprocessing or a
separate rejection changes lifecycle state.

Disposition recommendation: accepted.

Promotion impact: blocks review-surface safety readiness until pending
corrections are surfaced, filtered, or otherwise made visible to operators and
downstream consumers.

### P4-GATE-L010 - Entity and edge reuse provenance may be incomplete

Stable id: P4-GATE-L010

Severity: major

Source review: `REVIEW_invariants.md` "Entity and edge provenance completeness
is not demonstrated, and the reuse path appears incomplete".

Evidence: The deterministic builder reuses existing active entity and edge rows
when canonical keys already exist. On reuse, the reviewed code path returns
without appending contributing `source_belief_ids`, `source_claim_ids`, or
`evidence_ids`, and without writing a reuse/alias resolution event. Aggregate
checks prove existing rows have non-empty provenance arrays, but not that
provenance remains complete across reused contributors.

Disposition recommendation: accepted.

Promotion impact: blocks D021-style auditability claims for entity reuse until
the implementation either defines arrays as seed provenance only or records
append-only reuse provenance.

### P4-GATE-L011 - Predicate and stability-shape coverage is unreported

Stable id: P4-GATE-L011

Severity: high

Source review: `REVIEW_entity_quality.md` F5.

Evidence: RFC 0024 names identity, preference, project status, task,
relationship, and event-shaped predicates as required Tier 1 slice coverage.
The reports aggregate `current_beliefs` row counts and status distribution,
but do not decompose by predicate or stability class and do not publish a
deliberately covered labeled slice.

Disposition recommendation: accepted.

Promotion impact: blocks Tier 1 entity/review-quality promotion until a
labeled slice reports coverage across the required shapes.

### P4-GATE-L012 - Recursive CTE and rebuild evidence is not yet realistic-scale proof

Stable id: P4-GATE-L012

Severity: medium

Source review: `REVIEW_entity_quality.md` F6; `REVIEW_invariants.md` verdict.

Evidence: Read-only recursive CTE timings are favorable at the current active
edge scale, and code includes bounded depth and cycle handling. The source
review notes that the test fixture was not executed and appears to prove a
one-hop result even when called with `max_depth=2`; the realistic synthetic
scale benchmark required by RFC 0024 remains unrun.

Disposition recommendation: accepted.

Promotion impact: blocks Tier 1/Tier 2 query-plan readiness until one-hop and
two-hop traversal are exercised at realistic synthetic scale with p50/p95
timings.

### P4-GATE-L013 - `BUILD_PHASES.md` Phase 4 wording is stale

Stable id: P4-GATE-L013

Severity: medium

Source review: `REVIEW_invariants.md` "The Phase 4 section in
`BUILD_PHASES.md` is stale relative to D077/RFC 0024".

Evidence: The Phase 4 section still describes `current_beliefs` primarily as
a materialized view over `valid_to IS NULL` beliefs and does not carry the full
RFC 0024 Tier 0/Tier 1/Tier 2 promotion boundary, human-label requirement,
zero-known-false-merge gate, or complete status-aware filter.

Disposition recommendation: accepted-with-modification: record as a
cold-reader/documentation risk, not as the controlling gate source.

Promotion impact: does not independently block if D077/RFC 0024 remain the
controlling gate, but should be fixed before future handoffs depend on
`BUILD_PHASES.md` alone.

### P4-GATE-L014 - Reactivated rejected/superseded beliefs can remain invisible

Stable id: P4-GATE-L014

Severity: medium

Source review: `REVIEW_invariants.md` "The transition API permits a
rejected-to-provisional path that remains invisible to `current_beliefs`".

Evidence: The transition API permits rejected or superseded beliefs to move to
`provisional`, while `closed_at` is not cleared by that status update. Because
`current_beliefs` excludes rows where `closed_at IS NOT NULL`, a reactivated
provisional belief can remain outside the projection. No current Phase 4
review action exposes this path, so this is latent rather than observed.

Disposition recommendation: accepted.

Promotion impact: blocks broader lifecycle-safety claims until the transition
API either rejects this path, clears lifecycle fields correctly, or documents
the invisibility as intentional.

### P4-GATE-L015 - Phase 4 preflight does not verify append-only triggers

Stable id: P4-GATE-L015

Severity: medium

Source review: `REVIEW_invariants.md` "Phase 4 schema preflight checks the
append-only function but not the append-only triggers".

Evidence: The preflight checks the append-only function exists, but not that
the triggers on `entity_resolution_events`, `belief_review_actions`, and
`pinned_beliefs` are present and enabled. A drifted database with the function
but missing triggers could pass preflight while weakening append-only
guarantees.

Disposition recommendation: accepted.

Promotion impact: blocks strong append-only preflight claims until trigger
presence/enabled-state checks are added or separately verified before Tier 2.

### P4-GATE-L016 - Single-lane Tier evidence needs an explicit provenance decision

Stable id: P4-GATE-L016

Severity: major

Source review: `REVIEW_privacy_provenance.md` Finding 3.

Evidence: The Tier 0, Tier 1, and Tier 2 evidence files carry honest
single-lane Codex bylines. The privacy/provenance review notes that the RFC
0032 audit context requires either an explicit operator deviation recorded in
`DECISION_LOG.md` or a multi-lane re-review before single-lane evidence can
serve a tiered gate promotion decision.

Disposition recommendation: accepted.

Promotion impact: blocks promotion based on the Tier evidence until the owner
records an explicit single-lane acceptance/deviation or a satisfactory
multi-lane re-review supersedes the provenance concern.

### P4-GATE-L017 - Redaction and local-only artifact boundaries are preserved

Stable id: P4-GATE-L017

Severity: info

Source review: `REVIEW_entity_quality.md` F8; `REVIEW_invariants.md` info
finding; `REVIEW_privacy_provenance.md` Findings 1 and 4.

Evidence: All three reviews agree that the Tier artifacts use aggregate counts,
status distributions, schema names, timing summaries, and command shapes while
omitting private corpus content and private paths. The privacy/provenance
review also found no reuse of quarantined artifacts flagged by the RFC 0032
audit.

Disposition recommendation: accepted.

Promotion impact: no blocker. Preserve this boundary in any follow-on Tier 1
or Tier 2 report.

### P4-GATE-L018 - Tier 2 scaffold and command surface remain bounded

Stable id: P4-GATE-L018

Severity: info

Source review: `REVIEW_entity_quality.md` F7; `REVIEW_invariants.md` info
finding; `REVIEW_privacy_provenance.md` Finding 2.

Evidence: The Tier 2 scaffold caps future execution at `--limit 500`, carries
Tier 0/Tier 1 blockers forward, and explicitly avoids `engram phase4 run`.
The command-surface evidence aligns with RFC 0025's rule that Phase 4 exposes
specific bounded verbs until a later decision authorizes a full Phase 4 run
contract.

Disposition recommendation: accepted.

Promotion impact: no promotion authorization. This is a positive boundary
finding that keeps follow-on execution constrained.

## Promotion Blocker Summary

The following normalized findings block any Phase 4 promotion claim:

- P4-GATE-L001: overall non-passing gate state.
- P4-GATE-L002: missing environment, tests, and live Tier 0 smoke execution.
- P4-GATE-L003: absent human-label entity-quality substrate.
- P4-GATE-L004: structural duplicate checks do not prove semantic quality.
- P4-GATE-L005 and P4-GATE-L006: review queue and review-action invariants are
  not live-proven.
- P4-GATE-L007 through P4-GATE-L015: unresolved projection, graph provenance,
  correction visibility, lifecycle, query-scale, documentation, and preflight
  gaps.
- P4-GATE-L016: provenance decision still needed for single-lane Tier evidence.

Positive non-blocking findings:

- P4-GATE-L017: redaction and local-only artifact boundaries are preserved.
- P4-GATE-L018: Tier 2 remains bounded and does not create a full-run backdoor.

## Counts

- Total normalized findings: 18
- Severity breakdown: critical=2, high=4, major=7, medium=3, info=2
- Disposition recommendations: accepted=16, accepted-with-modification=2,
  deferred=0, rejected=0
