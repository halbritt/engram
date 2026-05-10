# RFC 0029 Bench Triage Workbench Implementation Runbook

This workflow builds, reviews, revises, and final-reviews the RFC 0029 Bench
Triage Workbench from Spec 0029.

## Objective

Implement the local-only bench review UI and CLI from
`docs/specs/0029-bench-triage-workbench-spec.md`.

## Process

1. Implement the workbench and publish `IMPLEMENTATION_HANDOFF.md`.
2. Run independent Claude, Codex, and Gemini implementation reviews.
3. Run adversarial usability review against the implemented surface.
4. Normalize findings into a ledger.
5. Synthesize accepted implementation deltas.
6. Apply accepted deltas.
7. Run final review.

## Privacy

Do not include private corpus excerpts, raw segment text, or raw claim text in
tracked artifacts. The implementation may read local scratch artifacts but must
store review state only in scratch SQLite and export redacted summaries.

## Completion Criteria

- CLI commands exist under `engram phase3 bench-review`.
- Local FastAPI/Jinja2 workbench exists under `src/engram/bench_review/`.
- Focused tests for loader, classification, storage, export, CLI, and web
  security pass.
- Implementation review reaches `accept` or `accept_with_findings`.

