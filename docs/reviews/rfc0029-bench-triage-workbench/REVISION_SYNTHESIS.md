# RFC 0029 Bench Triage Workbench Revision Synthesis
author: synthesizer-codex-gpt-5.5-001

Status: synthesis
Date: 2026-05-09
RFC refs: RFC-0029
Decision refs: D020, D074, D082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Decision

Revise RFC 0029 before any implementation. The design goal is accepted, but
the current draft leaves too much ambiguity in the exact areas that caused the
owner's cognitive overload: whether data is present, what verdicts mean, when
a run is ready, and how scratch artifacts become tracked summaries.

Proceed autonomously by applying the accepted findings to the RFC. Do not
promote the RFC to `accepted` or write `DECISION_LOG.md` yet; this remains a
proposal/spec candidate pending owner review or a future acceptance decision.

## Accepted Findings

- L001: require segment records for triage mode and separate semantic zero from
  unavailable data.
- L002: use the full prior extraction version triple or an explicit prior run
  artifact.
- L003: define redacted candidate display and private-detail display modes.
- L004: make tracked export CLI-only in v1 and harden output paths.
- L005: adopt RFC 0027's web security posture exactly.
- L006: replace "safe to promote" with explicit promotion readiness and
  run-level decision semantics.
- L007: define batch eligibility mechanically or defer acceptance-like batch
  actions.
- L008: clarify verdict labels and skip semantics.
- L009: add a top-level change summary to reduce screen memory load.
- L010: persist enough UI state for clean stop/resume.
- L011: make keyboard shortcuts focus-safe and avoid RFC 0027 collision.
- L012: expand acceptance tests to cover usability contracts.
- L013: resolve v1 command placement and `--output` syntax.
- L014: reaffirm scratch SQLite and no production-derivation consumption.

## Rejected Findings

None. The review set was convergent and all findings are either required RFC
edits or precise follow-on spec requirements.

## Deferred Findings

- A read-only Postgres role is desirable but can remain a spec/implementation
  hardening item if the existing connection setup makes it expensive.
- Segment IDs in tracked exports may be revisited after the first redacted
  summary format exists. The RFC should keep segment IDs but avoid raw private
  text and values by default.
- A Phase 4 alias is deferred until Phase 4 benchmark artifacts are actually
  supported.

## Required RFC Edits

1. Change the `serve` CLI contract to require candidate segment records for
   triage mode, preferably through `--segments` or by resolving
   `segment_records_path` from `run.json`; missing records produce a
   metadata-only status view.
2. Replace `--prior-version` with a full prior extraction identity:
   `--prior-prompt-version`, `--prior-model-version`, and
   `--prior-request-profile-version`, or `--prior-run`.
3. Add explicit data-availability states:
   `candidate_zero`, `candidate_redacted`, `candidate_missing`,
   `candidate_malformed`, `prior_missing`, and `complete`.
4. Define redacted candidate mode and private-detail mode; disable semantic
   acceptance decisions when data is insufficient.
5. Drop `POST /export`; make export CLI-only with `--output PATH`, no
   `--allow-outside-reviews`, no notes by default, and hardened path checks.
6. Copy RFC 0027's loopback, Origin, `Sec-Fetch-Site`, Tier 1 ceiling,
   vendored htmx, package-data, and no-CDN test expectations.
7. Rename "safe to promote" to "promotion readiness"; define blocked,
   review-incomplete, ready-for-owner-decision, and promoted-by-recorded
   decision states.
8. Add a run-level decision field to scratch review state.
9. Define verdict labels, consequences, and skip semantics.
10. Define batch eligibility and defer acceptance-like batch actions in v1.
11. Add a required top change-summary block for each segment.
12. Add session UI state for stable queue order, active filter, current item,
    unresolved item, and resume choices.
13. Change the follow-up shortcut away from `f`, and require focus-safety.
14. Expand acceptance criteria for data-availability, readiness, batch,
    resume, shortcut, no-CDN, and export-path behavior.
15. State review decisions do not feed production derivations.

## Required Follow-Up Artifacts

- The revision handoff should list every accepted ledger item and the RFC
  section changed for it.
- If the revised RFC is accepted later, create a promoted spec before code
  implementation, mirroring RFC 0027.
- The eventual implementation workflow should include adversarial usability
  review again after a working UI exists, because the main risk is not only
  architecture but actual operator load.
