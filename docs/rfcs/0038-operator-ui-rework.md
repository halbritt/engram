<a id="rfc-0038"></a>

# RFC 0038: Operator UI Rework

| Field | Value |
|-------|-------|
| RFC | RFC-0038 |
| Title | Operator UI Rework |
| Status | proposal |
| Implementation | none |
| Created | 2026-05-13 |
| Source | `ENGRAM_UI_REWORK_HANDOFF.md` |
| Context | RFC 0021, RFC 0027 / Spec 0027, RFC 0028, RFC 0029, D016, D020, D044, D069, D074, D080, D081 |

## Summary

This RFC proposes an implementation pass for the Engram operator web UI,
using `ENGRAM_UI_REWORK_HANDOFF.md` as the implementation-ready design
contract. The pass unifies the current Phase 3 gold-set interview UI and
bench triage workbench under a shared local-first operator visual system while
preserving their separate domain boundaries, route contracts, and storage
contracts.

The intended result is a local memory-governance workbench: dense, readable,
server-rendered, and precise about claim state. It is not a marketing surface,
not a hosted app, and not a promotion authority for derived memories.

## Goals

1. Build a shared Engram web UI substrate for local operator surfaces:
   typography, spacing, status chips, audit footer, error banners, future-slot
   markers, and no-CDN static delivery.
2. Rework the gold-set interview UI so one claim or belief can be reviewed
   with visible provenance, predicate intent, subject-kind warnings, privacy
   tier, rationale requirements, and session progress.
3. Rework the bench triage UI so prior/candidate deltas, queue state,
   readiness, redaction, and scratch-local decision posture are visible without
   implying production mutation or gate approval.
4. Preserve CLI ownership for export/history/coverage actions by surfacing
   exact CLI guidance rather than adding web mutations outside the accepted
   contracts.
5. Add acceptance checks for responsive layout, htmx fragments, accessibility,
   no-CDN/no-network behavior, and truthful status language.

## Non-Goals

- No cloud service, telemetry, hosted auth, CDN asset, remote storage, or
  non-loopback web binding.
- No Phase 4 entity-review implementation, full-corpus authorization, or
  promotion flow.
- No change to the advisory nature of gold labels under D044/D069.
- No change that makes bench-review scratch decisions feed production claims,
  beliefs, audits, raw evidence, or Striatum gates.
- No tenant-aware memory ingestion or RFC 0044 implementation work.
- No JavaScript framework or build pipeline.

## Required Implementation Slices

The implementation should be split into three independent lanes with disjoint
write scopes where possible:

1. **Shared web substrate**
   - Add a small `src/engram/web/` package for shared Jinja partials, CSS
     tokens, local-only/audit footer copy, status-chip semantics, and future
     slot rendering.
   - Add tests that prove shared assets are package-local and do not reference
     external URLs.
2. **Interview surface**
   - Update `src/engram/interview/templates/`,
     `src/engram/interview/web.py`, and `src/engram/interview/render.py`
     only as needed to implement the handoff's interview IA and state rules.
   - Preserve all existing session-state, CSRF, Origin/Sec-Fetch, Tier 1, and
     closed-session guards.
3. **Bench-review surface**
   - Update `src/engram/bench_review/templates/`,
     `src/engram/bench_review/web.py`, and related bench-review tests only as
     needed to implement the handoff's queue, segment-detail, readiness, and
     decision-state rules.
   - Preserve scratch-local review state and production-read-only posture.

After the three implementation lanes complete, an integration/test lane should
run the focused route/template/static checks and produce evidence before
review.

## Review Requirements

Use the standard multi-agent review loop, augmented with a dedicated
ergonomics design review:

- privacy/local-first/security review;
- implementation correctness review;
- operator contract/truthfulness review;
- ergonomics design review focused on layout density, decision cost,
  keyboard flow, responsive behavior, and warning comprehension.

The findings ledger must keep design/ergonomics findings separate from
security or correctness findings unless they share the same root cause.

## Acceptance Criteria

- Existing interview and bench-review route tests pass.
- New or updated tests assert no external static asset references.
- htmx fragment behavior remains tested for interview verdict/rationale flows
  and bench segment decisions.
- The interview UI visibly distinguishes `true`, `false`, `stale`,
  `unsupported`, `unsure`, and `skip`; rationale-required verdicts remain
  route-enforced.
- The bench UI visibly distinguishes accepted, candidate, reviewed, blocked,
  redacted, unavailable, failed, and future/backlog states.
- Phase 4 and RFC 0044 references render only as future/backlog or
  non-authorizing context.
- Responsive browser checks cover desktop and narrow-screen layouts for one
  interview question and one bench segment-detail page.
- Keyboard/accessibility checks cover verdict controls, rationale focus,
  queue navigation, status-chip labels, and disabled future links.

## Open Questions

1. Should the shared `src/engram/web/` substrate be adopted by future Phase 4
   entity-review UI as the default chrome, or remain Phase 3-only until a
   Phase 4 RFC accepts it?
2. Should responsive screenshot tests be implemented with Playwright now, or
   should this pass emit a manual screenshot checklist while route/template
   tests stay in pytest?
