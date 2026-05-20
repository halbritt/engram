# RFC 0053 Claim Grounding Boundary Findings Ledger

Status: ledger
Date: 2026-05-18
Sources:
  - REVIEW_privacy_query_boundary.md
  - REVIEW_network_security.md
  - REVIEW_schema_contract.md
  - REVIEW_runtime_integration.md
  - REVIEW_product_mcp_surface.md
  - REVIEW_eval_gate.md

## Findings

### F001 -- Non-surface query classes can bypass the entity-name leak boundary
Severity: major
Sources: [privacy_query_boundary]
Affects: `network_grant.query_text_class`; `src/engram/claim_grounding.py`; RFC 0053 Grounding Request V1
Rationale: Extractor-originated requests can use `operator_entered` or `broker_minimized` to carry arbitrary query text even though the private-text exception is meant to be bounded to the entity surface/search phrase.
merged_from:
  - privacy_query_boundary F001

### F002 -- Source references are not opaque enough for network-capable requests
Severity: major
Sources: [privacy_query_boundary]
Affects: `source_refs`; `src/engram/claim_grounding.py`; request schema
Rationale: Raw context can be smuggled through unconstrained identifier fields such as `target_id`, so the boundary relies too much on rejected field names rather than a closed local-reference grammar.
merged_from:
  - privacy_query_boundary F002

### F003 -- Network grants are not enforceable authorization
Severity: blocking
Sources: [network_security, runtime_integration]
Affects: `network_grant`; future broker dispatch
Rationale: A shape-valid grant is not proof of operator approval, expiry, revocation state, exact query binding, tenant/corpus scope, or target authorization.
merged_from:
  - network_security F001
  - runtime_integration F003

### F004 -- Broker credential separation is not yet a testable runtime profile
Severity: blocking
Sources: [network_security]
Affects: future internet-search-capable broker process; DB roles
Rationale: RFC 0053 states the credential split, but does not yet define or test the concrete process/DB role that prevents a network-capable broker from reading raw corpus tables.
merged_from:
  - network_security F002

### F005 -- Direct web/URL target vocabulary is SSRF-shaped without a URL safety spec
Severity: major
Sources: [network_security, schema_contract]
Affects: `NETWORK_TARGETS`; request schema; RFC 0053 network target semantics
Rationale: `public_web` and `operator_supplied_url` broaden the contract before URL parsing, private-address denial, redirect limits, DNS rebinding defense, and audit rules exist.
merged_from:
  - network_security F003
  - schema_contract F005

### F006 -- Covert-channel controls are absent from the broker contract
Severity: major
Sources: [network_security]
Affects: future broker egress envelope
Rationale: The future broker needs fixed adapters, bounded requests, deterministic retry/timing behavior, no model-controlled headers, and outbound-attempt audit to address D020 side channels.
merged_from:
  - network_security F004

### F007 -- Request/response/grant-use audit and sidecar persistence are optional
Severity: blocking
Sources: [network_security, runtime_integration, product_mcp_surface]
Affects: RFC 0053 Claim Integration; future sidecar tables; operator audit
Rationale: Network grounding needs mandatory append-only request, response, grant-use, outbound-attempt, and claim/extraction-link records before a response can affect extraction.
merged_from:
  - network_security F005
  - runtime_integration F001
  - product_mcp_surface F003

### F008 -- Response schema omits validator-enforced status invariants
Severity: major
Sources: [schema_contract]
Affects: `docs/schemas/claim_grounding_response.v1.schema.json`
Rationale: The JSON schema accepts response shapes the Python validator rejects, including invalid status/candidate cardinality and network status/mode combinations.
merged_from:
  - schema_contract F001

### F009 -- Request schema does not document all validator-enforced boundary checks
Severity: major
Sources: [schema_contract]
Affects: `docs/schemas/claim_grounding_request.v1.schema.json`; RFC schema authority
Rationale: Schema-only consumers can produce payloads that violate Python-only invariants such as query privacy ceiling, exact surface query equality, and local-context mode/text consistency.
merged_from:
  - schema_contract F002

### F010 -- Required/default semantics diverge between schemas and Python parsers
Severity: minor
Sources: [schema_contract]
Affects: claim-grounding request/response schemas and dataclasses
Rationale: The schemas require some arrays and capsule fields that Python defaults, while Python accepts some omitted fields that schemas reject.
merged_from:
  - schema_contract F003

