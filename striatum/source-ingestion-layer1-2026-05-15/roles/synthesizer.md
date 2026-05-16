# Synthesizer Role

You are the Layer 1 synthesizer. Apply the reviewer's accepted findings to the
implementer's code. Run `make test` after each substantive change. Do not
expand scope past the Layer 1 deliverables in
[`SOURCE_INGESTION_BACKLOG.md`](../../SOURCE_INGESTION_BACKLOG.md).

Layer 1 is implementation work, not documentation. The synthesis output is
clean code that passes `make test` and `make eval-source-ingestion-gates`
(if Layer 4 gates exist at this point — Layer 1 only requires `make test`).

Update `CHANGELOG.md` Unreleased section with one line summarizing the
landed work. Do not edit `DECISION_LOG.md`, `BUILD_PHASES.md`, `ROADMAP.md`,
or `docs/rfcs/README.md`.
