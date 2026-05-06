# RFC 0014 Dogfood Rerun Validation Notes

Run ID: `run_e1e472612df34abe8f0daef7cf9ffd32`
Branch: `agent-runner/rfc-0014-validation`
Date: 2026-05-06
Rerun slug: `2026-05-06-redaction-rerun`
Workflow: `docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun/workflow.json`

## Outcome

The rerun reached the expected root-review human checkpoint. Claude and Codex
returned `accept_with_findings`; Gemini returned `needs_revision`.

The workflow's `root_review_needs_revision` policy is `human_checkpoint`, so
`agent_runner` opened blocker `blk_d60c6aaecb6146af8a1d89fedbe3a695` and kept
downstream jobs blocked. Per P004, the ledger, synthesis, and final-review jobs
were not advanced manually.

## Sessions

- `sess_694e1067565d40d68b3025000c40fa38` / `reviewer-claude-1`
- `sess_be7b2c092c7144ca82b9351bd65820bf` / `reviewer-codex-1`
- `sess_cd3f271bbe7f4f3abf2bdd7da24aef72` / `reviewer-gemini-1`

## Published Artifacts

- `RFC_0014_REVIEW_claude.md`:
  `accept_with_findings`, artifact `art_230942c0acc440f98f8efe7ffaba8dee`
- `RFC_0014_REVIEW_codex.md`:
  `accept_with_findings`, artifact `art_9733d3aeb56043119db640ee17b3b8b8`
- `RFC_0014_REVIEW_gemini.md`:
  `needs_revision`, artifact `art_7c9fd53775784946957462f17a5c62e3`
- `RUN_EVIDENCE.md`:
  evidence export SHA-256
  `06c01fcaeab505886788c67046ac6f190a19de647dbfa85da373a78bb501751f`

## Absent Artifacts

These expected workflow artifacts are absent because the root-review gate
blocked before they became reachable:

- `RFC_0014_FINDINGS_LEDGER.md`
- `RFC_0014_SYNTHESIS.md`
- `RFC_0014_FINAL_REVIEW.md`

## Runner Evidence

`status --json --run-id run_e1e472612df34abe8f0daef7cf9ffd32` reported:

- jobs: `completed=2`, `waiting_human=1`, `blocked=3`
- no claimable jobs
- open human checkpoint `blk_d60c6aaecb6146af8a1d89fedbe3a695`
- next actions:
  `inspect_blocker`, `export_run_evidence`, `resolve_human_checkpoint`,
  `revise_workflow_cycle`

`why blk_d60c6aaecb6146af8a1d89fedbe3a695 --json` resolved the blocker,
related Gemini verdict, owning job/session, and blocked downstream ledger job.

`doctor --run-id run_e1e472612df34abe8f0daef7cf9ffd32 --json` returned
`ok: true`.

## Redaction Inspection

`RUN_EVIDENCE.md` was inspected for:

- `.agent_runner/state.sqlite3`
- transcript text
- private-looking sentinel strings from the redaction regression test
- unredacted verdict rationale text
- unredacted root-review blocker prose
- workflow job titles from the rerun workflow

No matches were found. Evidence export now uses stable author identity metadata
instead of workflow job titles.

## Runner Validation Findings

The rerun validates the RFC 0014 dogfood recovery fixes for the expected blocked
state:

- `submit-review` published root review artifacts and verdicts in one command.
- `status --json` surfaced the open human checkpoint, blocked downstream jobs,
  non-accepting verdict, and deterministic next actions.
- `why <blocker_id> --json` resolved blocker context.
- `evidence export` produced a committed, redacted artifact with job/artifact
  author identity and without workflow job-title prose.

Residual limitation: the process adapter reports network and repo-scope
constraints as advisory for the model lanes; transcript handling is recorded as
enforced because transcripts are not published.

## RFC 0014 State

RFC 0014 remains a proposal and needs revision before human disposition.
Gemini identified blocking RFC-level issues around unresolved path layout
choices and report/marker separation ambiguity.
