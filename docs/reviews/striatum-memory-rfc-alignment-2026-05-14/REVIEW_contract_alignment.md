author: operator [self-declared: alignment-review-contract]
verdict: accept_with_findings

# Striatum Memory RFC Alignment Contract Review

## Scope

Reviewed current contract alignment across:

- `docs/rfcs/0046-striatum-projection-index-schema.md`
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md`
- `docs/rfcs/0048-striatum-context-injection-policy.md`
- `docs/rfcs/0049-striatum-evaluation-gates.md`
- `STRIATUM_MEMORY_ROADMAP.md`
- `docs/rfcs/README.md`
- relevant synthesis, ledger, repair, and alignment handoffs under
  `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/` and
  `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/`

This review is read-only contract review. It does not promote an RFC, authorize
implementation, edit source artifacts, run Striatum publish/complete/verdict
commands, or change runtime behavior.

## Evidence Reviewed

- Canonical Engram constraints from `README.md`, `HUMAN_REQUIREMENTS.md`,
  `DECISION_LOG.md`, `BUILD_PHASES.md`, `ROADMAP.md`, `SPEC.md`, and
  `docs/schema/README.md`.
- RFC 0045 upstream contract text for proposal-only status, bundle identity,
  closed exact-reference vocabulary, redaction vocabulary, lifecycle rows,
  row-level tenant/corpus semantics, and dirty-working-tree rules.
- Current RFC 0046-RFC 0049 source text after the alignment pass.
- `STRIATUM_MEMORY_ROADMAP.md` and `docs/rfcs/README.md` for proposal/default-on
  posture.
- Prior review provenance: `FINAL_SYNTHESIS.md`, `FINDINGS_LEDGER.md`,
  `REVIEW_contract_coherence.md`, `REVIEW_contract_coherence_repair.md`,
  `REPAIR_RFC0046_PROJECTIONS.md`, and current alignment handoffs for RFC 0046,
  RFC 0047, RFC 0048, RFC 0049, plus roadmap/index cleanup.
- Five read-only sub-agent checks covering exact references, promotion/default-on
  gates, skip/provenance/audit semantics, roadmap/index wording, and prior
  finding closure.

## Blockers

None.

The current RFC source text resolves the previous safety blockers at
proposal-text level without authorizing implementation:

- RFC 0046 now carries RFC 0044 Phase 0 or EG-000-equivalent hardening as an
  implementation prerequisite (`docs/rfcs/0046-striatum-projection-index-schema.md:95`).
- RFC 0046 now includes `workflow_job_id` and `job_id` in the exact-reference
  vocabulary (`docs/rfcs/0046-striatum-projection-index-schema.md:352`) and in
  validation expectations (`docs/rfcs/0046-striatum-projection-index-schema.md:1035`).
- RFC 0046 now makes embedding skips active/invalidation-addressable
  (`docs/rfcs/0046-striatum-projection-index-schema.md:721`) and mirrors
  dirty-working-tree projection rules (`docs/rfcs/0046-striatum-projection-index-schema.md:539`).
- RFC 0047 now separates opaque `bundle_id` from `bundle_sha256`
  (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:292`) and requires
  unauthorized/no-data/pair-mismatch metadata redaction
  (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:347`).
- RFC 0048 now blocks routine default-on injection until accepted/promoted
  upstream successors and RFC 0049 Level 3 gates
  (`docs/rfcs/0048-striatum-context-injection-policy.md:657`).
- RFC 0049 blocks Level 3 default-on automatic injection until RFC 0045-RFC 0048,
  or accepted successors, are promoted and all automatic-required gates pass
  (`docs/rfcs/0049-striatum-evaluation-gates.md:270`).

## Nonblocking Findings

1. Major: RFC 0047 still lacks a mechanically complete exact-reference request
   shape. RFC 0046 projects a closed `ref_kind` vocabulary including
   `workflow_job_id`, `job_id`, `process_id`, `issue_id`, `blocker_id`,
   `source_hash`, and `bundle_id`
   (`docs/rfcs/0046-striatum-projection-index-schema.md:352`), and RFC 0049
   requires exact-reference coverage for every represented namespace with no
   lexical/vector fallback credit
   (`docs/rfcs/0049-striatum-evaluation-gates.md:660`). RFC 0047 exposes some
   filters in the JSON request example but not the whole closed vocabulary
   (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:211`). Before RFC
   0047 promotion or exact-lane implementation, add a generic
   `{ref_kind, ref_value}` filter or explicitly mirror RFC 0045/RFC 0046's exact
   vocabulary.

