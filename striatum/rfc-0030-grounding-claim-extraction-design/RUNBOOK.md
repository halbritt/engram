# RFC 0030 Public-Dataset Entity Grounding Design Runbook

This workflow drives a multi-agent design review of
`docs/rfcs/0030-public-dataset-entity-grounding.md` per
`docs/process/multi-agent-review-loop.md`, then revises the RFC and final-reviews
the revision.

## Objective

Decide whether RFC 0030 is ready for promotion to a spec, with explicit
positions taken on every design choice (D-A through D-H) and every open
question (Q1 through Q7).

## Process

1. Eight independent review jobs fan out in parallel:
   - Three generic reviews — `review_claude` (privacy/local-first lens),
     `review_codex` (implementation feasibility lens), `review_gemini`
     (operator workflow lens).
   - Five adversarial reviews — `review_usability_adversary`,
     `review_privacy_adversary`, `review_schema_adversary`,
     `review_eval_adversary`, `review_cost_adversary`.
2. `findings_ledger` normalizes all eight reviews into one ledger.
3. `revision_synthesis` decides accept / reject / defer per finding and
   takes a position on every D-A..D-H choice and Q1..Q7 question.
4. `apply_findings` revises the RFC in place; publishes a revision handoff.
5. `final_review` audits the revised RFC against the ledger, synthesis, and
   handoff. Verdict gates promotion to spec.

## Privacy

Do not include private corpus excerpts, raw segment text, or raw claim text in
any tracked artifact. The RFC is about extraction quality on user data — the
review must not leak that data through review prose.

## Completion criteria

- All eight review jobs complete with explicit verdicts.
- `FINDINGS_LEDGER.md` exists with cross-lane normalization.
- `REVISION_SYNTHESIS.md` takes positions on all D-A..D-H and Q1..Q7.
- `REVISION_HANDOFF.md` shows section / prior / new text per change.
- `FINAL_REVIEW.md` reaches `accept` or `accept_with_findings`.
- RFC 0030's status moves from `proposal` toward `promoted` (the actual
  status flip happens in the spec-authoring run).

## Promotion path

Per the RFC's own promotion path:

1. Design review (this run).
2. Spec authoring (next run, conditional on accept).
3. 100-segment bench gate (RFC 0017 re-extraction discipline).
4. Implementation (only if bench shows the predicted improvement).
