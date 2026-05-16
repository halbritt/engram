# Layer 1 Synthesis Prompt

Apply the accepted review findings to the implementation. Run
`make test` after each substantive change.

Inputs:

- The implementer's code (already in the tree).
- `docs/reviews/source-ingestion-layer1-2026-05-15/REVIEW.md`.
- The Layer 1 spec in
  [`SOURCE_INGESTION_BACKLOG.md`](../../SOURCE_INGESTION_BACKLOG.md).

Tasks:

1. Apply every accepted finding.
2. Run `make test`. If it fails, fix and re-run.
3. Update `CHANGELOG.md` Unreleased with one line per
   substantive landed deliverable.
4. Write a short synthesis report at
   `docs/reviews/source-ingestion-layer1-2026-05-15/SYNTHESIS_NOTES.md`
   naming the findings applied, the findings deferred (with reason),
   and the final test outcome.

Do not start the synthesis report with a markdown `Author:` line;
use `Lane:` and `Role:` instead.

Do not edit `DECISION_LOG.md`, `BUILD_PHASES.md`, `ROADMAP.md`, or
`docs/rfcs/README.md`.
