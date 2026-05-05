# P024B: Review Phase 3 Spec Synthesis After Codex Rejection

> Prompt ordinal: P024B. Introduced: 2026-05-05. Source commit: pending.

## Role

Preferred model: Codex GPT-5.5.

You are the same-model re-reviewer for the P022 Codex `reject_for_revision`
verdict. Your job is to verify that P024 synthesis and the patched canonical
spec actually address the rejection findings before any build prompt is
allowed to proceed.

## Wait For

Wait until:

```text
docs/reviews/phase3/markers/04_SPEC_SYNTHESIS.ready.md
```

exists.

## Read First

1. `docs/reviews/phase3/markers/04_SPEC_SYNTHESIS.ready.md`
2. `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md`
3. `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_FINDINGS_LEDGER_2026_05_05.md`
4. `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_REVIEW_codex_gpt_5_5_2026_05_05.md`
5. `docs/claims_beliefs.md`
6. `DECISION_LOG.md`
7. `BUILD_PHASES.md`
8. `ROADMAP.md`
9. `SPEC.md`
10. `docs/process/multi-agent-review-loop.md`
11. `docs/process/phase-3-agent-runbook.md`

## Review Lens

Focus on whether the P022 Codex rejection was materially resolved. Pay special
attention to:

- S-F001: `valid_to` / lifecycle semantics.
- S-F002: active claim set across re-extraction and vanished claims.
- S-F003: multi-valued, scoped-current, and event predicates becoming false
  contradictions.
- S-F005: enforceable audit-on-update mechanism.
- S-F011: predicate vocabulary and `object_json` schema/testability.

You may include new blockers only if the synthesis introduced a fresh
contradiction or made a previously non-blocking risk implementation-blocking.
This is not a second full architecture review.

## Task

Create:

```text
docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_REVIEW_codex_gpt5_5_2026_05_05.md
```

If that file already exists from an earlier blocked review, preserve it and
write a new rerun review file instead:

```text
docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_REVIEW_codex_gpt5_5_rerun_<YYYYMMDDTHHMMSSZ>.md
```

Use this format:

- Summary verdict: `accept`, `accept_with_findings`, or `reject_for_revision`.
- A short table mapping the original Codex rejection findings / ledger IDs to
  `resolved`, `partially_resolved`, or `unresolved`.
- Remaining blocking findings, if any, ordered by severity.
- Non-blocking follow-up findings, if any.
- Explicit statement whether `docs/claims_beliefs.md` is safe to hand to P025.

## Gate Behavior

If your verdict is `accept` or `accept_with_findings`, write:

```text
docs/reviews/phase3/markers/04_SPEC_SYNTHESIS_REVIEW_codex_gpt5_5.ready.md
```

The marker must include your verdict, review file path, files read, and
verification performed.

If your verdict is `reject_for_revision`, do **not** write the ready marker.
Instead write:

```text
docs/reviews/phase3/markers/04_SPEC_SYNTHESIS_REVIEW_codex_gpt5_5.blocked.md
```

The blocked marker must include the review file path and the exact blockers
that must be fixed before re-running this prompt. It must also state:

```text
Human intervention required before continuing Phase 3.
```

The tmux build prompt waits for the `.ready.md` marker, so a blocked marker
intentionally stops the run. Do not attempt an automatic repair loop after a
blocked marker; the owner decides whether to revise the synthesis, accept risk,
or redirect the phase.

## Constraints

- Do not edit `docs/claims_beliefs.md`.
- Do not edit `DECISION_LOG.md`.
- Do not write code.
- Do not create or execute the build prompt.
- Do not call external services.
