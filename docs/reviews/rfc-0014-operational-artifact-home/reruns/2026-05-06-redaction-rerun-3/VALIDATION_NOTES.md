# RFC 0014 Spec Handoff Agent Runner Validation Notes

Run slug: `2026-05-06-redaction-rerun-3`
Run ID: `run_198eb48427bb407c87dc72e03bc21948`
Branch: `agent-runner/rfc-0014-validation`
Date: 2026-05-06

## Result

The P004 rerun reached an expected human checkpoint during the root review
stage. The Codex root review returned `needs_revision`; the workflow declares
root-review `needs_revision` verdicts as human checkpoints, so downstream
ledger, synthesis, and final-review jobs remained blocked and were not
manually advanced.

Final runner state: `running`

Checkpoint blocker: `blk_7bf5cc384502409384c3ad1f29540343`

Checkpoint reason: root-review `needs_revision` under the declared
human-checkpoint policy.

## Sessions

- `reviewer-claude-1`: `sess_b6a1bfaaa2d54d4f8129ded107081f0e`
- `reviewer-codex-1`: `sess_ff1e27e694ef4032a770e1dfd0196d43`
- `reviewer-gemini-1`: `sess_534ce77468e244b484a4ce7379fe21ab`

No ledger, synthesis, or final-review sessions were registered because the root
review gate did not unblock those jobs.

## Artifacts

- `workflow.json`
- `RFC_0014_REVIEW_claude.md`: `accept_with_findings`
- `RFC_0014_REVIEW_codex.md`: `needs_revision`
- `RFC_0014_REVIEW_gemini.md`: `accept`
- `RUN_EVIDENCE.md`
- `VALIDATION_NOTES.md`

The following expected downstream artifacts are absent by design because the
workflow blocked before those jobs became claimable:

- `RFC_0014_FINDINGS_LEDGER.md`
- `RFC_0014_SYNTHESIS.md`
- `RFC_0014_FINAL_REVIEW.md`

## Evidence Redaction

Evidence was exported to `RUN_EVIDENCE.md`.

The exported evidence scan found no matches for:

- `.agent_runner/state.sqlite3`
- transcript text
- redaction-test private sentinels
- workflow job titles
- review rationale free text
- root-review checkpoint title labels
- uppercase `Author:`

The export includes structured author identity metadata and lowercase
`author:` bylines, which is the expected byline convention for this runner
revision. Free-text blocker descriptions and verdict rationales were redacted
as `<redacted-free-text>`.

## Runner Findings

- Preflight passed before the run: the full `agent_runner` pytest suite passed
  and the workflow fixture validated.
- `agent_runner status --json --run-id` surfaced the open human checkpoint,
  blocked downstream jobs, non-accepting review verdict, and next actions.
- `agent_runner why blk_7bf5cc384502409384c3ad1f29540343 --json` resolved the
  blocker and linked it to the Codex review verdict, job, session, run, and
  blocked ledger job.
- `agent_runner doctor --run-id` reported `ok: true` with no problems.
- `agent_runner evidence export` produced a commit-ready redacted evidence
  artifact for the honestly blocked run.
- The runner correctly preserved the root-review checkpoint boundary rather
  than allowing ledger, synthesis, or final review to proceed after a
  `needs_revision` root review.

## RFC 0014 Package Findings

The RFC-plus-spec handoff package is not ready for a later implementation
prompt yet. It needs package revision before implementation handoff.

The root reviews converged on these actionable issues:

- Flat legacy marker handling is underspecified. The spec scans per-loop
  operations and legacy roots, but leaves flat legacy post-build markers as
  audit-only provenance even though unresolved flat `blocked` or
  `human_checkpoint` markers may still be gate-relevant.
- The spec's human-checkpoint resolution rule adds behavior beyond RFC 0013 by
  requiring a linked owner-decision report; that new requirement should be
  made explicit in the RFC package or moved to a follow-on amendment.
- The marker private-content exception should be tightened so marker front
  matter and marker bodies remain categorically free of private corpus content.
- The missing-`created_at` ordering rule should be reconciled with the
  fail-closed malformed-front-matter rule.
- Minor implementation-prompt hygiene remains: pin or define `<loop_id>`
  grammar, bind optional `docs/operations/README.md` to redaction rules, clarify
  `loop` front matter versus path `<area>`, and prevent accidental per-loop
  README generation.

Gemini accepted the package; Claude accepted with findings; Codex requested
revision. The runner stopped at the expected human checkpoint.
