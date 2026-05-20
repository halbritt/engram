<a id="rfc-0046"></a>

# RFC 0046: Engram Striatum Projection And Index Schema

| Field | Value |
|-------|-------|
| RFC | RFC-0046 |
| Title | Engram Striatum Projection And Index Schema |
| Status | accepted_as_design_reference |
| Implementation | landed via Layers 1-5 of `STRIATUM_MEMORY_E2E_BACKLOG.md` (migration 015, `MemoryService`) |
| Created | 2026-05-14 |
| Source | `STRIATUM_MEMORY_ROADMAP.md` |
| Context | RFC 0044, RFC 0045, `STRIATUM_MEMORY_ROADMAP.md`, `docs/schema/README.md` |

## Summary

This RFC is accepted as the design reference for the Engram-side derived schema
used by the landed Striatum memory pipeline. It proposes the projection shape
for Striatum Corpus Contract V2
bundles. It turns validated Striatum raw evidence into rebuildable projection
families and local indexes for exact reference lookup, structured filtering, and
future layered retrieval.

Raw Striatum evidence remains append-only under `tenant_id='striatum'`.
Projection rows are caches over that evidence. They must cite V2 item identity,
raw Engram capture rows, hashes, privacy/redaction metadata, and derivation
versions so they can be invalidated, rebuilt, audited, and superseded without
rewriting raw evidence.

This RFC began as a schema handoff; D083 later accepted it as design reference
after the corresponding projection, retrieval, packet, gate, and MCP smoke
layers landed. It does not authorize cloud/hosted dependencies.

## Roadmap Position

RFC 0046 follows RFC 0045 and precedes:

- RFC 0047, retrieval augmentation boundary;
- RFC 0048, context-injection budgets and packet policy;
- RFC 0049, smoke, no-egress, isolation, stale-index, and retrieval-quality gates;
- implementation lanes for Striatum V2 export and Engram ingestion/projection.

RFC 0045 is the upstream file contract. RFC 0046 only operates on validated V2
raw rows. RFC 0044 V1 bundles remain raw-only input unless an explicit
compatibility adapter supplies the required V2 fields and is reviewed separately.

## Goals

1. Define derived projection families for V2 Striatum evidence.
2. Define common columns for provenance, privacy, tenant/corpus boundaries,
   derivation versioning, active state, and raw evidence references.
3. Define rebuild and activation semantics that preserve idempotency and prevent
   stale rows from serving after privacy/redaction or content changes.
4. Define exact, structured, lexical, and local pgvector index requirements.
5. Define validation fixtures and acceptance criteria for later implementation.
6. Preserve Engram's local-only/no-egress/no-telemetry constraints.

## Non-Goals

- No Striatum exporter implementation.
- No Striatum bundle schema replacement.
- No additional migration or generated schema-doc change beyond the landed
  scoped implementation unless a future change needs it.
- No MCP tool expansion beyond the landed packet/retrieval surfaces unless a
  later RFC accepts it.
- No retrieval-ranking or context-injection policy.
- No claim/belief creation from Striatum evidence in this pass.
- No personal-memory projection redesign.
- No hosted embedding, hosted reranking, telemetry, remote persistence, or cloud
  DLP/classification service.

## Upstream Contract Assumptions

RFC 0046 assumes RFC 0045 provides these stable V2 item fields:

- `tenant_id`, `corpus_id`, `source_kind`, and `sub_kind`;
- `item_id`, `logical_id`, and `version_id`;
- `content`, `content_sha256`, and `record_sha256`;
- `observed_at`, `recorded_at`, and `emitted_at`;
- retraceable provenance fields such as path, logical path, commit, run id,
  workflow id, workflow job id, job id, process id, artifact id, issue id,
  blocker id, and dirty-working-tree state;
- `privacy`, `visibility`, `classification`, and `links`.

Open RFC 0045 decisions remain upstream decisions, not hidden RFC 0046 choices:

1. exact per-instance `corpus_id` grammar;
2. source of `identity.instance_id` and `identity.repository_id`;
3. zero-row required files versus manifest-declared omitted streams;
4. full diff/stdout export depth;
5. final redaction-state vocabulary;
6. one-file-per-sub-kind versus sharded item layout;
7. compatibility adapter ownership;
8. fixture bundle selection for RFC 0049.

If any of those decisions change field names or required semantics, RFC 0046's
projection implementation and this design reference must be revised together.

## Dependencies And Implementation Prerequisites

D083 accepted this RFC as design reference after migration 015 and the
projection, retrieval, packet, gate, and e2e smoke slices landed. Future
projection changes must preserve or refresh the hardening evidence below and
update this RFC when code drifts:

- primary-pair semantics for Striatum reads, including
  `memory.read_cross_corpus` and `memory.read_cross_tenant` requirements for
  non-primary pairs;
- `engram.fetch_reference` reauthorization against the stored row's
  `tenant_id`, `corpus_id`, `source_kind`, and `source_capture_id`;
- structural or service-level guardrails tying Striatum tenant rows to
  `source_kind='striatum'` before content is returned;
- uniform unauthorized/not-found/malformed reference failures at the MCP
  boundary, including decoded UUID validation before database lookup;
- validation of known `memory.*` capability names;
- MCP frame content-length limits and JSON-RPC parse-error behavior;
- schema-version reporting by numeric migration prefix or applied ordering;
- real or committed fixture Striatum export smoke evidence, not only synthetic
  rows;
- reciprocal Striatum-side evidence that Striatum does not import Engram client
  code, does not require an Engram daemon/RPC dependency, and degrades
  gracefully when Engram is unavailable;
- honest no-egress evidence for the corpus-reading paths used by the projection
  worker and local embedding path.

RFC 0046 also remains blocked on RFC 0045's final row, bundle, and lifecycle
contract. In particular, projection implementation must not invent authority for
row-level `tenant_id`/`corpus_id`, `bundle_id`, tombstone records, redaction
records, or lifecycle vocabulary if RFC 0045 has not accepted those semantics.

## Design Principles

- Raw evidence is canonical. Projection rows are derived, rebuildable, and
  disposable.
- Every projection row carries `tenant_id` and `corpus_id`. No read path may infer
  them from display strings, shorthand, or bundle labels.
- Every query and index that can cross boundaries includes `tenant_id` and
  `corpus_id` in the leading filter or partial-index predicate.
- Every projection row cites raw evidence through Engram `captures.id` and the
  upstream V2 item identity.
- Privacy and redaction metadata are copied onto retrieval-visible rows so stale
  low-tier chunks or embeddings cannot remain queryable after reclassification.
- Projection jobs are corpus-reading processes. They run locally, use local
  PostgreSQL and local model runtimes only, and have no outbound network.
- Exact and structured lookup are first-class. Vector search is additive and must
  never be the only way to retrieve a known run id, file path, RFC id, issue id,
  artifact id, or commit SHA.

## Common Projection Columns

Every first-class projection table proposed below carries these columns unless
explicitly noted:

| Column | Purpose |
|--------|---------|
| `id UUID PRIMARY KEY` | Engram-local projection row identity. |
| `generation_id UUID NOT NULL` | Projection generation that produced the row. |
| `tenant_id TEXT NOT NULL` | Must be `striatum` for this RFC's tables. |
| `corpus_id TEXT NOT NULL` | Striatum corpus boundary; never `personal`. |
| `source_capture_id UUID NOT NULL` | Raw Engram capture that stores the V2 item. |
| `source_kind TEXT NOT NULL` | Copied from RFC 0045 `source_kind`; must be `striatum` for rows proposed by this RFC. |
| `source_item_id TEXT NOT NULL` | RFC 0045 exact-version `item_id`. |
| `source_logical_id TEXT NOT NULL` | RFC 0045 stable conceptual `logical_id`. |
| `source_version_id TEXT NOT NULL` | RFC 0045 `version_id`. |
| `source_sub_kind TEXT NOT NULL` | RFC 0045 `sub_kind`. |
| `source_dirty_working_tree BOOLEAN NOT NULL` | Copied from RFC 0045 `provenance.dirty_working_tree`; dirty evidence remains filterable and audit-visible. |
| `content_sha256 TEXT NOT NULL` | Hash of the indexable/citable content. |
| `record_sha256 TEXT NOT NULL` | Hash of the canonical V2 item record. |
| `observed_at TIMESTAMPTZ NOT NULL` | Source state observation time. |
| `recorded_at TIMESTAMPTZ NOT NULL` | Striatum record/materialization time. |
| `emitted_at TIMESTAMPTZ NOT NULL` | Bundle emission time. |
| `privacy_tier INT NOT NULL` | Effective tier copied from V2 privacy metadata. |
| `redaction_state TEXT NOT NULL` | RFC 0045 redaction state. |
| `visibility JSONB NOT NULL` | V2 default visibility and required capabilities. |
| `authority_class TEXT NOT NULL` | V2 classification authority class. |
| `stability_class TEXT NOT NULL` | V2 classification stability class. |
| `confidence FLOAT NULL` | V2 supplied confidence for generated/derived items. |
| `is_active BOOLEAN NOT NULL` | Retrieval-visible flag after generation activation. |
| `invalidated_at TIMESTAMPTZ NULL` | Set when this row must no longer serve. |
| `invalidation_reason TEXT NULL` | `privacy_reclassification`, `redaction`, `tombstone`, `superseded`, `rebuild`, or implementation-specific reason. |
| `carried_forward_from_id UUID NULL` | Prior projection row copied into this full-snapshot generation, when applicable. |
| `raw_payload JSONB NOT NULL` | Source-specific details and preserved optional fields. |

Implementation may factor the common fields into helper SQL or Python row
builders, but the physical tables should keep explicit columns for reviewable
indexes and boundary tests.

### `raw_payload` Privacy Inheritance Rule

Every projection `raw_payload` value inherits the parent item's
`privacy.privacy_tier`, `privacy.redaction_state`, `privacy.withheld_fields`,
and `visibility` (`visibility.default_visible_to` and
`visibility.requires_capabilities`) as exported by RFC 0045. No field whose
presence would exceed those constraints may live in `raw_payload`. In
particular:

- `raw_payload` must not carry hidden body text, withheld field values,
  pre-redaction content, operator-private absolute paths, or any data above
  the parent item's `privacy.privacy_tier`;
- `raw_payload` must not be used to smuggle identity, label, path, or
  reference fields that the parent item's `visibility` constraints would
  hide from the caller;
- when the parent item's `privacy.redaction_state` is `redacted`, `withheld`,
  or `synthetic_summary`, `raw_payload` must remain consistent with that
  state and must not reintroduce material the parent redacted;
- privacy reclassification of the parent item invalidates `raw_payload` on
  the affected projection rows together with the row itself.

Retrieval-visible `raw_payload`-derived fields above the caller's authorized
privacy tier, redaction state, or visibility are forbidden. RFC 0047 must not
expose `raw_payload`-derived fields to a response unless the upstream contract
whitelists them, and RFC 0048 must not inject `raw_payload`-derived content
that would exceed the caller's tier or violate the parent item's visibility.
RFC 0049 EG-060 carries the matching gate fixture.

This rule applies uniformly to every projection family proposed in this RFC,
including `striatum_items`, `striatum_references`, `striatum_documents`,
`striatum_runs`, `striatum_agents`, `striatum_artifacts`, `striatum_git_refs`,
`striatum_issues`, `striatum_links`, `striatum_chunks`,
`striatum_chunk_embeddings`, and `striatum_embedding_skips`. It composes with
the existing narrow rules already stated for dirty-working-tree audit hints
and `striatum_embedding_skips.raw_payload`; those narrow rules remain in
force.

### Mechanical Provenance And Authorization Rule

Retrieval-visible projection rows do not inherit authorization-critical source
identity solely through joins. They store the source identity directly, then use
joins as consistency checks.

For every retrieval-visible row family proposed in this RFC, the rule is:

| Row family | `source_capture_id` | `source_kind` | `source_sub_kind` |
|------------|---------------------|---------------|-------------------|
| First-class item/structured projection rows, including `striatum_items`, `striatum_documents`, `striatum_runs`, `striatum_agents`, `striatum_artifacts`, `striatum_git_refs`, `striatum_issues`, and `striatum_links` | Direct copied column from the validated V2 item capture. | Direct copied column from the validated V2 item; must be `striatum`. | Direct copied column from the validated V2 item. |
| `striatum_references` | Direct copied column; `item_projection_id` must match it but is not the source of authority. | Direct copied column; must match `striatum_items.source_kind` through `item_projection_id`. | Direct copied column; must match `striatum_items.source_sub_kind` through `item_projection_id`. |
| `striatum_chunks` | Direct copied column; `item_projection_id` must match it but is not the source of authority. | Direct copied column; must match `striatum_items.source_kind` through `item_projection_id`. | Direct copied column; must match `striatum_items.source_sub_kind` through `item_projection_id`. |
| `striatum_chunk_embeddings` | Direct copied column from the active chunk/item row. | Direct copied column from the active chunk/item row; must be `striatum`. | Direct copied column from the active chunk/item row. |
| `striatum_embedding_skips` | Direct copied column from the active chunk/item row. | Direct copied column from the active chunk/item row; must be `striatum`. | Direct copied column from the active chunk/item row. |

Mandatory joins still apply before a row can serve. Reference and chunk rows must
join to their item row in the same generation and authorized `(tenant_id,
corpus_id)`. Embedding and skip rows must join to their chunk and item rows in
the same generation and authorized `(tenant_id, corpus_id)`. The copied fields
and joined fields must match for `source_capture_id`, `source_kind`,
`source_item_id`, `source_logical_id`, `source_version_id`, `source_sub_kind`,
privacy tier, redaction state, dirty-working-tree state, content hash, and
record hash. A mismatch is a malformed or stale projection condition and must
fail closed; it is not resolved by choosing one side of the join.

