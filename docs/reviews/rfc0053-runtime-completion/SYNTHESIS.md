# RFC 0053 Runtime Completion Synthesis

author: operator [self-declared: codex-synthesis]

## Accepted Deltas

The runtime-completion slice accepts all six first-wave lanes:

- Grant lifecycle rows are append-only, and dispatch audit now verifies the
  latest persisted grant is approved, live, unexpired, target-authorized, and
  bound to the request/query/privacy lineage.
- The network adapter is a disabled-by-default configured HTTP search scaffold,
  not ambient network access. It uses fixed GET dispatch, bounded reads, and
  private-address result filtering.
- Broker credential separation has a PostgreSQL role regression proving raw
  corpus tables are unreadable to a broker-shaped role.
- Extraction integration is sidecar-only and disabled by default. It emits
  request/link sidecars from accepted claim drafts without changing claim
  content or passing raw segment/message text.
- The product surface is CLI-first: exact grant display plus draft, approve,
  deny, and revoke lifecycle rows. It performs no network IO.
- Docs and gates now describe the scaffold as partial and proposal-level, with
  no default live provider and no extractor network access.

## Verification

- `make e2e-claim-grounding-runtime` passed: 66 tests.
- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -q tests/test_cli.py -k claim_grounding` passed: 2 tests.
- `.venv/bin/python -m ruff check src/engram/claim_grounding_integration.py src/engram/claim_grounding_network.py src/engram/extractor.py src/engram/cli.py tests/test_claim_grounding_integration.py tests/test_claim_grounding_network.py tests/test_claim_grounding_security.py tests/test_cli.py` passed.
- `.venv/bin/python -m pyright src/engram/claim_grounding_integration.py src/engram/claim_grounding_network.py src/engram/extractor.py` passed with 0 errors.
- `.venv/bin/striatum --repo . workflow validate --allow-same-model-pairing striatum/rfc-0053-runtime-completion-2026-05-18/workflow.json` passed.
- `git diff --check` passed.

## Residual Risks

- Network search is scaffolded but not a shipped default provider. An operator
  still needs to configure/inject the adapter and accept provider-specific
  operational policy.
- Network result rows are sanitized into response-shaped candidates, but
  production use still needs durable materialization into local grounding
  evidence before extraction can depend on those results.
- The CLI grant lifecycle is usable but minimal; a richer review UI remains
  future work.
- The broker credential test proves the intended DB privilege shape in local
  PostgreSQL, but production packaging for a long-running broker role remains
  to be specified.
- RFC 0053 remains proposal-only. Grounding still must prove eval/extraction
  quality lift before it is allowed to affect claim content.
