# Review: Phase 4 Audit And Transition Invariants

Status: accept_with_findings
Date: 2026-05-13
author: operator [self-declared: phase4-review-invariants-codex]

## Findings

**Major: Tier 0-2 evidence does not promote Phase 4.**

The fresh evidence is useful, but it is explicitly non-passing. Tier 0 and
Tier 1 record that `.venv` is absent, system Python lacks `pytest`, the
preferred Phase 4 pytest surface did not run, and no live Phase 4 smoke write
was performed (`TIER0_SMOKE_REPORT.md:45`, `TIER0_SMOKE_REPORT.md:157`,
`TIER0_SMOKE_REPORT.md:196`, `TIER1_NONHUMAN_REPORT.md:51`,
`TIER1_NONHUMAN_REPORT.md:260`, `TIER1_NONHUMAN_REPORT.md:306`). Tier 2 is a
scaffold that preserves those blockers and restricts future execution to
bounded `--limit 500` commands (`TIER2_PREFLIGHT_SCAFFOLD.md:115`,
`TIER2_PREFLIGHT_SCAFFOLD.md:137`, `TIER2_PREFLIGHT_SCAFFOLD.md:237`,
`TIER2_PREFLIGHT_SCAFFOLD.md:255`). Full-corpus Phase 4 remains blocked.

**Major: Review-action invariants are favorable in code, but not live-proven.**

The inspected implementation routes `accept`, `reject`, and
`promote_to_pinned` through `transition_belief_status` and records
`belief_review_actions` (`src/engram/phase4.py:129`,
`src/engram/phase4.py:175`, `src/engram/phase4.py:294`). The transition API
sets `engram.transition_in_progress`, updates the belief, and inserts the
paired `belief_audit` row with the same `request_uuid`
(`src/engram/consolidator/transitions.py:118`,
`src/engram/consolidator/transitions.py:135`,
`src/engram/consolidator/transitions.py:157`). Corrections insert a raw
`captures` row with `capture_type = 'user_correction'`, link
`corrects_belief_id`, and record `action_status = 'queued_reprocessing'`
(`src/engram/phase4.py:221`, `src/engram/phase4.py:235`,
`src/engram/phase4.py:273`).

The evidence gap is operational, not an observed violation: the test surface
did not execute, and the live database has zero `belief_review_actions`, zero
correction actions, zero queued reprocessing actions, and zero pinned rows
(`TIER1_NONHUMAN_REPORT.md:190`, `TIER1_NONHUMAN_REPORT.md:197`,
`TIER1_NONHUMAN_REPORT.md:276`). Tier 2 still needs live accept, reject,
correct, and pin action evidence with audit completeness.

**Major: `current_beliefs` semantics are schema-correct but incompletely
exercised.**

The materialized view filters to rows where `valid_to IS NULL`,
`closed_at IS NULL`, `superseded_by IS NULL`, and status is one of
`candidate`, `provisional`, or `accepted`
(`migrations/009_phase4_entities_review.sql:143`). The live read-only
distribution supports exclusion of `rejected` and `superseded` rows:
`candidate=30700` in `current_beliefs`, `rejected=0`, `superseded=0`
(`TIER1_NONHUMAN_REPORT.md:121`). The gap is that the live corpus has no
`provisional` or `accepted` rows, and the unexecuted Phase 4 tests do not
directly cover `valid_to`, `closed_at`, or `superseded_by` exclusion
(`TIER1_NONHUMAN_REPORT.md:136`, `TIER1_NONHUMAN_REPORT.md:265`). This blocks
a full Tier 1/Tier 2 claim, but not the static status-aware design claim.

**Major: Entity build consumes candidate current beliefs without carrying
belief status into the graph surface.**

`build_deterministic_entities` selects from `current_beliefs` without selecting
or storing the source belief `status` (`src/engram/phase4.py:357`). Because
`current_beliefs` intentionally includes `candidate`, `provisional`, and
`accepted`, the entity builder can create active `entities` and `entity_edges`
from candidate beliefs (`src/engram/phase4.py:388`,
`src/engram/phase4.py:415`). That does not auto-promote the belief itself, but
it makes unaccepted belief evidence load-bearing in the graph without a
candidate/provisional label. D077 requires consumers of `current_beliefs` to
filter or label status explicitly; this consumer currently does neither. Tier 2
should either filter the entity build to the intended statuses or carry source
belief status into entity/edge provenance and downstream graph consumers.

**Major: Pending corrections are not surfaced in `current_beliefs` or
`belief_review_queue`.**

`correct_belief` records the correction as raw capture evidence and appends a
`belief_review_actions` row with `action_status = 'queued_reprocessing'`
(`src/engram/phase4.py:221`, `src/engram/phase4.py:273`). The
`current_beliefs` materialized view and `belief_review_queue` view do not join
or annotate pending correction actions (`migrations/009_phase4_entities_review.sql:143`,
`migrations/009_phase4_entities_review.sql:183`). Until a later reprocessing
pass or a separate reject action changes the belief state, the corrected belief
can remain current and reviewable without an inline warning. This preserves
D017 append-only correction semantics, but it is a review-surface safety gap.

