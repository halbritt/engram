author: operator [self-declared: rfc0038-repair-evidence]

# RFC 0038 Repair Evidence

Date: 2026-05-13
Lane: codex_review
Job: repair_evidence
Branch: `engram/rfc0038-ui-rework`

## Verdict

Result: **fail**

The repair lanes cleared the earlier bench FastAPI app-construction blocker,
the focused shared/interview-render tests pass, no-CDN/static checks pass, and
focused Ruff / whitespace checks pass. The real database-backed interview route
suite still fails one test:

- `tests/test_interview_web.py::test_question_renders_predicate_intent_and_warning`

Failure cause:

```text
psycopg.errors.CheckViolation: claim stability_class does not match predicate vocabulary
CONTEXT:  PL/pgSQL function fn_claims_insert_prepare_validate() line 101 at RAISE
```

The failing test seeds a `has_name` claim through the real DB path. The insert
is rejected before the route can render the predicate-intent / subject-kind
warning assertion.

## Environment

- Python: `.venv/bin/python -V` -> `Python 3.12.3`
- Pytest: `.venv/bin/python -m pytest --version` -> `pytest 8.4.2`
- Active venv `httpx`: `.venv/bin/python -c "import httpx; print(httpx.__version__)"`
  -> failed with `ModuleNotFoundError: No module named 'httpx'`
- Local user-site `httpx`: `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -c "import httpx; print(httpx.__version__)"`
  -> `0.28.1`
- Database: `psql postgresql:///engram_test -c "SELECT 1"` -> pass
- Network/dependency install: no network used; no dependency installation
  attempted.

## Commands And Results

| Command | Result |
|---------|--------|
| `striatum ack --session-id sess_5bd74654738b48a5a566747630a38c6e --message-id msg_dbbaecd4d5ef43d195ee09b904d0927e --lease-id lease_d80297364e984240a192380f391fc6d6` | Pass. |
| `striatum heartbeat --session-id sess_5bd74654738b48a5a566747630a38c6e --lease-id lease_d80297364e984240a192380f391fc6d6` | Pass. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python - <<'PY' ... create_app route construction smoke ... PY` | Pass. Interview app registered 11 method/path entries; bench app registered 11 method/path entries. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider tests/test_web_ui_shared.py tests/test_interview_render.py tests/test_interview_web.py tests/test_bench_review.py` | Pass with skipped DB route cases: `89 passed, 46 skipped`. Skips were because `ENGRAM_TEST_DATABASE_URL` was unset. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider -q -rs tests/test_interview_web.py tests/test_bench_review.py` | Pass with skips: `27 passed, 46 skipped`; every skip reason was `ENGRAM_TEST_DATABASE_URL is required for database tests`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider tests/test_interview_web.py tests/test_bench_review.py` | **Fail**: `1 failed, 72 passed`. Failure: `test_question_renders_predicate_intent_and_warning` rejected while inserting a `has_name` claim because `claim stability_class does not match predicate vocabulary`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider tests/test_web_ui_shared.py tests/test_interview_render.py` | Pass: `62 passed`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python - <<'PY' ... no-CDN/static resource scan ... PY` | Pass. Checked 26 shared/interview/bench template/static resources; no external asset markers found. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python - <<'PY' ... Jinja parse smoke ... PY` | Pass. Parsed 9 shared templates, 8 interview templates, and 6 bench templates. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m py_compile src/engram/web/__init__.py src/engram/web/assets.py src/engram/web/chrome.py src/engram/web/origin.py src/engram/web/status.py src/engram/web/tier.py src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass. |
| `.venv/bin/python -m ruff check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass: `All checks passed!` |
| `.venv/bin/python -m ruff format --check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass: `11 files already formatted`. |
| `git diff --check` | Pass. |
| `make check-refs` | Pass with `0 error(s), 5 warning(s), 181 check(s) ok`. Warnings match the prior integration evidence pattern: missing subrefs for `D034#request-profile`, `REVIEW-0003#context-overflow`, `PHASE-0002#generation-activation`, `D042#request-profile`, and duplicate prompt ordinal `P024`. |

## Finding Status From Focused Evidence

- Correctness C001 appears repaired: `engram.bench_review.web.create_app(...)`
  constructs successfully and focused bench route tests pass.
- Correctness C002 is partially repaired at the dependency-declaration level:
  `pyproject.toml` now declares `httpx>=0.27,<0.29`, and route tests collect
  when the already-local user-site `httpx` is exposed through `PYTHONPATH`.
  The active venv itself still lacks `httpx`; no install was attempted under
  the no-network constraint.
- Correctness C005 appears repaired for the focused files: Ruff check and Ruff
  format check both pass.
- Shared substrate/static checks pass: package resources exist, shared tests
  pass, templates parse, and the focused no-CDN resource scan found no external
  asset references.
- New blocking route evidence remains: one real-DB interview route test fails
  before route render because the test's `has_name` claim seed is rejected by
  the predicate/stability DB trigger.

## Not Run

- `make test` was not run. The repair prompt asked for focused checks, and the
  focused real-DB route command already produced a failing result.
- Browser/Playwright responsive screenshots were not run.
- No dependency install was run because network use is forbidden for this job.

## Residual Risk

- The failed real-DB interview route test needs repair before follow-up
  re-review treats the route/template evidence as green.
- Once the active venv is refreshed from the updated dev extra, route tests
  should no longer require the `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages`
  workaround.
