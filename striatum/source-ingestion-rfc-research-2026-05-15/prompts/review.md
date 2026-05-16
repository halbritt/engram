# Review Prompt

You are reviewing the three RFC drafts plus the prior-art dossier as a
candidate package for synthesis. The package is proposal-only; you are not
promoting an RFC. You are deciding whether synthesis can proceed cleanly.

Inputs:

- The three author drafts: `DRAFT_claude.md`, `DRAFT_codex.md`,
  `DRAFT_gemini.md` under
  `docs/reviews/source-ingestion-rfc-research-2026-05-15/`.
- The prior-art dossier: `PRIOR_ART_DOSSIER.md` under the same path.
- The source design document: `docs/design/source-ingestion-expansion-proposal-2026-05-15.md`.
- Project canon: `AGENTS.md`, `HUMAN_REQUIREMENTS.md`, `SPEC.md`,
  `BUILD_PHASES.md`, `ROADMAP.md`, `docs/schema/README.md`.
- Adjacent RFCs: `docs/rfcs/0033-*.md` through `0036-*.md`, and
  `0044-*.md` through `0049-*.md`.

Use a fresh context and the maximum useful number of read-only sub-agents.

Your review must report:

1. **Scope** — does the package overshoot what the design doc asks?
   Does it conflict with adjacent RFCs? Is the scope-kept-out section
   honest?
2. **Privacy and no-egress** — does any draft introduce a path that
   could exfiltrate user data, even by default? Does any importer
   propose hosted services without explicit user gating?
3. **Source contract coherence** — do the three drafts converge on a
   contract template that is implementable, or do they disagree on
   load-bearing fields? Flag the divergences explicitly.
4. **Rollout order** — is the proposed order defensible by the
   highest-signal, lowest-egress-risk principle?
5. **Evaluation gates** — are the proposed gates enough to keep the
   pipeline honest under regression?
6. **Open questions** — are there missing open questions that should
   block synthesis?

Return a verdict: `accept`, `accept_with_findings`, or `needs_revision`.
Verdicts apply to the candidate package for synthesis, not to any
individual draft. List each finding with a stable handle (e.g. `R-001`),
the affected drafts, and a concrete suggested edit.

Do not edit source documents, the drafts, or the dossier. Write only the
expected review artifact.
