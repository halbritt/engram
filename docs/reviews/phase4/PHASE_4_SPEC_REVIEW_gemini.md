# Phase 4 Build-Spec Review — gemini

author: reviewer-gemini-3.1-pro-preview-001
Status: review
Date: 2026-05-08
RFC refs: RFC-0007, RFC-0011, RFC-0018, RFC-0024
Decision refs: D006, D017, D020, D023, D044, D052, D068, D069
Phase refs: PHASE-0004

## Findings

### F001 — HITL queue semantics are too thin for user trust
Severity: major
Source: BUILD_PHASES.md:242-247; DECISION_LOG.md#d006; DECISION_LOG.md#d044
Rationale: The queue action list is correct but incomplete. A user-facing review surface needs to show why a belief is in the queue, its evidence, confidence, stability class, contradiction state, audit warnings, and what each action will do before the action mutates lifecycle state.

### F002 — `correct` needs an explicit lifecycle from capture to replacement belief
Severity: major
Source: DECISION_LOG.md#d017; BUILD_PHASES.md:242-247; HUMAN_REQUIREMENTS.md:591-605
Rationale: D017 says corrections are raw captures, not belief edits. The review surface must define how a correction capture links to the bad belief, how reprocessing is queued, how the old belief is marked while awaiting replacement, and how the UI prevents the user from mistaking "correction captured" for "memory fixed."

### F003 — Concurrent review and duplicate actions are unaddressed
Severity: major
Source: DECISION_LOG.md#d052; BUILD_PHASES.md:204-207; BUILD_PHASES.md:242-249
Rationale: Phase 4 can plausibly have multiple queue clients, retries, or stale screens. The spec should require optimistic locking or transition preconditions so two actions on the same belief cannot both appear to succeed, and every no-op retry should still be explainable.

### F004 — Privacy tier handling must be visible in review and entity views
Severity: major
Source: HUMAN_REQUIREMENTS.md:607-616; DECISION_LOG.md#d023; RFC-0024:220-239
Rationale: Phase 4 surfaces beliefs and canonical entities to a human reviewer and later feeds Phase 5. The queue and entity views need privacy-tier labels, reclassification behavior, and redacted reporting rules; otherwise low-tier derived rows can remain visible after a raw-row reclassification or leak private belief/entity names into committed reports.

### F005 — Queue ordering is not specified even though D055 makes rebuild IDs unstable
Severity: minor
Source: DECISION_LOG.md#d055; RFC-0018:195-201; BUILD_PHASES.md:242-249
Rationale: A review queue sorted by row creation or UUID will behave poorly after rebuilds that preserve structure but create new IDs. Ordering should prefer review value: contradictions, audit-invalidated contributing claims, low confidence, high stability class, high privacy tier, and recent correction/reclassification events.

### F006 — The local-first invariant should apply to the review harness too
Severity: minor
Source: HUMAN_REQUIREMENTS.md:90-119; HUMAN_REQUIREMENTS.md:153-170; DECISION_LOG.md#d020
Rationale: The workflow lanes name hosted model families, while the workflow constraints say network is forbidden. The Phase 4 process should either run reviewers locally or explicitly record that external review is an owner-approved export; otherwise the review process itself violates the principle it is reviewing.

## Open questions

- What exact evidence fields does the review queue show without overwhelming the reviewer?
- How does the UI label a correction that has been captured but not yet reprocessed?
- Which queue actions are idempotent, and what does the user see on stale action attempts?
- Does the first Phase 4 build ship CLI review only, or is a web review surface required for acceptance?

verdict: accept_with_findings
