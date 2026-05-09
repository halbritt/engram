# Pass B1 — Web App Handoff
author: author-codex-gpt-5.5-002

Status: handoff
Date: 2026-05-09
RFC refs: RFC-0027
Decision refs: D044, D069, D080
Phase refs: PHASE-0003-FOLLOWON

## Summary

Pass B1 lands the FastAPI app, Jinja2 templates, vendored htmx shim,
`pyproject.toml` deltas (`[serve]` extra and `package-data` block), and the
TestClient route-coverage test suite for Spec 0027. Pass B2's CLI subparser,
Makefile target, howto entry, and CHANGELOG entry are untouched.

All 23 tests in `tests/test_interview_web.py` pass against the real-DB
`conn` fixture. The D044 / D069 import-guard invariant
(`engram.interview.web` does not transitively import
`engram.consolidator.transitions`) holds.

## Files created

| File | Lines |
|------|-------|
| `src/engram/interview/web.py` | 995 |
| `src/engram/interview/templates/base.html` | 219 |
| `src/engram/interview/templates/index.html` | 58 |
| `src/engram/interview/templates/question.html` | 147 |
| `src/engram/interview/templates/_evidence_excerpt.html` | 19 |
| `src/engram/interview/templates/_strata_strip.html` | 10 |
| `src/engram/interview/static/htmx.min.js` | 174 (vendored stub; see "htmx vendoring") |
| `tests/test_interview_web.py` | 678 |

Total: 8 files, 2300 lines.

## Files modified

| File | Lines (post) | Note |
|------|--------------|------|
| `pyproject.toml` | 76 | Added `[serve]` optional extra, added `engram[serve]` to `dev` extra, added `[tool.setuptools.package-data]` block |

`src/engram/interview/__init__.py` was deliberately not modified — the
existing `__all__` already re-exports everything `web.py` needs
(`SAMPLER_ID`, `SAMPLER_VERSION`, `GoldLabelSampler`, `SampledTarget`,
`insert_session`, `mark_session_completed`, etc.). Adding a re-export of
`engram.interview.web` would break installs that lack the optional
`[serve]` extras.

## Verification commands run

| Command | Exit | Result |
|---------|------|--------|
| `.venv/bin/pip install -e ".[serve]" --quiet` | 0 | (silent) |
| `.venv/bin/python -c "from engram.interview.web import app; print('app ok')"` | 0 | `app ok` |
| `.venv/bin/python -c "import engram.interview.web; ...assert no consolidator.transitions..."` | 0 | `D044/D069 import guard: ok` |
| `.venv/bin/python -m pytest tests/test_interview_web.py -x --no-header` | 0 | **23 passed in 26.41s** |
| `.venv/bin/python -m pytest tests/test_interview_render.py tests/test_interview_storage.py tests/test_interview_sampler.py tests/test_interview_cli.py tests/test_migrations.py` | 0 | 77 passed (no regressions in adjacent surfaces) |

Test breakdown for `tests/test_interview_web.py`:

- 23 passed
- 0 failed
- 0 skipped (real DB available at `postgresql:///engram_test`)

The `test_htmx_loaded_from_static_not_cdn` test asserts the vendored shim is
present and references `/static/htmx.min.js` (not a CDN URL); it does not
skip in this environment because `static/htmx.min.js` is non-empty.

## htmx vendoring

`src/engram/interview/static/htmx.min.js` is a small (~174 line / 5 KB)
**custom shim** authored from the public htmx attribute spec, not the
upstream htmx bundle. It supports the attributes the Engram interview UI
actually uses:

- `hx-get`, `hx-post` on `<a>`, `<button>`, and `<form>` elements;
- `hx-target` (CSS selector or `closest <selector>`);
- `hx-swap` (`innerHTML`, `outerHTML`);
- `hx-push-url="true"`;
- `HX-Redirect` response-header handling (single-click verdict commit
  flow);
- `htmx:afterSwap` event dispatch (the `base.html` dispatcher listens for
  this to update `aria-live` and move focus).

