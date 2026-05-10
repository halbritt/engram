# RFC 0029 Bench Triage Workbench Adversarial Usability Review
author: usability-adversary-codex-gpt-5.5-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### U001 — Candidate absence and missing artifact states can collapse into the same UI
Severity: blocking
Source: docs/rfcs/0029-bench-triage-workbench.md:117, docs/rfcs/0029-bench-triage-workbench.md:216, docs/reviews/rfc0028-predicate-intent-implementation/REEXTRACTION_BENCH_100.md:42
Rationale: The RFC allows optional candidate segment result JSONL and says the page shows "candidate claims or candidate absence." That is unsafe unless the UI distinguishes at least three states: the candidate emitted zero claims, candidate claim detail is redacted or unavailable, and the candidate artifact is missing or invalid. The motivating RFC 0028 bench used the default redacted artifact policy, so this is not theoretical. A tired reviewer could interpret "no candidate claims shown" as a semantic zero and mark a good drop when the workbench only lacks enough detail to compare.
Suggested fix: Require a first-class data-availability banner and a typed comparison state for every segment. Verdicts that imply semantic acceptance should be disabled when candidate detail is missing; only "needs follow-up" or "skip" should remain available unless the workbench has enough structured candidate output to prove zero versus unavailable. Add acceptance tests for zero output, redacted detail, missing segment JSONL, malformed candidate output, and unavailable prior rows.

### U002 — "Safe to promote" can create false confidence before unresolved risks are closed
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:72, docs/rfcs/0029-bench-triage-workbench.md:206, docs/rfcs/0029-bench-triage-workbench.md:366, docs/reviews/rfc0028-predicate-intent-implementation/REEXTRACTION_BENCH_100.md:179
Rationale: The RFC puts a safe promotion state in the progress header, but leaves open whether it is derived, manually recorded, or both. The motivating benchmark had green schema and provenance metrics while still requiring review of a material claim-count reduction and 11 prior-positive candidate-zero segments. A header-level "safe" label can overpower the local evidence on the current segment, especially if the operator is tired and trying to finish a gate.
Suggested fix: Rename the header field to "promotion readiness" and make its states explicit: blocked, review incomplete, ready for owner decision, or promoted by recorded run-level decision. The UI should show unresolved blockers by count and tag, and "ready" should never mean semantically correct; it should only mean all configured review obligations are complete. Add tests that zeroed, provenance, high-drop, missing-data, and needs-followup items keep the run out of the ready state.

### U003 — Batch eligibility is underspecified and can still accept risky cases
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:198
Rationale: The RFC forbids batch actions for zeroed, provenance, and high-drop segments, but permits them for "unchanged or explicitly low-risk items" without defining low-risk. Count-changed, newly-nonzero, predicate-mix, and missing-detail cases can all look low-risk in aggregate while still being exactly the cases the workbench exists to prevent from slipping through. The danger is amplified by filtered queue views, where the operator may not notice that a broad action spans hidden risk tags.
Suggested fix: Define batchable eligibility mechanically: no risk tags, complete data availability, no candidate/prior count delta, no predicate delta, no provenance warning, and no prior review conflict. Batch actions should have a preview listing affected IDs and excluded IDs by reason, and should write a batch audit row. In v1, consider limiting batch to "mark unchanged as skipped" rather than any acceptance-like decision.

### U004 — Verdict labels remain ambiguous across different delta types
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:218
Rationale: "Good drop" is clear only for a dropped prior claim, not for newly-nonzero, predicate-mix, count-changed, or missing-data segments. "Regression" can mean the candidate run is worse, the prior extraction was better, or the source segment itself exposed bad prior state. "Skip" does not say whether the item is excluded from promotion readiness, deferred, or intentionally ignored. These labels encode project context that the operator must remember.
Suggested fix: Give each verdict a consequence label and scope. For example: "Accept candidate change," "Flag candidate regression," "Park for follow-up," and "Exclude from this review," with a one-line explanation visible beside or beneath each control. If "Good drop" remains, restrict it to dropped-claim review rows and use a different segment-level verdict for whole-segment acceptance. The summary and export should preserve the same plain-language labels.

