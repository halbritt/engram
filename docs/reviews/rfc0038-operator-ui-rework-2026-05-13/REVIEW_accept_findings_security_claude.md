---
schema_version: "striatum.finding.v1"
artifact_kind: "finding"
verdict_intent: "accept"
severity: "info"
---

author: operator [self-declared: rfc0038-accept-findings-security-review]

# RFC 0038 Accept-with-Findings Local-First / Security Review

Status: review
Date: 2026-05-13
Lane: claude_security
Workflow: `rfc-0038-accept-findings-followup-2026-05-13`
Job: `review_accept_findings_security`
RFC refs: RFC-0038
Spec refs: ENGRAM_UI_REWORK_HANDOFF.md, Spec 0027, RFC 0027, RFC 0028, RFC 0029
Decision refs: D044, D069, D074, D080, D081
Posture: security (local-first, no-CDN, CSRF/Origin, Tier 1 ceiling,
truthful-status copy, no weakening of DB validation or provenance)
Verdict: **accept**

## Scope

Fresh security re-review of the accept-with-findings follow-ups that landed
after `REVIEW_corrected_security_claude.md`. Inputs:

- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_corrected_security_claude.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_corrected_correctness_codex.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_corrected_ergonomics_claude.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_FOLLOWUP_EVIDENCE.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/ACCEPT_FINDINGS_INTERVIEW_HANDOFF.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/ACCEPT_FINDINGS_BENCH_HANDOFF.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/ACCEPT_FINDINGS_SHARED_HANDOFF.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/ACCEPT_FINDINGS_EVIDENCE.md`
- `src/engram/web/`, `src/engram/interview/`, `src/engram/bench_review/`
- `tests/test_web_ui_shared.py`, `tests/test_interview_web.py`, `tests/test_bench_review.py`
- `ENGRAM_UI_REWORK_HANDOFF.md`, `docs/rfcs/0038-operator-ui-rework.md`,
  `AGENTS.md`, `CHANGELOG.md`,
  `docs/process/multi-agent-review-loop.md`,
  `docs/process/project-judgment.md`

No implementation files were edited. Source-level claims are anchored to
file:line citations in the current branch
(`engram/rfc0038-ui-rework`).

## Verdict summary

`accept`.

Every open security-class follow-up the prior corrected pass listed
(CS001 architectural single-enforcement-point; CS002 interview audit-footer
fallback) is repaired in source. The bench tier-helper portion of CS001 also
landed. The local-first / no-CDN / Tier 1 ceiling / raw-evidence
immutability / Phase 4 non-authorization posture is preserved verbatim. The
DB validation forward constraint from the corrected pass is honored — the
predicate-vocabulary trigger remains the authority and the fixture seeds it
from canonical rows. Nothing in the diff weakens append-only invariants,
introduces external dependencies, or relaxes any tier check.

I actively looked for residual security weaknesses (origin policy bypasses,
footer copy that could lie under a configured bind, dead code reintroducing
the shared/per-surface drift, no-CDN regression in newly added partials,
DB validation shortcuts via fixtures, hosted-auth or cloud touches) and
found none actionable.

A single informational observation appears below the verdict line; it does
not block the security posture today and does not change the verdict.

## Verified preserved

### CS001 (closed)

The corrected pass kept this open as architectural drift: interview held a
local `_origin_check` and a local `_check_tier_1`; bench used its own inline
tier guard. Both surfaces now delegate to the shared substrate.

- Interview origin: `src/engram/interview/web.py:62`,
  `:214-223` (`_origin_check` imports and calls
  `engram.web.origin.require_origin` with the env-extended host allowlist).
  Module-level import path: `from engram.web.origin import require_origin`
  at `:62`.
- Interview tier ceiling: `src/engram/interview/web.py:63`,
  `:226-228` (`_check_tier_1` delegates to `require_tier_ceiling`). The
  ceiling constant `TIER_CEILING = 1` (`:131`) is preserved.
- Bench origin: `src/engram/bench_review/web.py:22`, `:251`, `:314`,
  `:336-344` (POST handlers call `origin_check`; the helper validates the
  request host against `ALLOWED_HOSTS`/operator-opted DNS suffixes, then
  calls `require_origin` with the bound port).
- Bench tier: `src/engram/bench_review/web.py:23`, `:228`,
  `:347-365` (`_require_excerpt_tier` calls `require_tier_ceiling` and
  preserves the prior bench denial envelope
  `{"error": "privacy_tier_ceiling", "privacy_tier": <tier>}`).

Tests pin the delegation contract:

- `tests/test_interview_web.py:870-885`
  (`test_origin_check_delegates_to_shared_helper` monkeypatches the imported
  symbol and asserts the call shape).
- `tests/test_interview_web.py:888-900`
  (`test_tier_check_delegates_to_shared_helper`).
- `tests/test_bench_review.py:490-517` (excerpt route raises through the
  shared tier helper; the response envelope shape is locked).

Three negative-path tests on the interview side
(`test_post_verdict_403_origin_mismatch`,
`test_post_verdict_requires_origin_header`,
`test_post_verdict_requires_same_origin_sec_fetch`,
`test_post_verdict_rejects_allowed_host_on_wrong_port`,
`test_origin_mismatch_blocks_all_post_routes` —
`tests/test_interview_web.py:796-867`) keep the 403 + `origin_mismatch`
envelope locked end-to-end.

### CS002 (closed)

The corrected pass left the interview audit footer rendering a hard-coded
`"127.0.0.1:8765"` literal whenever the Host header was not a loopback
match (the documented D081 Tailnet/TCP-bridge path). That path is gone.

- `src/engram/interview/web.py:73`,
  `:248-275` define `_LOOPBACK_BIND_HOSTS`, `_format_bind_address`,
  `_scope_bind_address` (reads `request.scope["server"]` and rejects
  non-loopback hosts), and `_bind_address_for_request` which prefers the
  scope server, then `app.state.engram_bind_address`, and raises
  `RuntimeError("interview bind address is not configured")` if neither is
  available. There is no Host-header-derived literal fallback.
- `create_app(...)` validates `host` against `_LOOPBACK_BIND_HOSTS`
  (`:743-744`) and stores the validated bind in `app.state`
  (`:751`). Bench's create-time validation has the same shape at
  `bench_review/web.py:87-88`.
- The shared `_audit_footer.html` template falls back to the placeholder
  string `"127.0.0.1:<port>"` only if `bind_address` is missing entirely
  (`web/templates/_audit_footer.html:2`). With the changes above, that path
  is unreachable from either surface at runtime.

Tests lock the truthful behavior on both surfaces:

- `tests/test_interview_web.py:312-327`
  (default interview app renders `127.0.0.1:8765`).
- `tests/test_interview_web.py:352-365`
  (`test_create_app_uses_configured_bind_address` constructs a TestClient
  app with `port=9876` and asserts the rendered footer matches).
- `tests/test_bench_review.py:335` (bench footer at port 8770).
- `tests/test_web_ui_shared.py:65-86` exercises the shared partial.

### No-CDN / no external asset markers

A repository search across all template and static surfaces matched only
loopback-shaped strings:

```
src/engram/interview/web.py:72   http://127.0.0.1:8770/segments?...
src/engram/bench_review/web.py:31 http://127.0.0.1:8765/
src/engram/web/origin.py:29       http://{host}:{port} (expected-origin pattern)
src/engram/web/assets.py:12-22    the CDN-marker enumeration itself
```

No CDN host markers (`unpkg`, `cdn.jsdelivr.net`, `cdnjs.cloudflare.com`,
`googleapis.com`, `googletagmanager.com`, `@import`) appear in any
`.html`, `.css`, or `.js` resource under `src/engram/{web,interview,
bench_review}`. The shared substrate test
`tests/test_web_ui_shared.py:60-62`
(`test_shared_resources_have_no_external_asset_references`) keeps this
locked for `engram.web`. The follow-up evidence
`ACCEPT_FINDINGS_EVIDENCE.md` also recorded a 27-resource scan that
returned zero markers.

### Tier 1 ceiling

`TIER_CEILING = 1` is preserved on the interview surface
(`interview/web.py:131`), and `require_tier_ceiling`'s default ceiling is
`1` (`web/tier.py:7`). Every interview message-rendering callsite still
guards through the helper:

- `interview/web.py:586` (question render: parent target tier)
- `interview/web.py:677` (display excerpts)
- `interview/web.py:1007` (`/sessions/{id}/messages/{message_id}`)
- `interview/web.py:1062`, `:1095` (context window)
- `interview/web.py:1133`, `:1139` (`evidence/all` route)

Bench `segment_excerpt` enforces the ceiling via the shared helper at
`bench_review/web.py:228` with the denial envelope shape preserved at
`:347-365`. The DB-trigger validator that surfaced earlier in this loop is
unchanged.

### DB validation preserved (S005 / forward constraint)

The accept-findings handoffs did not touch `migrations/` or
`engram.db.*`. The repair-driven fixture pattern in
`tests/test_interview_web.py:98-106` continues to resolve `stability_class`
from `predicate_vocabulary` via `_stability_class_for_predicate`, and
materialized session-target rows derive `stability_class` from the parent
claim row (`tests/test_interview_web.py:184-187`). The trigger
`fn_claims_insert_prepare_validate()` is the authority and is untouched.
The forward constraint the corrected pass set (do not weaken the trigger or
the predicate vocabulary to make a fixture green) is honored.

### Loopback-only bind / Phase 4 non-authorization copy

- Interview `create_app` rejects non-loopback hosts at construction time
  (`interview/web.py:743-744`); bench rejects non-loopback / non-testserver
  hosts at the same lifecycle point (`bench_review/web.py:87-88`).
- The Phase 4 / promotion non-authorization vocabulary is intact:
  `web/chrome.py:10` (`PHASE4_FUTURE_COPY`), the
  `Entities (future)` disabled span in `web/templates/_surface_tabs.html:6-10`
  (no `href`, `aria-disabled="true"`), bench disclosure lines at
  `bench_review/web.py:55-62`, interview disclosure lines at
  `interview/web.py:296-305`, and the bench "does not mutate" banner on the
  segment detail page (`bench_review/templates/segment.html:4-6`).
- FU105 cleanup landed: `chrome.DEFAULT_SURFACE_TABS` is gone, and
  `tests/test_web_ui_shared.py:123-125`
  (`test_chrome_does_not_define_parallel_surface_tab_defaults`)
  guards regression. Removing the dead Python constant removed a drift
  vector that could have desynced from the rendered tab vocabulary; this
  is a security-relevant tidy (one fewer place where "what the UI claims"
  can drift from "what is enforced").

### No new cloud / telemetry / hosted-auth introductions

The accept-findings diffs add nothing of the kind. The shared substrate
asserts no business-logic imports in its own modules
(`tests/test_web_ui_shared.py:287-306`,
`test_shared_package_does_not_import_business_logic`). `engram.web` only
depends on `fastapi` and standard library.

### Asymmetric surface tab is no longer a 404 (FU101)

The corrected ergonomics pass classified the interview→bench tab as major.
It is also a security-of-trust posture issue: a "live link" that always
404s teaches the operator to ignore "you are looking at the wrong surface"
signals, which the security copy depends on. The accept-findings interview
handoff added `ENGRAM_INTERVIEW_BENCH_URL` (default
`http://127.0.0.1:8770/segments?remaining=1&reviewable=1`) at
`interview/web.py:113-126`, threaded into `_base_context` via
`app.state.engram_bench_url` (`:282`). Tests cover both default and
operator-override paths
(`tests/test_interview_web.py:323-325, 336-349`).

