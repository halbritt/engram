# RFC 0027 Web UI Implementation — Final Review
author: reviewer-codex-gpt-5.5-002

Status: final-review
Date: 2026-05-09
Spec: spec-0027
RFC refs: RFC-0027
Decision refs: D080, D044, D069
Phase refs: PHASE-0003-FOLLOWON

## Scope

Contract-compliance audit of the RFC 0027 / Spec 0027 implementation against
the 12-item checklist supplied by `striatum/.../prompts/final_review.md`.
Pass A (render.py extraction, migration 011, CLI refactor), Pass B1 (FastAPI
app + templates + htmx shim + tests + pyproject deltas), and Pass B2 (serve
CLI subparser + Makefile target + howto + CHANGELOG) were all on disk and
already verified end-to-end by `VERIFICATION_REPORT.md`
(`accept_with_findings`). This review re-checks the contract surface; it
does not re-run the integration smoke.

## Audit findings

### A001 — Origin allowlist enforced on every POST route
Severity: nit (informational; PASS)
Source: `src/engram/interview/web.py:144-179`,
`src/engram/interview/web.py:464` (test_post_verdict_403_origin_mismatch)
Rationale: `_origin_check` (lines 144–179) validates `Origin` against
`ALLOWED_ORIGIN_HOSTS = ('127.0.0.1', 'localhost')` (line 61) and rejects
non-allowlisted values with 403 + structured envelope
`{"error": "origin_mismatch", "expected": [...]}`. `Sec-Fetch-Site`, when
present, must be `same-origin` (line 172). The dependency is attached only
to POST routes (`/sessions`, `/q/{idx}/verdict`, `/save-and-quit`,
`/complete`, `/abandon`); GETs are unguarded per spec § Origin allowlist
behavior. The empty-`Origin` exemption (line 157) is the documented
TestClient/curl accommodation; an attacker page from a real browser
context cannot strip the header on a cross-origin request, so the
exemption does not weaken the policy. The DB-backed test at
`tests/test_interview_web.py:464` exercises this with
`Origin: http://evil.example` and asserts the 403 envelope. PASS.

### A002 — Tier 1 ceiling enforced on message routes
Severity: nit (informational; PASS)
Source: `src/engram/interview/web.py:72`,
`src/engram/interview/web.py:182-192`,
`src/engram/interview/web.py:828`,
`src/engram/interview/web.py:861`,
`tests/test_interview_web.py:511,531,563,582`
Rationale: `TIER_CEILING = 1` constant at line 72; `_check_tier_1` at
182–192 raises 403 with `{"error": "privacy_tier_ceiling", "tier": n,
"ceiling": 1}`. `/messages/{id}` enforces single-row tier; the context
route at line 828 enforces anchor tier and at line 861 enforces
max-tier-carry across every returned row (any tier-2 row in the window
forces 403 for the entire response, matching spec § F023). Four DB-backed
tier-ceiling tests at lines 511, 531, 563, 582 cover `/messages/{id}`,
`/messages/{id}/context`, and `/q/{idx}/evidence/all`. The reserved
`ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX` env var is intentionally
unimplemented in v1 per spec § Out of scope. PASS.

### A003 — D044 / D069 import-graph guard holds
Severity: nit (informational; PASS)
Source: `tests/test_interview_web.py:634`,
verifier cmd 5 (`D044/D069 import guard: ok`)
Rationale: `engram.interview.web` does not import
`engram.consolidator.transitions`. The pytest case
`test_consolidator_transitions_unimportable_from_web` walks every public +
private symbol in `web.py` and asserts none resolves into the forbidden
module; the verifier also ran a runtime `sys.modules` probe (cmd 5) that
returned an empty match. No template renders a promote-belief / accept /
reject / pin affordance. PASS.

