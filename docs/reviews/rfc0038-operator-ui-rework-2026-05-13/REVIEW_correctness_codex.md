# RFC 0038 Implementation Correctness Review
author: operator [self-declared: rfc0038-review-correctness]

Date: 2026-05-13
Lane: review_correctness_codex
Verdict: needs_revision

## Scope

Reviewed the RFC 0038 UI implementation for shared substrate, interview UI,
bench-review UI, package data, route/template shape, and focused tests. No
implementation files were edited.

## Findings

### C001 — Blocking — bench review app cannot start

Affected files / behavior:

- `src/engram/bench_review/web.py:188`
- `src/engram/bench_review/web.py:257`

`create_app(review_db_path=...)` fails during FastAPI route registration before
any bench-review route can serve:

```text
fastapi.exceptions.FastAPIError: Invalid args for response field!
Hint: check that starlette.responses.RedirectResponse | starlette.responses.JSONResponse
is a valid Pydantic field type.
```

The failing route handlers are annotated as `RedirectResponse | JSONResponse`.
FastAPI treats those return annotations as response-model declarations unless
disabled.

Minimal change needed:

Annotate these handlers as `Response` (or remove the union annotations), or set
`response_model=None` on the decorators. Add a focused app-construction test
that imports `engram.bench_review.web` and calls `create_app(...)`.

### C002 — Blocking — checked-in route tests cannot collect in the declared dev environment

Affected files / behavior:

- `pyproject.toml:16`
- `tests/test_interview_web.py:24`
- `tests/test_bench_review.py:10`

Both route test modules import `fastapi.testclient.TestClient`, but Starlette's
test client requires `httpx`. The current `dev` and `serve` extras do not
declare `httpx`, so the focused route tests fail at collection:

```text
RuntimeError: The starlette.testclient module requires the httpx package to be installed.
```

Minimal change needed:

Add a bounded `httpx` dependency to the test/dev dependency set, then rerun
`tests/test_interview_web.py` and `tests/test_bench_review.py`. `httpx` belongs
in `dev` unless runtime code starts depending on it.

### C003 — Major — shared web substrate is packaged but not integrated into the surfaces

Affected files / behavior:

- `src/engram/web/templates/_app_shell.html:304`
- `src/engram/interview/templates/base.html:7`
- `src/engram/bench_review/templates/base.html:9`

RFC 0038 requires a shared chrome under `src/engram/web/` with interview and
bench mounted inside it. The implementation adds and packages the shared
substrate, but current rendered surfaces still use independent `base.html`
files with duplicated CSS/header/footer/help logic. A code search shows
`engram.web` is referenced only by shared tests, not by either surface.

This leaves the central shared-substrate contract unproven and allows future
footer/copy/status-chip/origin-helper drift between surfaces.

Minimal change needed:

Wire interview and bench Jinja loaders/templates to extend or include the
shared app shell and shared partials, or explicitly revise RFC 0038 to make
`src/engram/web/` a future substrate rather than current integration. Add a
route-level assertion that rendered interview and bench pages include the
shared shell/future-slot/audit-footer output from `engram.web`.

### C004 — Major — bench POST origin guard still fails open for missing browser-origin metadata

Affected files / behavior:

- `src/engram/bench_review/web.py:285`
- `src/engram/bench_review/web.py:289`
- `src/engram/bench_review/web.py:292`

RFC 0038 requires mutating bench routes to enforce an Origin allowlist. The
current bench helper only validates `Sec-Fetch-Site` if the header is present
and only validates Origin/Referer if either header is present. A POST with no
`Origin`, no `Referer`, and no `Sec-Fetch-Site` reaches the route handler.
This also bypasses the stricter shared `engram.web.origin.require_origin(...)`
helper added by the shared lane.

Minimal change needed:

Use the shared origin helper for bench POST routes, or update the local helper
to require an exact loopback Origin plus `Sec-Fetch-Site: same-origin` before
any mutation. Add tests for missing Origin and missing Sec-Fetch-Site, not just
bad-Origin cases.

### C005 — Minor — green-on-touch formatting checks fail

Affected files / behavior:

- `tests/test_web_ui_shared.py:1`
- `src/engram/web/*.py`
- `src/engram/interview/web.py`
- `src/engram/bench_review/web.py`
- `tests/test_interview_web.py`
- `tests/test_bench_review.py`

Focused ruff checks fail: one import-order error in `tests/test_web_ui_shared.py`,
and `ruff format --check` reports 11 touched files would be reformatted.

Minimal change needed:

Run `ruff check --fix` for the import ordering issue and `ruff format` on the
focused touched files after the behavioral fixes.

## Verification

Commands run:

- `git diff --check` — pass.
- `make check-refs` — pass with 0 errors, 5 pre-existing-style warnings.
- `.venv/bin/python -m pytest tests/test_web_ui_shared.py tests/test_interview_render.py` — pass, 59 tests.
- `.venv/bin/python - <<'PY' ... create_app(...) ... PY` — fails with the FastAPI response-field error in C001.
- `.venv/bin/python -m pytest tests/test_interview_web.py tests/test_bench_review.py` — fails during collection due missing `httpx` in C002.
- `.venv/bin/python -m ruff check ...focused UI files...` — fails with C005.
- `.venv/bin/python -m ruff format --check ...focused UI files...` — fails with C005.

## Residual Risk

After C001 and C002 are fixed, the route suites need to run against the real
FastAPI `TestClient` path. Additional route behavior failures may be hiding
behind the current collection/app-start blockers. No responsive screenshot or
browser keyboard-flow checks were run in this review.