This satisfies RFC 0027 F004 (no CDN reference) and D020 (operator runs
fully offline). An operator who wants the full htmx feature set may drop
the upstream `htmx.min.js` into the same path; no code change is required
because the shim publishes the same `window.htmx` global and the
`htmx:afterSwap` event name.

The shim has not been exercised in a real browser as part of this pass —
it is verified only by static inspection (the test asserts
`/static/htmx.min.js` is served and referenced from `base.html` and that
no CDN URLs are reachable from the rendered pages). Functional
verification is left to the post-merge `verify_web_ui` job.

## Routes implemented

All routes from Spec 0027 § Routes are implemented as sync `def` handlers:

- `GET /` — open-session list and new-session form
- `POST /sessions` — Origin check, sample N targets, materialize, redirect
  to `/sessions/{id}/q/1`; empty-corpus path renders index with
  diagnostic banner and calls `mark_session_completed`
- `GET /sessions/{session_id}` — resume redirect to current target's
  `q/{idx + 1}` or `/`
- `GET /sessions/{session_id}/q/{idx}` — render `question.html`; URL
  `idx` is 1-indexed, table is 0-indexed
- `POST /sessions/{session_id}/q/{idx}/verdict` — Origin check, validate,
  `agent.record_verdict(...)`, return `HX-Redirect: /q/{idx+1}` or
  `/sessions/{id}/complete` if `idx == n`. Trigger-rejection path catches
  `GoldLabelStorageError` / `GoldLabelVerdictError`, rolls back, and
  re-renders the question with an error banner
- `GET /sessions/{session_id}/messages/{message_id}` — Tier 1 ceiling;
  renders the full evidence row
- `GET /sessions/{session_id}/messages/{message_id}/context` — Tier 1
  max-tier-carry; hard cap `before + after <= 20` (422 above)
- `GET /sessions/{session_id}/q/{idx}/evidence/all` — Tier 1 ceiling;
  renders all evidence rows
- `POST /sessions/{session_id}/save-and-quit` — Origin check, no commit,
  banner attached as URL-encoded query param on the `/` redirect
- `POST /sessions/{session_id}/complete` — Origin check, mark completed,
  redirect
- `POST /sessions/{session_id}/abandon` — Origin check, mark completed
  with `operator_note='abandoned via web'`, redirect
- `GET /sessions/{session_id}/complete` — small extension beyond strict
  spec: lets htmx's `HX-Redirect` from the verdict POST land on a real
  URL when the operator clicks through. Marks the session completed and
  redirects to `/`

`mark_session_completed` does not accept an `operator_note` kwarg (storage.py
is out of write scope for Pass B1). The abandon route therefore issues an
inline `UPDATE gold_label_sessions SET completed_at = ..., operator_note =
%s` so the spec semantics hold without modifying storage.py.

## Origin-allowlist behavior

- Implemented as a FastAPI `Depends` dependency named `_get_origin_check`
  attached only to POST routes. GETs are unguarded.
- Accepts requests with no `Origin` header (TestClient and curl both
  default to that), but rejects mismatched `Origin` with 403 +
  `{"error": "origin_mismatch", "expected": [...]}`.
- `Sec-Fetch-Site`, when present, must be `same-origin`.
- `ALLOWED_ORIGIN_HOSTS = ('127.0.0.1', 'localhost')`. Any port matches.

## Tier 1 ceiling

- Defined as `TIER_CEILING = 1` constant; the env var
  `ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX` is reserved per spec but
  unimplemented in v1.
- `/messages/{id}`: rejects `privacy_tier > 1` with the structured
  envelope.
- `/messages/{id}/context`: max-tier carry across all returned rows; any
  row at tier > 1 forces a 403 for the entire response.
- `/q/{idx}/evidence/all`: enforces tier 1 across every cited message
  before rendering.

## Templates

- `base.html` carries the inline `<style>` block, the
  `<script src="/static/htmx.min.js" defer></script>` reference, the
  `<div id="live-region" aria-live="polite" class="visually-hidden">`,
  the inline keyboard dispatcher (bare-key + accesskey fallback,
  ignores INPUT/TEXTAREA focus, `?`/Esc help-modal handling), and the
  hidden help modal whose verdict-glosses table is populated from
  `gold_label_verdict_vocabulary` at template-render time.
