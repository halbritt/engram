# Synthesis Prompt

You are the final synthesizer. Produce a single RFC at
`docs/rfcs/0050-source-ingestion-expansion.md` from the three author drafts,
the prior-art dossier, and the accepted findings.

Inputs:

- `DRAFT_claude.md`, `DRAFT_codex.md`, `DRAFT_gemini.md`,
  `PRIOR_ART_DOSSIER.md` under
  `docs/reviews/source-ingestion-rfc-research-2026-05-15/`.
- `FINDINGS_LEDGER.md` under the same path.
- The source design document at
  `docs/design/source-ingestion-expansion-proposal-2026-05-15.md`.
- Project canon and adjacent RFCs as previously listed.

The synthesized RFC must:

1. Include front matter (number `0050`, title, status `proposal`, date,
   authors crediting the three lanes by name).
2. Cite the source design document as the primary input.
3. Resolve every divergence the findings ledger flagged. Pick a winner
   per divergence and record the reason in a "Synthesis Notes" section
   inside the RFC.
4. Apply every accepted finding from the ledger.
5. Honor every Engram constraint: no cloud dependency, no user data
   leaving the machine unless explicitly requested, immutable raw
   evidence, rebuildable projections, provenance/confidence/auditability.
6. Include explicit "Scope Kept Out" and "Open Questions" sections.
7. Cross-reference RFC 0033-0036 and RFC 0044-0049 where applicable.

The RFC is **proposal status only**. Do not record acceptance. Do not
edit `DECISION_LOG.md`, `BUILD_PHASES.md`, `CHANGELOG.md`, or
`docs/rfcs/README.md` index. Acceptance is an operator decision.

Run `git diff --check` on the allowed paths before completing. If the
RFC introduces new anchors, run `make check-refs`.
