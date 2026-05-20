<a id="rfc-0055"></a>
# RFC 0055: Grounding Evidence Materialization

| Field | Value |
|-------|-------|
| RFC | 0055 |
| Title | Grounding Evidence Materialization |
| Status | proposal |
| Implementation | implemented: materializer, broker-DSN CLI seam, local broker-daemon workflow, and runtime gate coverage present |
| Date | 2026-05-19 |
| Context | D020; D090; D095; RFC 0052; RFC 0053; RFC 0054; `src/engram/claim_grounding_broker.py`; `src/engram/claim_grounding_network.py`; `src/engram/claim_grounding_runtime.py`; `migrations/023_entity_grounding_review.sql`; `migrations/024_claim_grounding_runtime.sql` |

Decision refs:
  - [D020](../../DECISION_LOG.md#d020)
  - [D090](../../DECISION_LOG.md#d090)
  - [D095](../../DECISION_LOG.md#d095)

## Summary

This RFC defines the approved-grant processor that turns network search results
into append-only local grounding evidence. It is the runtime complement to RFC
0054. The core invariant is:

```text
approved grant -> minimized dispatch -> provider rows -> entity_grounding_evidence
              -> claim_grounding.response.v1 with local evidence ids
              -> optional entity_identity_review_actions
```

A network provider response must not be returned to extraction, entity review,
or any LLM agent as an authoritative candidate until the fetched material has
been stored locally as immutable grounding evidence.

## Goals

- Process latest-approved RFC 0053 grants in a separate broker-owned command.
- Verify the persisted grant before every network dispatch.
- Call only configured fixed target adapters.
- Materialize sanitized provider rows into `entity_grounding_evidence`.
- Return or persist `claim_grounding.response.v1` candidates that cite real
  local evidence row ids.
- Append review-action rows only as pending/evidence-attached facts, not as
  automatic identity merges.
- Keep provider secrets out of DB rows, logs, response payloads, and audit
  artifacts.

## Non-Goals

- No corpus-reading DB access in the network-capable process.
- No arbitrary URL fetch.
- No model-selected provider, method, headers, cookies, or retry behavior.
- No automatic claim/belief/entity mutation based on provider rank.
- No remote grounding LLM in this slice.
- No use of provider snippets as instructions.

## Authority Boundary

The approved-grant processor is a broker-authority process, not a normal Engram
operator process. Routine network-capable runs must connect with a restricted
database role that can read only the RFC 0053/0055 sidecars needed for dispatch
verification and can write only dispatch audits, materialized grounding evidence,
grounding responses, response/evidence links, and evidence-attachment review
actions.

The CLI seam is `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL`. When that
environment variable is set, `engram entity-grounding process-approved` opens
the materializer connection with that DSN. When it is absent, the command keeps
the historical default Engram connection behavior for local development,
tests, and backward compatibility; that fallback does not satisfy the routine
network-provider acceptance criterion. `engram entity-grounding broker-daemon`
is stricter: it refuses to start unless the broker DSN is set.

## Processor Input

The processor consumes persisted rows from the RFC 0053 sidecars:

- `claim_grounding_requests`;
- latest matching `claim_grounding_grants` with `grant_status='approved'`;
- no later `denied` or `revoked` lifecycle row for the same grant id;
- not expired at verification time;
- target set includes the configured adapter target, initially
  `internet_search`.

The processor may filter by:

- tenant/corpus;
- request id;
- grant id;
- limit;
- target adapter;
- provider name.

## Network Dispatch

For each approved grant:

1. Validate the original request.
2. Verify the persisted grant through `verify_claim_grounding_grant_for_dispatch`.
3. Build `claim_grounding.network_dispatch.v1`.
4. Record a dispatch attempt before provider I/O.
5. Invoke the configured adapter with only the minimized dispatch payload.
6. Capture provider status, byte count, result count, and sanitized failure
   reason in append-only audit metadata.

The dispatch payload must not include `source_refs`, local context capsules,
extraction prompt metadata, raw claim text, raw belief text, segment text,
message text, captures, or provider secrets.

## Materialization Contract

The adapter should expose sanitized result rows with:

- stable row id/hash;
- title;
- public URL;
- source label;
- excerpt;
- content hash;
- rank;
- provider/version metadata.

Provider rows are adversarial input. The processor must apply its own
public-result URL policy before insertion and must not rely only on adapter-side
filtering. Localhost, `.localhost`, loopback, private, link-local, unspecified,
multicast, and reserved IP result URLs are skipped during materialization.

The processor inserts each accepted row into `entity_grounding_evidence`:

```text
query_text = approved search_query
entity_kind = unknown until reviewed/classified
source_url = public result URL
source_label = sanitized source label
content_hash = hash over sanitized public row fields
content_excerpt = sanitized excerpt
fetched_at = processor timestamp
fetch_tool_version = provider adapter version
extractor_version = none
privacy_tier = query_privacy_tier
sensitivity_class = policy-derived default or request ceiling
raw_payload = bounded provider/result metadata without secrets
```

Review actions emitted from materialized evidence carry the approved query
privacy tier so a private entity query cannot create lower-tier review/audit
artifacts.

Deduplication is by tenant/corpus/query/content hash/source URL. Because
`entity_grounding_evidence` is append-only, duplicate suppression should happen
before insert by reusing existing rows rather than updating them.

## Response Contract

After materialization, the processor writes a `claim_grounding.response.v1`
where every candidate cites the local `entity_grounding_evidence.id` value.

Provider rank may influence candidate order, but it must not decide canonical
identity. Multiple plausible rows remain `ambiguous`. Empty result sets are
`not_found`. Provider failures are `error` or a persisted dispatch failure,
depending on whether a response can be produced.

## Entity Review Actions

When the request source references an entity id, the processor may append
`entity_identity_review_actions` rows with:

- `action_kind='grounding_evidence_attach'`;
- `grounding_evidence_id` set to the local evidence row;
- `entity_id` set to the unresolved entity;
- `actor='grounding-broker'` or a configured local actor;
- `raw_payload` containing request id, grant id, provider name, rank, and
  confidence metadata.

This is evidence attachment only. Alias attachment, external-id attachment,
merge, split, or not-same-entity actions remain explicit review decisions.

## Proposed CLI

```text
engram entity-grounding process-approved --tenant personal --corpus personal --limit 20
engram entity-grounding process-approved --request-id req-... --grant-id grant-...
engram entity-grounding broker-daemon --tenant personal --corpus personal --limit 20 --interval 10
engram entity-grounding broker-daemon --max-iterations 1
```

The command must refuse to run unless a provider is configured and a persisted
approved grant exists. It must not print provider secrets.

Current implementation note: `engram entity-grounding process-approved` is
wired as the one-shot operator-facing command. `engram entity-grounding
broker-daemon` is the local polling workflow for long-running broker operation.
The daemon dispatches lazily through `src/engram/entity_grounding_daemon.py`,
uses the restricted broker DSN, applies a transaction advisory lock per
iteration, and exposes `--max-iterations` for smoke tests and bounded local
runs. Both commands print sanitized JSON and redact secret-shaped output fields.
Operators should set `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` to a
restricted broker-role DSN before enabling a real network provider.
The default connection fallback is for local development and mocked tests; it
does not satisfy the routine network-provider acceptance criterion.

Provisioning is handled outside ordinary schema migrations because it creates a
database role. The local runbook is
`docs/runbooks/grounding-broker-role.md`; `make provision-grounding-broker`
creates/updates the restricted role and `make check-grounding-broker` verifies
the configured broker DSN. Long-running daemon operation is documented in
`docs/runbooks/grounding-broker-daemon.md`; `make grounding-broker-daemon`
wraps the daemon CLI.

## Failure Semantics

- `grant_missing`: no persisted approved grant exists.
- `grant_expired`: grant expired before dispatch.
- `grant_revoked`: latest lifecycle row revoked the grant.
- `provider_disabled`: adapter not configured.
- `provider_fetch_error`: provider call failed.
- `materialization_error`: provider returned rows but local evidence insert or
  response persistence failed.
- `policy_deferred`: query/evidence sensitivity exceeds the current policy.

Failures are append-only audit facts. They do not mutate entities, claims,
beliefs, or raw evidence.

Approved grants with an existing prepared, dispatched, succeeded, or failed
network dispatch row for the same target adapter are not selected again by the
materializer. This makes the daemon fail closed against tight retry loops for
private entity search strings; retrying requires a new approved grant.

## Security Rules

- Provider API keys are process environment secrets only.
- Provider keys must not appear in URLs, request bodies, DB rows, JSON payloads,
  logs, exceptions, or review artifacts.
- The network-capable process must not have read access to raw corpus tables.
- The network-capable process must run under broker database authority for
  routine provider use; a normal Engram DB role is acceptable only for local
  development and mocked verification.
- Provider output is treated as adversarial public data.
- Redirects and arbitrary URL fetches remain out of scope.
- Tests must use mocked providers only; no unit or e2e gate may require a live
  provider key.

## Tests

Required tests before implementation is accepted:

- approved grant is required before adapter invocation;
- denied/revoked/expired grants do not call the adapter;
- adapter receives only minimized dispatch payload;
- provider rows insert into `entity_grounding_evidence` before response
  persistence;
- response candidates cite real local evidence ids;
- duplicate provider rows reuse existing evidence rows;
- provider key is absent from request payloads, DB JSONB, response payloads,
  exceptions, and CLI output;
- poisoned provider content remains data only;
- entity review action is evidence attachment only;
- processor can run with a mocked Tavily-shaped provider and no live network.
- CLI dispatch uses `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` when present
  and does not print the broker DSN.
- provider rows with localhost/private/link-local/reserved result URLs are
  skipped before evidence insertion;
- private-tier entity queries keep the approved query privacy tier on both
  materialized evidence and evidence-attachment review actions.

## Relationship To RFC 0053

RFC 0053 defines the extractor/grounder boundary and grant contract. RFC 0055
does not relax that boundary. It makes the currently missing materialization
step explicit so the broker cannot return uncached provider rows directly to
extraction or entity review.

## Open Questions

1. Should `entity_grounding_evidence` gain first-class `request_id`,
   `grant_id`, `provider`, and `rank` columns, or should those stay in bounded
   `raw_payload` for the first slice?
2. Should candidate entity-kind classification happen during materialization or
   remain a later local review/classifier step?
3. What retention or redaction policy applies to failed provider excerpts that
   are fetched but rejected by policy?
4. Should materialized evidence automatically refresh the generic
   `evidence_items` / `evidence_refs` index from RFC 0051?
