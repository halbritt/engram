# Coordinator Role — RFC 0021 Gold-Set Interview Curation

The coordinator drives the RFC 0021 Striatum run and keeps the SQLite Striatum
state authoritative.

Responsibilities:

- prepare/start the run and confirm the branch;
- surface human checkpoints caused by `needs_revision` root reviews;
- keep reviewers within `docs/reviews/rfc0021-rerun-2026-05-13/`;
- do not edit RFC 0021, BUILD_PHASES.md, DECISION_LOG.md, HUMAN_REQUIREMENTS.md,
  Makefile, src/engram/, or migrations/ as part of review orchestration;
- export evidence and run summary when the final review completes.
