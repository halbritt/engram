# RFC 0029 Bench Triage Workbench Design Runbook

This workflow drafts, reviews, revises, and final-reviews RFC 0029: Bench
Triage Workbench.

## Objective

Produce an accepted design artifact for a much friendlier local UI that lets the
Engram operator validate extraction and re-extraction benchmark deltas without
reading dense scratch Markdown reports.

## Process

1. Draft or revise `docs/rfcs/0029-bench-triage-workbench.md` and publish
   `docs/reviews/rfc0029-bench-triage-workbench-design-2026-05-13/DESIGN_HANDOFF.md`.
2. Run independent Claude, Codex, and Gemini review lanes.
3. Run an additional adversarial usability review focused on whether the UI
   actually reduces cognitive load for the owner.
4. Normalize all findings into a ledger.
5. Synthesize accepted deltas.
6. Apply accepted deltas to the RFC and README index.
7. Run final review.

## Privacy

Do not include private corpus excerpts, raw segment text, or raw claim text in
review prompts or tracked artifacts. The RFC may reference benchmark metrics and
artifact paths, but tracked design artifacts must remain redacted.

## Completion Criteria

- RFC 0029 exists and is indexed.
- Four review artifacts exist, including adversarial usability review.
- Findings ledger, synthesis, revision handoff, final review, and run summary
  exist under `docs/reviews/rfc0029-bench-triage-workbench-design-2026-05-13/`.
- The workflow validates with Striatum.
