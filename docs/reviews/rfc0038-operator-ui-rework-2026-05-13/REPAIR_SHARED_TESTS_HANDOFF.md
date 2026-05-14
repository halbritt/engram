# RFC 0038 Shared/Test Repair Handoff
author: operator [self-declared: rfc0038-repair-shared-tests]

Date: 2026-05-13
Job: `repair_shared_and_tests`
Branch: `engram/rfc0038-ui-rework`

## Scope

Repaired only the shared substrate and test-dependency lane. No interview or
bench implementation files were edited.

## Files Changed

- `pyproject.toml`
  - Added bounded dev/test dependency `httpx>=0.27,<0.29` for
    Starlette/FastAPI `TestClient` collection.
  - Preserved the existing `engram.web` package-data registration.
- `src/engram/web/static/keyboard.js`
  - Added shared `data-copy-command` clipboard handling for the shared
    CLI command card.
- `src/engram/web/*.py`
  - Focus-formatted the shared Python helpers with Ruff.
- `tests/test_web_ui_shared.py`
  - Added assertions for the `httpx` dev dependency, shared shell partial
    wiring, package-local keyboard script reference, inert future slot, and
    shared CLI command-card copy support.
  - Fixed import ordering and applied Ruff format.

## Commands Run

- `striatum ack --session-id sess_2065a99cf9b94969a2d18fc4bde17549 --message-id msg_9a898b8f0389483d836ab0a467e57407 --lease-id lease_6b266aa870c54121b2faead7c1217425` — pass.
- `wc -l ...` over required context docs — pass.
- `git status --short` — observed dirty worktree with unrelated interview,
  bench, Striatum, and report changes already present.
- `sed -n ...` reads for required canonical docs, RFC 0038, reviews,
  integration evidence, process docs, coding standard, prompt, and changelog.
- `.venv/bin/python -c "import importlib.metadata ...; import httpx"` —
  failed because the current venv does not have `httpx` installed.
- `.venv/bin/python -m ruff check src/engram/web tests/test_web_ui_shared.py`
  — initially failed on import ordering, then passed after fix.
- `.venv/bin/python -m ruff format --check src/engram/web tests/test_web_ui_shared.py`
  — initially reported 7 files needing format, then passed after format.
- `.venv/bin/python -m ruff check --fix src/engram/web tests/test_web_ui_shared.py`
  — pass, fixed 1 import-order issue.
- `.venv/bin/python -m ruff format src/engram/web tests/test_web_ui_shared.py`
  — pass, formatted 7 Python files.
- `.venv/bin/python -m pytest tests/test_web_ui_shared.py` — pass,
  19 passed.
- `.venv/bin/python -m py_compile src/engram/web/__init__.py src/engram/web/assets.py src/engram/web/chrome.py src/engram/web/origin.py src/engram/web/status.py src/engram/web/tier.py tests/test_web_ui_shared.py`
  — pass.
- `git diff --check` — pass.

## Verification Summary

Passing:

- Shared UI tests: `19 passed`.
- Focused Ruff check: pass.
- Focused Ruff format check: pass.
- Focused Python compile: pass.
- Whitespace diff check: pass.

Not run:

- `tests/test_interview_web.py` and `tests/test_bench_review.py` were not
  rerun because the current venv still lacks `httpx`; this repair declares
  the missing dependency but did not run a dependency install under the
  no-network constraint.
- `make test` was not run for the same reason and because unrelated dirty
  interview/bench files are outside this lane.

## Residual Risks

- The route-test collection blocker should clear after the dev extra is
  installed in an environment with `httpx>=0.27,<0.29` available.
- Correctness review C001 (bench FastAPI response annotation), C003/C004
  (surface integration / bench origin enforcement), and ergonomics findings
  that require interview or bench template/web changes remain out of this
  lane's write scope.
- `CHANGELOG.md` was read but not edited because it is outside this work
  packet's allowed write paths.
