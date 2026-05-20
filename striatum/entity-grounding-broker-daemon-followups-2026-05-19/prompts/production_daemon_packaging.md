# Production Daemon Packaging

Document local-only packaging for the grounding broker daemon.

Required outcome:

- Add `docs/runbooks/grounding-broker-daemon-service.md`.
- Cover a user-level service flow, environment-file placement outside the repo,
  libpq password handling, provider key handling, logs, restart policy, and
  smoke checks.
- Cover a local container/S3-compatible-host style only if it remains local and
  does not imply cloud dependency.
- State that the daemon must not run with normal corpus-reading DB authority.
- Include commands for `check-grounding-broker`, one-shot `--max-iterations 1`
  smoke runs, and interpreting lock-skipped/processed counts.

Do not add a live service unit that embeds secrets. If a template is necessary,
keep it secret-free and local-only.

Publish
`docs/reviews/entity-grounding-broker-daemon-followups-2026-05-19/PRODUCTION_DAEMON_PACKAGING_HANDOFF.md`.
