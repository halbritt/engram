author: operator [self-declared: alignment-review-ergonomics-repair]
verdict: accept

## Scope

Re-review limited to B001 from
`docs/reviews/striatum-memory-rfc-alignment-2026-05-14/REVIEW_operator_ergonomics.md`.
The check considered only whether the current RFC 0046 repair and its handoff
resolve the projection provenance and authorization ambiguity for
retrieval-visible rows.

No source RFCs, code, tests, migrations, `OPERATOR_REPORT.md`, `CHANGELOG.md`,
`DECISION_LOG.md`, generated schema docs, Striatum state, publish commands, job
completion commands, or verdict-recording commands were edited or run.

## Evidence Reviewed

- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/REVIEW_operator_ergonomics.md`
  for the original B001 finding.
- `docs/rfcs/0046-striatum-projection-index-schema.md`, especially the proposal
  status and no-implementation posture at lines 9-10 and 28-30.
- `docs/rfcs/0046-striatum-projection-index-schema.md`, common columns and the
  mechanical provenance rule at lines 147-218.
- `docs/rfcs/0046-striatum-projection-index-schema.md`, `striatum_references`
  and `fetch_reference` text at lines 372-441.
- `docs/rfcs/0046-striatum-projection-index-schema.md`, chunks, embeddings, and
  skip rows at lines 666-820.
- `docs/rfcs/0046-striatum-projection-index-schema.md`, validation and
  downstream expectations at lines 1032-1052 and 1057-1117.
- `docs/rfcs/0046-striatum-projection-index-schema.md`, open-decision text at
  lines 1165-1173.
- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/REPAIR_RFC0046_PROVENANCE.md`
  for the repair author's intended rule and remaining-risk framing.

## B001 Disposition

B001 is repaired.

RFC 0046 now states a mechanically clear rule: retrieval-visible projection
rows store authorization-critical source identity directly and use joins as
consistency checks, not as the sole authority source
(`docs/rfcs/0046-striatum-projection-index-schema.md:186`). The rule table
explicitly covers first-class projection rows, `striatum_references`,
`striatum_chunks`, `striatum_chunk_embeddings`, and `striatum_embedding_skips`,
and names direct copied behavior for `source_capture_id`, `source_kind`, and
`source_sub_kind`
(`docs/rfcs/0046-striatum-projection-index-schema.md:192`).

The copied-column versus join-enforced behavior is now unambiguous. Reference
and chunk rows must carry direct copied fields, and their `item_projection_id`
joins must match but are not the source of authority
(`docs/rfcs/0046-striatum-projection-index-schema.md:197`). Embedding and skip
rows must copy the source fields from the active chunk/item row, and
`source_kind` must be `striatum`
(`docs/rfcs/0046-striatum-projection-index-schema.md:199`). The mandatory join
paragraph requires same-generation joins and fail-closed behavior on mismatches
for source identity, privacy/redaction, dirty state, and hashes
(`docs/rfcs/0046-striatum-projection-index-schema.md:202`).

The table sections are reconciled with the rule. `striatum_references` now says
common provenance columns include direct copied `source_capture_id`,
`source_kind`, and `source_sub_kind`
(`docs/rfcs/0046-striatum-projection-index-schema.md:378`). Embedding rows now
list `source_capture_id`, `source_kind`, `source_sub_kind`, and
`source_dirty_working_tree` directly
(`docs/rfcs/0046-striatum-projection-index-schema.md:734`). Skip rows carry the
same direct source fields
(`docs/rfcs/0046-striatum-projection-index-schema.md:780`).

`fetch_reference` is reconciled. The common rule requires authorization against
the stored candidate row's direct `tenant_id`, `corpus_id`, `source_kind`,
`source_capture_id`, privacy tier, redaction state, and visibility before
content lookup, then same-generation joins for references, chunks, embeddings,
and skips
(`docs/rfcs/0046-striatum-projection-index-schema.md:212`). The
`striatum_references` section repeats that direct copied authorization and
mandatory join requirement before returning content
(`docs/rfcs/0046-striatum-projection-index-schema.md:437`).

Validation expectations now match the rule. The fixture list requires negative
tenant/corpus/provenance cases for inconsistent `source_capture_id`,
`source_kind`, or `source_sub_kind` rows
(`docs/rfcs/0046-striatum-projection-index-schema.md:1032`). Later acceptance
expects every projection row to cite direct copied source fields
(`docs/rfcs/0046-striatum-projection-index-schema.md:1071`), and requires
embedding and skip rows to match active chunk and item rows in the same
generation, tenant/corpus, privacy tier, redaction state, dirty state, and hashes
(`docs/rfcs/0046-striatum-projection-index-schema.md:1086`).

The open-decision text no longer reopens B001. It only leaves the enforcement
mechanism open: composite foreign keys versus triggers/service guards for the
already-chosen direct copied provenance fields
(`docs/rfcs/0046-striatum-projection-index-schema.md:1169`). The repair handoff
states the same scope distinction and keeps the RFC proposal-only, with no
migrations, projection workers, runtime behavior, generated schema docs, or
promotion authorized
(`docs/reviews/striatum-memory-rfc-alignment-2026-05-14/REPAIR_RFC0046_PROVENANCE.md:42`).

## Blockers

None.

## Nonblocking Findings

None for B001. The remaining composite-foreign-key versus trigger/service-guard
choice is a later implementation enforcement decision, not an operator
ambiguity about which fields exist or authorize retrieval-visible rows.

## Deferred Items

- Enforcement mechanism selection for copied provenance consistency remains
  deferred to later implementation design.
- Promotion, migration, worker implementation, runtime serving behavior, and
  generated schema docs remain out of scope.

## Workflow Friction

- The worktree was already dirty, including RFC and review-path changes. This
  review treated those as current input and did not revert or alter them.
- No Striatum state commands were run.
- No independent sub-agent tool was available in this session; read-only checks
  were parallelized across the relevant RFC, original finding, handoff, diff,
  and line-numbered evidence.
