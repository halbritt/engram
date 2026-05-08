# RFC 0025 Command Surface Verification Report

author: reviewer-codex-gpt-5.5-002
date: 2026-05-08
run: run_5087eedb027549939471a2e88ec45e98
job: verify_command_surface
verdict: accept

## Result

Accepted after revision. The initial verification found two operator-surface issues, both now corrected:

1. `Makefile` now passes `LIMIT` through phase-scoped Phase 2 and Phase 3 targets, including docker and isolated variants. Dry-run checks confirm `make phase2-run LIMIT=25`, `make phase2-run-docker LIMIT=25`, `make phase2-run-isolated LIMIT=25`, `make phase3-run LIMIT=50`, and `make phase3-run-docker LIMIT=50` include the expected `--limit` argument.

2. `engram pipeline --help` now shows only the ambiguous-command disambiguation text and no longer advertises old writable Phase 2 options. Top-level help marks legacy commands as deprecated and points to phase-scoped replacements.

No blocking findings remain.

## Commands Run

- `.venv/bin/python -m ruff check src/engram/cli.py tests/test_cli.py`: passed.
- `.venv/bin/python -m ruff format --check src/engram/cli.py tests/test_cli.py`: passed.
- `.venv/bin/python -m pytest tests/test_cli.py`: 15 passed, 10 skipped.
- `.venv/bin/python -m engram.cli pipeline`: exited 2 with `engram phase2 run`, `engram phase3 run`, and `engram phase4 smoke` alternatives.
- `.venv/bin/python -m engram.cli phase4 run`: exited 2 because `phase4 run` is not defined.
- `.venv/bin/python -m engram.cli phase2 run --help`: exited 0 and showed Phase 2 run options.
- `.venv/bin/python -m engram.cli phase1 ingest-chatgpt --help`: exited 0 and showed the Phase 1 ingest path argument.
- `.venv/bin/python -m engram.cli --help`: exited 0 and marked legacy top-level commands as deprecated, with phase-scoped replacements.
- `.venv/bin/python -m engram.cli pipeline --help`: exited 0 and showed the fail-closed alternatives without writable Phase 2 options.
- `.venv/bin/python -m engram.cli pipeline --limit 5`: exited 2 with fail-closed alternatives.
- `make pipeline`: exited 2 with explicit alternatives.
- `make pipeline-docker`: exited 2 with explicit alternatives.
- `make pipeline-isolated`: exited 2 with explicit alternatives.
- `make -n phase2-run phase3-run phase4-smoke phase1-ingest-chatgpt PATH=/tmp/export`: exited 0 and showed phase-scoped commands.
- `make -n phase2-run LIMIT=25`: exited 0 and output included `--limit 25`.
- `make -n phase2-run-docker LIMIT=25`: exited 0 and output included `--limit 25`.
- `make -n phase2-run-isolated LIMIT=25`: exited 0 and output included `--limit 25`.
- `make -n phase3-run LIMIT=50`: exited 0 and output included `--limit 50`.
- `make -n phase3-run-docker LIMIT=50`: exited 0 and output included `--limit 50`.
- `make -n phase4-smoke LIMIT=25`: exited 0 and output included `--limit 25`.
- `git diff --check`: passed.
- `make check-refs`: 0 errors, 5 pre-existing warnings.

## Residual Risk

No live database pipeline was run during verification. The verification is limited to command parsing, dispatch wiring, Make dry-runs, focused tests, and documentation/reference checks.
