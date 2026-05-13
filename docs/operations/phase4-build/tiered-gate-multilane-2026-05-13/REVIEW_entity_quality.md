---
schema_version: "striatum.finding.v1"
artifact_kind: "finding"
verdict_intent: "accept_with_findings"
severity: "high"
tags: ["phase4", "entity-quality", "rfc-0024", "rfc-0021"]
---

# Phase 4 Entity Quality Review

author: operator [self-declared: phase4-review-entity-quality-claude]

Status: findings
Date: 2026-05-13

RFC refs:
  - RFC-0024
  - RFC-0021
  - RFC-0025

Decision refs:
  - D017
  - D020
  - D044
  - D052
  - D069
  - D077

Phase refs:
  - PHASE-0004

## Scope

This review evaluates the fresh Tier 0-2 Phase 4 evidence for entity quality
readiness only. It asks whether the published reports support any promotion
claim against the RFC 0024 gate, and whether their language matches the
evidence they actually carry.

Reviewed inputs:

- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER0_SMOKE_REPORT.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER1_NONHUMAN_REPORT.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER2_PREFLIGHT_SCAFFOLD.md`
- `docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md`
- `docs/rfcs/0021-gold-set-interview-curation.md`

This review is itself a multi-lane reviewer artifact. It is not a final
gate verdict; it produces findings the synthesizer can carry forward.

## Headline

The three Tier reports do not claim promotion readiness, and they correctly
preserve their own non-pass status. They are honest substrate.

They do not, however, deliver the entity quality evidence RFC 0024 § Tier 1
requires. Every load-bearing entity quality metric in RFC 0024 § Tier 1
(human-labeled same/different-entity precision and recall, false-merge count
on a labeled set, false-split reviewability on a labeled set, review-queue
operability judgment, predicate-shape coverage of the labeled slice) is
absent. The supporting test surface also did not execute in this worktree,
so even the non-human idempotency claim is structural rather than measured.

Promotion of Phase 4 beyond Tier 1 remains blocked.

## Findings, Severity-Ordered

### F1 — Zero human-label substrate, schema-only

Severity: critical (blocks any promotion claim).

Source:
- TIER1_NONHUMAN_REPORT.md § "Deferred RFC 0021 Gaps" (full list deferred).
- TIER0_SMOKE_REPORT.md `belief_review_actions` rows: 0; `pinned_beliefs`
  rows: 0.
- RFC 0024 § Tier 1 Required metrics requires entity-pair precision/recall
  on same-entity vs different-entity labels and false-merge/false-split
  counts on a hand-labeled set.
- RFC 0021 § Storage describes `gold_labels` / `gold_label_sessions` as the
  intended substrate for these labels; the reports do not reference any
  populated row in either table.

Rationale: RFC 0024 makes RFC 0021 / human-label evidence the only valid
input to the false-merge and false-split gates. The Tier 0 / Tier 1 reports
correctly mark this evidence as `deferred_until_rfc0021` and do not claim it.
That preservation is fine. But there is no migration to a state where the
reviewer can answer "is entity canonicalization safe for full-corpus run"
from this evidence alone. The label substrate must exist and be populated
before any Tier 1 promotion claim is even possible.

### F2 — Structural "zero duplicate active keys" must not be read as zero false merges

Severity: high.

Source:
- TIER0_SMOKE_REPORT.md "Duplicate active entity keys | 0", "Duplicate
  active entity edges | 0".
- TIER1_NONHUMAN_REPORT.md same aggregates; idempotency rationale at
  `src/engram/phase4.py:350-427` and unique active-key indexes at
  `migrations/009_phase4_entities_review.sql:1-84`.
- RFC 0024 § Tier 1 Promotion gates: "zero known false merges in the
  hand-labeled set".

Rationale: The "0 duplicate active entity keys" check proves the schema
prevents two active rows from sharing the same canonical key. It does not
prove the canonical key function maps semantically-distinct people /
projects / preferences to distinct keys. Two distinct people who happen to
share a key surface area would still produce one active row with no
duplicate. Likewise, two near-duplicate canonical keys for the same person
would produce two active rows that look fine to the structural check.

Neither report makes a "zero false merges" claim, so this is not an
overstatement finding. It is a framing finding: the synthesizer and any
future Tier 2 report must keep the structural check and the false-merge
gate clearly separate, and must not let the structural-zero number bleed
into the promotion narrative.

### F3 — False splits are not visible to any check in this evidence set

Severity: high.

Source:
- TIER1_NONHUMAN_REPORT.md aggregate counts include zero "Missing edge
  source entities" / "Missing edge target entities" / "Self-edges" but no
  cluster-cohesion or near-duplicate cluster signal.
- RFC 0024 § Tier 1 Promotion gates: "false splits are reviewable and do
  not hide evidence".

Rationale: A false split is one canonical-key value where one person /
project / preference has been split across multiple active entity rows.
None of the read-only Tier 0 / Tier 1 aggregates would detect that. The
synthetic graph timing run uses one selected seed that returns 1 row at
depth 1 and 1 row at depth 2, which is consistent with a small or
fragmented graph but cannot distinguish "fragmented because the corpus is
small" from "fragmented because the canonicalizer is over-splitting". A
labeled set or a clustering review is required.

### F4 — Review queue actionability is unmeasured at the reported scale

Severity: high.

Source:
- TIER0_SMOKE_REPORT.md `current_beliefs` rows: 30700; `belief_review_queue`
  rows: 30700; `belief_review_actions` rows: 0; status distribution is
  100% `candidate`.
- RFC 0024 § Tier 1 Recommended scope: "50 review-queue items, matching
  O005's feedback-richness question".
- RFC 0024 § Tier 1 Promotion gates: "all review actions preserve D017 and
  D052 invariants".

Rationale: The live queue is 30,700 items deep with no review actions
recorded against any of them. RFC 0024's recommended Tier 1 scope is 50
human-reviewed items. The published evidence is therefore 615x below
recommended scope on the dimension RFC 0024 most cares about for queue
operability, and has no operator UX or latency evidence at any scale.

Review-action invariants (accept / reject / correct / promote-to-pinned
routing through the D052 transition API, append-only audit) are verified
statically against `src/engram/phase4.py` and the migration. That static
verification is useful but is not the live invariant check RFC 0024
requires. There is no live latency, no live audit-row count, and no
operator feedback on whether the queue UX is operable at this scale.

### F5 — Predicate-shape coverage of the labeled slice is unverified

Severity: high.

Source:
- RFC 0024 § Tier 1 Recommended scope: "a fixed belief slice that includes
  identity, preference, project status, task, relationship, and event-shaped
  predicates".
- TIER0_SMOKE_REPORT.md and TIER1_NONHUMAN_REPORT.md aggregate the
  `current_beliefs` row count and the status distribution but do not
  decompose by predicate or stability class.

Rationale: RFC 0024 names six predicate / stability shapes that the Tier 1
slice must include. The Tier reports do not assert that the 30,700 candidate
rows cover all six shapes, do not break the queue down by stability class,
and do not propose a labeling slice that intentionally covers all six.
The "predicate-intent polish" memory item is a known orthogonal concern
that would amplify this gap (predicate gloss / coverage is currently
hidden from both the extractor prompt and the operator UI).

### F6 — Idempotency, two-hop traversal, and audit completeness are structural-only

Severity: medium.

Source:
- TIER0_SMOKE_REPORT.md "the live `make phase4-smoke LIMIT=25` command was
  not run because the needed project Python environment was absent" and
  test command failures before collection.
- TIER1_NONHUMAN_REPORT.md "the test was not executed because the local
  Python test environment is absent" and "the [two-hop] fixture proves a
  one-hop result".
- RFC 0024 § Tier 1 Required metrics: "entity-edge insert/update counts
  and rebuild idempotency", "recursive CTE p50/p95 for one-hop and two-hop
  neighborhood queries", "review action latency and audit completeness".

Rationale: Rebuild idempotency is asserted in code, indexed at the schema
level, and consistent with the live aggregate zero-duplicate check, but no
live rebuild has been executed and the targeted unit test did not run.
The two-hop recursive CTE timing is favorable at the current local edge
scale, but the single-seed evidence and the test fixture only prove a
one-hop traversal at most. Audit completeness across accept / reject /
correct / promote-to-pinned is static-only because no live review actions
exist.

These are not overstatements in the reports — the reports flag each gap
explicitly — but each item is required Tier 1 evidence per RFC 0024 and
remains uncollected.

### F7 — Tier 2 scaffold is bounded and does not over-promise

Severity: info (non-blocking, positive).

Source:
- TIER2_PREFLIGHT_SCAFFOLD.md § "Bounded Command Plan" caps Tier 2 at
  `--limit 500` and explicitly forbids `engram phase4 run`.
- TIER2_PREFLIGHT_SCAFFOLD.md § "Preserved Blockers" carries all Tier 0 /
  Tier 1 / RFC 0021 gaps forward.
- TIER2_PREFLIGHT_SCAFFOLD.md § "Recommendation": "does not authorize
  full-corpus Phase 4".

Rationale: The Tier 2 scaffold is correctly scoped and does not become a
backdoor full-run. Recording this so the synthesizer does not have to
re-prove it.

### F8 — Redaction discipline is preserved

Severity: info (non-blocking, positive).

Source:
- All three reports have an explicit "Redaction Boundary" paragraph naming
  what is and is not present.
- Aggregates only, no claim values, no belief values, no entity names, no
  relationship labels, no titles, no absolute paths.

Rationale: The artifact privacy contract from RFC 0024 § "Artifact And
Privacy Rules" is held by all three reports. Worth flagging as preserved
rather than assumed.

## Promotion Claim Audit

I checked the three reports for any language that would imply Phase 4
promotion readiness:

| Report | Strongest claim | Overstated? |
|---|---|---|
| TIER0_SMOKE_REPORT.md | "Tier 0 should remain in `findings` status …" and "Tier 0 does not authorize full-corpus Phase 4." | No. |
| TIER1_NONHUMAN_REPORT.md | "Do not promote Phase 4 beyond Tier 1 on this report." | No. |
| TIER2_PREFLIGHT_SCAFFOLD.md | "It does not recommend promotion beyond Tier 1, and it does not authorize full-corpus Phase 4." | No. |

None of the artifacts claims entity quality readiness or promotion
authorization. The reports' restraint matches the evidence they actually
carry.

## Verdict

`accept_with_findings`.

The Tier 0 / Tier 1 / Tier 2 reports are useful, honest, well-redacted
substrate. They do not overstate readiness, they preserve the RFC 0021
human-label gap, and they keep Tier 2 bounded.

They also do not move Phase 4 closer to promotion on the entity quality
axis. The RFC 0024 Tier 1 entity quality gates (zero known false merges on
a labeled set, false-split reviewability on a labeled set, review-queue
operability across the six required predicate shapes, live audit
completeness across all four review-action kinds, realistic-scale two-hop
CTE timing) are all unsatisfied. Until RFC 0021 substrate is populated and
a deliberate labeled slice covering identity / preference / project status
/ task / relationship / event predicates is in place, no Tier 1 promotion
claim is defensible.

Carry F1-F6 forward as gate blockers. F7 and F8 are positive
acknowledgements that do not require follow-up.

## Recommended Next Steps For The Synthesizer

1. Treat F1 as the gate-blocking finding; it precedes every other entity
   quality metric.
2. Require any Tier 1 re-run to publish predicate-shape coverage of the
   labeled slice, not just `current_beliefs` totals (F5).
3. Require any Tier 1 re-run to publish a labeled-set false-merge count and
   a labeled-set false-split reviewability count, not just structural
   `duplicate active entity keys = 0` (F2, F3).
4. Require any Tier 2 preflight to publish live review-action latency and
   audit-row counts across all four action kinds before any promotion
   discussion (F4, F6).
5. Keep the Tier 2 `--limit 500` ceiling and the explicit `engram phase4
   run` absence (F7).

## Evidence Artifacts

This review is the only artifact produced. No private scratch artifacts
were created. All cited evidence is in the three Tier reports and the two
referenced RFCs already on disk.
