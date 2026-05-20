# RFC 0053 Claim Grounding Boundary Review Runbook

Date: 2026-05-18
Workflow: `striatum/rfc-0053-claim-grounding-boundary-review-2026-05-18/workflow.json`

This workflow drives RFC 0053 through six independent review lanes, a findings
ledger, synthesis, accepted-delta application, and final review.

## Commands

```sh
STRIATUM_TEST_HARNESS=1 STRIATUM_DAEMON_REQUIRED=0 \
  striatum --repo . workflow validate --allow-same-model-pairing \
  striatum/rfc-0053-claim-grounding-boundary-review-2026-05-18/workflow.json

STRIATUM_TEST_HARNESS=1 STRIATUM_DAEMON_REQUIRED=0 \
  striatum --repo . run prepare --workflow \
  striatum/rfc-0053-claim-grounding-boundary-review-2026-05-18/workflow.json
```

Status should be scoped to the returned run id because older runs can remain in
the shared Striatum state:

```sh
STRIATUM_TEST_HARNESS=1 STRIATUM_DAEMON_REQUIRED=0 \
  striatum --repo . status --run-id <run_id> --json
```

The first wave is intentionally maximally parallel for this repo state:

- privacy/query boundary;
- network/security;
- schema/contract;
- runtime/integration;
- product/MCP surface;
- eval gate.

The lanes may be run by Codex subagents and published with an explicit
`publish-artifact --allow-no-process-execution` override. In that case the
artifact body must identify the actual Codex subagent lane and must not claim a
Claude/Gemini byline.
