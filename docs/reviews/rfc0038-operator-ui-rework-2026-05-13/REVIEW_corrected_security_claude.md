# RFC 0038 Corrected Follow-up Local-First / Security Review

author: operator [self-declared: rfc0038-corrected-security-review]

Status: review
Date: 2026-05-13
Lane: claude_security
Workflow: `rfc-0038-corrected-followup-review-2026-05-13`
Job: `corrected_review_security`
RFC refs: RFC-0038
Spec refs: ENGRAM_UI_REWORK_HANDOFF.md, Spec 0027, RFC 0027, RFC 0028, RFC 0029
Decision refs: D044, D069, D074, D080, D081
Posture: security (local-first, no-CDN, CSRF/Origin, Tier 1 ceiling,
truthful-status copy, no weakening of DB validation or provenance)
Verdict: **accept_with_findings**

## Why this pass exists

The prior follow-up security review (`REVIEW_followup_security_claude.md`)
was scored against a stale document set: it omitted the new
`REPAIR_DB_ROUTE_HANDOFF.md` and `REPAIR_FOLLOWUP_EVIDENCE.md`, and it
reviewed by reading documents only rather than the current source
surfaces. As a result it flagged S001 (bench POST origin guard
fail-open) and S003 (missing "does not mutate" banner on
`/segments/{id}`) as still-open from documents — when in fact source
inspection shows both are repaired.

This pass re-reviews against the current branch and the full input set
listed in the work packet:

- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_correctness_codex.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_followup_security_claude.md` (treated as prior, possibly stale signal)
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_DB_ROUTE_HANDOFF.md`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_FOLLOWUP_EVIDENCE.md`
- `src/engram/web/`, `src/engram/interview/`, `src/engram/bench_review/`
- `tests/test_interview_web.py`, `tests/test_bench_review.py`
- `ENGRAM_UI_REWORK_HANDOFF.md`, `docs/rfcs/0038-operator-ui-rework.md`,
  `AGENTS.md`, `CHANGELOG.md`,
  `docs/process/multi-agent-review-loop.md`,
  `docs/process/project-judgment.md`

I did not edit implementation files. Source-level claims are anchored
to file:line citations in the current branch.

## Verdict summary

`accept_with_findings`.

The two prior major security defects this loop existed to close are
repaired in source:

- **Bench POST origin guard fail-open (S001)** is closed. Bench POST
  routes now route through the shared `engram.web.origin.require_origin`
  helper, which always raises 403 if `Origin` is missing or
  `Sec-Fetch-Site` is not `same-origin`. See `bench_review/web.py:22`,
  `:114-116`, `:252`, `:315`, and `:337-345`; helper at
  `src/engram/web/origin.py:43-84`.
- **`/segments/{id}` "does not mutate" banner (S003)** is present.
  `src/engram/bench_review/templates/segment.html:4-6` includes
  `_status_banner.html` with the literal `bench_disclaimer` at the top
  of the segment-detail page — i.e., on the page where the operator
  actually commits a decision. The literal copy
  (`Bench review decisions do not mutate production data or bypass
  Phase 4 gates.`) is unchanged from the handoff §6.2.
- **DB validation preserved (S005)** under the route-test repair. The
  fixture in `tests/test_interview_web.py:98-106` now resolves
  `stability_class` from the canonical `predicate_vocabulary` row
  rather than hard-coding `"preference"`. Materialized
  `gold_label_session_targets.stability_class` reads back from the
  parent `claims` row (`tests/test_interview_web.py:184-186`). The
  trigger `fn_claims_insert_prepare_validate()` is untouched and
  continues to reject mismatched (predicate, stability_class) inserts.

Two open findings carry forward from the prior round; neither is a
present blocker for the security posture but both should land before
the substrate is treated as the single enforcement point the RFC
calls for:

- **CS001 (was S002, downgraded to minor):** Interview still routes
  POSTs through its own local `_origin_check` rather than
  `engram.web.origin.require_origin`. The local helper is functionally
  strict (same-origin, exact-loopback Origin, `Sec-Fetch-Site:
  same-origin`), but the architectural single-enforcement-point goal
  in the handoff §5.4 / §8 is half-met.
- **CS002 (was S004, scope clarified):** Interview audit-footer
  bind-address fallback is a hard-coded literal `"127.0.0.1:8765"`.
  Wrong on a non-default port reached via a non-loopback Host header
  (proxy / Tailnet path documented in D081). Bench's footer plumbing is
  correct (built from `host`/`port` at `create_app` time).

The five additional security-relevant constraints are preserved:
loopback-only bind, no-CDN / no external assets, Tier 1 ceiling, raw
evidence immutability, and the Phase 4 / promotion non-authorization
copy.

## Findings

Severity here is local-first / security severity. "Major" would mean a
handoff §5.4 / §6.3 contract is broken in the current source.
"Minor" means the constraint is held today but the design trends
drift-prone or has a narrow miss.

### CS001 — Minor — interview surface has not adopted the shared origin helper

Sources:
- `ENGRAM_UI_REWORK_HANDOFF.md` § 5.4 ("`engram.web.origin.require_origin`
  — single enforcement point. Bench's current `_origin_check` collapses
  into this.").
- `src/engram/interview/web.py:175-238` (interview defines its own
  `_origin_check` and `_get_origin_check` dependency).
- `src/engram/bench_review/web.py:22, :114-116, :337-345` (bench
  imports the shared helper and routes through it).
- `src/engram/web/origin.py:43-84` (shared helper).

Current state. Interview's local `_origin_check` enforces the same
contract the shared helper does:

- `Origin` header MUST be present (`web.py:202-207`).
- Scheme = `http`, hostname in `ALLOWED_ORIGIN_HOSTS`, exact bound
  port match, path empty/`/` (`web.py:218-228`).
- `Sec-Fetch-Site` MUST equal `same-origin` (`web.py:230-238`).

So the interview origin posture is functionally strict and matches the
shared helper's defaults. What is missing is the architectural property
the handoff named: a single enforcement point. As long as the two
helpers diverge in code, any future tightening (or any subtle drift —
e.g., Spec 0027 § 11 Open Question 9 picking the strict option in the
shared helper, but interview lagging) is a latent gap.

Tier-ceiling enforcement has the same shape: interview uses
`_check_tier_1` (`web.py:252-262`) at multiple call sites
(`web.py:597, :688, :1009, :1064, :1097, :1135, :1141`), and bench
uses an inline guard at `bench_review/web.py:222-229`, while the
shared `engram.web.tier.require_tier_ceiling` is unused. Same
"functionally correct, architecturally non-unified" shape.

Recommendation:

- Replace interview's `_origin_check` body with a call to
  `engram.web.origin.require_origin(request, allowed_hosts=ALLOWED_ORIGIN_HOSTS,
  bound_port=...)`. Keep the env-var-extended `ALLOWED_ORIGIN_HOSTS`
  resolution local; only the enforcement code moves.
- Replace `_check_tier_1` and bench's inline tier check with calls to
  `engram.web.tier.require_tier_ceiling`.
- Add a module-level test that the shared helper is the only path
  raising `origin_mismatch` from a mutating route.

This is a follow-up cleanup, not a blocker. The current functional
posture is correct.

### CS002 — Minor — interview audit footer fallback can render a wrong port

Sources:
- `src/engram/interview/web.py:282-287` (`_bind_address_for_request`
  returns the literal `"127.0.0.1:8765"` when the Host header does not
  start with `127.0.0.1:` or `localhost:`).
- `src/engram/bench_review/web.py:93-95` (bench injects
  `bind_address=f"{host}:{port}"` from the configured bind, not the
  request Host header).
- `src/engram/web/templates/_audit_footer.html:2` (shared template
  default `"127.0.0.1:<port>"` — placeholder, not a literal port; only
  reached when `bind_address` is missing entirely).
- `ENGRAM_UI_REWORK_HANDOFF.md` § 3.1, § 6.3 (audit footer is operational
  truth; "must not lie").
- `CHANGELOG.md` D081 (`ENGRAM_INTERVIEW_ALLOWED_ORIGINS` opt-in
  Tailnet/TCP-bridge pattern).

Current state. The interview's `_bind_address_for_request` has two
branches:

```python
host_header = request.headers.get("host", "")
if host_header.startswith(("127.0.0.1:", "localhost:")):
    return host_header.replace("localhost:", "127.0.0.1:", 1)
