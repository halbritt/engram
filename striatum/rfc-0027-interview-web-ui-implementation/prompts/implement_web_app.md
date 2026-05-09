# Pass B1: Implement the FastAPI app + Templates + Web Tests

You are running **Pass B1** of the RFC 0027 / Spec 0027 implementation.
Pass A (render.py extraction + migration 011 + cli.py refactor + tests)
is already landed in the most recent commit. **Pass B2** runs in
parallel and owns CLI/Makefile/docs/CHANGELOG; you do NOT touch those.

# Spec

`/home/halbritt/git/engram/docs/specs/0027-interview-web-ui-spec.md` is
the contract. Read § Routes, § Templates, § Test surface,
§ Privacy and security, and § Process model carefully before editing.

# Your write scope (strictly enforced by Striatum)

Only edit / create:

- `src/engram/interview/web.py` (NEW) — FastAPI app.
- `src/engram/interview/__init__.py` — re-exports if helpful.
- `src/engram/interview/templates/` (NEW directory) — Jinja2 templates.
- `src/engram/interview/static/` (NEW directory) — vendored static assets.
- `tests/test_interview_web.py` (NEW) — TestClient route coverage.
- `pyproject.toml` — add `[serve]` optional extra and `package-data` block.
- `docs/reviews/rfc0027-interview-web-ui-implementation/PASS_B1_WEB_APP_HANDOFF.md` (handoff artifact).

DO NOT touch: `src/engram/cli.py`, `Makefile`, `docs/howto/`,
`CHANGELOG.md`, `tests/test_interview_cli.py`, the existing
`engram.interview.{render, agent, sampler, storage, errors}` modules,
or any RFC / spec / decision-log / build-phases doc.

# Deliverables

## 1. `src/engram/interview/web.py`

FastAPI application factory. Sync `def` route handlers (psycopg is
sync; async would block the event loop). All routes from spec §
Routes. Origin allowlist middleware on POST routes. Tier 1 ceiling on
`/messages/{id}`, `/messages/{id}/context`, `/q/{idx}/evidence/all`.

Required imports: `fastapi`, `uvicorn` (only at run time, in CLI), `jinja2`,
`engram.db.connect`, `engram.interview.{render, agent, sampler, storage}`.

**Critical — D044/D069 invariant:** do NOT import
`engram.consolidator.transitions`, `engram.consolidator`, or any
symbol from those modules. The implementation must pass a test that
imports `engram.interview.web` and asserts no module containing
`consolidator.transitions` is reachable.

Module structure:

```python
from __future__ import annotations
# ... imports ...

ALLOWED_ORIGINS: tuple[str, ...] = (
    "http://127.0.0.1",
    "http://localhost",
)

def _origin_check(request) -> None:
    """Raise HTTPException(403) if Origin header is set and not in ALLOWED_ORIGINS."""

def _check_tier_1(privacy_tier: int) -> None:
    """Raise HTTPException(403) if privacy_tier > 1."""

def create_app() -> FastAPI:
    app = FastAPI(title="Engram interview", docs_url=None, redoc_url=None, openapi_url=None)
    # Mount static, configure Jinja templates, register routes.
    return app

app = create_app()
```

Routes per spec (verb / path / behavior):
- `GET  /` → render `index.html` with open sessions + new-session form.
- `POST /sessions` → Origin check, sample N targets, materialize order in `gold_label_session_targets`, redirect to `/sessions/{id}/q/1`. If `sampler.sample(n)` returns `[]`, render `index.html` with empty-corpus diagnostic banner; do NOT create the session.
- `GET  /sessions/{session_id}` → redirect to current target's `q/{idx}` if any unanswered remain, else redirect to `/`.
- `GET  /sessions/{session_id}/q/{idx}` → render `question.html`. URL `idx` is 1-indexed; table `idx` is 0-indexed (translate `url_idx - 1`).
- `POST /sessions/{session_id}/q/{idx}/verdict` → Origin check, `agent.record_verdict(...)`. Single-click commit for `true`/`skip` (rationale=NULL); two-click for `false`/`stale`/`unsupported`/`unsure` (rationale required, empty allowed for `unsure`). On commit: `HX-Redirect` to next idx, or `/sessions/{id}/complete` if `idx == n`.
- `GET  /sessions/{session_id}/messages/{message_id}` → Tier 1 check, render evidence excerpt fragment.
- `GET  /sessions/{session_id}/messages/{message_id}/context?before=N&after=M` → Tier 1 check, hard cap `N+M <= 20`, max-tier-carry across all rows; 403 if any returned row has tier > 1.
- `GET  /sessions/{session_id}/q/{idx}/evidence/all` → Tier 1 check, render all evidence rows.
- `POST /sessions/{session_id}/save-and-quit` → Origin check, no verdict commit, render banner with resume command, redirect to `/`.
- `POST /sessions/{session_id}/complete` → Origin check, `mark_session_completed`, redirect to `/`.
- `POST /sessions/{session_id}/abandon` → Origin check, `mark_session_completed(operator_note='abandoned via web')`, redirect to `/`.