**Major: Entity and edge provenance completeness is not demonstrated, and the
reuse path appears incomplete.**

`build_deterministic_entities` reuses an existing active entity or edge when
the canonical key already exists (`src/engram/phase4.py:621`,
`src/engram/phase4.py:714`). On reuse, it returns without appending
`source_belief_ids`, `source_claim_ids`, or `evidence_ids`, and without writing
a reuse/alias `entity_resolution_events` row. Tier 1 only proves that existing
entity and edge rows have non-empty provenance arrays, not that reused
canonical rows retain complete provenance across all contributing beliefs
(`TIER1_NONHUMAN_REPORT.md:153`). Before promotion, either define those arrays
as seed provenance only, or record append-only reuse provenance so D021-style
auditability is not lost during deterministic rebuilds.

**Medium: The Phase 4 section in `BUILD_PHASES.md` is stale relative to
D077/RFC 0024.**

The Phase 4 section still describes `current_beliefs` only as a materialized
view over beliefs with `valid_to IS NULL` and omits RFC 0024's Tier 0-2
promotion boundary, human-label requirements, zero-known-false-merge gate, and
full status-aware filter (`BUILD_PHASES.md:311`). D077 and RFC 0024 are the
controlling gate, so this is not a code invariant failure, but it is a
cold-reader risk for future review runs (`DECISION_LOG.md:101`,
`docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md:277`).

**Medium: The transition API permits a rejected-to-provisional path that remains
invisible to `current_beliefs`.**

`transition_belief_status` permits `rejected` or `superseded` beliefs to move to
`provisional` (`src/engram/consolidator/transitions.py:145`), but the status
update only sets `closed_at` when the target status is `rejected`; it never
clears an existing `closed_at` (`src/engram/consolidator/transitions.py:148`).
Since `current_beliefs` excludes rows where `closed_at IS NOT NULL`, a
reactivated `provisional` belief can remain invisible
(`migrations/009_phase4_entities_review.sql:170`). No Phase 4 review action
exposes this path today, so it is latent rather than observed, but the API
semantics should be tightened before broader use.

**Medium: Phase 4 schema preflight checks the append-only function but not the
append-only triggers.**

`phase4_schema_preflight` verifies `fn_phase4_append_only()` exists
(`src/engram/phase4.py:112`), but it does not verify that the triggers on
`entity_resolution_events`, `belief_review_actions`, and `pinned_beliefs` are
present and enabled (`migrations/009_phase4_entities_review.sql:131`,
`migrations/009_phase4_entities_review.sql:135`,
`migrations/009_phase4_entities_review.sql:139`). A drifted database with the
function present but one of those triggers missing would pass preflight while
weakening review-action append-only guarantees.

**Info: Redaction and command-surface boundaries look clean.**

The Tier reports keep to aggregate counts, schema names, command shapes, status
distributions, and timing summaries, and state that raw corpus text, prompts,
completions, belief values, entity names, relationship labels, unredacted row
ids, and home-directory paths are omitted (`TIER0_SMOKE_REPORT.md:22`,
`TIER1_NONHUMAN_REPORT.md:25`, `TIER2_PREFLIGHT_SCAFFOLD.md:27`). Dry-run
checks keep Phase 4 bounded, and `phase4 run` remains absent
(`TIER1_NONHUMAN_REPORT.md:103`, `TIER2_PREFLIGHT_SCAFFOLD.md:100`).

## Invariant Assessment

- **D017 corrections-as-captures:** Satisfied in inspected code and schema
  shape; not live-proven in this evidence set. Raw `captures` are immutable via
  the raw evidence trigger (`migrations/001_raw_evidence.sql:113`,
  `migrations/001_raw_evidence.sql:142`).
- **D044 no auto-promotion:** No violation found. Phase 3 consolidation builds
  new and merged belief payloads as `status="candidate"`
  (`src/engram/consolidator/__init__.py:686`,
  `src/engram/consolidator/__init__.py:730`). Promotion to `accepted` appears
  only behind Phase 4 review actions, and RFC 0021 gold labels remain advisory.
- **D052 transition auditability:** Satisfied in inspected code path for
  changed review transitions; not live-proven in this evidence set. Direct SQL
  mutation remains guarded by `engram.transition_in_progress`
  (`migrations/006_claims_beliefs.sql:488`).
- **`current_beliefs` status semantics:** Correct in migration definition and
  favorable in read-only live aggregate checks; incomplete for accepted /
  provisional inclusion and lifecycle-field exclusion edge cases.

## Verdict

`accept_with_findings`. I found no evidence of silent belief mutation,
unaudited changed review transition, or automatic promotion to `accepted`.
Promotion remains blocked until the Python environment is initialized, the
Phase 4 tests and live smoke run execute, live review-action audit evidence is
collected, RFC 0021/human-label gaps are addressed, and entity provenance reuse
semantics, candidate-derived graph labeling, pending-correction visibility,
reactivation lifecycle handling, and append-only trigger preflight are clarified
or fixed.