Future `fetch_reference` implementations must authorize against the stored
candidate row's direct `tenant_id`, `corpus_id`, `source_kind`,
`source_capture_id`, privacy tier, redaction state, and visibility before any
content lookup. If the candidate row is a reference, chunk, embedding, or skip
row, the implementation must also perform the mandatory same-generation joins
above and fail closed on mismatch. Joins may narrow or invalidate access; they
must not grant access that the candidate row's direct copied fields would deny.

## Generation-Scoped Keys And Active Serving Model

RFC 0046 chooses the full-snapshot generation model.

Every activated generation owns a complete serving set for one
`(tenant_id, corpus_id, projection_schema_version)` pair. Incremental bundles
may be implemented as deltas internally, but activation still materializes a
complete new projection generation by copying forward unchanged active rows from
the prior generation and writing changed, tombstoned, or redacted rows according
to the new V2 evidence.

Physical projection-table idempotency is generation-scoped:

```text
(generation_id, <projection-family natural key suffix>)
```

The natural key suffixes listed in the projection-family sections below are not
global unique keys. A later generation may contain the same `source_item_id`,
`source_logical_id`, `run_id`, `artifact_id`, `ref_kind/ref_value_normalized`,
or chunk hash without colliding with prior rows because its `generation_id` is
different.

Serving uniqueness is a separate active-row invariant. Retrieval, health checks,
and future service paths must read from active serving views or equivalent query
builders that restrict to:

```text
generation_id = <the activated generation for tenant/corpus/schema>
AND is_active
AND invalidated_at IS NULL
```

Within that active serving set, partial unique indexes or view-level validation
must ensure that the serving identity for each projection family is unique for
the authorized `(tenant_id, corpus_id)` pair. Base tables are not serving
surfaces. A direct query over base tables is stale/diagnostic unless it applies
the active serving rule above.

Activation is all-or-prior for the declared serving lanes. If a new generation
cannot satisfy required rows, required chunks, or required local embedding/skip
records, the prior generation remains the active serving set. The implementation
must not silently mix current exact/lexical rows with prior-generation vector
rows and present the result as fresh.

## Projection Generation State

Add a generation table for projection build state:

### `striatum_projection_generations`

One row per projection rebuild attempt.

Required columns:

- `id UUID PRIMARY KEY`;
- `tenant_id TEXT NOT NULL`;
- `corpus_id TEXT NOT NULL`;
- `bundle_id TEXT NOT NULL`;
- `contract_version TEXT NOT NULL`;
- `projection_schema_version TEXT NOT NULL`;
- `projection_code_version TEXT NOT NULL`;
- `input_manifest_sha256 TEXT NOT NULL`;
- `input_item_count INT NOT NULL`;
- `status TEXT NOT NULL`;
- `started_at TIMESTAMPTZ NOT NULL`;
- `completed_at TIMESTAMPTZ NULL`;
- `activated_at TIMESTAMPTZ NULL`;
- `superseded_at TIMESTAMPTZ NULL`;
- `error_count INT NOT NULL DEFAULT 0`;
- `last_error TEXT NULL`;
- `parent_generation_id UUID NULL`;
- `required_embedding_profile JSONB NOT NULL DEFAULT '{}'::jsonb`;
- `raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb`.

