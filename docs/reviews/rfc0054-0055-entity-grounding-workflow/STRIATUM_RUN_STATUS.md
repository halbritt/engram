# Striatum Run Status: RFC 0054/0055 Entity Grounding Workflow

Run: `run_8be1d202659a4fd093998367cf61495d`  
Checked: 2026-05-19

## Current Striatum State

Use the repo-local Striatum workflow mode documented in `docs/AGENT_CONTEXT_NOTES.md`:

```sh
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . status --run-id run_8be1d202659a4fd093998367cf61495d --json
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . run graph --run-id run_8be1d202659a4fd093998367cf61495d --format ascii
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . doctor --json
```

Observed graph:

```text
cli_docs, draft_workflow, materialization -> adversarial_security_review, verification -> synthesis -> final_review
```

Completed jobs:

- `job_run_8be1d202659a4fd093998367cf61495d_draft_workflow`
- `job_run_8be1d202659a4fd093998367cf61495d_materialization`
- `job_run_8be1d202659a4fd093998367cf61495d_cli_docs`
- `job_run_8be1d202659a4fd093998367cf61495d_adversarial_security_review`
- `job_run_8be1d202659a4fd093998367cf61495d_verification`

Blocked jobs:

- `job_run_8be1d202659a4fd093998367cf61495d_synthesis`
- `job_run_8be1d202659a4fd093998367cf61495d_final_review`

`claimable_jobs` is currently empty. `doctor` reports the real run blocker:

- completed review dependency lacks accepting verdict:
  `adversarial_security_review -> synthesis`
- completed review dependency lacks accepting verdict:
  `verification -> synthesis`

This happened because review artifacts were published and jobs completed before
their verdicts were recorded. No Striatum verdict rows are currently recorded.

## Published Artifacts

- `art_6d8a2c0ff5714f5887a3a5c8fd1bc30d`:
  `docs/reviews/rfc0054-0055-entity-grounding-workflow/DRAFT_WORKFLOW_HANDOFF.md`
- `art_4efe90dc4bf343f5a17390f7fe8aec92`:
  `docs/reviews/rfc0054-0055-entity-grounding-workflow/MATERIALIZATION_HANDOFF.md`
- `art_863def12767f453393a7e0282a2d0238`:
  `docs/reviews/rfc0054-0055-entity-grounding-workflow/CLI_DOCS_HANDOFF.md`
- `art_11a275824a394f568458410bac1c1ad9`:
  `docs/reviews/rfc0054-0055-entity-grounding-workflow/ADVERSARIAL_SECURITY_REVIEW.md`
- `art_1782833c7f46491e961411937dd63f90`:
  `docs/reviews/rfc0054-0055-entity-grounding-workflow/VERIFICATION.md`

## Do Not Proceed Yet

Do not override the missing verdicts while the security review findings are
still live. `ADVERSARIAL_SECURITY_REVIEW.md` records two high findings:

- network-capable materialization still runs with the normal Engram DB
  connection;
- materialized entity review actions downgrade privacy to Tier 1.

It also records two medium findings:

- materializer URL policy is weaker than adapter URL policy;
- entity-surface exact matching accepts normalized rather than byte-exact
  matches.

`BROKER_AUTHORITY_HANDOFF.md` appeared during this inspection and records a
post-review patch for the broker-DSN seam. Treat it as follow-up evidence for
the first high finding, but not as a Striatum-published artifact for this run.
The run state is unchanged: synthesis is still blocked on the missing accepting
verdicts for `adversarial_security_review` and `verification`.

Synthesis should wait until the implementation/security patches for all intended
security findings land and fresh verification evidence says whether each
security finding is fixed, downgraded, or still blocking.

## Exact Unblock Procedure After Patches Land

1. Re-check run state:

```sh
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . status --run-id run_8be1d202659a4fd093998367cf61495d --json
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . run graph --run-id run_8be1d202659a4fd093998367cf61495d --format ascii
```

