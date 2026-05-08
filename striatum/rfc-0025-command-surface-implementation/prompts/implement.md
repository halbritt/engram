# Implement RFC 0025 Command Surface

Implement the accepted RFC 0025 command-surface contract. Read the work packet,
`AGENTS.md`, `docs/rfcs/0025-phase-scoped-command-names.md`,
`DECISION_LOG.md`, `src/engram/cli.py`, `Makefile`, `README.md`, and
`tests/test_cli.py` before editing.

Required behavior:

1. Add nested phase-scoped CLI commands:
   `engram phase1 ingest-chatgpt`, `engram phase1 ingest-claude`,
   `engram phase1 ingest-gemini`, `engram phase2 segment`,
   `engram phase2 embed`, `engram phase2 run`, `engram phase3 extract`,
   `engram phase3 consolidate`, `engram phase3 run`, `engram phase4 smoke`,
   `engram phase4 refresh-current-beliefs`, `engram phase4 build-entities`,
   and `engram phase4 review-belief`.
2. Do not add `engram phase4 run`.
3. Make `engram pipeline` fail closed before any database connection and print
   explicit alternatives.
4. Add phase-scoped Make targets for Phase 1 ingest, Phase 2, Phase 3, and
   Phase 4 smoke/build paths. Make `pipeline`, `pipeline-docker`, and
   `pipeline-isolated` fail closed with scoped alternatives.
5. Keep legacy bare mutating commands operational for the compatibility window,
   but print warnings that name the phase-scoped replacement.
6. Update README/help-facing examples so they do not teach commands that now
   fail closed.
7. Add deterministic tests. At minimum, cover fail-closed behavior before
   database connection, nested phase command dispatch, absent `phase4 run`, and
   the relevant Make target surface where feasible.

Do not change migrations or database schema. Do not call live LLMs in tests.
Keep changes scoped to the declared write scope.

When done, write `docs/reviews/rfc0025-command-surface-implementation/IMPLEMENTATION_HANDOFF.md`
with the exact lowercase `author:` line from the work packet, a summary of
changed files, the verification commands already run, and any residual risks.
