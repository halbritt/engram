# RFC 0021 Gold-Set Implementation Runbook

This Striatum scaffold drives implementation of the accepted RFC 0021
gold-set interview curation. It is a sequential code-change run:

```text
implement_gold_set -> verify_gold_set -> final_review
```

## Start

Run from the Engram repository root.

```sh
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/rfc-0021-gold-set-implementation/workflow.json

"$RUNNER" --repo . workflow validate "$WORKFLOW" --json
"$RUNNER" --repo . workflow plan "$WORKFLOW" --json
PREP=$("$RUNNER" --repo . run prepare --workflow "$WORKFLOW" --json)
RUN_ID=$(printf '%s\n' "$PREP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["run_id"])')
"$RUNNER" --repo . branch confirm --run-id "$RUN_ID" --branch engram/rfc0021-gold-set-implementation --create --json
"$RUNNER" --repo . run start --run-id "$RUN_ID" --json
```

## Drive

Register a Codex session for the author lane, claim
`implement_gold_set`, and complete it with the required handoff
artifact. Then claim the verifier and final-review jobs in fresh
sessions.

```sh
"$RUNNER" --repo . register-session --run-id "$RUN_ID" --role author --lane codex --capability write --json
"$RUNNER" --repo . claim-next --session-id "$AUTHOR_SESSION_ID" --json
```

Follow the exact commands returned in each work packet for `ack`,
`publish-artifact`, `complete`, and review verdicts.

## Outputs

Durable run outputs live under:

```text
docs/reviews/rfc0021-gold-set-implementation/
```

Source code lands under `src/engram/interview/`, migrations under
`migrations/010_gold_labels.sql`, prompts under `prompts/interview/`,
tests under `tests/test_interview_*.py`. The live Striatum state remains
local in `.striatum/state.sqlite3` and should not be edited directly.
