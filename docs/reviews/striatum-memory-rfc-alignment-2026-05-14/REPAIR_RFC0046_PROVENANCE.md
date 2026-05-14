author: operator [self-declared: alignment-rfc0046-provenance-repair]

## Blocker Addressed

B001 from `REVIEW_operator_ergonomics.md`: RFC 0046 left projection provenance
and authorization fields ambiguous for implementors, especially for
`striatum_references`, `striatum_chunk_embeddings`,
`striatum_embedding_skips`, and future `fetch_reference` authorization.

## Files Changed

- `docs/rfcs/0046-striatum-projection-index-schema.md`
- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/REPAIR_RFC0046_PROVENANCE.md`

## Chosen Provenance And Authorization Rule

RFC 0046 now chooses a direct copied-column rule for retrieval-visible
projection rows. `source_capture_id`, `source_kind`, and `source_sub_kind` are
stored directly on first-class projection rows, references, chunks, chunk
embeddings, and embedding skip rows. For this RFC, `source_kind` must be
`striatum`.

Joins are still mandatory before serving, but they are consistency checks rather
than the only source of authority. Reference and chunk rows must join to their
item rows in the same generation and authorized tenant/corpus pair. Embedding
and skip rows must join to their chunk and item rows in the same generation and
authorized tenant/corpus pair. Any copied-field mismatch is a malformed or stale
projection condition that fails closed.

Future `fetch_reference` text now authorizes against the stored candidate row's
direct copied `tenant_id`, `corpus_id`, `source_kind`, `source_capture_id`,
privacy tier, redaction state, and visibility, then verifies the mandatory
same-generation joins before returning content.

## Validation Run And Result

- `git diff --check -- docs/rfcs/0046-striatum-projection-index-schema.md docs/reviews/striatum-memory-rfc-alignment-2026-05-14/REPAIR_RFC0046_PROVENANCE.md`:
  passed.
- `make check-refs`: not run because this repair did not change anchors, link
  targets, or reference paths.

## Remaining Risks / Deferred Items

- The RFC still leaves the enforcement mechanism open: composite foreign keys
  versus triggers/service guards for copied provenance consistency. That is now
  explicitly scoped as an implementation enforcement choice, not a schema
  ambiguity about whether the copied fields exist.
- RFC 0046 remains proposal-only. This repair does not authorize migrations,
  projection workers, runtime behavior, generated schema docs, or promotion.

## Workflow Friction

- The worktree was already dirty in RFC 0046 and other files before this repair.
  The repair adapted to the existing RFC 0046 text and did not touch files
  outside the allowed write scope.
- No Striatum state commands, publication commands, verdict commands, commits,
  code changes, migrations, tests, generated schema docs, or runtime changes
  were performed.
