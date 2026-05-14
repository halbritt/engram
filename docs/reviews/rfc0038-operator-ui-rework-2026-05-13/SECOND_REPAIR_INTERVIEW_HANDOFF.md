author: operator [self-declared: rfc0038-second-repair-interview]

# RFC 0038 Second Repair Interview Handoff

Date: 2026-05-13
Lane: codex_interview
Job: repair_interview_ipv6_origin
Verdict: pass

## Scope

Closed AC002 from
`REVIEW_accept_findings_correctness_codex.md`: interview mutating POST routes
now accept same-origin browser requests from `http://[::1]:<port>` when the
interview app is configured with the IPv6 loopback bind host `::1`.

The patch stays inside the allowed source/test files plus this handoff
artifact. No network access, dependency installation, bench/shared-surface
edits, canonical-doc edits, migration edits, `CHANGELOG.md`, or production-data
writes were used.

## Source Changes

- `src/engram/interview/web.py`
  - Adds `_allowed_origin_hosts_for_bind(host)` so an app created with a
    validated loopback bind host derives a process-local Origin host tuple.
  - Stores that tuple on `app.state.engram_allowed_origin_hosts`.
  - Keeps `_origin_check` delegated to `engram.web.origin.require_origin`, but
    passes the app-configured host tuple for requests when available.
  - Appends `::1` only for a configured IPv6 loopback bind; the default
    module-level D081 resolver remains `("127.0.0.1", "localhost")` plus any
    explicit `ENGRAM_INTERVIEW_ALLOWED_ORIGINS` entries.
- `tests/test_interview_web.py`
  - Makes the local `_origin_headers` test helper bracket IPv6 literals.
  - Adds a positive regression for `create_app(host="::1")` accepting
    `Host: [::1]:8765`, `Origin: http://[::1]:8765`, and
    `Sec-Fetch-Site: same-origin` on a verdict POST.
  - Adds a negative regression proving the default IPv4-bound app still
    rejects that IPv6 Origin.
  - Adds a focused helper test proving the IPv6 bind path includes `::1`
    without changing the default allowlist.

## Verification

Commands run:

- `striatum ack --session-id sess_e2790772eb1a4bd4962c67cb01aee5d5 --message-id msg_af80a4811d0349dcbfc9426c96083519 --lease-id lease_a354aade69a945f0a6622d2d478904f3`
  - Pass.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py::test_post_verdict_accepts_ipv6_loopback_origin_for_ipv6_bind tests/test_interview_web.py::test_post_verdict_rejects_ipv6_origin_when_not_ipv6_bound tests/test_interview_web.py::test_allowed_origin_hosts_for_ipv6_bind_adds_ipv6_loopback`
  - Pass: `3 passed in 2.47s`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py::test_post_verdict_403_origin_mismatch tests/test_interview_web.py::test_post_verdict_requires_origin_header tests/test_interview_web.py::test_post_verdict_requires_same_origin_sec_fetch tests/test_interview_web.py::test_post_verdict_rejects_allowed_host_on_wrong_port tests/test_interview_web.py::test_origin_mismatch_blocks_all_post_routes tests/test_interview_web.py::test_origin_check_delegates_to_shared_helper tests/test_interview_web.py::test_allowed_origin_hosts_default_is_loopback_only tests/test_interview_web.py::test_allowed_origin_hosts_env_var_extends_default`
  - Pass: `8 passed in 5.57s`.
- `.venv/bin/python -m py_compile src/engram/interview/web.py tests/test_interview_web.py`
  - Pass.
- `.venv/bin/python -m ruff check src/engram/interview/web.py tests/test_interview_web.py`
  - Pass: `All checks passed!`.
- `.venv/bin/python -m ruff format --check src/engram/interview/web.py tests/test_interview_web.py`
  - Pass: `2 files already formatted`.
- `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py`
  - Pass: `57 passed in 61.48s`.
- `striatum heartbeat --session-id sess_e2790772eb1a4bd4962c67cb01aee5d5 --lease-id lease_a354aade69a945f0a6622d2d478904f3`
  - Pass.
- `git diff --check -- src/engram/interview/web.py tests/test_interview_web.py`
  - Pass.

## AC002 Status

AC002 is closed for the interview lane. A configured IPv6 loopback bind now has
matching IPv6 loopback Origin acceptance for mutating POST routes, while the
default app remains limited to the existing D081 host allowlist and rejects
`http://[::1]:<port>` when not configured for an IPv6 bind.

## Not Run

- `make test` was not run; this packet requested focused interview repair and
  verification.
- Browser/Playwright responsive checks were not run.
- No dependency installation was attempted because network use is forbidden for
  this job.

## Residual Risk

- Route tests still require the already-local user-site `PYTHONPATH` workaround
  for `httpx`, matching the prior evidence packets.
- The shared `engram.web.origin.expected_origin_patterns` helper formats host
  strings literally in error-copy expectations. If an IPv6-bound app rejects a
  malformed IPv6 request, the expected list may display `http://::1:<bound-port>`
  rather than a bracketed IPv6 URL. That is display-only and outside this
  packet's write scope; the accepted same-origin IPv6 path is covered.