### F011 -- Schema uniqueness constraints are not enforced in Python
Severity: minor
Sources: [schema_contract]
Affects: `candidate_entity_kinds`; `allowed_modes`; `allowed_network_targets`
Rationale: The schema disallows duplicate enum arrays but the Python tuple helpers currently tolerate duplicates.
merged_from:
  - schema_contract F004

### F012 -- Schema tests do not use a real Draft 2020-12 validator
Severity: minor
Sources: [schema_contract]
Affects: `tests/test_claim_grounding.py`; schema verification
Rationale: The local subset validator can miss behavior once conditional JSON Schema rules are added.
merged_from:
  - schema_contract F006

### F013 -- No-egress extraction topology is not yet executable for grounding
Severity: major
Sources: [runtime_integration, eval_gate]
Affects: extractor runtime; `engram no-egress`; synthetic e2e gate
Rationale: RFC 0053 requires a no-egress extractor, but the extraction/grounding path has not been run under the no-egress wrapper while preserving local model access and denying broker network paths.
merged_from:
  - runtime_integration F002
  - eval_gate F005

### F014 -- Local lookup can overstate canonical grounding
Severity: minor
Sources: [runtime_integration]
Affects: `ground_claim_entity_locally`; `entity_grounding_evidence`
Rationale: Local lookup maps the original query text into `canonical_label`, which can look like resolved canonical identity when the evidence row may only support entity-kind/source disambiguation.
merged_from:
  - runtime_integration F004

### F015 -- Existing MCP `engram.ground_entity` is not the RFC 0053 exchange
Severity: major
Sources: [product_mcp_surface]
Affects: MCP surface; RFC 0052/RFC 0053 boundary
Rationale: The current local lookup tool returns RFC 0052-style hit rows and cannot carry request ids, source refs, network grants, response statuses, omissions, or claim provenance links.
merged_from:
  - product_mcp_surface F002

### F016 -- Operator grant UX is not a product contract
Severity: major
Sources: [product_mcp_surface]
Affects: future grant UI/CLI/MCP flow
Rationale: RFC 0053 does not yet define how a model/extractor request becomes an operator-visible exact query approval or denial outside the model.
merged_from:
  - product_mcp_surface F001

### F017 -- `allow_network` is a misleading MCP affordance
Severity: minor
Sources: [product_mcp_surface]
Affects: `engram.ground_entity` MCP schema
Rationale: A boolean network toggle teaches the wrong model; future network grounding must be grant-bound to an exact query, target scope, expiry, and audit.
merged_from:
  - product_mcp_surface F004

### F018 -- Synthetic e2e is not yet a claim-grounding gate
Severity: blocking
Sources: [eval_gate]
Affects: RFC 0053 E2E Gate; Makefile targets; synthetic fixtures
Rationale: The current context synthetic e2e proves context serving and local lookup, not extractor-adjacent claim-grounding request emission, sidecar persistence, response consumption, or claim provenance behavior.
merged_from:
  - eval_gate F001

### F019 -- Ambiguity is shape-tested, not extraction-tested
Severity: major
Sources: [eval_gate]
Affects: ambiguity failure semantics
Rationale: The scaffold can parse ambiguous responses, but no extraction-adjacent gate proves the extractor preserves ambiguity rather than selecting the first candidate.
merged_from:
  - eval_gate F002

### F020 -- Denied and granted network request paths are not e2e-proven
Severity: blocking
Sources: [eval_gate]
Affects: synthetic network broker fixture; failure semantics
Rationale: Unit tests cover grant shapes and unsupported fetches, but no e2e path proves denied responses, granted fake-broker fetch, append-only evidence write-before-response, and query-only broker input.
merged_from:
  - eval_gate F003

### F021 -- Poisoned public evidence handling is absent
Severity: major
Sources: [eval_gate]
Affects: synthetic fixtures; future broker/evidence ranking
Rationale: The adversarial requirement for prompt-injection-shaped public evidence is not yet represented in fixtures or tests.
merged_from:
  - eval_gate F004

## Counts

- Total findings: 21
- Severity breakdown: blocking=5, major=11, minor=5, nit=0
- Per-reviewer contributions: privacy_query_boundary=2, network_security=5,
  schema_contract=6, runtime_integration=4, product_mcp_surface=4,
  eval_gate=5
