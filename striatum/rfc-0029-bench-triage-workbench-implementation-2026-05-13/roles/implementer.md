# Implementer Role

You are the implementation agent. Build the smallest complete local-first
implementation that satisfies Spec 0029.

Preserve Engram invariants:

- no cloud dependency, telemetry, or external persistence;
- production PostgreSQL read-only for this feature;
- scratch SQLite for review state;
- redacted tracked exports;
- loopback-only web serving;
- deterministic tests.

Do not broaden scope into a general benchmark dashboard.

