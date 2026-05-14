# Striatum Memory Roadmap RFC Queue Runbook

Status: scaffolded
Date: 2026-05-14

## Goal

Use Striatum to drive the RFC 0044 hardening cleanup and the RFC 0045-0049
roadmap work with explicit dependency ordering and parallel review lanes.

## Workflow Shape

```text
rfc0044_hardening_handoff

rfc0045_contract_handoff
  ├─ rfc0046_projection_schema_handoff
  └─ rfc0047_augmentation_boundary_handoff
        └─ rfc0048_context_policy_handoff
              └─ rfc0049_evaluation_gates_handoff
                    ├─ review_privacy_boundary
                    ├─ review_contract_coherence
                    └─ review_operator_ergonomics
                          └─ findings_ledger -> final_synthesis
```

## One-Shot Environment

```bash
cd ~/git/engram
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/striatum-memory-roadmap-rfcs-2026-05-14/workflow.json
TARGET_REPO=.
```

## Validate And Prepare

```bash
"$RUNNER" --repo "$TARGET_REPO" workflow validate "$WORKFLOW" --json
PREP=$("$RUNNER" --repo "$TARGET_REPO" run prepare --workflow "$WORKFLOW" --json)
RUN_ID=$(printf '%s' "$PREP" | python3 -c \
  'import json,sys; print(json.load(sys.stdin)["data"]["run_id"])')
"$RUNNER" --repo "$TARGET_REPO" branch confirm \
  --run-id "$RUN_ID" \
  --branch engram/striatum-memory-roadmap-rfcs \
  --use-current --json
```

Start only after the operator confirms the queued docs are the right shape:

```bash
"$RUNNER" --repo "$TARGET_REPO" run start --run-id "$RUN_ID" --json
```

## Finish

```bash
"$RUNNER" --repo "$TARGET_REPO" evidence export \
  --run-id "$RUN_ID" \
  --path docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/EVIDENCE.md --json
"$RUNNER" --repo "$TARGET_REPO" run summary \
  --run-id "$RUN_ID" \
  --path docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/RUN_SUMMARY.md --json
make check-refs
```
