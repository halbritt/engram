# RFC 0028 Predicate Intent Implementation — Runbook

Status: scaffolded
Date: 2026-05-13

## Goal

Use Striatum to implement RFC 0028 and gate the result with three independent
review lanes before final acceptance.

## Workflow Shape

```text
implement_predicate_intent
  ├─ review_claude
  ├─ review_codex
  └─ review_gemini
        └─ findings_ledger -> revision_synthesis -> apply_findings -> final_review
```

## One-Shot Environment

```bash
cd ~/git/engram
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/rfc-0028-predicate-intent-promotion-2026-05-13/workflow.json
TARGET_REPO=.
```

## Validate, Prepare, Start

```bash
"$RUNNER" --repo "$TARGET_REPO" workflow validate "$WORKFLOW" --json
PREP=$("$RUNNER" --repo "$TARGET_REPO" run prepare --workflow "$WORKFLOW" --json)
RUN_ID=$(printf '%s' "$PREP" | python3 -c \
  'import json,sys; print(json.load(sys.stdin)["data"]["run_id"])')
"$RUNNER" --repo "$TARGET_REPO" branch confirm \
  --run-id "$RUN_ID" \
  --branch engram/rfc0028-predicate-intent-promotion-2026-05-13 \
  --use-current --json
"$RUNNER" --repo "$TARGET_REPO" run start --run-id "$RUN_ID" --json
```

## Finish

```bash
"$RUNNER" --repo "$TARGET_REPO" evidence export \
  --run-id "$RUN_ID" \
  --path docs/reviews/rfc0028-predicate-intent-promotion-2026-05-13/EVIDENCE.md --json
"$RUNNER" --repo "$TARGET_REPO" run summary \
  --run-id "$RUN_ID" \
  --path docs/reviews/rfc0028-predicate-intent-promotion-2026-05-13/RUN_SUMMARY.md --json
make check-refs
```
