# RFC 0038 Operator UI Rework — Security Review
author: operator [self-declared: rfc0038-review-security]

Date: 2026-05-13
Lane: claude_security
Role: reviewer
Posture: security
Verdict: accept_with_findings

Artifacts under review:

- `docs/rfcs/0038-operator-ui-rework.md`
- `ENGRAM_UI_REWORK_HANDOFF.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/IMPLEMENT_SHARED_HANDOFF.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/IMPLEMENT_INTERVIEW_HANDOFF.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/IMPLEMENT_BENCH_HANDOFF.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/INTEGRATION_EVIDENCE.md`

## Scope and Method

Document-only review of the RFC 0038 design and its implementation handoffs
against Engram's local-first posture, CSRF/Origin/Sec-Fetch enforcement,
Tier 1 privacy ceiling, the consolidator import boundary, and the truthful
non-promotion state required by D044 / D069 / D074. No implementation source
was inspected per the review packet's `document_only` access scope; tests in
`tests/` were treated as documented behavior via the handoff and integration
evidence only.

Method: read the RFC and handoff cover-to-cover, then trace each named
guard (Origin allowlist, `Sec-Fetch-Site`, Tier 1 ceiling + max-carry,
strong-decision route rejection, consolidator-import test, audit footer
copy, CDN scans, future-slot inertness, advisory copy invariants) through
to its acceptance check in §9 of the handoff, and confirm the
implementation handoffs claim it landed without behavior regression.
Cross-referenced D080 / D081 (Origin allowlist semantics) and D044 / D069
/ D074 (non-promotion semantics).

## Verdict

`accept_with_findings`.

The design preserves Engram's load-bearing security/privacy posture from
RFC 0027 / Spec 0027 and RFC 0029: loopback-only bind, strict
Origin + `Sec-Fetch-Site` enforcement on every mutating route, Tier 1
ceiling on render and message routes with max-carry on multi-message
windows, append-only verdict commit, no consolidator import from either
web app, no CDN egress, and an audit-footer assertion that reads
"local-only · loopback · no network egress" on every page. The
non-promotion truthfulness contract (D044 / D069 / D074) is encoded
both as visible copy invariants and as route-level disabling on strong
decisions. None of the proposed changes weaken these guards.

The review surfaces four security findings worth addressing — one
medium (a query-string banner reflection that is HTML-safe but
operator-prose-unsafe), three low (defense-in-depth headers, vendored
htmx version hygiene, and an integration-evidence gap that prevents
security tests from being proven to pass in the dirty worktree). None of
the four are architecture contradictions; each has a small, locally
applicable fix.

## Findings

Severity scale: `medium` = exploitable in a realistic local-attacker
scenario (malicious link / hostile clipboard content). `low` =
defense-in-depth, hygiene, or test-evidence gap; no exploit path
identified.

### F-SEC-1 (medium) — `?banner=` query reflection enables operator-prose phishing

**Affected behavior.** Handoff §4.7 (`/save-and-quit`) returns a 303 to
`/?banner=…`, and the index page renders the banner string inside the
`save_and_quit_banner` slot. IMPLEMENT_INTERVIEW_HANDOFF.md confirms a
"URL-encoded save-and-quit banner" was added.

**Risk.** Jinja autoescape blocks HTML injection in the slot, so this is
not an XSS finding. It is a social-engineering finding. An attacker who
gets the operator to click a crafted link like
`http://127.0.0.1:<port>/?banner=Saved.+To+finish+cleanup+run%3A+rm+-rf+~/engram-db`
can cause the operator's own UI to render attacker-controlled prose that
looks like an Engram system message. The threat model that motivates the
Origin allowlist (cross-tab POST drive-by from any local browser tab)
applies equally here: any local origin can craft a link to
`127.0.0.1:<port>/?banner=...`. The CLI-command card pattern (handoff
§4.1, §5.1 `cli_command_card`) makes operators primed to read Engram
banners as containing safe-to-copy commands, which amplifies this.

