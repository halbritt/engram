# Spec 0029 Bench Triage Workbench Revision Synthesis
author: synthesizer-codex-gpt-5.5-001

Status: synthesis
Date: 2026-05-09
RFC refs: RFC-0029
Spec refs: SPEC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Decision

Revise Spec 0029 before implementation. The spec remains accepted for build
after the revision, but accepted findings must be folded into the contract so
builders do not rediscover loader, queue, privacy, and UX rules.

## Accepted findings

- L001: define source field aliases, coercions, duplicate row handling, run-id
  fallback, and unusable-row rules.
- L002: define a single data-state precedence ladder and stable queue
  tie-breakers.
- L003: define rationale sanitizer, maximum length, and no-automatic-copy
  invariant.
- L004: state standard nonzero behavior for export/status/input failures.
- L005: expand tests for determinism, duplicate rows, privacy sanitization, and
  production-read-only boundaries.
- L006: add candidate prompt/model/request-profile versions to
  `review_sessions`.
- L008: soften `safe_to_promote` UI/export wording to bench-review scope.
- L009: require state-specific instructions for incomplete data states.
- L010: require first-screen resume counts and filters.

## Rejected findings

None.

## Deferred findings

- L007: `engramd` forward-compatibility note. This is useful context but not
  required for v1 build. The implementation can remain a narrow FastAPI app
  matching Spec 0027's current local-web posture.

## Required spec edits

1. In `Inputs`, add accepted source field aliases and row parsing rules for run
   artifacts and segment records, including duplicate segment handling.
2. In `Data Availability`, add explicit precedence from malformed/missing data
   through complete states and define `candidate_zero` as a state derived from
   an otherwise complete candidate/prior comparison.
3. In `Classification`, define risk ordering as first tag rank plus
   lexicographic `segment_id` tie-break.
4. In `Scratch SQLite State`, add candidate version columns and define
   rationale sanitization, max length, and storage/export privacy invariant.
5. In `CLI`, state that all non-loopback serve attempts exit 8 and other
   validation/runtime failures use the existing CLI framework's ordinary
   nonzero error behavior.
6. In `UX Contract`, require state-specific next-action text, bench-scoped run
   decision labels, and first-screen resume counts.
7. In `Tests`, add deterministic parsing, precedence, duplicate, sanitizer,
   route privacy, resume-count, and no-production-write tests.

## Required follow-up artifacts

The apply pass should publish `REVISION_HANDOFF.md` summarizing the edits and
recording any residual build risk. No owner question is required before moving
to implementation after final review.

