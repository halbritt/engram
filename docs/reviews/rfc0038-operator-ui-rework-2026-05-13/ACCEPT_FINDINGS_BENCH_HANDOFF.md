author: operator [self-declared: rfc0038-accept-findings-bench]

# RFC 0038 Accept-with-Findings Bench Handoff

Date: 2026-05-13
Lane: codex_bench
Job: implement_bench_followups
Verdict: pass

## Scope

Implemented the bench-owned corrected-review follow-ups for FU102 and the
bench-owned portion of CS001. The patch stays inside the bench review surface,
its focused tests, and this handoff artifact.

No network access, dependency installation, interview edits, shared-substrate
edits, canonical-doc edits, migration edits, or production-data writes were
used.

## Changed Files

- `src/engram/bench_review/web.py`
  - Mounts shared static assets at `/shared-static`.
  - Points the app shell keyboard script at `/shared-static/keyboard.js`.
  - Imports and calls `engram.web.tier.require_tier_ceiling` through a tiny
    bench adapter for excerpt rendering.
  - Preserves the existing bench excerpt denial envelope:
    `{"error": "privacy_tier_ceiling", "privacy_tier": <tier>}`.
- `src/engram/bench_review/templates/base.html`
  - Loads the bench-only `/static/queue_filter.js` enhancement after htmx.
- `src/engram/bench_review/static/queue_filter.js`
  - Adds only bench-specific queue behavior: `/` focuses `#queue-filter`, and
    input events hide/show visible queue table rows.
  - Does not duplicate shared help-modal, `data-key`, copy-command, htmx
    live-region, or swapped-heading behavior.
- `tests/test_bench_review.py`
  - Pins the shared dispatcher script URL on rendered bench pages.
  - Pins the bench-local queue-filter script and verifies it does not contain
    shared dispatcher behaviors.
  - Verifies the excerpt route calls the shared tier helper while preserving
    the prior bench 403 response shape.

## Finding Disposition

- FU102: accepted and resolved. Bench now consumes the shared keyboard
  dispatcher and keeps only a small queue-filter enhancement.
- CS001, bench tier-helper portion: accepted and resolved. Bench excerpt
  rendering now uses `require_tier_ceiling` without changing current denial
  behavior.

Out-of-scope CS001 interview origin/tier cleanup and CS002 interview footer
cleanup remain for the interview lane.

## Verification

Commands run:

- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_bench_review.py`
  - Pass: `25 passed in 1.75s`
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_web_ui_shared.py`
  - Pass: `21 passed in 0.21s`
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_bench_review.py tests/test_web_ui_shared.py`
  - Pass: `46 passed in 1.71s`
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m py_compile src/engram/bench_review/web.py tests/test_bench_review.py`
  - Pass
- `.venv/bin/python -m ruff check src/engram/bench_review/web.py tests/test_bench_review.py`
  - Pass: `All checks passed!`
- `.venv/bin/python -m ruff format --check src/engram/bench_review/web.py tests/test_bench_review.py`
  - Pass: `2 files already formatted`
- `rg -n "https?://|cdn\\.|unpkg|cloudflare|jsdelivr|googleapis|googletagmanager|@import|src=\\"//|href=\\"//" src/engram/bench_review/templates src/engram/bench_review/static`
  - Pass: no matches

`ruff format tests/test_bench_review.py` was run once after the first format
check reported the touched test file needed formatting.

## Not Run

- `make test` was not run.
- Browser/Playwright responsive checks were not run.
- No dependency install was attempted because this job forbids network use.

## Remaining Risk

- This lane relies on the shared dispatcher contract in `src/engram/web`, but
  does not edit that shared code.
- The full bench segment detail page still uses template-level redaction for
  private excerpts; this patch intentionally changes only the existing excerpt
  route enforcement path.
- The active virtualenv still requires the documented local user-site
  `PYTHONPATH` workaround for route tests because `httpx` is not installed in
  `.venv`.
- `CHANGELOG.md` was not updated because this packet explicitly forbids edits
  to that file.
