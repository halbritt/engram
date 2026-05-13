# Rerun Backlog Focused Reviews Runbook

Status: scaffolded
Date: 2026-05-13

## Goal

Queue focused re-reviews for the just-completed rerun backlog fixes. This
workflow is review-only. It must not implement code, revise source documents,
promote RFCs, accept Phase 4, or authorize full-corpus execution.

Acceptance of review artifacts is not promotion. The final ledger records
received findings and remaining blockers only.

## Workflow Shape

```text
rfc0028_focused_review
rfc0027_focused_review
rfc0021_contract_re_review
rfc0029_design_re_review
phase4_evidence_fix_scaffold_review
  -> focused_review_ledger
```

The five review jobs can run in parallel because they inspect separate
surfaces and write distinct artifacts. Reviewers may use maximal useful
sub-agents internally for their assigned review.

## Validate And Plan Only

```bash
cd /home/halbritt/git/engram
WORKFLOW=striatum/rerun-backlog-focused-reviews-2026-05-13/workflow.json
STRIATUM_DAEMON_REQUIRED=0 .venv/bin/striatum --repo . workflow validate "$WORKFLOW" --json
STRIATUM_DAEMON_REQUIRED=0 .venv/bin/striatum --repo . workflow plan "$WORKFLOW" --json
git diff --check -- striatum/rerun-backlog-focused-reviews-2026-05-13/
```

Do not run `prepare`, `start`, or any execution command until the operator
explicitly authorizes this workflow.