### Status banner consolidation (FU103) and copy-command deduplication (FU104)

- Interview index renders the empty-corpus and save-and-quit banners through
  the shared `_status_banner.html` partial (`interview/templates/index.html:6-25`),
  and `tests/test_interview_web.py:333` asserts the local `banner-status`
  class no longer ships. These are ergonomics fixes with a security side
  effect — banner semantics now live in one place; future copy changes
  cannot accidentally weaken the warn-toned cues operators rely on for
  trust signals.
- `interview/templates/base.html:192-213` keeps only the htmx
  `aria-busy` / button-disable behavior; the duplicate
  `[data-copy-command]` handler is gone. The shared `keyboard.js` owns
  clipboard behavior. No new XSS surface introduced; `data-copy-command`
  values come from autoescape-rendered Jinja context (`_cli_command_card.html`).

## Informational observation (does not change verdict)

### IS001 — Info — interview `_origin_check` does not pass `bound_port`

Source: `src/engram/interview/web.py:214-223`; `src/engram/web/origin.py:43-74`.

```python
def _origin_check(request: Request) -> None:
    require_origin(request, allowed_hosts=ALLOWED_ORIGIN_HOSTS)
```

The shared helper, when called without `bound_port=...`, derives the
target port from `request_host_port(request)` (`origin.py:65`). In
practice this matches the bench shape *only* in the browser threat model
where the Host header and Origin header are both bound to the same page
origin by the user agent. Bench passes `bound_port=port` explicitly
(`bench_review/web.py:343`), which ties the constraint to the configured
bind rather than the request Host.

