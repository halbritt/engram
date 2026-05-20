# Daemon Core

Implement the local broker daemon loop for RFC 0055 approved-grant
materialization.

Required behavior:

- add a daemon module under `src/engram/`;
- poll `process_approved_grounding_grants` through an injected connection
  factory;
- commit one batch per iteration;
- support `limit`, `interval_seconds`, `target_adapter`, `max_iterations`,
  injected sleep, and optional stop event;
- use a PostgreSQL transaction advisory lock per iteration;
- return sanitized JSON-compatible summaries;
- add deterministic unit tests with monkeypatched materialization and no live
  provider calls.

Publish `docs/reviews/entity-grounding-broker-daemon-2026-05-19/DAEMON_CORE_HANDOFF.md`.
