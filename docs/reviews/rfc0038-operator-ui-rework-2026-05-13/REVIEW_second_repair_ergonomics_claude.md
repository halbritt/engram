---
schema_version: "striatum.finding.v1"
artifact_kind: "finding"
verdict_intent: "accept"
severity: "low"
---

author: operator [self-declared: rfc0038-second-repair-ergonomics-review]

# RFC 0038 Operator UI Rework — Second-Repair Ergonomics Review (claude)

Status: review
Date: 2026-05-13
RFC refs: RFC-0038
Spec refs: ENGRAM_UI_REWORK_HANDOFF.md, Spec 0027, RFC 0027, RFC 0028, RFC 0029
Decision refs: D044, D069, D074, D080, D081
Posture: custom:ergonomics_dx (first-time-user discoverability, decision cost,
scan order, keyboard flow, banner/status semantics, design-system fit)
Round: fresh-context review of the second-repair lane
(closes AC001 + AC002 from `REVIEW_accept_findings_correctness_codex.md`)
Prior ergonomics round: docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_accept_findings_ergonomics_claude.md
Evidence packet: docs/reviews/rfc0038-operator-ui-rework-2026-05-13/SECOND_REPAIR_EVIDENCE.md

## Scope and method

This is a fresh-context ergonomics pass over the second repair lane. The
prior accept-with-findings ergonomics review verdict was `accept`; this
round must verify the second repair preserves that posture. The required
focus per the task prompt:

- shared chrome, cross-surface navigation, keyboard behavior, status-banner
  semantics, and first-time operator flow accepted by the prior ergonomics
  review must remain intact;
- disabling generated FastAPI docs/openapi routes on bench must not remove
  operator-facing UI affordances promised by the handoff;
- IPv6 loopback support must not create confusing copy or misleading audit
  footer behavior;
- carry-forward polish findings may remain non-blocking if unchanged and
  honestly tracked.

Files re-examined against the second-repair scope (AC001/AC002) and the
prior-round verdict surface:

- `src/engram/interview/web.py` (bind validation, Origin allowlist resolver,
  app-factory bench-URL plumbing, `_format_bind_address`, `_base_context`).
- `src/engram/bench_review/web.py` (FastAPI construction, mounts, templates
  globals, cross-surface `INTERVIEW_URL`).
- `src/engram/interview/templates/{base,index}.html` and
  `src/engram/web/templates/{_app_shell,_surface_tabs,_audit_footer,_status_banner,_cli_command_card,_help_modal,_future_slot}.html`.
- `tests/test_interview_web.py` (IPv6 positive/negative coverage, bench-URL
  resolver, configured-bench-URL render, bind-address footer).
- `tests/test_bench_review.py` (disabled docs/redoc/openapi route coverage,
  shared keyboard + queue-filter coverage, surface-URL render).
- `tests/test_web_ui_shared.py` (no-CDN scan, chrome surface-tabs source-of-truth).

I did not edit implementation, templates, or tests; this artifact is the
only file I wrote.

## Verdict summary

`accept`.

The second repair narrows to two correctness/security closures (AC001 and
AC002) and is shaped to leave the accepted ergonomics surface alone. The
repair does both:

- AC001 removes only the framework's auto-generated *developer* surfaces
  (`/docs`, `/redoc`, `/openapi.json`). The handoff and RFC 0038 never
  promised these as operator-facing affordances; the bench operator UI
  consists of the rendered templates under `bench_review/templates/`
  (`/`, `/segments`, `/segments/{id}`, `/segments/{id}/excerpt`,
  `/summary`). None of those affordances change.
- AC002 adds `::1` to the Origin allowlist *only* when the bench / interview
  app is constructed with a validated IPv6 loopback bind. The default
  IPv4-bound app still rejects IPv6 Origins, mismatched ports, missing
  Origins, and non-same-origin `Sec-Fetch-Site`. The CLI-validated
  `host="::1"` flag is the explicit opt-in.

The prior round's `accept` surface (FU101–FU105 + F017 + carry-forward
F008/F010/F013/F015/F018) is preserved without regression. The bench
cross-surface tab still uses the bench-configured `INTERVIEW_URL` (default
`http://127.0.0.1:8765/`); the interview cross-surface tab still uses the
app-factory `bench_url` parameter (default
`http://127.0.0.1:8770/segments?remaining=1&reviewable=1`); both shared
chrome partials (`_app_shell`, `_surface_tabs`, `_audit_footer`,
`_status_banner`, `_cli_command_card`, `_help_modal`, `_future_slot`)
remain the single source of truth; the shared `/shared-static/keyboard.js`
dispatcher plus the bench-only `queue_filter.js` enhancement remain
exactly as accepted.

