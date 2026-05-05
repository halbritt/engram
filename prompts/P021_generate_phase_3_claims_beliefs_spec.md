# P021: Generate Phase 3 Claims And Beliefs Spec

> Prompt ordinal: P021. Introduced: pending first commit. Source commit: pending.

## Role

Preferred model: Claude Opus 4.7.

You are the Phase 3 architecture author. Your job is to turn RFC 0011 into a
binding implementation spec, without writing code and without starting the
Phase 3 build.

## Wait For

No marker is required. Start only from a clean, current `master`.

## Read First

1. `README.md`
2. `HUMAN_REQUIREMENTS.md`
3. `DECISION_LOG.md`
4. `BUILD_PHASES.md`
5. `ROADMAP.md`
6. `SPEC.md`
7. `docs/schema/README.md`
8. `docs/segmentation.md`
9. `docs/rfcs/0011-phase-3-claims-beliefs.md`
10. `docs/process/phase-3-agent-runbook.md`
11. `docs/reviews/v1/PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04.md`
12. `docs/reviews/v1/PHASE_2_QWEN27B_UMBRELLA_AB_2026_05_05.md`

## Task

Create `docs/claims_beliefs.md`.

The spec must settle the implementation contract between RFC 0011 and the build
prompt. It should be specific enough that a fresh Codex implementation context
can build Phase 3 without reopening architecture.

Required sections:

- Purpose and status.
- Phase 3 scope and non-goals.
- Inputs: active Phase 2 AI-conversation segments only.
- Stage A: claim extraction contract.
- Stage B: deterministic belief consolidation contract.
- Tables and columns for `claim_extractions`, `claims`, `beliefs`,
  `belief_audit`, and `contradictions`.
- Predicate vocabulary for V1.
- `object_text` vs `object_json` rules with examples.
- Evidence rules, including `evidence_message_ids`, `evidence_ids`, and
  whether empty evidence is ever allowed.
- Time semantics: `observed_at`, `valid_from`, `valid_to`, `recorded_at`,
  `extracted_at`.
- Value equality and grouping rules.
- Contradiction detection and auto-resolution rules.
- Privacy-tier propagation and reclassification behavior.
- Versioning and re-derivation behavior.
- Local LLM request profile and structured-output schema expectations.
- Failure diagnostics and resumability.
- CLI/operator expectations.
- Tests and acceptance criteria.
- Explicit deferrals to Phase 4 / Phase 5.
- Open owner checkpoints, if any remain.

Also update `docs/README.md` to list `docs/claims_beliefs.md` under Current
Design.

## Constraints

- No cloud APIs, hosted services, telemetry, or external persistence.
- Do not weaken raw immutability, provenance, auditability, or local-first.
- Do not implement code.
- Do not create the Phase 3 build prompt yet.
- Do not update `DECISION_LOG.md` unless a decision is already unambiguous and
  required to make the spec internally coherent. Prefer leaving decision
  promotion to P024.

## Output

Write:

- `docs/claims_beliefs.md`
- updated `docs/README.md`
- marker `docs/reviews/phase3/markers/01_SPEC_DRAFT.ready.md`

The marker must list files changed and any unresolved questions reviewers
should focus on.

