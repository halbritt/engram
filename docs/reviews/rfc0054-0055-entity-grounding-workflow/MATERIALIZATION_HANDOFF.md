Lane: codex_materialization
Role: implementer

# RFC0055 Materialization Handoff

## Scope

Implemented the approved-grant processor in
`src/engram/entity_grounding_materialization.py` and focused DB coverage in
`tests/test_entity_grounding_materialization.py`.

## Implementation

- Consumes only latest approved persisted grant lifecycle rows for the requested
  tenant/corpus/target, excluding grants whose latest row is denied, revoked, or
  expired and excluding approvals past `expires_at`.
- Verifies the persisted grant via `verify_claim_grounding_grant_for_dispatch`
  before invoking the adapter.
- Records an append-only `prepared` dispatch audit row before provider I/O and
  an append-only terminal `succeeded` or `failed` dispatch row after provider
  completion. The existing dispatch helper allocates a new attempt number for
  each append-only row.
- Calls only `raw_result_rows()` on an injected/configured
  `ClaimGroundingConfiguredSearchAdapter`; tests use a mock adapter and no live
  network.
- Sanitizes and materializes provider rows into `entity_grounding_evidence`
  before writing `claim_grounding.response.v1`.
- Builds response candidates that cite local `entity_grounding_evidence.id`
  values, not provider row ids, and records response-to-evidence links.
- Reuses existing local evidence rows for duplicate provider rows by
  tenant/corpus/query/content hash/source URL.
- Appends only `entity_identity_review_actions.action_kind =
  'grounding_evidence_attach'` when persisted request payloads include an
  entity id. No alias, external-id, merge, split, or not-same action is emitted.
- Provider failure handling stores sanitized error codes based on exception
  class names only, avoiding provider secrets/private text in dispatch metadata,
  response omissions, and returned summaries.

## Verification

Focused tests run:

```text
ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test" ./.venv/bin/python -m pytest tests/test_entity_grounding_materialization.py -q
8 passed in 17.00s
```

Adjacent checks run during implementation:

```text
./.venv/bin/python -m ruff check src/engram/entity_grounding_materialization.py tests/test_entity_grounding_materialization.py
All checks passed!

ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test" ./.venv/bin/python -m pytest tests/test_claim_grounding_runtime.py -q
8 passed in 15.57s

./.venv/bin/python -m pytest tests/test_claim_grounding_network.py -q
18 passed in 0.04s

./.venv/bin/python -m py_compile src/engram/entity_grounding_materialization.py tests/test_entity_grounding_materialization.py
passed
```

One intermediate rerun of the focused DB tests hit a transient
`public.schema_migrations` type residue during fixture setup after parallel test
activity. A direct focused rerun passed cleanly.

## Known Gaps

- No CLI command was wired because `src/engram/cli.py` is outside this lane's
  write scope.
- Terminal dispatch auditing uses a second append-only dispatch row because the
  existing helper and schema do not support mutating a prepared row in place.
- Request-to-entity discovery is intentionally narrow: it reads `entity_id`,
  `entity_ids`, or entity-shaped `source_refs` from persisted request payload
  JSON. The current RFC0053 request validator still does not admit
  `source_refs.target_table = 'entities'`.

## Coordinator Follow-Up

After lane completion, coordinator integration added JSON-safe summary methods
for CLI output and grant-payload entity-id discovery for draft-created grants.
The focused worker/materializer suite now passes together:

```text
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -q tests/test_entity_grounding_workflow.py tests/test_entity_grounding_materialization.py
13 passed
```
