# Focused Review Recovery Ledger
author: operator [self-declared: rfc0027-focused-recovery-ledger]

Status: ledger
Date: 2026-05-14

## Scope

This ledger records the two focused-review recovery artifacts created after the
original Claude focused-review lanes exited without publishing the required
artifacts or verdicts.

Sources:

- `docs/reviews/rerun-backlog-focused-reviews-2026-05-13/RFC0027_FOCUSED_REVIEW_RECOVERY.md`
- `docs/operations/phase4-build/evidence-fix-2026-05-13/FOCUSED_SCAFFOLD_REVIEW_RECOVERY.md`
- `OPERATOR_REPORT.md`
- `striatum/rerun-backlog-focused-review-recovery-2026-05-13/RUNBOOK.md`

This recovery ledger does not complete, repair, or reinterpret the original
Claude jobs. It does not publish artifacts under their sessions. It does not
promote RFC 0027, RFC 0024, any other RFC, or Phase 4, and it does not
authorize full-corpus Phase 4 execution. Acceptance here means only that a
recovery review finding was received and normalized for the backlog.

## Recovery Outcomes

| Recovery review | Artifact verdict | Ledger disposition |
|---|---|---|
| RFC 0027 web privacy and session-state recovery | `needs_revision` | Accept F001-F005 as real repair findings from the recovery review. |
| Phase 4 evidence-fix scaffold recovery | `accept` | Accept the scaffold review as non-promoting evidence that the scaffold remains bounded, privacy-preserving, and tier-sequenced. |

## Output-Missing Friction

### REC-L001 - Original Claude recovery targets lacked required publication state

Severity: major

Sources: recovery runbook; `OPERATOR_REPORT.md` focused-review and recovery
sections.

Rationale: The recovery workflow exists because the original RFC 0027 and
Phase 4 focused-review Claude lanes exited without the required artifact and
verdict publication state. The recovery run intentionally created fresh
substitute review artifacts with honest provenance instead of completing the
original sessions after the fact.

Disposition: accepted as process friction.

Promotion impact: none. This preserves provenance only; it does not validate
the original Claude jobs and does not convert their missing-output state into
a completed review.

## Accepted RFC 0027 Recovery Findings

### REC-L002 - `evidence/all` bypassed the parent-target Tier 1 ceiling

Severity: major

Source finding: `RFC0027_FOCUSED_REVIEW_RECOVERY.md` F001.

Rationale: The normal question route checked both the parent target tier and
rendered evidence-message tiers, while the direct evidence-all route checked
only the evidence rows. A Tier 2 target with Tier 1 cited messages could
therefore be blocked on the question page but still render through the direct
route.

Disposition: accepted as a recovery review finding.

### REC-L003 - Completed or abandoned sessions could still be resumed and mutated

Severity: major

Source finding: `RFC0027_FOCUSED_REVIEW_RECOVERY.md` F002.

Rationale: Web resume, question rendering, and verdict POST paths did not
reject sessions with `completed_at IS NOT NULL`, and the agent-level verdict
path did not enforce terminal session state. A direct URL or POST could append
labels after completion or abandonment.

Disposition: accepted as a recovery review finding.

### REC-L004 - Final completion was based on URL position, not remaining frozen targets

Severity: major

Source finding: `RFC0027_FOCUSED_REVIEW_RECOVERY.md` F003.

Rationale: The verdict POST completed a session when the submitted URL index
reached the target count. Out-of-order direct posts could close the session
while earlier materialized targets remained unanswered.

Disposition: accepted as a recovery review finding.

### REC-L005 - Web progress counts ignored the frozen target/version predicate

Severity: medium

Source finding: `RFC0027_FOCUSED_REVIEW_RECOVERY.md` F004.

Rationale: Resume behavior used the frozen target/version predicate, but open
session and question-page progress counts counted all labels by `session_id`.
That could display answered counts inconsistent with the actual resumable
target set.

Disposition: accepted as a recovery review finding.

### REC-L006 - Targetless open sessions remained stranded in the web path

Severity: medium

Source finding: `RFC0027_FOCUSED_REVIEW_RECOVERY.md` F005.

Rationale: Storage rejected open sessions with no materialized targets, but
the web path could list such sessions and then silently redirect to the index
on resume. The recovery finding correctly kept the pre-011 targetless-session
case visible instead of silently completing it.

Disposition: accepted as a recovery review finding.

## Accepted Phase 4 Recovery Findings

### REC-L007 - Evidence-fix scaffold remains non-promoting

Severity: info

Source finding: `FOCUSED_SCAFFOLD_REVIEW_RECOVERY.md` "Scaffold remains
correctly non-promoting".

Rationale: The scaffold explicitly states that it does not promote Phase 4,
does not authorize full-corpus Phase 4, and does not run a corpus-scale job.
It records bounded result states only: `blocked`, `findings`,
`ready-for-tier2-bounded-preflight`, or `human-checkpoint`.

Disposition: accepted as a recovery review finding.

Promotion impact: none. The scaffold remains evidence collection only.

### REC-L008 - Phase 4 scaffold redaction and privacy boundaries are clear

Severity: info

Source finding: `FOCUSED_SCAFFOLD_REVIEW_RECOVERY.md` "Redaction and privacy
boundaries are clear".

Rationale: The scaffold keeps committed outputs aggregate-only and excludes
raw corpus text, prompts, completions, conversation titles, belief values,
claim values, entity names, relationship labels, credentials, private values,
and home-directory absolute paths. Local scratch remains ignored.

Disposition: accepted as a recovery review finding.

### REC-L009 - Phase 4 scaffold execution remains bounded

Severity: info

Source finding: `FOCUSED_SCAFFOLD_REVIEW_RECOVERY.md` "Execution is explicitly
bounded".

Rationale: The scaffold caps Tier 0 smoke at `LIMIT=25`, caps the Tier 2
guardrail at `--limit 500` or an equivalent deterministic fixed slice, and
restricts review-action evidence to one bounded action sample.

Disposition: accepted as a recovery review finding.

### REC-L010 - Phase 4 scaffold preserves tier eligibility sequencing

Severity: info

Source finding: `FOCUSED_SCAFFOLD_REVIEW_RECOVERY.md` "Tier eligibility
requirements are preserved".

Rationale: The scaffold keeps Tier 0 eligible only after pytest evidence,
stages Tier 1 entity-pair and review-action evidence separately, and keeps
Tier 2 ineligible until Tier 0 and Tier 1 passing evidence is recorded or
unresolved blockers are explicitly carried forward.

Disposition: accepted as a recovery review finding.

## Remaining Blockers

- RFC 0027 recovery review outcome was `needs_revision`; this ledger records
  F001-F005 as accepted repair findings, not as cleared blockers.
- `OPERATOR_REPORT.md` records a later RFC 0027 web-state re-review with
  verdict `accept` for the implemented F001-F005 repairs. This ledger does
  not decide whether that accepted re-review clears checkpoint
  `blk_4d7be5151bec4e18ae6aea672269998f`, and it does not resolve the
  separate Striatum process-adapter blocker tracked as issue 7.
- Phase 4 full-corpus execution remains blocked. The Phase 4 recovery review
  accepted only the bounded evidence-fix scaffold and explicitly did not
  promote Phase 4.
- The original Claude output-missing jobs remain historical provenance gaps.
  The recovery artifacts replace missing review evidence only for the recovery
  lane; they do not mutate or complete the original sessions.

## Verification

No network access was used. No code or schema tests were run because this is a
ledger-only documentation artifact.
