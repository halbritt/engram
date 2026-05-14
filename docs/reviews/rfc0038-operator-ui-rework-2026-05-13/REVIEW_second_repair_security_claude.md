---
schema_version: "striatum.finding.v1"
artifact_kind: "finding"
verdict_intent: "accept"
severity: "info"
---

author: operator [self-declared: rfc0038-second-repair-security-review]

# RFC 0038 Second Repair Local-First / Security Review

Status: review
Date: 2026-05-13
Lane: claude_security
Workflow: `rfc-0038-accept-findings-second-repair-2026-05-13`
Job: `review_second_repair_security`
RFC refs: RFC-0038
Spec refs: ENGRAM_UI_REWORK_HANDOFF.md, Spec 0027, RFC 0027, RFC 0028, RFC 0029
Decision refs: D044, D069, D074, D080, D081
Posture: security (local-first, no-CDN, CSRF/Origin, loopback-only bind,
Tier 1 ceiling, truthful-status copy, no weakening of DB validation or
provenance)
Verdict: **accept**

## Scope

Fresh-context security review of the RFC 0038 second repair, which targeted
the two blockers from the prior correctness pass:

- AC001 — bench FastAPI default `docs_url` / `redoc_url` / `openapi_url`
  served generated pages that referenced `cdn.jsdelivr.net` (no-CDN escape
  hatch outside the template/static surface).
- AC002 — interview accepted `::1` as a bind host but rejected
  `Origin: http://[::1]:<port>` on POST routes (advertised loopback bind
  mode was unusable for mutating routes).

Inputs read for this pass:

- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_accept_findings_security_claude.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_accept_findings_correctness_codex.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_accept_findings_ergonomics_claude.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/ACCEPT_FINDINGS_EVIDENCE.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/SECOND_REPAIR_EVIDENCE.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/ACCEPT_FINDINGS_INTERVIEW_HANDOFF.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/ACCEPT_FINDINGS_BENCH_HANDOFF.md`
- `src/engram/web/`, `src/engram/interview/`, `src/engram/bench_review/`
- `tests/test_interview_web.py`, `tests/test_bench_review.py`,
  `tests/test_web_ui_shared.py`
- `AGENTS.md`, `ENGRAM_UI_REWORK_HANDOFF.md`,
  `docs/rfcs/0038-operator-ui-rework.md`,
  `docs/process/multi-agent-review-loop.md`,
  `docs/process/project-judgment.md`, `CHANGELOG.md`

No implementation or test files were edited. Source-level claims are
anchored to `file:line` citations on the current branch
(`engram/rfc0038-ui-rework`).

## Verdict summary

`accept`.

Both blockers from the prior correctness pass are repaired without
broadening the security perimeter. AC001 is closed at the framework level
on the bench side (and the interview side already had it). AC002 is closed
in a way that ties IPv6 loopback Origin acceptance to the validated bind
host stored in `app.state` — it cannot be reached without
`create_app(host="::1")` succeeding through the loopback-bind validator
first. The shared `engram.web` substrate, the no-CDN ceiling, the Tier 1
ceiling, the truthful audit-footer behavior, raw-evidence immutability, and
the Phase 4 non-authorization copy are all preserved verbatim.

I actively looked for:

- a no-CDN escape hatch via FastAPI-generated routes (`/docs`, `/redoc`,
  `/openapi.json`),
- a broadened Origin allowlist that would accept IPv6 loopback when the
  bind is IPv4 (or extend hosts beyond local loopback / operator-opted DNS
  suffixes),
- a Host-header-driven port shortcut that would let a forged Host change
  the effective Origin port the helper compares against,
- a CSRF / `Sec-Fetch-Site` weakening (e.g., implicit `none`/`same-site`
  acceptance, missing-header acceptance, missing-Origin acceptance),
- a bind validator relaxation that would let `create_app(host=...)` accept
  a non-loopback host on either surface,
- a Tier 1 ceiling relaxation introduced incidentally by the new code
  paths,
- a privacy-tier denial envelope shape regression on bench
  (`{"error": "privacy_tier_ceiling", "privacy_tier": <tier>}`),
- an audit footer that could lie under a configured bind by reintroducing
  a Host-header literal fallback,
- a hosted-auth / cloud / telemetry / external persistence import or env
  var on the changed surface,
- a DB-validation shortcut via fixtures or trigger weakening.

I found none actionable. The single residual observation (IS001 from the
prior pass — interview `_origin_check` not passing `bound_port`) is
unchanged on this branch and remains informational; the second repair did
not make it worse.

## Verified preserved

### AC001 (closed) — bench `/docs` / `/redoc` / `/openapi.json` disabled

- `src/engram/bench_review/web.py:89–94` constructs the bench app with
  ```python
  app = FastAPI(
      title="Engram bench review",
      docs_url=None,
      redoc_url=None,
      openapi_url=None,
  )
  ```
- `tests/test_bench_review.py:352–358`
  (`test_create_app_disables_generated_docs_and_openapi_routes`) is a
  parametrized regression test on `/docs`, `/redoc`, `/openapi.json` asserting
  `response.status_code == 404` via `TestClient`.
- `src/engram/interview/web.py:763–768` keeps the equivalent block on the
  interview side (`docs_url=None`, `redoc_url=None`, `openapi_url=None`).
- The second-repair evidence (`SECOND_REPAIR_EVIDENCE.md` § "AC Status",
  command row "generated route probe") confirmed all three paths return 404
  on both surfaces with `markers=[]` — no `https://`, `cdn.jsdelivr.net`,
  `swagger-ui`, or `redoc` strings in the 404 bodies.
