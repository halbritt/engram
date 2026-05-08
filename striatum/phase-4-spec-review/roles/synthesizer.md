# Synthesizer Role — Phase 4 Build-Spec Synthesis

Synthesize the Phase 4 build-spec findings ledger into a recommendation for
how to proceed. The synthesis is the artifact the owner reads to decide
whether to:

1. Author a Phase 4 RFC (a design proposal).
2. Author an implementation spec (a binding handoff for build).
3. Revise the Phase 4 row in `BUILD_PHASES.md` before any spec is authored.
4. Pause and resolve a blocker that the reviewers surfaced as
   `needs_revision`.

Structure the synthesis as:

- **Findings outcome** — list of accepted / deferred / rejected ledger IDs
  with a one-line reason for each. "Accepted" means the finding will land
  in whichever spec is authored; "deferred" means it goes to a follow-up
  RFC or is out of Phase 4 scope; "rejected" means the finding is wrong
  or non-blocking and explained why.
- **Open decisions** — questions the ledger surfaced that the owner needs
  to answer before a spec can be authored. Frame as `O###`-style options
  (one accepted resolution per question is fine, but list the alternatives
  for the owner to overrule).
- **Recommendation** — pick one of the four numbered outcomes above with
  a short justification. If the recommendation is "author a spec," include
  a one-paragraph sketch of what the spec covers (entity tables, view
  definition, review-queue surface, query patterns).
- **Risks the synthesis itself carries** — places the synthesis chose a
  resolution the ledger did not unambiguously support; flag these so the
  final review can audit.

Write only the synthesis artifact at the path your job-packet specifies.
Do not modify the ledger or any review file.
