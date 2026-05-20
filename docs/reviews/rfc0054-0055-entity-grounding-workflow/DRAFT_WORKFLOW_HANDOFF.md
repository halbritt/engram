Lane: codex_draft
Role: implementer

# RFC 0054 Draft Workflow Handoff

## Summary

Implemented the draft-only RFC 0054 entity grounding workflow in
`src/engram/entity_grounding_workflow.py`.

The worker:

- selects active `entity_kind='unknown'` entities by scoped tenant/corpus and
  deterministic ordering: `privacy_tier ASC`, `confidence DESC`,
  `created_at ASC`, `id ASC`;
- calls `search_grounding_evidence` before drafting any network-capable sidecar;
- attaches local hits through append-only
  `entity_identity_review_actions.action_kind='grounding_evidence_attach'`;
- creates no RFC 0053 request/grant rows for local hits;
- creates deterministic RFC 0053 request ids and draft grant ids for local
  misses;
- uses `entities.source_claim_ids` as opaque `claims` source refs and never
  invents `target_table='entities'`;
- encodes entity linkage in deterministic `extraction_run_id` values and grant
  audit payload metadata;
- keeps raw corpus text, claim text, message text, segment text, capture text,
  and context snippets out of request/grant/action payloads;
- does not import or instantiate network adapters.

## Changed Files

- `src/engram/entity_grounding_workflow.py`
- `tests/test_entity_grounding_workflow.py`
- `docs/reviews/rfc0054-0055-entity-grounding-workflow/DRAFT_WORKFLOW_HANDOFF.md`

## Verification

Focused checks run:

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/pytest tests/test_entity_grounding_workflow.py -q`
  - result: `5 passed in 0.85s`
- `.venv/bin/python -m py_compile src/engram/entity_grounding_workflow.py tests/test_entity_grounding_workflow.py`
  - result: passed

## Known Gaps

- No CLI wiring was added because `src/engram/cli.py` is outside this lane's
  write scope.
- The focused DB tests use a minimal PostgreSQL schema for the workflow-owned
  tables. The shared full-migration test reset path was unstable in this
  workspace due a leftover `schema_migrations` composite type; avoiding a
  broad fixture refactor kept the lane inside its write scope.
- Full-suite and adjacent runtime tests were not run in this lane.

## Coordinator Follow-Up

After lane completion, coordinator integration added CLI-compatible `entity_id`
filtering to `draft_entity_grounding_batch`. The focused worker/materializer
suite now passes together:

```text
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -q tests/test_entity_grounding_workflow.py tests/test_entity_grounding_materialization.py
13 passed
```
