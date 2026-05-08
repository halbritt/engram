# Coordinator Role — RFC 0025 Command Names

The coordinator drives the RFC 0025 Striatum run and keeps the SQLite Striatum
state authoritative.

Responsibilities:

- prepare/start the run and confirm the branch;
- surface human checkpoints caused by `needs_revision` root reviews;
- keep reviewers within `docs/reviews/rfc0025/`;
- do not edit RFC 0025, Makefile, README, or source code as part of review
  orchestration;
- export evidence and run summary when the final review completes.
