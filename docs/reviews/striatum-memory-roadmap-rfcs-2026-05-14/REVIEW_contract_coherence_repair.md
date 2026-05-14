# Contract Coherence Repair Re-Review

verdict: accept_with_findings
reviewer: codex contract-coherence repair reviewer
date: 2026-05-14
scope: repaired RFC0045/RFC0046/RFC0049 and cross-RFC implications

## Summary

The bounded repairs adequately resolve the prior blocking contract-coherence
verdict. No original CC finding remains blocking, and I found no new blocking
cross-RFC inconsistency introduced by the RFC0045, RFC0046, or RFC0049 repairs.

The remaining issues are proposal-stage alignment defects. They should be fixed
before promotion or implementation, but RFC0049 now prevents them from becoming
silent default-on injection risks because Level 3 remains blocked until accepted
RFC0045-RFC0048 successors and passing gates exist.

## Original Findings Disposition

| ID | Disposition | Notes |
|----|-------------|-------|
| CC-001 | resolved | RFC0045 now requires row-level `tenant_id`, `corpus_id`, and `bundle_id` on every item and validates the row pair against `manifest.memory_target`; see `docs/rfcs/0045-striatum-corpus-contract-v2.md:432` and `docs/rfcs/0045-striatum-corpus-contract-v2.md:607`. |
| CC-002 | partially_resolved_nonblocking | RFC0045 now defines `bundle_id`, `bundle_sha256`, `previous_bundle_id`, and lifecycle record shapes; see `docs/rfcs/0045-striatum-corpus-contract-v2.md:276` and `docs/rfcs/0045-striatum-corpus-contract-v2.md:674`. Downstream RFC0047 example drift remains in Findings. |
| CC-003 | resolved | RFC0046 now uses generation-scoped idempotency and full-snapshot active generation activation with carry-forward rows; see `docs/rfcs/0046-striatum-projection-index-schema.md:183` and `docs/rfcs/0046-striatum-projection-index-schema.md:872`. |
| CC-004 | partially_resolved_nonblocking | RFC0046 now copies serving safety fields onto embedding rows and defines `striatum_embedding_skips`; see `docs/rfcs/0046-striatum-projection-index-schema.md:658` and `docs/rfcs/0046-striatum-projection-index-schema.md:699`. Skip-row invalidation semantics still need tightening. |
| CC-005 | resolved | RFC0049 now blocks Level 3 until RFC0045, RFC0046, RFC0047, and RFC0048 or accepted successors are promoted; see `docs/rfcs/0049-striatum-evaluation-gates.md:38`, `docs/rfcs/0049-striatum-evaluation-gates.md:59`, and `docs/rfcs/0049-striatum-evaluation-gates.md:267`. |
| CC-006 | resolved | RFC0046 now blocks migration/projection implementation on RFC0044 Phase 0 hardening or EG-000-equivalent evidence; see `docs/rfcs/0046-striatum-projection-index-schema.md:94` and `docs/rfcs/0046-striatum-projection-index-schema.md:1037`. |
| CC-007 | partially_resolved_nonblocking | RFC0045 now closes provenance, classification, reference, lifecycle, authority, stability, and confidence vocabularies; see `docs/rfcs/0045-striatum-corpus-contract-v2.md:385`, `docs/rfcs/0045-striatum-corpus-contract-v2.md:472`, and `docs/rfcs/0045-striatum-corpus-contract-v2.md:530`. RFC0046 does not yet fully mirror that reference vocabulary. |
| CC-008 | resolved | RFC0049 now defines Level 2 experimental automatic injection, matrix columns for Levels 1-3, and per-gate failure actions; see `docs/rfcs/0049-striatum-evaluation-gates.md:249` and `docs/rfcs/0049-striatum-evaluation-gates.md:312`. |
| CC-009 | resolved | RFC0049 now makes no-egress scope transitive across local model, embedding, reviewer/evaluator, and loopback helper runtimes that receive corpus text; see `docs/rfcs/0049-striatum-evaluation-gates.md:400` and `docs/rfcs/0049-striatum-evaluation-gates.md:414`. |
| CC-010 | partially_resolved_nonblocking | RFC0049 now requires machine-readable golden-query manifests and candidate-level packet audit reconstruction; see `docs/rfcs/0049-striatum-evaluation-gates.md:565` and `docs/rfcs/0049-striatum-evaluation-gates.md:779`. Exact job-id reference coverage and RFC0048 audit wording still need alignment. |

## Findings

- blocker: None. No blockers remain.

- major: RFC0047 still models bundle identity as a SHA in response examples, while
  repaired RFC0045 separates opaque `bundle_id` from `bundle_sha256`.
  RFC0045 states that `bundle_sha256` is not a replacement for `bundle_id` at
  `docs/rfcs/0045-striatum-corpus-contract-v2.md:283` and defines bundle identity
  at `docs/rfcs/0045-striatum-corpus-contract-v2.md:601`. RFC0047 still shows
  `"bundle_ids": ["sha256:<hex>"]` and citation `"bundle_id": "sha256:<hex>"`
  at `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:293` and
  `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:333`.

