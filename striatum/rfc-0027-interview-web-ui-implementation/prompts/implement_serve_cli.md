# Pass B2: CLI serve subparser + Makefile + Docs + CHANGELOG

You are running **Pass B2** of the RFC 0027 / Spec 0027 implementation.
Pass A (render.py + migration 011 + cli.py refactor) is already landed.
**Pass B1** runs in parallel and owns the FastAPI app + templates +
web tests; you do NOT touch those.

# Spec

`/home/halbritt/git/engram/docs/specs/0027-interview-web-ui-spec.md`
sections relevant to you: § CLI integration, § Acceptance criteria
(Tier 0 smoke), § Privacy and security (loopback-only invariants).

# Your write scope (strictly enforced by Striatum)

Only edit:

- `src/engram/cli.py` — add `engram phase3 interview serve` subparser + driver.
- `Makefile` — add `phase3-interview-serve` target.
- `docs/howto/gold-set-interview.md` — add a "Web UI" section.
- `CHANGELOG.md` — entry under `## [Unreleased]`.
- `tests/test_interview_cli.py` — add tests for the serve subparser.
- `docs/reviews/rfc0027-interview-web-ui-implementation/PASS_B2_SERVE_CLI_HANDOFF.md` (handoff artifact).

DO NOT touch: `src/engram/interview/*.py`,
`src/engram/interview/templates/`, `src/engram/interview/static/`,
`tests/test_interview_web.py`, `pyproject.toml`, or any RFC / spec /
decision-log / build-phases / human-requirements doc.

# Deliverables

## 1. CLI subparser in `src/engram/cli.py`

Add `engram phase3 interview serve` under the existing `phase3
interview` subparser group (look for `phase3_interview_parser` and the
existing subcommands `start`, `resume`, `history`, `export`,
`list-sessions`, `coverage`, `enable-active-learning`).

```python
phase3_interview_serve_parser = interview_subparsers.add_parser(
    "serve",
    help="Run the local web UI for the gold-set interview (RFC 0027)",
)
phase3_interview_serve_parser.add_argument("--host", type=str, default="127.0.0.1")
phase3_interview_serve_parser.add_argument("--port", type=int, default=8765)
phase3_interview_serve_parser.set_defaults(command="phase3-interview-serve")
```

Driver function `run_phase3_interview_serve(args)`:

1. Reject non-loopback `--host`. Allowed exactly: `127.0.0.1`, `localhost`, `::1`. Anything else → print clear error and `sys.exit(8)`. Do NOT add an `--allow-non-loopback` flag.
2. Try to import: `from engram.interview.web import app` and `import uvicorn`. If either ImportError, print `Run: pip install engram[serve]` and `sys.exit(2)`.
3. Print a one-line banner: `phase3 interview serve: listening on http://<host>:<port>` plus a hint like `ctrl-c to stop; non-loopback hosts refused`.
4. Call `uvicorn.run(app, host=args.host, port=args.port, workers=1, log_level="warning")`. Single worker per spec § Process model.

Wire dispatch in `main()`'s command-handler chain (look for the existing
`if args.command == "phase3-interview-..."` block).

## 2. Makefile target

```make
phase3-interview-serve: install
	$(PYTHON) -m engram.cli phase3 interview serve $(if $(HOST),--host $(HOST),) $(if $(PORT),--port $(PORT),)
```

Add `phase3-interview-serve` to the `.PHONY` line at the top of the
Makefile (look for the existing `phase3-interview-*` entries).

## 3. `docs/howto/gold-set-interview.md` — Web UI section

Add a new section near the top (after "Prerequisites" or after "What is
wired today" — the natural placement is right after the section that
discusses the CLI loop, since the web UI is an alternate surface for
the same data).

Content (operator-facing, ~20–30 lines):

```md
## Web UI (alternative to the CLI loop)

`engram phase3 interview serve` runs a local browser UI for the same
interview surface (RFC 0027 / spec 0027). The app binds to
127.0.0.1 by default; non-loopback hosts are refused. There is no
auth and no TLS — same posture as the CLI.

```sh
# install the optional FastAPI / Uvicorn / Jinja2 deps if you haven't yet
pip install -e ".[serve]"

# start the server
engram phase3 interview serve            # http://127.0.0.1:8765
engram phase3 interview serve --port 9000
```

Open `http://127.0.0.1:8765/` in your browser. The index page lists
open sessions and exposes a "New session" form (`n`, `seed`). Click
"Start" and you'll be on a per-question page with the same metadata
the CLI shows: header, predicate gloss, evidence excerpts, and the
six verdict buttons. `true` and `skip` commit on a single click;
`false` / `stale` / `unsupported` / `unsure` reveal a verdict-specific
rationale prompt before committing. Press `?` to see all keyboard
shortcuts; `Esc` closes the help. `q` (or the "Save and quit" button)
leaves the session open and prints a resume command.

