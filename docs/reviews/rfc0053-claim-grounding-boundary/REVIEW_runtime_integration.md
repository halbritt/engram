# RFC 0053 Claim Grounding Boundary Review -- codex_runtime

Status: review
Date: 2026-05-18
Lane: codex_runtime
Role: reviewer
RFC refs: RFC-0053
Decision refs: D020, D090, D094

## Findings

### F001 -- Sidecar persistence and idempotency are still underspecified
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:201; docs/rfcs/0053-claim-extraction-grounding-boundary.md:264; docs/rfcs/0053-claim-extraction-grounding-boundary.md:315; docs/rfcs/0053-claim-extraction-grounding-boundary.md:366; src/engram/claim_grounding.py:694
Rationale: The RFC says requests must be persisted if they affect a claim and lists possible sidecar tables, but it leaves the owning process, uniqueness key, retry behavior, and claim/link semantics open. The current scaffold exposes validators plus a local lookup helper, with no persistence API or migration. That is acceptable for a contract scaffold, but not for extractor integration: an interrupted `(segment_id, version)` worker could duplicate grounding requests/responses, lose which response influenced a claim, or hide grounding inside mutable claim `raw_payload` without a durable replay path.
Proposed fix: Before grounding affects extraction output, define one append-only sidecar contract: request rows, response rows, and claim/extraction links, or an explicit RFC 0051-compatible equivalent. Add a stable request fingerprint over tenant/corpus, extraction id or run id, schema version, source refs, surface form, allowed mode, and grant id; enforce uniqueness for the idempotent worker path; persist response hashes and broker version; and test that rerunning the same extraction version is a no-op while a new prompt/model version creates a distinct sidecar lineage.

### F002 -- The no-egress extractor runtime topology is not yet executable
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:53; docs/rfcs/0053-claim-extraction-grounding-boundary.md:318; src/engram/extractor.py:563; src/engram/extractor.py:617; src/engram/segmenter.py:1918; src/engram/no_egress.py:261
Rationale: RFC 0053 correctly requires the extractor to remain no-egress, and the scaffold has an OS-level no-egress wrapper elsewhere in the repo. The actual extractor path still instantiates an HTTP client to the local model endpoint and is not shown running under that wrapper. `ensure_local_base_url()` prevents a remote model URL, but it is not equivalent to D020 enforcement. There is also a practical topology question: an isolated network namespace that blocks non-loopback egress may not be able to reach a host-loopback model server unless the model runs inside the same namespace, uses a Unix socket, or is otherwise explicitly routed. Until that path is proven, a future extraction-grounding integration can satisfy schema tests while failing the no-egress runtime contract.
Proposed fix: Add an extraction-grounding smoke gate that runs the extractor or an extractor-adjacent harness inside the selected no-egress mechanism, proves non-loopback egress is blocked, proves the approved local model transport still works, and fails if the extractor invokes any network-fetch broker/tool path. Document the supported runtime topology before enabling grounded extraction outside local lookup tests.

### F003 -- Schema-valid network grants are not runtime authorization
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:189; docs/rfcs/0053-claim-extraction-grounding-boundary.md:279; docs/reviews/rfc0053-claim-grounding-boundary/ADVERSARIAL_SECURITY_REVIEW.md:47; src/engram/claim_grounding.py:263; docs/schemas/claim_grounding_request.v1.schema.json:80
Rationale: `NetworkGroundingGrant` validates shape, target vocabulary, timestamps, query tier, and the `entity_surface_form` equality case, but there is no local grant store or dispatch check. A runtime broker must not treat a schema-valid `grant_id` as authorization, especially because `network_grant.search_query` may contain private entity-name text and because non-`entity_surface_form` query classes are intentionally not semantically provable by the schema.
Proposed fix: Gate any network-capable broker dispatch on a persisted operator grant table with actor, exact query text, allowed targets, expiry, revocation status, tenant/corpus scope, and privacy/sensitivity policy verdict. Persist denied/deferred responses as first-class sidecar rows so failed grants are auditable and idempotent.

### F004 -- Local lookup responses can overstate canonical grounding
Severity: minor
Source: migrations/023_entity_grounding_review.sql:10; migrations/023_entity_grounding_review.sql:22; src/engram/entity_grounding.py:81; src/engram/claim_grounding.py:795
Rationale: The implemented local lookup maps `entity_grounding_evidence.query_text` into `ClaimGroundingCandidate.canonical_label`, while migration 023 has no first-class canonical label or external-id columns. That is safe enough as a cited local evidence lookup, but if extraction later treats `status=resolved` as canonical identity grounding, the candidate label may be just the original search surface rather than a reviewed public/entity label. This weakens the runtime path from local lookup to claim-safe provenance.
Proposed fix: Either add structured canonical label/external-id extraction from grounding evidence metadata before claim use, or define that local lookup without those fields is only entity-kind/source disambiguation. Add tests for two local evidence rows with the same surface form but different canonical identities so integration cannot collapse ambiguity by copying the query text.

## Open Questions

- Which component owns the durable request/response/link write: extractor worker, grounding broker, or a coordinator around both?
- What is the exact idempotency key for a grounding request that spans an extraction id, source refs, surface form, mode, prompt/model version, and grant id?
- How will the no-egress extraction runtime reach the local model while still blocking all non-loopback or unapproved network paths?
- Which local grounding candidate fields are claim-authoritative, and which are only hints for a later extractor prompt or review UI?
- What metric must pass before grounded extraction is allowed to change claim output rather than only recording sidecars?

verdict: accept_with_findings
