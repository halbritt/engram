# Spec 0029 Bench Triage Workbench Adversarial Usability Review
author: usability-adversary-codex-gpt-5.5-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0029
Spec refs: SPEC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### U001 - Primary-screen contract is too narrow to guarantee every screen answers the three triage questions
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md#UX Contract
Rationale: The spec says "The primary screen must answer three questions," but then defines the primary screen as a generic contract and gives concrete details that mostly map to the run summary and segment screen. It does not explicitly bind the run summary, filtered queue, one-segment view, and completion summary to "what changed, why should I care, what do I do next." A tired operator can still land on `/segments` or `/summary` and see a browser-shaped report: counts, filters, or a run verdict form without a clear local next action and without enough explanation of the highest-risk unresolved delta.
Suggested fix: Make the UX contract screen-specific. Require `/` to show top changed/risky buckets and the next queue entry, `/segments` to show why the current filtered queue matters and the next unresolved item, `/segments/{segment_id}` to show the segment's delta and permitted action, and `/summary` to show unresolved blockers before the run-level decision. Add acceptance tests that assert these labels or landmarks exist on each primary route.

### U002 - Verdict labels are plain, but the risk semantics are not obvious enough at the decision point
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md#Scratch SQLite State; docs/specs/0029-bench-triage-workbench-spec.md#UX Contract
Rationale: The segment labels are readable, but they rely on the reviewer already knowing the behavioral consequence of each decision. "Accept candidate change" is especially risky because it can read as approving the segment rather than approving this delta as harmless. "Exclude from review" can also be mistaken for "hide this annoying case" unless the UI states that it removes the segment from run-verdict influence. The spec requires compact badges, but not decision-adjacent helper text that ties each verdict to its downstream effect.
Suggested fix: Require each segment decision control to render a short consequence label in the form itself, such as "counts toward promotion readiness," "blocks promotion until resolved," "parks this segment outside promote/block counts," and "removes this artifact/slice case from verdict math." Keep the stored vocabulary unchanged, but test the rendered form for consequence text and not just the raw option labels.

### U003 - Run-level "safe to promote" can create false confidence while unresolved uncertainty remains
Severity: blocking
Source: docs/specs/0029-bench-triage-workbench-spec.md#Scratch SQLite State; docs/specs/0029-bench-triage-workbench-spec.md#Acceptance
Rationale: The run decision vocabulary includes `safe_to_promote`, but the spec does not require the UI or storage layer to prevent that verdict when high-risk, incomplete, or undecided segments remain. The acceptance criteria only say the workbench can triage rows and persist progress, not that a safe verdict is guarded. Given the stated operator condition, this is the highest usability risk: a reviewer can misread a partial review as sufficient and export a tracked summary that overstates readiness.
Suggested fix: Rename the visible label to something less absolute, such as "No reviewed blockers found," or require a confirmation gate that lists remaining undecided, `needs_followup`, incomplete data states, and high-risk tags before allowing `safe_to_promote`. Prefer making `safe_to_promote` disabled until all non-excluded high-risk and incomplete rows have an explicit decision, unless the reviewer records an override rationale that appears in export and status output.

### U004 - Risky cases can still be accepted too easily
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md#Data Availability; docs/specs/0029-bench-triage-workbench-spec.md#Classification; docs/specs/0029-bench-triage-workbench-spec.md#Tests
Rationale: The spec disables accept/regression only for `candidate_missing` and `candidate_malformed`. Other high-risk or weak-evidence states, including `prior_missing`, `candidate_redacted`, `candidate_zero`, `zeroed`, `high_drop_count`, and `provenance_anomaly`, can apparently be accepted with the same friction as an unchanged row. That lets a fatigued reviewer click through the default action path and mark risky or non-comparable cases as acceptable without acknowledging the specific risk.
Suggested fix: Define risk-tier-specific guardrails. For incomplete or high-risk states, require a rationale, a visible warning in the decision form, and a second confirmation before `accept_candidate_change`. At minimum, acceptance tests should verify that `prior_missing`, `candidate_redacted`, `candidate_zero`, `zeroed`, `high_drop_count`, and `provenance_anomaly` render an acceptance warning and require rationale.

### U005 - Parking and resuming uncertain cases is under-specified
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md#Web Routes; docs/specs/0029-bench-triage-workbench-spec.md#UX Contract; docs/specs/0029-bench-triage-workbench-spec.md#Tests
Rationale: `needs_followup`, `remaining=1`, and persisted SQLite state are necessary, but they are not enough to make uncertainty easy to park and resume. The spec does not require a dedicated follow-up queue, age/last-updated ordering, visible rationale snippets, "return to where I left off" behavior, or a summary of parked cases before the run verdict. A reviewer can defer a difficult case and then lose the thread, especially across server restarts.
Suggested fix: Require a first-class "Needs follow-up" queue on `/` and `/summary`, sorted by risk and updated time, with counts, rationale preview, and a direct next-item link. Define that saving `needs_followup` routes to the next unresolved high-risk segment while preserving the parked item in a resumable queue. Add restart/resume tests that verify parked decisions remain visible and actionable after reloading the app.

