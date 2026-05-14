# RFC Promotion Recommendation Prompt

You are authoring a promotion recommendation for one Striatum memory RFC after
the completed alignment workflow. You are not promoting the RFC unilaterally,
not editing the RFC itself, and not authorizing implementation.

Read the assigned RFC, the alignment findings ledger, the alignment final
synthesis, the matching `ALIGN_RFC*.md` handoff, and the relevant prior
roadmap findings ledger and synthesis. Use the maximum useful number of native
sub-agents for read-only analysis. Ask them to identify exactly which
nonblocking/deferred findings from the alignment ledger still affect this RFC
at promotion time, and whether the RFC text is internally consistent with
itself and adjacent RFCs.

Produce the expected handoff artifact `PROMOTE_RFC<id>.md`. It must include:

- recommendation: one of `ready_for_promotion`, `ready_with_findings`,
  `blocked_on_deferred`, or `needs_revision`;
- per-finding disposition for every alignment-ledger AL-N item the RFC
  touches, naming whether the finding is resolved, residual nonblocking,
  carried-as-deferred, or unresolved;
- per-finding disposition for the deferred AL-D001 RFC 0044 hardening / EG-000
  evidence, AL-D002 acceptance decision, AL-D003 Level 3 default-on, and
  AL-D004 generated-product contract gates as they apply to this RFC;
- a short, explicit list of human checkpoints still required before
  promotion (for example, a recorded AL-D002 acceptance entry in
  `DECISION_LOG.md`);
- evidence that the RFC stays local-only, no-egress, immutable for raw
  evidence, rebuildable for derived projections, and provenance-preserving;
- validation run and result (`make check-refs` at minimum);
- residual workflow friction or remaining ambiguity for the next operator.

Do not edit code, tests, migrations, generated schema docs, the RFC text
itself, `DECISION_LOG.md`, `CHANGELOG.md`, or `STRIATUM_MEMORY_ROADMAP.md`.
The recommendation is proposal-only and does not authorize implementation.

Run `git diff --check` for the allowed paths.
