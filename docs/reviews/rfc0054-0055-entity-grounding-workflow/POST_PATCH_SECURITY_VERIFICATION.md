# RFC0054/0055 Post-Patch Security Verification

Run: `run_8be1d202659a4fd093998367cf61495d`  
Date: 2026-05-19  
Role: coordinator follow-up

## Security Finding Disposition

- High, broker DB authority: addressed with the CLI seam
  `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL`. Routine provider-backed
  `engram entity-grounding process-approved` runs must set that DSN to a
  restricted broker role. The default connection remains only for local
  development and mocked tests.
- High, Tier 1 review-action downgrade: fixed. Materialized
  `entity_identity_review_actions` now carry the approved query privacy tier.
- Medium, materializer URL filtering: fixed. Materialization skips localhost,
  `.localhost`, loopback, private, link-local, unspecified, multicast, and
  reserved IP result URLs before evidence insertion.
- Medium, normalized "exact" entity query matching: fixed. Both RFC0053 request
  validation and network adapter dispatch now require byte-exact
  `network_grant.search_query == surface_form` for
  `query_text_class="entity_surface_form"`.

## Verification

```text
ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test_rfc0054_0055_integrated" \
  .venv/bin/python -m pytest -q \
  tests/test_entity_grounding_workflow.py \
  tests/test_entity_grounding_materialization.py \
  tests/test_claim_grounding.py \
  tests/test_claim_grounding_network.py \
  tests/test_cli.py \
  -k "entity_grounding or claim_grounding"

78 passed, 39 deselected in 42.70s
```

```text
.venv/bin/python -m ruff check \
  src/engram/entity_grounding_workflow.py \
  src/engram/entity_grounding_materialization.py \
  src/engram/claim_grounding.py \
  src/engram/claim_grounding_network.py \
  src/engram/cli.py \
  tests/test_entity_grounding_workflow.py \
  tests/test_entity_grounding_materialization.py \
  tests/test_claim_grounding.py \
  tests/test_claim_grounding_network.py \
  tests/test_cli.py

All checks passed!
```

```text
.venv/bin/python -m pyright \
  src/engram/entity_grounding_workflow.py \
  src/engram/entity_grounding_materialization.py \
  src/engram/claim_grounding.py \
  src/engram/claim_grounding_runtime.py \
  src/engram/claim_grounding_network.py

0 errors, 0 warnings, 0 informations
```

```text
make e2e-claim-grounding-runtime \
  TEST_DATABASE_URL=postgresql:///engram_test_rfc0054_0055_runtime

98 passed in 97.97s
```

```text
git diff --check

passed
```

## Follow-Up

The local restricted-role provisioning surface landed after this verification:
`make provision-grounding-broker` creates/updates `engram_grounding_broker`,
`make check-grounding-broker` verifies the grants, and
`docs/runbooks/grounding-broker-role.md` documents runtime use.

Deployments that need direct broker login still need password, pg_hba, or
service-file configuration outside the repo. Running `process-approved` without
`ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` remains a development fallback and
does not satisfy the routine network-provider acceptance criterion.
