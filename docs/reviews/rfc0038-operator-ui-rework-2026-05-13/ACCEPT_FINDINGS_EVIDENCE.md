author: operator [self-declared: rfc0038-accept-findings-evidence]

# RFC 0038 Accept-with-Findings Evidence

Date: 2026-05-13
Completed at: 2026-05-13T23:10:26Z
Lane: codex_review
Job: accept_findings_evidence
Branch: `engram/rfc0038-ui-rework`
Verdict: pass

## Scope

Focused evidence pass after the accept-with-findings implementation handoffs:

- `ACCEPT_FINDINGS_INTERVIEW_HANDOFF.md`
- `ACCEPT_FINDINGS_BENCH_HANDOFF.md`
- `ACCEPT_FINDINGS_SHARED_HANDOFF.md`

No implementation files were edited. This pass wrote only this evidence
artifact. No dependency install and no network access were used.

## Summary

The focused accept-with-findings evidence is green.

- DB-backed interview plus bench route suite: `79 passed in 64.62s`.
- Shared substrate plus interview-render tests: `64 passed in 0.24s`.
- Bench plus shared substrate focused suite: `46 passed in 1.39s`.
- Route construction smoke passed for both apps.
- No-CDN/static scan passed across 27 shared/interview/bench resources.
- Jinja parse smoke passed for 9 shared, 8 interview, and 6 bench templates.
- Focused `py_compile`, Ruff check, Ruff format check, and `git diff --check`
  passed.
- `make check-refs` passed with `0 error(s), 5 warning(s), 181 check(s) ok`.
  The warnings match the existing reference-warning pattern from prior
  evidence.

The active virtualenv still lacks `httpx`; route checks used the already-local
user-site dependency path at `/home/halbritt/.local/lib/python3.12/site-packages`.

## Environment

| Check | Result |
| --- | --- |
| `.venv/bin/python -V` | `Python 3.12.3` |
| `.venv/bin/python -m pytest --version` | `pytest 8.4.2` |
| `.venv/bin/python -c "import httpx; print(httpx.__version__)"` | Failed: `ModuleNotFoundError: No module named 'httpx'` |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -c "import httpx; print(httpx.__version__)"` | Pass: `0.28.1` |
| `psql postgresql:///engram_test -c "SELECT 1"` | Pass |

## Commands And Results

| Command | Result |
| --- | --- |
| `striatum ack --session-id sess_f3d1d09e288e43b99675754577562ace --message-id msg_2ac8f54cfc624bfeab5764a162020265 --lease-id lease_70a7a92227d546b59cf1687c074c9ef8` | Pass. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py tests/test_bench_review.py` | Pass: `79 passed in 64.62s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_web_ui_shared.py tests/test_interview_render.py` | Pass: `64 passed in 0.24s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_bench_review.py tests/test_web_ui_shared.py` | Pass: `46 passed in 1.39s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python - <<'PY' ... route construction smoke ... PY` | Pass: `interview_routes=13`; `bench_routes=13`; route construction smoke passed. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python - <<'PY' ... no-CDN/static resource scan ... PY` | Pass: checked 27 shared/interview/bench template/static resources; no external asset references found. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python - <<'PY' ... Jinja parse smoke ... PY` | Pass: `shared_templates=9`; `interview_templates=8`; `bench_templates=6`; Jinja parse smoke passed. |
| `.venv/bin/python -m py_compile src/engram/web/__init__.py src/engram/web/assets.py src/engram/web/chrome.py src/engram/web/origin.py src/engram/web/status.py src/engram/web/tier.py src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass. |
| `.venv/bin/python -m ruff check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass: `All checks passed!`. |
| `.venv/bin/python -m ruff format --check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass: `11 files already formatted`. |
| `git diff --check` | Pass. |
| `make check-refs` | Pass: `0 error(s), 5 warning(s), 181 check(s) ok`. |
| `striatum heartbeat --session-id sess_f3d1d09e288e43b99675754577562ace --lease-id lease_70a7a92227d546b59cf1687c074c9ef8` | Pass. |

## Finding Status From Focused Evidence

- Interview follow-ups from `ACCEPT_FINDINGS_INTERVIEW_HANDOFF.md` are covered
  by the focused DB-backed route suite and shared/render tests. Evidence
  passed for the configured bench tab URL, shared origin/tier helper
  delegation, bind-address footer behavior, shared status banners, and removal
  of the duplicate copy-command handler.
- Bench follow-ups from `ACCEPT_FINDINGS_BENCH_HANDOFF.md` are covered by the
  DB-backed route suite, bench/shared suite, no-CDN scan, and Ruff checks.
  Evidence passed for loading the shared keyboard dispatcher, using the
  bench-only queue-filter enhancement, and preserving the shared tier-helper
  denial envelope.
- Shared cleanup from `ACCEPT_FINDINGS_SHARED_HANDOFF.md` is covered by
  `tests/test_web_ui_shared.py`, Jinja parse smoke, `py_compile`, and focused
  Ruff checks. Evidence passed for the template-owned surface-tab contract and
  removal of the dead Python tab defaults.
- The local-first/no-CDN posture remains supported by the resource scan and
  the focused route/static tests. No hosted assets, CDN markers, telemetry, or
  network dependency installs were introduced by this evidence pass.

## Not Run

- `make test` was not run; the packet requested focused follow-up evidence.
- Browser/Playwright responsive screenshot checks were not run.
- No dependency installation was attempted because network use is forbidden for
  this job.

## Residual Risk

- The active `.venv` still needs a local/offline refresh to install the
  repository-declared `httpx` dev dependency. Until then, route tests require
  the already-local user-site `PYTHONPATH` workaround.
- This is focused evidence, not a full-suite or browser-layout pass.
- Corrected-review polish items outside the accept-findings handoffs remain
  outside this evidence scope, including the bench index CTA placement,
  metric-parity polish, interview metadata density suggestion, next-in-queue
  affordance, and commit-vs-rationale visual cue.
