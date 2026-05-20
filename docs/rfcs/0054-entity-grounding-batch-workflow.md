<a id="rfc-0054"></a>
# RFC 0054: Entity Grounding Batch Workflow

| Field | Value |
|-------|-------|
| RFC | 0054 |
| Title | Entity Grounding Batch Workflow |
| Status | proposal |
| Implementation | implemented: batch worker, CLI seam, and runtime gate coverage present |
| Date | 2026-05-19 |
| Context | D020; D090; D094; D095; RFC 0052; RFC 0053; `src/engram/phase4.py`; `src/engram/entity_grounding.py`; `src/engram/claim_grounding.py`; `migrations/023_entity_grounding_review.sql`; `migrations/024_claim_grounding_runtime.sql` |

Decision refs:
  - [D020](../../DECISION_LOG.md#d020)
  - [D090](../../DECISION_LOG.md#d090)
  - [D094](../../DECISION_LOG.md#d094)
  - [D095](../../DECISION_LOG.md#d095)

## Summary

This RFC defines a batch workflow for grounding unresolved Phase 4 entities.
It does not fetch the network itself. Its job is to select candidate entities,
perform local lookup, and draft auditable RFC 0053 grounding requests/grants
that an operator can approve or deny.

The workflow exists because entity grounding is not a one-off lookup problem.
After `engram phase4 build-entities`, Engram can contain many active entities
with `entity_kind='unknown'` and ambiguous `canonical_text`. The system needs a
repeatable way to move those surfaces into the RFC 0053 grant flow without
letting the corpus-reading or entity-building process gain network access.

## Goals

- Select unresolved active entities that are reasonable grounding candidates.
- Resolve any already-local grounding evidence first.
- Draft RFC 0053 request/grant sidecars for unresolved entities without making
  network calls.
- Preserve exact entity-surface query display for operator review.
- Keep drafts idempotent so repeated runs do not create duplicate active work.
- Keep raw corpus context out of every draft and dispatch payload.
- Produce a queue that can be processed later by the approved-grant materializer
  specified in RFC 0055.

## Non-Goals

- No live internet search in the batch draft command.
- No automatic entity merge, split, alias, or external-id decision.
- No use of surrounding belief, claim, segment, message, or capture text as a
  network query.
- No claim or belief mutation.
- No default-on grounding provider.
- No attempt to decide whether a surface is a person, product, place, or
  organization without cited evidence.

## Candidate Selection

The first batch source is the Phase 4 `entities` table.

Eligible rows:

- `status='active'`;
- `entity_kind='unknown'`;
- non-empty `canonical_text`;
- `tenant_id` / `corpus_id` match the requested batch scope, where those
  columns exist or can be derived from provenance;
- not already linked to local grounding evidence through
  `entity_identity_review_actions`;
- not already represented by a live draft or approved RFC 0053 grant for the
  same tenant/corpus/entity/surface/provider target.

The selection query must be deterministic:

```text
ORDER BY privacy_tier ASC, confidence DESC, created_at ASC, id ASC
LIMIT :limit
```

If the current `entities` table does not carry tenant/corpus directly, the
batch worker must derive scope from source beliefs/claims or require explicit
operator scope and record the derivation in the draft payload. Ambiguous
multi-scope provenance should be skipped with an audit omission until the
schema is extended.

## Local-First Draft Flow

For each eligible entity:

1. Build the bounded `surface_form` from `entities.canonical_text`.
2. Run local lookup through `entity_grounding_evidence` using
   `engram.ground_entity` semantics.
3. If local lookup has cited results, record a draft review action rather than
   a network grant.
4. If local lookup misses, create a `claim_grounding.request.v1` payload with:
   - `surface_form` equal to the entity `canonical_text`;
   - `candidate_entity_kinds` including person, product, place, organization,
     media work, tool, and concept unless the entity already carries a narrower
     kind hint;
   - `source_refs` containing only local opaque entity/provenance references,
     not raw text;
   - `local_context_capsule={"mode":"none","text":null}`;
   - `allowed_modes=["local_lookup","network_fetch"]`;
   - `network_grant.search_query` exactly equal to `surface_form`;
   - `network_grant.query_text_class="entity_surface_form"`;
   - `network_grant.query_privacy_tier` copied from the entity/provenance tier;
   - `network_grant.allowed_network_targets=["internet_search"]`.
5. Persist the request and append a draft grant row.

The draft step is allowed to store private entity names because the operator
must see the exact query before approval. It is not allowed to send that query
to a provider.

## Idempotency

The batch worker should compute an idempotency key from:

- tenant id;
- corpus id;
- entity id;
- entity canonical text;
- query privacy tier;
- target adapter set;
- request schema version;
- batch workflow version.

If an active draft, approved grant, or completed grounding action already exists
for the same key, the worker reports it as reused/skipped rather than creating a
new row.

## Proposed CLI

```text
engram entity-grounding draft --tenant personal --corpus personal --limit 50
engram entity-grounding draft --entity-id UUID
engram entity-grounding list --status draft --tenant personal --corpus personal
```

The command names are proposal-level. Implementation may choose to nest them
under `engram claim-grounding entities ...` if that fits the CLI better, but the
workflow boundary remains the same: draft-only, no network.

Current implementation note: `engram entity-grounding draft` is wired as the
operator-facing command. It dispatches lazily to
`src/engram/entity_grounding_workflow.py`, prints sanitized JSON, and performs
no provider-secret display. The separate grant list/approval surface remains
under `engram claim-grounding grants ...` from RFC 0053.

## Output Shape

The draft command returns a compact summary:

```json
{
  "workflow_version": "entity_grounding_batch.v1",
  "selected": 50,
  "local_hits": 12,
  "drafts_created": 31,
  "drafts_reused": 5,
  "skipped": [
    {
      "entity_id": "uuid",
      "reason": "ambiguous_scope"
    }
  ]
}
```

Rows must be auditable in the RFC 0053 sidecar tables. The operator-facing list
must display `surface_form`, exact `search_query`, privacy tier, target set,
and entity id before approval.

## Safety Rules

- The batch draft process runs without network egress.
- The only string that can later cross to a provider is the exact approved
  entity surface/search query.
- The draft process must not include raw belief text, claim text, message text,
  segment text, captures, or context snippets in `network_grant` or network
  dispatch payloads.
- Private-person, exact-address, health, finance, credential, or similar
  sensitive query classes may be skipped pending a later policy extension.
- Approval is an operator action, not an LLM output.

## Tests

Required tests before implementation is accepted:

- deterministic selection over active unknown entities;
- local-hit path creates no network grant;
- network-miss path drafts a valid RFC 0053 request and draft grant;
- rerun is idempotent;
- payloads contain no raw context fields;
- private/high-sensitivity entities are skipped or marked policy-deferred;
- command opens no sockets under a socket-blocking test;
- grant list displays exact query text and entity provenance without provider
  secrets.

## Relationship To RFC 0055

RFC 0054 stops at drafts and local hits. RFC 0055 owns the separate approved
grant processor that may call a network adapter and materialize fetched rows
into append-only local grounding evidence before any response, review action, or
claim/extraction path consumes the result.

## Open Questions

1. Should the first implementation store the entity id directly on
   `claim_grounding_requests`, or only inside `request_payload.source_refs`?
2. Should local hits automatically draft `entity_identity_review_actions`, or
   only surface candidate rows for a later UI?
3. What privacy-tier cutoff should block automatic draft generation entirely?
4. Should batch selection prioritize high-confidence entities or high-ambiguity
   entities first?