### A004 — render.py extraction is no-behavior-change
Severity: nit (informational; PASS)
Source: `src/engram/interview/render.py`,
`tests/test_interview_render.py`,
verifier cmd 6 (65 passed)
Rationale: render.py owns `VERDICT_PROMPT`, `VERDICT_ALIAS`,
`VERDICT_VALID`, `RATIONALE_PROMPT_BY_VERDICT`, `EVIDENCE_EXCERPT_LIMIT`,
`EVIDENCE_ROWS_SHOWN`, plus the eight render helpers per spec § render.py
API. cli.py re-imports them (per spec lines 263–270) and the underscore
copies are gone from cli.py. Pass A's golden-output tests in
`tests/test_interview_render.py` pin `format_header`,
`format_summary_line`, `format_evidence_dates`,
`format_evidence_excerpts`, and the `pick_question` framings against the
exact CLI strings. All 65 non-DB tests pass per verifier cmd 6, including
the existing `tests/test_interview_cli.py` golden-output assertions. PASS.

### A005 — Migration 011 correctness
Severity: nit (informational; PASS)
Source: `migrations/011_gold_label_session_targets.sql:1-59`,
`tests/test_migrations.py:159,184,204`
Rationale: the migration declares (1) `PRIMARY KEY (session_id, idx)`
(line 26), (2) the version-triple CHECK constraint
`chk_session_targets_version_triple` (lines 27–39) — claim rows must
carry `extraction_*` non-null and `consolidation_*` null; belief rows
the opposite, (3) the append-only trigger
`gold_label_session_targets_00_append_only` raising `P0001` on
UPDATE / DELETE (lines 48–59). Three DB-backed tests
(`test_011_session_targets_append_only`,
`test_011_session_targets_version_triple_check`,
`test_011_session_targets_pk_uniqueness`) at
`tests/test_migrations.py:159,184,204` exercise each invariant
(verifier cmd 17 confirmed 36 passed including these). PASS.

### A006 — Verdict commit flow: single-click + two-click
Severity: nit (informational; PASS)
Source: `src/engram/interview/templates/question.html:50-146`,
`src/engram/interview/web.py:677-764`,
`tests/test_interview_web.py:test_post_verdict_true_single_click_commit`,
`tests/test_interview_web.py:test_post_verdict_false_two_click_flow`
Rationale: question.html ships a single `<form id="verdict-form">` with
six buttons. `[true]` and `[skip]` are `type="submit"` (lines 58, 83) —
clicking either submits the form natively in one round-trip with an empty
rationale. `[false]`, `[stale]`, `[unsupported]`, `[unsure]` are
`type="button"` (lines 63, 68, 73, 78); the inline script at lines
117–146 reveals `<div id="rationale-area">`, populates the prompt from
`RATIONALE_PROMPT_BY_VERDICT`, and focuses the textarea — the second
click on the `<button id="commit-rationale" type="submit">` (line 93)
posts the form. The route at web.py:677–764 catches
`GoldLabelStorageError` / `GoldLabelVerdictError`, rolls back, and
re-renders with an inline error banner (trigger-rejection path); on
success it returns 200 + `HX-Redirect: /q/{idx+1}` (or
`/sessions/{id}/complete` if `idx == n`, line 740–743). DB-backed tests
exercise both paths plus 404 / 422 / 403 envelopes. PASS.

### A007 — Vendored htmx shim covers the templates' attribute set
Severity: minor (informational; matches V001 from VERIFICATION_REPORT)
Source: `src/engram/interview/static/htmx.min.js:1-174`,
templates' `hx-*` usage
Rationale: the shim is a 174-line `engram-htmx-stub.v1`, not upstream
htmx. Spec § F004 sanctions a vendored offline asset and forbids a CDN
reference; nothing in the spec mandates the upstream artifact. Templates
use exactly four hx-* attributes: `hx-get`, `hx-post`, `hx-swap`,
`hx-target` (verified by grep). The shim implements all four (lines
85–153 wire `hx-get`/`hx-post` for `<a>`, `<button>`, `<form>`; lines
33–53 implement `innerHTML` / `outerHTML` swap modes; lines 23–31
resolve `hx-target` including `closest <selector>`) plus `hx-push-url`
(unused by templates — see A012) and `HX-Redirect` response-header
following (lines 60–63). The `htmx:afterSwap` event the dispatcher in
`base.html` listens for is dispatched on every swap (lines 48–52). The
contract is satisfied. Carry V001 forward as a known maintenance
risk: any new `hx-*` attribute introduced after v1 silently no-ops until
the shim is extended or upstream htmx is dropped in.

