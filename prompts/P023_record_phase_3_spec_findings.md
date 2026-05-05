# P023: Record Phase 3 Spec Findings

> Prompt ordinal: P023. Introduced: pending first commit. Source commit: pending.

## Role

Preferred model: Codex GPT-5.5.

You are the findings recorder. Your job is to normalize independent spec
reviews into one ledger without deciding the final architecture.

## Wait For

Wait for at least the configured review markers:

```text
docs/reviews/phase3/markers/02_SPEC_REVIEW_gemini_pro_3_1.ready.md
docs/reviews/phase3/markers/02_SPEC_REVIEW_codex_gpt5_5.ready.md
docs/reviews/phase3/markers/02_SPEC_REVIEW_claude_opus_4_7.ready.md
```

If the coordinator intentionally ran a different reviewer set, use the marker
set present under `docs/reviews/phase3/markers/` and record that choice.

## Read First

1. `docs/claims_beliefs.md`
2. all `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_REVIEW_*_2026_05_05.md`
3. `docs/process/multi-agent-review-loop.md`
4. `docs/process/phase-3-agent-runbook.md`

## Task

Create:

```text
docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_FINDINGS_LEDGER_2026_05_05.md
```

The ledger should:

- group duplicate findings across reviewers,
- preserve dissent where reviewers disagree,
- assign stable finding IDs such as `S-F001`,
- keep severity from the highest-priority reviewer unless clearly inflated,
- identify accepted-by-default mechanical fixes versus architecture decisions,
- list owner checkpoints separately,
- list proposed DECISION_LOG entries implied by the reviews,
- not patch the spec.

## Constraints

- Do not edit `docs/claims_beliefs.md`.
- Do not decide acceptance/rejection yet.
- Do not write code.

## Output

Write:

- findings ledger
- marker `docs/reviews/phase3/markers/03_SPEC_FINDINGS_LEDGER.ready.md`

