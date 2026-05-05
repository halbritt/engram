# P024: Synthesize Phase 3 Spec Findings

> Prompt ordinal: P024. Introduced: pending first commit. Source commit: pending.

## Role

Preferred model: Claude Opus 4.7 for judgment-heavy synthesis, with Codex
GPT-5.5 for patch execution if needed.

You are the spec synthesis owner. Your job is to accept, modify, defer, or
reject findings and update the binding Phase 3 spec accordingly.

## Wait For

Wait until:

```text
docs/reviews/phase3/markers/03_SPEC_FINDINGS_LEDGER.ready.md
```

exists.

## Read First

1. `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_FINDINGS_LEDGER_2026_05_05.md`
2. all spec review files under `docs/reviews/phase3/`
3. `docs/claims_beliefs.md`
4. `docs/rfcs/0011-phase-3-claims-beliefs.md`
5. `DECISION_LOG.md`
6. `BUILD_PHASES.md`
7. `ROADMAP.md`
8. `SPEC.md`
9. `docs/process/multi-agent-review-loop.md`

## Task

Create:

```text
docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md
```

Then apply accepted deltas to:

- `docs/claims_beliefs.md`
- `DECISION_LOG.md` for binding architecture decisions
- `BUILD_PHASES.md`, `ROADMAP.md`, or `SPEC.md` only if sequencing or canonical
  summaries need updates

The synthesis must include:

- accepted findings,
- accepted-with-modification findings,
- deferred findings and revisit trigger,
- rejected findings and reason,
- owner checkpoints,
- exact files changed,
- whether `docs/claims_beliefs.md` is now build-ready.

## Constraints

- Do not write implementation code.
- Do not create or execute the build prompt.
- Keep RFC 0011 as historical proposal context; do not rewrite it unless a
  direct contradiction would mislead future agents.

## Output

Write:

- synthesis document
- patched canonical/spec docs as needed
- marker `docs/reviews/phase3/markers/04_SPEC_SYNTHESIS.ready.md`

