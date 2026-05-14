# RFC 0038 Interview UI Handoff
author: operator [self-declared: rfc0038-implement-interview]

Status: implemented
Date: 2026-05-13
RFC refs: RFC-0038, RFC-0027, RFC-0028

## Summary

Implemented the RFC 0038 gold-set interview UI slice in the interview-owned
templates and route helpers. The pass keeps the existing FastAPI/Jinja/htmx
surface, preserves the current session/security/Tier 1 guards, and adds the
operator-truthfulness and local-only presentation required by the redesign.

## Files Changed

- `src/engram/interview/web.py`
- `src/engram/interview/templates/base.html`
- `src/engram/interview/templates/index.html`
- `src/engram/interview/templates/question.html`
- `src/engram/interview/templates/_question_main.html`
- `src/engram/interview/templates/_evidence_excerpt.html`
- `tests/test_interview_web.py`

## Interview Flow Changes

- Added interview chrome with surface tabs, disabled `Entities (future)` slot,
  local-only audit footer, and help modal copy for local-only/no-CDN posture
  plus D044/D069 advisory semantics.
- Added the on-question advisory disclosure line:
  `Verdict is an advisory eval input. It does not flip belief status (D044) or gate extraction / consolidation (D069).`
- Promoted predicate intent and subject-kind warning lines into visibly styled
  question content.
- Added evidence-row `show conversation context` htmx affordances targeting the
  existing context panel route.
- Split the question body into `_question_main.html` so `HX-Request: true`
  renders a `<main id="main">` fragment without the full page shell.
- Updated empty-corpus and save/resume copy to match the handoff more closely,
  including the CLI refresh command card and URL-encoded save-and-quit banner.
- Restored `unsure` rationale behavior to optional blank rationale while
  keeping non-empty rationale enforcement for `false`, `stale`, and
  `unsupported`.

## Truthfulness / Guard Preservation

- Existing closed-session guards remain in `_require_open_session(...)` for
  resume, question render, verdict, complete, abandon, and save-and-quit.
- Existing Origin and `Sec-Fetch-Site: same-origin` enforcement remains attached
  to every POST route; tests now cover non-verdict POST routes too.
- Existing Tier 1 ceilings remain on question render, full message, context,
  and show-all evidence paths.
- The D044/D069 invariant remains: the interview route layer still does not
  import `engram.consolidator.transitions`, and the UI adds no production
  mutation controls.
- Static references remain package-local; no CDN, Google font, or external URL
  reference was introduced in interview templates/static assets.

## Tests Run

- `PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile src/engram/interview/web.py src/engram/interview/render.py tests/test_interview_web.py tests/test_interview_render.py`
- `git diff --check`
- `rg -n "unpkg\\.com|cdn\\.jsdelivr\\.net|cdnjs\\.cloudflare\\.com|googleapis\\.com|googletagmanager\\.com|@import|https?://" src/engram/interview/templates src/engram/interview/static` returned no matches.

`pytest` was not runnable in this worktree: `.venv/bin/python` is absent and
system `python3` does not have `pytest` installed. No dependency installation
was attempted because this work packet forbids network use.

## Residual Risk

- Focused route tests were added, but they need to be executed in an Engram test
  environment with `pytest` and `ENGRAM_TEST_DATABASE_URL`.
- Responsive behavior is implemented with CSS media queries, but no Playwright
  screenshot check was run in this lane.
- This lane did not implement the shared `src/engram/web/` substrate because the
  assigned write scope is interview-only; shared/bench changes in the worktree
  belong to other RFC 0038 lanes.
