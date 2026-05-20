---
schema_version: "striatum.synthesis.v1"
artifact_kind: "synthesis"
---

# RFC 0053 Claim Grounding Boundary Synthesis

Status: synthesis
Date: 2026-05-18
RFC refs: RFC-0053
Decision refs: D020, D090, D094

## Findings Outcome

| ID | Outcome | Reason | Delta |
|----|---------|--------|-------|
| F001 | accepted | Extractor-originated network queries must be narrower than the current enum permits. | RFC: bind extractor-originated network requests to `entity_surface_form`; defer other query origins to separate surfaces. |
| F002 | accepted | Identifier fields must not become raw-context tunnels. | RFC: close `source_refs` grammar and forbid source refs to network fetch adapters except opaque audit ids. |
| F003 | accepted | Shape validation is not authorization. | RFC: make persisted grant-store verification mandatory before network runtime. |
| F004 | accepted | Credential split must be enforceable, not advisory. | RFC: require broker DB/process credential profile and permission tests. |
| F005 | accepted | URL/direct-web targets are too broad for the current contract. | RFC: remove direct URL targets from v1 runtime scope until a direct-fetch spec exists. |
| F006 | accepted | D020 side-channel risks need a broker egress envelope. | RFC: require deterministic outbound-attempt policy and audit. |
| F007 | accepted | Grounding that can affect extraction needs durable replay. | RFC: promote request/response/grant-use/link sidecars from optional examples to required before runtime. |
| F008 | accepted with modification | Schema/Python drift is real, but implementation belongs in a follow-up code slice. | RFC/review: record schema parity as a pre-integration blocker. |
| F009 | accepted with modification | Cross-field rules cannot all live in JSON Schema. | RFC: state Python validator is normative where schema cannot express invariants; code follow-up should improve parity. |
| F010 | deferred | Defaults are contract hygiene, not a network-boundary blocker. | Follow-up schema/code cleanup. |
| F011 | accepted with modification | Duplicate gate arrays should be rejected, but not needed for RFC prose revision. | Follow-up validator/schema parity tests. |
| F012 | deferred | A full JSON Schema validator is useful after conditionals are added. | Follow-up test-tooling improvement. |
| F013 | accepted | No-egress must be proven on the extractor-adjacent grounding path. | RFC: require no-egress claim-grounding gate and document local-model topology. |
| F014 | accepted with modification | Local lookup evidence should not be overstated as canonical identity. | RFC: distinguish entity-kind/source disambiguation from canonical identity. |
| F015 | accepted | RFC 0052 local lookup is not the RFC 0053 exchange. | RFC: define a future versioned MCP claim-grounding tool or equivalent broker surface. |
| F016 | accepted | Human approval must be a product contract, not an LLM-filled field. | RFC: add Operator Grant Surface requirements. |
| F017 | accepted with modification | The existing fail-closed boolean can remain temporarily, but must not be the future grant model. | RFC: mark `allow_network` as local-tool compatibility, not the RFC 0053 network approval surface. |
| F018 | accepted | Existing synthetic context e2e is seed coverage only. | RFC/roadmap: require dedicated claim-grounding synthetic e2e before extraction use. |
| F019 | accepted | Ambiguity must be preserved through extraction-adjacent behavior. | RFC: add explicit ambiguity gate expectation. |
| F020 | accepted | Denied and granted network paths need fake-broker e2e proof. | RFC: add denied/granted fake-broker fixtures with query-only boundary assertions. |
| F021 | accepted | Public evidence can be hostile and must be tested as such. | RFC: add poisoned evidence fixture requirement. |

## Required Deltas

- Revise RFC 0053 so extractor-originated network requests may use only exact
  `entity_surface_form` search queries. `operator_entered` and
  `broker_minimized` require separate non-corpus surfaces or specs.
- State that network-capable broker dispatch cannot rely on grant shape:
  persisted grants, expiry, revocation, exact query binding, target binding,
  tenant/corpus scope, actor audit, and denial rows are mandatory.
- Require a separate broker process/DB credential profile before any internet
  runtime, with permission tests proving raw corpus reads fail.
- Restrict current v1 runtime scope to search/dataset adapters. Direct URL and
  arbitrary web fetch targets require a later URL-fetch security spec.
- Add the deterministic broker egress envelope: fixed adapters, no arbitrary
  headers/cookies, bounded retries/timing, byte/time limits, request-count
  budget, and outbound-attempt audit.
- Promote claim-grounding request, response, grant-use, and claim/extraction
  link sidecars to required pre-runtime infrastructure.
- Add Operator Grant Surface requirements: draft request, exact private query
  display, approve/deny outside the model, persisted grant id or denied
  response, expiry/revocation, and audit view.
- Clarify that RFC 0052 `engram.ground_entity` remains local lookup; RFC 0053
  needs a versioned claim-grounding broker/MCP surface before agent use.
- Add a dedicated claim-grounding synthetic e2e gate covering no-egress
  extractor behavior, ambiguity preservation, denied network requests, granted
  fake-broker search, append-only evidence write-before-response, query-only
  broker input, and poisoned public evidence.
- Record schema/validator parity as a pre-integration blocker: response
  cardinality, request boundary checks, duplicate arrays, default semantics,
  and real Draft 2020-12 validation should be cleaned up before public
  independent producers rely on the JSON schemas alone.

## Deferred Deltas

- Implementing the grant store, network broker, direct fetch adapter, provider
  credentials, DB roles, or real internet search runtime.
- Adding a new MCP tool implementation for RFC 0053.
- Changing claim extraction output based on grounding responses.
- Promoting RFC 0053 from proposal to accepted specification.
- Full schema/test parity implementation; this should be a follow-up code
  slice after the RFC text pins the contract.

## Recommendation

revise-rfc

The review package supports keeping RFC 0053 as the right boundary direction,
but not as a runtime-ready specification. The immediate action is to revise the
RFC and adjacent roadmap/changelog text so the blockers are explicit. After
that, the next implementation slice should be the claim-grounding synthetic e2e
gate and schema/validator parity cleanup, still without implementing live
internet search.

## Residual Risks

- The review cycle used Codex lanes only; Striatum records this as Codex-lane
  provenance, not cross-model review.
- The `needs_revision` verdicts were overridden to `accept_with_findings`
  because the operator requested continued execution without additional human
  intervention. The underlying findings remain accepted blockers before
  runtime.
- The current code still accepts broader network targets and non-surface query
  classes; the RFC revision must mark those as non-runtime or follow-up work
  until code catches up.
