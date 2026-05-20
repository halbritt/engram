# RFC 0053 Claim Grounding Boundary Review -- codex_schema

Status: review
Date: 2026-05-18
Lane: codex_schema
Role: reviewer
RFC refs: RFC-0053
Decision refs: D020, D090, D094

## Findings

### F001 -- Response schema omits status/candidate cardinality invariants
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:253; docs/schemas/claim_grounding_response.v1.schema.json:16; src/engram/claim_grounding.py:657; src/engram/claim_grounding.py:903; tests/test_claim_grounding.py:270
Rationale: The Python validator correctly rejects `resolved` responses without exactly one candidate, `ambiguous` responses with fewer than two candidates, terminal statuses with candidates, and `performed_by_grounding_broker` unless `mode == "network_fetch"`. The public JSON schema only enumerates the field values and candidate item shape; it accepts response payloads that Python rejects and that would violate the RFC failure semantics. The tests only check the uncited-candidate schema case, so this drift is not pinned.
Proposed fix: Add `allOf` conditionals to `claim_grounding_response.v1.schema.json` for status-to-candidate cardinality and `network_fetch`/`mode` consistency, then add schema tests for each invalid response shape already enforced by `ClaimGroundingResponse.from_json()`.

### F002 -- Request schema does not match validator-enforced boundary checks
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:186; docs/rfcs/0053-claim-extraction-grounding-boundary.md:191; docs/schemas/claim_grounding_request.v1.schema.json:124; src/engram/claim_grounding.py:939; src/engram/claim_grounding.py:945; src/engram/claim_grounding.py:949; tests/test_claim_grounding.py:161
Rationale: The Python validator enforces three important RFC boundary rules: `local_context_capsule.text` is rejected for network-capable requests, `query_privacy_tier` may not exceed `privacy_tier_ceiling`, and an `entity_surface_form` grant must search exactly the `surface_form`. The JSON schema covers only the first rule for network mode. It still accepts privacy-ceiling violations and search-query drift that Python rejects. It also accepts `local_context_capsule.mode == "none"` with non-null text on local-only requests, while Python rejects that shape. This leaves two competing contract authorities: schema-only consumers can produce payloads the runtime contract will reject.
Proposed fix: Encode the local-context `mode`/`text` branch in the JSON schema. For cross-field constraints JSON Schema cannot express cleanly, make the RFC and schema descriptions explicit that `src/engram/claim_grounding.py` is the normative validator, and add parity tests documenting those Python-only invariants.

### F003 -- Required/default semantics diverge between schemas and Python dataclasses
Severity: minor
Source: docs/schemas/claim_grounding_response.v1.schema.json:60; src/engram/claim_grounding.py:870; src/engram/claim_grounding.py:881; src/engram/claim_grounding.py:892; docs/schemas/claim_grounding_request.v1.schema.json:201; src/engram/claim_grounding.py:240
Rationale: The response schema requires `candidates`, `omissions`, and `dataset_snapshots`, but the Python parser silently defaults all three missing arrays to empty tuples. Conversely, the request schema requires both `mode` and `text` whenever `local_context_capsule` is present, while the Python parser defaults a missing capsule or missing mode/text to local none/null behavior. These are small shape differences, but they make schema-validation results and runtime-validation results disagree on ordinary defaulted payloads.
Proposed fix: Choose one defaulting contract. Either make the Python parser require the same explicit arrays/fields as the schemas, or relax the schemas to match the Python defaults. Add round-trip tests for missing optional/defaulted fields so the chosen behavior stays stable.

### F004 -- Schema uniqueness constraints are not enforced by the Python validator
Severity: minor
Source: docs/schemas/claim_grounding_request.v1.schema.json:44; docs/schemas/claim_grounding_request.v1.schema.json:71; docs/schemas/claim_grounding_request.v1.schema.json:257; src/engram/claim_grounding.py:1008; src/engram/claim_grounding.py:1030
Rationale: The request schema marks `candidate_entity_kinds`, `allowed_modes`, and `allowed_network_targets` as unique arrays, but `_string_tuple()` and `_enum_tuple()` preserve duplicates. A schema-validating caller and a Python-validating caller can therefore disagree on duplicate-mode or duplicate-target payloads. This is not a direct leak path, but it weakens the contract discipline for fields that gate broker behavior.
Proposed fix: Enforce uniqueness in the Python tuple helpers for these fields, or remove `uniqueItems` from the schema if duplicates are intentionally tolerated. Add direct tests for duplicate modes, entity kinds, and network targets.

### F005 -- Network target vocabulary is broader than the RFC-tested contract
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:163; docs/rfcs/0053-claim-extraction-grounding-boundary.md:348; docs/reviews/rfc0053-claim-grounding-boundary/ADVERSARIAL_SECURITY_REVIEW.md:59; docs/schemas/claim_grounding_request.v1.schema.json:257; src/engram/claim_grounding.py:125; tests/test_claim_grounding.py:52
Rationale: The RFC request example and current tests exercise `internet_search` and `public_dataset_api`; the schema and Python validator also accept `public_web` and `operator_supplied_url`. Those extra targets materially broaden the future network-capable broker contract, especially because the security review calls arbitrary targets an SSRF/covert-channel risk before runtime allowlists exist. If these targets are intentional, their semantics, grant requirements, and denial tests need to be in the RFC and test suite rather than only in the enum.
Proposed fix: Remove `public_web` and `operator_supplied_url` from the v1 schema/validator until the network runtime spec exists, or add explicit RFC prose and tests that define their allowed use, audit shape, and pre-runtime denial behavior.

### F006 -- Schema tests use a partial local validator, not a Draft 2020-12 validator
Severity: minor
Source: docs/schemas/claim_grounding_request.v1.schema.json:2; docs/schemas/claim_grounding_response.v1.schema.json:2; tests/test_claim_grounding.py:406
Rationale: The tests assert behavior of a hand-rolled subset validator. It is useful for current simple assertions, but it is not a full Draft 2020-12 implementation and already ignores important details such as `format`. Once the response schema adds conditional cardinality and the request schema grows more cross-field rules, this partial validator can create false confidence about actual public-schema behavior.
Proposed fix: Add a dev dependency on a real JSON Schema validator or a small helper that shells out to one in tests, then keep only minimal local helper coverage where dependency cost is not justified.

## Open Questions

- Should `request_id`, `source_refs.target_id`, and `grounding_evidence_ids` be UUID-patterned as the RFC examples imply, or intentionally opaque non-empty strings as the tests currently use?
- Is `ClaimGroundingRequest.from_json()` the normative contract for all producers, with JSON schemas serving as documentation, or must the public JSON schemas be sufficient for independent validation?
- Are `public_web` and `operator_supplied_url` part of `claim_grounding.request.v1`, or should they wait for the network-fetch runtime RFC?

verdict: needs_revision
