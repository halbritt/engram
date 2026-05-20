# Entity Grounding Broker Daemon Follow-ups Runbook

This Striatum scaffold drives the residual findings from the completed daemon
run `run_ecf126b2e6234ae3b54958d8471e5e56`.

```text
durable_dispatch_boundary,
retry_cooldown_policy,
production_daemon_packaging,
cli_typecheck_debt,
grounding_review_surface_gate
  -> docs_gate -> verification -> synthesis -> final_review
```

The first five jobs are intended to run in parallel with disjoint write scopes.
All work is local-only. Do not call live search providers in this workflow.

## Start

Run from the Engram repository root:

```sh
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/entity-grounding-broker-daemon-followups-2026-05-19/workflow.json

STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 \
  "$RUNNER" --repo . workflow validate --allow-same-model-pairing "$WORKFLOW" --json
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 \
  "$RUNNER" --repo . workflow plan "$WORKFLOW" --json
```

Prepare/start only when the operator wants Striatum to own live state:

```sh
PREP=$(STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 \
  "$RUNNER" --repo . run prepare --workflow "$WORKFLOW" --json)
RUN_ID=$(printf '%s\n' "$PREP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["run_id"])')
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 \
  "$RUNNER" --repo . run start --run-id "$RUN_ID" --json
```

Register one session per first-wave lane and claim in parallel.

## Outputs

Durable artifacts land under:

```text
docs/reviews/entity-grounding-broker-daemon-followups-2026-05-19/
```

The live Striatum state remains local in `.striatum/state.sqlite3`.
