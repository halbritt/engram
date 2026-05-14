# RFC 0038 Interview Repair Handoff
author: operator [self-declared: rfc0038-repair-interview]

Date: 2026-05-13
Lane: `codex_interview`
Job: `repair_interview_surface`

## Summary

The interview surface is now wired into the shared operator chrome contract
without changing its storage, session, CSRF/Origin, Tier 1, rationale, htmx, or
closed-session route guards.

The repair keeps the interview-specific htmx fragment boundary intact:
full-page renders use the shared app shell, while htmx question swaps still
return a standalone `<main id="main">` fragment.

## Files Changed

- `src/engram/interview/web.py`
  - Loads shared `engram.web` templates alongside interview templates.
  - Mounts shared static assets at `/shared-static` without disturbing
    `/static/htmx.min.js`.
  - Adds shared chrome context: active surface, help rows, disclosure lines,
    and shared keyboard URL.
- `src/engram/interview/templates/base.html`
  - Extends shared `_app_shell.html`.
  - Keeps interview-specific CSS, htmx loading, copy-command handling, and
    htmx busy-state handling.
- `src/engram/interview/templates/index.html`
  - Uses the shared CLI command card for the empty-corpus hint.
  - Renders the shared Phase 4 future-slot card.
  - Keeps session resume/start/abandon semantics unchanged.
- `src/engram/interview/templates/question.html`
  - Uses the shared shell for full-page question renders.
- `src/engram/interview/templates/_question_content.html`
  - New content partial shared by full-page and htmx-fragment question renders.
- `src/engram/interview/templates/_question_script.html`
  - New verdict/rationale behavior partial, preserving the existing two-click
    rationale flow.
- `src/engram/interview/templates/_question_main.html`
  - Preserves the htmx `<main id="main">` fragment wrapper.
- `tests/test_interview_web.py`
  - Adds assertions for shared header/tab/footer/help/static/future-slot
    rendering and for htmx fragments omitting full-page chrome.

Note: `src/engram/interview/templates/_evidence_excerpt.html` was already
dirty before this repair lane and was not edited by this lane.

## Commands Run

- `striatum ack --session-id sess_296b50fb90ab4e7493a76d2a77980416 --message-id msg_52db891206834d73b68e8935391e39c1 --lease-id lease_429e142e095c4ab7989494fd45974079` — pass.
- `.venv/bin/python -m pytest tests/test_interview_web.py tests/test_interview_render.py` — blocked during collection because the local venv lacks `httpx`, required by `fastapi.testclient`.
- `.venv/bin/python -m pytest tests/test_interview_render.py tests/test_web_ui_shared.py` — pass, 62 tests.
- `.venv/bin/python -m py_compile src/engram/interview/web.py` — pass.
- Interview `create_app()` route registration smoke — pass.
- Jinja parse smoke over shared and interview templates — pass.
- Manual Jinja render smoke for `index.html`, `question.html`, and `_question_main.html` — pass.
- `.venv/bin/python -m ruff format src/engram/interview/web.py tests/test_interview_web.py` — applied.
- `.venv/bin/python -m ruff check src/engram/interview/web.py tests/test_interview_web.py` — pass.
- `.venv/bin/python -m ruff format --check src/engram/interview/web.py tests/test_interview_web.py` — pass.
- `git diff --check -- src/engram/interview/web.py src/engram/interview/templates/base.html src/engram/interview/templates/index.html src/engram/interview/templates/question.html src/engram/interview/templates/_question_main.html src/engram/interview/templates/_question_content.html src/engram/interview/templates/_question_script.html tests/test_interview_web.py` — pass.

## Residual Risks

- The FastAPI route tests in `tests/test_interview_web.py` still need to run in
  an environment where `httpx` is installed. I did not install dependencies
  because the packet forbids network use; local pip cache did not contain an
  `httpx` wheel.
- This lane only repaired the interview surface. Bench chrome integration and
  bench route blockers remain outside this lane's write scope.
- `CHANGELOG.md` was read but not edited because the Striatum write scope for
  this lane permits only interview files, focused tests, and this handoff.
