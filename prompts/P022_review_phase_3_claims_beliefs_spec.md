# P022: Review Phase 3 Claims And Beliefs Spec

> Prompt ordinal: P022. Introduced: pending first commit. Source commit: pending.

## Role

Preferred models: Gemini Pro 3.1, Codex GPT-5.5, and Claude Opus 4.7 in fresh
contexts. Run one reviewer per tmux pane/session. Each reviewer writes a unique
review file.

You are an adversarial reviewer of `docs/claims_beliefs.md`. Do not edit the
spec directly.

## Wait For

Wait until:

```text
docs/reviews/phase3/markers/01_SPEC_DRAFT.ready.md
```

exists.

## Read First

1. `docs/reviews/phase3/markers/01_SPEC_DRAFT.ready.md`
2. `docs/claims_beliefs.md`
3. `docs/rfcs/0011-phase-3-claims-beliefs.md`
4. `README.md`
5. `HUMAN_REQUIREMENTS.md`
6. `DECISION_LOG.md`
7. `BUILD_PHASES.md`
8. `ROADMAP.md`
9. `SPEC.md`
10. `docs/schema/README.md`
11. `docs/segmentation.md`
12. `docs/process/multi-agent-review-loop.md`

## Review Lens By Model

- Gemini Pro 3.1: broad cross-document consistency, missing cases, privacy and
  local-first drift, unresolved open questions hidden as decisions.
- Codex GPT-5.5: schema feasibility, migration/testability, code boundaries,
  operator flow, failure modes, and whether the spec can become a build prompt.
- Claude Opus 4.7 fresh context: architecture coherence, temporal semantics,
  evidence/audit model, false-precision risks, and human-review boundaries.

## Task

Write findings under:

```text
docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_REVIEW_<model_slug>_2026_05_05.md
```

Use this format:

- Summary verdict: `accept`, `accept_with_findings`, or `reject_for_revision`.
- Findings ordered by severity.
- For each finding: priority `P0`-`P3`, affected file/section, issue,
  consequence, and proposed fix.
- Open questions for the owner.
- Test or acceptance-criteria gaps.
- Any places where the spec contradicts RFC 0011 or should intentionally
  supersede it.

## Constraints

- Do not edit `docs/claims_beliefs.md`.
- Do not write code.
- Do not start the build prompt.
- Do not call external services.

## Output

Write:

- review file under `docs/reviews/phase3/`
- marker `docs/reviews/phase3/markers/02_SPEC_REVIEW_<model_slug>.ready.md`

The marker must include your model slug and review file path.

