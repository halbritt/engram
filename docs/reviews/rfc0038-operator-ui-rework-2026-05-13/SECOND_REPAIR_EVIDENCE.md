author: operator [self-declared: rfc0038-second-repair-evidence]

# RFC 0038 Second Repair Evidence

Date: 2026-05-13
Completed at: 2026-05-13T23:42:39Z
Lane: codex_review
Job: second_repair_evidence
Branch: `engram/rfc0038-ui-rework`
Verdict: pass

## Scope

Focused evidence pass for the RFC 0038 second repair. This pass verified that
AC001 and AC002 from `REVIEW_accept_findings_correctness_codex.md` are closed,
and that the prior accept-with-findings follow-ups remain green.

No implementation files were edited. This pass wrote only this evidence
artifact. No dependency install and no network access were used.

## Summary

The second repair evidence is green.

- DB-backed interview plus bench route suite: `85 passed in 58.49s`.
- Shared substrate plus interview-render tests: `64 passed in 0.24s`.
- Bench plus shared substrate focused suite: `49 passed in 1.44s`.
- Explicit generated-route probe passed: bench and interview `/docs`, `/redoc`,
  and `/openapi.json` all returned 404 with no CDN markers.
- Template/static no-CDN scan passed across 27 shared/interview/bench resources.
- Focused `py_compile`, Ruff check, Ruff format check, and `git diff --check`
  passed.
- `make check-refs` passed with `0 error(s), 5 warning(s), 181 check(s) ok`.
  The warnings match the existing reference-warning pattern from prior
  evidence.

The active virtualenv still lacks `httpx`; route checks used the already-local
user-site dependency path at `/home/halbritt/.local/lib/python3.12/site-packages`.

## Environment

| Check | Result |
| --- | --- |
| `.venv/bin/python -V` | `Python 3.12.3` |
| `.venv/bin/python -m pytest --version` | `pytest 8.4.2` |
| `.venv/bin/python -c "import httpx; print(httpx.__version__)"` | Failed: `ModuleNotFoundError: No module named 'httpx'` |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -c "import httpx; print(httpx.__version__)"` | Pass: `0.28.1` |
| `psql postgresql:///engram_test -c "SELECT 1"` | Pass |

## Commands And Results

| Command | Result |
| --- | --- |
| `striatum ack --session-id sess_f1b54bdaee914f8c9d30d5fc736bb61f --message-id msg_4d6e0371d41849a092108e9829690f8e --lease-id lease_98630c9247f0421e9947b5506b12d455` | Pass. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py tests/test_bench_review.py` | Pass: `85 passed in 58.49s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_web_ui_shared.py tests/test_interview_render.py` | Pass: `64 passed in 0.24s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_bench_review.py tests/test_web_ui_shared.py` | Pass: `49 passed in 1.44s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python - <<'PY' ... generated route probe ... PY` | Pass: bench `/docs`, `/redoc`, `/openapi.json` all returned 404 with `markers=[]`; interview `/docs`, `/redoc`, `/openapi.json` all returned 404 with `markers=[]`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages .venv/bin/python - <<'PY' ... no-CDN template/static scan ... PY` | Pass: `checked=27; external_asset_markers=0`. |
| `.venv/bin/python -m py_compile src/engram/web/__init__.py src/engram/web/assets.py src/engram/web/chrome.py src/engram/web/origin.py src/engram/web/status.py src/engram/web/tier.py src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass. |
| `.venv/bin/python -m ruff check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass: `All checks passed!`. |
| `.venv/bin/python -m ruff format --check src/engram/web src/engram/interview/web.py src/engram/bench_review/web.py tests/test_web_ui_shared.py tests/test_interview_web.py tests/test_bench_review.py` | Pass: `11 files already formatted`. |
| `git diff --check` | Pass. |
| `make check-refs` | Pass: `0 error(s), 5 warning(s), 181 check(s) ok`. |
| `striatum heartbeat --session-id sess_f1b54bdaee914f8c9d30d5fc736bb61f --lease-id lease_98630c9247f0421e9947b5506b12d455` | Pass. |

## AC Status

### AC001: Bench generated docs/openapi routes

Status: closed.

Evidence:

- `src/engram/bench_review/web.py` constructs the bench app with
  `docs_url=None`, `redoc_url=None`, and `openapi_url=None`.
- `tests/test_bench_review.py::test_create_app_disables_generated_docs_and_openapi_routes`
  is included in the green bench route suite.
- The explicit generated-route probe confirmed bench `/docs`, `/redoc`, and
  `/openapi.json` return 404 and contain no `https://`, `cdn.jsdelivr.net`,
  `redoc`, or `swagger-ui` markers.

### AC002: Interview IPv6 loopback same-origin POSTs

Status: closed.

Evidence:

- `src/engram/interview/web.py` keeps the default D081 allowlist as
  `("127.0.0.1", "localhost")`, but appends `::1` for an app instance created
  with a validated IPv6 loopback bind.
- The green route suite includes positive coverage for
  `create_app(host="::1")` accepting
  `Host: [::1]:8765`, `Origin: http://[::1]:8765`, and
  `Sec-Fetch-Site: same-origin` on a verdict POST.
- The green route suite includes negative coverage proving the default
  IPv4-bound app still rejects the IPv6 Origin, mismatched ports, missing
  Origin headers, non-same-origin `Sec-Fetch-Site`, and untrusted origins.

## Prior Follow-Up Preservation

- FU101 interview-to-bench tab, CS001 shared origin/tier helper delegation,
  CS002 truthful bind-address footer, FU103 shared status banners, FU104
  duplicate copy-command handler removal, and FU105 shared surface-tab cleanup
  remain covered by the green interview, bench, shared, and render suites.
- Bench FU102 shared keyboard dispatcher plus bench-only queue-filter behavior
  remains covered by the green bench/shared suite.
- Local-first/no-CDN posture is covered by the resource scan and explicit
  generated-route probe. No hosted assets, CDN markers, telemetry, dependency
  installs, or network use were introduced by this evidence pass.

## Not Run

- `make test` was not run; this packet requested focused second-repair
  evidence.
- Browser/Playwright responsive screenshot checks were not run.
- `pytest-socket` or an OS-level egress-deny wrapper was not run.
- No dependency installation was attempted because network use is forbidden for
  this job.

## Residual Risk

- The active `.venv` still needs a local/offline refresh to install the
  repository-declared `httpx` dependency. Until then, route tests require the
  already-local user-site `PYTHONPATH` workaround.
- This is focused evidence, not a full-suite or browser-layout pass.
- Corrected-review polish items outside the accept-findings and second-repair
  scopes remain outside this evidence scope, including bench index CTA
  placement, metric-parity polish, interview metadata density, next-in-queue
  affordance, commit-vs-rationale visual cue, and trivial save-and-quit banner
  polish.
