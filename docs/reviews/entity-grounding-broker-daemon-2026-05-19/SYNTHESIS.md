---
schema_version: "striatum.synthesis.v1"
artifact_kind: "synthesis"
---

author: operator

# Synthesis

Run: `run_ecf126b2e6234ae3b54958d8471e5e56`  
Job: `synthesis`  
Date: 2026-05-19

## Accepted Deltas

- The daemon core is implemented as a bounded-testable local loop over
  `process_approved_grounding_grants`, with injected connection factory,
  injected sleep, `max_iterations`, structured JSON output, option validation,
  transaction advisory locking, and Ctrl-C handling.
- The operator surface is wired as `engram entity-grounding broker-daemon`; it
  requires `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL`, forwards
  tenant/corpus/limit/interval/target-adapter/max-iterations, and reuses the
  existing secret-redacting entity-grounding JSON output path.
- `make grounding-broker-daemon` wraps the daemon command with an explicit
  broker-DSN environment guard.
- The materializer excludes approved grants that already have prepared,
  dispatched, succeeded, or failed dispatch rows for the same
  request/grant/target adapter. This prevents ordinary daemon polling from
  repeatedly sending the same approved entity query.
- Docs record the broker role boundary, daemon runbook, sensitive metadata
  handling, advisory lock, no repeated dispatch for existing audit rows, D096,
  roadmap state, and remaining gates.
- The Striatum workflow itself validates and encodes the intended maximum
  parallelism: daemon core, CLI surface, idempotency/security, and docs run in
  parallel before verification, synthesis, and final review.

## Verification

Verification published `accept_with_findings` with:

- `65 passed` for focused daemon/materializer/CLI tests;
- Ruff clean on touched Python files;
- Pyright clean on `entity_grounding_daemon.py` and
  `entity_grounding_materialization.py`;
- `cli.py` compileall clean;
- Striatum workflow validation clean;
- `make -n grounding-broker-daemon` prints the expected guard and dispatch.

## Residual Findings

- Full pyright including `src/engram/cli.py` still fails on an existing optional
  `uvicorn` import and a pre-existing complexity warning. The daemon source and
  materializer source type-check cleanly.
- Crash-before-commit remains a real retry caveat: if the daemon calls the
  provider and the process dies before committing the prepared dispatch row, a
  later pass can dispatch the same approved grant. Fixing that requires a
  stronger durable claim/dispatch transaction boundary.
- Direct concurrent callers of `process_approved_grounding_grants` are not as
  smooth as daemon callers. The daemon's advisory lock protects the intended
  runtime path, while direct concurrent materializer calls may still race into
  the dispatch attempt unique index.
- Retry is intentionally conservative: prepared/failed rows block automatic
  retry for that grant. Operators need a new approved grant to retry unless a
  later RFC adds bounded retry/cooldown state.
- Production packaging for a user-level daemon service remains outside this
  scaffold.

## Verdict Recommendation

Accept with findings. The requested local daemon workflow is implemented,
documented, Striatum-scaffolded, and verified. The residual findings are either
pre-existing toolchain debt or follow-up hardening beyond the scaffold.
