You are the RFC 0038 follow-up evidence lane. Do not implement code.

Read `REPAIR_EVIDENCE.md` and `REPAIR_DB_ROUTE_HANDOFF.md`. Rerun the focused
checks needed to establish whether the remaining blocker is repaired:

- the DB-backed interview route tests with
  `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test`;
- focused interview and bench route tests;
- shared web substrate tests;
- no-CDN/static checks;
- focused Ruff check/format checks on touched UI files;
- `git diff --check`;
- `make check-refs`.

Publish the required evidence artifact. Include exact commands and outcomes.
If a dependency is missing from the active venv, record it explicitly and use
only already-local dependencies; do not install from the network.