2. Major: retrieval-to-packet omission audit continuity is under-specified. RFC
   0047's response example includes `omitted` but does not define the omitted-entry
   schema or reason vocabulary
   (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:279`). RFC 0048
   requires ineligible results to be omitted with reason codes
   (`docs/rfcs/0048-striatum-context-injection-policy.md:261`), and RFC 0049
   requires selected and omitted candidate reconstruction with candidate ids,
   projection/chunk lineage, scores, ranks, and omission reasons
   (`docs/rfcs/0049-striatum-evaluation-gates.md:821`). This does not create a
   current runtime blocker because no implementation is authorized, but RFC 0047
   or a promotion successor should define `omitted[]` or an equivalent
   privacy-safe local audit event shape before automatic packet implementation.

3. Major: embedding skip completeness is stronger after alignment but still needs
   one promotion-level invariant. RFC 0046 requires complete embedding rows or
   skip rows before activation
   (`docs/rfcs/0046-striatum-projection-index-schema.md:292`) and later refers to
   the declared model/dimension set
   (`docs/rfcs/0046-striatum-projection-index-schema.md:906`), but the generation
   row does not persist that required embedding profile
   (`docs/rfcs/0046-striatum-projection-index-schema.md:238`). Embedding and skip
   rows also share the same logical key in separate tables
   (`docs/rfcs/0046-striatum-projection-index-schema.md:710`) without an explicit
   "exactly one active embedding or active skip" invariant. Add a persisted
   required embedding profile or equivalent activation manifest, plus an XOR
   health/activation rule per `(generation_id, chunk_id, model, dimension)`.

4. Minor: stale F017 redaction-open-decision text remains in RFC 0046 and RFC
   0048. RFC 0045 now closes `privacy.redaction_state` as `none`, `redacted`,
   `withheld`, or `synthetic_summary`
   (`docs/rfcs/0045-striatum-corpus-contract-v2.md:641`), but RFC 0046 and RFC
   0048 still list "final redaction-state vocabulary" as an open RFC 0045 decision
   (`docs/rfcs/0046-striatum-projection-index-schema.md:81`;
   `docs/rfcs/0048-striatum-context-injection-policy.md:137`). RFC 0049 appears
   cleaned up on this point.

5. Minor: RFC 0049 still says `identity_leak` and `citation_leak` are gate-local
   until RFC 0048 reconciles them
   (`docs/rfcs/0049-striatum-evaluation-gates.md:568`), but RFC 0048 now defines
   those omission codes
   (`docs/rfcs/0048-striatum-context-injection-policy.md:264`). This is stale
   wording, not a behavioral contradiction.

6. Minor: no-egress HTTP wording is uneven across RFC 0047 and RFC 0049. RFC 0049
   correctly distinguishes external/non-loopback/unpaired HTTP dependencies from
   paired loopback/local runtimes with no-egress evidence
   (`docs/rfcs/0049-striatum-evaluation-gates.md:426`). RFC 0047 still states
   "no HTTP client for corpus-serving paths" while later allowing future reviewed
   loopback HTTP
   (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:423`). Aligning
   the wording would reduce gate interpretation friction.

7. Minor: roadmap and RFC-index "current follow-up" language is accurate about
   proposal-only status, but slightly stale now that alignment handoffs exist.
   The roadmap says the immediate next step is completing RFC alignment cleanup
   (`STRIATUM_MEMORY_ROADMAP.md:254`), and the RFC index says current follow-up is
   RFC alignment plus RFC 0044 hardening/EG-000 evidence
   (`docs/rfcs/README.md:65`). Since the RFC 0046-RFC 0049 handoffs now record
   scoped alignment completion, the next promotion packet should say whether the
   alignment handoffs are accepted and then move to RFC 0044 hardening/EG-000
   evidence.

8. Minor: RFC 0047 occasionally overstates RFC 0045 as accepted authority. RFC
   0045 is still `Status | proposal` and `Implementation | none`
   (`docs/rfcs/0045-striatum-corpus-contract-v2.md:5`), while RFC 0047 says RFC
   0045 "defines" the V2 bundle and that the "versioned corpus contract wins"
   (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:41`;
   `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:122`). The nearby
   review-target language prevents a current overclaim, but promotion cleanup
   should say "proposes" or "accepted successor wins."

## Deferred Items

- RFC 0044 hardening or EG-000-equivalent evidence remains required before any
  projection, retrieval, or operator-context implementation depends on the
  current Striatum substrate.
- RFC 0045-RFC 0048 remain proposal material until a recorded project decision,
  accepted spec, or promoted successor makes them binding.
- Routine Level 3 default-on automatic memory remains blocked by RFC 0049 until
  accepted/promoted upstream contracts and passing gates exist.
- Generated memory products remain blocked from Level 2 and Level 3 injection
  until a separate accepted privacy-inheritance, citation, audit, and gate
  contract exists.
- The audit storage home remains an implementation decision. Existing generated
  schema docs show `projection_audits` without Striatum tenant/corpus,
  projection-generation, selected/omitted candidate, or privacy-tier fields
  (`docs/schema/README.md:370`), while RFC 0046 leaves open whether to extend it
  or add a Striatum-specific audit table
  (`docs/rfcs/0046-striatum-projection-index-schema.md:1132`).
- Collapsed no-data status ergonomics remain a deferred UX issue rather than a
  contract blocker.

## Workflow Friction

- Five read-only sub-agents were used. All completed. Four reported no blockers;
  one classified embedding skip completeness and retrieval omission shape as
  blockers. This review carries those as major nonblocking findings because the
  current source text is proposal-only, RFC 0049 still blocks implementation and
  default-on use, and the issues are promotion/implementation-contract gaps rather
  than currently unsafe runtime behavior.
- The roadmap synthesis and findings ledger predate the alignment handoffs, so
  some "still unresolved" findings in the older ledger are stale relative to the
  current RFC source text. The current RFC bodies plus
  `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/` handoffs are the most
  accurate alignment layer.
- The workflow has two similarly named review roots:
  `striatum-memory-roadmap-rfcs-2026-05-14/` for the original synthesis/ledger
  and `striatum-memory-rfc-alignment-2026-05-14/` for current alignment handoffs.
  Several handoffs note that prompt-named review inputs were absent under the
  Striatum run directory and were read from `docs/reviews/...` instead.
- The shared worktree was already dirty, including out-of-scope changes to
  `CHANGELOG.md`, `OPERATOR_REPORT.md`, RFC source files, roadmap/index files,
  and untracked alignment directories. This reviewer wrote only this review
  artifact.
