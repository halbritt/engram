# Phase 4 Tiered Gate Runbook

This Striatum scaffold drives RFC 0024 Tier 0, Tier 1, and Tier 2 evidence
collection without human involvement. It does not authorize full-corpus Phase 4.

```text
tier0_schema_workflow_smoke
  -> tier1_nonhuman_quality_gate
  -> tier2_bounded_preflight_scaffold
  -> final_gate_review
```

The RFC 0021 interview/gold-label branch remains the source for human-labeled
entity and review evidence. Until that evidence exists, Tier 1 and Tier 2 may
collect non-human evidence and scaffolding only; they must not promote full
corpus.

## Start

Run from the Engram repository root.

```sh
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/phase-4-tiered-gate-multilane-2026-05-13/workflow.json

"$RUNNER" --repo . workflow validate "$WORKFLOW" --json
"$RUNNER" --repo . workflow plan "$WORKFLOW" --json
PREP=$("$RUNNER" --repo . run prepare --workflow "$WORKFLOW" --json)
RUN_ID=$(printf '%s\n' "$PREP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["run_id"])')
"$RUNNER" --repo . branch confirm --run-id "$RUN_ID" --branch engram/phase4-tiered-gate-scaffold --use-current --json
"$RUNNER" --repo . run start --run-id "$RUN_ID" --json
```

## Drive

Register an operator session, claim each sequential job, and follow the exact
commands in the work packet.

```sh
"$RUNNER" --repo . register-session --run-id "$RUN_ID" --role operator --lane codex --json
"$RUNNER" --repo . claim-next --session-id "$SESSION_ID" --json
```

Use fresh reviewer sessions for final review.

## Outputs

Durable, redacted outputs live under:

```text
docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/
```

The live gate state remains local in `.striatum/state.sqlite3`.