This is not a defect for v1:

- The CSRF attacker model that `Sec-Fetch-Site: same-origin` defends
  against is browser-mediated; the Host header in that case is set by the
  user agent from the configured bind, so the Host-port-derived constraint
  is equivalent.
- A non-browser attacker (curl) can forge Host, Origin, and
  `Sec-Fetch-Site` all together, regardless of which port the helper is
  parameterized on. That is the threat model loopback-bind handles, not
  the helper.
- `ENGRAM_INTERVIEW_ALLOWED_ORIGINS` only extends the host allowlist (per
  `interview/web.py:76-100`); it cannot relax the scheme or port logic.

Worth surfacing as a future cleanup so the two surfaces share one mental
model. Recommendation when next touched:

```python
def _origin_check(request: Request) -> None:
    bind = getattr(request.app.state, "engram_bind_port", None)
    if bind is not None:
        require_origin(request, allowed_hosts=ALLOWED_ORIGIN_HOSTS, bound_port=bind)
    else:
        require_origin(request, allowed_hosts=ALLOWED_ORIGIN_HOSTS)
```

(Plumb the bound port into `app.state` at `create_app` time, mirroring the
existing `engram_bind_address` / `engram_bench_url`.)

Not a blocker. Not a behavior change. Tracked here so the next pass that
touches the helper can land it.

