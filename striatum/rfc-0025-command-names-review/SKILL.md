---
name: engram-rfc-0025-command-names-review
description: Drive the Engram RFC 0025 command-names multi-agent review through Striatum. Three independent reviewers examine the RFC, command surface, and phase boundaries; a ledger normalizes findings; a synthesis recommends acceptance/revision/split/rejection; a final review gates the recommendation.
---

# Engram RFC 0025 Command-Names Review

Use this skill from `~/git/engram` to start or drive the RFC 0025 review.

## Ground Rules

- Do not edit `.striatum/state.sqlite3` directly.
- Reviewers write only under `docs/reviews/rfc0025/`.
- Review jobs do not edit RFC 0025, Makefile, README, or code.
- Root-review `needs_revision` verdicts become human checkpoints.

## Quick Start

```bash
cd ~/git/engram
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/rfc-0025-command-names-review/workflow.json
TARGET_REPO=.

make rfc25-validate
"$RUNNER" --repo "$TARGET_REPO" run prepare --workflow "$WORKFLOW" --json
```

Use `RUNBOOK.md` for branch confirmation, session registration, and finish
commands.