- No-CDN scan over 27 shared/interview/bench template/static resources
  remains zero markers (same evidence § "Commands And Results"). The shared
  CDN-marker enumeration is canonical in `src/engram/web/assets.py:11–25`,
  and `tests/test_web_ui_shared.py::test_shared_resources_have_no_external_asset_references`
  continues to lock the shared substrate.

This closes the prior correctness pass's blocker without any change to the
no-CDN ceiling: the fix is purely "do not enable the generated routes,"
which is the right shape for a local-first surface that ships its own
no-CDN templates and static assets.

### AC002 (closed) — IPv6 loopback Origin acceptance is bind-bound, not blanket

The fix lives in three small surfaces, each constrained to the loopback
ceiling.

- `src/engram/interview/web.py:73` declares the loopback bind set:
  ```python
  _LOOPBACK_BIND_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1"})
  ```
- `interview/web.py:115–119` defines the bind-to-allowlist mapping:
  ```python
  def _allowed_origin_hosts_for_bind(host: str) -> tuple[str, ...]:
      if host not in _LOOPBACK_BIND_HOSTS or host in ALLOWED_ORIGIN_HOSTS:
          return ALLOWED_ORIGIN_HOSTS
      return (*ALLOWED_ORIGIN_HOSTS, host)
  ```
  `ALLOWED_ORIGIN_HOSTS` is the env-extended `("127.0.0.1", "localhost", ...)`
  set from `_resolve_allowed_origin_hosts` (`:76–100`). The function only
  *appends* `::1` when the host is in the loopback bind set and not already
  present in the env-extended tuple. It cannot widen the allowlist to any
  non-loopback host: a non-loopback `host` returns the env-extended tuple
  unchanged.
- `interview/web.py:122–128` resolves per-request:
  ```python
  def _allowed_origin_hosts_for_request(request: Request) -> tuple[str, ...]:
      state = getattr(getattr(request, "app", None), "state", None)
      configured = getattr(state, "engram_allowed_origin_hosts", None)
      if isinstance(configured, tuple) and all(isinstance(host, str) for host in configured):
          return configured
      return ALLOWED_ORIGIN_HOSTS
  ```
  The "configured" tuple is only the one populated at `create_app` time.
