# Spec 0029 Bench Triage Workbench Findings Ledger
author: ledger-codex-gpt-5.5-002

Status: findings
Date: 2026-05-09
RFC refs: RFC-0029
Spec refs: SPEC-0029
Decision refs: D020, D074, D-082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### L001 - Artifact field mapping remains implicit
Severity: major
Sources: REVIEW_codex F001
Disposition target: accept
Rationale: The spec defines normalized dataclasses but not source aliases,
coercions, duplicate-row handling, run-id fallback, or row unusability rules.
Without those rules, loaders can differ across agents.

### L002 - Data-state precedence is not deterministic
Severity: major
Sources: REVIEW_codex F002; REVIEW_claude F002
Disposition target: accept
Rationale: Several data states overlap. The spec needs an ordered precedence
ladder so every row receives exactly one state and queue ordering is stable.

### L003 - Rationale storage can receive private pasted text
Severity: major
Sources: REVIEW_codex F003; REVIEW_claude F001
Disposition target: accept
Rationale: The scratch DB has no raw segment or claim columns, but free-form
rationale fields can still store pasted excerpts. The implementation contract
needs a sanitizer, length cap, and no-automatic-copy invariant.

### L004 - CLI failure behavior is underspecified beyond non-loopback serve
Severity: minor
Sources: REVIEW_codex F004
Disposition target: accept
Rationale: The serve non-loopback exit code is fixed at 8, but export/status
and malformed input failures are unspecified. The spec should state whether
they use standard argparse/framework nonzero behavior.

### L005 - Tests miss determinism and privacy edge cases
Severity: major
Sources: REVIEW_codex F005; REVIEW_claude F003
Disposition target: accept
Rationale: Required tests should cover data-state precedence, duplicate segment
rows, stable queue ordering, redacted/prior-missing controls, rationale
sanitization, and the production-read-only boundary.

### L006 - Candidate versions are not materialized in review_sessions
Severity: minor
Sources: REVIEW_gemini F001
Disposition target: accept
Rationale: Review sessions reference the run artifact but do not materialize
candidate prompt/model/request-profile versions. Storing them makes redacted
exports and status output self-contained if scratch run artifacts move.

### L007 - Forward compatibility with engramd is unspecified
Severity: nit
Sources: REVIEW_gemini F002
Disposition target: defer
Rationale: The missing RFC 0022 migration note is useful but not necessary for
v1 implementation. It can be captured as a short non-blocking note if touched.

### L008 - Run decision wording can overstate promotion authority
Severity: major
Sources: REVIEW_usability_adversary U001
Disposition target: accept
Rationale: `safe_to_promote` can be read as bypassing other gates. UI/export
copy should label it as a bench-review decision and explicitly state that it
does not mutate production data or bypass Phase 4 gates.

### L009 - Incomplete data states need state-specific instructions
Severity: major
Sources: REVIEW_usability_adversary U002
Disposition target: accept
Rationale: Banners and disabled controls are not enough. Missing, malformed,
redacted, and prior-missing states need direct one-line guidance.

### L010 - Parked work needs first-screen visibility
Severity: minor
Sources: REVIEW_usability_adversary U003
Disposition target: accept
Rationale: Resume ergonomics require above-the-fold counts and filters for
undecided, needs-follow-up, regression-flagged, and excluded rows.

## Consensus

All lanes accept Spec 0029 with findings. The consensus is that the spec is
buildable after tightening deterministic loader/state behavior, rationale
privacy, run-decision wording, and tests.

## Conflicts

No substantive conflicts. Gemini's `engramd` note is deferred because it is not
needed to build v1.

## Recommended next action

Revise Spec 0029 before implementation. The apply pass should update artifact
mapping, data-state precedence, review-session schema, rationale sanitization,
UX wording, and tests, then proceed to final review.

