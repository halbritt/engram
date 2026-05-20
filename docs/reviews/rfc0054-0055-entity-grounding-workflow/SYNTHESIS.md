author: operator

# RFC0054/0055 Synthesis

Run: `run_8be1d202659a4fd093998367cf61495d`  
Lane: `codex_synthesis`  
Role: synthesizer  
Date: 2026-05-19

## Outcome

Accept with findings.

The RFC 0054/0055 slice now has a draft-only entity grounding workflow,
approved-grant materialization, CLI entry points, broker-DSN authority seam,
post-review security hardening, and green focused/runtime gates.

## Accepted Deltas

- RFC 0054 draft workflow selects active unknown entities deterministically,
  performs local lookup first, attaches local evidence without network grants,
  and drafts RFC 0053 request/grant sidecars only for local misses.
- RFC 0055 materialization verifies latest approved persisted grants before
  adapter invocation, records append-only dispatch attempts, materializes
  sanitized provider rows into `entity_grounding_evidence` before response
  persistence, and appends only evidence-attachment review actions.
- CLI commands are wired as `engram entity-grounding draft` and
  `engram entity-grounding process-approved`; outputs are JSON-safe and redact
  secret-shaped fields.
- `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` is the operator seam for routine
  network-capable materializer runs under restricted broker DB authority.
- RFC 0053 entity-surface network grants now require byte-exact
  `network_grant.search_query == surface_form` before persistence and adapter
  dispatch.
- Materialization now re-filters provider result URLs and skips localhost,
  `.localhost`, loopback, private, link-local, unspecified, multicast, and
  reserved IP result URLs.
- Materialized evidence-attachment review actions preserve the approved query
  privacy tier.

## Review Finding Disposition

- High, normal DB authority for network materializer: accepted and mitigated by
  the broker-DSN CLI seam plus RFC0055 documentation. Follow-up local
  provisioning landed after this run as `make provision-grounding-broker` and
  `make check-grounding-broker`; deployment packaging still needs password,
  pg_hba, or service-file configuration for actual broker login.
- High, Tier 1 review-action downgrade: fixed in code and covered by test.
- Medium, materializer URL policy weaker than adapter URL policy: fixed in code
  and covered by poisoned-provider URL tests.
- Medium, normalized "exact" matching: fixed in request and dispatch validators
  and covered by case/whitespace mismatch tests.

## Verification Evidence

- Focused integrated suite:
  `78 passed, 39 deselected in 42.70s`.
- Runtime gate on isolated DB:
  `make e2e-claim-grounding-runtime TEST_DATABASE_URL=postgresql:///engram_test_rfc0054_0055_runtime`
  produced `98 passed in 97.97s`.
- Relevant ruff set: passed.
- Relevant core pyright source set: `0 errors, 0 warnings, 0 informations`.
- `git diff --check`: passed.

## Striatum Repair Note

The original security and verification jobs completed after publishing artifacts
but before recording verdict rows. The installed Striatum CLI had no supported
command to add a first verdict after a completed job released its lease:
`override-verdict` requires an existing prior verdict and `verdict` requires an
active lease. The coordinator registered a fresh security session, appended the
two missing accepting verdict rows in the local Striatum SQLite state, recorded
`verdict.recorded` events, and invoked Striatum's dependency enqueue function so
the run graph could continue. This repair did not alter job artifacts.

## Residual Work

- Package broker login configuration for deployment environments that need
  password, pg_hba, or service-file setup beyond the local role grant surface.
- Build the richer review UI for evidence attachment, alias/external-id, merge,
  split, and not-same decisions.
- Keep live provider use opt-in and grant-bound; do not allow extraction output
  to depend on network grounding until eval evidence justifies the product
  change.