**Minimal change.** Treat `?banner=` as a key, not as free text. The
index route should map `banner` to a known canonical-string allowlist
(e.g., `banner=save_and_quit` → the literal "Saved and quit. Resume
with: engram phase3 interview resume --session-id …" rendered from
`session_id` extracted from a separate, sanitized query param). Unknown
banner keys must render nothing. The session id should be validated as a
UUID before being rendered into the banner text and the CLI command
card.

**Test to add to §9.5.** `test_index_rejects_unknown_banner_key` —
`GET /?banner=arbitrary-attacker-text` must not surface the string
`arbitrary-attacker-text` anywhere in the rendered HTML.

### F-SEC-2 (low) — No CSP / X-Frame-Options / Referrer-Policy headers specified

**Affected behavior.** RFC 0038, the handoff, RFC 0027, Spec 0027, and
RFC 0029 specify Origin/`Sec-Fetch-Site` checks on POST, vendored htmx,
no external assets, and loopback-only bind, but none of them require
defense-in-depth response headers on the FastAPI app. Spec 0027 §
"Origin-header allowlist may be insufficient against a determined
attacker" already notes that a non-browser client can spoof the Origin
header; defense-in-depth headers reduce the surface in the *browser*
case.

**Risk.** Low. The loopback bind, vendored static delivery, and strict
Origin allowlist already collapse most of the surface. The remaining
risk is that a local malicious page that successfully spoofs Origin (or
that uses an iframe / window.opener trick) could still attempt to read
or interact with the UI. CSP `default-src 'self'`,
`frame-ancestors 'none'`, and `Referrer-Policy: no-referrer` are
inexpensive to add and align with the loopback-only / no-external-asset
posture the audit footer already asserts.

**Minimal change.** Add a small response-header helper in
`engram.web.headers` (or extend `engram.web.origin`) that sets, on every
response from both apps:

- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `X-Content-Type-Options: nosniff`

Add an acceptance check under §9.7 of the handoff
(`test_security_headers_present_on_every_route`).

**Why this is `low`, not `medium`.** The Origin/`Sec-Fetch-Site`
allowlist, loopback-only bind, and the consolidator import boundary
already enforce the load-bearing properties. CSP is hygiene, not a
primary defense in this design.

### F-SEC-3 (low) — Vendored htmx version hygiene is not specified

**Affected behavior.** Handoff §8 calls for two sibling copies of
`htmx.min.js` (one under `src/engram/interview/static/`, one under
`src/engram/bench_review/static/`). Neither RFC 0038 nor the handoff
states a pinned version, a checksum, or a policy for keeping the two
sibling copies aligned.

**Risk.** Low. Two on-disk copies of the same dependency can drift,
which means a security advisory on htmx requires updating two files. If
only one is updated, the operator runs an inconsistent surface. There
is no current evidence the two copies disagree — the integration
evidence confirms 25 resource files were scanned for external asset
markers with no findings — but version drift is a maintenance hazard.

**Minimal change.** One of:
- Replace the two sibling copies with a single copy served from
  `engram.web.static/htmx.min.js`, served by both surfaces through a
  shared static mount.
- Or: record the htmx version and SHA-256 in
  `src/engram/web/STATIC_VERSIONS.md` and add a test
  (`test_static_versions_match`) that fails when the two `htmx.min.js`
  files do not byte-match.

The shared-mount option is also consistent with §5.1 ("shared substrate")
and removes a Tier-aware-helper duplication.

### F-SEC-4 (low) — Bench app cannot be constructed; route-level security tests are unprovable

**Affected behavior.** INTEGRATION_EVIDENCE.md §"Blocking Findings" §1
reports that `engram.bench_review.web.create_app(...)` fails at startup
with a FastAPI annotation error on `segment_decision(...)` and
`run_decision(...)` because their return types are typed
`RedirectResponse | JSONResponse` and FastAPI tries to derive a response
model from that union. §2 reports that `tests/test_interview_web.py`
and `tests/test_bench_review.py` cannot collect because `httpx` is not
installed in the worktree's dev environment.

