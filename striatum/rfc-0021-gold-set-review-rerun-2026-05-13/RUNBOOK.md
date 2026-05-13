# RFC 0021 Gold-Set Interview Curation Review — Runbook

Status: scaffolded
Date: 2026-05-08

## Goal

Use Striatum to run an adversarial multi-agent review of RFC 0021, the
proposal for an agent-driven interview loop that authors gold-set verdicts
against the local corpus.

The output is a synthesis recommending whether to accept, revise, split, or
reject the RFC before any migration or CLI changes land.

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
WORKFLOW=striatum/rfc-0021-gold-set-review-rerun-2026-05-13/workflow.json
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
  --branch engram/rfc0021-gold-set-review-rerun-2026-05-13 \
  --create \
  --json

"$RUNNER" --repo "$TARGET_REPO" run start --run-id "$RUN_ID" --json
```

## Register Sessions

```bash
register() {
  "$RUNNER" --repo "$TARGET_REPO" register-session \
    --run-id "$RUN_ID" --role "$1" --lane "$2" \
    --capability "$3" --json \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["session_id"])'
}

CLAUDE_REVIEWER=$(register reviewer claude review)
CODEX_REVIEWER=$(register reviewer codex review)
GEMINI_REVIEWER=$(register reviewer gemini review)
LEDGER=$(register ledger codex write)
SYNTHESIZER=$(register synthesizer claude synthesis)
FINAL_REVIEWER=$(register reviewer codex review)
```

## Finish

```bash
"$RUNNER" --repo "$TARGET_REPO" evidence export \
  --run-id "$RUN_ID" \
  --path docs/reviews/rfc0021-rerun-2026-05-13/EVIDENCE.md --json

"$RUNNER" --repo "$TARGET_REPO" run summary \
  --run-id "$RUN_ID" \
  --path docs/reviews/rfc0021-rerun-2026-05-13/RUN_SUMMARY.md --json
```

Run final checks:

```bash
make check-refs
git status --short --branch
```
