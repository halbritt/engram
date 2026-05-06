# Agent Runner Validation Notes

Run ID: `run_2970e12484aa4320a85084cb45e6e880`
Branch: `agent-runner/rfc-0014-validation`
Date: 2026-05-06
Workflow: `agent-runner/examples/rfc-0014-operational-artifact-home/workflow.json`

## Outcome

The dogfood run reached an honest runner-level block during the independent
review stage. The Codex review job returned `needs_revision`, and the workflow
declares no `needs_revision` cycle from `review_codex`. `agent_runner` recorded
the review verdict and opened human checkpoint
`blk_2bb7128d76674eb58d8245f7357fb225` with description:
`needs_revision verdict has no matching workflow cycle`.

Per the workflow discipline, downstream ledger, synthesis, and final-review
jobs were not manually advanced.

## Runner Findings

1. `status --json` did not surface the open blocker or next useful action.
   It reported only aggregate job counts and left the run in `running`, which
   is technically accurate but not enough for coordinator recovery.

2. `why` could explain the blocked review job, but `why
   blk_2bb7128d76674eb58d8245f7357fb225 --json` failed because blocker IDs are
   not supported introspection targets.

3. The recommended prompt command used `python`, but this environment has only
   `python3` on PATH. The runner worked with `PYTHONPATH=src python3 -m
   agent_runner.cli ...`. The exact system-python pytest check also failed
   because `pytest` is not installed for `/usr/bin/python3`; the project
   virtualenv check `./.venv/bin/python -m pytest -q` passed.

4. The first external Codex CLI review lane attempted web searches despite a
   local-only review task. The process was stopped and replaced with a fresh
   in-process Codex worker constrained to local files. This exposed a missing
   runner/process-adapter control: the workflow can describe local-only scope,
   but the MVP did not enforce tool or network restrictions for launched lanes.

5. Artifact publication worked, but required manual command plumbing:
   publish each artifact, capture its artifact ID, then pass that ID into the
   verdict command. The work packet provided command skeletons but not a
   copy-paste-complete sequence for the common publish-and-verdict path.

6. Branch behavior matched the prompt caveat: the coordinator had to run
   `git switch` manually, then record branch confirmation with
   `agent_runner branch confirm`.

7. The run validated the SQLite control plane, artifact publication, and verdict
   routing. It did not validate autonomous process/tmux adapter launch behavior;
   model lanes were invoked manually by the coordinator.

## RFC 0014 State

The review artifacts exist and are published in runner state:

- `docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_REVIEW_claude.md`
- `docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_REVIEW_codex.md`
- `docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_REVIEW_gemini.md`

No runner-produced findings ledger, synthesis, or final review was produced
because the root review gate blocked before downstream jobs became claimable.
After the human follow-up, a manual post-block findings ledger was recorded at
`docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_FINDINGS_LEDGER.md`;
it is not published through the blocked runner workflow.

## Verification

- `PYTHONPATH=src python3 -m pytest -q`: failed before tests ran,
  `/usr/bin/python3: No module named pytest`.
- `./.venv/bin/python -m pytest -q`: passed, 18 tests.
- `PYTHONPATH=src python3 -m agent_runner.cli --repo .. status --json`:
  runner reachable; run remains `running` with two completed review jobs, one
  waiting-human review job, and three blocked downstream jobs.
- `PYTHONPATH=src python3 -m agent_runner.cli --repo .. doctor --json`: passed
  with `ok: true`, schema version `1`, and no reported problems.
