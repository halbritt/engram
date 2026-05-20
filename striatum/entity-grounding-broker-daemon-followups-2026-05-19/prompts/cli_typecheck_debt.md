# CLI Typecheck Debt

Clear the pre-existing CLI typecheck blocker that surfaced during daemon
verification.

Required outcome:

- Make the focused typecheck path including `src/engram/cli.py` green for the
  daemon-related verification command, or document why the correct scoped check
  excludes the optional serve dependency.
- Address the unresolved optional `uvicorn` import without adding hosted
  services or changing runtime semantics for `phase3 interview serve`.
- Avoid broad CLI refactors. The existing complexity warning is known debt; fix
  only if the minimal optional-import repair naturally removes it.
- Add or update deterministic tests only if behavior changes.

Suggested checks:

```sh
.venv/bin/python -m pyright src/engram/entity_grounding_daemon.py src/engram/entity_grounding_materialization.py src/engram/cli.py
.venv/bin/python -m pytest -q tests/test_cli.py
```

Publish
`docs/reviews/entity-grounding-broker-daemon-followups-2026-05-19/CLI_TYPECHECK_DEBT_HANDOFF.md`.
