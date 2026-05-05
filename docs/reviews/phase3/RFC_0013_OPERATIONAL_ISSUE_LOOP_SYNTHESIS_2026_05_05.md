# RFC 0013 Review Synthesis

Date: 2026-05-05
Artifact: `docs/rfcs/0013-development-operational-issue-loop.md`

## Review Inputs

- `docs/reviews/phase3/RFC_0013_OPERATIONAL_ISSUE_LOOP_REVIEW_codex_gpt5_5_2026_05_05.md`
- `docs/reviews/phase3/RFC_0013_OPERATIONAL_ISSUE_LOOP_REVIEW_claude_opus_4_7_2026_05_05.md`
- `docs/reviews/phase3/RFC_0013_OPERATIONAL_ISSUE_LOOP_REVIEW_gemini_pro_3_1_2026_05_05.md`

## Verdicts

- Codex GPT-5.5: `reject_for_revision`
- Claude Opus 4.7: `accept_with_findings`
- Gemini Pro 3.1: `accept_with_findings`

Because Codex returned `reject_for_revision`, the revised RFC requires a fresh
Codex re-review before implementation proceeds.

## Findings Ledger

| Finding | Source | Disposition | Applied Delta |
| --- | --- | --- | --- |
| Artifact privacy / corpus-content redaction | Codex High, Claude Major | accepted | Added committed-artifact privacy rules, owner-approval escape hatch, untracked local diagnostics pattern, and redaction requirement. Redacted the existing limit-10 report. |
| Progress-state quarantine is not enforceable | Codex High | accepted | Replaced progress-only quarantine with an enforceable quarantine invariant: ready markers require query exclusion proof or repair through close/supersede/rebuild/requeue. |
| Marker precedence and stale ready markers | Codex Medium, Gemini Low | accepted | Added machine-readable marker schema, per-loop directories, `supersedes`, newest-state precedence, and blocked/human-checkpoint terminal behavior. |
| Objective expansion limits / OQ4 | Codex Medium, Claude Major | accepted | Resolved with conservative defaults: nonzero exit, failed stage, prompt/model contract failure, unrepaired partial state, dropped-claim rate >10%, unapplied findings, or missing same-model re-review block expansion. |
| Infrastructure/environment class | Gemini Medium | accepted | Added `infrastructure_or_environment_failure`. |
| Targeted rerun must hit the failed scope | Gemini Medium, Claude Major | accepted | Verification ladder now requires targeted rerun of the failed entity when feasible before broadening. |
| Deletion path too permissive | Claude Major | accepted | Forbids deleting `beliefs`, `belief_audit`, `contradictions`, or `claim_extractions` in development loops; any other derived deletion needs repair plan, review, selector, counts, and owner approval. |
| Script automation is aspirational | Claude Major | accepted_with_modification | RFC now states automation must be updated before relying on the policy, or runbook must explicitly mark manual enforcement. |
| Postbuild marker filename convention undefined | Claude Moderate | accepted | Added per-loop marker directory and canonical filenames. Existing flat markers remain legacy provenance. |
| Front matter should be mandatory | Claude Moderate | accepted | Added required YAML front matter. |
| Raw-evidence repair silence | Claude Moderate | accepted | Added raw-evidence corruption route to data RFC / owner decision; operational loop may not edit raw rows. |
| Acceptance criterion self-referential | Claude Moderate | accepted_with_modification | Replaced with concrete acceptance requirements for re-review, runbook/script update, redacted report, markers, and gates. |
| Taxonomy overlap | Claude Moderate | accepted_with_modification | Added "most restrictive default action wins" rather than a brittle total order. |
| Re-review semantics duplicate runbook | Claude Moderate | accepted | RFC now points to the runbook as source of truth. |
| Counts before/after vague | Claude Minor | accepted | Added canonical Phase 3 post-build counts. |
| Concurrent loops undefined | Claude Minor | accepted | Added one-loop-per-area unless distinct run IDs and marker directories exist. |

## Additional Coordinator Fixes

- Resolved the duplicate `D060` decision id by renumbering the Phase 3
  partial-consolidation guard to D061. The existing generalized-path decision
  remains D060.
- Updated RFC 0013 references from D060 to D061.
- Redacted the Phase 3 limit-10 run report so tracked operational artifacts no
  longer contain private corpus-derived summaries or belief values.

## Next Step

Run a Codex same-reviewer re-review on the revised RFC. If it accepts, promote
the accepted process policy into `DECISION_LOG.md` and update the Phase 3
runbook/script posture before any larger bounded run.
