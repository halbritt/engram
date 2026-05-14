author: operator [self-declared: rfc0038-second-repair-bench]

# RFC 0038 Second Repair Bench Handoff

Date: 2026-05-13
Lane: codex_bench
Job: repair_bench_no_cdn_docs
Verdict: pass

## Scope

Closed AC001 from
`REVIEW_accept_findings_correctness_codex.md` for the bench FastAPI app.
This repair stayed inside the assigned bench app, bench tests, and this handoff
artifact.

No network access, dependency installation, interview/shared edits,
canonical-doc edits, migration edits, changelog edits, or production-data writes
were used.

## Source Changes

- `src/engram/bench_review/web.py`
  - Constructs the bench FastAPI app with `docs_url=None`, `redoc_url=None`,
    and `openapi_url=None`.
  - This disables generated `/docs`, `/redoc`, and `/openapi.json` routes so
    the bench surface cannot serve FastAPI-generated pages that reference CDN
    assets.
- `tests/test_bench_review.py`
  - Adds a focused parametrized regression test covering `/docs`, `/redoc`,
    and `/openapi.json`.
  - The test asserts each generated-docs/openapi path returns 404 for the bench
    app.

## AC001 Status

AC001 is resolved for the bench lane. The bench app no longer exposes the
FastAPI generated docs or OpenAPI routes that previously served CDN-backed
Swagger/ReDoc assets.

## Verification

Commands run:

- `striatum ack --session-id sess_fa9d14e0c2784b5b959f9e6941d0e932 --message-id msg_639e4c79d8a64631b7ff8e2f4d043440 --lease-id lease_ce0625af5af2464eb6daf23100a22a8a`
  - Pass.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_bench_review.py`
  - Pass before formatting: `28 passed in 1.74s`.
  - Pass after formatting: `28 passed in 1.52s`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m py_compile src/engram/bench_review/web.py tests/test_bench_review.py`
  - Pass.
- `.venv/bin/python -m ruff check src/engram/bench_review/web.py tests/test_bench_review.py`
  - Pass: `All checks passed!`.
- `.venv/bin/python -m ruff format --check src/engram/bench_review/web.py tests/test_bench_review.py`
  - First run failed because `tests/test_bench_review.py` needed formatting.
  - After `.venv/bin/python -m ruff format src/engram/bench_review/web.py tests/test_bench_review.py`, rerun passed: `2 files already formatted`.
- `git diff --check -- src/engram/bench_review/web.py tests/test_bench_review.py`
  - Pass.
- `striatum heartbeat --session-id sess_fa9d14e0c2784b5b959f9e6941d0e932 --lease-id lease_ce0625af5af2464eb6daf23100a22a8a`
  - Pass.

## Not Run

- `make test` was not run; this packet requested focused bench regression
  coverage.
- Browser/Playwright responsive checks were not run.
- No dependency install was attempted because this job forbids network use.

## Residual Risk

- The active virtualenv still needs the local user-site `PYTHONPATH` workaround
  for route tests because `httpx` is not installed inside `.venv`.
- This repair covers the bench generated-docs/openapi blocker only. The
  separate interview IPv6 loopback finding from the correctness review remains
  outside this bench lane's write scope.
- The worktree already contains unrelated edits from other lanes; this repair
  did not revert or alter them.
