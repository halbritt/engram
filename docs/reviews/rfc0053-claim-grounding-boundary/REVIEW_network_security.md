# RFC 0053 Claim Grounding Boundary Review -- codex_network

Status: review
Date: 2026-05-18
Lane: codex_network
Role: reviewer
RFC refs: RFC-0053
Decision refs: D020, D090, D094

## Findings

### F001 -- Network grants are shape-checked but not enforceable authorization
Severity: blocking
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:163; docs/rfcs/0053-claim-extraction-grounding-boundary.md:191; docs/rfcs/0053-claim-extraction-grounding-boundary.md:366; src/engram/claim_grounding.py:263; src/engram/claim_grounding.py:286; src/engram/claim_grounding.py:949
Rationale: The scaffold validates that a `network_grant` object exists, has timestamps, a purpose, targets, `search_query`, and `query_privacy_tier`, but it does not bind `grant_id` to a persisted operator approval, revocation state, tenant/corpus, request id, exact final outbound query, or target set. The exact-surface check applies only to `query_text_class == "entity_surface_form"`; `operator_entered` and `broker_minimized` can carry any non-empty string up to the length limit. That is acceptable for contract parsing, but not for an internet-search-capable broker because stale, replayed, broadened, or fabricated grants would be indistinguishable from approved grants at dispatch time.
Proposed fix: Before any network runtime, define an append-only grant store and verifier. The verifier should require a live, unrevoked grant scoped to tenant/corpus, purpose, request id or extraction run, exact outbound `search_query`, allowed targets, expiry, approving actor, and query privacy tier. Add denial/audit rows and tests for expired, revoked, mismatched-query, mismatched-target, mismatched-tenant, and broker-rewritten query cases.

### F002 -- Broker credential separation is a rule, not a testable runtime profile
Severity: blocking
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:281; docs/rfcs/0053-claim-extraction-grounding-boundary.md:294; DECISION_LOG.md:42; docs/reviews/rfc0053-claim-grounding-boundary/ADVERSARIAL_SECURITY_REVIEW.md:33
Rationale: RFC 0053 correctly states that a network-capable broker must not reuse corpus-reading credentials, but it does not specify the concrete DB role, process profile, or credential manifest that makes this enforceable. The runtime needs more than a convention: the internet-search broker must be unable to read `messages`, `segments`, `conversations`, private `captures`, claims, or beliefs even if compromised. External search/API credentials are also unspecified, including where they live, which process can read them, and how their use is audited without putting secrets in request/response rows.
Proposed fix: Add a required broker credential profile before runtime implementation: separate OS process, separate DB role, no raw-corpus `SELECT`, insert-only or tightly scoped write access to grounding evidence/audit tables, read access only to minimized broker request/grant rows, and explicit handling for external provider secrets outside raw evidence and audit payloads. Add a permission test that attempts forbidden reads with the broker role and proves they fail.

### F003 -- `public_web` and `operator_supplied_url` create an SSRF-shaped contract without a URL safety spec
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:191; docs/schemas/claim_grounding_request.v1.schema.json:257; src/engram/claim_grounding.py:125; docs/reviews/rfc0053-claim-grounding-boundary/ADVERSARIAL_SECURITY_REVIEW.md:59
Rationale: The RFC says `network_grant.search_query` is the only string the network-capable mode may use for external lookup, but the schema and Python validator already accept `public_web` and `operator_supplied_url` as network targets. Those targets imply direct URL fetch semantics, yet the request contract has no URL field, canonicalization rule, host allowlist, redirect policy, DNS rebinding defense, private-IP/loopback/link-local/cloud-metadata denial, method restriction, or byte/time budget. Leaving these enum values in v1 invites an implementation to treat search text as a URL or to add an unreviewed side channel later.
Proposed fix: Remove `public_web` and `operator_supplied_url` from the v1 network target vocabulary until a network-fetch spec exists, or add that spec now with URL parsing, scheme and host policy, DNS/IP validation before and after redirects, private-address denial, GET-only behavior, redirect/byte/time/retry limits, and tests for loopback, RFC1918, link-local, metadata-service, rebinding, and redirect-to-private cases.

### F004 -- Covert-channel controls are not part of the broker contract
Severity: major
Source: HUMAN_REQUIREMENTS.md:142; HUMAN_REQUIREMENTS.md:169; docs/rfcs/0053-claim-extraction-grounding-boundary.md:119; docs/rfcs/0053-claim-extraction-grounding-boundary.md:296
Rationale: The core project threat model explicitly calls out DNS, URL parameters, request timing, and retry patterns as unverifiable leak channels. RFC 0053 minimizes payload content, which is necessary, but it does not define an outbound egress envelope for the future broker: fixed provider set, one outbound lookup per grant, no model-controlled headers/cookies, deterministic retry behavior, rate/concurrency limits, response byte caps, and audited timing. Without that envelope, a compromised broker or model-adjacent fetcher can encode private information in target choice, query sequencing, retries, delays, or request metadata even when the visible payload is just `search_query`.
Proposed fix: Make the network broker runtime spec include an egress budget and deterministic dispatch policy. At minimum: fixed target adapters, no arbitrary headers, no cookies, bounded retries with fixed backoff, per-grant request count, byte/time limits, normalized user agent, no model-controlled timing, and an append-only outbound-attempt audit containing grant id, request id, target adapter, normalized query hash/plaintext as policy permits, timestamps, redirect count, byte count, and denial reason.

### F005 -- Append-only evidence exists, but request/response/network audit is not mandatory
Severity: blocking
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:264; docs/rfcs/0053-claim-extraction-grounding-boundary.md:299; docs/rfcs/0053-claim-extraction-grounding-boundary.md:301; migrations/023_entity_grounding_review.sql:5; migrations/023_entity_grounding_review.sql:99
Rationale: Migration 023 makes `entity_grounding_evidence` append-only, which is the right substrate. The network path still lacks mandatory append-only request, response, grant-use, and outbound-attempt records. RFC 0053 says future integration "may use" request/response/link tables, but the audit requirement must be stronger for network fetches: the operator must reconstruct what query was approved, what process ran, what external source answered, what was stored locally, and which claim version consumed it. The current evidence row does not carry `request_id`, `grant_id`, outbound target, resolved URL/IP/redirect metadata, fetch status, denial reason, or claim-grounding link by default.
Proposed fix: Promote the sidecar/audit tables from optional to required before network runtime. Require append-only `claim_grounding_requests`, `claim_grounding_responses`, `claim_grounding_grant_uses` or equivalent, and `claim_grounding_links` tying response candidates to claim/extraction versions. Network fetch should insert grounding evidence and audit rows before returning a response, and response validation/persistence should verify cited evidence exists under the same tenant/corpus and request/grant lineage.

## Open Questions

- Are `public_web` and `operator_supplied_url` intended to be part of request v1, or should v1 be limited to search-provider and public-dataset adapters?
- Should network grants be one-shot per `request_id`, reusable within an extraction run, or reusable until expiry?
- Where will external search provider credentials live, and which process is allowed to read them?
- What exact audit payload may store private `search_query` plaintext versus hashes or redacted display text?

verdict: needs_revision
