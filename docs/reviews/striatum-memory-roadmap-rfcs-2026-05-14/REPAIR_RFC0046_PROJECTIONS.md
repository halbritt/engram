# RFC 0046 Projection Repair Handoff

author: codex [self-declared: rfc0046-repair-implementor]
date: 2026-05-14
status: repair_handoff
scope: RFC 0046 proposal text only

## Summary

This repair updates RFC 0046 in response to the contract-coherence
`needs_revision` finding and the operator decision to route the package through
a bounded repair cycle. It keeps RFC 0046 as proposal text only and does not
implement migrations, code, tests, schema docs, or any serving surface.

The repair chooses full-snapshot projection generations with carry-forward rows,
makes projection-family idempotency generation-scoped, separates physical
uniqueness from active serving uniqueness, and adds concrete embedding skip and
embedding safety semantics. It also adds the RFC 0044 Phase 0 / RFC 0049 EG-000
hardening prerequisite before any migration or projection implementation.

## Accepted Findings

- CC-003 accepted: RFC 0046 now states that physical projection uniqueness is
  `(generation_id, natural key suffix)` and that active serving uniqueness is a
  separate partial-view/index invariant.
- CC-003 accepted: RFC 0046 now chooses the full-snapshot carry-forward model.
  Incremental bundles may be processed as deltas internally, but the activated
  result is a complete generation, not a mixed-generation active set.
- CC-004 accepted: `striatum_chunk_embeddings` now copies serving safety fields
  and requires enforced same-generation joins to active chunks/items before
  vector serving.
- CC-004 accepted: RFC 0046 now defines `striatum_embedding_skips` keyed by
  `(generation_id, chunk_id, embedding_model_version, embedding_dimension)`.
- CC-006 accepted: RFC 0046 now blocks migration/projection implementation on
  RFC 0044 Phase 0 hardening or EG-000-equivalent evidence.
- PB-001 partially accepted where it affects RFC 0046: projection-time path
  rules now require repository-relative paths by default and reject or sanitize
  operator-private absolute paths unless RFC 0045 supplies explicit opt-in.
- PB-005 accepted: embeddings may be computed only from persisted
  `striatum_chunks.chunk_text`; fully withheld bodies must never be embedded
  before redaction-notice substitution.
- PB-006 accepted where it affects RFC 0046: reference values and opaque
  references are scoped by stored `(tenant_id, corpus_id)` and future fetches
  must reauthorize the stored row.
- PB-007 accepted where it affects RFC 0046: the prerequisite section calls out
  RFC 0044 hardening items including tenant/source-kind consistency and decoded
  UUID/reference validation.

## Changed Sections

- Added `Dependencies And Implementation Prerequisites`.
- Added `carried_forward_from_id` to common projection columns.
- Added `Generation-Scoped Keys And Active Serving Model`.
- Revised `Projection Generation State` idempotency and activation language.
- Reframed projection-family key lists as generation-scoped idempotency suffixes.
- Added path and reference privacy rules after `striatum_references`.
- Added withheld-body embedding rules under `striatum_chunks`.
- Expanded `striatum_chunk_embeddings` with serving safety fields and enforced
  active join semantics.
- Added `striatum_embedding_skips`.
- Repaired full rebuild, incremental bundle handling, privacy reclassification,
  freshness detection, validation fixtures, validation expectations, downstream
  dependencies, and acceptance criteria.

## Validation Evidence

Command:

```sh
git diff --check -- docs/rfcs/0046-striatum-projection-index-schema.md docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REPAIR_RFC0046_PROJECTIONS.md
```

Result: passed with exit code 0 and no output.

## Deferred Questions

- RFC 0045 still owns final row-level `tenant_id`/`corpus_id`, `bundle_id`, and
  lifecycle record semantics. RFC 0046 now names those as upstream blockers
  rather than inventing authority locally.
- RFC 0049 still owns fixture execution and gate evidence. RFC 0046 names the
  projection fixtures and health checks it expects downstream gates to exercise.
- The exact PostgreSQL lexical index strategy and per-corpus pgvector partial
  index strategy remain RFC 0046 open decisions.
