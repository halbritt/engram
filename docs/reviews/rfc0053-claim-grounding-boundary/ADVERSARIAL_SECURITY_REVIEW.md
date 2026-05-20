# RFC 0053 Adversarial Security Review

Date: 2026-05-18
Scope:

- `docs/rfcs/0053-claim-extraction-grounding-boundary.md`
- `src/engram/claim_grounding.py`
- `docs/schemas/claim_grounding_request.v1.schema.json`
- `docs/schemas/claim_grounding_response.v1.schema.json`
- `tests/test_claim_grounding.py`

## Verdict

The scaffold is acceptable as a contract layer only. It correctly preserves the
core split: the claim extractor can create a bounded grounding request, while
the grounding broker is expected to have an internet-search-capable mode
represented only through an explicit `network_grant` and minimized
`search_query`. The search query may itself be private entity-name text.

No internet-search runtime should be implemented until the blockers below are
closed in code, not just policy prose.

## Threat Model

The primary adversary is not an internet attacker first; it is a confused or
prompt-injected extraction path trying to smuggle surrounding private corpus
context into an internet-search-capable grounding broker. Secondary adversaries
are malicious public web content, poisoned grounding evidence, local
cross-tenant leakage, and operator mistakes that over-broaden a grant.

## Findings

### S1: Internet-Search Broker Must Not Hold Corpus Read Credentials

The internet-search-capable grounding broker process must not reuse the
extractor's DB credential or any credential that can read `messages`, `segments`,
`conversations`, private `captures`, claims, or beliefs.

Current scaffold status: RFC 0053 states the rule. No network runtime exists, so
there is no violating process yet.

Required before runtime: create a separate broker credential/process profile
that can read only broker request rows, perform granted internet search, write
append-only grounding evidence, and cannot join back to raw private corpus
tables.

### S1: Network Grants Need Runtime Verification

The schema requires `network_grant`, but a schema cannot prove that the grant was
actually operator-approved, unexpired, or scoped to the requested target.

Current scaffold status: `NetworkGroundingGrant` validates shape, timestamps,
purpose, target vocabulary, bounded `search_query`, query class, and query
privacy tier.

Required before runtime: persist grants locally, verify `grant_id` against that
store, enforce expiry, and audit the actor that approved it.

### S1: Network Egress Must Be Explicitly Constrained

If the future broker accepts arbitrary URLs or search targets, the internet
search surface can become an SSRF primitive or a covert channel.

Current scaffold status: `allowed_network_targets` is a closed vocabulary, but
there is no egress code.

Required before runtime: implement target allowlists, loopback/private-IP
blocking, DNS rebinding protection, timeout/byte limits, redirect limits, and
full request audit.

### S2: `search_query` Is A Semantic Leak Channel

Even without raw message text, a proper noun can itself be private. A request
like a private person's name plus private context can leak sensitive information
through a search query.

Current scaffold status: the contract allows private entity names as the
explicit `search_query`, records `query_privacy_tier`, forbids raw context/body
fields, bounds query length, and rejects `local_context_capsule.text` when
`network_fetch` is allowed.

Required before runtime: make the operator grant UI display the exact
`search_query`; add policy checks for private-person, exact-address, health,
finance, credential, and other sensitive lookup classes; record denied outcomes
as first-class responses.

### S2: Context Capsule Must Never Reach Network Mode

`local_context_capsule.text` is useful for local no-egress classification but is
too risky for any network-capable broker request.

Current scaffold status: `ClaimGroundingRequest.from_json()` rejects any
network-capable request that includes `local_context_capsule.text`.

Required before runtime: keep this as an invariant at request persistence and
broker dispatch boundaries.

### S2: Candidate Results Need Local Evidence Before Claim Use

The extractor must never consume an uncited prose answer from a broker or remote
LLM as entity truth.

Current scaffold status: responses require cited `grounding_evidence_ids` for
every candidate; local lookup maps rows from `entity_grounding_evidence` into
the RFC 0053 response shape.

Required before runtime: network fetch output must be written to append-only
grounding evidence before response candidates are returned to extraction.

### S2: Public Web Content Can Poison Grounding Evidence

Public pages can lie, change, or contain prompt injection.

Current scaffold status: the response contract includes source URL/label,
content hash, excerpt, confidence, and stability fields, but no fetcher exists.

Required before runtime: store content hash, fetch metadata, parser version,
and source class; never execute remote page instructions; treat fetched content
as evidence to be ranked, not as authority.

### S3: Cross-Tenant And Cross-Corpus Confusion

A broker request with the wrong `tenant_id` / `corpus_id` could search or write
evidence in another local corpus.

Current scaffold status: request/response shapes carry tenant and corpus; local
lookup already scopes by tenant/corpus.

Required before runtime: authorize the broker request against the tenant/corpus
pair before lookup or fetch, and audit denied cross-boundary requests.

## Required Gates Before Network Runtime

- Unit tests proving private text fields are rejected at request validation and
  persistence.
- A no-egress test proving extractor code cannot make network calls.
- Broker-process tests proving it cannot read raw corpus tables.
- Egress tests for loopback/private-IP/redirect/DNS-rebinding denial.
- Grant-store tests for expiry, target scope, actor audit, and revoked grants.
- End-to-end synthetic fixture with one local hit, one denied network request,
  one granted network request, one ambiguous response, and one poisoned public
  evidence sample.
