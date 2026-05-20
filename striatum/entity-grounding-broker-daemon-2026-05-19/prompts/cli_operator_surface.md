# CLI Operator Surface

Wire the daemon into the operator command surface.

Required behavior:

- add `engram entity-grounding broker-daemon`;
- require `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL`;
- expose `--tenant`, `--corpus`, `--limit`, `--interval`, `--target-adapter`,
  and `--max-iterations`;
- route output through the existing secret-redacting entity-grounding JSON path;
- add a Makefile target for local daemon startup;
- add focused CLI tests for broker DSN use, failure without broker DSN, option
  forwarding, and secret redaction.

Publish `docs/reviews/entity-grounding-broker-daemon-2026-05-19/CLI_OPERATOR_HANDOFF.md`.
