---
schema_version: "striatum.finding.v1"
artifact_kind: "finding"
verdict_intent: "accept"
severity: "info"
---

author: operator [self-declared: rfc0038-second-repair-correctness-review]

# RFC 0038 Second Repair Correctness Review

Status: review
Date: 2026-05-13
Lane: codex_review
Workflow: `rfc-0038-accept-findings-second-repair-2026-05-13`
Job: `review_second_repair_correctness`
RFC refs: RFC-0038
Decision refs: D020, D044, D069, D074, D080, D081
Verdict: **accept**

## Scope

Fresh correctness review of the RFC 0038 second repair against:

- `REVIEW_accept_findings_correctness_codex.md`
- `SECOND_REPAIR_EVIDENCE.md`
- `SECOND_REPAIR_BENCH_HANDOFF.md`
- `SECOND_REPAIR_INTERVIEW_HANDOFF.md`
- `ENGRAM_UI_REWORK_HANDOFF.md`
- `docs/rfcs/0038-operator-ui-rework.md`
- implementation and test surfaces under `src/engram/interview`,
  `src/engram/bench_review`, `src/engram/web`,
  `tests/test_interview_web.py`, `tests/test_bench_review.py`, and
  `tests/test_web_ui_shared.py`

No implementation or test files were edited.

## Findings

No correctness findings.

## AC Status

### AC001 - bench must not expose CDN-backed generated docs/openapi routes

Status: **closed**.

`src/engram/bench_review/web.py:89-94` now constructs the bench app with
`docs_url=None`, `redoc_url=None`, and `openapi_url=None`. The regression test
at `tests/test_bench_review.py:352-358` covers `/docs`, `/redoc`, and
`/openapi.json` returning 404.

I also probed the actual generated routes for both bench and interview apps:

```text
bench /docs 404 markers=[]
bench /redoc 404 markers=[]
bench /openapi.json 404 markers=[]
interview /docs 404 markers=[]
interview /redoc 404 markers=[]
interview /openapi.json 404 markers=[]
```

That covers the prior hidden escape hatch: framework-generated route behavior,
not only template/static file contents.

### AC002 - interview must accept configured IPv6 loopback same-origin POSTs

Status: **closed**.

`src/engram/interview/web.py:115-128` derives app-local Origin hosts from the
configured bind host; `create_app(host="::1")` stores that tuple on app state
at `src/engram/interview/web.py:769-770`; `_origin_check` uses the configured
tuple at `src/engram/interview/web.py:241`. The default D081 allowlist remains
`("127.0.0.1", "localhost")`, and `::1` is appended only for an IPv6 loopback
bind.

The route-level positive and negative regressions at
`tests/test_interview_web.py:859-890` passed:

- `create_app(host="::1")` accepts `Host: [::1]:8765`,
  `Origin: http://[::1]:8765`, `Sec-Fetch-Site: same-origin` on verdict POST.
- The default IPv4-bound app still rejects the same IPv6 Origin.

The helper-level default/env/IPv6 coverage at
`tests/test_interview_web.py:946-986` also passed, preserving the D081 default
and operator-extensible allowlist behavior.

## Prior Follow-Up Preservation

The accepted follow-ups did not regress in the focused route suites:

- FU101 interview-to-bench configured tab remains covered by the interview
  route suite.
- CS001 shared Origin/tier delegation remains covered by interview, bench, and
  shared helper tests.
- CS002 audit-footer bind-address truthfulness remains covered by the
  interview route tests.
- FU102 bench shared keyboard plus bench-only queue filter remains covered by
  the bench/shared tests.
- FU103 shared status banners, FU104 duplicate copy handler removal, and FU105
  surface-tab cleanup remain covered by the interview/shared tests.

The no-CDN/local-only static scan remains green across package resources:

```text
checked=27 external_asset_references=0
```

## Verification

Commands run:

- `.venv/bin/python -c "import httpx; print(httpx.__version__)"` - failed with
  `ModuleNotFoundError: No module named 'httpx'`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -c "import httpx; print(httpx.__version__)"` -
  passed: `0.28.1`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python - <<'PY' ... generated route probe ... PY` -
  passed; output shown under AC001.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_bench_review.py::test_create_app_disables_generated_docs_and_openapi_routes tests/test_interview_web.py::test_post_verdict_accepts_ipv6_loopback_origin_for_ipv6_bind tests/test_interview_web.py::test_post_verdict_rejects_ipv6_origin_when_not_ipv6_bound tests/test_interview_web.py::test_allowed_origin_hosts_for_ipv6_bind_adds_ipv6_loopback` -
  passed: `6 passed in 2.53s`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py tests/test_bench_review.py` -
  passed: `85 passed in 63.62s`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_web_ui_shared.py tests/test_interview_render.py` -
  passed: `64 passed in 0.25s`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_bench_review.py tests/test_web_ui_shared.py` -
  passed: `49 passed in 1.47s`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python - <<'PY' ... template/static no-CDN scan ... PY` -
  passed: `checked=27 external_asset_references=0`.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m py_compile src/engram/web/__init__.py src/engram/web/assets.py src/engram/web/chrome.py src/engram/web/origin.py src/engram/web/status.py src/engram/web/tier.py src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` -
  passed.
- `.venv/bin/python -m ruff check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` -
  passed: `All checks passed!`.
- `.venv/bin/python -m ruff format --check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` -
  passed: `11 files already formatted`.
- `git diff --check` - passed.

## Not Run

- `make test` was not run.
- Browser/Playwright responsive screenshot checks were not run.
- `pytest-socket` or OS-level egress-deny testing was not run.
- `make check-refs` was not run in this review pass.
- No dependency installation was attempted because network use is forbidden for
  this job.

## Residual Risk

The active `.venv` still lacks `httpx`, so route tests require the already-local
user-site `PYTHONPATH` workaround. That is unchanged from the evidence packet
and does not affect AC001/AC002 closure.

The shared `expected_origin_patterns` helper still renders unbracketed IPv6
hosts in expected-origin error copy. That is display-only for rejected
requests; the accepted configured IPv6 loopback same-origin POST path is
covered and green.
