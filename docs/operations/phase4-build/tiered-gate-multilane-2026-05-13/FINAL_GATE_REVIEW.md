---
schema_version: "striatum.finding.v1"
artifact_kind: "finding"
verdict_intent: "accept"
severity: "critical"
tags: ["phase4", "final-gate", "rfc-0024", "rfc-0021", "rfc-0025"]
---

# Phase 4 Final Gate Review
author: operator [self-declared: phase4-final-gate-review-codex]

Status: accept
Date: 2026-05-13

RFC refs:
  - RFC-0024
  - RFC-0021
  - RFC-0025

Decision refs:
  - D017
  - D020
  - D021
  - D044
  - D052
  - D074
  - D077
  - D078

Phase refs:
  - PHASE-0004

## Verdict

Accept the Tier 0, Tier 1, Tier 2 scaffold, findings ledger, and promotion
synthesis as a privacy-safe, correctly non-promoting evidence package.

This acceptance is not Phase 4 promotion. Full-corpus Phase 4 remains blocked.
Tier 0 is still non-passing, Tier 1 lacks RFC 0021 / human-label evidence, and
Tier 2 is only a bounded preflight scaffold. No reviewed artifact authorizes
full-corpus Phase 4, hides the missing human-label dependency, or includes
private corpus content.

## Findings

### Critical: Full-corpus Phase 4 remains blocked

RFC 0024 and D077 require the Tier 0, Tier 1, and Tier 2 gate sequence before
any full-corpus Phase 4 run. The current evidence does not satisfy that
sequence: `TIER0_SMOKE_REPORT.md` and `TIER1_NONHUMAN_REPORT.md` are findings
reports, not passes, and `TIER2_PREFLIGHT_SCAFFOLD.md` is a scaffold, not an
executed production preflight.

The promotion synthesis carries the right gate state: promotion is blocked
pending environment, human-label, live review-action, Tier 2 execution, and
projection/provenance evidence fixes. This matches RFC 0024's promotion
criteria and does not create a full-run authorization.

### Critical: RFC 0021 human-label evidence is still absent

Tier 1 cannot pass without a human-labeled entity-quality substrate. The Tier 1
report explicitly records the missing same/different-entity labels,
precision/recall, zero-known-false-merge validation, false-split
reviewability, review-queue UX feedback, and action-outcome evidence as
`deferred_until_rfc0021`.

That deferral is honest and blocks promotion. RFC 0021 creates claim/belief
gold-label machinery; a follow-on Tier 1 pass still needs an explicit mapping
or slice design that turns those labels into RFC 0024 entity-pair and
false-merge/false-split evidence.

### High: Tier 0 executable smoke evidence is missing

Tier 0 reports favorable read-only schema and aggregate checks, but the
project Python environment was absent, targeted pytest commands did not run,
and no live `make phase4-smoke LIMIT=25` write was performed. Dry-run command
shape and static inspection are useful, but they do not satisfy RFC 0024's
end-to-end Tier 0 smoke requirement.

### High: Tier 1 non-human evidence is not promotion-grade

The Tier 1 report gives useful structural evidence: status-aware
`current_beliefs`, zero duplicate active entity keys/edges, bounded command
surface, and non-pathological read-only CTE timings at the current scale. Those
checks do not establish semantic entity quality or review operability.

Remaining Tier 1 blockers include unexecuted tests, no live provisional or
accepted inclusion evidence, no live review actions, no labeled false-merge or
false-split measurement, no required predicate/stability slice coverage, and
no realistic synthetic graph-scale benchmark.

### High: Review-action and projection invariants are favorable but unproven

The inspected implementation appears aligned with D017, D044, and D052:
corrections write raw `captures`, Phase 3 does not auto-promote to accepted,
and accept/reject/pin transitions route through the transition API. The gate
evidence does not yet prove those invariants operationally because the tests
did not execute and the live database has zero review-action rows.

The ledger also correctly carries projection/provenance risks: candidate
beliefs can become active graph state without status labeling, pending
corrections are not surfaced on current/review projections, entity/edge reuse
provenance is not demonstrated complete, reactivation lifecycle semantics are
latent, and append-only trigger preflight needs stronger verification.

### Major: Promotion synthesis is supported, with bookkeeping fixes needed

The main synthesis recommendation is supported by the Tier reports and
independent reviews: promotion remains blocked, the evidence is aggregate-only,
Tier 2 remains bounded, and the next evidence-fix step is clear.

Two bookkeeping issues should be corrected before future operators rely on the
ledger as a cold-read summary. The severity count appears to list `high=4,
medium=3` even though the normalized entries read as three high and four
medium findings. Also, `P4-GATE-L013` is summarized with the blockers even
though its own entry says stale `BUILD_PHASES.md` wording does not
independently block promotion.

### Major: Provenance remains a promotion precondition

The evidence bylines are honest. The privacy/provenance review nevertheless
flags that single-lane Tier evidence and reviewer lane names require an
operator decision or satisfactory multi-lane re-review before being used for a
promotion decision. That provenance issue does not create a privacy failure,
but it remains a promotion precondition.

### Info: Privacy and redaction boundaries are preserved

The reviewed artifacts use aggregate counts, command shapes, schema names,
status distributions, timings, and summarized findings. I found no committed
raw corpus text, model prompts or completions, conversation titles, belief
values, claim values, private entity names, relationship labels, private
absolute paths, credentials, or cloud/egress workflow instructions.

This satisfies RFC 0024's artifact privacy rules for the current evidence
package.

### Info: Tier 2 remains bounded and RFC 0025-compliant

The Tier 2 artifact is explicitly a scaffold, caps future execution at
`--limit 500` or equivalent fixed bounded scope, preserves Tier 0/Tier 1
blockers, and states that it does not authorize full-corpus Phase 4. The
command-surface evidence preserves RFC 0025's absence of `engram phase4 run`.

## Next Validation Step

The next artifact should be a bounded evidence-fix report, not a promotion
report. It should initialize the project Python environment, run the Phase 4
pytest surface, execute live Tier 0 smoke, define and populate the RFC
0021-aligned human-label/entity-pair slice, collect live accept/reject/correct
and promote-to-pinned action evidence, address or explicitly decide the
projection/provenance gaps, and add realistic one-hop/two-hop CTE p50/p95
timing.

Only after that evidence-fix report should a bounded Tier 2 production
preflight be eligible. Full-corpus Phase 4 remains blocked until RFC 0024's
promotion criteria are satisfied with no unresolved human-checkpoint blocker.

## Evidence Artifacts

- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER0_SMOKE_REPORT.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER1_NONHUMAN_REPORT.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER2_PREFLIGHT_SCAFFOLD.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/FINDINGS_LEDGER.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/PROMOTION_SYNTHESIS.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/REVIEW_entity_quality.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/REVIEW_invariants.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/REVIEW_privacy_provenance.md`