return "127.0.0.1:8765"
```

In typical loopback use, the Host header is `127.0.0.1:<actual-port>`
and the footer is correct. The narrow but real failure mode is the
D081-documented Tailnet/TCP-bridge pattern: an operator-extended
`ENGRAM_INTERVIEW_ALLOWED_ORIGINS` accepts requests with a non-loopback
Host (e.g., `engram.tailnet.example:9000`). The function refuses to
trust that Host (correct: it is defending against a non-loopback Host
spoofing the footer) but then renders the literal `127.0.0.1:8765`
regardless of the actual `--port`. The footer claim is no longer
operational truth in that scenario.

Bench does not have this issue because it builds `bind_address` from
the configured `host` / `port` at `create_app` time, independent of the
request Host header.

Recommendation:

- Resolve `bind_address` from the application configuration, not from
  the request, on the interview surface. The simplest path is to plumb
  the configured bind into `_base_context` once at startup (mirroring
  bench's `templates.env.globals.update(bind_address=...)`), then use
  the shared `engram.web.chrome.audit_footer_copy(bind_address)` to
  render the footer.
- If a runtime resolution is needed, fail loud (return 500) when the
  configured bind is unset, rather than silently displaying a literal.
  The handoff §6.3 disallows footer content the system cannot back.

Severity is minor because the path is narrow (operator opted into a
non-loopback-Host pattern AND ran a non-default port AND has not
plumbed the actual bind into the template context). The handoff still
classes the audit footer as a load-bearing trust circuit-breaker, so I
am keeping this surfaced rather than silently dropping.

## Verified preserved

The following constraints were checked against current source and prior
evidence and are preserved by the repair pass.

- **Bench POST origin guard now strict (S001 closed).**
  `bench_review/web.py:252` and `:315` both call `origin_check(request)`
  before any state change. `origin_check` first verifies the request
  host is in `ALLOWED_HOSTS` (or an opted-in DNS suffix) and then calls
  `engram.web.origin.require_origin(..., bound_port=port)`, which
  always raises 403 on missing `Origin` (`origin.py:54-56`) and
  always raises 403 on missing or non-`same-origin` `Sec-Fetch-Site`
  (`origin.py:76-84`). The C004 / S001 fail-open shape is gone in
  source.

- **`/segments/{id}` carries the "does not mutate" banner (S003 closed).**
  `bench_review/templates/segment.html:4-6` includes
  `_status_banner.html` with `kind="warn"`, `message=bench_disclaimer`
  at the top of the page. The disclaimer literal is defined at
  `bench_review/web.py:26-28` and matches the handoff verbatim.

- **DB validation under repair (S005 closed correctly).** The
  failing route test now seeds claims with a stability class read from
  the canonical `predicate_vocabulary` row
  (`tests/test_interview_web.py:78`, `:98-106`). Materialized
  session-target rows derive `stability_class` from the parent claim
  (`tests/test_interview_web.py:184-186`). The trigger
  `fn_claims_insert_prepare_validate()` is unchanged and remains the
  authority for stability/predicate validation. The repair did not
  weaken append-only triggers, predicate-vocabulary checks, or
  stability-class enforcement, as REPAIR_DB_ROUTE_HANDOFF.md §
  "Root Cause" / "Files Changed" attests and source confirms.

- **No-CDN / no external asset markers.** A repository scan over
  `src/engram/{web,interview,bench_review}` for `https?://`,
  `cdn.`, `unpkg`, `googleapis`, `cloudflare`, `jsdelivr`, and
  `googletagmanager` returned no matches in templates or static
  assets. The shared `assets.py:11-25` enumerates these markers as the
  guard set; `tests/test_web_ui_shared.py` exercises them. The only
  `127.0.0.1:8765` literal in the source tree is the
  `ENGRAM_BENCH_REVIEW_INTERVIEW_URL` env-var default at
  `bench_review/web.py:30` — used as the cross-surface link target,
  not as a footer claim. The interview-footer literal at
  `interview/web.py:287` is the CS002 issue, not a CDN issue.

- **Loopback-only bind, single-worker.** Per the handoff Stack line
  and CHANGELOG.md (D080); no source change in this round to bind
  shape. Bench `create_app` rejects non-loopback hosts at construction
  time (`bench_review/web.py:86-87`).

- **Tier 1 ceiling.** Interview's `_check_tier_1` is invoked at every
  message-rendering callsite and at the question-page entry
  (`interview/web.py:597, :688, :1009, :1064, :1097, :1135, :1141`).
  Bench's `segment_excerpt` route inline-checks
  `segment_detail.privacy_tier > 1` and 403s
  (`bench_review/web.py:222-229`). The DB trigger that surfaced the
  failing fixture is a separate predicate-vocabulary validator, not a
  tier check; tier handling is unchanged.

- **No new cloud / telemetry / hosted-auth introductions.** Neither
  REPAIR_DB_ROUTE_HANDOFF.md nor REPAIR_FOLLOWUP_EVIDENCE.md adds any
  external dependency, outbound network call, or hosted-auth surface;
  source confirms.