- `interview/web.py:754–771` plumbs the bind through the validator and into
  `app.state`:
  ```python
  if host not in _LOOPBACK_BIND_HOSTS:
      raise ValueError(f"interview host must be loopback, got {host!r}")
  ...
  app.state.engram_bind_address = _format_bind_address(host, int(port))
  app.state.engram_allowed_origin_hosts = _allowed_origin_hosts_for_bind(host)
  ```
  Non-loopback `host` raises at construction time. The `engram_allowed_origin_hosts`
  attribute is set exactly once, derived from the validated bind, and
  consumed read-only by `_allowed_origin_hosts_for_request`.
- `interview/web.py:232–241` keeps the `_origin_check` shape but pulls the
  per-app allowlist from state:
  ```python
  def _origin_check(request: Request) -> None:
      require_origin(request, allowed_hosts=_allowed_origin_hosts_for_request(request))
  ```

Tests pin both the positive and negative paths:

- `tests/test_interview_web.py:859–878`
  (`test_post_verdict_accepts_ipv6_loopback_origin_for_ipv6_bind`)
  constructs `create_app(host="::1")` with the real `conn` fixture, issues a
  verdict POST with `Host: [::1]:8765`, `Origin: http://[::1]:8765`,
  `Sec-Fetch-Site: same-origin`, and asserts `200` with `HX-Redirect` to
  the next question.
- `tests/test_interview_web.py:881–891`
  (`test_post_verdict_rejects_ipv6_origin_when_not_ipv6_bound`) issues the
  same IPv6 Origin against the default IPv4-bound TestClient and asserts
  `403 origin_mismatch`. This is the explicit guard against blanket IPv6
  acceptance.
- `tests/test_interview_web.py:981–986`
  (`test_allowed_origin_hosts_for_ipv6_bind_adds_ipv6_loopback`) asserts
  `::1` is appended only for the `::1` bind and that the `127.0.0.1` bind
  returns the env-extended default unchanged.
- The five pre-existing negative-path tests
  (`test_post_verdict_403_origin_mismatch`,
  `test_post_verdict_requires_origin_header`,
  `test_post_verdict_requires_same_origin_sec_fetch`,
  `test_post_verdict_rejects_allowed_host_on_wrong_port`,
  `test_origin_mismatch_blocks_all_post_routes` —
  `tests/test_interview_web.py:796–910`) keep the `403 origin_mismatch`
  envelope locked end-to-end for missing Origin, missing
  `Sec-Fetch-Site`, wrong-port Origin, wrong-host Origin, and all
  mutating routes.

The IPv6 acceptance is *strictly* tied to the validated bind. A default
IPv4 deployment cannot receive an IPv6 Origin acceptance through any code
path I could find: `_allowed_origin_hosts_for_bind("127.0.0.1")` returns
the env-extended default tuple, never appending `::1`. The
`ENGRAM_INTERVIEW_ALLOWED_ORIGINS` env var (`:76–100`) extends only the
host membership, never the scheme (locked to `http`) or the port logic
(derived from Host header), so an operator opt-in to a tailnet host name
does not relax the IPv6 logic either.

The bench surface uses a different but consistent shape
(`bench_review/web.py:689–696`): `_allowed_origin_hosts` derives the
allowlist from the *request* Host (gated by `_is_allowed_request_host`,
`:680–686`, which requires loopback or operator-opted DNS suffix). The
ceiling on bench is identical: an IPv4 request can never get IPv6 Origin
acceptance, because the bench helper only appends `::1` when the request
Host is `::1`. Both surfaces therefore enforce "IPv6 Origin only if you
arrived on the IPv6 (or bound to it) path."

### CSRF / Same-origin enforcement

The shared `require_origin` helper at `src/engram/web/origin.py:43–84` is
unchanged in this repair and remains the single point of CSRF enforcement.
It performs five gated checks before accepting a POST:

- `Origin` header is present (no implicit accept on missing header,
  `origin.py:54–56`).
- The Origin URL parses; parser failure raises the same 403 envelope
  (`origin.py:58–61`).
