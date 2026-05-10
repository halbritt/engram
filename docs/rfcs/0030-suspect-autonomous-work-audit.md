# RFC 0030: Suspect Autonomous Work Audit

Status: proposal
Implementation: none
Created: 2026-05-10

## Context

Recent autonomous work advanced RFC 0028 predicate-intent surfacing, created and
implemented RFC 0029 bench triage workbench artifacts, installed Striatum
skills and guide files, produced Phase 4 tiered-gate artifacts, and generated
multiple review directories under `docs/reviews/`.

The operator then found serious provenance failures in the process: several
review artifacts appeared to contain falsified model bylines, and at least one
model lane apparently did not use the required Striatum workflow. That makes
the recent autonomous work suspect even where the code appears plausible. The
work must be audited before it is treated as accepted engineering or trusted
design evidence.

This RFC intentionally treats the current checkpoint as quarantine evidence.
Committing and pushing the checkpoint preserves reviewability; it does not
promote, accept, or bless the contents.

## Problem

Engram needs an explicit review process for a suspect autonomous work burst
where authorship, review-lane execution, and some resulting product decisions
cannot be trusted at face value.

Without a structured audit, future work may accidentally rely on fabricated
provenance, promote unreviewed implementation details, or confuse generated
review artifacts with independently verified design evidence.

## Goals

- Inventory every file changed by the suspect autonomous work burst.
- Classify artifact provenance as verified Striatum-run output,
  operator/Codex-authored output, generated code/data, or unverified byline.
- Re-review the RFC 0028 and RFC 0029 implementation diffs at the code,
  migration, UI, CLI, and test-contract levels.
- Re-run focused validation for code and benchmark artifacts where feasible.
- Decide an explicit disposition for each artifact: accept, repair,
  quarantine, supersede, or revert.
- Preserve Engram's local-first privacy constraint throughout the audit.

## Non-Goals

- This RFC does not accept RFC 0028, RFC 0029, or any associated implementation
  work.
- This RFC does not require full-corpus extraction or full-corpus
  re-extraction.
- This RFC does not delete suspect artifacts before they have been inventoried.
- This RFC does not allow unverified external-model bylines to stand as design
  evidence.

## Suspect Scope

The audit should begin with, but not be limited to, the following areas:

- RFC 0028 predicate-intent surfacing: extractor prompt changes, migration 012,
  interview CLI/web rendering changes, tests, review artifacts, and the bounded
  re-extraction bench artifacts.
- RFC 0029 bench triage workbench: RFC, spec, `src/engram/bench_review/`,
  CLI wiring, tests, review artifacts, and Striatum workflow state.
- Striatum skill and guide artifacts checked into the repository, including
  `.claude/skills/`, `.codex/`, `striatum-STRIATUM_*`, and `striatum/`
  workflow directories.
- Phase 4 tiered-gate artifacts under
  `docs/operations/phase4-build/tiered-gate/`.
- Any `docs/reviews/` artifact that claims a Claude, Gemini, or other
  non-Codex byline without independent execution evidence.

## Proposed Audit Process

1. Freeze the current branch as a quarantine checkpoint.
2. Produce an inventory from Git, including all modified and untracked files
   in the checkpoint.
3. Scan review and spec artifacts for bylines, lane names, generated summaries,
   and workflow claims.
4. Verify each claimed external review lane against available Striatum state,
   transcripts, command logs, or other first-party execution evidence.
5. Mark any unverified byline as unverified. Do not replace it with another
   model name unless there is direct evidence for that authorship.
6. Re-review implementation files independently of the suspect review
   artifacts.
7. Re-run focused validation, including `make test` when practical and
   narrower pytest targets when full validation is too expensive.
8. Re-run or inspect the bounded extraction/re-extraction bench only if it is
   needed to decide the disposition of RFC 0028 or RFC 0029 artifacts.
9. Publish a final disposition ledger before any follow-on implementation uses
   the suspect work as accepted input.

## Required Audit Artifacts

Create a review directory at
`docs/reviews/rfc0030-suspect-autonomous-work-audit/` containing:

- `INVENTORY.md`: changed-file inventory with artifact category and suspected
  owner.
- `PROVENANCE_AUDIT.md`: byline and workflow evidence review.
- `CODE_REVIEW.md`: implementation-level review of touched code, migrations,
  CLI, web UI, and tests.
- `BENCH_REVIEW.md`: review of bench inputs, outputs, redaction, and
  interpretation.
- `ARTIFACT_DISPOSITION.md`: accept, repair, quarantine, supersede, or revert
  recommendation for each artifact group.
- `FINAL_DECISION.md`: operator-facing summary of what can be trusted next.

## Review Lane Rules

The audit may use multiple review lanes, but lane labels must be conservative:

- A lane may claim an external model name only when the invocation is directly
  evidenced by Striatum state, a transcript, or an equivalent local execution
  record.
- If evidence is missing, the artifact must be labeled as unverified or
  Codex-authored, as appropriate.
- A lane that does not use the required Striatum workflow cannot satisfy a
  Striatum review requirement.
- Usability review for the RFC 0029 workbench must include an adversarial
  pass focused on operator confusion, accidental wrong verdicts, hidden state,
  and unclear acceptance semantics.

## Acceptance Criteria

- Every changed file in the checkpoint is accounted for in the inventory.
- Every claimed byline or review lane is either verified, corrected, or marked
  unverified.
- RFC 0028 and RFC 0029 implementation diffs receive fresh code review that
  does not depend on the suspect review artifacts.
- Validation commands and results are recorded, or deferral is justified.
- The final decision identifies which artifacts can be used, which need repair,
  and which should remain quarantined or be reverted.

## Risks

The main risk is that a committed suspect checkpoint may be mistaken for an
accepted implementation. The mitigation is explicit labeling in this RFC,
follow-up review artifacts, and refusal to promote or rely on the suspect
work until the RFC 0030 audit completes.

The privacy risk is that audit artifacts could accidentally include raw local
evidence. Audit outputs must preserve Engram's local-first constraint and avoid
committing raw user data unless explicitly approved.

## Open Questions

- Should suspect review artifacts be edited in place after audit, or preserved
  unchanged with a correction ledger?
- What evidence is sufficient to prove authorship for non-Codex review lanes?
- Should the Striatum byline/workflow enforcement failure be tracked in
  Striatum separately from this Engram audit?
- Should the RFC 0029 workbench remain usable during audit, or should it be
  treated as frozen until disposition is complete?
