author: operator [self-declared: rfc0038-accept-findings-shared]

# RFC 0038 Accept-with-Findings Shared Cleanup Handoff

Date: 2026-05-13
Lane: codex_shared
Job: implement_shared_cleanup
Verdict: pass

## Scope

Implemented the shared-owned corrected-review cleanup for FU105 from
`REVIEW_corrected_ergonomics_claude.md`.

Write scope was limited to `src/engram/web/`, `tests/test_web_ui_shared.py`,
and this handoff. No interview or bench surface files were edited. No network
access or dependency install was used.

## Changed Files

- `src/engram/web/chrome.py`
  - Removed the unused `SurfaceTab` dataclass and `DEFAULT_SURFACE_TABS`
    constant.
  - Left shared chrome helpers that are actually consumed by the current
    surfaces.
- `tests/test_web_ui_shared.py`
  - Added direct `_surface_tabs.html` coverage for context-provided
    `interview_url` / `bench_url`, active-tab rendering for both surfaces,
    and the disabled future Entities tab.
  - Added an explicit regression check that `engram.web.chrome` no longer
    exposes the parallel Python tab defaults.

## Finding Disposition

- FU105: accepted and resolved. The shared tab render contract is now the
  `_surface_tabs.html` template plus its tests; the dead Python-side tab model
  can no longer drift from rendered UI.
- F017: partially helped. The duplicated future-tab tooltip literal in
  `chrome.py` was removed. The remaining literal lives in the shared template,
  where it is rendered and tested.

## Verification

Commands run:

- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_web_ui_shared.py`
  - Pass: `21 passed in 0.23s`
- `.venv/bin/python -m ruff check src/engram/web tests/test_web_ui_shared.py`
  - Pass: `All checks passed!`
- `.venv/bin/python -m ruff format --check src/engram/web tests/test_web_ui_shared.py`
  - Pass: `7 files already formatted`
- `.venv/bin/python -m py_compile src/engram/web/__init__.py src/engram/web/assets.py src/engram/web/chrome.py src/engram/web/origin.py src/engram/web/status.py src/engram/web/tier.py tests/test_web_ui_shared.py`
  - Pass

`ruff format tests/test_web_ui_shared.py` was also run once after the first
format check reported that the touched test file needed formatting.

## Not Run

- Full route suites were not run; this lane did not touch interview or bench
  route/template ownership.
- `make test` was not run.
- Browser/Playwright responsive checks were not run.
- No dependency install was attempted because this job forbids network use.

## Remaining Risk

- FU101 remains out of scope: the interview surface still needs its own
  `bench_url` configuration in an interview-owned lane.
- If a future implementation wants a programmatic tab model again, it should
  add real Jinja context plumbing in the owning surfaces and update
  `_surface_tabs.html` tests in the same change. Reintroducing an unused Python
  constant would recreate FU105.
- `CHANGELOG.md` was not updated because this packet explicitly forbids edits
  to that file.
