author: operator [self-declared: rfc0038-accept-findings-interview]

# RFC 0038 Accept-with-Findings Interview Handoff

Date: 2026-05-13
Lane: codex_interview
Job: implement_interview_followups
Verdict: pass

## Scope

Implemented the interview-owned corrected-review follow-ups from
`REVIEW_corrected_security_claude.md` and
`REVIEW_corrected_ergonomics_claude.md`.

The patch stays inside the interview surface, its focused route tests, and
this handoff artifact. No network access, dependency installation, bench
edits, shared-substrate edits, canonical-doc edits, migration edits, or
production-data writes were used.

## Changed Files

- `src/engram/interview/web.py`
  - Adds `ENGRAM_INTERVIEW_BENCH_URL` support with a safe default of
    `http://127.0.0.1:8770/segments?remaining=1&reviewable=1`, then passes
    that URL into the shared surface tabs.
  - Routes interview POST Origin / `Sec-Fetch-Site` enforcement through
    `engram.web.origin.require_origin` while preserving strict same-origin
    behavior.
  - Routes interview privacy-tier checks through
    `engram.web.tier.require_tier_ceiling` while preserving the existing
    `privacy_tier_ceiling` response envelope.
  - Sources audit-footer bind text from the ASGI server socket when available,
    with an app-factory bind configuration fallback, instead of a request-Host
    fallback literal.
  - Adds `create_app(host=..., port=..., bench_url=...)` configuration and
    rejects non-loopback app-factory hosts.
- `src/engram/interview/templates/index.html`
  - Replaces the empty-corpus and save-and-quit local banner sections with the
    shared `_status_banner.html` partial.
- `src/engram/interview/templates/base.html`
  - Removes the interview-local `.banner-status` CSS.
  - Removes the duplicate inline `[data-copy-command]` click handler, leaving
    the htmx busy-state behavior in place.
- `tests/test_interview_web.py`
  - Pins the configured bench URL, custom bind-address footer rendering, shared
    Origin/tier helper delegation, shared banner rendering, and removal of the
    duplicate copy-command handler.

## Finding Disposition

- FU101: accepted and resolved. The interview tab now links to a configured
  bench-review URL with a local safe default; the broken same-origin
  `/segments?...` href is no longer rendered.
- CS001: accepted and resolved for the interview lane. Origin and tier checks
  now delegate to the shared helpers without relaxing the same-origin policy or
  Tier 1 ceiling.
- CS002: accepted and resolved. Footer bind text no longer falls back to a
  hard-coded request-Host-derived `127.0.0.1:8765` literal; it uses ASGI
  server socket metadata or app-factory bind configuration and fails loud if
  neither exists.
- FU103: accepted and resolved. Interview index banners now use the shared
  status-banner partial.
- FU104: accepted and resolved. The duplicate interview copy-command handler
  is removed; the shared keyboard script owns copy behavior.

## Verification

Commands run:

- `striatum ack --session-id sess_7025aeef44104da095feaf2d442fb284 --message-id msg_7be14ef0f33a421f830bce695fbab7b4 --lease-id lease_5e26e2e5b0364745a0c9827a8679263d`
  - Pass.
- `striatum heartbeat --session-id sess_7025aeef44104da095feaf2d442fb284 --lease-id lease_5e26e2e5b0364745a0c9827a8679263d`
  - Pass.
- `psql postgresql:///engram_test -c "SELECT 1"`
  - Pass.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -c "import httpx; print(httpx.__version__)"`
  - Pass: `0.28.1`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py::test_index_renders_no_open_sessions tests/test_interview_web.py::test_index_uses_configured_bench_url tests/test_interview_web.py::test_create_app_uses_configured_bind_address tests/test_interview_web.py::test_post_sessions_empty_corpus_renders_diagnostic tests/test_interview_web.py::test_origin_check_delegates_to_shared_helper tests/test_interview_web.py::test_tier_check_delegates_to_shared_helper tests/test_interview_web.py::test_interview_bench_url_resolver_defaults_and_overrides tests/test_interview_web.py::test_post_save_and_quit_discards_in_progress`
  - Pass: `8 passed in 6.78s`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py`
  - Pass: `54 passed in 57.25s`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py tests/test_bench_review.py`
  - Pass: `79 passed in 55.60s`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_web_ui_shared.py tests/test_interview_render.py`
  - Pass: `64 passed in 0.24s`.
- `.venv/bin/python -m py_compile src/engram/interview/web.py tests/test_interview_web.py`
  - Pass.
- `.venv/bin/python -m ruff check src/engram/interview/web.py tests/test_interview_web.py`
  - Pass: `All checks passed!`.
- `.venv/bin/python -m ruff format --check src/engram/interview/web.py tests/test_interview_web.py`
  - Pass: `2 files already formatted`.
- `git diff --check -- src/engram/interview/web.py src/engram/interview/templates/base.html src/engram/interview/templates/index.html tests/test_interview_web.py docs/reviews/rfc0038-operator-ui-rework-2026-05-13/ACCEPT_FINDINGS_INTERVIEW_HANDOFF.md`
  - Pass.

`ruff format src/engram/interview/web.py tests/test_interview_web.py` was run
once after the first format check reported that the touched test file needed
formatting.

## Not Run

- `make test` was not run.
- Browser/Playwright responsive checks were not run.
- No dependency install was attempted because this job forbids network use.

## Remaining Risk

- The tab degradation path to a disabled bench tab was not implemented because
  the shared `_surface_tabs.html` template is outside this lane's write scope.
  This lane instead makes the tab usable with a symmetric local default and
  `ENGRAM_INTERVIEW_BENCH_URL` override.
- The audit footer depends on standard ASGI `scope["server"]` metadata for
  runtime socket truth when the module-global app is served on a non-default
  port. Uvicorn provides that metadata; the app-factory fallback covers tests
  and direct `create_app(...)` use.
- The active virtualenv still requires the documented local user-site
  `PYTHONPATH` workaround for route tests because `httpx` is not installed in
  `.venv`.
- `CHANGELOG.md` was not updated because this packet explicitly forbids edits
  to that file.
