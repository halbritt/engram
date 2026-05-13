---
schema_version: "striatum.finding.v1"
artifact_kind: "finding"
verdict_intent: "accept_with_findings"
severity: "medium"
tags: ["phase4", "evidence-fix", "rfc-0024", "rfc-0021", "rfc-0025", "focused-review"]
---

# Phase 4 Evidence-Fix Scaffold Focused Review
author: operator [self-declared: focused-claude-2]

Status: accept_with_findings
Date: 2026-05-13

RFC refs:
  - RFC-0024
  - RFC-0021
  - RFC-0025
  - RFC-0032

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

## Scope

This is a focused re-review of the Phase 4 evidence-fix scaffold at
`docs/operations/phase4-build/evidence-fix-2026-05-13/EVIDENCE_FIX_REPORT.md`.
It assesses only boundedness, privacy/redaction discipline, evidence
sufficiency against the carried Phase 4 gate findings, and clarity of Tier 0 /
Tier 1 / Tier 2 eligibility and non-promoting gate language.

This review does not run commands, does not authorize any full-corpus Phase 4
work, does not edit the scaffold, and does not edit any source code or
canonical doc. Per the assigned write scope it only publishes this artifact
under `docs/operations/phase4-build/evidence-fix-2026-05-13/`.

## Verdict

Accept the scaffold with findings. The scaffold is correctly non-promoting,
preserves the RFC 0024 redaction boundary, keeps Tier 0 / Tier 1 / Tier 2
execution bounded, and carries the prior blocking findings forward without
laundering them. Two evidence-sufficiency gaps and one provenance gap should
be tightened before the loop is executed.

This acceptance is acceptance of the scaffold only. It is not Phase 4
promotion, is not a Tier 0 / Tier 1 / Tier 2 pass, and does not authorize any
full-corpus Phase 4 work. The scaffold remains a planning artifact for a
future bounded evidence-fix loop.

## Inputs Reviewed

- `docs/operations/phase4-build/evidence-fix-2026-05-13/EVIDENCE_FIX_REPORT.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/FINAL_GATE_REVIEW.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/PROMOTION_SYNTHESIS.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/FINDINGS_LEDGER.md`
- `docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md`
- `docs/rfcs/0021-gold-set-interview-curation.md` (relevant sections)
- `docs/reviews/rerun-backlog-2026-05-13/BACKLOG.md`
- `striatum/rerun-backlog-focused-reviews-2026-05-13/roles/reviewer.md`

## Findings

### Info: Non-promoting language is correctly load-bearing

The scaffold opens with an explicit boundary statement: it does not promote
Phase 4, does not authorize full-corpus Phase 4, and caps future Tier 2 work
at `--limit 500` or an equivalent deterministic fixed slice. The result
template enumerates four exit labels (`blocked`, `findings`,
`ready-for-tier2-bounded-preflight`, `human-checkpoint`) and adds a guard that
`promotion` is unavailable unless RFC 0024 promotion criteria are all
satisfied by later evidence and a final committed review says so.

The "Carried Findings" section preserves P4-GATE-L001 through P4-GATE-L016 as
open blockers and explicitly states that the positive boundary findings
P4-GATE-L017 and P4-GATE-L018 are constraints to preserve, not promotion
authority. This matches the FINDINGS_LEDGER disposition and prevents
re-laundering positive boundaries into permission.

No blocker.

### Info: Privacy and redaction boundary is preserved

Committed outputs are restricted to aggregate counts, command shapes, test
outcomes, timing summaries, schema relation names, redacted identifiers, and
finding ids. The scaffold explicitly excludes raw corpus text, prompts,
completions, conversation titles, belief values, claim values, entity names,
relationship labels, private values, credentials, and home-directory paths.

The scaffold further routes item-level material to ignored scratch: RFC 0021
slice rows stay local; review-action notes, correction text, belief values,
entity names, and raw ids are excluded from the committed report; pytest
output is summarized by failure class with raw logs kept in ignored
diagnostics when they could carry private environment details. These rules
match RFC 0024's artifact privacy rules and the prior gate's positive
boundary finding (P4-GATE-L017).

No blocker.

### Info: Boundedness is correctly enforced

Tier 0 is capped at `make phase4-smoke LIMIT=25` (within RFC 0024's 25-50
recommended scope) with an equivalent direct command shape. Tier 1's RFC
0021-aligned slice targets about 200 human-reviewed entity mentions matching
RFC 0024 and O003, with explicit strata stratification and counts. Tier 2 is
capped at `engram phase4 build-entities --limit 500` or the equivalent
`make phase4-build-entities LIMIT=500`.