Trigger error handling: if `record_verdict` raises `GoldLabelStorageError` or `GoldLabelVerdictError`, render the same question with an error banner; do NOT 500.

## 2. Templates at `src/engram/interview/templates/`

- `base.html` — page chrome, single inline `<style>` block, `<script src="/static/htmx.min.js">` (vendored, NOT a CDN), inline `<script>` keyboard dispatcher (bare-key + accesskey fallback; ignore when `<input>`/`<textarea>` focused), `aria-live="polite"` live region, `htmx:afterSwap` focus listener moving focus to `<h2 tabindex="-1">`, hidden help-modal markup bound to `?` and dismissed with `Esc`.
- `index.html` — extends base; lists open sessions with progress (`K/N answered, opened Xh ago`) and per-row `[Abandon]` link; new-session form with `n` and `seed` only (no superseded/cooldown checkboxes); empty-corpus diagnostic banner slot; page title `Engram interview — open sessions`.
- `question.html` — extends base; per-target header line, summary line with predicate-doc append, evidence-dates / valid-from line, evidence excerpts section (3-row cap with "show all N rows" link to `/q/{idx}/evidence/all`), evidence-context panel (initially empty; populated by htmx swap from `/messages/{id}/context`), question line, six verdict buttons in row `[true] [false] [stale] [unsupported] [unsure] [skip]` (with `aria-label` carrying gloss verbatim from `gold_label_verdict_vocabulary` and `<sup>` accesskey letter on each face), rationale textarea (initially `display:none`; revealed by htmx swap on `false`/`stale`/`unsupported`/`unsure` click), Save-and-quit button, status-line "K/N answered — closing this tab is safe", inline strata strip footer (one `SELECT stability_class, count(*) FROM gold_labels WHERE session_id = ? GROUP BY 1`).
- `_evidence_excerpt.html` — partial: one evidence row.
- `_strata_strip.html` — partial: inline strata footer.

Keyboard binding letters per spec § Verdict keyboard shortcuts:
- `t`=true, `f`=false, `s`=stale, `n`=unsupported, `u`=unsure, `k`=skip, `?`=help, `q`=save-and-quit, `Esc`=close help.

CSS: small inline block, no external stylesheet. Use icon + underline + color (not color-alone) for verdict differentiation.

## 3. `src/engram/interview/static/htmx.min.js`

Vendored htmx (the user has no internet during install; D020). Do NOT
download from a CDN. Either:

- Use the python `htmx` package contents if pip-available, OR
- Write a stub minimal-htmx that supports `hx-post`, `hx-get`, `hx-target`, `hx-swap`, `hx-push-url` for the route shapes you use; document this clearly in a comment, OR
- If neither is feasible, document in the handoff that you couldn't ship the vendored bundle and need the user to drop in a copy.

Recommended: ship a small (~12KB) bundled htmx that you author from
the public spec — but only if you can do so accurately. Otherwise,
document the gap in the handoff. Do NOT add a CDN reference.

**Pragmatic fallback:** if you cannot produce a working htmx bundle in
this session, write `static/README.md` documenting that the operator
must drop `htmx.min.js` here from a trusted source, and ship the rest of
the implementation. The tests will skip the `htmx_loaded_from_static`
test if the file is empty/missing and report that gap.

## 4. `pyproject.toml`

Add:

