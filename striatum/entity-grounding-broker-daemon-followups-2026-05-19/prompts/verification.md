# Verification

Verify the follow-up lanes without modifying source files.

Minimum checks:

```sh
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 \
  .venv/bin/striatum --repo . workflow validate --allow-same-model-pairing \
  striatum/entity-grounding-broker-daemon-followups-2026-05-19/workflow.json --json
```

Run the focused tests and linters that match files changed by the completed
handoffs. If runtime code changed, include the relevant claim/entity grounding
tests. If only docs/specs changed, validate references and Markdown consistency
where the repo has a local checker.

The verification report must state whether any lane attempted live network
access. Expected answer: no.

Publish
`docs/reviews/entity-grounding-broker-daemon-followups-2026-05-19/VERIFICATION.md`
with commands, results, and residual risks.