2. Confirm the post-patch evidence exists in the review artifacts or a clearly
   dated follow-up note under this review directory. At minimum, rerun focused
   security/verification checks for the patched areas.

3. If the security blockers are fixed or explicitly accepted as non-blocking,
   record the missing accepting verdicts with operator overrides:

```sh
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . override-verdict \
  --session-id sess_1e02092f441b4f8f8167c186e2d79214 \
  --job-id job_run_8be1d202659a4fd093998367cf61495d_adversarial_security_review \
  --verdict accept_with_findings \
  --findings-artifact-id art_11a275824a394f568458410bac1c1ad9 \
  --rationale "Post-patch operator override: security review artifact completed before verdict submission; patched blockers have fresh follow-up evidence and remaining findings are synthesis inputs." \
  --json

STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . override-verdict \
  --session-id sess_3aa3648e67364b8b95746dd268f7958a \
  --job-id job_run_8be1d202659a4fd093998367cf61495d_verification \
  --verdict accept_with_findings \
  --findings-artifact-id art_1782833c7f46491e961411937dd63f90 \
  --rationale "Post-patch operator override: verification artifact completed before verdict submission; focused post-patch checks passed or residual risks are documented for synthesis." \
  --json
```

4. Confirm `synthesis` becomes claimable:

```sh
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . status --run-id run_8be1d202659a4fd093998367cf61495d --json
```

5. Claim and run synthesis:

```sh
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . register-session \
  --run-id run_8be1d202659a4fd093998367cf61495d \
  --lane codex_synthesis \
  --role synthesizer \
  --capability synthesis \
  --fresh \
  --json

STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . claim-next \
  --session-id <synthesis-session-id> \
  --lease-seconds 3600 \
  --json
```

Write only:

```text
docs/reviews/rfc0054-0055-entity-grounding-workflow/SYNTHESIS.md
```

Then submit the synthesis with a verdict using the job id and lease id returned
by `claim-next`:

```sh
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . submit-review \
  --session-id <synthesis-session-id> \
  --job-id job_run_8be1d202659a4fd093998367cf61495d_synthesis \
  --lease-id <synthesis-lease-id> \
  --path docs/reviews/rfc0054-0055-entity-grounding-workflow/SYNTHESIS.md \
  --logical-name synthesis \
  --kind finding \
  --verdict accept_with_findings \
  --rationale "Synthesis complete; accepted deltas, required fixes, deferred work, and verification evidence are recorded." \
  --json
```

6. Claim and run final review from a fresh final-review session:

```sh
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . register-session \
  --run-id run_8be1d202659a4fd093998367cf61495d \
  --lane codex_final \
  --role reviewer \
  --capability review \
  --fresh \
  --json

STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . claim-next \
  --session-id <final-session-id> \
  --lease-seconds 3600 \
  --json
```

Write only:

```text
docs/reviews/rfc0054-0055-entity-grounding-workflow/FINAL_REVIEW.md
```

Submit `accept` only if no blocking bugs/security issues remain; otherwise use
`needs_revision` to exercise the configured one-shot cycle back to
`draft_workflow` and/or `materialization`:

```sh
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . submit-review \
  --session-id <final-session-id> \
  --job-id job_run_8be1d202659a4fd093998367cf61495d_final_review \
  --lease-id <final-lease-id> \
  --path docs/reviews/rfc0054-0055-entity-grounding-workflow/FINAL_REVIEW.md \
  --logical-name final_review \
  --kind finding \
  --verdict accept \
  --rationale "Final review found no remaining blocking issues." \
  --json
```

## Operational Notes

- Do not edit implementation files from this coordination lane.
- Do not use `run retry-job` for the completed security/verification jobs;
  Striatum only retries `failed`, `canceled`, or `blocked` jobs. These reviews
  are `completed`, so the appropriate repair is `override-verdict` after
  post-patch evidence exists.
- The prepared run graph in Striatum state is authoritative for this run.
- `striatum run summary --path ...` writes a repo-relative file; avoid pointing
  it at any source/workflow file.