One trivial new ergonomics observation surfaced from this round's scan —
the IPv6 audit-footer bind-address format is unbracketed (`::1:8765`
rather than the RFC 3986 `[::1]:8765`). This is logged as N301 below and
is **not** a blocker; it is a polish item for the IPv6 opt-in path only.

## AC dispositions (ergonomics-facing impact)

### AC001 — Bench `/docs`, `/redoc`, `/openapi.json` were CDN-backed FastAPI defaults
Disposition: **resolved, no operator-UI affordance loss.**

- `src/engram/bench_review/web.py:89–94` now constructs
  `FastAPI(title="Engram bench review", docs_url=None, redoc_url=None,
  openapi_url=None)`, matching the interview app's posture
  (`interview/web.py:763–768`).
- These routes were not surfaced anywhere in the operator UI. The bench
  index, segment list, segment detail, excerpt fragment, and summary pages
  do not (and never did) link to `/docs`, `/redoc`, or `/openapi.json`;
  RFC 0038 § Non-Goals explicitly excludes CDN assets, and the handoff
  describes only the templated server-rendered surfaces as operator UI.
- The help modal (`_help_modal.html`, surfaced via `?` and the shared
  shortcut row "? Open help") contains decision-help rows, shortcut rows,
  and disclosure lines — not generated docs links. A first-time operator
  hitting `?` still sees the same help content as before this repair.
- Pinned mechanically by
  `tests/test_bench_review.py::test_create_app_disables_generated_docs_and_openapi_routes`
  (parametrized over `/docs`, `/redoc`, `/openapi.json`; all assert 404).
- Net ergonomics effect: positive but invisible to the operator; the
  local-first / no-CDN surface is now reachable through the framework-
  generated route surface as well, not only through templates/static.

### AC002 — Interview IPv6 loopback POSTs were rejected even when bound on `::1`
Disposition: **resolved with no operator confusion for the IPv4 default; one trivial polish item filed for the IPv6 opt-in path.**

- `src/engram/interview/web.py:69–119` defines
  `_DEFAULT_ALLOWED_ORIGIN_HOSTS=("127.0.0.1","localhost")`,
  `_LOOPBACK_BIND_HOSTS=frozenset({"127.0.0.1","localhost","::1"})`, and
  `_allowed_origin_hosts_for_bind(host)` which appends `::1` to the
  Origin allowlist *only* when the host is `::1` (the IPv6 loopback opt-in).
- `create_app(host=...)` validates `host` against `_LOOPBACK_BIND_HOSTS`
  and stores the resolved allowlist on `app.state.engram_allowed_origin_hosts`
  for per-request lookup (`interview/web.py:761–771`).
- Bench already had a `::1` branch (`bench_review/web.py:25`); the interview
  now matches the bench's posture so an operator running both surfaces
  bound on `::1` gets symmetric Origin enforcement.
- Pinned mechanically by three tests:
  `tests/test_interview_web.py::test_post_verdict_accepts_ipv6_loopback_origin_for_ipv6_bind`
  (positive: `create_app(host="::1")` + `Origin: http://[::1]:8765`),
  `tests/test_interview_web.py::test_post_verdict_rejects_ipv6_origin_when_not_ipv6_bound`
  (negative: default IPv4 bind still rejects IPv6 Origin),
  `tests/test_interview_web.py::test_allowed_origin_hosts_for_ipv6_bind_adds_ipv6_loopback`
  (resolver-level coverage).
- Ergonomics effect on the IPv4 default (the documented "normal" path):
  none. A first-time operator running `engram phase3 interview` on
  `127.0.0.1` sees exactly the same audit-footer text, surface tabs,
  banners, and POST behavior as before this repair.
- Ergonomics effect on the IPv6 opt-in path: see N301 below.

## Net-new ergonomics observation from this round

### N301 — Audit-footer bind-address text is unbracketed for IPv6 loopback
Severity: trivial
Source: `src/engram/interview/web.py:266–269` (`_format_bind_address`);
`src/engram/bench_review/web.py:99` (`bind_address=f"{host}:{port}"`);
`src/engram/web/templates/_audit_footer.html:2`.

