# Spec 0029 Bench Triage Workbench Revision Handoff
author: author-codex-gpt-5.5-002

Status: revised
Date: 2026-05-09
RFC refs: RFC-0029
Spec refs: SPEC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Changes made

- Added deterministic candidate run and segment-record field aliases.
- Added count coercion, duplicate segment handling, and unusable-row rules.
- Added explicit data-state precedence and stable queue ordering.
- Added candidate prompt/model/request-profile version columns to
  `review_sessions`.
- Added rationale sanitization, length cap, and no-automatic-private-copy
  invariant.
- Clarified CLI failure behavior outside the fixed non-loopback exit 8 case.
- Scoped the `safe_to_promote` run decision to bench-review copy.
- Required incomplete-state instructions and first-screen resume counts.
- Expanded required tests for determinism, privacy, UX, and production-write
  boundary coverage.

## Findings addressed

Accepted findings L001, L002, L003, L004, L005, L006, L008, L009, and L010
were addressed in the spec.

## Findings deferred

L007, the `engramd` forward-compatibility note, remains deferred because it is
not needed for the v1 local FastAPI implementation.

## Validation run

- `.venv/bin/striatum workflow validate striatum/rfc-0029-bench-triage-workbench-spec/workflow.json`

## Residual risk

Historical benchmark artifacts may still expose fields outside the accepted
alias set. The implementation should keep unsupported rows in
`candidate_malformed` instead of expanding aliases without a reviewed reason.