The CLI loop continues to work unchanged — sessions started in the
CLI are resumable in the web UI and vice-versa, since both write to
`gold_label_sessions` and `gold_label_session_targets`.

What the web UI does NOT expose in v1 (CLI-only): `export`, `history`,
`coverage` (a small inline strata strip ships in v1; the dashboard is
deferred), `enable-active-learning`, `--include-superseded`,
`--ignore-cooldown`. Drop to the CLI for those.
```

## 4. CHANGELOG entry

Under `## [Unreleased]` → `### Added`, add:

```md
- RFC 0027 implementation: FastAPI + htmx web UI for the gold-set
  interview surface, served by `engram phase3 interview serve` (RFC
  0027 / spec 0027 / D080). Loopback-only with no escape clause;
  Origin-allowlist enforces CSRF posture; Tier 1 ceiling on
  full-message and context routes; vendored htmx (no CDN). Verdict
  commit single-click for `true`/`skip` and two-click rationale-required
  for `false`/`stale`/`unsupported`/`unsure`; the CLI loop continues to
  exist and shares the new `engram.interview.render` helpers landed in
  Pass A. Migration 011 materializes the sampled order at session
  creation so CLI- and web-started sessions are mutually resumable.
  FastAPI / Uvicorn / Jinja2 ship under the `engram[serve]` optional
  extra; headless installs unchanged.
```

## 5. CLI test extensions in `tests/test_interview_cli.py`

Add 4 tests:

- `test_phase3_interview_serve_subparser_registered` — `engram phase3 interview --help` lists `serve`.
- `test_phase3_interview_serve_default_host_port` — argparse defaults `127.0.0.1` and `8765`.
- `test_phase3_interview_serve_refuses_non_loopback` — invoke `cli.main(["phase3", "interview", "serve", "--host", "0.0.0.0"])`; expect exit code 8 and stderr containing "loopback".
- `test_phase3_interview_serve_pip_install_hint_when_imports_fail` — monkeypatch the `engram.interview.web` import to raise ImportError; expect exit code 2 and stderr containing `pip install engram[serve]`.

Tests must NOT actually start uvicorn. Use `monkeypatch` to replace
`uvicorn.run` with a no-op for the import-success path; for the
`--host` rejection path, the function should exit BEFORE importing
uvicorn (so no monkeypatch needed).

## 6. Handoff artifact

When done, write `docs/reviews/rfc0027-interview-web-ui-implementation/PASS_B2_SERVE_CLI_HANDOFF.md`:

```md
# Pass B2 — Serve CLI / Makefile / Docs Handoff
author: <byline from work packet>

Status: handoff
Date: 2026-05-09
RFC refs: RFC-0027
Decision refs: D080
Phase refs: PHASE-0003-FOLLOWON

## Files modified
- src/engram/cli.py
- Makefile
- docs/howto/gold-set-interview.md
- CHANGELOG.md
- tests/test_interview_cli.py

## Verification commands run
| Command | Exit | Result |
|---------|------|--------|
| .venv/bin/engram phase3 interview --help | 0 | shows serve subcommand |
| .venv/bin/engram phase3 interview serve --help | 0 | shows --host, --port, no --allow-non-loopback |
| .venv/bin/python -m pytest tests/test_interview_cli.py -x | 0 | N passed |
| make -n phase3-interview-serve | 0 | shows serve invocation |
| make check-refs 2>&1 | tail -3 | 0 | 0 errors |

## Residual gaps
- ...

## Next steps
- Pass B1 produces docs/reviews/rfc0027-interview-web-ui-implementation/PASS_B1_WEB_APP_HANDOFF.md in parallel.
- verify_web_ui runs against both handoffs.
```

# Verification commands you must run (capture in handoff)

```sh
.venv/bin/engram phase3 interview --help 2>&1 | head -15
.venv/bin/engram phase3 interview serve --help 2>&1 | head -10
.venv/bin/python -m pytest tests/test_interview_cli.py -x --no-header 2>&1 | tail -5
make -n phase3-interview-serve 2>&1 | head -3
make check-refs 2>&1 | tail -3
```

# Guardrails

- DO NOT import `engram.interview.web` at module level in `cli.py` —
  defer the import to inside `run_phase3_interview_serve` so the CLI
  itself doesn't require FastAPI to be installed.
- DO NOT add `engram phase3 interview serve --allow-non-loopback` or
  any equivalent escape hatch.
- DO NOT touch `pyproject.toml` (Pass B1 owns the dependency block).
- DO NOT touch `src/engram/interview/web.py` or templates (Pass B1).
- The Web UI section in the howto must be honest about v1 scope (no
  export/history/coverage/active-learning toggle).

Report back: files modified, test results, the exact `engram phase3 interview --help` output as evidence the serve subcommand is wired, any blockers.