When the interview or bench app is bound on `::1`, `_format_bind_address`
returns `"::1:8765"` (or `"::1:8770"`), and the shared audit footer
renders:

```
local-only · loopback bind: ::1:8765 · no network egress.
```

RFC 3986 § 3.2.2 requires brackets around IPv6 literals in URI authority
(`[::1]:8765`). As displayed footer text it is not a URI, but the
unbracketed form is technically ambiguous: a reader scanning quickly could
misread the trailing `:8765` as part of the IPv6 address rather than as
the port separator. This matters only on the IPv6 opt-in path; the IPv4
default (`127.0.0.1:8765`) reads unambiguously.

This is genuinely trivial:

- The operator who is on the IPv6 path explicitly typed `--host ::1` on
  the CLI to reach this state, so the syntax is consistent with what they
  entered.
- The audit footer is descriptive (a local-first / no-egress reassurance),
  not a URL the operator pastes into a browser.
- The cross-surface tabs default to IPv4 URLs (`127.0.0.1`) regardless of
  bind, so the IPv6 footer text is not the operator's only cue about
  reachable URLs.

Proposed fix when this is polished: bracket IPv6 literals when formatting
the audit-footer bind address, e.g. `f"[{host}]:{port}"` when
`":" in host`. Trivial; not blocking; follow-up scope.

## Carry-forward observations preserved by this round (status unchanged)

The prior ergonomics review's accepted carry-forward items are explicitly
scoped out by `SECOND_REPAIR_EVIDENCE.md` § "Residual Risk" and confirmed
unchanged in the source:

- **F008 — Bench index resume CTA buried below metrics.**
  `bench_review/templates/index.html` unchanged. Open polish.
- **F010 — Bench index (5 metrics) vs summary (4 metrics) parity.**
  Templates unchanged. Open polish.
- **F013 — Interview question stacks 6+ metadata rows before evidence.**
  `interview/templates/_question_content.html` unchanged. Open polish.
- **F015 — Bench segment detail "Back to this queue" only, no
  "Next in queue".** `segment.html` unchanged. Open polish.
- **F018 — Commit-on-click vs rationale-required visual cue.**
  `_question_content.html` unchanged. Open polish.
- **N201 — Save-and-quit banner uses `kind="warn"` for an informational
  message.** `interview/templates/index.html:19–25` still wraps the
  save-and-quit message with `kind="warn"`. Unchanged from prior round.
- **N202 — Save-and-quit banner embeds the CLI command in its sentence
  rather than using `_cli_command_card`.** Unchanged from prior round.
- **N203 — Cross-surface tabs degrade to "browser-level connection
  refused" when the other surface is not running.** Unchanged design
  trade-off; the corresponding tabs in `_surface_tabs.html:2–5` still
  emit real `<a href>` elements.
- **N204 — Asymmetric env-var names for cross-surface URL overrides
  (`ENGRAM_INTERVIEW_BENCH_URL` vs `ENGRAM_BENCH_REVIEW_INTERVIEW_URL`).**
  Unchanged. Documentation concern, not a defect.

The second repair does not touch any of these surfaces, so the prior
accepted ergonomics posture is preserved exactly.

## Positive notes preserved by this round

- The shared keyboard dispatcher (`/shared-static/keyboard.js`) is still
  the sole binder for `[data-key]`, `[data-help-open]`, and
  `[data-copy-command]` across both surfaces; the bench-only
  `queue_filter.js` enhancement still handles only `/`-focus and tbody
  filtering. The shared/enhancement split is intact
  (`tests/test_bench_review.py::test_bench_loads_shared_keyboard_and_queue_filter_enhancement`).
- The empty-corpus banner on the interview index still pairs
  `_status_banner.html` (kind="warn", role="status") with
  `_cli_command_card.html` for the `engram phase4 refresh-current-beliefs`
  command, with a real shared-dispatcher copy button
  (`interview/templates/index.html:6–14`).
- The interview `_app_shell.html` chrome (brand line, surface tabs, `?`
  help button, audit footer) and the bench equivalent share the same
  partials; the prior round's removal of `chrome.DEFAULT_SURFACE_TABS`
  remains in effect (single source of truth is `_surface_tabs.html`).
- The audit-footer truth invariant (`_audit_footer.html` reads
  `bind_address` from `app.state.engram_bind_address` or the live
  Uvicorn server scope) is preserved on the IPv4 default path. The IPv6
  path uses the same plumbing; only the rendered string format triggers
  N301.
