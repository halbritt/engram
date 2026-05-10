# RFC 0029 Bench Triage Workbench Spec Runbook

This workflow turns RFC 0029 into a buildable implementation contract and
reviews it before code work starts.

## Objective

Produce an accepted spec at `docs/specs/0029-bench-triage-workbench-spec.md`
that a builder can implement without re-deriving contract details from the RFC
or review artifacts.

## Process

1. Draft or revise the spec and publish `SPEC_HANDOFF.md`.
2. Run independent Claude, Codex, and Gemini review lanes.
3. Run an adversarial usability review focused on residual cognitive overhead.
4. Normalize all findings into a ledger.
5. Synthesize accepted spec deltas.
6. Apply accepted deltas to the spec and RFC index.
7. Run final review.

## Privacy

Do not include private corpus excerpts, raw segment text, or raw claim text in
review prompts or tracked artifacts. The spec may define fields and paths, but
tracked artifacts must remain redacted.

## Completion Criteria

- Spec 0029 exists.
- RFC 0029 points at the accepted spec.
- Four review artifacts exist, including adversarial usability review.
- Findings ledger, synthesis, revision handoff, final review, and run summary
  exist under `docs/reviews/rfc0029-bench-triage-workbench-spec/`.
- The workflow validates with Striatum.