**Why this is a security finding even though it is also a correctness
finding.** The security guards added in this rework — bench-route 403
on Tier 1 violation in the excerpt route
(IMPLEMENT_BENCH_HANDOFF.md), strong-decision route rejection with a
JSON 400 envelope (IMPLEMENT_BENCH_HANDOFF.md), rationale-cap rejection
(IMPLEMENT_BENCH_HANDOFF.md), Origin/`Sec-Fetch-Site` rejection on bench
POSTs (handoff §9.2) — cannot be demonstrated to fire in the current
worktree because (a) the bench app does not start and (b) the route
tests cannot collect. The integration evidence's
overall verdict is `fail`, so this is already surfaced, but it must be
called out as a security-test gap, not only a correctness gap.

**Minimal change.** Two pieces, both small:
- Change the return type of `segment_decision(...)` and
  `run_decision(...)` to `Response` (the Starlette base type FastAPI
  accepts) and rely on the existing per-branch construction of
  `RedirectResponse` / `JSONResponse`. This is the standard FastAPI
  pattern when a route legitimately returns more than one response
  shape; see Spec 0027's existing interview handlers for the same
  pattern.
- Add `httpx` to the `dev` extra in `pyproject.toml`. This is the
  documented Starlette `TestClient` dependency.

Acceptance: after both changes, `pytest tests/test_bench_review.py`
must run all bench security tests in §9.2 / §9.7 of the handoff and they
must pass, including `test_origin_mismatch_blocks_post_run_decision`,
`test_post_segment_decision_strong_rejected_for_malformed`, and the
excerpt-route Tier 1 403 test.

## Areas Examined And Considered Safe

These items were actively inspected for security weaknesses and no
actionable issue was found. Listing them here makes the
`accept_with_findings` verdict auditable: I read each one looking for a
gap and did not see one.

1. **Loopback-only bind.** Spec 0027 §"Acceptance criteria (Tier 0
   smoke)" requires `sys.exit(8)` on non-loopback host; RFC 0029 §
   "Privacy posture" reaffirms it. RFC 0038 adds no new flag and is
   explicitly tagged as not introducing a non-loopback bind. D081
   extends the Origin allowlist (not the bind) for authenticated tailnet
   forwarders, which keeps the bind invariant intact.

2. **Origin allowlist + `Sec-Fetch-Site: same-origin` on every mutating
   route.** Handoff §4.3, §4.7, §4.8, §4.12, §4.15 require it. §5.4 and
   §8 consolidate enforcement into
   `engram.web.origin.require_origin(...)`, removing the
   bench-vs-interview policy divergence flagged in §10.9 (the bench
   tightening to `same-origin` only is acknowledged as a behavior
   change, not a silent regression). Spec 0027 §"Origin-header allowlist
   may be insufficient" is already in the doc record.

3. **Tier 1 ceiling on render, message, context, evidence-all, and
   bench excerpt routes.** Handoff §4.2, §4.4, §4.5, §4.6, §4.13, §10.8;
   IMPLEMENT_BENCH_HANDOFF confirms route-level 403 was added to
   excerpt detail, closing the open question in §10.8. Max-tier carry
   on multi-message context is reaffirmed at §4.5 and Spec 0027 §1043.
   The 403 envelope shape
   `{"error":"privacy_tier_ceiling","tier":N,"ceiling":1,"message_id":"..."}`
   is preserved.

4. **Append-only verdicts; no mutating GET.** Handoff §4.3 routes
   verdict commit through POST with Origin enforcement and runs final
   session completion inside the same guarded transaction. Spec 0027 §
   "Origin allowlist on POST routes" / §"Per-form CSRF tokens deferred
   to v1.1" stand.

5. **No consolidator import from either web app, and the shared
   `engram.web` package may not import any business logic.** Handoff
   §8.1 specifies the boundary, §9.9 specifies the import-graph tests,
   and the integration evidence confirms the AST import-boundary check
   passes today.

6. **No CDN / no external font / no Google asset / no `@import`.**
   Handoff §9.7; IMPLEMENT_SHARED_HANDOFF confirms no external asset
   markers were found, and integration evidence confirms 25 resource
   files scanned, zero external refs.

7. **Strong-decision bench buttons are disabled in template AND
   rejected at the route.** Handoff §4.11, §4.12; IMPLEMENT_BENCH_HANDOFF
   confirms 400 envelope returned for malformed/missing/prior-missing
   states. Defense in depth holds.

