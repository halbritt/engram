# RFC 0025 Command Surface Implementation Handoff

author: author-codex-gpt-5.5-001
date: 2026-05-08
run: run_5087eedb027549939471a2e88ec45e98
job: implement_command_surface

## Summary

Implemented the first RFC 0025 command-surface slice. The CLI now exposes phase-scoped commands for Phase 1 ingestion, Phase 2 segmentation/embedding/run, Phase 3 extraction/consolidation/run, and Phase 4 refresh/entity build/smoke/review operations. The top-level `engram pipeline` command now fails closed with explicit phase-specific alternatives instead of running the Phase 2 segment/embed path.

The Makefile now exposes phase-scoped targets and keeps legacy targets as warning aliases where the replacement is unambiguous. Generic `pipeline`, `pipeline-docker`, and `pipeline-isolated` targets fail closed with explicit alternatives.

## Files Changed

- `src/engram/cli.py`: Added phase-scoped argparse subcommands, legacy command warnings, and fail-closed handling for top-level `pipeline`.
- `Makefile`: Added phase-scoped targets and fail-closed generic pipeline targets; converted legacy targets to warning aliases; preserved `LIMIT` passthrough for phase-scoped bounded targets.
- `tests/test_cli.py`: Added parser and dispatch coverage for phase-scoped commands, ambiguous pipeline behavior, rejected `phase4 run`, legacy warning behavior, `pipeline --help` disambiguation, and Makefile `LIMIT` passthrough.
- `README.md`: Updated operator examples to use phase-scoped commands and documented fail-closed generic pipeline targets.
- `CHANGELOG.md`: Recorded the RFC 0025 command-surface implementation slice.
- `docs/rfcs/README.md`: Marked RFC 0025 implementation status as partial.

## Verification

- `.venv/bin/python -m ruff check --fix src/engram/cli.py tests/test_cli.py`: passed.
- `.venv/bin/python -m ruff format src/engram/cli.py tests/test_cli.py`: no changes needed.
- `.venv/bin/python -m ruff check src/engram/cli.py tests/test_cli.py`: passed.
- `.venv/bin/python -m ruff format --check src/engram/cli.py tests/test_cli.py`: passed.
- `.venv/bin/python -m pytest tests/test_cli.py`: 15 passed, 10 skipped.
- `.venv/bin/python -m engram.cli pipeline`: exited 2 with `engram phase2 run`, `engram phase3 run`, and `engram phase4 smoke` alternatives.
- `.venv/bin/python -m engram.cli phase4 run`: exited 2 because Phase 4 intentionally has no generic `run` command.
- `.venv/bin/python -m engram.cli phase2 run --help`: passed.
- `.venv/bin/python -m engram.cli phase1 ingest-chatgpt --help`: passed.
- `.venv/bin/python -m engram.cli pipeline --help`: passed and showed only fail-closed alternatives.
- `make pipeline`: exited 2 with explicit alternatives.
- `make pipeline-docker`: exited 2 with explicit alternatives.
- `make pipeline-isolated`: exited 2 with explicit alternatives.
- `make -n phase2-run phase3-run phase4-smoke phase1-ingest-chatgpt PATH=/tmp/export`: dry-run emitted the expected phase-scoped commands.
- `make -n phase2-run LIMIT=25`: dry-run emitted `--limit 25`.
- `make -n phase3-run LIMIT=50`: dry-run emitted `--limit 50`.
- `git diff --check`: passed.
- `make check-refs`: 0 errors, 5 pre-existing warnings.

## Residual Risks

This is a command-surface implementation slice, not a full pipeline run. The verification is focused on parser behavior, dispatch wiring, target naming, and documentation consistency. No live Phase 2, Phase 3, or Phase 4 corpus job was executed as part of this handoff.

The implementation intentionally preserves legacy top-level commands as warning aliases except for the ambiguous generic pipeline entry points, which fail closed. A later cleanup can remove legacy aliases after operator migration.