- Scheme is in `allowed_schemes` (default `("http",)`, no https upgrade)
  (`origin.py:67–73`).
- Origin hostname (normalized lowercase, trailing dot stripped) is in
  `normalized_hosts` (`origin.py:63–69`).
- Origin port matches the bound target port. Bound port resolution is
  `bound_port if bound_port is not None else request_host_port(request)`
  (`origin.py:65`). Path on Origin is empty / "/" only (`origin.py:73`).
- `Sec-Fetch-Site` is present and in `allowed_sec_fetch_sites`
  (default `("same-origin",)`, `origin.py:76–84`).

Bench's call site (`bench_review/web.py:341–349`) passes
`bound_port=port`, tying the Origin port to the configured bind.
Interview's call site (`interview/web.py:232–241`) does not pass
`bound_port`, so the helper falls back to `request_host_port(request)`.
This was IS001 in the prior security review and remains the only
observation; it does not regress in this repair and is not security-class
in the v1 threat model (browser sets Host from the bound origin; a
non-browser attacker can forge Host, Origin, and `Sec-Fetch-Site`
together regardless of which port the helper compares against, so the
delta is mental-model symmetry, not a CSRF gap). The new bind validator
+ `app.state` plumbing make the eventual one-line lift (read
`request.app.state.engram_bind_port` and forward it) mechanically
trivial; I am not raising it as a blocker.

No POST route bypasses the helper:

- Interview: every mutating handler (`POST /sessions`, `POST .../verdict`,
  `POST .../save-and-quit`, `POST .../complete`, `POST .../abandon`)
  takes `_origin: None = _ORIGIN_CHECK_DEPENDENCY`
  (`interview/web.py:223`, applied at `:813, :923, :1177, :1192, :1204`).
- Bench: `POST /segments/{id}/decision` and `POST /run-decision` both call
  `origin_check(request)` as the first line of the handler
  (`bench_review/web.py:244–256, :313–319`). The closure captures the
  validated `host`/`port` from `create_app`.

### Loopback-only bind validation (both surfaces)

- Interview: `create_app(...)` raises `ValueError("interview host must be
  loopback, got ...")` for any host not in `_LOOPBACK_BIND_HOSTS`
  (`interview/web.py:761–762`). The CLI loopback set
  (`src/engram/cli.py:2278`) matches the interview's allowlist
  (`{"127.0.0.1", "localhost", "::1"}`), so the CLI's `::1` accept path now
  has a server-side counterpart that does not reject same-origin POSTs.
- Bench: `create_app(...)` raises `ValueError("bench review host must be
  loopback, got ...")` for any host not in `ALLOWED_HOSTS`
  (`bench_review/web.py:85–88`). `ALLOWED_HOSTS` is
  `{"127.0.0.1", "localhost", "::1", "testserver"}` — the `testserver`
  entry is the Starlette TestClient default and is the same shape that
  pre-existed the second repair.
- Neither surface accepts a non-loopback bind via the factory. The
  configurable `ENGRAM_BENCH_REVIEW_ALLOWED_DNS_SUFFIXES` env var
  (`bench_review/web.py:65–82`) only opts in additional *request* Host
  suffixes for non-loopback access (e.g., a tailnet hostname); it cannot
  bypass the `ALLOWED_HOSTS` gate at `create_app` time, and a non-loopback
  request still has to satisfy the shared `require_origin` helper
  parameterized on the operator-opt-in DNS suffix.

### Tier 1 ceiling (both surfaces)

- Interview: `TIER_CEILING = 1` (`interview/web.py:149`), `_check_tier_1`
  delegates to the shared `require_tier_ceiling`
  (`src/engram/web/tier.py:24–32`) at every message-rendering callsite
  I could enumerate from the surface:
  - parent target tier guard: `interview/web.py:602–604`
  - display evidence excerpts: `:690–695`
  - `/messages/{id}` render: `:1026`
  - `/messages/{id}/context` anchor + window: `:1080–1081, :1113–1114`
  - `/q/{idx}/evidence/all`: `:1151–1152, :1155–1158`
