# RFC 0054/0055 Entity Grounding Workflow

This Striatum workflow coordinates the implementation of the entity grounding
batch draft workflow and approved-grant materialization path.

The workflow is intentionally maximum-parallel. Implementation lanes have
disjoint write scopes, review lanes write only review artifacts, and synthesis
converges the work before final verification.

Network-capable behavior remains broker-owned and disabled unless an operator
configures a provider and approves persisted grants. Drafting never opens the
network. Tests must use mocked adapters only.

Useful local commands:

```sh
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . workflow validate --allow-same-model-pairing striatum/rfc-0054-0055-entity-grounding-workflow-2026-05-19/workflow.json
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . workflow plan striatum/rfc-0054-0055-entity-grounding-workflow-2026-05-19/workflow.json
STRIATUM_DAEMON_REQUIRED=0 STRIATUM_TEST_HARNESS=1 striatum --repo . run prepare --workflow striatum/rfc-0054-0055-entity-grounding-workflow-2026-05-19/workflow.json --json
```

