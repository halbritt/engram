# RFC 0054/0055 Adversarial Security Review

Run: `run_8be1d202659a4fd093998367cf61495d`  
Lane: `codex_security`  
Role: reviewer  
Date: 2026-05-19

## Findings

### High: Network-capable materialization still runs with the normal Engram DB connection

RFC 0055 says the network-capable process must not have corpus-reading DB access
and must not read raw corpus tables. The current CLI opens the normal Engram
connection and calls `process_approved_grounding_grants` in-process
(`src/engram/cli.py:1708`-`src/engram/cli.py:1719`). That function selects
sidecar rows and invokes the configured network adapter from the same Python
process (`src/engram/entity_grounding_materialization.py:151`,
`src/engram/entity_grounding_materialization.py:156`,
`src/engram/entity_grounding_materialization.py:197`-`src/engram/entity_grounding_materialization.py:207`).

The adapter receives a minimized payload, which is good, but the process itself
still holds a full Engram DB connection. This does not satisfy the process-level
separation required by RFC 0055 (`docs/rfcs/0055-grounding-evidence-materialization.md:49`,
`docs/rfcs/0055-grounding-evidence-materialization.md:185`). A compromised
adapter, future import-time side effect, or later materializer drift would run
inside the same authority boundary as raw messages, segments, captures, notes,
claims, and beliefs.

Required fix: run `entity-grounding process-approved` through a broker-owned
restricted DB role or separate process/DSN that can read only RFC 0053/0055
sidecars and write dispatch/response/evidence/action rows. Add a regression test
using a restricted role or a connection wrapper that raises on raw corpus table
access before any adapter invocation.

### High: Materialized entity review actions downgrade privacy to Tier 1

Materialized evidence inherits the approved query privacy tier when inserted
(`src/engram/entity_grounding_materialization.py:481`-`src/engram/entity_grounding_materialization.py:482`),
but the follow-on `entity_identity_review_actions` row hard-codes
`privacy_tier` to `1` (`src/engram/entity_grounding_materialization.py:586`).

That action row links an entity id to a grounding evidence id and stores request
and grant metadata (`src/engram/entity_grounding_materialization.py:588`-`src/engram/entity_grounding_materialization.py:596`).
For a Tier 3-5 private entity query, this creates a lower-tier review artifact
that can disclose the existence and grounding state of a private entity through
review queues or audits. The local-hit path correctly uses the candidate privacy
tier (`src/engram/entity_grounding_workflow.py:312`-`src/engram/entity_grounding_workflow.py:314`),
so the materialization path is inconsistent.

Required fix: set review-action `privacy_tier` to the materialized evidence tier
or the approved grant query privacy tier, whichever is stricter. Add a test with
`query_privacy_tier=4` proving both `entity_grounding_evidence` and
`entity_identity_review_actions` remain Tier 4.

### Medium: Materializer accepts provider result URLs that the network adapter would reject

The network adapter rejects localhost/private/reserved result URLs
(`src/engram/claim_grounding_network.py:587`-`src/engram/claim_grounding_network.py:593`),
but the materializer's own URL cleaner only checks `http/https` plus a host
(`src/engram/entity_grounding_materialization.py:739`-`src/engram/entity_grounding_materialization.py:746`).
Because `process_approved_grounding_grants` accepts an injected adapter and
treats provider rows as adversarial input, the materialization boundary should
not rely on adapter-side filtering alone.

Impact: a malicious or buggy adapter can persist `http://127.0.0.1/...`,
RFC1918, link-local, or reserved network URLs as `entity_grounding_evidence`.
Even if this code does not fetch those URLs later, downstream operators or tools
may treat stored grounding evidence as public citation material.

Required fix: apply the same public-result URL policy in the materializer before
inserting evidence. Add poisoned provider tests for localhost, private IP,
link-local, and reserved-host results.

### Medium: Entity-surface "exact" matching is normalized rather than byte-exact

The RFC 0054/0055 security posture repeatedly says the exact approved entity
query is the only string allowed to cross the broker boundary. The generic
request and adapter validation allow case and whitespace-normalized equality
between `surface_form` and `network_grant.search_query`
(`src/engram/claim_grounding.py:990`-`src/engram/claim_grounding.py:995`,
`src/engram/claim_grounding_network.py:515`-`src/engram/claim_grounding_network.py:516`).

RFC 0054's draft worker emits byte-identical values
(`src/engram/entity_grounding_workflow.py:341`,
`src/engram/entity_grounding_workflow.py:353`), so this is not an immediate leak
from that path. The risk is that a hand-authored or future RFC 0053 request can
be approved with a search query that is not literally the reviewed surface. If
"exact" means byte-exact operator approval, the validators are too permissive.

Required fix: for `query_text_class="entity_surface_form"`, require
`search_query == surface_form` before persistence and before adapter dispatch.
Add tests for case-only and whitespace-only mismatches.

## Positive Checks

- RFC 0054 draft workflow imports no network adapter and the focused test blocks
  sockets around draft execution (`tests/test_entity_grounding_workflow.py:279`-`tests/test_entity_grounding_workflow.py:299`).
- Network dispatch payloads exclude `source_refs` and `local_context_capsule`
  before adapter invocation (`tests/test_entity_grounding_materialization.py:65`-`tests/test_entity_grounding_materialization.py:77`).
- Latest approved grant filtering prevents missing, denied, revoked, and expired
  lifecycle rows from invoking the adapter in the intended test coverage
  (`tests/test_entity_grounding_materialization.py:141`-`tests/test_entity_grounding_materialization.py:204`).
- Provider rows are inserted into `entity_grounding_evidence` before the response
  candidate cites them (`src/engram/entity_grounding_materialization.py:225`-`src/engram/entity_grounding_materialization.py:235`).
- Provider rank only orders evidence-backed candidates; it does not write merge,
  alias, split, external-id, claim, belief, or entity mutation rows
  (`src/engram/entity_grounding_materialization.py:513`-`src/engram/entity_grounding_materialization.py:527`,
  `src/engram/entity_grounding_materialization.py:562`-`src/engram/entity_grounding_materialization.py:600`).

## Verification Notes

Inspection used the requested RFCs, implementation files, CLI wiring, and focused
tests. I also attempted:

```sh
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/pytest \
  tests/test_entity_grounding_workflow.py \
  tests/test_entity_grounding_materialization.py \
  tests/test_cli.py -q
```

The combined run ended with `42 passed, 3 failed, 11 errors`. The failures were
not useful security signal: the selected DB fixtures reset the shared
`engram_test` schema in incompatible ways during the combined run, producing
catalog duplicate-type and undefined-table setup errors. I did not edit
implementation files.

## Publish Notes

Striatum lifecycle was available after switching from the stale
`session register` form to `register-session`. Session:
`sess_1e02092f441b4f8f8167c186e2d79214`; job acked under lease
`lease_36465031466f4feeaf688e35743a9ae1`. Publish succeeded as
`art_11a275824a394f568458410bac1c1ad9`, and the job was completed. A later
attempt to republish this publish-note correction failed with `lease is not
active`; the review content above was already present in the published artifact.
