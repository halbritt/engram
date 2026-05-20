# CLI, Docs, And Gate Slice

Wire the RFC 0054/0055 implementation into operator-facing local commands and
update project tracking.

Required:

1. Add CLI commands consistent with the RFCs:
   - `engram entity-grounding draft`
   - `engram entity-grounding process-approved`
2. Add CLI dispatch tests in `tests/test_cli.py`.
3. Add the new entity-grounding tests to the relevant Makefile e2e target.
4. Update `CHANGELOG.md` and roadmap/RFC status notes after implementation is
   present.
5. Do not hand-edit generated schema docs.
6. CLI output must not print provider secrets.

Use maximum safe parallelism for file inspection and tests. You are not alone in
the codebase; stay inside the declared write scope and do not revert other
lanes.

Write `docs/reviews/rfc0054-0055-entity-grounding-workflow/CLI_DOCS_HANDOFF.md`.

