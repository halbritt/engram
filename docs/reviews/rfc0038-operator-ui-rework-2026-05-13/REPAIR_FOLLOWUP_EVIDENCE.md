author: operator [self-declared: rfc0038-followup-evidence]

# RFC 0038 Follow-up Repair Evidence

Date: 2026-05-13
Lane: codex_review
Job: followup_evidence
Branch: `engram/rfc0038-ui-rework`

## Verdict

Result: **pass**

The remaining DB-backed interview route blocker recorded in
`REPAIR_EVIDENCE.md` is repaired. The previously failing test now passes
against `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test`, the full
interview route suite passes against the real test database, and the combined
focused interview/bench route suite passes.

The active virtualenv still does not contain `httpx`, so the focused route
checks use the already-local user-site dependency path recorded in the prior
evidence. No dependency install and no network access were attempted.

## Environment

- Python: `.venv/bin/python -V` -> `Python 3.12.3`
- Pytest: `.venv/bin/python -m pytest --version` -> `pytest 8.4.2`
- Active venv `httpx`: `.venv/bin/python -c "import httpx; print(httpx.__version__)"`
  -> failed with `ModuleNotFoundError: No module named 'httpx'`
- Local user-site `httpx`:
  `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -c "import httpx; print(httpx.__version__)"`
  -> `0.28.1`
- Database: `psql postgresql:///engram_test -c "SELECT 1"` -> pass
- Network/dependency install: no network used; no dependency installation
  attempted.

## Commands And Results

| Command | Result |
|---------|--------|
| `striatum ack --session-id sess_7b81c95c0598459a9a133dca6694bbc1 --message-id msg_7b0df5e56a2b47509196fb4f8cf5ab5b --lease-id lease_982c403f72444dcbb1da3f051c2f0a7e` | Pass. |
| `striatum heartbeat --session-id sess_7b81c95c0598459a9a133dca6694bbc1 --lease-id lease_982c403f72444dcbb1da3f051c2f0a7e` | Pass. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py::test_question_renders_predicate_intent_and_warning` | Pass: `1 passed in 1.65s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py` | Pass: `49 passed in 57.45s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py tests/test_bench_review.py` | Pass: `73 passed in 53.41s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_web_ui_shared.py tests/test_interview_render.py` | Pass: `62 passed in 0.27s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python - <<'PY' ... create_app route construction smoke ... PY` | Pass. Interview app registered 11 method/path entries; bench app registered 11 method/path entries. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python - <<'PY' ... no-CDN/static resource scan ... PY` | Pass. Checked 27 shared/interview/bench template/static resources; no external asset markers found. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python - <<'PY' ... Jinja parse smoke ... PY` | Pass. Parsed 9 shared templates, 8 interview templates, and 6 bench templates. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m py_compile src/engram/web/__init__.py src/engram/web/assets.py src/engram/web/chrome.py src/engram/web/origin.py src/engram/web/status.py src/engram/web/tier.py src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass. |
| `.venv/bin/python -m ruff check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass: `All checks passed!`. |
| `.venv/bin/python -m ruff format --check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass: `11 files already formatted`. |
| `git diff --check` | Pass. |
| `make check-refs` | Pass with `0 error(s), 5 warning(s), 181 check(s) ok`. Warnings match the prior evidence pattern: missing subrefs for `D034#request-profile`, `REVIEW-0003#context-overflow`, `PHASE-0002#generation-activation`, `D042#request-profile`, and duplicate prompt ordinal `P024`. |

## Finding Status From Focused Evidence

- The DB-backed interview route blocker is repaired. The formerly failing
  `test_question_renders_predicate_intent_and_warning` passes through the real
  database path.
- The full DB-backed interview route file passes: `49 passed`.
- The combined focused interview and bench route suite passes: `73 passed`.
- Shared substrate and interview-render tests pass: `62 passed`.
- No-CDN/static, Jinja parse, bytecode compile, focused Ruff, whitespace, and
  reference checks pass.
- The active venv still lacks `httpx`; route checks still require the
  already-local user-site `PYTHONPATH` workaround until the venv is refreshed
  from the updated dependency declaration.

## Not Run

- `make test` was not run. The packet requested focused follow-up evidence.
- Browser/Playwright responsive screenshots were not run.
- No dependency install was run because network use is forbidden for this job.

## Residual Risk

- The focused repair evidence is green, but this is not a full-suite or browser
  evidence pass.
- The `httpx` dependency state remains operationally stale in the active venv;
  a local venv refresh should remove the `PYTHONPATH` workaround.
