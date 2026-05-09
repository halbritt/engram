# Final Review RFC 0027 Web UI Implementation

Review the completed implementation against `docs/specs/0027-interview-web-ui-spec.md`,
the implementation handoff, and the verification report. Do not modify
implementation files.

## Audit checklist

1. **Origin allowlist enforcement.** All POST routes (verdict, complete,
   save-and-quit, abandon, sessions-create) reject 403 when `Origin` is
   not in the allowlist. Test exists for at least one POST route with
   non-localhost Origin.
2. **Tier 1 ceiling.** `/messages/{id}` and `/messages/{id}/context`
   return 403 for parent tier > 1. `/q/{idx}/evidence/all` enforces the
   same ceiling.
3. **D044/D069 import-graph guard.** A test asserts
   `engram.consolidator.transitions` is not imported by
   `engram.interview.web`.
4. **render.py extraction is no-behavior-change.** Golden-output tests
   pass; existing `tests/test_interview_cli.py` is unchanged in
   behavior expectations.
5. **Migration 011 correctness.** Append-only trigger raises on
   UPDATE/DELETE; CHECK enforces version-triple shape per `target_kind`;
   PK `(session_id, idx)` rejects duplicates.
6. **Verdict commit flow.** Single-click for `true`/`skip` (one
   round-trip, empty rationale committed); two-click rationale-required
   for `false`/`stale`/`unsupported`/`unsure`.
7. **Vendored htmx.** No CDN reference reachable from any rendered page;
   `/static/htmx.min.js` served from the wheel.
8. **Loopback-only.** `engram phase3 interview serve` exits 8 on
   non-loopback host. No `--allow-non-loopback` flag.
9. **`gold_label_session_targets` materialization.** Both web
   POST `/sessions` and CLI `phase3 interview start` write to the
   table. CLI-started sessions are web-resumable.
10. **Accessibility.** `aria-live` live region, focus management on
    htmx swaps, `aria-label` on verdict buttons sourced from
    `gold_label_verdict_vocabulary`, color-not-only differentiation.
11. **Empty-corpus path.** POST `/sessions` with empty sampler returns
    `index.html` with a diagnostic banner; no session row created.
12. **Spec drift.** Any deltas from spec § Routes / Templates /
    render.py API / Test surface are documented in the handoff.

## Verdict guidance

- `accept` — implementation lands the contract; residual gaps minor and
  documented.
- `accept_with_findings` — notable but non-blocking gaps (e.g.,
  spec-deferred items not yet wired, missing accessibility polish).
- `needs_revision` — Origin allowlist missing, Tier 1 ceiling missing,
  D044/D069 import guard absent, render extraction breaks CLI, or
  migration 011 trigger broken.
- `reject` — fundamental contract violation.

## Output

Write `docs/reviews/rfc0027-interview-web-ui-implementation/FINAL_REVIEW.md`
with the work-packet author byline (line 2), ## Audit findings (A###
with Severity / Source / Rationale), final `verdict:` line.
