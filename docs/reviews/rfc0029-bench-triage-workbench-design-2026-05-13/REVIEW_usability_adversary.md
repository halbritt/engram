# RFC 0029 Bench Triage Workbench Adversarial Usability Review
author: operator [self-declared: rfc0029-design-usability-adversary-codex]

Status: review
Date: 2026-05-13
RFC refs: RFC-0029
Decision refs: D020, D074
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### U001 - Promotion readiness depends on context that is not recorded
Severity: blocking
Source: docs/rfcs/0029-bench-triage-workbench.md:212
Rationale: The review-state schema stores only `decision`, `confidence`, optional `note`, and timestamps, but the readiness matrix later depends on whether local source context or private detail was available when the operator accepted a `candidate_zero` or `candidate_redacted` item. That hidden condition is load-bearing: `candidate_zero + accept_candidate_change` clears the blocker only when source context was available, and `candidate_redacted + accept_candidate_change` clears only aggregate/count-only deltas. After reload, status, export, or a later implementation pass, the system cannot distinguish "accepted after seeing enough evidence" from "accepted from redacted counts only." This is exactly the false-confidence path the workbench is meant to prevent.
Suggested fix: Persist the review basis at decision time. Add fields such as `review_basis`, `source_context_available`, `private_detail_available`, and `semantic_delta_cleared` to `segment_reviews` or an associated decision metadata JSON column with explicit CHECK-constrained values. The POST route should compute these from the loaded artifacts and route state, not trust form input. Readiness should use the stored basis, and the UI should render states like "accepted count-only; semantic blocker remains" rather than treating all `accept_candidate_change` rows alike. Resolve the open `candidate_redacted` eligibility question before promotion to an implementation spec.

### U002 - Parked and blocking decisions lack first-class resume queues
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:309
Rationale: The queue tabs are risk-tag views, not decision-state views. A tired reviewer who parks an item as `needs_followup`, flags a regression, or excludes a blocker needs a direct way to return to those unresolved decisions. The RFC says those states block readiness, but the primary navigation lists Needs review, risk categories, and All; it does not require Follow-up, Regressions, or Excluded blockers queues. Because `needs_followup` and `flag_candidate_regression` clear the review obligation while blocking promotion, they can vanish from the operator's next obvious task list and force the operator to reconstruct unresolved work from summary counts.
Suggested fix: Add decision-state queues to the route and screen contract: Follow-up, Regressions, Excluded blockers, and Accepted. The landing page should make "resume unresolved blockers" the primary action when any exist. `GET /segments` should support decision-state filters in addition to risk-tag filters, and the default Needs review view should either include unresolved blocking decisions or clearly link to the blocker queue.

### U003 - Scratch promotion wording is still too authoritative
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:193
Rationale: The RFC correctly states that scratch run decisions do not update Striatum state, but the proposed schema and UI states still use authoritative words: `run_decision IN ('undecided', 'promote', 'do_not_promote')`, readiness values named `promoted_by_recorded_decision`, and a `/run-decision` route that records `decision=promote`. Under D074, Striatum is the gate state; this workbench should not let a reviewer mistake a scratch-local recommendation for the actual gate decision, especially after a long review session when the UI says the run is "promoted."
Suggested fix: Rename the entire scratch decision surface to recommendation language: `run_recommendation IN ('undecided', 'recommend_promote', 'recommend_do_not_promote')`, readiness states like `promotion_recommendation_recorded`, and UI copy that says "recommend promotion to owner gate" rather than "promote." The export should label this as a non-authoritative recommendation and name the next external gate action, while still avoiding raw private content.

### U004 - `exclude_from_review` is too easy to use as a disposal action
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:359
Rationale: `Exclude from this review` is one of four large verdict controls, counts as an operator action, and clears the review obligation even for risky, missing, malformed, or ambiguous rows while leaving a blocker behind. The note field is optional, so a reviewer can create an excluded-blocker pile with no explanation. The RFC says the summary shows excluded items separately, but that is a backstop after the damage has happened; the primary screen should prevent "I do not want to think about this now" from looking like a normal verdict.
Suggested fix: Split the action. Keep a narrow `exclude_unchanged_from_review` action for complete, unchanged, no-risk rows. For any risky, missing, malformed, ambiguous, zeroed, or changed row, replace the button with `mark_blocking_out_of_scope` or `defer_as_blocker`, require a rationale, and keep the item visible in the blocker queue. Batch exclusion should be available only from an unchanged/no-risk preview and should write a machine-readable reason plus the queue fingerprint used for the preview.

### U005 - Acceptance tests do not yet pin the cognitive-load contract
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:654
Rationale: The test list is strong on mechanics, privacy, paths, and route safety, but the usability contract is still described too generically. "UI contract tests for data-availability blocking, promotion-readiness blockers, deterministic resume, shortcut focus safety, and visible post-decision confirmation" does not force the implementation to preserve the core screen promise: what changed, why it matters, what action is required, whether the decision is authoritative, and what unresolved pile the item now belongs to. Without golden HTML or route-level assertions for those states, a later implementation can technically pass while hiding the reason an item blocks promotion or using ambiguous promotion/exclusion language.
Suggested fix: Add explicit acceptance tests for each data-availability state and each verdict result. Tests should assert the rendered change-summary consequence text, disabled/enabled controls, the persisted review basis, the resulting queue membership, the promotion-readiness label, and the exact export wording for scratch recommendations. Add regression tests that `candidate_redacted` semantic deltas cannot clear readiness without a stored sufficient review basis and that excluded blockers remain directly reachable from the landing page.

## Open questions

1. Should `candidate_redacted` ever be eligible for semantic acceptance, or should it only support count/provenance acceptance until a local source excerpt or private-detail artifact is present?
2. Should `exclude_from_review` exist for risky rows at all, or should risky out-of-scope rows always be modeled as unresolved blockers with a required rationale?
3. What exact non-authoritative wording should the UI and export use so a scratch recommendation cannot be confused with the D074 Striatum gate state?

verdict: needs_revision
