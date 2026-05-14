# Roadmap And Index Cleanup Prompt

You are cleaning stale roadmap/index text after the completed Striatum memory
roadmap workflow. You are not promoting an RFC and not making a binding
architecture decision.

Read `STRIATUM_MEMORY_ROADMAP.md`, `docs/rfcs/README.md`, the prior final
synthesis, and the findings ledger. Use the maximum useful number of native
sub-agents for read-only checks before editing.

Make only narrow cleanup edits inside the assigned write scope:

- remove or revise stale text that says the next step is merely to scaffold RFC
  0045;
- ensure the roadmap points to the alignment and hardening evidence workflows
  as follow-up, without claiming implementation authorization;
- keep RFC 0045-RFC 0049 in proposal status unless a separate promotion
  decision already exists.

Produce the expected handoff artifact with changed files, cleanup rationale,
validation, and any remaining stale-doc risks. Run `git diff --check` for the
allowed paths and `make check-refs`.

