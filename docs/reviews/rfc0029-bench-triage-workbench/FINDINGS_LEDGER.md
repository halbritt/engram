# RFC 0029 Bench Triage Workbench Findings Ledger
author: ledger-codex-gpt-5.5-001

Status: findings
Date: 2026-05-09
RFC refs: RFC-0029
Decision refs: D020, D074, D-082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### L001 - Require segment records for triage mode and separate missing data from semantic zero
Severity: blocking
Sources: Codex F001; Usability U001; Gemini F004
Disposition target: accept
Rationale: The RFC treats candidate segment-result JSONL as optional and says
the UI shows candidate absence, but the workbench cannot classify or review
zeroed/count-changed/predicate/provenance deltas from aggregate `run.json`
alone. The UI must distinguish candidate emitted zero claims, candidate detail
redacted/unavailable, and artifact missing/invalid. Semantic verdicts must be
disabled or downgraded when data is unavailable.

### L002 - Prior extraction comparison must use the full version triple
Severity: major
Sources: Codex F002
Disposition target: accept
Rationale: A prompt-only `--prior-version` can silently mix extraction rows
across model or request-profile versions. The CLI and loader should require a
full prior extraction identity or derive one from an explicit prior run
artifact, and reject ambiguous matches.

### L003 - Candidate claim display needs redacted and private-detail modes
Severity: major
Sources: Codex F003; Usability U001
Disposition target: accept
Rationale: Default benchmark artifacts intentionally omit raw candidate
subject/object/rationale text. The RFC should not promise full candidate
subject/object rows from redacted `segments.jsonl`. It needs a redacted mode
using structured non-text fields and an explicit private-detail mode when the
operator supplies local claim-text artifacts. Tracked exports remain redacted
in both modes.

### L004 - Export should be CLI-only in v1 and path hardened
Severity: major
Sources: Claude F003, F004, F005; Codex F004; Gemini F002; Usability U007
Disposition target: accept
Rationale: A browser route writing into `docs/reviews/` is unnecessary and
crosses the scratch-to-tracked boundary from a local web form. V1 should drop
`POST /export`; tracked export should be an explicit CLI command with a named
`--output` path under `docs/reviews/`, no `--allow-outside-reviews`, path
resolution checks, no notes by default, and a recorded note-inclusion warning
if any future private export mode exists.

### L005 - Match RFC 0027's web security posture exactly
Severity: major
Sources: Claude F001, F002, F007, F008, F009, F010
Disposition target: accept
Rationale: RFC 0029 should inherit RFC 0027's concrete local-web contract:
Tier 1 route ceiling with no v1 escape clause, loopback-only bind with exit 8
and no non-loopback flag, Origin allowlist and `Sec-Fetch-Site` checks on
mutating routes, vendored htmx under the package static path, package-data
shipping checks, and no CDN asset references. Shared helper extraction should
be narrow and named.

### L006 - Replace "safe to promote" with explicit promotion readiness semantics
Severity: major
Sources: Usability U002; Gemini F003; Claude open question
Disposition target: accept
Rationale: The RFC's "safe to promote" phrase risks false confidence because
schema/provenance can be green while semantic review remains unresolved.
Rename the surface to promotion readiness, define states such as blocked,
review incomplete, ready for owner decision, and promoted by run-level
decision, and record a run-level decision separately from derived readiness.

### L007 - Define batch eligibility mechanically or defer acceptance-like batch actions
Severity: major
Sources: Usability U003
Disposition target: accept
Rationale: "Explicitly low-risk" is not enough for tired-reviewer safety.
Batch actions must be limited to complete-data, no-risk, unchanged items, with
preview and exclusions by reason. V1 can safely limit batch to skipping
unchanged items or defer batching entirely.

### L008 - Clarify verdict labels and skip semantics
Severity: major
Sources: Usability U004; Gemini open question
Disposition target: accept
Rationale: "Good drop", "regression", and "skip" are ambiguous across segment
delta types. The UI should use consequence-oriented labels or restrict
drop-specific labels to dropped-claim cases, and the RFC must define whether
skip counts as reviewed, deferred, or excluded from readiness.

### L009 - Add a top-level change summary and reduce screen memory load
Severity: major
Sources: Usability U005
Disposition target: accept
Rationale: The proposed screen has better structure than Markdown but still
requires the reviewer to mentally combine risk chips, prior rows, candidate
rows, excerpts, and counts. Each segment page should start with a plain
language change summary: what changed, data completeness, highest risk, and
required next action.

### L010 - Persist enough UI state for clean stop/resume
Severity: major
Sources: Usability U006
Disposition target: accept
Rationale: Storing only per-segment decisions is not enough to resume a tired
work session. The scratch store should capture active queue/filter/order,
current segment, last unresolved segment, draft note metadata, and enough state
for the landing page to offer explicit resume choices.

### L011 - Keyboard shortcuts need focus-safety and collision handling
Severity: minor
Sources: Gemini F001; Usability U008
Disposition target: accept
Rationale: Single-letter shortcuts help throughput but can collide with RFC
0027 habits and can accidentally submit decisions while typing. The RFC should
avoid `f` for follow-up or explicitly choose a non-conflicting key, disable
decision shortcuts while input-like elements have focus, and require visible
post-decision confirmation or undo.

### L012 - Expand acceptance tests to cover usability contracts
Severity: major
Sources: Usability U009; Claude F009; Codex F004
Disposition target: accept
Rationale: Existing acceptance criteria cover loaders, routes, storage, and
redaction, but not the UI semantics that prevent a return to Markdown-level
cognitive load. Tests should cover data-availability blocking, visible saved
decisions, readiness blockers, batch preview exclusions, deterministic resume,
shortcut focus safety, no-CDN rendering, and hardened export paths.

### L013 - Resolve command placement in the follow-on spec
Severity: minor
Sources: Codex F005; Gemini F002
Disposition target: accept
Rationale: `phase3 bench-review` is right for extraction/re-extraction review,
but the RFC also references Phase 4 gates. The RFC should state that v1 is
canonical under `engram phase3 bench-review` for extraction artifacts and any
Phase 4 alias requires Phase 4 artifact support in a follow-on spec. Export
should use a concrete `--output` flag.

### L014 - Keep scratch SQLite as the v1 boundary and reaffirm no production derivation use
Severity: nit
Sources: Claude F006
Disposition target: accept
Rationale: Scratch SQLite is the right v1 storage boundary. The RFC should
explicitly say benchmark-review decisions do not feed extraction,
consolidation, interview, or other production derivations.

## Consensus

All lanes agree the RFC is directionally valuable and addresses a real
operator bottleneck. The high-severity convergence is around making data
availability explicit, tightening the scratch-to-tracked export boundary, and
turning "safe to promote" into auditable readiness semantics. The
adversarial usability review found the most important missing UX contract:
without clearer state, the web UI can recreate the Markdown review's mental
load inside a browser.

## Conflicts

The only material conflict is process posture: Gemini accepted the RFC as-is
with minor findings, while Codex and the adversarial lane requested revision.
The ledger resolves that by accepting the revision findings and continuing
autonomously, because the user requested progress without a human checkpoint.

## Recommended Next Action

Revise RFC 0029 before implementation. Required edits: require segment records
for triage mode, define data-availability states, change export to CLI-only,
match RFC 0027 security language, replace safe-to-promote wording, define
batch/verdict/resume semantics, and expand tests to cover usability behavior.
