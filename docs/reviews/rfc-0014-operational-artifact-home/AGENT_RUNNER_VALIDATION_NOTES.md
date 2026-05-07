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

## Durable Runner-State Evidence

The live runner state remains ignored under `.agent_runner/` and is not
committed. The following redacted snapshot records the runner evidence needed to
audit this validation from a fresh checkout without the SQLite database.

### Command Outputs

`PYTHONPATH=src python3 -m agent_runner.cli --repo .. status --json`

```json
{"data":{"jobs":{"blocked":3,"completed":2,"waiting_human":1},"runs":[{"branch_name":"agent-runner/rfc-0014-validation","run_id":"run_2970e12484aa4320a85084cb45e6e880","state":"running"}]},"ok":true}
```

`PYTHONPATH=src python3 -m agent_runner.cli --repo .. doctor --json`

```json
{"data":{"ok":true,"problems":[],"schema_version":"1"},"ok":true}
```

Failed blocker introspection command:
`PYTHONPATH=src python3 -m agent_runner.cli --repo .. why blk_2bb7128d76674eb58d8245f7357fb225 --json`

```json
{"error":{"code":3,"message":"target id is not a known job or message"},"ok":false}
```

### Runner IDs And States

Run:

```json
{
  "run_id": "run_2970e12484aa4320a85084cb45e6e880",
  "branch_name": "agent-runner/rfc-0014-validation",
  "state": "running"
}
```

Review jobs and verdicts:

```json
[
  {
    "workflow_job_id": "review_claude",
    "job_id": "job_run_2970e12484aa4320a85084cb45e6e880_review_claude",
    "state": "completed",
    "lane": "claude",
    "artifact_id": "art_edf0900d4ddc4353a6ed6db551570669",
    "verdict_id": "verdict_a5315936b825460ea32f5b36007ccd88",
    "verdict": "accept_with_findings"
  },
  {
    "workflow_job_id": "review_gemini",
    "job_id": "job_run_2970e12484aa4320a85084cb45e6e880_review_gemini",
    "state": "completed",
    "lane": "gemini",
    "artifact_id": "art_87c126ade8c747309a7b31ba13a28b88",
    "verdict_id": "verdict_ac79b9bd32904c22a78b001bac2e5c0a",
    "verdict": "accept_with_findings"
  },
  {
    "workflow_job_id": "review_codex",
    "job_id": "job_run_2970e12484aa4320a85084cb45e6e880_review_codex",
    "state": "waiting_human",
    "lane": "codex",
    "artifact_id": "art_a10b681f211a49da82473cda9f1efe96",
    "verdict_id": "verdict_c393dbe3f6394895ac6989dfc3baf80c",
    "verdict": "needs_revision",
    "blocker_id": "blk_2bb7128d76674eb58d8245f7357fb225"
  }
]
```

Human checkpoint:

```json
{
  "blocker_id": "blk_2bb7128d76674eb58d8245f7357fb225",
  "job_id": "job_run_2970e12484aa4320a85084cb45e6e880_review_codex",
  "severity": "human_checkpoint",
  "blocker_kind": "revision_routing",
  "state": "open",
  "description": "needs_revision verdict has no matching workflow cycle"
}
```

Downstream jobs that did not become runner-completed:

```json
[
  {
    "workflow_job_id": "findings_ledger",
    "job_id": "job_run_2970e12484aa4320a85084cb45e6e880_findings_ledger",
    "job_type": "ledger",
    "lane": "codex",
    "state": "blocked"
  },
  {
    "workflow_job_id": "synthesis",
    "job_id": "job_run_2970e12484aa4320a85084cb45e6e880_synthesis",
    "job_type": "synthesis",
    "lane": "claude",
    "state": "blocked"
  },
  {
    "workflow_job_id": "final_review",
    "job_id": "job_run_2970e12484aa4320a85084cb45e6e880_final_review",
    "job_type": "review",
    "lane": "codex",
    "state": "blocked"
  }
]
```

Published review artifacts recorded by runner state:

```json
[
  {
    "artifact_id": "art_edf0900d4ddc4353a6ed6db551570669",
    "job_id": "job_run_2970e12484aa4320a85084cb45e6e880_review_claude",
    "artifact_kind": "finding",
    "logical_name": "review",
    "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_REVIEW_claude.md",
    "runner_content_sha256": "787528353abf262b9da66c64b8bb09f037ab30ee67dc4fd00c0db84e6397eef2"
  },
  {
    "artifact_id": "art_a10b681f211a49da82473cda9f1efe96",
    "job_id": "job_run_2970e12484aa4320a85084cb45e6e880_review_codex",
    "artifact_kind": "finding",
    "logical_name": "review",
    "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_REVIEW_codex.md",
    "runner_content_sha256": "5ac48595ac825ef9016d46afabd919089fe1ad2d5bfde5541b684049984a59be",
    "current_file_sha256_after_whitespace_cleanup": "7f48529632c17db3f039fba26673e30a45e54f3d843349b0fbe71e2fe371ce93"
  },
  {
    "artifact_id": "art_87c126ade8c747309a7b31ba13a28b88",
    "job_id": "job_run_2970e12484aa4320a85084cb45e6e880_review_gemini",
    "artifact_kind": "finding",
    "logical_name": "review",
    "repo_path": "docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_REVIEW_gemini.md",
    "runner_content_sha256": "45537567c952691346dfec62576d27069255dc8331305bbc913565b0b531fd09"
  }
]
```

The Codex artifact hash changed after publication because a later docs-only
cleanup stripped Markdown trailing spaces. The runner ID, verdict, job state,
and committed review content remain durable; the stored runner hash is retained
here as historical state evidence rather than as a current-file hash.

## Runner Findings

Follow-up product fixes are specified in
`agent-runner/docs/RFC_0014_DOGFOOD_FIX_SPEC.md`.

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
- `PYTHONPATH=src ./.venv/bin/python -m pytest -q`: passed, 18 tests.
- `PYTHONPATH=src python3 -m agent_runner.cli --repo .. status --json`:
  runner reachable; run remains `running` with two completed review jobs, one
  waiting-human review job, and three blocked downstream jobs.
- `PYTHONPATH=src python3 -m agent_runner.cli --repo .. doctor --json`: passed
  with `ok: true`, schema version `1`, and no reported problems.
