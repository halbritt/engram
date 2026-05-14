author: operator [self-declared: rfc0038-corrected-correctness-review]

# RFC 0038 Corrected Follow-up Correctness Review

Date: 2026-05-13
Lane: codex_review
Verdict: accept_with_findings

## Scope

Fresh correctness re-review of RFC 0038 after the DB-backed route repair. I
read the canonical project docs, RFC 0038, the UI rework handoff, prior
correctness findings, `REPAIR_EVIDENCE.md`, `REPAIR_DB_ROUTE_HANDOFF.md`,
`REPAIR_FOLLOWUP_EVIDENCE.md`, and the assigned source/test surfaces. I did
not edit implementation files.

## Findings

### CF001 - Minor - active venv still lacks `httpx`

Affected evidence / files:

- `pyproject.toml:16`
- `pyproject.toml:17`
- `REPAIR_FOLLOWUP_EVIDENCE.md`

The implementation-side dependency repair is present: `httpx>=0.27,<0.29` is
declared in the `dev` optional dependency set. However, the active `.venv`
has not been refreshed from that declaration. I reproduced the current
environment behavior:

```text
.venv/bin/python -c "import httpx; print(httpx.__version__)"
ModuleNotFoundError: No module named 'httpx'
```

and the focused route suite still fails collection without the documented
local user-site workaround:

```text
.venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py tests/test_bench_review.py
RuntimeError: The starlette.testclient module requires the httpx package to be installed.
```

This is not a remaining implementation blocker because the repository now
declares the dependency that `make install` installs for the dev environment.
It is still an evidence/operations gap: do not claim a no-workaround route
test run from the current active venv until it is refreshed.

Close-out:

Refresh the local venv from the updated dev extra using an offline/local
dependency source if network remains forbidden, then rerun the focused route
suite without `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages`.

## Prior Correctness Finding Status

| Prior finding | Corrected follow-up status |
| --- | --- |
| C001 bench review app cannot start | Repaired. `src/engram/bench_review/web.py` now annotates mutating handlers as `Response`, and app construction succeeds. |
| C002 route tests cannot collect | Source-level repair complete. `pyproject.toml` declares `httpx`; active venv remains stale, tracked as CF001. |
| C003 shared substrate not integrated | Repaired. Interview and bench `base.html` extend `_app_shell.html`, and the route tests assert the shared future tab/audit footer. |
| C004 bench POST origin guard fails open | Repaired. Bench POST routes call `_origin_check`, which delegates to `engram.web.origin.require_origin`; tests cover bad Origin, missing Origin, and missing `Sec-Fetch-Site`. |
| C005 formatting checks fail | Repaired. Focused Ruff check and format check pass. |
| DB-backed predicate-intent route blocker from `REPAIR_EVIDENCE.md` | Repaired. Test fixtures now read canonical predicate stability and materialize target stability from the claim row; the DB-backed route suite passes. |

## Verification

Commands run:

- `psql postgresql:///engram_test -c "SELECT 1"` - pass.
- `.venv/bin/python -c "import httpx; print(httpx.__version__)"` - fails with `ModuleNotFoundError` (CF001).
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py tests/test_bench_review.py` - pass, `73 passed`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_web_ui_shared.py tests/test_interview_render.py` - pass, `62 passed`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python - <<'PY' ... create_app smoke ... PY` - pass; interview and bench apps construct.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m py_compile ...focused files...` - pass.
- `.venv/bin/python -m ruff check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` - pass.
- `.venv/bin/python -m ruff format --check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` - pass, `11 files already formatted`.
- `git diff --check` - pass.
- `make check-refs` - pass with `0 error(s), 5 warning(s), 181 check(s) ok`; warnings match the repair evidence.

## Not Run

- `make test` was not run.
- Browser/Playwright responsive screenshot checks were not run.
- No dependency install was attempted because this packet forbids network use.

## Residual Risk

The corrected correctness blockers are resolved for the focused implementation
surface. Remaining risk is limited to environment freshness (`httpx` in the
active venv), lack of full-suite coverage in this pass, and lack of browser
layout evidence.
