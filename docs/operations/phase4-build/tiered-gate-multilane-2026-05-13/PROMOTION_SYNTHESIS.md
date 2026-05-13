---
schema_version: "striatum.synthesis.v1"
artifact_kind: "synthesis"
---

# Phase 4 Promotion Synthesis
author: operator [self-declared: phase4-promotion-synthesis-codex]

Status: synthesis
Date: 2026-05-13

## Recommendation

Promotion blocked pending implementation or evidence fixes.

This is the only promotion recommendation from this synthesis. Phase 4 should
not be promoted, and full-corpus Phase 4 remains blocked. The block is broader
than "pending human labels": RFC 0021 human-label evidence is a decisive Tier 1
gap, but the current evidence also lacks executable Tier 0 smoke results, live
review-action audit evidence, an executed Tier 2 preflight, and fixes or
explicit decisions for several Phase 4 projection/provenance gaps.

The Tier 2 artifact is a scaffold, not an authorization to run full-corpus Phase
4. A later bounded Tier 2 preflight may be considered only after the Tier 0 and
Tier 1 blockers below are resolved or explicitly carried forward by an operator
decision.

## Decisive Evidence

Tier 0 is not a pass. The Tier 0 report records favorable read-only schema
presence and command-shape evidence, but the project Python environment was
absent, the preferred pytest surface did not run, and no live
`make phase4-smoke LIMIT=25` write was performed.

Tier 1 is not a pass. The Tier 1 report is explicitly non-human evidence. It
shows useful structural facts such as status-aware `current_beliefs`, zero
duplicate active entity keys, zero duplicate active edges, bounded command
surface, and favorable read-only query timings at the current scale. Those
facts do not satisfy RFC 0024's human-label gates: same/different-entity
precision and recall, zero known false merges on a labeled set, false-split
reviewability, required predicate-shape coverage, and review-queue UX/action
evidence are all absent.

Tier 2 is not executed. The Tier 2 artifact provides a bounded
`--limit 500` preflight shape and correctly preserves the Tier 0 and Tier 1
blockers. It did not execute the production preflight, prove absence of
failed/in-flight Phase 4 jobs after completion, or collect post-run projection,
entity, review-action, and latency evidence.

The independent reviews agree on the gate state. The entity-quality review
finds the reports honest and well-redacted but non-promoting. The invariants
review finds no silent mutation or auto-promotion, but identifies unproven live
review actions and unresolved projection/provenance issues. The
privacy/provenance review finds the redaction boundary and full-corpus block
intact, while flagging the need for an operator decision or multi-lane re-review
before single-lane Tier evidence can support a promotion decision.

The findings ledger normalizes 18 findings: 2 critical, 4 high, 7 major,
3 medium, and 2 info. Findings P4-GATE-L001 through P4-GATE-L016 are promotion
blockers. P4-GATE-L017 and P4-GATE-L018 are positive boundary findings only.

## Decisive Gaps

The immediate blockers are:

1. Initialize the project Python environment, run the Phase 4 pytest surface,
   and execute live Tier 0 smoke.
2. Populate and report an RFC 0021-aligned human-label entity slice covering
   same/different entity labels, false merges, false splits, and the required
   predicate/stability shapes.
3. Collect live review-queue evidence across accept, reject, correct, and
   promote-to-pinned, including latency, `belief_audit` rows,
   `belief_review_actions` rows, correction captures, and queued reprocessing
   counts.
4. Verify `current_beliefs` lifecycle behavior beyond the current all-candidate
   live distribution, including provisional/accepted inclusion and rejection of
   closed, superseded, and historical rows.
5. Resolve or explicitly decide the implementation gaps around candidate-derived
   graph state labeling/filtering, pending-correction visibility, entity/edge
   reuse provenance, rejected-to-provisional lifecycle behavior, and append-only
   trigger preflight checks.
6. Run realistic synthetic 1-2 hop recursive CTE scale tests with p50/p95
   timing, separate from the current small active-edge timing.
7. Record an operator decision accepting single-lane Tier evidence for this gate
   or run a satisfactory multi-lane re-review.

## Positive Evidence To Preserve

The reports maintain the RFC 0024 redaction boundary: they use aggregate
counts, command shapes, status distributions, schema names, and timing
summaries while omitting corpus text, prompts, completions, titles, belief
values, claim values, entity names, relationship labels, private paths, and
unredacted row ids.

The command surface remains bounded and phase-scoped. The evidence preserves
RFC 0025's absence of `engram phase4 run`, keeps generic pipeline paths
fail-closed by dry-run inspection, and keeps future Phase 4 execution constrained
to explicit bounded verbs.

The inspected implementation is directionally aligned with D017, D044, and
D052: corrections are represented as raw captures, Phase 3 does not
auto-promote to `accepted`, and changed accept/reject/pin transitions route
through the audited transition API. These are favorable code-shape findings,
not yet live Tier 2 proof.

## Required Next Gate State

The next acceptable gate artifact is not a promotion report. It should be a
bounded evidence-fix report that:

- shows the initialized environment and successful Phase 4 pytest execution;
- records a live Tier 0 smoke result;
- reports the labeled Tier 1 entity/review substrate or explicitly marks it as
  still blocking;
- demonstrates live review actions and audit completeness;
- addresses the projection/provenance implementation gaps or records the
  operator decision that carries them forward;
- preserves aggregate-only redaction; and
- keeps any production preflight bounded to `--limit 500` or an equivalent
  deterministic fixed slice.

Only after that bounded evidence-fix report should a Tier 2 production
preflight be treated as eligible. Full-corpus Phase 4 remains blocked until RFC
0024's promotion criteria are satisfied, including Tier 0 and Tier 1 passing
with no blocking findings and Tier 2 completing with no failed jobs or
human-checkpoint blocker.

## Evidence Artifacts

- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER0_SMOKE_REPORT.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER1_NONHUMAN_REPORT.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/TIER2_PREFLIGHT_SCAFFOLD.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/REVIEW_entity_quality.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/REVIEW_invariants.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/REVIEW_privacy_provenance.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/FINDINGS_LEDGER.md`
