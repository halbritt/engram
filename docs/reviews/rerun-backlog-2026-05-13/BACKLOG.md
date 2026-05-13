# Fresh Rerun Backlog

Date: 2026-05-13

This backlog synthesizes the fresh rerun evidence produced after RFC 0032. It is
an execution queue, not promotion authority. Items remain blocked for promotion
until their originating review findings are resolved by implementation, revised
RFC/spec text, fresh review, or an explicit operator decision.

## Dependency Order

1. Preserve trust reset and provenance discipline from RFC 0032.
2. Resolve RFC 0021/RFC 0027 contract blockers before using their historical
   promotion decisions as fresh Phase 4 gate evidence.
3. Resolve RFC 0028 prompt provenance and warning behavior before any
   non-scratch extraction writes rows under
   `extractor.v9.d082.predicate-intent`.
4. Revise RFC 0029 design before spec or implementation reruns.
5. Treat Phase 4 bounded evidence-fix work as non-promoting until Tier 0, Tier
   1 human-label evidence, review-action evidence, and projection/provenance
   blockers are cleared.

## Parallel Lanes

| Lane | Scope | Inputs | Blocking Outcome |
|---|---|---|---|
| RFC 0028 implementation fix | Prompt artifact/provenance and ambiguous entity warning behavior. | `docs/reviews/rfc0028-predicate-intent-promotion-2026-05-13/REVIEW_codex.md` | Fresh promotion remains blocked until focused fixes pass and review reruns clear the findings. |
| RFC 0027 web/UI fix | Tier ceiling, mutating routes, CSRF contract, message reachability, frozen session target behavior, and baseline docs. | `docs/reviews/rfc0027-rerun-2026-05-13/RFC_0027_INTERVIEW_WEB_UI_REVIEW_codex.md` | RFC 0027 remains a real `needs_revision` checkpoint until privacy/state blockers are resolved or waived. |
| RFC 0021 contract revision | Align RFC text with implementable schema/code for synthetic audit, session targets, belief version stamps, strata validation, and stale status wording. | `docs/reviews/rfc0021-rerun-2026-05-13/` | RFC 0021 historical acceptance should not be treated as freshly cleared until revised and re-reviewed or explicitly waived. |
| RFC 0029 design revision | Make the design persistable, resumable, redaction-safe, and unambiguous about readiness/promotion states. | `docs/reviews/rfc0029-bench-triage-workbench-design-2026-05-13/` | RFC 0029 spec/implementation reruns remain downstream of design revision. |
| Phase 4 evidence-fix scaffold | Define the next bounded evidence package without full-corpus execution. | `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/` | Full-corpus Phase 4 remains blocked until a later accepted gate decision. |
| RFC 0044 Engram memory Phase 1 queue | Scaffold future tenant-aware Striatum memory integration without starting implementation. | `/home/halbritt/git/striatum/ENGRAM_DEVELOPER_REQUEST.md`, `/home/halbritt/git/striatum/docs/rfcs/0044-engram-phase-1-implementation-spec.md` | Future implementation remains blocked until the tenant terminology handoff is produced and read. |

## Backlog Items

### B001 - RFC 0028 Prompt Provenance

Add the governed extraction-prompt artifact for
`extractor.v9.d082.predicate-intent`, or replace the decision-tagged version
with a clearly non-promoting proposal tag. `D082` is currently only a proposed
reservation.

### B002 - RFC 0028 Subject-Kind Warning

Suppress person-only subject warnings when the active entity set includes a
person row for the same canonical key, and add a deterministic regression test
covering mixed person/non-person rows.

### B003 - RFC 0027 Question-Page Tier Ceiling

Ensure the question page cannot render Tier 2+ evidence excerpts before the
operator reaches the guarded full-message/context routes.

### B004 - RFC 0027 Mutation And CSRF Contract

Remove the final-question mutating GET path and either enforce or precisely
document the actual Origin/Sec-Fetch behavior with tests.

### B005 - RFC 0027 Evidence-Scoped Reachability

Constrain full-message rendering to messages reachable from the session target's
cited evidence rather than any message in the conversation.

### B006 - RFC 0027 Frozen Target Resume

Make web resume and completion behavior respect the materialized target version
triple. Pre-011 sessions without materialized targets should not be silently
marked complete.

### B007 - RFC 0021 Contract Truthfulness

Revise RFC 0021 so the synthetic-audit trigger, candidate-pool snapshot,
belief-side request profile, and strata validation claims match implementable
schema/code or are explicitly assigned to follow-up work.

### B008 - RFC 0029 Design Revision

Revise RFC 0029 around persistable prior-run artifacts, queue fingerprints,
redacted identifiers, read-only DB enforcement, follow-up queues, readiness
language, and promotion/exclusion semantics.

### B009 - Phase 4 Evidence-Fix Scaffold

Create a bounded, privacy-preserving evidence-fix workflow/report that clears
the next evidence gaps without authorizing full-corpus Phase 4.

### B010 - RFC 0044 Tenant-Aware Memory Integration Queue

Queued scaffold only at
`striatum/rfc-0044-engram-memory-phase1-tenant-isolation-2026-05-13/`.
The workflow requires a tenant terminology/RFC-amendment handoff before any
implementation, then implementation, capability-boundary tests, independent
reviews, findings ledger, and final synthesis. Do not start the workflow until
the operator explicitly authorizes execution.

### B011 - Focused Re-Review Queue

Queued scaffold only at
`striatum/rerun-backlog-focused-reviews-2026-05-13/`. It fans out five
independent review jobs for RFC 0028, RFC 0027, RFC 0021, RFC 0029, and the
Phase 4 evidence-fix scaffold, then records a ledger if those reviews accept or
accept with findings. Review artifacts remain evidence only, not promotion
authority.

### B012 - Interview CLI Test Fixture Repair

The full local suite exposed one regression in
`tests/test_interview_cli.py::test_phase3_interview_start_writes_session_targets`.
The repaired fixture now seeds real claim and belief parent rows before
materializing session targets, preserving the RFC 0027 storage guard instead of
weakening parent/version validation.

## Review Gate

After the implementation/documentation lanes land, rerun focused review rather
than promoting directly. Minimum review gates:

- RFC 0028: focused implementation review across prompt provenance and warning
  regression.
- RFC 0027: privacy/state review of the web surface and session-target
  behavior.
- RFC 0021: RFC contract re-review.
- RFC 0029: design re-review before any spec/implementation rerun.
- Phase 4: evidence-fix review that explicitly states whether it remains
  non-promoting.
