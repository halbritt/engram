# RFC 0027 Interview Web UI Review — Runbook

Status: scaffolded
Date: 2026-05-08

## Goal

Multi-agent review of RFC 0027, the proposal for a localhost-only
FastAPI + htmx web UI over the gold-set interview surface.

The output is a synthesis recommending whether to accept (yielding a
spec at `docs/specs/0027-interview-web-ui-spec.md`), revise, split, or
reject before any build code lands.

## Workflow Shape

```text
review_claude   ┐
review_codex    ├─→ findings_ledger ─→ synthesis ─→ final_review
review_gemini   ┘
```

## One-Shot Environment

```bash
cd ~/git/engram
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/rfc-0027-interview-web-ui-review/workflow.json
TARGET_REPO=.
```

## Validate And Prepare

```bash
"$RUNNER" --repo "$TARGET_REPO" workflow validate "$WORKFLOW" --json
"$RUNNER" --repo "$TARGET_REPO" workflow plan "$WORKFLOW" --json | head -40
PREP=$("$RUNNER" --repo "$TARGET_REPO" run prepare --workflow "$WORKFLOW" --json)
RUN_ID=$(printf '%s' "$PREP" | python3 -c \
  'import json,sys; print(json.load(sys.stdin)["data"]["run_id"])')
echo "RUN_ID=$RUN_ID"
```

## Confirm Branch And Start

```bash
"$RUNNER" --repo "$TARGET_REPO" branch confirm \
  --run-id "$RUN_ID" \
  --branch engram/rfc0027-interview-web-ui-review \
  --use-current --json

"$RUNNER" --repo "$TARGET_REPO" run start --run-id "$RUN_ID" --json
```

## Drive

Register sessions for claude/codex/gemini reviewers (parallel),
ledger, synthesizer, final-reviewer. Claim packets, ack, dispatch
agents, publish artifacts, submit verdicts. See
`striatum/rfc-0021-gold-set-review/RUNBOOK.md` for the equivalent
flow.

## Finish

```bash
"$RUNNER" --repo "$TARGET_REPO" evidence export \
  --run-id "$RUN_ID" \
  --path docs/reviews/rfc0027/EVIDENCE.md --json

"$RUNNER" --repo "$TARGET_REPO" run summary \
  --run-id "$RUN_ID" \
  --path docs/reviews/rfc0027/RUN_SUMMARY.md --json

make check-refs
```
