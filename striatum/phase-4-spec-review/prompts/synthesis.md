# Phase 4 Synthesis — Task

Read `PHASE_4_SPEC_FINDINGS_LEDGER.md` plus the Phase 4 inputs
(`BUILD_PHASES.md`, `HUMAN_REQUIREMENTS.md`).

Produce a synthesis that recommends one of these outcomes:

1. **Author a Phase 4 RFC.** Use this when the ledger surfaces enough open
   design questions that a proposal-stage RFC is needed before any
   implementation spec.
2. **Author a Phase 4 implementation spec.** Use this when the ledger
   surfaces only minor findings and the BUILD_PHASES Phase 4 row plus
   existing decisions are coherent enough for direct handoff.
3. **Revise the Phase 4 row in `BUILD_PHASES.md` before any spec.** Use
   this when the row itself has gaps the ledger highlights.
4. **Pause and resolve a blocker.** Use this when one or more `blocking`-
   severity findings require human decision before any spec proceeds.

## Output

Write to `docs/reviews/phase4/PHASE_4_SPEC_SYNTHESIS.md`:

```md
# Phase 4 Build-Spec Synthesis

Status: synthesis
Date: <YYYY-MM-DD>
RFC refs: ...
Decision refs: ...
Phase refs: PHASE-0004

## Findings outcome

| ID  | Outcome  | Reason |
|-----|----------|--------|
| F001 | accepted | <one-line reason>  |
| F002 | deferred | <one-line reason>  |
| F003 | rejected | <one-line reason>  |
[...]

## Open decisions

### O###1 — <one-line question>
- Option A — <one-line description>
- Option B — <one-line description>
- Recommended: <A | B>
- Rationale: <one paragraph>

[...]

## Recommendation

<one of: author-rfc | author-spec | revise-build-phases | pause-and-resolve>

<short paragraph explaining the choice. If the recommendation is
"author a spec," include a one-paragraph sketch of what the spec covers:
entity tables, view definition, review-queue surface, query patterns.>

## Risks the synthesis carries

- <each place the synthesis chose a resolution the ledger did not
  unambiguously support>
```

Do not modify the ledger or any review file. Do not edit `BUILD_PHASES.md`,
`DECISION_LOG.md`, or any RFC.