- **Raw evidence immutability.** The repair touches templates, web
  routes, the shared substrate package, and a route-test fixture.
  Nothing in the diff rewrites raw evidence or relaxes append-only
  invariants.

- **Phase 4 / promotion non-authorization copy.** The "scratch-local /
  not a promotion authority" framing is intact across
  `bench_review/web.py:54-61` (`BENCH_DISCLOSURE_LINES`),
  `interview/web.py:307-316` (`disclosure_lines`),
  `web/chrome.py:12` (`PHASE4_FUTURE_COPY`), and the disabled
  `Entities (future)` tab at `web/chrome.py:31-37`.

## Forward constraint for the next pass

S005 carried forward as a guard rail rather than a defect: the
predicate-vocabulary trigger is correctly rejecting bad fixtures.
**Do not** repair future test failures of this shape by modifying
the trigger, by raw-SQL bypassing the validator, or by relaxing
`predicate_vocabulary`. The accepted repair path is the one
REPAIR_DB_ROUTE_HANDOFF.md took: fix the seed.

## Outstanding items the next pass should close

1. **CS001 / handoff §5.4 / §8 — wire interview through the shared
   `require_origin` and both surfaces through `require_tier_ceiling`.**
   Functional posture is already strict; this is an architectural
   cleanup so the single-enforcement-point property holds. Tests in
   `tests/test_interview_web.py` should also assert that POST routes
   receive 403 with `{"error": "origin_mismatch", ...}` on missing
   `Origin` and missing `Sec-Fetch-Site` — these complement the
   already-existing bench coverage.
2. **CS002 — make the interview audit footer source the bind address
   from configuration, not the request.** Use
   `engram.web.chrome.audit_footer_copy` and remove the hard-coded
   `"127.0.0.1:8765"` fallback. If a runtime fallback is still
   wanted, render an explicit `<unset>` / fail-loud rather than a
   literal that can lie under D081 patterns.
3. **CS003 (carry-over from S006) — when interview adopts
   `require_origin`, keep `same-origin` strict by default and route
   any tailnet opt-out through an env-var documented at the helper
   layer, not by relaxing the helper.** This is the policy lever the
   handoff §11 Open Question 9 names; do not silently inherit a
   looser policy into the unified helper.

## Mapping to prior findings

| Prior finding | Source | Status in current source |
|---------------|--------|---------------------------|
| C004 / S001 — bench POST origin fail-open | `REVIEW_correctness_codex.md`, `REVIEW_followup_security_claude.md` | Closed at `bench_review/web.py:252,315,337-345`. |
| C003 / F001 / S002 — shared substrate built but not integrated | correctness, ergonomics, security | Closed for chrome (`interview/templates/base.html:1`, `bench_review/templates/base.html:1` both extend `_app_shell.html`) and for bench origin. **Open** for interview origin and both tier checks → carried as CS001 (minor). |
| F006 / S003 — `/segments/{id}` missing "does not mutate" banner | ergonomics, security | Closed at `bench_review/templates/segment.html:4-6`. |
| F019 / S004 — interview audit footer fallback literal | ergonomics, security | **Open**, narrow path → carried as CS002 (minor). |
| Failing DB-backed route test | `REPAIR_EVIDENCE.md`, `FC001` | Closed at `tests/test_interview_web.py:78,98-106,184-186`; no change to the trigger or vocabulary. Validation preserved per S005 forward constraint. |
| C001 — bench app cannot start | correctness | Closed per REPAIR_FOLLOWUP_EVIDENCE.md (`create_app` smoke pass) and not contradicted by source. |
| C002 — route tests cannot collect (`httpx`) | correctness | Declared in `pyproject.toml` extras per REPAIR evidence; venv refresh still pending in operator env (out of security scope). |
| Origin / Sec-Fetch-Site policy unification | handoff § 11 OQ9 / S006 | Strict default exists in `engram.web.origin.require_origin`; carried as CS003 to land when interview is wired. |

## Verdict

`accept_with_findings`.

The two prior major security findings this loop exists to close
(bench POST origin fail-open; missing "does not mutate" banner on
the segment-detail commit page) are repaired in source. The DB-route
repair preserved predicate-vocabulary and stability-class validation
exactly as required. No-CDN / loopback / Tier 1 / raw-evidence /
Phase 4 non-authorization posture is preserved.

Two minor findings carry forward (CS001 architectural unification
of the shared origin/tier helpers on the interview surface; CS002
interview audit-footer fallback literal). Neither blocks the
security posture, but both should land in the next pass so the
single-enforcement-point and "footer must not lie" contracts in the
handoff hold mechanically as well as functionally.
