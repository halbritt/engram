# Layer 1 Review Prompt

Review the implementer's Layer 1 code with a fresh context. Run
`make test` yourself. Verify:

1. **Tests pass.** `make test` exits 0. If the implementer's tests
   are missing key cases (idempotent re-import, conflict on changed
   identity, no-egress), flag them.
2. **No outbound network.** Static and runtime inspection of
   `src/engram/git_import.py` — only `subprocess.run(["git", ...])`
   and local filesystem calls.
3. **Contract validator coverage.** The validator rejects every
   mandatory-field omission with a closed error code. The example
   contracts validate cleanly.
4. **Migration soundness.** Migration adds `source_kind='git'` and
   the new tables idempotently. Re-running the migration is safe.
5. **Code matches the standard** in
   [`docs/rfcs/0012-python-agentic-coding-standard.md`](../../docs/rfcs/0012-python-agentic-coding-standard.md):
   `from __future__ import annotations`, type hints, domain
   exception family, no bare `except`, env-var-driven tunables.
6. **RFC 0050 fidelity.** The contract template matches the
   RFC 0050 § Source Contract field set; deviations are flagged.

Return verdict `accept`, `accept_with_findings`, or
`needs_revision`. List findings with stable handles `L1-R-001..`.

Write only the review artifact at
`docs/reviews/source-ingestion-layer1-2026-05-15/REVIEW.md`. Do not
edit source files.

Do not start the review with a markdown `Author:` line; use `Lane:`
and `Role:` instead.
