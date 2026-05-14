# RFC 0038 Operator UI Integration Evidence
author: operator [self-declared: rfc0038-integration-evidence]

Date: 2026-05-13
Lane: integration_evidence
Branch: `engram/rfc0038-ui-rework`

## Verdict

Result: **fail**

The shared UI and interview-render focused tests pass, and static no-CDN /
template checks pass. The combined UI rework is not ready for review because
the bench-review FastAPI app fails during `create_app(...)` route registration,
and the interview/bench route pytest modules cannot collect without `httpx`.

No implementation files were edited by this lane.

## Environment

- Python: `.venv/bin/python -V` -> `Python 3.12.3`
- Pytest: `.venv/bin/python -m pytest --version` -> `pytest 8.4.2`
- Network/dependency install: no network used; no dependency installation
  attempted.
- Worktree note: implementation lanes are present as uncommitted changes.

## Commands And Results

| Command | Result |
|---------|--------|
| `git diff --check` | Pass. No whitespace errors. |
| `make check-refs` | Pass with 0 errors, 5 warnings, 181 checks ok. Warnings were pre-existing-style reference issues: missing subrefs `D034#request-profile`, `REVIEW-0003#context-overflow`, `PHASE-0002#generation-activation`, `D042#request-profile`, and duplicate prompt ordinal `P024`. |
| `.venv/bin/python -m py_compile ...` on focused shared/interview/bench Python and tests | Pass for 12 focused files. |
| `.venv/bin/python -m ruff check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Fail: `tests/test_web_ui_shared.py:1` has `I001` unsorted imports. |
| `.venv/bin/python -m ruff format --check ...` on the same focused files | Fail: 11 files would be reformatted: `src/engram/bench_review/web.py`, `src/engram/interview/web.py`, all checked `src/engram/web/*.py`, `tests/test_bench_review.py`, `tests/test_interview_web.py`, and `tests/test_web_ui_shared.py`. |
| `.venv/bin/python -m pytest tests/test_web_ui_shared.py` | Pass: 16 passed. |
| `.venv/bin/python -m pytest tests/test_interview_render.py` | Pass: 43 passed. |
| `.venv/bin/python -m pytest tests/test_web_ui_shared.py tests/test_interview_render.py tests/test_interview_web.py tests/test_bench_review.py` | Fail during collection: `tests/test_interview_web.py` and `tests/test_bench_review.py` import `fastapi.testclient.TestClient`, and Starlette requires missing package `httpx`. |
| Jinja parse smoke for shared, interview, and bench templates | Pass: parsed 9 shared templates, 6 interview templates, and 6 bench templates. |
| Resource no-CDN scan using `engram.web.assets.find_external_asset_references` over shared/interview/bench HTML/JS/CSS resources | Pass: checked 25 resource text files; no external asset references. |
| AST import-boundary check over `src/engram/interview/web.py`, `src/engram/bench_review/web.py`, and `src/engram/web/*.py` | Pass: no imports from `engram.consolidator` or `engram.consolidator.transitions`. |
| Interview route table introspection | Pass: required 10 method/path pairs are registered on `engram.interview.web.app`. |
| Bench route table introspection via `engram.bench_review.web.create_app(...)` | Fail: FastAPI raises `FastAPIError` while registering `/segments/{segment_id}/decision`. |
| `.venv/bin/pyright ...` on focused shared/interview/bench files/tests | Fail: pyright cannot resolve installed packages in this environment and also reports local type issues in `src/engram/web/origin.py`, `src/engram/bench_review/web.py`, and `tests/test_bench_review.py`. |

## Blocking Findings

### 1. Bench app cannot be constructed

`engram.bench_review.web.create_app(review_db_path=...)` fails before serving
any route:

```text
fastapi.exceptions.FastAPIError: Invalid args for response field!
Hint: check that starlette.responses.RedirectResponse | starlette.responses.JSONResponse
is a valid Pydantic field type.
```

The first failing decorator is `src/engram/bench_review/web.py:188`, where
`segment_decision(...)` is annotated as:

```python
) -> RedirectResponse | JSONResponse:
```

FastAPI tries to derive a response model from that union. The same pattern is
also present on `run_decision(...)` at `src/engram/bench_review/web.py:262`.
This is a startup blocker for the RFC 0038 bench surface.

### 2. Route pytest cannot collect without `httpx`

Focused route tests cannot run:

```text
RuntimeError: The starlette.testclient module requires the httpx package to be installed.
```

Affected modules:

- `tests/test_interview_web.py`
- `tests/test_bench_review.py`

`pyproject.toml` currently includes the `serve` extra but does not list
`httpx` in `dev` or `serve`, so the checked-in route tests are not executable
in the current venv.

### 3. Focused style checks fail

Ruff reports an import-order failure in `tests/test_web_ui_shared.py`, and
`ruff format --check` says 11 focused files would be reformatted. This does
not block runtime by itself, but it blocks the expected green-on-touch quality
bar for the new/changed UI files.

## Passing Evidence

- Shared UI unit tests pass: `tests/test_web_ui_shared.py` -> 16 passed.
- Interview render tests pass: `tests/test_interview_render.py` -> 43 passed.
- Focused Python compile check passes for shared, interview, bench, and tests.
- Shared/interview/bench Jinja templates parse successfully.
- No external asset references were found in shared/interview/bench rendered
  resource files checked by the shared asset scanner.
- Interview route registration includes the expected RFC 0027 route set.
- Static AST import checks show the UI app modules do not import
  `engram.consolidator` or `engram.consolidator.transitions`.

## Not Run

- `make test` was not run. The target depends on `install`, and this dirty
  worktree has a changed `pyproject.toml`; invoking it could run
  `pip install -e ".[dev]"`. Under the no-network constraint, I used the
  existing venv directly and ran the focused pytest commands instead. Those
  focused commands already expose the missing `httpx` collection blocker.
- Browser/Playwright responsive screenshots were not run; no Playwright
  dependency or browser harness was used in this evidence lane.

## Residual Risk

- Once `httpx` is added to the local dev/test dependency set, the interview
  and bench route tests need to be rerun. The bench tests may then expose
  additional route behavior failures after the `create_app(...)` FastAPI
  annotation issue is fixed.
- No live database-backed route round trip was completed in this lane because
  route collection/app construction failed before those checks could run.
- Static checks cover asset references and import boundaries, but not visual
  overlap, keyboard flow, or responsive screenshots.
