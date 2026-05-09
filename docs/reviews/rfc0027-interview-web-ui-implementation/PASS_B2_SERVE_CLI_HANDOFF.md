# Pass B2 — Serve CLI / Makefile / Docs Handoff
author: author-codex-gpt-5.5-001

Status: handoff
Date: 2026-05-09
RFC refs: RFC-0027
Decision refs: D080
Phase refs: PHASE-0003-FOLLOWON

## Scope

Pass B2 owns the operator-facing scaffolding around the FastAPI app
that Pass B1 produces in parallel:

- `engram phase3 interview serve` subparser + driver in
  `src/engram/cli.py` (loopback-only, deferred FastAPI/Uvicorn import).
- Makefile target `phase3-interview-serve` with `HOST` / `PORT`
  passthrough.
- Operator-facing Web UI section in `docs/howto/gold-set-interview.md`.
- CHANGELOG entry under `## [Unreleased]` → `### Added`.
- Four new dispatch tests in `tests/test_interview_cli.py`.

Strict write-scope: no edits to `src/engram/interview/`,
`src/engram/interview/templates/`, `src/engram/interview/static/`,
`tests/test_interview_web.py`, or `pyproject.toml`. Those land via Pass
B1.

## Files modified

| Path | Change |
|------|--------|
| `src/engram/cli.py` | Added `phase3 interview serve` subparser, `_SERVE_LOOPBACK_HOSTS`, and `run_phase3_interview_serve` driver; wired dispatch. Imports `engram.interview.web` and `uvicorn` lazily inside the driver. |
| `Makefile` | Added `phase3-interview-serve` target (with `HOST` / `PORT` passthrough) and added it to the `.PHONY` list. |
| `docs/howto/gold-set-interview.md` | New "Web UI (alternative to the CLI loop)" section after "Your first session". Documents loopback-only posture, single-click vs rationale-required commit paths, keyboard hints, and v1 CLI-only features. |
| `CHANGELOG.md` | New `[Unreleased]` → `Added` entry summarizing RFC 0027 implementation (FastAPI + htmx, loopback-only, Tier 1 ceiling, vendored htmx, migration 011, optional `engram[serve]` extra). |
| `tests/test_interview_cli.py` | Four new dispatch tests under "RFC 0027 / Spec 0027: serve subparser" header. |

## Key design choices

- **Deferred FastAPI/Uvicorn import.** `from engram.interview.web import app`
  and `import uvicorn` live inside `run_phase3_interview_serve` so the
  CLI itself does not require the `engram[serve]` extra to be installed.
  Non-serve subcommands (and headless installs) never touch FastAPI.
- **Host check runs before the import.** Non-loopback `--host` exits 8
  before any optional deps load, so the policy holds even on an install
  that happens to have FastAPI present.
- **Loopback set: `127.0.0.1`, `localhost`, `::1`.** Per work-packet
  guidance. The spec's prose lists `127.0.0.1` and `localhost`; `::1` is
  the IPv6 loopback equivalent and is the same posture. No
  `--allow-non-loopback` flag (F005).
- **Single worker, `log_level="warning"`.** Matches spec § Process model.
- **Banner.** `phase3 interview serve: listening on http://<host>:<port>
  (ctrl-c to stop; non-loopback hosts refused)`.

## Verification commands run

| Command | Exit | Result |
|---------|------|--------|
| `.venv/bin/engram phase3 interview --help` | 0 | `serve` subcommand listed alongside the existing seven |
| `.venv/bin/engram phase3 interview serve --help` | 0 | `--host`, `--port` shown; no `--allow-non-loopback` |
| `.venv/bin/python -m pytest tests/test_interview_cli.py -x --no-header` | 0 | 17 passed, 1 skipped (pre-existing DB-required test, untouched by B2) |
| `make -n phase3-interview-serve` | 0 | shows `.venv/bin/python -m engram.cli phase3 interview serve` |
| `make -n phase3-interview-serve HOST=127.0.0.1 PORT=9000` | 0 | shows `--host 127.0.0.1 --port 9000` passthrough |
| `make check-refs` | 0 | 0 errors, 5 pre-existing warnings, 162 checks ok |

### `engram phase3 interview --help` (verbatim, proves serve registered)

```
usage: engram phase3 interview [-h]
                               {start,resume,history,export,list-sessions,coverage,enable-active-learning,serve}
                               ...

positional arguments:
  {start,resume,history,export,list-sessions,coverage,enable-active-learning,serve}
    start               Start a new gold-set interview session
    resume              Resume an existing gold-set interview session
    history             Show gold-label history for a target
    export              Export gold-label rows (default --privacy-tier-max 1)
    list-sessions       List gold-label sessions
    coverage            Show stratum coverage for the gold-label corpus
    enable-active-learning
                        Enable opt-in active-learning bias for the next
                        session
    serve               Run the local web UI for the gold-set interview (RFC
                        0027)

options:
  -h, --help            show this help message and exit
```

### `engram phase3 interview serve --help` (verbatim, proves no escape clause)

```
usage: engram phase3 interview serve [-h] [--host HOST] [--port PORT]

options:
  -h, --help   show this help message and exit
  --host HOST
  --port PORT
```

### `tests/test_interview_cli.py` (verbose tail)

```
tests/test_interview_cli.py::test_phase3_interview_serve_subparser_registered PASSED
tests/test_interview_cli.py::test_phase3_interview_serve_default_host_port PASSED
tests/test_interview_cli.py::test_phase3_interview_serve_refuses_non_loopback PASSED
tests/test_interview_cli.py::test_phase3_interview_serve_pip_install_hint_when_imports_fail PASSED

======================== 17 passed, 1 skipped in 0.18s =========================
```

The single skipped test is the pre-existing DB-required
`test_phase3_interview_start_writes_session_targets` (Migration 011);
B2 did not touch that test or its surrounding code.

## Residual gaps / cross-pass coupling

- The howto's new "Web UI" section optimistically references a
  navigable index page, six verdict buttons, and a `?` keyboard help
  modal — all owned by Pass B1's templates. B2 wrote the prose without
  inspecting those files (they are out of write scope). If B1's final
  template names diverge (e.g., a different keyboard hint), the howto
  will need a small follow-up in a later pass.
- `engram[serve]` extra is declared by Pass B1 in `pyproject.toml`. B2
  did not add or modify any dependency declarations. Test
  `test_phase3_interview_serve_pip_install_hint_when_imports_fail`
  monkey-patches `builtins.__import__` to simulate a missing dep
  rather than uninstalling FastAPI, so the test works regardless of
  B1's install state.
- The driver prints to stdout for the success-path banner and to stderr
  for both the loopback-refusal and missing-dep paths. `uvicorn.run`
  blocks; its own `log_level="warning"` keeps the CLI quiet under
  normal operation.

## Next steps

- Pass B1 produces `docs/reviews/rfc0027-interview-web-ui-implementation/PASS_B1_WEB_APP_HANDOFF.md` in parallel.
- A follow-on `verify_web_ui` pass runs against both handoffs (Tier 0
  smoke from spec § Acceptance criteria — start `engram phase3
  interview serve`, hit `/`, confirm an index renders).
