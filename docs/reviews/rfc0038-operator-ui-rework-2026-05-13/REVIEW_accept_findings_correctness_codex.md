author: operator [self-declared: rfc0038-accept-findings-correctness-review]

# RFC 0038 Accept-with-Findings Correctness Review

Date: 2026-05-13
Lane: codex_review
Verdict: needs_revision

## Scope

Fresh correctness review of the accept-with-findings follow-ups for RFC 0038.
I read the required canonical docs, RFC 0038, the operator UI handoff, the
corrected correctness/security/ergonomics reviews, the repair and
accept-findings evidence, the accept-findings implementation handoffs, and the
declared source/test surfaces. I did not edit implementation files.

## Findings

### AC001 - Blocker - bench FastAPI defaults expose CDN-backed docs routes

Affected files:

- `src/engram/bench_review/web.py:89`
- `src/engram/interview/web.py:745-750`
- `docs/rfcs/0038-operator-ui-rework.md:47`
- `ENGRAM_UI_REWORK_HANDOFF.md:1090-1100`

RFC 0038 explicitly excludes CDN assets and requires no-CDN/no-network checks.
The focused evidence scans templates/static resources, but the bench app still
constructs FastAPI with defaults:

```python
app = FastAPI(title="Engram bench review")
```

That leaves `/docs`, `/redoc`, and `/openapi.json` enabled. I reproduced the
current behavior with `TestClient(create_app(...))`:

```text
/docs 200 text/html; charset=utf-8
  https://
  cdn.jsdelivr.net
  swagger-ui
/redoc 200 text/html; charset=utf-8
  https://
  cdn.jsdelivr.net
  redoc
/openapi.json 200 application/json
```

The interview app disables these routes with `docs_url=None`,
`redoc_url=None`, and `openapi_url=None`; bench should do the same. Until that
lands, the no-CDN acceptance evidence is incomplete and the bench surface still
serves generated pages that reference external assets.

Recommended fix:

- Construct the bench app as
  `FastAPI(title="Engram bench review", docs_url=None, redoc_url=None, openapi_url=None)`.
- Add a bench route test asserting `/docs`, `/redoc`, and `/openapi.json` are
  404, or extend the no-CDN route walk to include framework-generated GET
  routes.

### AC002 - Major - interview accepts `::1` as a bind host but rejects valid IPv6 loopback POST origins

Affected files:

- `src/engram/cli.py:2278`
- `src/engram/interview/web.py:69-73`
- `src/engram/interview/web.py:214-223`
- `src/engram/interview/web.py:736-744`

The interview CLI and app factory both accept `::1` as loopback, but the
interview Origin allowlist defaults to only `127.0.0.1` and `localhost`. A
browser POST from an app served at `http://[::1]:8765` therefore fails the
shared Origin helper even though the host was explicitly allowed by the serve
path.

Reproduction against the current helper:

```text
Host: [::1]:8765
Origin: http://[::1]:8765
Sec-Fetch-Site: same-origin

HTTPException 403 {'error': 'origin_mismatch',
 'expected': ['http://127.0.0.1:<bound-port>',
              'http://localhost:<bound-port>']}
```

Bench has an explicit `::1` branch in `_allowed_origin_hosts`; interview does
not. This is not a default-path blocker because the normal bind is
`127.0.0.1`, but it makes one of the advertised loopback bind modes unusable
for mutating routes.

Recommended fix:

- Include `::1` in the interview default allowed Origin hosts, or derive
  allowed hosts from the configured bind host plus the default loopback aliases.
- Add a regression test for `create_app(host="::1")` or `_origin_check` with
  `Origin: http://[::1]:<port>`.

## Corrected Finding Status

| Prior item | Current status |
| --- | --- |
| CF001 active venv lacks `httpx` | Still present. The dependency is declared in `pyproject.toml`, but `.venv/bin/python -c "import httpx"` still fails. Focused route tests require the documented local user-site `PYTHONPATH` workaround. |
| CS001 shared origin/tier helper cleanup | Repaired for the main loopback path. Interview delegates to `require_origin` and `require_tier_ceiling`; bench delegates excerpt tier checks to `require_tier_ceiling`. AC002 covers the remaining IPv6 loopback correctness gap. |
| CS002 interview audit footer fallback literal | Repaired. Footer bind text comes from ASGI server socket metadata or app-factory configuration, and `create_app(port=9876)` renders `127.0.0.1:9876`. |
| FU101 interview to bench tab | Repaired. Interview now renders the configured/default bench URL instead of same-origin `/segments?...`. |
| FU102 bench keyboard duplication | Repaired. Bench loads `/shared-static/keyboard.js` plus a small `/static/queue_filter.js` enhancement. |
| FU103 shared status banners | Repaired. Interview empty-corpus and save-and-quit banners use `_status_banner.html`. |
| FU104 duplicate interview copy handler | Repaired. The duplicate `[data-copy-command]` handler is gone; the htmx busy-state script remains. |
| FU105 dead Python tab defaults | Repaired. `chrome.DEFAULT_SURFACE_TABS` and `SurfaceTab` are removed; `_surface_tabs.html` is the active render contract. |

## Verification

Commands run:

- `striatum ack ...` - pass.
- `striatum heartbeat ...` - pass.
- `.venv/bin/python -c "import httpx; print(httpx.__version__)"` - fails with `ModuleNotFoundError`.
- `psql postgresql:///engram_test -c "SELECT 1"` - pass.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py tests/test_bench_review.py` - pass, `79 passed in 55.38s`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_web_ui_shared.py tests/test_interview_render.py` - pass, `64 passed in 0.24s`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_bench_review.py tests/test_web_ui_shared.py` - pass, `46 passed in 1.74s`.
- `.venv/bin/python -m py_compile ...focused files...` - pass.
- `.venv/bin/python -m ruff check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` - pass.
- `.venv/bin/python -m ruff format --check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` - pass, `11 files already formatted`.
- `git diff --check` - pass.
- `make check-refs` - pass with `0 error(s), 5 warning(s), 181 check(s) ok`; warnings match the existing reference-warning pattern.
- `rg -n "https?://|cdn\\.|unpkg|cloudflare|jsdelivr|googleapis|googletagmanager|@import|src=\\"//|href=\\"//" src/engram/web/templates src/engram/web/static src/engram/interview/templates src/engram/interview/static src/engram/bench_review/templates src/engram/bench_review/static` - no matches.
- `TestClient` probe of bench `/docs` and `/redoc` - fails no-CDN expectation; both pages return 200 and contain `cdn.jsdelivr.net`.
- `TestClient` probe of interview `/docs`, `/redoc`, and `/openapi.json` - pass; all return 404.

## Not Run

- `make test` was not run.
- Browser/Playwright responsive screenshot checks were not run.
- No dependency install was attempted because network use is forbidden for this
  job.

## Residual Risk

The focused route and shared-substrate suites are green with the local
`httpx` workaround, and the accepted follow-up patches are otherwise in the
shape claimed by their handoffs. The remaining blocker is the unreviewed
FastAPI-generated bench docs surface, which creates an actual CDN-reference
escape hatch outside the scanned templates/static assets.
