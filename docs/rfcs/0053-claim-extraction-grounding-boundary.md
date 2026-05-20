<a id="rfc-0053"></a>
# RFC 0053: Claim Extraction Grounding Boundary

| Field | Value |
|-------|-------|
| RFC | 0053 |
| Title | Claim Extraction Grounding Boundary |
| Status | proposal |
| Implementation | partial: request/response/network-dispatch schemas, Python validators, append-only runtime sidecars, grant lifecycle/product CLI scaffold, disabled extraction sidecar integration, constrained generic HTTP and Tavily search-adapter scaffolds, broker credential tests, and synthetic/runtime e2e gates; no default-on live network provider |
| Date | 2026-05-18 |
| Context | D020; D090; D094; RFC 0017; RFC 0030; RFC 0051; RFC 0052; `src/engram/extractor.py`; `src/engram/entity_grounding.py`; `src/engram/claim_grounding.py`; `src/engram/claim_grounding_broker.py`; `src/engram/claim_grounding_runtime.py`; `migrations/023_entity_grounding_review.sql`; `migrations/024_claim_grounding_runtime.sql` |

Decision refs:
  - [D020](../../DECISION_LOG.md#d020)
  - [D090](../../DECISION_LOG.md#d090)
  - [D094](../../DECISION_LOG.md#d094)

Review refs:
  - [Adversarial security review](../reviews/rfc0053-claim-grounding-boundary/ADVERSARIAL_SECURITY_REVIEW.md)
  - [Striatum review findings ledger](../reviews/rfc0053-claim-grounding-boundary/FINDINGS_LEDGER.md)
  - [Striatum synthesis](../reviews/rfc0053-claim-grounding-boundary/SYNTHESIS.md)

This RFC defines the missing constrained interface between the LLM/process that
reads private corpus evidence and creates claims, and any separate LLM/tooling
that grounds ambiguous entities in those claims. The intended product direction
is that the grounding broker can have network access and search the internet
under a constrained grant. This RFC defines that broker contract and now has a
disabled-by-default Tavily provider adapter scaffold, but it does not make
network grounding default behavior or approve grounding to affect extraction
output. It exists so grounding expansion preserves the network/corpus separation
from D020.

The 2026-05-18 Striatum review kept this RFC in proposal state and made several
blockers explicit: extractor-originated network requests must be exact
entity-surface queries; grants must be persisted and verified before dispatch;
the network-capable broker must use separate credentials; and dedicated
claim-grounding synthetic/runtime gates must pass before grounding affects
extraction output. The current scaffold provides the local tables, helper APIs,
operator CLI lifecycle rows, credential-separation tests, and a disabled
generic HTTP/Tavily adapter boundary for those checks, but still does not
provide a default live internet-search provider.

RFC 0054 and RFC 0055 build on this boundary for entity-wide grounding: RFC
0054 proposes the no-network batch draft workflow for unresolved entities, and
RFC 0055 proposes the approved-grant processor that materializes provider rows
into append-only local grounding evidence before responses or review actions
consume them.

## Motivation

Owner-history gold-set work surfaced a recurring failure class: many proper
nouns are ambiguous unless grounded. A model can often avoid bad extraction if
it can learn whether a surface form is a person, product, place, organization,
media work, or concept. At the same time, the claim extractor reads private
corpus evidence and therefore must not gain live web access or send surrounding
raw corpus context to a remote grounding provider.

RFC 0030 proposed local public-dataset grounding for claim extraction. RFC 0052
implemented the first local-only MCP lookup substrate (`engram.ground_entity`).
Neither document fully specifies the boundary between:

- the corpus-reading claim extractor; and
- a grounding resolver, grounding LLM, web-search adapter, or local grounding
  broker.

That boundary needs a small, versioned protocol before grounding can become part
of extraction or re-extraction.

## Actors

### Claim Extractor

The claim extractor reads segments, messages, captures, and local derivation
state. It runs in a no-egress environment. It may identify groundable mentions
and emit extraction candidates, but it must not:

- make network requests;
- invoke a network-fetch mode through MCP or another tool;
- send surrounding raw segment/message/capture text to a grounding process with
  network access;
- treat unresolved grounding as permission to guess.

### Grounding Broker

The grounding broker is the only interface the extractor can call. Its default
mode is local lookup over already-captured grounding evidence, local public
dataset snapshots, and reviewed entity identity rows. It is also the intended
home for network access and internet search, but only behind an explicit
operator grant and a bounded entity search query. That query may itself be
private text, because entity names can originate in the private corpus. The
constraint is that the broker receives only the entity surface/search query and
grant metadata, not surrounding segment/message/capture context. It returns
bounded candidates with citations.

Extractor-originated network-capable requests are limited to
`query_text_class="entity_surface_form"` and a `search_query` that normalizes to
the same value as `surface_form`. Broader query classes such as
`operator_entered` and `broker_minimized` require a separate product surface or
minimizer specification that proves the query was created outside the
corpus-reading extractor or by a process without raw corpus access.

The current implemented substrate is RFC 0052's `engram.ground_entity`
local-lookup tool. The RFC 0053 scaffold adds request/dispatch/response
validation, append-only sidecar persistence helpers, a local broker API,
local-only CLI/MCP entry points, CLI grant lifecycle commands, disabled
extraction sidecar emission, and an explicit configured HTTP-search adapter
boundary with an optional Tavily provider. No default live internet search is
enabled.

### Network Fetch Adapter

Any internet search or network fetch adapter used by the broker is a separate
capability from private corpus reading. It may search/fetch public grounding data
only under an explicit operator grant and only from a request that has already
been stripped of surrounding private corpus context. It must not hold read
credentials for private raw evidence tables. Its output is append-only local
grounding evidence; the extractor consumes that local evidence later.

The current internet-search runtime remains disabled by default and broker-only.
`src/engram/claim_grounding_network.py` can call either a locally configured
generic HTTP search endpoint with a fixed GET query parameter, or Tavily's fixed
HTTPS Search API with a POST JSON body and Bearer API key read from
`ENGRAM_CLAIM_GROUNDING_TAVILY_API_KEY`. Both providers accept only the
minimized `claim_grounding.network_dispatch.v1` payload, reject extra private
context fields, and require the exact `entity_surface_form` search query. Engram
does not configure a provider by default, and the extractor never receives
network access.

For Tavily, the exact granted entity surface/search query, caller IP, request
timing, and provider account metadata leave the machine and may be logged by
the provider. Surrounding raw corpus text, source refs, local context capsules,
corpus-reading DB credentials, and provider secrets must not be sent or
persisted. The current v1 runtime scope is limited to search-provider and
public-dataset-adapter semantics (`internet_search`, `public_dataset_api`).
Direct URL or arbitrary web fetch targets require a later URL-fetch security
spec covering canonicalization, scheme/host policy, private-address denial, DNS
rebinding, redirects, byte/time budgets, retries, and audit.

### Grounding LLM

A grounding LLM, if used, is part of the grounding broker/fetcher side, not the
claim-extractor side. If it is local, it may classify and rank local grounding
evidence. If it is remote, it may receive only the granted entity search query
and public fetched evidence permitted by an operator grant. The search query may
contain a private entity surface. It must not receive raw segment text, raw
messages, private captures, or unconstrained claim/belief context.

## Boundary Rule

The extraction side may pass only a **grounding request**, never raw corpus
evidence. The grounding side may return only a **grounding response**, never an
uncited prose assertion. The extractor may use the response as provenance or
disambiguation input, but unresolved or ambiguous responses must remain explicit
and auditable.

The default mode is:

```text
private corpus -> no-egress extractor
              -> grounding request
              -> local grounding broker
              -> local grounding evidence / reviewed identity rows
              -> grounding response with citations
              -> claim sidecar / claim provenance
```

A future network mode, if accepted, must be:

```text
private corpus -> no-egress extractor
              -> grounding request + explicit network intent
              -> local grounding broker verifies persisted grant
              -> minimized network dispatch
              -> network adapter / internet search
              -> append-only local grounding evidence
              -> grounding response with citations
              -> claim sidecar / claim provenance
```

Surrounding private corpus content does not cross into the
network-dispatch payload. The bounded entity surface/search query can cross
when a persisted `network_grant` explicitly authorizes that exact query.

## Grounding Request V1

The request is a JSON object with this logical shape:

```json
{
  "schema_version": "claim_grounding.request.v1",
  "request_id": "uuid",
  "tenant_id": "personal",
  "corpus_id": "personal",
  "extraction_run_id": "uuid-or-versioned-run-id",
  "extraction_prompt_version": "extractor.vN...",
  "extraction_model_version": "local-model-version",
  "surface_form": "Tartine",
  "mention_role": "subject|object|context",
  "candidate_entity_kinds": ["person", "product", "place", "organization", "media_work", "tool", "concept"],
  "source_refs": [
    {
      "target_table": "messages",
      "target_id": "uuid",
      "span_hash": "sha256-hex",
      "span_start": 120,
      "span_end": 127
    }
  ],
  "local_context_capsule": {
    "mode": "none|local_only_redacted_hint",
    "text": null
  },
  "allowed_modes": ["local_lookup", "network_fetch"],
  "network_grant": {
    "grant_id": "operator-grant-id",
    "granted_by": "operator",
    "granted_at": "RFC3339 timestamp",
    "expires_at": "RFC3339 timestamp or null",
    "purpose": "entity_grounding",
    "search_query": "Tartine",
    "query_text_class": "entity_surface_form",
    "query_privacy_tier": 1,
    "allowed_network_targets": ["internet_search", "public_dataset_api"]
  },
  "privacy_tier_ceiling": 1,
  "sensitivity_ceiling": ["routine_project"],
  "requested_at": "RFC3339 timestamp"
}
```

Rules:

- `surface_form` is required and must be short enough for audit display.
- `source_refs` cite private evidence by opaque local reference and optional
  span hash. They do not include message text.
- `source_refs.target_table` is a closed local evidence vocabulary, and
  `source_refs.target_id` is a local opaque id such as a UUID. Network-capable
  broker dispatch must not dereference these ids into raw corpus text.
- `local_context_capsule.text` defaults to `null`. If present, it is usable only
  by local no-egress lookup/classification. It must not be passed to a network
  fetcher or remote LLM.
- `allowed_modes` defaults to `["local_lookup"]`. `network_fetch` is valid only
  when `network_grant` is present.
- `network_grant.search_query` records the exact string the broker may later
  dispatch to the network adapter after persisted grant verification. It may be
  private text when the entity surface itself is private. It must be bounded to
  the entity/search phrase and operator-granted; it is not raw segment, message,
  claim, or capture text.
- Extractor-originated network requests must use
  `query_text_class="entity_surface_form"` and an exact normalized match between
  `network_grant.search_query` and `surface_form`. `operator_entered` and
  `broker_minimized` are reserved for separately specified non-extractor
  surfaces.
- `network_grant.query_privacy_tier` records the privacy tier of the query being
  sent to the broker's internet-search surface.
- If `allowed_modes` includes `network_fetch`, `local_context_capsule.text` must
  be null so private contextual hints cannot leak into a network-capable broker
  request.
- The request must be persisted if it affects a claim, so grounded extraction is
  reproducible.

## Network Dispatch V1

The network dispatch object is separate from the extractor-to-broker request.
It is the only payload shape a future broker may hand to an internet-search or
public-dataset adapter:

```json
{
  "schema_version": "claim_grounding.network_dispatch.v1",
  "request_id": "uuid",
  "tenant_id": "personal",
  "corpus_id": "personal",
  "surface_form": "Tartine",
  "network_grant": {
    "grant_id": "operator-grant-id",
    "granted_by": "operator",
    "granted_at": "RFC3339 timestamp",
    "expires_at": "RFC3339 timestamp or null",
    "purpose": "entity_grounding",
    "search_query": "Tartine",
    "query_text_class": "entity_surface_form",
    "query_privacy_tier": 1,
    "allowed_network_targets": ["internet_search", "public_dataset_api"]
  },
  "requested_at": "RFC3339 timestamp"
}
```

Rules:

- It must not include `source_refs`, `local_context_capsule`, extraction prompt
  metadata, sensitivity ceilings, raw claim text, or raw corpus text.
- `schema_version` is `claim_grounding.network_dispatch.v1`; it is intentionally
  not valid as `claim_grounding.request.v1`.
- The broker must derive it from a schema-valid request plus a live persisted
  grant bound to the exact `search_query`, target set, tenant/corpus, purpose,
  and privacy tier.
- The current helper `network_broker_dispatch_payload()` creates this minimized
  shape for tests. It does not perform network IO.

## Grounding Response V1

The response is a JSON object with this logical shape:

```json
{
  "schema_version": "claim_grounding.response.v1",
  "request_id": "uuid",
  "status": "resolved|ambiguous|not_found|denied|deferred|error",
  "mode": "local_lookup|network_fetch",
  "network_fetch": "not_requested|unsupported|denied|performed_by_grounding_broker",
  "candidates": [
    {
      "candidate_id": "stable-local-id",
      "entity_kind": "product",
      "canonical_label": "Tartine",
      "external_ids": [
        {
          "kind": "wikidata_qid",
          "value": "Q..."
        }
      ],
      "grounding_evidence_ids": ["uuid"],
      "source_url": "https://example.invalid/source",
      "source_label": "Local grounding snapshot",
      "content_hash": "sha256-hex",
      "content_excerpt": "Short public excerpt safe for grounding display.",
      "confidence": 0.82,
      "stability": "stable_public_entity",
      "ambiguity_reasons": []
    }
  ],
  "omissions": [
    {
      "reason": "network_fetch_not_allowed",
      "details": "local lookup had no result"
    }
  ],
  "broker_version": "grounding-broker.v1",
  "dataset_snapshots": [
    {
      "dataset": "wikidata",
      "snapshot_id": "2026-05-01"
    }
  ],
  "created_at": "RFC3339 timestamp"
}
```

Rules:

- Every candidate must cite local immutable grounding evidence or a local dataset
  snapshot.
- A response may contain multiple candidates. The extractor must preserve
  ambiguity rather than collapsing to a single unsupported entity.
- `not_found`, `ambiguous`, and `denied` are valid outcomes, not errors.
- `content_excerpt` must be public or policy-permitted text. It must not contain
  private message/capture content.
- Network fetch status is explicit even when unsupported.

## Claim Integration

Grounded extraction should write sidecar/provenance rows rather than mutating
raw evidence or overwriting existing claims. Migration 024 scaffolds the
append-only sidecars:

- `claim_grounding_requests`;
- `claim_grounding_grants`;
- `claim_grounding_network_dispatches`;
- `claim_grounding_grant_uses`;
- `claim_grounding_responses`;
- `claim_grounding_links`;
- or a compatible generic evidence/reference sidecar from RFC 0051.

Claim rows may reference grounding artifacts by id in versioned raw payload or a
dedicated sidecar, but the active claim content remains re-extractable under RFC
0017. A grounding change creates a new extraction/grounding version or a new
sidecar row; it does not silently rewrite prior claim provenance.

Before grounding can affect extraction output, sidecar persistence is required,
not optional. The implementation now provides append-only equivalents of:

- `claim_grounding_requests`;
- `claim_grounding_responses`;
- `claim_grounding_network_dispatches` or equivalent minimized outbound-attempt
  rows;
- `claim_grounding_grant_uses` or broker outbound-attempt audit rows;
- `claim_grounding_links` tying response candidates to claim/extraction
  versions.

`src/engram/claim_grounding_runtime.py` records validated requests, grants,
grant uses, dispatch attempts, responses, and response-candidate links. The
local broker in `src/engram/claim_grounding_broker.py` can opt into these rows
with `persist_sidecars=True`; the default remains local-only and network-free.

The idempotency key must cover enough of the extraction and request shape to
make `(segment_id, version) -> idempotent commit` safe: tenant/corpus,
extraction run or extraction id, prompt/model version, source refs, surface
form, mode, grant id, and request schema version.

## Authorization And Network Division

Required process capabilities:

| Process | May read private corpus? | May call network? | May write grounding evidence? | Default |
|---------|---------------------------|-------------------|-------------------------------|---------|
| Claim extractor | yes | no | no | implemented posture |
| Local grounding broker | no raw corpus; request payload only | no | append-only audit sidecars when enabled | RFC 0052 local lookup plus RFC 0053 scaffold |
| Internet-search-capable grounding broker | no raw corpus context; bounded search query + grant only | only with explicit grant | yes | disabled configured-HTTP adapter scaffold only |
| Local public dataset indexer | no private corpus | optional dataset download only | yes | future proposal |
| Network fetch adapter | no private corpus | only with explicit grant | yes, through broker-controlled append-only rows | disabled HTTP search-adapter scaffold |
| Remote grounding LLM | bounded granted search query only; no corpus context | n/a, remote by nature | no direct DB write | not approved |

Rules:

- A corpus-reading DB credential must not be reused by a network-capable broker,
  adapter, or remote LLM.
- Internet-search-capable broker modes receive only bounded entity/search query
  strings and operator grant metadata. Those query strings may be private, and
  that privacy must be explicit in `query_privacy_tier`.
- Fetch output lands as append-only `entity_grounding_evidence` or successor
  evidence rows before the extractor consumes it.
- Operator-visible audit must answer: "What did the extractor ask to ground?",
  "What data source answered?", "Did any network-capable process run?", and
  "Which claim version used the result?"

### Operator Grant Surface

Network grants are operator decisions, not LLM assertions. Before any
network-capable runtime exists, the product surface must support this flow:

```text
draft grounding request
  -> exact operator display of search_query, surface_form, query_text_class,
     query_privacy_tier, allowed targets, expiry, tenant/corpus, extraction run,
     and opaque source refs
  -> approve or deny outside the model
  -> persisted grant id or persisted denied grounding response
```

The exact `search_query` must be visible before approval because it may contain
private entity-name text. Denials are first-class audit outcomes.

### Grant Store And Broker Credentials

A schema-valid `network_grant` is not authorization. Network dispatch requires a
local persisted grant record that is live, unrevoked, unexpired, actor-audited,
and bound to the exact outbound query, tenant/corpus, purpose, request or
extraction run, target set, and query privacy tier. Migration 024 and
`claim_grounding_runtime.py` scaffold that grant lineage; the CLI product
surface can list exact draft/persisted grants and append approve, deny, and
revoke rows. A richer review UI remains future work.

The internet-search-capable broker requires a separate process/credential
profile:

- no read access to `messages`, `segments`, `conversations`, private
  `captures`, claims, or beliefs;
- read access only to minimized broker request/grant rows needed for dispatch;
- append-only or tightly scoped write access to grounding evidence and audit
  rows;
- explicit external-provider secret handling outside raw evidence and audit
  payloads;
- permission tests proving forbidden raw-corpus reads fail. The starter
  broker-role regression lives in `tests/test_claim_grounding_security.py`.

### Broker Egress Envelope

The future broker egress path must be deterministic and bounded:

- fixed target adapters, not arbitrary model-selected endpoints;
- no model-controlled headers, cookies, methods, or retry timing;
- one-shot or explicitly budgeted request counts per grant;
- fixed retry policy, byte limits, timeout limits, redirect limits, and
  concurrency limits;
- append-only outbound-attempt audit with grant id, request id, target adapter,
  normalized query display/hash policy, timing, byte count, redirect count,
  status, and denial reason.

The current adapter scaffold enforces two fixed provider shapes:

- `generic_http`: fixed GET-only dispatch to
  `ENGRAM_CLAIM_GROUNDING_SEARCH_ENDPOINT`, timeout/byte/result limits, no
  model-controlled headers/cookies/methods, public-address endpoint/result URL
  policy with explicit localhost allowance for local development, and response
  sanitization into candidate-shaped payloads.
- `tavily`: fixed POST dispatch to `https://api.tavily.com/search`, JSON body
  containing only the exact granted query and bounded search parameters, Bearer
  auth from `ENGRAM_CLAIM_GROUNDING_TAVILY_API_KEY`, no key in URL/body/audit
  payloads, and sanitized public result rows.

Neither provider is enabled unless an operator configures and injects it. Live
adapter invocation through `ClaimGroundingBroker` additionally requires
`persist_sidecars=True` and a latest-approved persisted grant verified before
the adapter is called.

### Schema Authority

The JSON schemas document the public wire shape. The Python validator in
`src/engram/claim_grounding.py` is the normative validator for cross-field
invariants that JSON Schema cannot express cleanly today, including query
privacy ceilings, exact surface-query matching, local context capsule rules,
and response status/candidate cardinality. Schema/validator parity remains a
pre-integration blocker before independent producers rely on the JSON schemas
alone.

The committed schema set now has three separate RFC 0053 contracts:
`claim_grounding.request.v1` for extractor-to-broker intent,
`claim_grounding.network_dispatch.v1` for broker-to-network-adapter egress, and
`claim_grounding.response.v1` for cited broker output.

## Failure Semantics

- `not_found`: extraction may proceed, but the claim must not gain external
  entity provenance.
- `ambiguous`: extraction may preserve the surface form and ambiguity set; it
  must not choose a candidate solely because one is first.
- `denied`: extraction records grounding denied and proceeds only with private
  evidence provenance.
- `deferred`: the operator or a later local indexer may add evidence; current
  extraction remains ungrounded.
- `error`: the grounding broker failed; extraction should retry only if the
  worker idempotency contract can preserve `(segment_id, version)` semantics.

## E2E Gate

Before grounding is allowed to affect extraction output, a synthetic e2e gate
must pass:

- a fixture with ambiguous proper nouns;
- local grounding evidence that resolves at least product/person/place;
- an extractor or extractor-adjacent harness that emits grounding requests;
- local broker responses with citations;
- no network calls from the extractor process, exercised under
  `engram no-egress run` where supported and with a socket-blocking fallback in
  tests where OS enforcement is unavailable;
- explicit ambiguous/not-found/denied cases;
- evidence that raw surrounding private corpus text is not present in any
  network-capable request payload;
- a network-granted request fixture that proves only `network_grant.search_query`
  may cross into the internet-search-capable broker mode, and that the query can
  carry an explicit privacy tier.
- a denied network request fixture that yields an audited `denied` response;
- a granted fake-broker fixture that receives only the granted search query,
  writes append-only local grounding evidence before responding, and returns a
  cited `performed_by_grounding_broker` response;
- an ambiguous extraction-adjacent case proving candidate order does not decide
  canonical identity;
- a poisoned public-evidence fixture proving prompt-injection-shaped fetched
  content is treated only as cited evidence, not as instructions.

The current `tests/fixtures/context_eval/synthetic_e2e/` harness is seed
coverage for context-serving and local lookup. It is not yet the full extraction
grounding gate described here. The dedicated starter gate is
`make e2e-claim-grounding-synthetic`; it covers request/dispatch/response shape,
denied network results, fake granted broker results, local ambiguity, poisoned
public evidence, and socket-blocked no-live-network behavior. The runtime
sidecar gate is `make e2e-claim-grounding-runtime`; it exercises the broker,
persistence helpers, grant lifecycle, disabled extraction sidecar emission,
constrained network adapter, broker credential separation, migration sidecars,
and synthetic gate together.

## Relationship To RFC 0030 And RFC 0052

RFC 0030 remains the public-dataset grounding design seed. This RFC narrows and
version-controls the interface between extraction and grounding.

RFC 0052 remains the accepted local entity-grounding/review substrate. This RFC
defines how an extractor may call that substrate and how a network-capable
broker mode must be constrained before the internet-search runtime is introduced.

The existing MCP `engram.ground_entity` tool remains an RFC 0052 local lookup
surface. The RFC 0053 scaffold adds `engram.claim_ground_entity` and
`engram claim-grounding entity --request-json PATH` as local-only surfaces that
accept `claim_grounding.request.v1` and return `claim_grounding.response.v1`.
They do not perform live network fetches. Future product work must route
approved network mode through persisted grants before emitting
`claim_grounding.network_dispatch.v1`.

## Non-Goals

- No live web calls from the extraction loop.
- No remote LLM calls with surrounding raw corpus context.
- No default-on network grounding.
- No default-on internet search, arbitrary URL fetch, or network access from
  the extractor.
- No direct URL fetch or arbitrary public-web adapter in the current runtime
  scope.
- No public-dataset downloads or indexers beyond existing local evidence rows.
- No automatic mutation of existing claims, beliefs, entities, or raw evidence.
- No private-person, exact-address, health, finance, credential, or other
  sensitive lookup expansion without a later policy spec.

## Open Questions

1. Should grounding happen before extraction, after extraction, or both?
   Proposed default: post-extraction sidecar first; prompt-time candidates only
   after the synthetic e2e gate shows benefit.
2. Should `source_refs` include span offsets, span hashes, or both?
3. What is the minimum redaction rule for `local_context_capsule`?
4. Which process owns request/response persistence: extractor worker,
   grounding broker, or a dedicated coordinator?
5. Which production DB role/credential packaging should replace the starter
   broker-role regression before a long-running internet-search-capable broker
   is shipped?
6. How should grounding requests join the generic `evidence_items` /
   `evidence_refs` index from RFC 0051?
7. Which metrics prove grounding helped enough to justify re-extraction:
   entity-kind false-positive rate, claim audit verdict lift, context-eval lift,
   or all three?
