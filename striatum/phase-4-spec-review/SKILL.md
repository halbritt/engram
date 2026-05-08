---
name: engram-phase-4-spec-review
description: Drive the Engram Phase 4 build-spec multi-agent review through Striatum. Three independent reviewers (Claude, Codex, Gemini) examine the inputs that would inform a Phase 4 spec; a ledger normalizes findings; a synthesis recommends next action; a final review gates the recommendation. Root-review needs_revision verdicts surface as human checkpoints.
---

# Engram Phase 4 Spec Review

Use this skill from `~/git/engram` to start or drive the Phase 4
build-spec review. The output is a synthesis recommending one of:
author a Phase 4 RFC, author an implementation spec, revise
`BUILD_PHASES.md`, or pause to resolve a blocker.

## Ground Rules

- Do not edit `.striatum/state.sqlite3` directly.
- The workflow's `review_revision_policy` declares
  `root_review_needs_revision: human_checkpoint` — a `needs_revision`
  verdict from any of the three root reviewers blocks the run for
  human resolution; it does not auto-cycle.
- Reviewers stay within their declared `write_scope`; ledger and
  synthesis read all three reviews.
- Capture friction as `harness_improvement_proposal` artifacts using
  `HARNESS_PROPOSAL_TEMPLATE.md`.
- Final review's verdict is the ship/no-ship signal; if it accepts,
  the owner authors whichever Phase 4 spec the synthesis recommended.

## Quick Start

```bash
cd ~/git/engram
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/phase-4-spec-review/workflow.json
TARGET_REPO=.
```

Verify and prepare:

```bash
make phase4-validate
make phase4-prepare
# or, equivalently:
"$RUNNER" --repo "$TARGET_REPO" workflow validate "$WORKFLOW" --json
"$RUNNER" --repo "$TARGET_REPO" run prepare --workflow "$WORKFLOW" --json
```

Capture the run id, confirm the branch, and start:

```bash
RUN_ID=$("$RUNNER" --repo "$TARGET_REPO" run prepare --workflow "$WORKFLOW" --json \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["run_id"])')

"$RUNNER" --repo "$TARGET_REPO" branch confirm \
  --run-id "$RUN_ID" \
  --branch engram/phase4-spec-review \
  --create \
  --json

"$RUNNER" --repo "$TARGET_REPO" run start --run-id "$RUN_ID" --json
```

Register the lanes you'll drive. Minimum:

- `CLAUDE_REVIEWER`
- `CODEX_REVIEWER`
- `GEMINI_REVIEWER`
- `LEDGER`
- `SYNTHESIZER`
- `FINAL_REVIEWER`

Claim sequentially per the workflow plan (three parallel reviews,
then ledger, then synthesis, then final review).

```bash
"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$CLAUDE_REVIEWER" --json
"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$CODEX_REVIEWER"  --json
"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$GEMINI_REVIEWER" --json
# after all three reviews complete:
"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$LEDGER"        --json
"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$SYNTHESIZER"   --json
"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$FINAL_REVIEWER" --json
```

Watch:

```bash
"$RUNNER" --repo "$TARGET_REPO" dashboard --run-id "$RUN_ID"
make phase4-status
```

If the final review accepts, record the owner's decision via:

```bash
mkdir -p docs/decisions/phase4
"$RUNNER" --repo "$TARGET_REPO" decision record \
  --run-id "$RUN_ID" \
  --path docs/decisions/phase4/PHASE_4_DIRECTION.md \
  --outcome <accepted|accepted_with_follow_up|rejected> \
  --title "Phase 4 spec direction" \
  --follow-up "<what the owner will author next: RFC, build spec, BUILD_PHASES revision>" \
  --json
```

Finish:

```bash
"$RUNNER" --repo "$TARGET_REPO" evidence export \
  --run-id "$RUN_ID" \
  --path docs/reviews/phase4/EVIDENCE.md --json

"$RUNNER" --repo "$TARGET_REPO" run summary \
  --run-id "$RUN_ID" \
  --path docs/reviews/phase4/RUN_SUMMARY.md --json
```

Use `RUNBOOK.md` for the full operator procedure including session
registration commands, friction capture, and reset.
