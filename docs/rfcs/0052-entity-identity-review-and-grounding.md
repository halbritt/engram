<a id="rfc-0052"></a>
# RFC 0052: Entity Identity Review And Grounding

| Field | Value |
|-------|-------|
| RFC | 0052 |
| Title | Entity Identity Review And Grounding |
| Status | accepted_as_design_reference |
| Implementation | partial: migration 023, `src/engram/entity_grounding.py`, MCP `engram.ground_entity` local lookup |
| Date | 2026-05-17 |
| Context | D090, D094; RFC 0030; RFC 0051; `ARCHITECTURE_RECOMMENDATION_EXECUTION_PLAN_2026-05-16.md` Phase 9; migrations 009, 021, and 023 |

Decision refs:
  - [D090](../../DECISION_LOG.md#d090)
  - [D094](../../DECISION_LOG.md#d094)

This RFC is the design reference for the narrow entity grounding and review
substrate approved by D094. It defines only the local lookup/review substrate;
RFC 0053 defines the constrained network-capable broker contract. This RFC does
not implement network runtime or a full entity review UI.

Post-RFC0053 note: RFC 0053 owns the proposal-level boundary between the
corpus-reading extractor and any grounding broker, grounding LLM, or future
network-capable broker/fetch adapter. This RFC remains the accepted local
lookup/review substrate.

Post-RFC0054/0055 note: RFC 0054 owns the proposed entity-wide batch workflow
that drafts grounding requests/grants across unresolved entities. RFC 0055 owns
the proposed materialization workflow that stores approved provider results in
append-only local grounding evidence before responses or review actions consume
them.

## Motivation

Broader biography sources require entity review that can distinguish proper
names, products, places, organizations, media works, and other ambiguous named
things. The live model/context path should not gain hidden network egress.
Grounding therefore needs an explicit local tool/product surface that can be
called by LLM agents and audited by Engram.

RFC 0030 remains useful seed context for local public-dataset grounding, but it
is not the accepted contract for this broader A9 track.

## Goals

- Define an entity identity review model for aliases, merges, splits, external
  ids, and "not same entity" decisions.
- Define an MCP-facing grounding interface for LLM agents.
- Store grounding evidence, including any future fetch outputs, as immutable raw
  evidence with provenance.
- Preserve no-egress for live model/context serving paths.
- Ensure reviewed identities remain evidence-backed and auditable.

## Non-Goals

- No entity review UI is implemented by this RFC alone.
- The first MCP tool is local lookup only; no network fetch mode is implemented.
- No background cloud memory service is introduced.
- No private corpus content is sent to a remote grounding provider by default.
- No entity merge/split decision is mutable in place.

## Grounding Evidence Contract

Grounding evidence rows are raw evidence. If a future approved workflow fetches
grounding material, the fetch output is stored locally as append-only grounding
evidence before any extractor consumes it. A grounding row or capture must
preserve:

- source URL and/or query;
- fetched timestamp;
- content hash;
- fetch/tool version;
- extractor/parser version where applicable;
- tenant/corpus;
- privacy tier and sensitivity class;
- provenance linking fetched material to the grounding request.

The implemented local slice stores append-only grounding evidence. Any future
remote/network fetch mode must separately define authorization, evidence class,
serving eligibility, and the extractor/grounder request boundary described by
RFC 0053.

## MCP Grounding Surface

The first MCP surface is `engram.ground_entity`, an authorized local lookup
that lets an LLM agent ask Engram to ground ambiguous entities while doing
active work. It explicitly rejects network fetch requests. Future extensions
must define:

- tool names and request/response schemas;
- authorization and audit boundaries;
- whether a request may perform network fetches or only query local grounding
  evidence;
- how results cite immutable grounding evidence;
- failure modes for ambiguous, private-person, exact-address, health, finance,
  and other sensitive lookups.

## Implemented Slice

The 2026-05-17 D094 implementation slice adds:

- `entity_grounding_evidence`: append-only local grounding evidence rows with
  query text, entity kind, source URL/label, content hash, excerpt, fetch and
  extractor versions, tenant/corpus, privacy tier, sensitivity class, and raw
  payload.
- `entity_identity_review_actions`: append-only review-action rows for alias
  attachment, merge/split, not-same-entity, external id attachment, and
  grounding-evidence attachment.
- `src/engram/entity_grounding.py`: deterministic local grounding evidence
  lookup.
- MCP `engram.ground_entity`: authorized local lookup for LLM agents. It
  explicitly rejects network fetch requests.

## Entity Review Surface

Migration 023 implements append-only review-action rows for:

- alias attachment;
- entity merge;
- entity split;
- "not same entity";
- external-id attachment;
- grounding evidence attachment.

The full review UI remains deferred.

Reviewed entities must remain usable by `context_for` without inventing
identity links that are not grounded in evidence or review decisions.

## Expansion Questions

1. Which local grounding datasets or providers are acceptable beyond the first
   local evidence rows?
2. What explicit operator action may authorize any future remote grounding
   fetch mode? RFC 0054/0055 propose the first batch draft plus approved-grant
   materialization path.
3. What is the minimal review UI for merge/split safety?
4. How should grounding evidence join the generic evidence/reference index from
   RFC 0051?
5. Which context-eval failure class justifies expanding beyond local lookup?