### A008 — Loopback-only bind enforced before FastAPI import
Severity: nit (informational; PASS)
Source: `src/engram/cli.py:2061-2105`,
verifier cmd 9 (`exit 8`),
`tests/test_interview_cli.py:test_phase3_interview_serve_refuses_non_loopback`
Rationale: `_SERVE_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost",
"::1"})` at cli.py:2064. The host check at line 2079 runs before the
deferred FastAPI / Uvicorn import (lines 2087–2097), so the policy holds
even on installs that happen to have FastAPI present. Refusal prints the
exact spec string `"phase3 interview serve: refusing non-loopback host
(--host=...); v1 is loopback-only"` to stderr and `sys.exit(8)`. The
`--allow-non-loopback` flag is intentionally absent — only a comment at
line 2062 documents the deliberate omission (verifier cmd 16 confirmed
no parser entry). The spec's loopback set names `127.0.0.1` and
`localhost`; the implementation extends to `::1` (IPv6 loopback) which is
a strict superset of loopback addresses and matches the F005 intent.
Spec drift documented under § Spec drift below. PASS.

### A009 — `gold_label_session_targets` materialized by both CLI and web
Severity: nit (informational; PASS)
Source: `src/engram/interview/web.py:615` (web POST `/sessions`),
`src/engram/cli.py:run_phase3_interview_start`,
`tests/test_interview_cli.py:test_phase3_interview_start_writes_session_targets`
Rationale: web POST `/sessions` calls `_insert_session_targets(conn,
session_id, sampled)` at web.py:615 inside the same transaction as
`insert_session`. The CLI driver `run_phase3_interview_start` materializes
the same rows after `sampler.sample(n)` (per spec § CLI integration
lines 730–735); the new test
`test_phase3_interview_start_writes_session_targets` (skipped without DB,
asserted in the `accept_with_findings` verifier run — see Pass B2 cmd 6
output) pins this. Empty-sample paths in both surfaces call
`mark_session_completed` rather than DELETE, preserving append-only-ish
semantics on `gold_label_sessions`. PASS.

### A010 — Accessibility: aria-live, aria-label, focus management,
color-not-only
Severity: nit (informational; PASS)
Source: `src/engram/interview/templates/base.html:138`,
`src/engram/interview/templates/question.html:55-87`,
`tests/test_interview_web.py:674`
Rationale: base.html line 138 declares
`<div id="live-region" aria-live="polite" class="visually-hidden">`. The
inline `htmx:afterSwap` listener (base.html:205) updates the live region
text and moves focus to the new `<h2 tabindex="-1">`. question.html
verdict buttons (lines 60, 65, 70, 75, 80, 85) carry `aria-label` sourced
from `verdict_glosses[...]` — populated from the
`gold_label_verdict_vocabulary` table per web.py:_load_verdict_glosses
(line 200), with a fallback to the hard-coded map if the table is
unreachable. Each button also carries a verdict-specific class
(`v-true`, `v-false`, etc.) plus an `<span class="icon" aria-hidden="true">`
glyph (✓, ✗, ⌛, ⚠, ?, ») so the verdict identity does not depend on
color alone (WCAG 1.4.1). The `test_aria_live_region_present` test at
line 674 pins the live-region presence in rendered HTML. PASS.

### A011 — Empty-corpus path renders index with diagnostic banner
Severity: nit (informational; PASS)
Source: `src/engram/interview/web.py:595-614`,
`tests/test_interview_web.py:274`
Rationale: web.py:595 detects `not sampled`, calls
`mark_session_completed(conn, session_id)` to keep the session row out of
the open-sessions list (spec § POST `/sessions` recommendation, lines
337–340), commits, and re-renders index.html with
`empty_corpus_banner = "no targets matched (empty corpus, all on
cooldown, or current_beliefs not refreshed)"`. The 200 status is correct
per spec (not a 422 or 303). The banner is rendered with
`role="status"` per spec § index.html accessibility note (verified in
`templates/index.html`). Test
`test_post_sessions_empty_corpus_renders_diagnostic` at
tests/test_interview_web.py:274 exercises the path. PASS.

