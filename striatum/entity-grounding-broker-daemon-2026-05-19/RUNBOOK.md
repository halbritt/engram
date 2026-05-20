# Entity Grounding Broker Daemon Workflow Runbook

This Striatum scaffold drives the local daemon slice for the RFC 0055
grounding broker.

```text
daemon_core, cli_operator_surface, idempotency_security, docs_gate
  -> verification -> synthesis -> final_review
```

The first four jobs are intentionally parallel and have disjoint write scopes.
The workflow is implementation-only and local-only; it must not call the live
network provider.

## Start

Run from the Engram repository root.

```sh
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/entity-grounding-broker-daemon-2026-05-19/workflow.json

STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 \
  "$RUNNER" --repo . workflow validate --allow-same-model-pairing "$WORKFLOW" --json
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 \
  "$RUNNER" --repo . workflow plan "$WORKFLOW" --json
```

Prepare and start only when the operator wants Striatum to own the live run
state:

```sh
PREP=$(STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 \
  "$RUNNER" --repo . run prepare --workflow "$WORKFLOW" --json)
RUN_ID=$(printf '%s\n' "$PREP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["run_id"])')
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 \
  "$RUNNER" --repo . run start --run-id "$RUN_ID" --json
```

Register sessions for each implementation lane and claim in parallel. Follow
the exact packet commands for `ack`, `publish-artifact`, `complete`, and review
verdict submission.

## Outputs

Durable artifacts land under:

```text
docs/reviews/entity-grounding-broker-daemon-2026-05-19/
```

The live Striatum state remains local in `.striatum/state.sqlite3` and should
not be edited by hand.
