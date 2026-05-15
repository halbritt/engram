# Findings Ledger Prompt

You are recording the findings ledger for the source-ingestion RFC research
workflow. You are not authoring the final RFC.

Inputs:

- `REVIEW_privacy_boundary.md` and `REVIEW_project_judgment.md` under
  `docs/reviews/source-ingestion-rfc-research-2026-05-15/`.

Produce a single `FINDINGS_LEDGER.md` that:

1. Normalizes each review's findings into stable handles (e.g.
   `R-001`, `R-002`, `R-003`) with consistent severity.
2. Records the verdict from each review verbatim.
3. Marks each finding as **accepted**, **deferred**, or **declined**
   based on the operator decision (default: accept all unless the
   reviews disagree, in which case mark `needs_operator_decision`).
4. Lists the explicit follow-up actions for the synthesizer.

Do not edit source documents, drafts, or reviews. Do not author RFC body
text. Do not promote the RFC.
