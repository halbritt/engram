You are the RFC 0038 accept-with-findings evidence lane. Do not implement code.

Read the three accept-findings handoffs and run focused evidence:

- DB-backed interview and bench route tests with
  `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test`;
- shared web substrate tests;
- route construction smoke checks;
- no-CDN/static scan;
- focused Ruff check and format check on touched UI files;
- `git diff --check`;
- `make check-refs`.

If the active venv still lacks `httpx`, record that explicitly and use only
already-local dependencies; do not install from the network. Publish exact
commands and outcomes.
