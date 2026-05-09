# RFC 0027 Web UI Implementation — Verification Report
author: reviewer-codex-gpt-5.5-001

Status: verification
Date: 2026-05-09
Spec: spec-0027
RFC refs: RFC-0027
Decision refs: D080, D044, D069
Phase refs: PHASE-0003-FOLLOWON

## Scope

Verify integration of Pass A (foundation: render.py extraction, migration 011,
cli.py refactor — already committed) with parallel-built Pass B1 (FastAPI
`web.py`, templates, htmx shim, `tests/test_interview_web.py`, `pyproject`
serve extras + package-data) and Pass B2 (cli.py `serve` subparser, Makefile
target, howto Web UI section, CHANGELOG, `tests/test_interview_cli.py`)
against the spec contract in `docs/specs/0027-interview-web-ui-spec.md`.

## Commands run

| # | Command | Exit | Result |
|---|---------|------|--------|
| 1 | `git status --short --branch` | 0 | branch `engram/rfc0027-interview-web-ui-implementation`; expected modifications + new files (web.py, templates/, static/, tests/test_interview_web.py); no stray edits outside contract |
| 2 | `.venv/bin/pip install -e ".[serve]" --quiet` | 0 | clean install of FastAPI/Uvicorn/Jinja2/python-multipart |
| 3 | `make check-refs` | 0 | `Summary: 0 error(s), 5 warning(s), 162 check(s) ok` (warnings pre-exist; not RFC-0027) |
| 4 | `python -c "from engram.interview.web import app; print('app ok')"` | 0 | `app ok` |
| 5 | D044/D069 import-graph guard probe | 0 | `D044/D069 import guard: ok` (no `consolidator.transitions` reachable from `engram.interview.web`) |
| 6 | `pytest tests/test_interview_render.py tests/test_interview_cli.py tests/test_interview_web.py tests/test_interview_storage.py tests/test_interview_sampler.py tests/test_migrations.py` | 0 | 65 passed, 35 skipped (web/storage/migrations skipped due to no `ENGRAM_TEST_DATABASE_URL`) |
| 7 | `engram phase3 interview --help` | 0 | `serve` subcommand listed alongside start/resume/history/export/list-sessions/coverage/enable-active-learning |
| 8 | `engram phase3 interview serve --help` | 0 | `--host HOST`, `--port PORT` advertised; no `--allow-non-loopback` |
| 9 | `engram phase3 interview serve --host 0.0.0.0` | 8 | stderr: `phase3 interview serve: refusing non-loopback host (--host=0.0.0.0); v1 is loopback-only`; non-zero exit (8) confirms F005 enforcement |
| 10 | `ls migrations/011_gold_label_session_targets.sql src/engram/interview/{render.py,web.py}` | 0 | all present |
| 11 | `ls src/engram/interview/{templates,static}/` | 0 | base.html, index.html, question.html, _evidence_excerpt.html, _strata_strip.html, htmx.min.js |
| 12 | `grep -c "phase3-interview-serve" Makefile` | 0 | 2 occurrences (`.PHONY` line + target body) |
| 13 | `grep -E "\[project.optional-dependencies\]\|^serve = " pyproject.toml` | 0 | `[project.optional-dependencies]` present; `serve = [fastapi>=0.110,<1, uvicorn>=0.30,<1, jinja2>=3.1,<4, python-multipart>=0.0.9,<1]` |
| 14 | `grep package-data pyproject.toml` | 0 | `[tool.setuptools.package-data]` → `"engram.interview" = ["templates/*.html", "templates/*", "static/*"]` |
| 15 | `make -n phase3-interview-serve` | 0 | dry-run resolves to `python -m engram.cli phase3 interview serve` with optional `HOST`/`PORT` env passthrough |
| 16 | `grep allow-non-loopback src/engram/cli.py` | 0 | only a comment confirming the flag is intentionally absent (line 2062) — no flag, no parser entry |
| 17 | `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test pytest tests/test_interview_web.py tests/test_interview_storage.py tests/test_migrations.py` | 0 | **36 passed in 38.10s** — full DB-backed run; covers Origin allowlist (line 464), tier-1 ceiling (lines 511, 582, 531, 563), D044/D069 import guard (line 634), htmx-not-CDN (line 652), aria-live (line 674), trigger rejection (line 375), session completion (line 478), 404/422 envelopes (lines 428–450) |

