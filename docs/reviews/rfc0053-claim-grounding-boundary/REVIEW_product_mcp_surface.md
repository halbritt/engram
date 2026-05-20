# RFC 0053 Claim Grounding Boundary Review -- product/MCP surface

Status: review
Date: 2026-05-18
Lane: codex_product
Role: reviewer
RFC refs: RFC-0053
Decision refs: D020, D090, D094

## Findings

### F001 -- Operator grant UX is not yet a product contract
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:164; docs/rfcs/0053-claim-extraction-grounding-boundary.md:279; docs/reviews/rfc0053-claim-grounding-boundary/ADVERSARIAL_SECURITY_REVIEW.md:82
Rationale: RFC 0053 correctly models `network_grant.search_query` as the only networkable string and explicitly allows it to contain private entity-name text, but the grant arrives in the request as already-approved data. The RFC does not yet define the product flow that turns an LLM/extractor desire to search into an operator-visible approval: who displays the exact query, how approval is captured outside the model, how denial is represented, how expiry/revocation are shown, and how the operator sees the difference between `surface_form` and `search_query` for `operator_entered` or `broker_minimized` queries. Without that, an MCP-using agent can only construct a grant-shaped payload, not safely obtain a grant.
Proposed fix: Add a normative "Operator Grant Surface" section before any runtime implementation. It should specify the MCP/CLI/UI flow as draft request -> exact operator display -> approve/deny -> persisted grant id or denied response. The display must include the exact `network_grant.search_query`, `surface_form`, `query_text_class`, `query_privacy_tier`, allowed targets, expiry, tenant/corpus, extraction run, and source refs by opaque id. Approval must be a human/operator action, not an LLM self-asserted field.

### F002 -- Current `engram.ground_entity` is not the RFC 0053 agent surface
Severity: major
Source: docs/rfcs/0052-entity-identity-review-and-grounding.md:77; src/engram/mcp_stdio.py:170; src/engram/mcp_stdio.py:390; docs/rfcs/0053-claim-extraction-grounding-boundary.md:134
Rationale: The existing MCP tool is a useful constrained local lookup for active LLM work, but it does not accept or return the RFC 0053 request/response contract. It takes a free-form `query`, rejects network fetch, and returns local hit rows. It has no `request_id`, `source_refs`, `allowed_modes`, `network_grant`, response `status`, `omissions`, or `dataset_snapshots`. That is fine for RFC 0052 local lookup, but it is not enough for an extractor-adjacent agent that needs a stable, auditable grounding exchange that can later be linked to claim provenance.
Proposed fix: Keep `engram.ground_entity` as the ad-hoc local lookup tool, and define a separate versioned MCP surface for RFC 0053, for example `engram.claim_ground_entity`, that accepts `claim_grounding.request.v1` and returns `claim_grounding.response.v1`. In unsupported network cases, return a valid `denied` or `deferred` response with omissions instead of relying only on MCP errors, so LLM agents can preserve failure semantics.

### F003 -- Audit requirements are stated but not made inspectable
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:201; docs/rfcs/0053-claim-extraction-grounding-boundary.md:301; docs/schema/README.md:1141; src/engram/mcp_stdio.py:390
Rationale: The RFC says operator-visible audit must answer what was asked, what source answered, whether a network-capable process ran, and which claim version used the result. The current scaffold validates request/response shapes and the existing grounding evidence table stores fetched/local evidence, but there is no concrete audit record for the request, grant display/decision, MCP caller, denied outcome, response, or claim-version link. A product surface cannot make private query use reviewable unless those rows and views exist.
Proposed fix: Define append-only audit persistence before network runtime: `claim_grounding_requests`, `claim_grounding_responses`, and `network_grounding_grant_events`, or equivalent generic evidence rows. The audit view should be body-free except for the exact granted/denied `search_query`, opaque source refs, actor, timestamp, expiry, allowed targets, broker version, network status, response id, and claim/extraction version that consumed the result.

### F004 -- `allow_network` is a misleading MCP affordance
Severity: minor
Source: src/engram/mcp_stdio.py:181; src/engram/mcp_stdio.py:352; docs/rfcs/0053-claim-extraction-grounding-boundary.md:189
Rationale: The current tool fails closed when `allow_network=true`, which is the right runtime behavior today. As a product surface, though, a boolean named `allow_network` teaches LLM agents the wrong approval model: future network grounding cannot be a boolean toggle, because the safe unit is an exact query plus operator grant, target scope, expiry, and audit.
Proposed fix: Remove `allow_network` from the local-only tool schema, or mark it as a temporary compatibility field that always returns an unsupported/denied grounding response. Any future network-capable MCP tool should require the full grant object or a persisted grant id bound to the exact query.

## Open Questions

- Which surface creates grants: a CLI, local browser UI, MCP tool that only drafts a request for human approval, or a combination?
- Are `operator_entered` and `broker_minimized` query classes allowed to be proposed by an LLM agent, or only by an operator/broker after minimization review?
- Should denied private queries be persisted forever for audit, and under what privacy tier?
- Is the intended LLM-agent response shape always RFC 0053, or may local lookup continue returning the RFC 0052 hit shape for non-extraction workflows?
- What exact audit view should an operator use to answer "show every private query that was granted or denied this week"?

verdict: accept_with_findings