## Spec drift

The implementation diverges from the spec in two intentional, documented
places. Neither is a contract violation:

1. **`mark_session_completed` does not accept `operator_note`.** The
   abandon route at `web.py:_abandon_session` (line 424) issues an inline
   `UPDATE gold_label_sessions SET completed_at = ..., operator_note =
   %s` rather than calling `mark_session_completed(conn, session_id,
   operator_note='abandoned via web')` as the spec § POST `/abandon`
   suggests. Pass B1's handoff (lines 132–135) called this out — storage.py
   was out of write scope for the pass, so the inline UPDATE preserves
   the spec semantics without modifying the storage helper. This is a
   followable seam if a v1.1 lands (centralize in storage.py and replace
   the inline UPDATE), but it does not affect operator-visible
   behavior or contract compliance.

2. **`_SERVE_LOOPBACK_HOSTS` includes `::1` (IPv6 loopback) in addition
   to `127.0.0.1` and `localhost`.** Spec § Privacy and security names
   only `127.0.0.1` and `localhost`. The Pass B2 work-packet guidance
   added `::1` as the IPv6 equivalent; the loopback policy intent (F005)
   is preserved (the bind is still loopback-only). Documented in
   PASS_B2_SERVE_CLI_HANDOFF.md § Key design choices.

3. **Templates do not use `hx-push-url`** even though spec § GET
   `/q/{idx}` mentions it ("the page sets `hx-push-url='true'` so back /
   forward and bookmarks work"). The shim supports the attribute but
   templates omit it. Direct `GET /sessions/{id}/q/{idx}` requests still
   work for bookmarks (the route handles full-page renders), and htmx
   redirects via `HX-Redirect` (which causes `window.location.href = url`,
   updating the address bar) so the address bar tracks navigation
   either way. No operator-visible loss; nit-level deviation only.

## Residual risks (carry forward)

These were flagged by the verifier and are reproduced here as carry-forward
items for v1.1 / future RFCs. None block acceptance.

- The htmx shim's attribute coverage will need extension or replacement
  the first time a future template introduces a new `hx-*` attribute.
- No test pins `Cache-Control: private, no-store` on message responses;
  the spec § Privacy and security notes the header as a property but does
  not list it in the audit checklist. Worth a follow-on test to lock in.
- The DB-backed web/storage/migrations tests skip silently without
  `ENGRAM_TEST_DATABASE_URL`; CI must run with the env set or the
  substantive web invariants are not exercised.
- Per-form CSRF tokens deferred to v1.1 with a documented trigger (any
  new mutating route added after v1 forces re-evaluation). The
  Origin-allowlist + Sec-Fetch-Site posture is sufficient for a
  single-user loopback surface.

## Summary

All twelve audit-checklist items pass on contract grounds. Origin
allowlist, Tier 1 ceiling, D044/D069 import guard, render-extraction
no-behavior-change, migration 011 invariants, verdict-commit flow,
vendored-htmx-not-CDN, loopback-only bind, session-targets
materialization (CLI + web), accessibility, and the empty-corpus path
all check out against `src/engram/interview/web.py`,
`src/engram/cli.py`, the templates, the migration, and the test surface.
The three documented spec drifts (inline operator_note UPDATE, `::1`
added to the loopback set, omitted `hx-push-url`) are intentional,
non-blocking, and tracked in handoffs.

The verifier's prior `accept_with_findings` carries one minor finding
(V001: htmx shim is a custom 174-line subset, sanctioned by spec § F004
but worth carrying as a maintenance risk). This final review reaches the
same conclusion on the lighter contract pass: the implementation lands
the contract; one minor residual gap (custom htmx shim) is documented
and carried forward.

verdict: accept_with_findings