### U005 — The primary screen still asks the reviewer to synthesize too many visual states
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:204
Rationale: The proposed screen includes progress, risk chips, metadata, excerpt, prior rows, candidate rows, dropped reasons, verdict controls, prompt version, and privacy messaging. That is better than Markdown, but it still makes the reviewer visually merge several regions to answer the core questions: what changed, why should I care, and what do I do next. Risk chips also mix statuses with deltas, and if color or chip order carries meaning, the state can become overloaded.
Suggested fix: Add a required top "change summary" block that states the concrete delta, data completeness, highest risk reason, and recommended review obligation in plain language before the rows. Rows should be grouped as removed, retained, added, and unavailable rather than requiring side-by-side mental diffing. Use chips only as secondary filters, not as the primary explanation. Add HTML contract tests that the segment page includes a concrete delta sentence and data-completeness state before verdict controls.

### U006 — Resume support lacks enough state for a tired operator to stop cleanly
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:148, docs/rfcs/0029-bench-triage-workbench.md:245
Rationale: The route table mentions last decision and a resume link, but the review schema stores only decisions by segment. It does not store the active queue, current filter, sort order, current segment, draft note, last viewed risk group, or whether the operator was in the middle of a batch preview. Resuming at "last decision" is not equivalent to resuming the work session; the reviewer may need to reconstruct what they had intentionally parked.
Suggested fix: Add session-level UI state for active queue, stable queue order/version, current segment, last undecided segment, draft note timestamp, and last batch preview state. The landing page should have explicit resume choices: continue next unresolved item, revisit needs-followup, revisit skipped, and open summary. Add tests that a partially reviewed session resumes to the next unresolved item without changing prior decisions.

### U007 — Notes are treated as private state until export, but included notes can leak raw text
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:167, docs/rfcs/0029-bench-triage-workbench.md:279, docs/rfcs/0029-bench-triage-workbench.md:344
Rationale: The RFC correctly omits segment and claim text from review state columns, but free-form notes can still contain private excerpts typed by the reviewer. The export path allows notes with a flag, while the default tests only prove notes are omitted by default. That makes privacy depend on the operator remembering not to paste local evidence into a note that later becomes tracked.
Suggested fix: Treat notes as private by default even when exports are requested. Add a separate optional "redacted export note" field or require an explicit per-note redaction confirmation before notes can leave scratch. If `--include-notes` remains, it should refuse tracked `docs/reviews/` output unless a stronger flag acknowledges that notes may contain private text. Add tests with note content that resembles source text to prove default and tracked exports do not include it.

### U008 — Single-key shortcuts can cause accidental decisions
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md:224
Rationale: The RFC says keyboard review is supported without being required, which is good, but the single-letter decision keys are dangerous if focus handling is not specified. A reviewer typing in notes, search, browser find, or an expanded excerpt could accidentally submit a verdict. The risk is not that shortcuts exist; it is that the RFC does not say whether they preview, focus, or immediately write state.
Suggested fix: Specify that decision shortcuts are disabled while any input, textarea, select, or contenteditable element has focus. For destructive or acceptance-like verdicts, the first keypress should focus the relevant button and the second should submit, or the UI should provide immediate undo with visible saved state. Add tests for focused inputs and for visible post-decision confirmation.

### U009 — Acceptance criteria do not yet test the usability contract
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:332
Rationale: The acceptance criteria cover loaders, classifiers, storage, routes, privacy rejection, export redaction, CLI validation, and no network calls. They do not assert that decisions are visible after save, that ambiguous data states block unsafe verdicts, that batch actions exclude hidden risky items, that promotion readiness is blocked by unresolved cases, or that resume behavior is deterministic. Those are the usability regressions most likely to recreate the Markdown workflow's cognitive overhead inside a web UI.
Suggested fix: Add UI-level contract tests for visible current decision, changed-decision warnings, unavailable-data blocking, safe-promotion blockers, batch preview exclusions, resume target selection, shortcut focus safety, and redacted export behavior. Manual acceptance should include an interrupted review: decide several items, park one item, close the server, restart, and verify the operator lands on the correct next action without rereading prior context.

## Open questions

1. Is "safe to promote" intended to be a purely derived readiness state, or an explicit run-level owner decision recorded after segment review completes?
2. Will v1 ever display candidate claim detail when the benchmark run was created with redacted segment JSONL, and if so, from which local artifact is that detail recovered?
3. Should "skip" remove an item from promotion readiness, defer it, or mark it as intentionally not reviewed?
4. Are batch actions needed in v1, or can they wait until the non-batch review flow proves that risk tags and resume behavior are unambiguous?

verdict: needs_revision
