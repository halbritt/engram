# Verification Gate

Run the focused verification for RFC 0054/0055.

Required checks:

1. Focused entity-grounding workflow tests.
2. Focused materialization tests.
3. CLI dispatch tests touching entity-grounding.
4. `make e2e-claim-grounding-runtime`.
5. `python -m ruff check` on touched Python files.
6. `python -m pyright` on touched Python test/source files where feasible.
7. `git diff --check`.
8. `scripts/authority_lint.py`.

Record commands, results, skipped checks, and residual risk. Use maximum safe
parallelism where commands do not contend for the same database.

Write `docs/reviews/rfc0054-0055-entity-grounding-workflow/VERIFICATION.md`.