## Mapping to prior findings

| Prior finding | Source | Status in current source |
|---------------|--------|---------------------------|
| CS001 — interview not on shared origin / tier helpers | corrected security review | Closed at `interview/web.py:62-63, :214-228`; bench tier portion closed at `bench_review/web.py:23, :228, :347-365`. Tests at `tests/test_interview_web.py:870-900` and `tests/test_bench_review.py:490-517`. |
| CS002 — interview audit footer fallback literal | corrected security review | Closed at `interview/web.py:248-275`; verified by `tests/test_interview_web.py:352-365`. |
| FU101 — interview → bench tab is a live 404 | corrected ergonomics review | Closed at `interview/web.py:113-126`, `:282`; tests at `tests/test_interview_web.py:323-325, 336-349`. Security-relevant because a live link is a trust promise. |
| FU102 — bench keyboard dispatcher fork | corrected ergonomics review | Closed at `bench_review/web.py:105` (`keyboard_static_url="/shared-static/keyboard.js"`), `:115-118` (shared-static mount), plus `bench_review/static/queue_filter.js` (small bench-only enhancement, no duplicated dispatcher behavior). |
| FU103 — interview banner-status local class | corrected ergonomics review | Closed at `interview/templates/index.html:6-25`; `tests/test_interview_web.py:333` asserts the class no longer renders. |
| FU104 — interview duplicate copy-command handler | corrected ergonomics review | Closed at `interview/templates/base.html:192-213`. |
| FU105 — `chrome.DEFAULT_SURFACE_TABS` dead code | corrected ergonomics review | Closed by deletion in `web/chrome.py`; guarded at `tests/test_web_ui_shared.py:123-125`. |
| S005 forward constraint — preserve DB validation | corrected security review | Honored. Fixtures still resolve from `predicate_vocabulary`; trigger is untouched. |

## Outstanding items the next pass should track (none merge-blocking)

1. **IS001** — interview `_origin_check` could pass `bound_port` from
   `app.state` so the helper's port constraint follows the configured
   bind rather than the request Host header. Bench already does this; the
   one-line lift to interview removes the last single-mental-model gap.
2. Carry-forward ergonomics polish from the corrected pass (F008 resume CTA
   placement, F010 metric parity, F013 metadata density, F015 next-in-queue
   affordance, F017 tooltip literal, F018 commit-vs-rationale visual cue)
   remain open per `REVIEW_corrected_ergonomics_claude.md`. None of these
   are security-class; flagged here only because future security
   correspondence about trust copy or status banners may touch the same
   files.

## Verdict

`accept`.

The accept-with-findings follow-ups close every open security-class item
from the corrected security and ergonomics reviews. Local-first / no-CDN /
loopback-bind / Tier 1 ceiling / raw-evidence immutability / Phase 4
non-authorization copy / DB validation are all preserved. The single
residual observation (IS001) is informational and has no behavioral
impact in the v1 threat model.
