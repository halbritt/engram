# Implement RFC 0027 / Spec 0027 Interview Web UI

Implement the contract at `docs/specs/0027-interview-web-ui-spec.md`.
Read the spec first; it pins routes, templates, render API, migration
SQL, dependencies, tests, keyboard bindings, privacy posture, process
model, and acceptance criteria.

## Context

- Spec: `docs/specs/0027-interview-web-ui-spec.md` (~1230 lines).
- Source RFC: `docs/rfcs/0027-interview-web-ui.md` (status `promoted`,
  references the spec).
- Synthesis: `docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_SYNTHESIS.md`
  (D080).
- Existing helpers: `src/engram/interview/{agent.py, sampler.py,
  storage.py}` — reuse, don't duplicate.
- Existing CLI loop: `src/engram/cli.py` lines 1700–1860 (interactive
  interview start). The render-helper extraction targets these lines.
- Schema baseline: `migrations/010_gold_labels.sql`.

## What to build

Follow the spec's § Implementation sequencing as a guide; you may
re-order for dependency reasons but the spec contract takes
precedence. Key deliverables:

1. **`migrations/011_gold_label_session_targets.sql`** per spec §
   Migration 011, including `fn_gold_label_session_targets_append_only`
   trigger.
2. **`src/engram/interview/render.py`** with the full extraction surface
   per spec § render.py API. Extract verdict-vocabulary constants,
   evidence-layout caps, and rendering helpers from `cli.py`. CLI
   imports these names rather than defining them locally.
3. **Refactor `src/engram/cli.py`** to import the extracted symbols
   from `render.py`. Add golden-output tests pinning current CLI
   rendering so the extraction is verified no-behavior-change.
4. **Update `run_phase3_interview_start`** to also write
   `gold_label_session_targets` rows so CLI-started sessions are
   web-resumable. Update `tests/test_interview_cli.py` to expect the
   materialized rows.
5. **`src/engram/interview/web.py`** — FastAPI app with all routes per
   spec § Routes. Origin-allowlist middleware. Tier 1 enforcement.
   D044/D069 import guard.
6. **`src/engram/interview/templates/`** — `base.html`, `index.html`,
   `question.html`, `_evidence_excerpt.html`, `_strata_strip.html`
   per spec § Templates. Inline CSS in `base.html`. Vendored htmx
   loaded via `<script src="/static/htmx.min.js">`. `aria-live`,
   focus management, keyboard dispatcher.
7. **`src/engram/interview/static/htmx.min.js`** — vendored copy.
   Download once and commit; do NOT reference a CDN.
8. **CLI `engram phase3 interview serve`** subparser + driver in
   `src/engram/cli.py`. Localhost-only with exit 8 on non-loopback;
   no `--allow-non-loopback` flag in v1. Actionable
   `pip install engram[serve]` error if FastAPI/Uvicorn/Jinja2 imports
   fail.
9. **`Makefile`** — `phase3-interview-serve` target (`HOST=`, `PORT=`).
10. **`pyproject.toml`** — `[project.optional-dependencies] serve`
    extra; `dev` extra grows `"engram[serve]"`;
    `[tool.setuptools.package-data]` block for templates and static.
11. **`tests/test_interview_web.py`** — full route coverage per spec §
    Test surface. Use FastAPI `TestClient` + the existing real-DB
    `conn` fixture from `tests/conftest.py`.
12. **`tests/test_interview_render.py`** — golden-output tests for
    every render helper (header, summary, evidence-dates,
    evidence-excerpts, pick_question with explicit UTC `now`).
13. **`tests/test_migrations.py`** — extend with three migration 011
    tests (append-only trigger, version-triple CHECK, PK uniqueness).
14. **`docs/howto/gold-set-interview.md`** — add a "Web UI" section
    (cold-start, port, what's wired, what's CLI-only).
15. **`CHANGELOG.md`** — entry under `## [Unreleased]`.

## Out of scope

- Coverage dashboard route, history-from-UI, export-from-UI,
  active-learning toggle UI — all CLI-only in v1 (spec § Out of
  scope).
- Per-form CSRF tokens — deferred to v1.1; Origin allowlist is the v1
  enforcement.
- `--allow-non-loopback` — no escape clause in v1.
- `ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX` — Tier 1 hard-coded; env var
  reserved.

## Implementation discipline

- `from __future__ import annotations` on every Python file.
- Type hints on all signatures.
- No `Any` without a one-line reason.
- No bare `except:`.
- No live LLM calls in tests.
- Sync `def` route handlers + `uvicorn --workers 1`.
- Match existing trigger naming: `fn_<table>_<purpose>()`.
- `gen_random_uuid()` (pgcrypto already enabled in migration 001).

## Handoff artifact

When done, write
`docs/reviews/rfc0027-interview-web-ui-implementation/IMPLEMENTATION_HANDOFF.md`
with the work-packet author byline as the second line, a summary of
files changed, the verification commands run and their outcomes, and
any residual gaps. Run these at minimum:

- `make check-refs 2>&1 | tail -3`
- `.venv/bin/python -m pytest tests/test_interview_render.py tests/test_interview_cli.py -x` (golden-output + CLI regression)
- `.venv/bin/python -m pytest tests/test_interview_web.py -x` (web routes)
- `.venv/bin/python -m pytest tests/test_migrations.py -x` (migration 011)
- `.venv/bin/python -c "from engram.interview.web import app; print('ok')"` (import smoke)
- `.venv/bin/engram phase3 interview serve --help` (CLI subparser registered)
- A web import-graph test (TestClient or static): assert
  `engram.consolidator.transitions` is unreachable from
  `engram.interview.web`.

Stay inside the declared write scope. Do not edit
`docs/specs/0027-interview-web-ui-spec.md` (the spec is the contract);
do not edit `docs/rfcs/0027-interview-web-ui.md`,
`BUILD_PHASES.md`, `DECISION_LOG.md`, or `HUMAN_REQUIREMENTS.md`.