## Audit checklist (per spec § Acceptance criteria)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | `engram phase3 interview serve` boots (help works) | PASS | cmd 7, 8 |
| 2 | `engram phase3 interview serve --host 0.0.0.0` exits non-zero (loopback-only) | PASS | cmd 9 (exit=8); cli.py:2061–2102 (`_SERVE_LOOPBACK_HOSTS` frozenset, refusal before FastAPI import) |
| 3 | No `--allow-non-loopback` flag | PASS | cmd 16 — only a comment at cli.py:2062 noting the flag is intentionally absent |
| 4 | `migrations/011_gold_label_session_targets.sql` present | PASS | cmd 10; trigger `gold_label_session_targets_00_append_only` defined at lines 48–59 |
| 5 | `render.py`, `web.py`, `__init__.py` importable | PASS | cmd 4 + `python -c "import engram.interview"` ok |
| 6 | All five templates present | PASS | cmd 11 |
| 7 | `static/htmx.min.js` exists, non-trivial | PASS (with finding V001) | 5717 bytes / 174 lines; header declares `engram-htmx-stub.v1` — a hand-authored shim covering only hx-get/hx-post/hx-target/hx-swap/hx-push-url. Spec § F004 explicitly contemplates a vendored offline shim, so this satisfies the contract |
| 8 | `[project.optional-dependencies] serve = [...]` with FastAPI/Uvicorn/Jinja2 | PASS | cmd 13; also includes `python-multipart` (required by FastAPI form parsing) |
| 9 | `[tool.setuptools.package-data]` block for templates and static | PASS | cmd 14 |
| 10 | Makefile `phase3-interview-serve` target listed in `.PHONY` | PASS | cmd 12; Makefile:11 (.PHONY) and Makefile:168 (target body) |
| 11 | D044/D069 import-graph guard test | PASS | cmd 5 (runtime probe) + `tests/test_interview_web.py:634` `test_consolidator_transitions_unimportable_from_web` (passed under DB run) |
| 12 | Origin allowlist test (POST non-localhost Origin → 403) | PASS | `tests/test_interview_web.py:464` `test_post_verdict_403_origin_mismatch` (passed under DB run); web.py:140–174 raises 403 with structured envelope |
| 13 | Tier-1 ceiling test | PASS | `tests/test_interview_web.py:511,531,563,582` four tier-ceiling tests (all passed); web.py:182–192 `_check_tier_1` with `TIER_CEILING` |
| 14 | CLI test for `--host 0.0.0.0` rejection | PASS | `tests/test_interview_cli.py:439` (test invokes cli.main, asserts non-zero + stderr mention of `0.0.0.0`); passed in cmd 6 |
| 15 | CLI test for missing FastAPI deps (pip install hint) | PASS | `tests/test_interview_cli.py:446` `test_phase3_interview_serve_pip_install_hint_when_imports_fail` (passed in cmd 6) |
| 16 | `make check-refs` clean (0 errors) | PASS | cmd 3: `0 error(s)`; the 5 warnings are pre-existing and unrelated to RFC-0027 |

## Findings

### V001 — `htmx.min.js` is a hand-authored shim, not upstream htmx
Severity: minor (informational; spec-compliant)
Source: `src/engram/interview/static/htmx.min.js:1–15`
Rationale: The vendored asset is `engram-htmx-stub.v1`, a 174-line hand-rolled
shim that implements only the htmx attributes the UI uses (hx-get, hx-post,
hx-target, hx-swap, hx-push-url, HX-Redirect, htmx:afterSwap). The header
comment is explicit: "This is NOT a full htmx implementation. It is
intentionally vendored so the operator can run the UI fully offline (D020)
without a CDN reference (RFC 0027 F004). Drop in upstream htmx.min.js to gain
the full feature set." Spec § F004 sanctions a vendored asset; nothing in the
spec mandates the upstream artifact, and the `test_htmx_loaded_from_static_not_cdn`
test at `tests/test_interview_web.py:652` enforces only the static-vs-CDN
invariant. Logged so future operators are not surprised that swapping in a
new htmx attribute will require either editing the shim or replacing it with
upstream htmx.

### V002 — `make check-refs` carries 5 pre-existing warnings
Severity: nit
Source: cmd 3 output
Rationale: Warnings reference D034#request-profile, REVIEW-0003#context-overflow,
PHASE-0002#generation-activation, D042#request-profile, and a duplicate
prompt ordinal P024. None of these were introduced by RFC-0027 (they predate
this branch). Spec acceptance criterion only requires `0 error(s)`, which is
met. No action required for this implementation.

### V003 — Web/storage/migrations tests skip silently without `ENGRAM_TEST_DATABASE_URL`
Severity: nit
Source: cmd 6 (35 skipped) vs cmd 17 (36 passed once env set)
Rationale: Without the DB URL the suite reports `passed` for the 65 non-DB
tests but skips the 36 DB-backed cases. The skip behavior is correct
(deterministic, no network, matches the project Python standard) but a CI
runner that does not provision PostgreSQL would never exercise the
substantive web invariants. Recommend the CI matrix surface a job that
sets `ENGRAM_TEST_DATABASE_URL` (existing convention; not a regression
introduced here).

## Residual risks

- The htmx shim ships only the attribute subset that the current templates
  use; future templates that introduce a new `hx-*` attribute will silently
  no-op until the shim is extended or upstream htmx is dropped in. F004 is
  satisfied today but ongoing maintenance has a small footgun.
- No automated test asserts the `Cache-Control: private, no-store` header on
  message responses (Spec § 6 lists it as a requirement). The audit
  checklist in this verify task did not list it, but it is worth flagging
  for a follow-on review.
- The Makefile `phase3-interview-serve` target shells out to `python -m
  engram.cli`, which works locally but does not exercise the
  `[serve]`-extras install path — operators who used `make install` (which
  installs `[dev]`, which transitively pulls `engram[serve]`) get serve
  deps; operators using a bare wheel install will need `pip install
  engram[serve]` separately. The test at `tests/test_interview_cli.py:446`
  catches this case at runtime with a friendly hint.

## Summary

All 16 spec acceptance criteria pass. The Pass A foundation, Pass B1 web
app, and Pass B2 CLI driver compose cleanly: the CLI refuses non-loopback
binds before importing FastAPI (defense-in-depth), the web app enforces
Origin allowlist + tier-1 ceiling at the request layer, the import-graph
guard keeps `engram.interview.web` free of `engram.consolidator.transitions`
(D044/D069), and the pyproject `package-data` declaration ensures templates
+ static assets ship with the wheel. Three minor findings logged
(htmx shim is a custom subset, pre-existing check-refs warnings, DB tests
skip without env var); none are blocking.

verdict: accept_with_findings
