# Review: Striatum Memory Roadmap RFC Contract Coherence
author: operator [self-declared: roadmap-review-contract-coherence]

Verdict: needs_revision

## Scope

Reviewed dependency order, V2 contract completeness, projection readiness, and
evaluation traceability across RFC 0045, RFC 0046, and RFC 0049, with RFC 0044
acceptance findings and the Striatum memory roadmap as upstream constraints.

Read-only sub-agent lanes were used for dependency order, V2 contract,
projection schema, and evaluation gates. No writes were delegated.

## Findings

### CC-001 - blocking - V2 tenant/corpus identity is not a complete row contract

Affected: RFC 0045 Item Record Shape and Validation Rules; RFC 0046 Upstream
Contract Assumptions; RFC 0049 EG-010.

Rationale: RFC 0045 puts `tenant_id` and `corpus_id` only in
`manifest.memory_target`, while RFC 0046 and RFC 0049 treat tenant/corpus as
stable item or row fields and require row-level mismatch fixtures. RFC 0049
also asks for a multi-corpus fixture, which is ambiguous under a single
manifest-level `memory_target`.

Proposed fix: choose one authority model before promotion. Prefer adding
top-level `tenant_id` and `corpus_id` to every V2 item record and validating
them against the manifest. If rows inherit from the manifest instead, update
RFC 0046/RFC 0049 to remove row-level mismatch assumptions and model
multi-corpus tests as separate bundles.

### CC-002 - blocking - Bundle and lifecycle identity is underspecified

Affected: RFC 0045 Manifest Shape and Incremental Export Watermarks; RFC 0046
Projection Generation State.

Rationale: RFC 0046 requires `bundle_id` in projection generation keys, but RFC
0045 defines `bundle_sha256` and `previous_bundle_id` without defining the
current bundle ID or its uniqueness semantics. RFC 0045 also requires
tombstone/redaction records for incremental export but does not define their
record shape, target identity, content/hash rules, or lifecycle vocabulary.

Proposed fix: define `bundle_id` explicitly and state whether it is
producer-assigned or derived from the canonical manifest hash. Add a closed
lifecycle vocabulary such as `content`, `tombstone`, `redaction`, and
`withheld_marker`, with required target logical/version identity and hash
rules.

### CC-003 - blocking - RFC 0046 generation idempotency and active-set semantics conflict

Affected: RFC 0046 Projection Generation State, Projection Families unique
keys, and Incremental Bundle Handling.

Rationale: changed schema/code/input creates a new generation, but several
projection unique keys omit `generation_id`, so later generations of the same
V2 item collide with prior rows. Incremental handling also says changed rows
are inserted and affected logical IDs invalidated, while only one activated
generation is allowed per corpus/schema. The RFC does not state whether
unchanged rows are copied forward, remain active from older generations, or are
selected through a delta view.

Proposed fix: make per-table idempotency keys generation-scoped and add
separate partial active uniqueness for serving. Then choose one active-set
model: full-snapshot generations with carry-forward rows, or delta generations
with an active view keyed by latest active logical item.

### CC-004 - blocking - Retrieval-visible embedding rows lack invalidation and redaction state

Affected: RFC 0046 `striatum_chunk_embeddings`.

Rationale: vector rows are retrieval-visible but carry only tenant/corpus,
privacy tier, activity, and model metadata. They lack redaction state,
visibility, invalidation fields, source identity, hashes, and a concrete table
for the required local skip records. That weakens stale-index and withheld
content guarantees in RFC 0049.

Proposed fix: either copy the minimum serving and invalidation fields onto
embedding rows or define enforced joins plus health checks that prove stale or
withheld chunks cannot be returned. Add a concrete
`striatum_embedding_skips` table keyed by generation, chunk, model, and
dimension.

### CC-005 - blocking - RFC 0049 default-on promotion can outrun upstream contracts

Affected: RFC 0049 Level 3 Promotion Criteria and Gate Matrix.

Rationale: RFC 0049 states that it is not a shortcut around RFC 0045-0048, but
Level 3 only requires every automatic gate plus RFC 0048 promotion. It does
not explicitly require accepted/promoted successors for RFC 0045, RFC 0046, or
RFC 0047 even though the gates depend on their field names, health checks,
statuses, and request/response contracts.

Proposed fix: require accepted/promoted successors for RFC 0045, RFC 0046, RFC
0047, and RFC 0048 before Level 3. Dependent gates should report
`blocked_upstream` until those contracts are accepted.

### CC-006 - major - RFC 0046 is missing the RFC 0044 hardening prerequisite