- The cross-surface tab targets remain real links on both surfaces with
  symmetric env-var overrides
  (`ENGRAM_INTERVIEW_BENCH_URL` / `ENGRAM_BENCH_REVIEW_INTERVIEW_URL`)
  and sensible cross-port defaults — `test_index_renders_no_open_sessions`,
  `test_index_uses_configured_bench_url`, and
  `test_interview_bench_url_resolver_defaults_and_overrides` continue
  to pin this.
- The "does not mutate" disclaimer continues to render on bench index,
  segment detail, and summary via `_status_banner.html` + `bench_disclaimer`.
- The no-CDN / no-external-asset invariant continues to hold per
  `tests/test_web_ui_shared.py::test_shared_resources_have_no_external_asset_references`;
  with AC001 closed, FastAPI's auto-generated CDN-backed routes are now
  also covered by an explicit per-route 404 assertion.

## Verification performed

This review is artifact-only (review_only_artifact write scope). The
verification I performed:

- Read `RFC-0038`, `ENGRAM_UI_REWORK_HANDOFF.md` (skim of the relevant
  shared/interview/bench surface sections), the prior accept-with-findings
  ergonomics review (verdict `accept`), the blocking correctness review
  (AC001/AC002 details), the second-repair evidence packet, the
  multi-agent review loop doc, and AGENTS.md.
- Cross-checked the bench `create_app` constructor against AC001's
  recommended fix (line-by-line confirmation that `docs_url`, `redoc_url`,
  `openapi_url` are all `None`).
- Cross-checked the interview Origin allowlist resolver against AC002's
  recommended fix (line-by-line confirmation of `_LOOPBACK_BIND_HOSTS`,
  `_allowed_origin_hosts_for_bind`, `_allowed_origin_hosts_for_request`,
  `app.state.engram_allowed_origin_hosts`).
- Walked `_audit_footer.html`, `_surface_tabs.html`, `_status_banner.html`,
  `_cli_command_card.html`, and the interview index template to confirm
  prior-round affordances are intact.
- Read the bench `INTERVIEW_URL` resolution path (module-level env-var
  read with default `http://127.0.0.1:8765/`) and the interview
  `_resolve_bench_review_url` / `create_app(bench_url=...)` path to
  confirm both directions of the cross-surface tab still work on default
  ports.
- Inspected the IPv6 positive test, the IPv6 negative test, the resolver
  unit test, and the bench docs-route 404 parametrized test in
  `tests/test_interview_web.py` and `tests/test_bench_review.py` to
  confirm mechanical coverage of the repair surface.
- Surfaced N301 by tracing `_format_bind_address("::1", 8765)` →
  `"::1:8765"` and reading the resulting `_audit_footer.html` render.

## Not run

The reviewer write scope explicitly restricts me to writing this artifact
only. I did not:

- run `make test` or any pytest invocation;
- run browser / Playwright responsive screenshot checks;
- run `pytest-socket` or an OS-level egress-deny wrapper;
- run an end-to-end IPv6 browser session on `::1`;
- install dependencies or use the network.

The blocking correctness review (codex) already ran the focused interview
+ bench + shared + render suites green (`85 passed in 58.49s` + `64 passed
in 0.24s` + `49 passed in 1.44s`) and the explicit generated-route probe
(bench `/docs`, `/redoc`, `/openapi.json` all 404 with no CDN markers).
The mechanical coverage pinning AC001 and AC002 in place is sufficient to
let an ergonomics reviewer evaluate from-source without re-running.

## Suggested verdict

`accept`.

The second repair closes AC001 and AC002 without touching the accepted
ergonomics posture from the prior round. Generated FastAPI docs/openapi
routes were never operator-facing affordances, so their removal removes
nothing the handoff promised. IPv6 loopback Origin support is gated to
the explicit `host="::1"` opt-in, leaving the default IPv4 flow visually
and behaviorally identical to the prior accepted surface. The shared
chrome, cross-surface tabs (both directions, both defaults, both env-var
overrides), shared keyboard dispatcher + bench-only enhancement split,
shared status banners, audit footer, help modal, and future-slot
rendering are all preserved. Carry-forward polish items (F008, F010,
F013, F015, F018, N201, N202, N203, N204) remain unchanged and honestly
tracked in `SECOND_REPAIR_EVIDENCE.md` § "Residual Risk". One trivial
new polish item (N301 — unbracketed IPv6 audit-footer text) is filed for
follow-up; it is not a merge blocker.

End of second-repair ergonomics review.