- Bench: `_require_excerpt_tier(privacy_tier)` (`bench_review/web.py:352–370`)
  wraps `require_tier_ceiling` and re-raises with the bench-shaped
  envelope:
  ```json
  {"error": "privacy_tier_ceiling", "privacy_tier": <tier>}
  ```
  The wrapper preserves the prior bench denial envelope shape (no
  `tier`/`ceiling` rekey) even though the shared helper raises with the
  new envelope (`tier.py:10–21`). That envelope shape is locked by
  `tests/test_bench_review.py:495–517`
  (`test_excerpt_privacy_tier_above_one_rejected`).
- Default ceiling is `1` in the shared helper (`tier.py:7`). Neither
  surface raises the ceiling; the reserved env var
  `ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX` is still documented but
  unimplemented (`interview/web.py:149–155`).
- The DB-side validator (`fn_claims_insert_prepare_validate()` /
  `predicate_vocabulary` trigger from prior loops) is unchanged on this
  branch; the second repair did not edit `migrations/` or `engram.db.*`,
  consistent with the forward constraint set by the prior security review.

### Truthful audit-footer copy (CS002 still closed)

The `_bind_address_for_request` helper (`interview/web.py:285–293`) still
prefers `request.scope.get("server")` and falls back to
`app.state.engram_bind_address`, raising `RuntimeError("interview bind
address is not configured")` if neither is available. There is no
Host-header-derived literal fallback. The second repair adds the
`app.state.engram_allowed_origin_hosts` attribute without changing the
bind-address resolution path. Bench `create_app` (`bench_review/web.py:85–88,
:96–117`) still installs `bind_address=f"{host}:{port}"` into the template
globals at construction time, using the validator-checked `host`/`port`
pair. The shared `_audit_footer.html` partial's
`"127.0.0.1:<port>"` placeholder is unreachable from either surface at
runtime: interview raises before it returns nothing, and bench always
populates `bind_address` at globals install.

`tests/test_interview_web.py:352–365`
(`test_create_app_uses_configured_bind_address` constructs `port=9876` and
asserts the rendered footer matches) and `tests/test_bench_review.py:335`
(bench footer at port 8770) keep the truthful path locked on both
surfaces.

### No-CDN / no external asset markers

Two layers continue to hold:

- Static/template scan: `src/engram/web/assets.py:11–25` enumerates the
  CDN marker set (`http://`, `https://`, `unpkg.com`, `cdn.jsdelivr.net`,
  `cdnjs.cloudflare.com`, `googleapis.com`, `googletagmanager.com`,
  `@import`, `url(http://`, `url(https://`, `src="//`, `href="//`).
  `tests/test_web_ui_shared.py::test_shared_resources_have_no_external_asset_references`
  locks the shared substrate. `SECOND_REPAIR_EVIDENCE.md` reports a
  27-resource scan with `external_asset_markers=0`.
- Framework-generated routes: this repair's primary work. Both surfaces
  construct `FastAPI(..., docs_url=None, redoc_url=None, openapi_url=None)`
  (`interview/web.py:763–768`, `bench_review/web.py:89–94`). The
  parametrized 404 test on bench (`tests/test_bench_review.py:352–358`)
  and the second-repair evidence's generated-route probe close the prior
  AC001 escape hatch from outside the template scan.

No new CDN host markers, hosted-auth strings, telemetry endpoints, or
external persistence touches appear in the diff. The bench/interview
loopback URL references (`127.0.0.1:8770`, `127.0.0.1:8765`,
`expected-origin pattern http://{host}:{port}` in `origin.py:29`) are the
only matches that contain `http://`, and all are loopback-shaped.

### Phase 4 non-authorization copy

Both surfaces still ship the Phase 4 future copy intact:

- Interview disclosure lines (`interview/web.py:314–323`) and Spec 0027
  audit-footer copy (`_audit_footer.html` via shared substrate).