### U006 - Incomplete data states are named, but their required action is not
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md#Data Availability; docs/specs/0029-bench-triage-workbench-spec.md#UX Contract
Rationale: The data-state model is strong, but the UI requirement only says to show an explicit banner above verdict controls and disable some controls for missing or malformed candidates. It does not require the banner to explain whether the operator should locate a segment artifact, re-run extraction, verify prior version inputs, exclude the case, or mark follow-up. Without state-specific action copy, incomplete rows become another ambiguous badge.
Suggested fix: Add a required action matrix for each non-complete `data_state`. For example, `candidate_missing` should point to the expected segment-record path and suggest checking `--segments`; `candidate_malformed` should name the parse failure and artifact path; `prior_missing` should show the prior prompt/model/request-profile selector values; `candidate_redacted` should say that count-only review cannot support predicate-level acceptance. Test representative banners for state-specific action text.

### U007 - Queue ordering surfaces risk, but filtered views can hide risk context
Severity: minor
Source: docs/specs/0029-bench-triage-workbench-spec.md#Classification; docs/specs/0029-bench-triage-workbench-spec.md#Web Routes
Rationale: The default queue order is risk-aware, but filters can create a local view where a reviewer handles easy rows while higher-risk rows remain unresolved elsewhere. The spec does not require every filtered queue to show "you are viewing N of M; X higher-risk unresolved items are hidden." That omission matters because the workbench exists to avoid overloaded review mistakes, not just to provide filtering power.
Suggested fix: Require `/segments` to show hidden higher-risk unresolved counts whenever filters are active, with a link back to the riskiest queue. Add an acceptance test for an active low-risk filter that verifies the page still exposes hidden high-risk unresolved counts.

### U008 - Acceptance tests do not cover the core usability promises
Severity: blocking
Source: docs/specs/0029-bench-triage-workbench-spec.md#Tests; docs/specs/0029-bench-triage-workbench-spec.md#Acceptance
Rationale: The required tests heavily cover loader tolerance, storage, redaction, route safety, and one disabled-control case. They do not prove that the screens answer the three triage questions, that verdict consequences are visible, that `safe_to_promote` is guarded, that parked cases are resumable, or that incomplete-state banners are actionable. This leaves the highest-risk usability failures outside the implementation contract.
Suggested fix: Add focused HTML-level tests for all primary routes. The test set should assert the presence of "what changed / why care / next action" regions or equivalent landmarks, state-specific incomplete banners, consequence text for each verdict, safe-to-promote blocking or override behavior, follow-up queue persistence after restart, hidden-risk warnings under filters, and required rationale/confirmation for accepting high-risk rows.

## Open questions

- Should `safe_to_promote` remain a stored decision value if the visible UI label is softened, or should the vocabulary itself be renamed before implementation?
- Which segment states must be fully reviewed before any positive run verdict is allowed: all non-excluded rows, only high-risk rows, or only rows with complete candidate/prior data?
- Should `candidate_redacted` ever allow `accept_candidate_change`, or should it always force `needs_followup` or `exclude_from_review` because predicate-level review is unavailable?

verdict: needs_revision
# Spec 0029 Bench Triage Workbench Adversarial Usability Review
author: usability-adversary-codex-gpt-5.5-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0029
Spec refs: SPEC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### U001 - `safe_to_promote` can imply more certainty than the tool owns
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md § Scratch SQLite State; § UX Contract
Rationale: The run decision `safe_to_promote` is easy to read as project-wide approval even though the workbench is only one benchmark-review input. A tired operator may over-trust it when Phase 4 still needs other gates.
Suggested fix: Keep the stored enum if desired, but require the UI/export label to say "Bench review: safe to promote candidate" and show a short note that it does not mutate production data or bypass Phase 4 gates.

### U002 - Incomplete data states need one-line instructions, not just banners
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md § Data Availability; § UX Contract
Rationale: The spec requires state banners and disabled controls, but it does not require the page to tell the operator what action remains valid. For `candidate_missing`, `candidate_malformed`, and `prior_missing`, a tired reviewer needs a clear next step: park for follow-up, exclude, or return to artifact generation.
Suggested fix: Require one-line state-specific action text on the segment screen and include a rendered test for at least missing and malformed candidate states.

### U003 - Parked work is not prominent enough in the resume path
Severity: minor
Source: docs/specs/0029-bench-triage-workbench-spec.md § Web Routes; § UX Contract
Rationale: The workbench is meant to be resumable, but the primary summary contract does not explicitly require counts for `needs_followup` and undecided risky rows above the fold. Without that, the UI can still force the operator to rediscover what remains.
Suggested fix: Require the index and summary screens to show undecided, needs-follow-up, regression-flagged, and excluded counts with direct filters.

## Open questions

None.

verdict: accept_with_findings