The forbidden-command list explicitly excludes `engram phase4 run`,
unbounded `engram phase4 build-entities`, unbounded Make targets, generic
`pipeline` commands, and any hosted inference or network egress path. This
preserves the RFC 0025 phase-scoped command surface and the P4-GATE-L018
positive boundary finding.

No blocker.

### Info: Evidence-to-finding mapping is mostly complete

The scaffold establishes coverage for almost every carried blocker:

- P4-GATE-L002 maps to the environment / pytest section.
- The Tier 0 executable smoke gap maps to the bounded smoke section.
- P4-GATE-L003, L004, L011 map to the RFC 0021-aligned entity-pair slice.
- P4-GATE-L005, L006 map to the review-action evidence section.
- P4-GATE-L007 through L015 map to the projection / provenance gap ledger,
  each with a "resolve by evidence, requires code/spec change, or owner
  decision" disposition.
- P4-GATE-L016 maps to a multi-lane review or owner provenance decision on
  the evidence-fix result itself.

The disposition language ("evidence", "requires code/spec change", or "owner
decision") matches the prior gate's findings-not-promotion posture and does
not let unresolved gaps silently disappear.

No blocker.

### Major: Tier 2 eligibility does not gate on P4-GATE-L008 / L010 resolution

The "Tier 2 Guardrail" allows `engram phase4 build-entities --limit 500` after
Tier 0 and Tier 1 pass or carry unresolved blockers forward. P4-GATE-L008
records that the entity builder consumes `current_beliefs` rows in
`candidate`, `provisional`, and `accepted` status without carrying source
belief status into entity / edge rows, and P4-GATE-L010 records that the
reuse path may not append contributing `source_belief_ids`,
`source_claim_ids`, or `evidence_ids`.

If Tier 2 runs at `--limit 500` before L008 and L010 are explicitly resolved
or accepted by owner decision, the bounded preflight will write production
entity / edge rows whose status provenance and reuse provenance remain
debated. The scaffold lists "no entity or edge row loses D021
provenance/version metadata" in the Tier 2 prove list, but this is a
post-hoc structural check that does not by itself answer L008 (graph rows
derived from candidate beliefs without status propagation) or L010 (reuse
path not appending provenance arrays).

Recommendation when the loop executes:

- treat Tier 2 as ineligible until L008 has an owner decision recorded
  (either "build is filtered to intended statuses" or "graph carries source
  belief status and downstream consumers handle it") and L010 has an owner
  decision recorded (either "arrays are seed provenance only" or "reuse path
  records append-only reuse evidence");
- if either decision selects an implementation change, treat Tier 2 as
  ineligible until that change lands and is exercised in Tier 0 / Tier 1
  evidence; the scaffold cannot edit code, so it should record this as a
  `human-checkpoint` carry rather than promote to
  `ready-for-tier2-bounded-preflight`.

This is a major finding because Tier 2 even at `--limit 500` writes to the
production database surface, and shipping it before resolving L008 / L010
would commit ambiguous graph provenance into the real entity / edge tables.

### Major: Single-lane evidence-fix outputs reopen P4-GATE-L016 for the loop's products

The scaffold itself is honestly bylined as a single-lane Codex artifact, and
it correctly carries P4-GATE-L016 forward as an open finding. It says
"Resolve P4-GATE-L016 with a multi-lane review of the evidence-fix result or
an explicit owner provenance decision."

That clause addresses the scaffold but is silent on the lane shape of the
evidence-fix Tier 0 / Tier 1 / Tier 2 reports the loop is expected to
produce. If those reports are produced single-lane and only the synthesis is
reviewed multi-lane, the privacy / provenance review's underlying concern -
single-lane Tier evidence supporting a tiered gate decision - recurs at the
same severity. The RFC 0032 audit context makes this concrete: single-lane
Codex Tier evidence is exactly what triggered the prior provenance finding.

Recommendation when the loop executes:

- either produce each Tier evidence report through a multi-lane workflow
  (parallel evidence collection + cross-lane attestation) and record the
  workflow id, or record an explicit operator deviation in
  `DECISION_LOG.md` that accepts single-lane evidence collection for this
  bounded loop only;
- the multi-lane review of the synthesis is necessary but not by itself
  sufficient if the Tier evidence files were produced single-lane and are
  individually relied on by downstream decisions.

This is a major finding because P4-GATE-L016 is already a promotion-blocking
concern, and a quiet recurrence of the same single-lane posture would
re-introduce the issue at the layer that actually carries the metrics.

### Medium: `make install` failure modes are not surfaced as decision points

The environment section uses `test -x .venv/bin/python || make install` as
the gate to running pytest. `make install` can fail in ways that are not
Phase 4 specific (Python toolchain availability, native build failure,
network restrictions, lock-file drift). The scaffold tells the loop to
summarize pytest failure classes without pasting private stack traces, but
does not call out that an `install` failure should classify as a separate
finding kind ("environment unavailable") rather than a Phase 4 evidence
failure.

Recommendation: add an explicit handling clause that an `install` or Python
toolchain failure should be reported under an `environment_unavailable`
finding class and classifies the loop result as `blocked` rather than
`findings`. This protects against later confusion between "Phase 4 evidence
is failing" and "the Phase 4 evidence loop could not start".

Medium because misclassification only delays decisions; it does not bypass
the boundary.

### Medium: Tier 1 eligibility ordering is implicit

The scaffold's "Live Tier 0 Smoke Plan" makes Tier 0 explicitly conditional
on the pytest surface passing. The RFC 0021-aligned slice and review-action
sections do not state an analogous ordering: a reader could interpret them
as runnable in parallel with Tier 0.

Recommendation: state explicitly that Tier 1 evidence (RFC 0021 slice +
review actions) is eligible only after Tier 0 smoke is recorded as a pass or
is classified `findings` with a clear unrelated-to-Tier-1 disposition. This
matches the dependency in the FINAL_GATE_REVIEW and PROMOTION_SYNTHESIS.

Medium because the current `Carried Findings` priority order partially
encodes the same ordering, so this is documentation tightening, not a
silent failure path.

### Medium: RFC 0021 candidate-pool snapshot caveat is not carried

RFC 0021 (the implementation contract for the gold-label substrate) states
that `candidate_pool_snapshot_id` is currently an opaque session-instance
tag, not a replayable candidate-pool snapshot. The scaffold relies on
`engram phase3 interview` commands and the gold-label substrate to build the
Tier 1 slice but does not mention this limitation.

If the Tier 1 slice is later expected to be exactly replayable by snapshot
id, the loop will discover the gap mid-execution. The simpler fix is to
state in the scaffold that the loop should capture the strata weights,
seeds, and session ids it used and not rely on `candidate_pool_snapshot_id`
to reproduce the candidate pool.

Medium because it is a reproducibility caveat rather than a privacy or
boundary breach.

### Info: Tier 0 / Tier 1 / Tier 2 eligibility is otherwise well-bounded

Excluding the L008 / L010 dependency in the major finding above, the
scaffold's tier eligibility language is clear:

- Tier 0 is eligible after pytest passes or after failures are explicitly
  classified as unrelated to Phase 4 gate behavior.
- Tier 1 RFC 0021 commands are explicitly capped at the Tier 1 ceiling for
  export and forbid copying higher-tier exports into committed reports.
- Tier 2 remains explicitly ineligible until Tier 0 and Tier 1 evidence pass
  or unresolved blockers are explicitly carried forward.

The scaffold also states that full-corpus Phase 4 remains blocked
independently of the loop's result, matching RFC 0024's promotion criteria
and D077.

No blocker.

## Recommendation

Accept the scaffold as a non-promoting, bounded, privacy-preserving evidence
plan. Before the loop executes, fold the following into the scaffold or into
the loop's pre-flight notes (recorded by an operator, since this review's
write scope cannot edit the scaffold):

1. Gate Tier 2 eligibility on explicit owner decisions for P4-GATE-L008 and
   P4-GATE-L010 (status propagation and reuse provenance) before any
   `--limit 500` build-entities run, and treat the loop as
   `human-checkpoint` rather than `ready-for-tier2-bounded-preflight` when
   those decisions are not in hand.
2. Require multi-lane production of the Tier 0, Tier 1, and Tier 2 evidence
   reports, or record an explicit operator deviation accepting single-lane
   evidence for this bounded loop only, before relying on those reports for
   any later promotion decision.
3. Classify `make install` or Python toolchain failures as a distinct
   `environment_unavailable` finding kind that maps to a `blocked` loop
   result.
4. State the Tier 1 ordering rule explicitly: RFC 0021 slice and
   review-action evidence are eligible only after Tier 0 passes or is
   classified as unrelated.
5. Carry the RFC 0021 `candidate_pool_snapshot_id` reproducibility caveat
   into the slice-construction notes so the loop captures seeds, strata
   weights, and session ids deliberately.

The next executable artifact under
`docs/operations/phase4-build/evidence-fix-2026-05-13/` should still be a
bounded evidence-fix report, not a promotion report, and should preserve
every redaction and boundary clause the scaffold already encodes.

## Evidence Artifacts

- `docs/operations/phase4-build/evidence-fix-2026-05-13/EVIDENCE_FIX_REPORT.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/FINAL_GATE_REVIEW.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/PROMOTION_SYNTHESIS.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/FINDINGS_LEDGER.md`
- `docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md`
- `docs/rfcs/0021-gold-set-interview-curation.md`
- `docs/reviews/rerun-backlog-2026-05-13/BACKLOG.md`