Affected: RFC 0046 Roadmap Position; STRIATUM_MEMORY_ROADMAP Phase 0; RFC 0044
Final Synthesis follow-up queue.

Rationale: the roadmap says to finish RFC 0044 hardening before expanding the
surface. RFC 0046 projections depend directly on the hardening queue:
tenant/source-kind consistency, `fetch_reference` guards, real-bundle smoke
evidence, capability validation, uniform MCP errors, and reciprocal
Striatum-side independence.

Proposed fix: add a Dependencies section to RFC 0046 requiring RFC 0044 Phase
0 hardening or EG-000-equivalent evidence before migration/projection
implementation.

### CC-007 - major - V2 provenance and classification vocabularies are not closed enough

Affected: RFC 0045 Item Record Shape, Item Requirements, and Downstream
Requirements.

Rationale: downstream RFCs depend on issue, blocker, workflow, job, authority,
stability, and confidence metadata, but the base provenance object omits some
of those fields and classification semantics are partly proposed rather than
closed. Generated summaries require confidence, but the contract does not
mechanically define which records are generated.

Proposed fix: add the missing nullable provenance fields to the base shape and
define closed vocabularies or per-`sub_kind` rules for `authority_class`,
`stability_class`, `evidence_kind`, and confidence range/nullability.

### CC-008 - major - RFC 0049 Level 2 and failure actions are not mechanically traceable

Affected: RFC 0049 Gate Matrix.

Rationale: the matrix tracks Level 1 manual search and Level 3 default-on
injection, but Level 2 experimental automatic injection has separate
requirements and no column. Reviewers cannot mechanically tell whether a
failed gate blocks opt-in automatic injection, default-on injection, or only a
specific surface.

Proposed fix: add a Level 2 column and per-gate failure actions for `fail`,
`blocked_upstream`, and `accepted_with_scope_limit`.

### CC-009 - major - RFC 0049 no-egress evidence omits transitive model runtimes

Affected: RFC 0049 EG-020.

Rationale: the gate allows loopback access to Ollama or local model runtimes.
If corpus text is sent to a local model or embedding server, that server is
also a corpus-reading process. Probing only the caller does not prove D020
for the transitive runtime.

Proposed fix: require every process receiving corpus content, including
loopback model/embedding servers, to be covered by no-egress evidence or by a
separate sandbox probe. Static inspection should allow justified loopback HTTP
clients only when paired with that evidence.

### CC-010 - major - Golden-query and packet audit traceability are underspecified

Affected: RFC 0049 EG-070 and EG-110.

Rationale: RFC 0049 lists query families and thresholds but not minimum counts
or required coverage by RFC 0045 sub-kind, RFC 0046 projection family/lane, or
RFC 0048 purpose. EG-110 records selected and omitted references, but not the
projection row ID, chunk ID, chunk hash, lane, score, rank, and ranking inputs
needed to reconstruct exact automatic packet memory.

Proposed fix: add a machine-readable golden-query manifest with fixture IDs
and hashes, lane, purpose, expected/forbidden references, and minimum counts
per family. Extend audit evidence with projection row ID, chunk ID, chunk
hash, retrieval lane, score/rank, generation, and omission reason per
candidate.

## Required Review Notes

Dependency order: the intended order is coherent: RFC 0044 hardening, then RFC
0045 contract, RFC 0046 projections, RFC 0047/RFC 0048 retrieval and injection,
then RFC 0049 gates. The package does not yet enforce that order consistently:
RFC 0046 omits the RFC 0044 hardening prerequisite, and RFC 0049 Level 3 can
pass while RFC 0045-0047 remain proposals.

V2 contract completeness: RFC 0045 covers the right domains, but it is not
complete enough for promotion. The blocking gaps are tenant/corpus row
authority, current bundle identity, lifecycle record shapes for incremental
export, and downstream-stable provenance/classification vocabularies.

Projection readiness: RFC 0046 has the right projection families and local-only
posture, but it is not migration-ready. Generation keys, incremental active-set
semantics, bundle validation state, vector readiness, and embedding
invalidation/redaction state need revision before implementation.

RFC 0049 gate traceability: the gate taxonomy is strong and aligned with the
local-first constraints. It needs Level 2 traceability, upstream-contract
blocking rules, transitive no-egress evidence, a concrete golden-query
manifest, and row/chunk-level packet audit reconstruction before it can serve
as a promotion contract.

## Validation Evidence

Command:

```sh
git diff --check -- docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_contract_coherence.md
```

Result: passed with exit code 0 and no output.

Additional new-file check:

```sh
git diff --check --no-index -- /dev/null docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_contract_coherence.md
```

Result: no whitespace output; command exits nonzero because the file differs
from `/dev/null`.
