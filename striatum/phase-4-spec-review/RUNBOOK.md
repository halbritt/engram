# Phase 4 Build-Spec Review — Runbook

Status: scaffolded
Last refactored: 2026-05-08 (moved from `prompts/phase4/`)

## Goal

Use Striatum to drive an adversarial multi-agent review of the inputs
that would inform a Phase 4 build spec — `BUILD_PHASES.md`'s
PHASE-0004 row, `HUMAN_REQUIREMENTS.md`, the relevant decisions in
`DECISION_LOG.md`, and the upstream RFCs (0007, 0011, 0018). The
output is a synthesis that recommends one of:

1. Author a Phase 4 RFC (design proposal).
2. Author a Phase 4 implementation spec (binding handoff for build).
3. Revise the Phase 4 row in `BUILD_PHASES.md`.
4. Pause to resolve a blocker the reviewers surfaced.

## Workflow Shape

```text
review_claude   ┐
review_codex    ├─→ findings_ledger ─→ synthesis ─→ final_review
review_gemini   ┘
```

Five edges, no cycles. Root-review `needs_revision` verdicts surface
as human checkpoints (workflow's `review_revision_policy`); the run
blocks for owner resolution rather than auto-cycling.

## Why This Run Exists

Phase 3 is in active repair; Phase 4 introduces entity canonicalization
and the human-in-the-loop review surface. Before any Phase 4 spec is
authored, three independent reviewers should pressure-test the inputs
adversarially so the eventual spec accounts for the risks each
reviewer surfaces.

## Before You Start

Verify Striatum is wired up:

```bash
make install-striatum
make phase4-validate
```

The validate target should print `{"valid": true, ...}` plus any V1.5
lint warnings (currently none).

If a particular CLI lane is unavailable (e.g., one of `claude`,
`codex`, `gemini` is not installed), either install it before running
or capture the friction as a `harness_improvement_proposal` so the
spec author knows that lane was substituted.

## One-Shot Environment

```bash
cd ~/git/engram
RUNNER=.venv/bin/striatum
WORKFLOW=striatum/phase-4-spec-review/workflow.json
TARGET_REPO=.
```

## Initialize And Inspect

```bash
"$RUNNER" --repo "$TARGET_REPO" init --json
"$RUNNER" --repo "$TARGET_REPO" workflow validate "$WORKFLOW" --json
"$RUNNER" --repo "$TARGET_REPO" workflow plan "$WORKFLOW" --json | head -80
```

## Prepare, Confirm Branch, Start

```bash
PREP=$("$RUNNER" --repo "$TARGET_REPO" run prepare --workflow "$WORKFLOW" --json)
RUN_ID=$(printf '%s' "$PREP" | python3 -c \
  'import json,sys; print(json.load(sys.stdin)["data"]["run_id"])')
echo "RUN_ID=$RUN_ID"

"$RUNNER" --repo "$TARGET_REPO" branch confirm \
  --run-id "$RUN_ID" \
  --branch engram/phase4-spec-review \
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

CLAUDE_REVIEWER=$(register reviewer claude_code review)
CODEX_REVIEWER=$(register reviewer codex review)
GEMINI_REVIEWER=$(register reviewer gemini review)
LEDGER=$(register ledger codex write)
SYNTHESIZER=$(register synthesizer codex synthesis)
FINAL_REVIEWER=$(register reviewer codex review)
```

## Drive The Run

The three reviews are a parallel group; the workflow lets them run
concurrently with disjoint write scopes
(`docs/reviews/phase4/PHASE_4_SPEC_REVIEW_<lane>.md`). Claim them in
any order:

```bash
"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$CLAUDE_REVIEWER" --json
# ... do the work, publish the review artifact, complete

"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$CODEX_REVIEWER" --json
# ... ditto

"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$GEMINI_REVIEWER" --json
# ... ditto
```

After all three reviews complete:

```bash
"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$LEDGER" --json
# normalize the three reviews into a stable findings ledger

"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$SYNTHESIZER" --json
# recommend one of the four numbered outcomes

"$RUNNER" --repo "$TARGET_REPO" claim-next --session-id "$FINAL_REVIEWER" --json
# gate the recommendation
```

## Human Checkpoint

If any root reviewer (claude / codex / gemini) returns
`needs_revision`, the workflow blocks for owner resolution. The
checkpoint surfaces under:

```bash
"$RUNNER" --repo "$TARGET_REPO" status --run-id "$RUN_ID" --json \
  | python3 -c 'import json,sys; d=json.load(sys.stdin)["data"]; print(json.dumps(d.get("human_checkpoints", []), indent=2))'
```

Resolve by editing the inputs the reviewer flagged and reclaiming the
review job, OR by recording an owner decision that overrides the
verdict. There is no auto-cycle in this workflow.

## Capture Harness Friction

```bash
mkdir -p striatum/phase-4-spec-review/findings
cp striatum/phase-4-spec-review/HARNESS_PROPOSAL_TEMPLATE.md \
   striatum/phase-4-spec-review/findings/HARNESS-001.md
# edit, then publish from the active job
```

## Finish

```bash
"$RUNNER" --repo "$TARGET_REPO" evidence export \
  --run-id "$RUN_ID" \
  --path docs/reviews/phase4/EVIDENCE.md --json

"$RUNNER" --repo "$TARGET_REPO" run summary \
  --run-id "$RUN_ID" \
  --path docs/reviews/phase4/RUN_SUMMARY.md --json
```

Run final checks:

```bash
make lint
make typecheck
make test
git status --short --branch
```

## Reset

Only after confirming local runner state and the spec-review branch
can be discarded:

```bash
rm -rf .striatum/
git checkout master
git branch -D engram/phase4-spec-review 2>/dev/null || true
```