- major: RFC0046's exact-reference vocabulary omits `workflow_job_id` and
  `job_id`, even though RFC0045 defines them and RFC0049 requires exact lookup
  coverage for them. RFC0045 includes the ref kinds at
  `docs/rfcs/0045-striatum-corpus-contract-v2.md:543`, RFC0046's
  `striatum_references` vocabulary omits them at
  `docs/rfcs/0046-striatum-projection-index-schema.md:348`, RFC0047 exposes them
  as filters at `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:216`,
  and RFC0049 requires exact identifier lookup by them at
  `docs/rfcs/0049-striatum-evaluation-gates.md:613`.

- major: `striatum_embedding_skips` is not clearly invalidation-addressable.
  RFC0046 says privacy reclassification invalidates embedding skips and health
  checks count skip rows, but the skip table lacks `is_active`, `invalidated_at`,
  and `invalidation_reason`. Either skip rows need those fields, or the RFC needs
  an explicit rule that skip validity is derived only through same-generation
  active chunk/item joins. See `docs/rfcs/0046-striatum-projection-index-schema.md:699`,
  `docs/rfcs/0046-striatum-projection-index-schema.md:890`, and
  `docs/rfcs/0046-striatum-projection-index-schema.md:906`.

- major: RFC0047 still leaves corpus metadata redaction at the retrieval contract
  layer weaker than RFC0049's gate. The response shape exposes
  `corpus.bundle_ids`, `source_time_min`, `source_time_max`, and
  `staleness_seconds` at
  `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:292`, while the
  failure text at `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:386`
  does not explicitly require those fields to be omitted or nulled for
  `unauthorized`, `no_data`, or pair-mismatch responses. RFC0049 now gates that
  behavior at `docs/rfcs/0049-striatum-evaluation-gates.md:481` and
  `docs/rfcs/0049-striatum-evaluation-gates.md:806`, so this is not a blocker.

- minor: EG-020 has a wording conflict: one bullet rejects any HTTP client on the
  corpus-reading path, while the next allows loopback HTTP/model/embedding
  clients when paired with no-egress evidence. Clarify this as no external or
  unpaired HTTP client. See `docs/rfcs/0049-striatum-evaluation-gates.md:424`
  and `docs/rfcs/0049-striatum-evaluation-gates.md:428`.

- minor: RFC0048 should align with RFC0049 on audit and default-on wording.
  RFC0048 says the target after RFC0049 acceptance is automatic augmentation at
  `docs/rfcs/0048-striatum-context-injection-policy.md:230`, but RFC0049 also
  requires accepted/promoted upstream successors at
  `docs/rfcs/0049-striatum-evaluation-gates.md:269`. RFC0048's audit field list
  at `docs/rfcs/0048-striatum-context-injection-policy.md:591` is also weaker
  than RFC0049's opaque omitted-candidate and privacy-inheritance audit rules at
  `docs/rfcs/0049-striatum-evaluation-gates.md:806`.

- minor: RFC0048's suggested omission reason list does not include the
  `identity_leak` and `citation_leak` reasons that RFC0049 now requires for
  path, label, and citation leak handling. See
  `docs/rfcs/0048-striatum-context-injection-policy.md:262` and
  `docs/rfcs/0049-striatum-evaluation-gates.md:555`.

- nit: Downstream open-decision lists still treat the final redaction-state
  vocabulary as open even though RFC0045 now defines it. See
  `docs/rfcs/0045-striatum-corpus-contract-v2.md:646`,
  `docs/rfcs/0046-striatum-projection-index-schema.md:86`,
  `docs/rfcs/0048-striatum-context-injection-policy.md:143`, and
  `docs/rfcs/0049-striatum-evaluation-gates.md:158`.

- nit: `STRIATUM_MEMORY_ROADMAP.md` still says the immediate next step is to
  scaffold RFC0045 even though RFC0045-RFC0049 now exist and the operator routed
  the package through repair plus fresh re-review. See
  `STRIATUM_MEMORY_ROADMAP.md:248` and
  `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/OPERATOR_DECISION_CONTRACT_REPAIR.md:21`.

## Residual Risks

- All repaired artifacts remain proposal text. No migration, fixture, service
  path, sandbox, or packet-audit evidence exists yet.
- Level 3 default-on automatic injection remains correctly blocked until
  accepted/promoted RFC0045-RFC0048 successors exist and the RFC0049 gates pass.
- Exact per-instance `corpus_id`, `instance_id`, `repository_id`,
  Striatum-side privacy-tier assignment, and final fixture selection remain open
  proposal decisions.
- Vector retrieval remains optional/open for Level 3. Any promotion packet must
  name the enabled retrieval lanes and the declared embedding model/dimension set
  used for completeness checks.
- No-egress proof still depends on future OS-level sandbox evidence and accurate
  inventory of transitive local runtimes that receive corpus content.
- Generated memory products remain correctly blocked for Level 2 and Level 3
  injection until a separate accepted privacy-inheritance, citation, and audit
  contract exists.

## Recommendation

Striatum may replace/supersede the prior `needs_revision` contract-coherence
verdict with this `accept_with_findings` re-review verdict. The remaining major
findings should be repaired or explicitly scope-limited before RFC promotion or
implementation, but they do not justify preserving the prior blocking verdict.
