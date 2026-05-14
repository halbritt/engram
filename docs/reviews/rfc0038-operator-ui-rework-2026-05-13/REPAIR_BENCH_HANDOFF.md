author: operator [self-declared: rfc0038-repair-bench]

# RFC 0038 Bench Repair Handoff

Date: 2026-05-13
Lane: codex_bench
Job: repair_bench_surface

## Summary

Repaired the bench-review surface startup, mutating-route origin enforcement,
shared chrome integration, copy affordance, future-slot/help wiring, and
segment-decision disclaimer behavior.

## Changes

- `src/engram/bench_review/web.py`
  - Changed mutating route return annotations to `Response` so FastAPI no
    longer interprets `RedirectResponse | JSONResponse` as a response model.
  - Uses a combined bench/shared Jinja loader so bench templates can extend the
    shared `_app_shell.html` and include shared chrome partials.
  - Routes mutating POST checks through `engram.web.origin.require_origin(...)`
    after validating the request host, requiring an `Origin` header and
    `Sec-Fetch-Site: same-origin`.
  - Supplies shared help, audit footer, surface-tab, future-slot, and CLI-copy
    context.
- `src/engram/bench_review/templates/`
  - Bench `base.html` now extends the shared app shell and keeps only
    bench-specific CSS/layout rules.
  - `/`, `/summary`, and `/segments/{id}` render the scratch-local disclaimer:
    `Bench review decisions do not mutate production data or bypass Phase 4 gates.`
  - `/summary` uses the shared CLI command-card partial for the redacted export
    handoff.
  - `/` renders a disabled Phase 4 future-slot card.
  - Fixed Jinja access to `copy` dict keys with bracket syntax so readiness and
    state-chip help text does not render as Python dict methods.
- `src/engram/bench_review/static/keyboard.js`
  - Reworked the dispatcher to match the shared `data-key`/help-modal pattern.
  - Added queue-filter focus and functional `data-copy-command` clipboard
    handling with a fallback copy path.
- `tests/test_bench_review.py`
  - Added app-construction route registration coverage.
  - Updated POST tests to send strict same-origin headers.
  - Added missing-Origin and missing-`Sec-Fetch-Site` rejection assertions.
  - Added assertions for shared chrome/future/help/copy/disclaimer rendering.

## Commands Run

- `striatum ack --session-id sess_550d9a10237049cda1faf6b18ea021d1 --message-id msg_5fc7183544764fe58f1ad023efbcd24c --lease-id lease_cc7070b51db34f1a8de634224218ac95` — pass.
- `.venv/bin/python -m py_compile src/engram/bench_review/web.py` — pass.
- `.venv/bin/python - <<'PY' ... create_app(...) route introspection ... PY` — pass; bench app registers GET/POST routes.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest tests/test_bench_review.py` — pass after repair: 24 passed.
- `.venv/bin/python -m ruff check src/engram/bench_review/web.py tests/test_bench_review.py` — initially found one line-length issue; pass after fix.
- `.venv/bin/python -m ruff format src/engram/bench_review/web.py tests/test_bench_review.py` — reformatted 2 files.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest tests/test_web_ui_shared.py tests/test_bench_review.py` — pass: 43 passed.
- `.venv/bin/python -m ruff check src/engram/bench_review/web.py tests/test_bench_review.py` — pass.
- `.venv/bin/python -m ruff format --check src/engram/bench_review/web.py tests/test_bench_review.py` — pass.
- `.venv/bin/python -m py_compile src/engram/bench_review/web.py tests/test_bench_review.py` — pass.
- `git diff --check -- src/engram/bench_review tests/test_bench_review.py docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_BENCH_HANDOFF.md` — pass.

## Residual Risks

- The active `.venv` still does not have `httpx`; focused route tests were run
  with `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages` so
  Starlette could import the already-local user-site `httpx`. No dependency
  installation was attempted because network access is forbidden for this job.
- Browser/Playwright responsive and keyboard-flow checks were not run.
- The bench surface now links the shared Interview tab to
  `ENGRAM_BENCH_REVIEW_INTERVIEW_URL`, defaulting to local
  `http://127.0.0.1:8765/`. Operators using a different interview port should
  set that environment variable.
- `CHANGELOG.md` was read but not edited because this job's write scope only
  allowed bench-review files, `tests/test_bench_review.py`, and this handoff.