- `question.html` carries the version-triple line in the page header
  (Spec 0027 § Risks "frozen at session creation"), the six verdict
  buttons in the spec-mandated order with `aria-label` from the
  vocabulary table and `<sup>` accesskey letters, the rationale
  textarea (initially `display:none`; revealed by an inline two-click
  flow handler that does NOT round-trip a `rationale-form` GET), the
  Save-and-quit form, the status line carrying the `data-live-status`
  attribute the dispatcher reads on swap, and the inline strata strip.
- `index.html` lists open sessions with progress + per-row Abandon
  form; the new-session form has only `n` and `seed` fields per spec
  (no superseded / cooldown checkboxes).
- `_evidence_excerpt.html` and `_strata_strip.html` partials match the
  spec.

Verdict differentiation uses icon + underline pattern + colour to
satisfy WCAG 1.4.1 (no colour-alone).

## Known gaps / residual risks

- **htmx shim is not the upstream bundle.** A small custom shim
  authored from the spec ships in `static/htmx.min.js`. It covers all
  the attributes the templates use, but is not a drop-in for arbitrary
  htmx examples that rely on more obscure features. Operators who want
  the full htmx surface can replace the file with the upstream
  `htmx.min.js` and the rest of the implementation continues to work
  unchanged.
- **`htmx:afterSwap` not exercised in a real browser.** The
  `aria-live` region announcement and focus management are wired
  client-side in `base.html` and are tested only by checking the
  rendered HTML for `aria-live="polite"`. A VoiceOver / NVDA / Orca
  smoke test is recommended before promoting beyond Tier 0.
- **Migration 011 'frozen at session creation' semantics.** The
  question page header now displays the version triple
  (`extraction=...`, `consolidation=...`, `profile=...`) so the operator
  can tell whether the session is bound to an old extraction / belief
  prompt. The mitigation in Spec 0027 § Risks is satisfied; no extra
  work needed in this pass.
- **The version triple shown in the header on `q/{idx}/verdict`
  re-renders (trigger-rejection path) is the same triple the original
  GET rendered.** This is correct (it carries the session-creation
  triple), but the test does not pin the rendered string — it asserts
  only that the error banner appears.
- **Connection lifecycle in tests differs from production.** In
  production, each request opens its own connection via
  `engram.db.connect()`. The TestClient fixture overrides `_get_conn`
  so all routes share one connection with the test body, which is the
  only way to make the test see committed rows without a second
  connection. Production routes still get a fresh per-request
  connection.

## No blockers from Pass B2

I did not need to import anything from `cli.py`. The web app stands on
the existing `engram.interview.{render, agent, sampler, storage}`
modules plus `engram.db.connect`. Pass B2's CLI subparser and
`run_phase3_interview_serve` driver own the process boundary; my code
runs cleanly under `pytest` without needing the CLI to exist.

The handoff at
`docs/reviews/rfc0027-interview-web-ui-implementation/PASS_B2_SERVE_CLI_HANDOFF.md`
already exists; the verify_web_ui job runs against both handoffs.

## Next steps

- The `verify_web_ui` job should run both handoffs end-to-end: spawn
  `engram phase3 interview serve` (Pass B2's driver) on a free port and
  curl the routes covered here.
- A real-browser smoke test against the vendored shim (or against an
  operator-supplied upstream `htmx.min.js`) should be added to the
  manual QA pass before Tier 0 → Tier 1 promotion.
- v1.1 may add per-form CSRF tokens (Spec 0027 § Privacy and security
  carries the deferral with a documented trigger: any new mutating
  route added after v1).

## Import-guard test result

```
$ .venv/bin/python -c "import engram.interview.web; import sys; \
  mods=[m for m in sys.modules if 'consolidator.transitions' in m]; \
  assert not mods, mods; print('D044/D069 import guard: ok')"
D044/D069 import guard: ok
```

The pytest case
`tests/test_interview_web.py::test_consolidator_transitions_unimportable_from_web`
also passes; it iterates every public + private symbol in
`engram.interview.web` and asserts none of them resolves to anything in
`engram.consolidator.transitions`.
