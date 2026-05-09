# RFC 0027 / Spec 0027 Web UI Implementation Runbook

This Striatum scaffold drives implementation of the accepted spec at
`docs/specs/0027-interview-web-ui-spec.md`. It is a sequential code-change
run:

```text
implement_web_ui -> verify_web_ui -> final_review
```

## Start

```sh
cd ~/git/engram
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/rfc-0027-interview-web-ui-implementation/workflow.json

"$RUNNER" --repo . workflow validate "$WORKFLOW" --json
"$RUNNER" --repo . workflow plan "$WORKFLOW" --json | head -40
PREP=$("$RUNNER" --repo . run prepare --workflow "$WORKFLOW" --json)
RUN_ID=$(printf '%s' "$PREP" | python3 -c \
  'import json,sys; print(json.load(sys.stdin)["data"]["run_id"])')
echo "RUN_ID=$RUN_ID"

"$RUNNER" --repo . branch confirm --run-id "$RUN_ID" \
  --branch engram/rfc0027-interview-web-ui-implementation \
  --use-current --json
"$RUNNER" --repo . run start --run-id "$RUN_ID" --json
```

## Drive

Register a Codex session for the author lane, claim
`implement_web_ui`, complete it with the required handoff artifact,
then claim verifier and final-review jobs in fresh sessions. Use
`--force-non-fresh --reason "single-process orchestrator"` for the
review sessions if the run was prepared in the same orchestrator
process that ran the author.

## Outputs

```text
docs/reviews/rfc0027-interview-web-ui-implementation/
```

Source code lands under `src/engram/interview/{web,render}.py` plus
`src/engram/interview/{templates,static}/`; migration under
`migrations/011_gold_label_session_targets.sql`; tests under
`tests/test_interview_{web,render}.py` plus extensions to
`tests/test_migrations.py`. Live Striatum state remains local in
`.striatum/state.sqlite3`.
