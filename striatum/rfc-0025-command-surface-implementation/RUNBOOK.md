# RFC 0025 Command-Surface Implementation Runbook

This Striatum scaffold drives implementation of the accepted RFC 0025 command
surface. It is a sequential code-change run:

```text
implement_command_surface -> verify_command_surface -> final_review
```

## Start

Run from the Engram repository root.

```sh
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/rfc-0025-command-surface-implementation/workflow.json

"$RUNNER" --repo . workflow validate "$WORKFLOW" --json
"$RUNNER" --repo . workflow plan "$WORKFLOW" --json
PREP=$("$RUNNER" --repo . run prepare --workflow "$WORKFLOW" --json)
RUN_ID=$(printf '%s\n' "$PREP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["run_id"])')
"$RUNNER" --repo . branch confirm --run-id "$RUN_ID" --branch engram/rfc0025-command-surface-implementation --use-current --json
"$RUNNER" --repo . run start --run-id "$RUN_ID" --json
```

If the editable Striatum install is importing an in-progress Striatum worktree,
run the same commands through a clean Striatum source snapshot by setting
`PYTHONPATH` to that snapshot's `src` directory.

## Drive

Register a Codex session for the author lane, claim
`implement_command_surface`, and complete it with the required handoff
artifact. Then claim the verifier and final-review jobs in fresh sessions.

```sh
"$RUNNER" --repo . register-session --run-id "$RUN_ID" --role author --lane codex --json
"$RUNNER" --repo . claim-next --run-id "$RUN_ID" --role author --lane codex --json
```

Follow the exact commands returned in each work packet for `ack`,
`publish-artifact`, `complete`, and review verdicts.

## Outputs

Durable run outputs live under:

```text
docs/reviews/rfc0025-command-surface-implementation/
```

The live Striatum state remains local in `.striatum/state.sqlite3` and should
not be edited directly.