The `required_embedding_profile` column persists the activation manifest that
declares which `(embedding_model_version, embedding_dimension)` lanes this
generation must satisfy before activation. It is the authoritative input to the
embedding/skip XOR invariant described in
[Embedding Activation Invariant](#embedding-activation-invariant). The minimal
proposed shape, subject to later contract review, is:

```text
{
  "version": "1",
  "models": [
    {
      "embedding_model_version": "<text>",
      "embedding_dimension": "<int>",
      "lane": "<text>",                          // serving lane label, e.g. "vector_primary"
      "required": "<bool>",                      // true when activation must satisfy this lane
      "policy_source": "<text>"                  // why this lane is in the manifest, e.g. "default_profile", "operator_opt_in"
    }
  ],
  "selected_at": "<timestamptz>",
  "selected_by": "<text>"                        // operator id or worker identity that froze the profile
}
```

`models[]` is closed for the duration of a generation: once a generation row is
written, its required embedding profile is immutable. Changing the profile
requires a new generation. Profile shape, additional keys, lane vocabulary, and
the exact JSON schema remain proposal subject to later contract review during
RFC 0046 promotion.

Status vocabulary:

```text
pending
building
ready
activated
superseded
failed
abandoned
```

Uniqueness:

- unique `(tenant_id, corpus_id, bundle_id, projection_schema_version,
  projection_code_version, input_manifest_sha256)`;
- at most one current `activated` generation with `superseded_at IS NULL` per
  `(tenant_id, corpus_id, projection_schema_version)`.

Idempotency rule:

The projection worker key is:

```text
(tenant_id, corpus_id, bundle_id, projection_schema_version,
 projection_code_version, input_manifest_sha256)
```

Re-running the same key must be a no-op or resume the same generation. Changed
input, schema, or code version creates a new generation. Projection-family
writes inside a generation are idempotent by `(generation_id, natural key
suffix)`, not by tenant/corpus/source keys alone.

Activation is atomic for the declared serving lanes: all required projection
rows, required chunks, and required embedding rows or embedding skip rows for
that generation are present before `is_active=true` rows become queryable. A
failed activation leaves the prior generation active and marks the candidate
generation `failed` or `abandoned`.

## Projection Families

The proposed schema uses Striatum-specific table names for v1 to avoid a broad
generic application-memory abstraction. The common column contract above is the
reuse point for future local application memories.

### `striatum_items`

Canonical per-V2-item projection. This is the anchor for exact lookup and
cross-table joins.

Additional columns:

- `logical_id TEXT NOT NULL`;
- `version_id TEXT NOT NULL`;
- `title TEXT NULL`;
- `summary_text TEXT NULL`;
- `content_text TEXT NOT NULL`;
- `content_length INT NOT NULL`;
- `source_path TEXT NULL`;
- `logical_path TEXT NULL`;
- `line_start INT NULL`;
- `line_end INT NULL`;
- `commit_sha TEXT NULL`;
- `run_id TEXT NULL`;
- `workflow_id TEXT NULL`;
- `workflow_job_id TEXT NULL`;
- `job_id TEXT NULL`;
- `process_id TEXT NULL`;
- `artifact_id TEXT NULL`;
- `issue_id TEXT NULL`;
- `blocker_id TEXT NULL`;
- `source_links JSONB NOT NULL DEFAULT '{}'::jsonb`.

Generation-scoped idempotency key suffixes:

- `(tenant_id, corpus_id, source_item_id)`;
- `(tenant_id, corpus_id, source_logical_id, source_version_id)`.

### `striatum_references`

Normalized exact-reference index. One V2 item can emit many references.

Columns:

- common provenance columns, including direct copied `source_capture_id`,
  `source_kind`, and `source_sub_kind`;
- `item_projection_id UUID NOT NULL`;
- `ref_kind TEXT NOT NULL`;
- `ref_value TEXT NOT NULL`;
- `ref_value_normalized TEXT NOT NULL`;
- `ref_scope TEXT NULL`;
- `ref_payload JSONB NOT NULL DEFAULT '{}'::jsonb`.

Reference kinds:

```text
item_id
logical_id
version_id
path
logical_path
rfc_id
decision_id
review_id
run_id
workflow_id
workflow_job_id
job_id
agent_process_id
artifact_id
issue_id
blocker_id
commit_sha
branch
tag
source_hash
bundle_id
```

Generation-scoped idempotency key suffix:

- `(tenant_id, corpus_id, ref_kind, ref_value_normalized, item_projection_id)`.

This table is the primary target for "find RFC 0044", "fetch run
`run_...`", "show artifacts touching `docs/schema/README.md`", and commit/issue
lookup. It is also where shorthand bugs are easiest to catch because a query
without explicit `tenant_id` and `corpus_id` should be treated as invalid in the
service layer.

Path and reference privacy rules:

- `ref_kind in ('path', 'logical_path')`, `striatum_items.source_path`,
  `striatum_items.logical_path`, `striatum_artifacts.path`,
  `striatum_artifacts.logical_path`, `striatum_chunks.path`, and
  `striatum_git_refs.changed_paths` are repository-relative by default.
- Absolute paths, operator home-directory prefixes, private checkout parents,
  and other operator-local filesystem details must be rejected or sanitized at
  projection time unless RFC 0045 supplies an explicit operator opt-in in the
  manifest and the resulting path fields inherit the appropriate privacy tier,
  redaction state, and visibility metadata.
- Reference values are scoped to `(tenant_id, corpus_id)`. Path names,
  branch/tag names, issue IDs, artifact IDs, and opaque `reference_id` payloads
  are not globally authoritative and are never authorization grants.
- Future `fetch_reference` implementations must reauthorize the stored
  projection row's direct copied `tenant_id`, `corpus_id`, `source_kind`,
  `source_capture_id`, privacy tier, redaction state, and visibility before
  returning content, then verify mandatory same-generation joins to the item row.
  Collision-shaped personal-memory and Striatum references must fail closed.

### `striatum_documents`

Structured projection for document-like evidence:

- `rfc`;
- `design`;
- `decision_log_row`;
- `operator_report`;
- `changelog_entry`;
- `review`;
- `synthesis`;
- `handoff`;
- `prompt`;
- `packet`;
- `ubiquitous_language_term`;
- `harness_friction_pattern`.

Additional columns:

- `document_kind TEXT NOT NULL`;
- `document_id TEXT NOT NULL`;
- `document_status TEXT NULL`;
- `title TEXT NULL`;
- `section_id TEXT NULL`;
- `section_title TEXT NULL`;
- `author TEXT NULL`;
- `verdict TEXT NULL`;
- `severity TEXT NULL`;
- `decision_status TEXT NULL`;
- `target_ref_kind TEXT NULL`;
- `target_ref_value TEXT NULL`;
- `body_text TEXT NOT NULL`.

Generation-scoped idempotency key suffix:

- `(tenant_id, corpus_id, document_kind, document_id, source_item_id)`.

### `striatum_runs`

Projection for `run_summary` and `workflow_run`.

Additional columns:

- `run_id TEXT NOT NULL`;
- `workflow_id TEXT NULL`;
- `workflow_job_id TEXT NULL`;
- `job_id TEXT NULL`;
- `session_id TEXT NULL`;
- `lease_id TEXT NULL`;
- `run_status TEXT NOT NULL`;
- `started_at TIMESTAMPTZ NULL`;
- `ended_at TIMESTAMPTZ NULL`;
- `operator TEXT NULL`;
- `objective TEXT NULL`;
- `result_summary TEXT NULL`;
- `failure_summary TEXT NULL`.

Generation-scoped idempotency key suffix:

- `(tenant_id, corpus_id, run_id, source_item_id)`.

### `striatum_agents`

Projection for `agent_process` and agent log summaries.

Additional columns:

- `process_id TEXT NOT NULL`;
- `run_id TEXT NULL`;
- `workflow_job_id TEXT NULL`;
- `job_id TEXT NULL`;
- `agent_role TEXT NULL`;
- `agent_model TEXT NULL`;
- `adapter_kind TEXT NULL`;
- `status TEXT NOT NULL`;
- `started_at TIMESTAMPTZ NULL`;
- `ended_at TIMESTAMPTZ NULL`;
- `exit_code INT NULL`;
- `summary_text TEXT NULL`.

Generation-scoped idempotency key suffix:

- `(tenant_id, corpus_id, process_id, source_item_id)`.

### `striatum_artifacts`

Projection for `artifact_manifest` and `generated_artifact`.

Additional columns:

- `artifact_id TEXT NOT NULL`;
- `artifact_kind TEXT NOT NULL`;
- `path TEXT NULL`;
- `logical_path TEXT NULL`;
- `content_type TEXT NULL`;
- `producer_run_id TEXT NULL`;
- `producer_process_id TEXT NULL`;
- `artifact_status TEXT NULL`;
- `artifact_sha256 TEXT NULL`;
- `summary_text TEXT NULL`.

Generation-scoped idempotency key suffix:

- `(tenant_id, corpus_id, artifact_id, source_item_id)`.

### `striatum_git_refs`

Projection for `commit` and `git_diff_summary`.

Additional columns:

- `git_ref_kind TEXT NOT NULL`;
- `commit_sha TEXT NULL`;
- `parent_shas TEXT[] NOT NULL DEFAULT '{}'::text[]`;
- `branch_name TEXT NULL`;
- `tag_name TEXT NULL`;
- `author_name TEXT NULL`;
- `author_email_hash TEXT NULL`;
- `committed_at TIMESTAMPTZ NULL`;
- `subject TEXT NULL`;
- `changed_paths TEXT[] NOT NULL DEFAULT '{}'::text[]`;
- `diff_summary TEXT NULL`.

`author_email_hash` stores a local hash when email must be searchable without
copying a full address into lower-tier projections.

Generation-scoped idempotency key suffix:

- `(tenant_id, corpus_id, git_ref_kind, commit_sha, source_item_id)` for commit
  rows where `commit_sha IS NOT NULL`;
- `(tenant_id, corpus_id, source_item_id)` otherwise.

Dirty working tree projection rules:

- RFC 0046 operates only on RFC 0045-validated rows. A bundle with
  `identity.git_dirty=true` but no manifest-level operator opt-in, or a dirty
  item without `provenance.dirty_working_tree=true`, fails before projection.
- Projection rows derived from dirty evidence copy
  `source_dirty_working_tree=true` onto retrieval-visible rows, including
  references, git refs, artifacts, chunks, chunk embeddings, and embedding skip
  rows. `raw_payload` may preserve the local opt-in identifier for audit, but it
  must not leak hidden diff/stdout content or operator-private paths.
- Dirty evidence must not be presented as clean committed state. Exact lookups,
  citations, health checks, and future packet builders must be able to
  distinguish dirty working-tree evidence from evidence tied only to committed
  Git objects.

### `striatum_issues`

Projection for `issue` and `blocker`.

Additional columns:

- `tracker_kind TEXT NOT NULL`;
- `issue_id TEXT NULL`;
- `blocker_id TEXT NULL`;
- `status TEXT NOT NULL`;
- `severity TEXT NULL`;
- `owner TEXT NULL`;
- `opened_at TIMESTAMPTZ NULL`;
- `closed_at TIMESTAMPTZ NULL`;
- `title TEXT NULL`;
- `summary_text TEXT NULL`;
- `related_run_id TEXT NULL`;
- `related_artifact_id TEXT NULL`.

Generation-scoped idempotency key suffix:

- `(tenant_id, corpus_id, tracker_kind, coalesce(issue_id, blocker_id),
  source_item_id)`.

### `striatum_links`

Materialized cross-link graph among V2 items and projection families.

Columns:

- common provenance columns;
- `source_projection_kind TEXT NOT NULL`;
- `source_projection_id UUID NOT NULL`;
- `link_kind TEXT NOT NULL`;
- `target_ref_kind TEXT NOT NULL`;
- `target_ref_value TEXT NOT NULL`;
- `target_projection_kind TEXT NULL`;
- `target_projection_id UUID NULL`;
- `link_confidence FLOAT NULL`;
- `link_payload JSONB NOT NULL DEFAULT '{}'::jsonb`.

Generation-scoped idempotency key suffix:

- `(tenant_id, corpus_id, source_projection_kind, source_projection_id,
  link_kind, target_ref_kind, target_ref_value)`.

Link kinds:

```text
parent
related
supersedes
superseded_by
produced
reviewed
accepted
deferred
rejected
blocked_by
unblocked_by
mentions
touches_path
touches_commit
touches_issue
```

Materialization rule:

- RFC 0045 `links.parent_ids`, `related_ids`, `supersedes`, and `superseded_by`
  are always materialized.
- Extracted exact references from content are materialized only for the closed
  `ref_kind` vocabulary in `striatum_references`.
- Semantic or inferred relationships are out of scope unless a future local
  reviewer/auditor RFC supplies confidence, model/prompt version, and audit
  evidence.

### `striatum_chunks`

Deterministic retrieval chunks over V2 `content`. Chunks are required for lexical
and vector retrieval, but vector embedding population is local-only and may be
deferred by implementation phase.

Additional columns:

- `item_projection_id UUID NOT NULL`;
- `chunk_index INT NOT NULL`;
- `chunk_kind TEXT NOT NULL`;
- `chunk_text TEXT NOT NULL`;
- `chunk_sha256 TEXT NOT NULL`;
- `token_estimate INT NULL`;
- `path TEXT NULL`;
- `line_start INT NULL`;
- `line_end INT NULL`;
- `source_offset_start INT NULL`;
- `source_offset_end INT NULL`;
- `chunker_version TEXT NOT NULL`.

Chunk kinds:

```text
markdown_section
log_entry
diff_summary
artifact_excerpt
record_summary
redaction_notice
```

Generation-scoped idempotency key suffix:

- `(tenant_id, corpus_id, item_projection_id, chunker_version, chunk_index)`;
- `(tenant_id, corpus_id, chunk_sha256, chunker_version, item_projection_id)`.

Chunking is deterministic and parser-driven. It must not require an LLM. Markdown
sections, bounded log entries, bounded diff summaries, and artifact excerpts use
source-aware chunkers. Fully withheld items still produce a deterministic
`redaction_notice` chunk so retrieval can represent known absence without
leaking content.

Embedding input is limited to the stored `striatum_chunks.chunk_text`. A fully
withheld source body must never be sent to a local embedding runtime before
substitution. If a chunk is a deterministic `redaction_notice`, the embedding
input is that notice text only, and only when policy allows the notice itself to
serve; otherwise the vector lane records an embedding skip.

### `striatum_chunk_embeddings`

Local pgvector rows for `striatum_chunks`.

Columns:

- `chunk_id UUID NOT NULL`;
- `generation_id UUID NOT NULL`;
- `item_projection_id UUID NOT NULL`;
- `embedding_cache_id UUID NOT NULL`;
- `embedding VECTOR NOT NULL`;
- `embedding_model_version TEXT NOT NULL`;
- `embedding_dimension INT NOT NULL`;
- `is_active BOOLEAN NOT NULL DEFAULT false`;
- `invalidated_at TIMESTAMPTZ NULL`;
- `invalidation_reason TEXT NULL`;
- `privacy_tier INT NOT NULL`;
- `redaction_state TEXT NOT NULL`;
- `visibility JSONB NOT NULL`;
- `source_capture_id UUID NOT NULL`;
- `source_kind TEXT NOT NULL`;
- `source_item_id TEXT NOT NULL`;
- `source_logical_id TEXT NOT NULL`;
- `source_version_id TEXT NOT NULL`;
- `source_sub_kind TEXT NOT NULL`;
- `source_dirty_working_tree BOOLEAN NOT NULL`;
- `chunk_sha256 TEXT NOT NULL`;
- `content_sha256 TEXT NOT NULL`;
- `record_sha256 TEXT NOT NULL`;
- `raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb`;
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`;
- `tenant_id TEXT NOT NULL`;
- `corpus_id TEXT NOT NULL`.

Generation-scoped primary/idempotency key:

- `(generation_id, chunk_id, embedding_model_version, embedding_dimension)`.

Embedding rows copy the minimum serving and invalidation fields needed for
health checks, but copying is not the only guard. Vector serving must also join
or otherwise enforce that the embedding row, chunk row, and item row all belong
to the same active generation and same `(tenant_id, corpus_id)`, and that none
has `invalidated_at IS NOT NULL`. A copied field mismatch is a malformed/stale
index condition, not a tie-breaker.

### `striatum_embedding_skips`

Concrete local skip records for chunks that intentionally do not receive a
vector row in a generation.

Columns:

- `generation_id UUID NOT NULL`;
- `chunk_id UUID NOT NULL`;
- `item_projection_id UUID NOT NULL`;
- `embedding_model_version TEXT NOT NULL`;
- `embedding_dimension INT NOT NULL`;
- `is_active BOOLEAN NOT NULL DEFAULT false`;
- `invalidated_at TIMESTAMPTZ NULL`;
- `invalidation_reason TEXT NULL`;
- `skip_reason TEXT NOT NULL`;
- `skip_detail TEXT NULL`;
- `privacy_tier INT NOT NULL`;
- `redaction_state TEXT NOT NULL`;
- `visibility JSONB NOT NULL`;
- `source_capture_id UUID NOT NULL`;
- `source_kind TEXT NOT NULL`;
- `source_item_id TEXT NOT NULL`;
- `source_logical_id TEXT NOT NULL`;
- `source_version_id TEXT NOT NULL`;
- `source_sub_kind TEXT NOT NULL`;
- `source_dirty_working_tree BOOLEAN NOT NULL`;
- `chunk_sha256 TEXT NOT NULL`;
- `content_sha256 TEXT NOT NULL`;
- `record_sha256 TEXT NOT NULL`;
- `raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb`;
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`;
- `tenant_id TEXT NOT NULL`;
- `corpus_id TEXT NOT NULL`.

Primary/idempotency key:

- `(generation_id, chunk_id, embedding_model_version, embedding_dimension)`.

Skip reason vocabulary:

```text
redaction_withheld
privacy_tier_exceeded
vector_disabled
unembeddable
model_dimension_unsupported
policy_omitted
```

Skip records must not contain hidden body text in `skip_detail` or `raw_payload`.
They are only local evidence that the embedding completeness gate was satisfied
without producing a vector.

A skip row satisfies activation and embedding completeness only when it belongs
to the same active generation, tenant/corpus pair, chunk row, and item row as the
serving lane, has `is_active=true`, and has `invalidated_at IS NULL`.
Invalidation from rebuild, tombstone, redaction, or privacy reclassification
treats active skip rows like active embedding rows: stale skip rows are set
inactive and receive an `invalidation_reason` before a lower-tier or
newer-generation lane can serve.

<a id="embedding-activation-invariant"></a>

### Embedding Activation Invariant

For every `(generation_id, chunk_id, embedding_model_version,
embedding_dimension)` tuple covered by the activated generation's
`required_embedding_profile`, exactly one of the following must hold for that
generation to remain activated and for the affected vector lane to remain
serving:

- exactly one active, non-invalidated `striatum_chunk_embeddings` row
  (`is_active=true` and `invalidated_at IS NULL`) with that key; or
- exactly one active, non-invalidated `striatum_embedding_skips` row
  (`is_active=true` and `invalidated_at IS NULL`) with that key.

This is an XOR invariant. The following states are malformed and must fail
activation closed or trigger invalidation of the affected lane:

- both an active embedding row and an active skip row exist for the same
  `(generation_id, chunk_id, embedding_model_version, embedding_dimension)`;
- neither an active embedding nor an active skip row exists for a required key;
- more than one active row exists in either table for the same key.

Scope and key shape:

- The invariant applies per row in the active generation's
  `required_embedding_profile.models[]` whose `required=true`. Lanes not in the
  manifest are not subject to the invariant and must not be served as vector
  results for that generation.
- Active chunks that are removed from the generation (tombstoned, redacted, or
  superseded) are not subject to the invariant for that generation, since the
  `chunk_id` is no longer part of the active serving set.
- Implementation may enforce this through partial unique indexes, a serving
  view, transactional activation checks, or trigger-style guards. RFC 0046 does
  not pick the enforcement mechanism. It only requires that the invariant hold
  at activation time and at every later read.

Projection and embedding workers must treat the manifest plus this invariant as
the unambiguous activation rule. The activation step in
`Rebuild, Invalidation, And Freshness` and the freshness checks that feed
RFC 0049 must be implemented against this rule rather than against per-chunk
heuristics.

### Embedding Boundaries

- embeddings use local model runtimes only, such as the existing local Ollama
  path;
- no hosted embedding API, telemetry, remote vector store, or cloud reranker is
  allowed;
- dimensions are versioned per D033-style rules, with indexes per active
  `(embedding_model_version, embedding_dimension)`;
- embeddings for a generation do not become active until all required chunks in
  that generation have either an active, non-invalidated embedding row or an
  active, non-invalidated `striatum_embedding_skips` row for every
  `(embedding_model_version, embedding_dimension)` lane listed as required in
  the generation's persisted `required_embedding_profile`, in accordance with
  the [Embedding Activation Invariant](#embedding-activation-invariant);
- embeddings are computed only from persisted `striatum_chunks.chunk_text`, never
  from a pre-redaction or fully withheld body;
- lexical and exact lookup must remain usable if vector embedding is disabled.

## Index Requirements

All indexes below include `tenant_id` and `corpus_id` either as leading columns
or as a partial-index predicate pinned to a specific pair.
Serving indexes must also operate over the active serving view or include the
current `generation_id`, `is_active`, and `invalidated_at IS NULL` predicates.
Physical base-table indexes used for rebuild/idempotency include
`generation_id`; serving-active uniqueness excludes inactive prior generations
through the active predicate rather than by deleting or rewriting old rows.

### Exact Identifier Lookup

- `striatum_items(tenant_id, corpus_id, source_item_id)`.
- `striatum_items(tenant_id, corpus_id, source_logical_id, source_version_id)`.
- `striatum_references(tenant_id, corpus_id, ref_kind, ref_value_normalized)`.
- `striatum_runs(tenant_id, corpus_id, run_id)`.
- `striatum_agents(tenant_id, corpus_id, process_id)`.
- `striatum_artifacts(tenant_id, corpus_id, artifact_id)`.
- `striatum_git_refs(tenant_id, corpus_id, commit_sha) WHERE commit_sha IS NOT NULL`.
- `striatum_issues(tenant_id, corpus_id, issue_id) WHERE issue_id IS NOT NULL`.
- `striatum_issues(tenant_id, corpus_id, blocker_id) WHERE blocker_id IS NOT NULL`.

### Structured Filters

- source kind/sub-kind/status/time:
  `(tenant_id, corpus_id, source_kind, source_sub_kind, is_active,
  observed_at DESC)`;
- privacy:
  `(tenant_id, corpus_id, privacy_tier, is_active)`;
- authority:
  `(tenant_id, corpus_id, authority_class, stability_class, is_active)`;
- path:
  `(tenant_id, corpus_id, logical_path, is_active)`;
- run/job:
  `(tenant_id, corpus_id, workflow_id, workflow_job_id, job_id)`;
- producer lineage:
  `(tenant_id, corpus_id, producer_run_id, producer_process_id)`.
- dirty working tree:
  `(tenant_id, corpus_id, source_dirty_working_tree, is_active)`.

### Lexical Search

Implementation should provide local PostgreSQL full-text or trigram indexes over:

- `striatum_documents.body_text`;
- `striatum_runs.objective`, `result_summary`, and `failure_summary`;
- `striatum_artifacts.summary_text`;
- `striatum_git_refs.subject` and `diff_summary`;
- `striatum_issues.title` and `summary_text`;
- `striatum_chunks.chunk_text`.

The exact extension choice is an implementation detail, but it must stay inside
local PostgreSQL. No hosted search service is permitted.

### Vector Search

Use pgvector only for `striatum_chunk_embeddings` in this RFC. Suggested HNSW
indexes are per active model/dimension, matching existing Engram segment
embedding practice:

```text
WHERE is_active
  AND tenant_id = 'striatum'
  AND corpus_id = '<corpus>'
  AND embedding_model_version = '<model>'
  AND embedding_dimension = <dimension>
```

If per-corpus partial indexes create too many indexes, implementation may choose
a shared active model/dimension index with tenant/corpus prefilters, but review
must include query plans for the expected corpus count.

## Query Surfaces

This RFC prepares, but does not expose, these local read surfaces:

- exact reference lookup by item id, logical id, RFC id, decision id, review id,
  run id, workflow id, workflow job id, job id, process id, artifact id, issue
  id, blocker id, commit SHA, path, or source hash;
- structured filters by corpus, sub-kind, authority class, status, privacy tier,
  time window, run/job, agent role, artifact kind, path, commit, and
  dirty-working-tree state;
- cross-link traversal such as "reviews for RFC 0044", "runs that produced this
  handoff", "commits touching this design", or "blockers mentioned by failed
  jobs";
- lexical search over chunks and selected summary columns;
- local vector search over chunk embeddings;
- projection health/freshness summaries for RFC 0049.

No MCP or CLI shape is accepted here. RFC 0047 decides which surfaces become
runtime augmentation APIs and which remain internal implementation details.

## Rebuild, Invalidation, And Freshness

### Full Rebuild

A full rebuild creates a new `striatum_projection_generations` row and writes a
complete serving snapshot with `is_active=false`. After validation, the
activation step:

1. marks the new generation `activated`;
2. sets required rows in that generation `is_active=true`;
3. makes that generation the only active generation for the
   `(tenant_id, corpus_id, projection_schema_version)` pair;
4. sets the prior active generation `superseded`;
5. sets prior active rows `is_active=false` and invalidates them with
   `invalidation_reason='rebuild'`.

The activation step must be transactional where PostgreSQL can enforce it. If
embedding generation is deferred or vector search is disabled, vector rows for a
prior generation must not be served as if they belong to the newly activated
generation. The vector lane either remains unavailable/stale by explicit status
or activates only when the new generation satisfies the
[Embedding Activation Invariant](#embedding-activation-invariant) for every
required `(embedding_model_version, embedding_dimension)` lane in its persisted
`required_embedding_profile`.

### Incremental Bundle Handling

Incremental bundles produce a new full-snapshot generation. The builder may read
the prior active generation as an input cache, but the activated result is not a
mixed-generation view.

- Unchanged item: copy forward the prior active projection rows into the new
  generation, preserving source identities, hashes, privacy/redaction/visibility
  metadata, and optional `carried_forward_from_id` lineage.
- New item version: insert new projection rows and links in the new generation.
- Tombstone: omit the affected `source_logical_id` from the new active serving
  set and invalidate the prior active rows.
- Redaction: write replacement rows in the new generation, replace body chunks
  with redaction-notice chunks where the V2 item supplies them, and invalidate
  prior chunks, references, embeddings, and skips for the affected logical item.
- Source omission: carry forward prior active rows unless RFC 0045 emits
  tombstone or redaction evidence. Silent omission is not deletion.
- Dirty working-tree evidence: copy forward dirty state unchanged for unchanged
  rows. A new dirty item version is projected only after RFC 0045 validation has
  accepted both the manifest-level operator opt-in and row-level
  `provenance.dirty_working_tree=true`; replacement projection rows carry
  `source_dirty_working_tree=true` and remain distinguishable from clean
  committed evidence.

### Privacy Reclassification

If Engram later receives a privacy reclassification capture that targets a raw
Striatum item, all retrieval-visible projections for the affected
`source_item_id` or `source_logical_id` must be invalidated before lower-tier
reads can serve them. Replacement rows carry the new effective tier or a
withheld/redaction state. Invalidation covers items, references, documents,
structured projections, links, chunks, chunk embeddings, embedding skips, and
any active serving view or cache built over them.

This mirrors existing segment privacy invalidation discipline: stale lower-tier
derived rows are not allowed to remain queryable. Path-like metadata and display
labels inherit the highest effective privacy tier and redaction state of the
item or chunk they identify; a lower-tier path/reference row must not outlive a
higher-tier reclassification of its parent evidence.

### Freshness Detection

Projection health checks compare:

- latest validated V2 raw bundle per `(tenant_id, corpus_id)`;
- latest active projection generation for the same pair;
- manifest hash and item count;
- active chunk count and embedding count by model/dimension;
- embedding skip count by model/dimension and skip reason;
- required-lane coverage from the generation's `required_embedding_profile`,
  including per-required-lane counts of chunks with neither an active embedding
  nor an active skip row (must be zero) and per-required-lane counts of chunks
  with both an active embedding and an active skip row (must be zero), per the
  [Embedding Activation Invariant](#embedding-activation-invariant);
- invalidated-but-still-active row count, which must be zero;
- dirty-working-tree projection count and any dirty rows missing copied dirty
  provenance state, which must be zero;
- copied-field mismatches for direct provenance, privacy/redaction, dirty state,
  and hashes between active embeddings, active chunks, and active items;
- V1 raw-only bundle presence, which must not be treated as projection-ready.

Stale-index detection hooks feed RFC 0049. They do not authorize automatic
Striatum export or any Engram call into Striatum.

## Validation Fixtures

Implementation should add deterministic local fixtures before migration
acceptance:

1. Minimal V2 bundle with every required stream represented, including zero-row
   streams.
2. Multi-corpus fixture with `corpus_id='striatum'` and a second
   `striatum:<fixture>` corpus proving isolation.
3. Document fixture with RFC, review, synthesis, handoff, changelog, and decision
   rows that share links.
4. Run fixture with run, workflow job, agent process, artifact, stdout/stderr
   summary, issue, and blocker links.
5. Git fixture with commit SHA, path references, and bounded diff summary.
6. Redaction fixture with `redaction_state='withheld'` and deterministic
   redaction-notice chunk.
7. Tombstone/incremental fixture that invalidates a prior logical item.
8. Negative V1 fixture proving V1 raw-only bundles do not populate RFC 0046
   projection tables.
9. Negative tenant/corpus/provenance fixture proving inconsistent `tenant_id`,
   `corpus_id`, `source_capture_id`, `source_kind`, or `source_sub_kind` rows
   fail before projection or fail closed before serving.
10. Local embedding fixture using mocked or precomputed local vectors for unit
    tests; no live hosted model call is allowed.
11. Generation rollover fixture proving the same V2 items can exist in two
    generations without physical unique-key collisions and that only the active
    serving view returns the current generation.
12. Incremental carry-forward fixture proving unchanged rows are copied into the
    new full snapshot and tombstoned/redacted logical IDs are absent or replaced
    in the active serving set.
13. Embedding skip fixture with `redaction_withheld`, `privacy_tier_exceeded`,
    and `vector_disabled` rows keyed by generation/chunk/model/dimension.
14. Withheld-body fixture proving a nearest-neighbor query for a known withheld
    phrase cannot return a vector derived from the hidden body.
15. Path privacy fixture proving absolute/operator-private paths are rejected or
    sanitized before references, chunks, git rows, or artifact rows become
    active.
16. Reference-collision fixture proving personal-memory and Striatum
    collision-shaped references are scoped by stored `(tenant_id, corpus_id)` and
    fail closed through `fetch_reference` reauthorization.
17. Dirty-working-tree fixture proving projection refuses unapproved dirty
    exports, projects approved dirty rows with `source_dirty_working_tree=true`,
    and never presents dirty evidence as clean committed state.

## Validation And Test Expectations

Later implementation acceptance should include:

- migration applies cleanly from empty and from current development schema;
- `make schema-docs` regenerates `docs/schema/README.md`; the generated doc is
  not edited by hand;
- projection rebuild is idempotent for the same worker key;
- projection-family writes are idempotent by `(generation_id, natural key
  suffix)`;
- full rebuild and incremental rebuild produce the same active projection set for
  equivalent inputs;
- every active serving query uses active views or equivalent predicates, not
  unfiltered base tables;
- every projection row cites direct copied `source_capture_id`, `source_kind`,
  `source_item_id`, `source_logical_id`, `source_version_id`,
  `source_sub_kind`, hashes, and derivation generation;
- every active projection row has matching `tenant_id` and `corpus_id`;
- active serving uniqueness is enforced separately from physical
  generation-scoped uniqueness;
- single-pair serving/query paths enforce primary-pair and cross-boundary
  capabilities through the actual service path, not only helper methods;
- exact reference lookups never scan or return another tenant/corpus;
- exact reference vocabulary and fixtures include `workflow_job_id` and `job_id`
  as scoped lookup identifiers;
- privacy reclassification invalidates old chunks, embeddings, and embedding
  skips before lower tier retrieval can see them;
- each generation persists a `required_embedding_profile` that names the
  `(embedding_model_version, embedding_dimension)` lanes required for
  activation, and that profile is immutable for the life of the generation;
- the [Embedding Activation Invariant](#embedding-activation-invariant) holds
  at activation and at every later serving read: exactly one active embedding
  row or exactly one active skip row exists per
  `(generation_id, chunk_id, embedding_model_version, embedding_dimension)`
  for every required lane in the generation's `required_embedding_profile`;
- embedding rows and active, non-invalidated skip rows are complete for every
  `(generation_id, chunk_id, embedding_model_version, embedding_dimension)`;
- embedding rows cannot serve unless their direct copied provenance fields match
  active chunk and item rows in the same generation, tenant/corpus, privacy tier,
  redaction state, dirty state, and hashes;
- embedding skip rows cannot satisfy completeness unless matching active chunk
  and item rows share the same direct copied provenance fields, generation,
  tenant/corpus, privacy tier, redaction state, dirty state, and hashes;
- withheld bodies are never embedded before redaction-notice substitution;
- path-like fields are repository-relative unless an explicit RFC 0045 operator
  opt-in permits absolute paths at an appropriate privacy tier;
- dirty working-tree rows are rejected unless RFC 0045 validation accepted the
  manifest-level opt-in and row-level dirty provenance, and projected dirty rows
  carry `source_dirty_working_tree=true`;
- personal/Striatum reference collisions fail closed through stored-row
  reauthorization;
- V1 bundles are rejected or routed through an explicit reviewed adapter;
- vector population works with local pgvector rows and local embedding inputs
  only;
- no code path requires network, hosted services, telemetry, or remote
  persistence.

## Downstream Dependencies

- RFC 0047 uses active serving views over `striatum_items`,
  `striatum_references`, `striatum_links`, `striatum_chunks`, and optional
  `striatum_chunk_embeddings` as candidate retrieval lanes.
- RFC 0048 uses authority class, privacy tier, provenance, and chunk boundaries
  to decide context-injection budgets and redaction behavior.
- RFC 0049 uses projection generations, fixture bundles, stale-index health
  checks, no-egress probes, tenant/corpus isolation tests, embedding skip counts,
  invalidated-active-row checks, copied-field mismatch checks, dirty-export
  projection checks, and golden reference queries including workflow/job
  identifiers.
- Striatum exporter implementation must emit V2 fields stable enough for these
  projection keys.
- Engram implementation must add migrations, projection workers, service query
  tests, and generated schema docs in a later write scope.

## Review Requirements

Use the multi-agent review loop before promotion:

- schema/migration safety review;
- provenance and rebuildability review;
- tenant/corpus isolation and service-path authorization review;
- local-only/no-egress and embedding-boundary review;
- query ergonomics review against expected Striatum operator questions;
- fixture and RFC 0049 gate-readiness review.

Reviewers should classify blockers separately from follow-ups. A blocker is a
schema or rule gap that could allow cross-corpus reads, stale low-tier retrieval,
irrebuildable projections, uncited answers, silent V1 projection, or hosted
dependency drift. A follow-up is hardening or ergonomics that does not weaken
those invariants.

## Acceptance Criteria

- The RFC defines concrete projection families and common column requirements.
- RFC 0044 Phase 0 hardening or EG-000-equivalent evidence is an explicit
  prerequisite before migration/projection implementation.
- Every projection row can be rebuilt from RFC 0045 V2 raw evidence.
- Every projection row cites raw Engram evidence plus V2 item identity, hashes,
  provenance, privacy, visibility, and derivation generation.
- Physical idempotency is generation-scoped, and serving active uniqueness is a
  separate partial-view/index invariant.
- The active-set model is full-snapshot generation activation with carry-forward
  rows for unchanged evidence.
- Tenant/corpus boundaries are structural in tables, indexes, and service-path
  test expectations.
- Exact-reference, structured, lexical, and local pgvector index requirements are
  named.
- Embedding rows and embedding skip rows preserve enough privacy, visibility,
  redaction, source identity, hash, and invalidation state to prevent stale or
  withheld chunks from serving.
- Each `striatum_projection_generations` row persists a
  `required_embedding_profile` activation manifest, and the
  [Embedding Activation Invariant](#embedding-activation-invariant) is stated
  as an XOR rule: exactly one active embedding or one active skip per
  `(generation_id, chunk_id, embedding_model_version, embedding_dimension)`
  for every required lane in the manifest.
- Rebuild, activation, invalidation, stale-index, privacy reclassification, and
  V1 rejection behavior are specified.
- Validation fixtures and downstream RFC dependencies are named.
- Local-only/no-cloud/no-telemetry/no-hosted-persistence constraints are
  preserved.

## Open Decisions

1. Whether `striatum_projection_generations` should share a generic projection
   generation table with future application memories or remain Striatum-specific.
2. Whether direct copied provenance fields (`source_capture_id`, `source_kind`,
   `source_item_id`, `source_logical_id`, `source_version_id`, and
   `source_sub_kind`) should be enforced by composite foreign keys that include
   `(tenant_id, corpus_id)` or by triggers/service guards, given the current raw
   and projection table primary-key shapes.
3. Exact PostgreSQL lexical index strategy: built-in full-text, trigram, or both.
4. Whether per-corpus pgvector partial indexes are acceptable once multiple
   Striatum corpora exist.
5. Whether author emails, branch names, and local paths are stored directly,
   hashed, redacted, or split by privacy tier in git projections.
6. Whether `projection_audits` should be extended with tenant/corpus and
   projection-generation fields or whether Striatum projection audits need a new
   audit table.
7. Whether semantic/inferred links belong in RFC 0046 follow-up work or should
   wait for a separate local reviewer/auditor RFC.
8. Final shape and key vocabulary of `required_embedding_profile` (manifest
   schema version, lane labels, required vs. optional lanes, `policy_source`
   values, and any additional per-lane metadata). The shape proposed above is
   minimal and remains subject to later contract review during RFC 0046
   promotion.
9. Enforcement mechanism for the
   [Embedding Activation Invariant](#embedding-activation-invariant): partial
   unique indexes, a serving view, transactional activation checks, or
   trigger-style guards. RFC 0046 fixes the invariant but leaves the mechanism
   to implementation review.