- Bench disclosure lines (`bench_review/web.py:55–62`), bench disclaimer
  banner ("Bench review decisions do not mutate production data or bypass
  Phase 4 gates.", `:27–29, :96–98`), and the segment-detail page banner.
- `web/chrome.py` still ships `PHASE4_FUTURE_COPY`, `LOCAL_ONLY_HELP_COPY`,
  `AUDIT_EGRESS_STATUS`, `audit_footer_copy`. `DEFAULT_SURFACE_TABS` /
  `SurfaceTab` remain deleted; the surface-tabs vocabulary lives in
  `_surface_tabs.html`. The deletion is guarded by
  `tests/test_web_ui_shared.py:123–125`.

### No new cloud / telemetry / hosted-auth introductions

The diff vs. master across `src/engram/interview/web.py` and
`src/engram/bench_review/web.py` introduces no new external dependencies.
The relevant new imports are local: `from engram.web.origin import
require_origin`, `from engram.web.tier import require_tier_ceiling`, and
`from engram.web import assets as shared_assets` on the bench side. Both
surfaces only depend on `fastapi`, `psycopg`, `jinja2`, stdlib, and
internal `engram.*` modules. `engram.web` itself is shared-substrate and
remains business-logic-free
(`tests/test_web_ui_shared.py::test_shared_package_does_not_import_business_logic`).

### DB validation preserved (S005 forward constraint)

The second repair did not touch `migrations/`, `engram.db.*`, or
`engram.interview.storage` (other than re-exports already present).
Test fixtures continue to resolve `stability_class` from the canonical
`predicate_vocabulary` table
(`tests/test_interview_web.py:98–106, :184–187`), keeping the trigger
authoritative. The forward constraint from the corrected pass (do not
weaken the trigger or vocabulary to make a fixture green) is honored.

## Mapping to prior findings

| Prior item | Source | Status in current source |
|---|---|---|
| AC001 — bench `/docs`, `/redoc`, `/openapi.json` served CDN markers | corrected correctness review | Closed at `bench_review/web.py:89–94`; tests at `tests/test_bench_review.py:352–358`; generated-route probe in `SECOND_REPAIR_EVIDENCE.md`. |
| AC002 — interview rejected IPv6 same-origin Origin for `::1` bind | corrected correctness review | Closed at `interview/web.py:73, :115–119, :122–128, :241, :754–771`; tests at `tests/test_interview_web.py:859–891, :981–986`. Negative-path tests at `:796–910` remain green. |
| CS001 — shared origin/tier helper delegation | prior security review | Still closed at `interview/web.py:62–63, :214–246` and `bench_review/web.py:22–23, :347, :356`. |
| CS002 — interview audit-footer Host-fallback literal | prior security review | Still closed at `interview/web.py:266–293`; configured-bind footer pinned by `tests/test_interview_web.py:352–365`. |
| IS001 — interview `_origin_check` does not pass `bound_port` | prior security review | Unchanged. Still informational. The new `app.state.engram_bind_port` plumbing this repair did not add is the natural place to land the one-line lift. |
| S005 forward constraint (preserve DB validation / trigger / vocabulary) | corrected security review | Honored. No `migrations/` or `engram.db.*` edits in this repair. |
| Local-first / no-CDN / loopback-bind / Tier 1 ceiling / Phase 4 non-authorization copy | RFC 0038 invariants | Preserved across both surfaces and the shared substrate. |

## Verification performed

Read-only inspection only (no implementation or test edits):

- Read context: `AGENTS.md`,
  `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_accept_findings_security_claude.md`,
  `REVIEW_accept_findings_correctness_codex.md`,
  `REVIEW_accept_findings_ergonomics_claude.md`,
  `ACCEPT_FINDINGS_EVIDENCE.md`, `SECOND_REPAIR_EVIDENCE.md`,
  `ACCEPT_FINDINGS_INTERVIEW_HANDOFF.md`,
  `ACCEPT_FINDINGS_BENCH_HANDOFF.md`,
  `docs/process/multi-agent-review-loop.md`,
  `docs/process/project-judgment.md`.
- Read source surfaces: `src/engram/interview/web.py`,
  `src/engram/bench_review/web.py`, `src/engram/web/origin.py`,
  `src/engram/web/tier.py`, `src/engram/web/assets.py`.
- Read test surfaces around the changed paths:
  `tests/test_interview_web.py` (Origin / IPv6 / shared-helper delegation
  blocks) and `tests/test_bench_review.py` (excerpt tier, generated-docs
  404, shared-keyboard wiring).
- Diff vs. master:
  - `git diff master -- src/engram/interview/web.py` — confirmed new
    `_LOOPBACK_BIND_HOSTS`, `_allowed_origin_hosts_for_bind`,
    `_allowed_origin_hosts_for_request`, `app.state.engram_allowed_origin_hosts`,
    and shared-helper delegation.
  - `git diff master -- src/engram/bench_review/web.py` — confirmed
    `docs_url=None`, `redoc_url=None`, `openapi_url=None` on
    `FastAPI(...)` and the `_origin_check` / `_require_excerpt_tier`
    helpers wiring through `engram.web.{origin,tier}`.
- Source grep for the markers / hosts:
  - `Grep "::1|ipv6|_allowed_origin_hosts" src` — IPv6 references are
    confined to loopback bind validators (`segmenter.py:1922`,
    `embedder.py:567`, `cli.py:2278`,
    `bench_review/cli.py:25`, `bench_review/web.py:25, :689–696`,
    `interview/web.py:73, :115–119, :122–128, :241, :770`). No new
    non-loopback path.
- Asserted by reading second-repair evidence: focused interview+bench
  suite `85 passed in 58.49s`; shared substrate + render `64 passed`;
  bench + shared substrate `49 passed`; explicit generated-route probe
  (`/docs`, `/redoc`, `/openapi.json` → 404, no CDN markers); 27-resource
  no-CDN scan green; ruff check + format + `git diff --check` +
  `make check-refs` green.

## Not run

- I did not execute the test suite. The second-repair evidence packet
  reported all focused suites green; this review trusts the evidence row
  rather than re-running it inside a security-only fresh context.
- I did not edit implementation or test files (write scope is
  artifact-only).
- I did not run a browser / Playwright pass.
- I did not run a network-egress wrapper (`pytest-socket` or an
  OS-level deny). The local-first ceiling continues to rely on the
  no-CDN scan + generated-route probe rather than a network sandbox.
- I did not re-validate the corrected-pass ergonomics carry-forwards
  (F008 / F010 / F013 / F015 / F018) — those are out of security scope
  and unchanged on this branch.

## Outstanding items the next pass should track (none merge-blocking)

1. **IS001 carry-forward** — interview `_origin_check` could read
   `request.app.state.engram_bind_port` (newly available alongside the
   `engram_bind_address` plumbing landed on this branch) and pass
   `bound_port=...` into the shared helper, so the helper's port
   constraint follows the configured bind rather than the request Host
   header. This is a single-mental-model tidy, not a behavior change.
2. Carry-forward ergonomics polish from the corrected pass (F008 resume
   CTA placement, F010 metric parity, F013 metadata density, F015 next-in-queue
   affordance, F017 tooltip literal, F018 commit-vs-rationale visual
   cue) and the new trivial nits the prior ergonomics pass surfaced
   (N201–N204) remain open. None are security-class. Flagged only
   because future correspondence on trust copy / status banners may
   touch the same files.

## Verdict

`accept`.

The second repair closes both AC001 and AC002 without weakening the
local-first ceiling. No-CDN, CSRF / `Sec-Fetch-Site`, loopback-only bind
validation, the Tier 1 ceiling, raw-evidence immutability, Phase 4
non-authorization copy, and the truthful audit-footer behavior are all
preserved. The IPv6 Origin acceptance path is bind-bound and cannot be
reached from a default IPv4 deployment.