8. **Future-slot inertness.** Handoff §3.4 / §9.8 require the
   `Entities (future)` tab to render with `aria-disabled="true"` and no
   `href`, and to be inert (not just visually muted). The future-slot
   card is the only place where the words `accept` / `promote` are
   permitted, and only inside fixed disclosure prose; §9.1 last item
   and §9.2 last item enforce the global "no promotion affordance"
   substring scan, with the documented whitelisted phrasing.

9. **Operator-truthful copy invariants (D044 / D069 / D074).** Handoff
   §6 (entire), §6.1, §6.2, §6.3 list the literal lines that must
   render. §9.5 turns each into a test; §9.8 forbids the
   `accept` / `promote` / `reject` / `pin` substrings outside the
   future-slot disclosure. IMPLEMENT_INTERVIEW_HANDOFF confirms the
   `Verdict is an advisory eval input...` line was added; IMPLEMENT_BENCH_HANDOFF
   confirms the `Bench review decisions do not mutate production data
   or bypass Phase 4 gates.` literal banner renders on `/` and
   `/summary` with warning/advisory styling (not success styling).

10. **HX-Redirect / open-redirect.** Handoff §4.3 sets `HX-Redirect`
    only to server-computed in-app paths
    (`/sessions/{id}/q/{idx+1}` or `/`). No code path was identified
    where a user-controlled value drives the redirect target.

11. **Keyboard dispatcher safety.** Handoff §5.1 and §9.6 require the
    dispatcher to ignore key events from INPUT/TEXTAREA except Esc,
    and the implementation handoff confirms the early-return check is
    in `keyboard.js`.

12. **Rationale length cap.** Bench rationale is capped at
    `ENGRAM_BENCH_REVIEW_RATIONALE_MAX_CHARS` (default 500); over-cap
    submissions are rejected at the storage layer with a 400 banner
    (handoff §4.11, §9.2). This bounds the size of operator input
    bound for the scratch DB.

## Residual Risk

These items are not findings — the design treats them correctly — but
they are worth flagging in the synthesis loop so the originating agent
can decide whether to take additional belt-and-suspenders steps:

- **Origin-header allowlist is still primary CSRF defense in v1.**
  Spec 0027 already documents this is deferral, not denial; per-form
  CSRF tokens remain queued for v1.1, with D081's named trigger ("any
  new mutating route added after v1") still in force. RFC 0038 adds no
  new mutating route, so the trigger does not fire on this rework.

- **`ENGRAM_INTERVIEW_ALLOWED_ORIGINS` extension (D081)** stays loopback
  by default. Operators who set this var to point at a non-tailnet,
  non-auth-gated network bypass the browser-Origin guard at their own
  device's risk. No design change requested; flagging for the
  synthesizer.

- **CSP `style-src 'self' 'unsafe-inline'` (proposed under F-SEC-2)**
  is required because the handoff §7 specifies an inline `<style>`
  block in `_app_shell.html` rather than an external sheet. The
  `'unsafe-inline'` allowance is the load-bearing
  cost of "no external fonts, no CSS imports." This is the right
  tradeoff for a loopback-only local-first surface; do not move the
  styles to an external sheet just to drop `'unsafe-inline'`.

## Recommended Synthesis Path

1. Accept F-SEC-1 and revise the handoff's §4.7 banner contract to be a
   key-based allowlist before implementation freezes. Add the test.
2. Accept F-SEC-2 as a low-priority follow-on; either land the header
   helper inside the shared `engram.web` substrate in this RFC, or open
   a dedicated follow-up RFC if the synthesizer prefers narrower scope
   here.
3. Accept F-SEC-3 in its shared-mount form, which also removes a small
   amount of duplication and is consistent with RFC 0038's "shared
   substrate" intent.
4. Accept F-SEC-4. The two changes (return-type widening + `httpx` in
   `dev`) are the minimum required to make the security tests provable
   in CI; the integration-evidence lane already flagged the same issues
   for correctness reasons.

No finding here rises to `reject` or `needs_revision` on a security
basis. The design's security posture is sound; these are improvements,
not blockers.