```toml
[project.optional-dependencies]
serve = [
    "fastapi>=0.110,<1",
    "uvicorn>=0.30,<1",
    "jinja2>=3.1,<4",
]
```

Add `engram[serve]` to existing `dev` extra so `pytest` etc. can import the web module.

Add:

```toml
[tool.setuptools.package-data]
"engram.interview" = ["templates/*.html", "templates/*", "static/*"]
```

Read the existing pyproject.toml to find the right insertion points
without disturbing existing structure.

## 5. `tests/test_interview_web.py`

Use FastAPI `TestClient` plus the existing real-DB `conn` fixture from
`tests/conftest.py`. Cover all tests from spec § Test surface (web
routes section). At minimum:

- `test_index_renders_no_open_sessions`
- `test_index_renders_open_sessions_with_progress`
- `test_post_sessions_redirects_to_q1`
- `test_post_sessions_empty_corpus_renders_diagnostic`
- `test_get_question_renders`
- `test_post_verdict_true_single_click_commit`
- `test_post_verdict_skip_single_click_commit`
- `test_post_verdict_false_two_click_flow`
- `test_post_verdict_trigger_rejection_renders_banner`
- `test_post_verdict_404_unknown_session`
- `test_post_verdict_404_out_of_range_idx`
- `test_post_verdict_422_unknown_verdict`
- `test_post_verdict_403_origin_mismatch`
- `test_post_verdict_completes_session_at_n`
- `test_get_messages_tier_1_enforced`
- `test_get_messages_context_max_tier_carry`
- `test_get_evidence_all_tier_1_enforced`
- `test_post_save_and_quit_discards_in_progress`
- `test_post_abandon_marks_completed`
- `test_consolidator_transitions_unimportable_from_web`
- `test_htmx_loaded_from_static_not_cdn` (skip if static/htmx.min.js is missing/empty; report in handoff)
- `test_aria_live_region_present`

Tests must be DETERMINISTIC and not require live LLMs. Skip cleanly when `ENGRAM_TEST_DATABASE_URL` is unset (the `conn` fixture handles this).

## 6. Handoff artifact

When done, write `docs/reviews/rfc0027-interview-web-ui-implementation/PASS_B1_WEB_APP_HANDOFF.md`:

```md
# Pass B1 — Web App Handoff
author: <byline from work packet>

Status: handoff
Date: 2026-05-09
RFC refs: RFC-0027
Decision refs: D044, D069, D080
Phase refs: PHASE-0003-FOLLOWON

## Files created
- src/engram/interview/web.py (N lines)
- ...

## Files modified
- pyproject.toml
- src/engram/interview/__init__.py (if touched)

## Verification commands run
| Command | Exit | Result |
|---------|------|--------|
| .venv/bin/python -m pytest tests/test_interview_web.py -x | 0 | N passed, M skipped |
| .venv/bin/python -c "from engram.interview.web import app; print('ok')" | 0 | ok |
| ... |

## Residual risks / known gaps
- ...

## Next steps
- Pass B2 (CLI serve subparser) is running in parallel and produces docs/reviews/rfc0027-interview-web-ui-implementation/PASS_B2_SERVE_CLI_HANDOFF.md.
- verify_web_ui job runs against both handoffs.
```

# Verification commands you must run (capture in handoff)

```sh
.venv/bin/pip install -e ".[serve]" --quiet 2>&1 | tail -2
.venv/bin/python -c "from engram.interview.web import app; print('app ok')"
.venv/bin/python -c "import engram.interview.web; import sys; mods = [m for m in sys.modules if 'consolidator.transitions' in m]; assert not mods, mods; print('D044/D069 import guard: ok')"
.venv/bin/python -m pytest tests/test_interview_web.py -x --no-header 2>&1 | tail -10
```

# Guardrails

- `from __future__ import annotations` on every Python file.
- Type hints on all signatures; no `Any` without one-line reason.
- No bare `except:`.
- No live LLM calls in tests.
- Sync `def` route handlers, not `async def`.
- Match existing trigger / function naming conventions.
- The CLI's serve subparser is Pass B2's responsibility — DO NOT add it from this pass.

Report back: files modified/created with line counts, test results, any gaps in the handoff (especially around the htmx vendoring), any blockers.