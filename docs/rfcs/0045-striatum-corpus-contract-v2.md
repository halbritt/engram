<a id="rfc-0045"></a>

# RFC 0045: Striatum Corpus Contract V2

| Field | Value |
|-------|-------|
| RFC | RFC-0045 |
| Title | Striatum Corpus Contract V2 |
| Status | proposal |
| Implementation | none |
| Created | 2026-05-14 |
| Source | `STRIATUM_MEMORY_ROADMAP.md` |
| Context | RFC 0044, `STRIATUM_MEMORY_ROADMAP.md`, `SPEC.md`, `docs/schema/README.md` |

## Summary

This RFC defines a reviewable proposal for the Striatum Corpus Contract V2: a
durable local export contract owned by Striatum and consumed by Engram.

V2 extends RFC 0044's raw retrieval bundle into a stable contract for full and
incremental Striatum memory exports. It defines bundle manifest shape, item
record shape, identity rules, source-kind and sub-kind vocabulary, privacy and
redaction metadata, content hashes, validation rules, compatibility
expectations, and downstream handoff points.

This RFC does not implement a Striatum exporter, implement Engram ingestion,
create projections, expand MCP tools, or authorize runtime coupling. Engram
continues to read disk bundles produced outside Engram; Striatum continues to
run when Engram is missing, stale, or unavailable.

## Roadmap Position

RFC 0045 is Phase 1 of the Striatum memory roadmap, after RFC 0044 Phase 1
acceptance and before:

- RFC 0046, which turns validated Striatum evidence into rebuildable Engram
  projections and indexes;
- RFC 0047, which defines runtime retrieval as optional augmentation;
- RFC 0048, which defines context-injection budgets and policy;
- RFC 0049, which defines smoke, no-egress, isolation, and retrieval-quality
  gates.

The contract should be specific enough that later RFCs can target its fields
without reopening the export format on every pass.

## Contract Authority

The V2 contract is an export/import file contract only.

Striatum owns producing V2 bundles. Engram owns validating, ingesting, storing,
projecting, and serving from those bundles after they land on local disk. The
bundle may declare intended local memory identity, but it is not authority for
Engram authorization. Engram capability checks, visible pairs, primary-pair
semantics, and personal-memory isolation remain Engram-local concerns.

The accepted RFC 0044 boundary still holds:

- `tenant_id='striatum'` is the local application-memory boundary;
- the current default corpus remains `corpus_id='striatum'`;
- future per-instance corpora live under the Striatum tenant, for example
  `corpus_id='striatum:<instance-or-repository-id>'`;
- `source_kind='striatum'` is the ingest/parser discriminator for Striatum
  evidence;
- identity and discovery fields are never read grants;
- default Striatum operator access cannot read personal memory or secondary
  corpora without explicit Engram-local capabilities.

## Goals

1. Define the V2 bundle manifest shape.
2. Define the V2 item record shape.
3. Define source-kind and sub-kind vocabulary.
4. Define required and optional metadata for every exported item.
5. Define stable item IDs, logical IDs, content hashes, bundle IDs, instance
   identity, and repository identity.
6. Define privacy, redaction, visibility, provenance, confidence, stability,
   and audit metadata.
7. Define full and incremental export watermarks.
8. Define deterministic validation rules that require no live network or model
   calls.
9. Define V1 compatibility expectations.
10. Preserve local-only operation, immutable raw evidence, rebuildable
    projections, and the Striatum augmentation-not-dependency boundary.

## Non-Goals

- No Engram ingestion implementation.
- No Striatum exporter implementation.
- No Engram projection or index schema.
- No retrieval-ranking, context-injection, or prompt-packet policy.
- No MCP tool expansion beyond RFC 0044.
- No write-side memory mutation from Striatum into Engram.
- No hosted service, cloud API, telemetry, remote persistence, or outbound
  network requirement.
- No default exposure of personal memory to Striatum.
- No replacement of Striatum's repository files, git history,
  `.striatum/state.sqlite3`, daemon DB, operator reports, changelogs, or RFCs
  as authority.

## Dependencies

- RFC 0044 Engram Phase 1 acceptance with findings.
- RFC 0044 hardening cleanup for tenant/source-kind consistency, real-bundle
  smoke evidence, uniform MCP/reference failures, known `memory.*` capability
  validation, and schema-version reporting.
- RFC 0044 findings ledger preconditions F004 and F009: Striatum rows must be
  structurally tied to `source_kind='striatum'`, and decoded reference
  identifiers must be validated before database lookup. V2 bundle identity and
  references do not relax either hardening item.
- The reciprocal Striatum-side augmentation artifact: Striatum must not import
  Engram client code, must not add daemon RPC dependence on Engram, and must
  degrade gracefully when Engram is unavailable.
- `STRIATUM_MEMORY_ROADMAP.md` Phase 1 expectations for manifest shape,
  source kinds, metadata, stable IDs, hashes, identity, redaction, watermarks,
  validation, and backward compatibility.

## Contract Overview

V2 keeps the operator-triggered pull model:

```text
Striatum local repository, state, run, review, and artifact evidence
  -> striatum corpus export --contract v2 --out <local-dir>
  -> deterministic JSONL bundle plus manifest.json
  -> engram ingest-striatum --bundle <local-dir> [Engram-local options]
  -> immutable raw evidence under tenant_id='striatum'
  -> rebuildable projections, retrieval, and optional context augmentation
```

The exporter must run locally. The validator must run locally. Neither side of
this contract requires network access, hosted persistence, telemetry, cloud
model calls, or an Engram/Striatum runtime import in the other repository.

## Bundle Layout

A V2 bundle is a directory containing `manifest.json` and UTF-8 JSONL files.
The manifest is authoritative for the file list; filenames below are canonical
defaults, not parser magic.

```text
manifest.json
items/rfcs.jsonl
items/designs.jsonl
items/reviews.jsonl
items/syntheses.jsonl
items/handoffs.jsonl
items/operator_reports.jsonl
items/changelog.jsonl
items/decision_log_rows.jsonl
items/run_summaries.jsonl
items/workflow_runs.jsonl
items/agent_processes.jsonl
items/prompts.jsonl
items/packets.jsonl
items/artifact_manifests.jsonl
items/commits.jsonl
items/git_diff_summaries.jsonl
items/issues.jsonl
items/blockers.jsonl
items/operator_log_entries.jsonl
items/workflow_agent_log_entries.jsonl
items/stdout_stderr_summaries.jsonl
items/generated_artifacts.jsonl
items/vocabulary_terms.jsonl
items/friction_patterns.jsonl
```

Required core files may contain zero rows. Optional files may be omitted only
when the manifest records the omitted stream and the omission reason.

## Manifest Shape

The manifest must be deterministic JSON. The canonical bundle hash is computed
from the manifest with `bundle_sha256` omitted, using sorted object keys and
the same canonical JSON encoding rules that Engram already uses for RFC 0044
manifest hashing unless a later accepted spec narrows the canonicalization.

Proposed V2 manifest shape:

```json
{
  "schema_version": "striatum.corpus_export.v2",
  "bundle_kind": "striatum_corpus",
  "bundle_id": "striatum.bundle:<stable-local-id>",
  "bundle_sha256": "sha256:<hex>",
  "generated_at": "2026-05-14T00:00:00Z",
  "generator": {
    "name": "striatum",
    "version": "1.48.1",
    "command": "striatum corpus export",
    "contract_version": "v2"
  },
  "memory_target": {
    "tenant_id": "striatum",
    "corpus_id": "striatum:<instance-or-repository-id>",
    "source_kind": "striatum"
  },
  "identity": {
    "instance_id": "striatum-instance:<stable-local-id>",
    "instance_label": "operator-visible label",
    "repository_id": "git-repository:<stable-local-id>",
    "repository_label": "engram",
    "repository_root_hint": "engram",
    "git_head": "<commit-sha-or-null>",
    "git_dirty": false
  },
  "export": {
    "mode": "full",
    "sequence": 1,
    "previous_bundle_id": null,
    "watermark": {
      "git_after": null,
      "git_through": "<commit-sha-or-null>",
      "striatum_event_after": null,
      "striatum_event_through": "<event-id-or-null>"
    },
    "source_time_min": "2026-05-01T00:00:00Z",
    "source_time_max": "2026-05-14T00:00:00Z"
  },
  "privacy": {
    "default_privacy_tier": 1,
    "max_privacy_tier": 2,
    "redaction_profile": "striatum-v2-default",
    "redaction_ruleset_sha256": "sha256:<hex>",
    "path_policy": {
      "allow_absolute_paths": false,
      "allow_home_prefixes": false
    },
    "dirty_working_tree": {
      "export_allowed": false,
      "operator_opt_in_id": null
    },
    "withheld_streams": []
  },
  "schema": {
    "source_kinds": ["striatum"],
    "sub_kinds": ["rfc", "review", "synthesis"],
    "required_fields": [
      "tenant_id",
      "corpus_id",
      "bundle_id",
      "source_kind",
      "sub_kind",
      "item_id",
      "lifecycle",
      "content"
    ]
  },
  "files": {
    "items/rfcs.jsonl": {
      "sub_kind": "rfc",
      "required": true,
      "rows": 12,
      "bytes": 12345,
      "sha256": "sha256:<hex>"
    }
  },
  "row_counts": {
    "rfc": 12
  },
  "compatibility": {
    "min_reader_contract": "striatum.corpus_export.v2",
    "producer_contract": "striatum.corpus_export.v2"
  }
}
```

### Manifest Requirements

- `schema_version` must be exactly `striatum.corpus_export.v2` for V2
  validation.
- `memory_target.tenant_id` must be `striatum`.
- `memory_target.source_kind` must be `striatum`.
- `memory_target.corpus_id` must be non-empty and must not equal
  `personal`.
- `bundle_id` must be present, immutable for the emitted bundle, unique within
  `(memory_target.tenant_id, memory_target.corpus_id)`, and safe to use as
  RFC 0046's projection-generation input key.
- `bundle_id` is producer-assigned by Striatum, not derived from display
  labels, absolute paths, or Engram ingestion state. The producer may derive it
  from a canonical local export identity input, but that input must exclude
  `bundle_sha256` to avoid circularity.
- `bundle_sha256` remains the integrity hash for the exact manifest. It is not
  a replacement for `bundle_id`.
- `export.previous_bundle_id` is null for full exports and, for incremental
  exports, must name the prior accepted `bundle_id` in the same tenant/corpus
  chain. It must not name the current bundle.
- `identity.instance_id` must be stable across exports from the same local
  Striatum instance.
- `identity.repository_id` must be stable across exports from the same logical
  repository even if the local checkout path changes.
- `identity.instance_label`, `identity.repository_label`, and
  `identity.repository_root_hint` are display-only fields. They are never
  authorization grants, discovery authority, join keys, or collision
  boundaries.
- Labels inherit at least the manifest `privacy.max_privacy_tier` for the
  corpus they describe and must not appear in agent-visible diagnostics for a
  caller that is not authorized to read that corpus.
- `repository_root_hint` must be a display hint, not an absolute-path
  authority. It must avoid leaking private parent directory names unless the
  operator explicitly opts into that.
- If `identity.git_dirty` is true, the bundle is invalid unless
  `privacy.dirty_working_tree.export_allowed` is true and
  `privacy.dirty_working_tree.operator_opt_in_id` records an explicit local
  operator opt-in. Items sourced from uncommitted working-tree state must set
  `provenance.dirty_working_tree=true`.
- `files` must list every JSONL file included in the bundle.
- `row_counts` must match the parsed item counts per `sub_kind`.
- `privacy.redaction_profile` and `privacy.redaction_ruleset_sha256` must
  identify the local redaction rules used before export.
- `bundle_sha256` must match the canonical manifest hash with that field
  omitted.

## Source Kind And Sub-Kind Vocabulary

`source_kind` is closed for this contract:

```text
source_kind = striatum
```

V2 `sub_kind` values are grouped by evidence family. A V2 validator should
reject unknown required streams and preserve unknown optional fields inside
raw payloads only when the manifest declares a compatible minor extension.

| `sub_kind` | Required | Purpose |
|------------|----------|---------|
| `rfc` | yes | Striatum and Engram RFC documents and sections. |
| `design` | yes | Design docs and implementation specs. |
| `decision_log_row` | yes | Accepted, proposed, deferred, rejected, or superseded decision rows. |
| `operator_report` | yes | Operator-maintained status reports. |
| `changelog_entry` | yes | Changelog sections and entries. |
| `run_summary` | yes | Bounded summaries of Striatum runs. |
| `workflow_run` | yes | Workflow/run metadata: IDs, status, dependencies, timestamps. |
| `agent_process` | yes | Process metadata: lane, role, model, adapter status, exit state. |
| `review` | yes | Individual review artifacts and verdicts. |
| `synthesis` | yes | Syntheses, final decisions, and findings ledgers. |
| `handoff` | yes | Author, implementation, repair, and evidence handoffs. |
| `prompt` | yes | Workflow prompts, role prompts, and packet prompts. |
| `packet` | yes | Agent packets and assigned work scopes. |
| `artifact_manifest` | yes | Generated artifact metadata and artifact file references. |
| `commit` | yes | Git commit metadata and redacted commit text. |
| `git_diff_summary` | no | Bounded diff summaries; full diff export is an open decision. |
| `issue` | no | Issue or blocker tracker records available locally. |
| `blocker` | no | Striatum blocker/checkpoint records. |
| `operator_log_entry` | no | Operator log entries or summaries. |
| `workflow_agent_log_entry` | no | Agent log entries or summaries. |
| `stdout_stderr_summary` | no | Redacted stdout/stderr summaries, not raw streams. |
| `generated_artifact` | no | Metadata and safe excerpts for generated artifacts. |
| `ubiquitous_language_term` | no | Project vocabulary terms. |
| `harness_friction_pattern` | no | Known harness or workflow friction patterns. |

Required streams are required for schema stability; they may have zero rows.
Optional streams are omitted only with a manifest omission reason.

## Item Record Shape

Every non-empty JSONL line must be a JSON object with this base shape:

```json
{
  "tenant_id": "striatum",
  "corpus_id": "striatum:<instance-or-repository-id>",
  "bundle_id": "striatum.bundle:<stable-local-id>",
  "source_kind": "striatum",
  "sub_kind": "rfc",
  "item_id": "striatum.v2:repository:<repo-id>:rfc:0045@sha256:<hex>",
  "logical_id": "rfc:0045",
  "version_id": "sha256:<hex>",
  "lifecycle": {
    "state": "content",
    "target_item_id": null,
    "target_logical_id": null,
    "target_version_id": null,
    "reason": null,
    "effective_at": null,
    "replacement_item_id": null
  },
  "content": "Markdown or text body to index and cite.",
  "content_sha256": "sha256:<hex>",
  "record_sha256": "sha256:<hex>",
  "observed_at": "2026-05-14T00:00:00Z",
  "recorded_at": "2026-05-14T00:00:00Z",
  "emitted_at": "2026-05-14T00:00:00Z",
  "provenance": {
    "path": "docs/rfcs/0045-striatum-corpus-contract-v2.md",
    "logical_path": "docs/rfcs/0045-striatum-corpus-contract-v2.md",
    "commit_sha": "<commit-sha-or-null>",
    "blob_sha256": "sha256:<hex>",
    "source_hash": "sha256:<hex>",
    "line_start": 1,
    "line_end": 120,
    "run_id": null,
    "workflow_id": null,
    "workflow_job_id": null,
    "job_id": null,
    "process_id": null,
    "artifact_id": null,
    "issue_id": null,
    "blocker_id": null,
    "dirty_working_tree": false
  },
  "privacy": {
    "privacy_tier": 1,
    "redaction_state": "redacted",
    "redaction_profile": "striatum-v2-default",
    "withheld_fields": []
  },
  "visibility": {
    "default_visible_to": ["striatum_operator"],
    "requires_capabilities": ["memory.read_striatum"]
  },
  "classification": {
    "evidence_kind": "raw",
    "stability_class": "decision",
    "confidence": null,
    "authority_class": "canonical_doc"
  },
  "links": {
    "parent_ids": [],
    "related_ids": [],
    "supersedes": [],
    "superseded_by": [],
    "typed": []
  },
  "metadata": {}
}
```

### Item Requirements

- `tenant_id`, `corpus_id`, and `bundle_id` must be present on every item.
- `tenant_id` must be `striatum`.
- `corpus_id` must be non-empty, must not be `personal`, and must exactly match
  `manifest.memory_target.corpus_id`.
- `bundle_id` must exactly match `manifest.bundle_id`.
- `source_kind` must be `striatum` and must exactly match
  `manifest.memory_target.source_kind`.
- `sub_kind` must match the containing file's manifest entry.
- `item_id` must be immutable for the exact exported evidence version.
- `logical_id` must be stable for the same conceptual object across exports.
- `version_id` must identify the observed version, usually from
  `content_sha256` or source-native revision identity.
- `lifecycle.state` must be one of `content`, `tombstone`, `redaction`, or
  `withheld_marker`.
- `content` is the text Engram may index and cite. If source content is fully
  withheld, `content` must contain a deterministic redaction notice and
  `privacy.redaction_state` must not be `none`.
- `content_sha256` hashes the exact `content` string.
- `record_sha256` hashes the canonical item record with `record_sha256`
  omitted.
- `observed_at` is when the underlying source state was true or observed.
- `recorded_at` is when Striatum recorded or materialized that source state.
- `emitted_at` is when the exporter wrote this item into the bundle.
- `provenance` must include the closed base keys shown above, using `null`
  when a key is not applicable.
- `provenance` must include at least one retraceable source pointer: path,
  logical path, commit SHA, source hash, run id, workflow id, job id, process
  id, artifact id, issue id, or blocker id.
- Path-shaped item fields, including `provenance.path`,
  `provenance.logical_path`, chunk paths, and path references, must be
  repository-relative by default.
- Absolute paths, home-directory prefixes (`/home/<user>`, `/Users/<user>`,
  `/root`), and Windows user-profile equivalents are forbidden unless the
  manifest records explicit operator opt-in for absolute-path export.
- `privacy.privacy_tier` must be present and must use Engram's integer tier
  vocabulary.
- `links` must use `logical_id` or `item_id` values, not display strings.
- `metadata` is extension space. Consumers may preserve it but must not depend
  on unreviewed keys for authorization.

### Classification Contract

`classification` uses closed V2 vocabularies so downstream projections and
evaluation fixtures can filter without guessing producer intent.

`classification.evidence_kind` must be one of:

```text
raw
derived_summary
generated_artifact
redaction_notice
tombstone
```

`classification.authority_class` must be one of:

```text
canonical_doc
accepted_decision
accepted_synthesis
review_artifact
operator_report
changelog
workflow_state
run_log
agent_log
git_commit
issue_tracker
artifact_manifest
generated_artifact
draft
```

`classification.stability_class` must be one of:

```text
identity
decision
project_status
run_state
artifact_state
task
event
ephemeral
```

Confidence rules:

- `classification.confidence` must be `null` for direct raw evidence unless the
  source system itself supplies a meaningful confidence value.
- `classification.confidence` must be a number from `0.0` through `1.0` for
  `derived_summary`, generated or synthetic summaries, inferred relationships,
  and any content whose wording was produced by an agent or model.
- `tombstone` records and deterministic `redaction_notice` records use
  `confidence=null` unless the record contains a generated summary of the
  withheld or removed source.

### Reference And Link Vocabulary

Exact references emitted from V2 rows use this closed `ref_kind` vocabulary:

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

Typed links in `links.typed` must use objects with this shape:

```json
{
  "link_kind": "mentions",
  "target_ref_kind": "rfc_id",
  "target_ref_value": "0045",
  "confidence": null
}
```

`link_kind` must be one of:

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

The legacy array fields `parent_ids`, `related_ids`, `supersedes`, and
`superseded_by` remain allowed shorthand for item/logical-id links. New
cross-family links should use `links.typed`.

## Identity Rules

V2 separates identity at seven layers:

| Layer | Field | Rule |
|-------|-------|------|
| Local application memory | row `tenant_id` and `manifest.memory_target.tenant_id` | Always `striatum` for this contract. |
| Corpus | row `corpus_id` and `manifest.memory_target.corpus_id` | Non-empty Striatum corpus inside the Striatum tenant. Default remains `striatum`; per-instance form is `striatum:<stable-id-or-slug>`. |
| Bundle | `bundle_id` | Opaque Striatum-assigned identity for one emitted bundle, validated against `bundle_sha256` but not replaced by it. |
| Striatum instance | `identity.instance_id` | Stable local Striatum instance identifier, not derived solely from a mutable checkout path. |
| Repository | `identity.repository_id` | Stable repository identifier, preferably derived from git identity plus a local salt or explicit Striatum metadata. |
| Evidence item | `item_id` | Immutable exact-version row identity. |
| Conceptual object | `logical_id` | Stable object identity across versions, bundles, and incremental exports. |

The row-level `tenant_id` and `corpus_id` are the item contract consumed by
Engram raw capture, RFC 0046 projections, and RFC 0049 mismatch fixtures. The
manifest `memory_target` is the bundle-level validation target. A row whose
pair differs from the manifest is invalid; a consumer must not infer the row
pair from labels, paths, file names, or the containing directory.

V2 uses both machine-stable IDs and operator-visible labels. Human-readable
labels improve ergonomics, but labels must not be the only collision boundary
and must not be used as authorization or discovery shortcuts.

## Hashing Rules

V2 uses SHA-256 for deterministic validation:

- file hashes are computed over exact UTF-8 JSONL bytes;
- `content_sha256` is computed over the exact item `content` string bytes;
- `record_sha256` is computed over canonical item JSON with `record_sha256`
  omitted;
- `bundle_id` is validated as an opaque bundle identity and is included in
  `bundle_sha256` canonicalization;
- `bundle_sha256` is computed over canonical manifest JSON with
  `bundle_sha256` omitted;
- all hash fields use `sha256:<hex>` form in V2.

Hash mismatches are validation failures. A repeated `item_id` with different
`record_sha256` in one bundle is invalid. A repeated `item_id` across bundles
with different content must be represented as a new `item_id` and a stable
`logical_id`, not as a mutation of the old item.

Lifecycle records hash only the content and metadata actually emitted in the
bundle. Tombstones, redaction records, and withheld markers must not hash or
embed the hidden body they suppress; `content_sha256` covers the deterministic
notice in `content`, and `record_sha256` covers the emitted lifecycle record.

## Privacy, Redaction, And Visibility

Redaction happens before export and must be local. V2 does not authorize cloud
DLP, hosted redaction APIs, telemetry, or remote classification services.

Every item must include:

- `privacy.privacy_tier`;
- `privacy.redaction_state`, one of `none`, `redacted`, `withheld`, or
  `synthetic_summary`;
- `privacy.redaction_profile`;
- `privacy.withheld_fields`;
- `visibility.default_visible_to`;
- `visibility.requires_capabilities`.

Privacy tiers use Engram's existing integer vocabulary. V2 does not redefine
the meaning of tiers; it carries the tier attached by Striatum so Engram can
preserve and enforce it on raw captures and later projections.

If a source is too sensitive to export, V2 should either omit the stream with a
manifest omission reason or emit a withheld marker that contains provenance and
redaction metadata without sensitive content. It must not silently drop
evidence in a way that makes downstream retrieval overstate coverage.

When `privacy.redaction_state` is `withheld`, `content` must be a deterministic
redaction notice. Embeddings and chunks downstream may be computed only over
that emitted notice, never over the original withheld body.

Redaction metadata must not leak the hidden value through field names or
reason strings. `privacy.withheld_fields` should name schema fields, not
original secret values, absolute paths, private user names, or content
snippets.

## Lifecycle Record Shapes

V2 lifecycle is append-only. A lifecycle row never mutates or deletes earlier
raw evidence; it emits new evidence that downstream projections can use to
invalidate, replace, or represent absence.

`lifecycle.state` is closed:

```text
content
tombstone
redaction
withheld_marker
```

All lifecycle rows use the base item shape and the same row-level
`tenant_id`, `corpus_id`, `bundle_id`, hashing, provenance, privacy,
visibility, classification, and link rules.

### `content`

`content` records represent exported evidence text.

- `lifecycle.target_item_id`, `lifecycle.target_logical_id`, and
  `lifecycle.target_version_id` must be null.
- `content` is the indexable and citable text.
- `classification.evidence_kind` is usually `raw`, `derived_summary`, or
  `generated_artifact`.
- `content_sha256` hashes the exact emitted content.

### `tombstone`

`tombstone` records state that a prior item or logical object should no longer
be served as active evidence for this corpus.

- `lifecycle.target_logical_id` is required.
- `lifecycle.target_item_id` or `lifecycle.target_version_id` is required when
  the producer can identify the exact prior exported version.
- `lifecycle.reason` and `lifecycle.effective_at` are required.
- `content` must be a deterministic tombstone notice and must not include the
  prior hidden body.
- `classification.evidence_kind` must be `tombstone`.

### `redaction`

`redaction` records state that prior exported evidence has been reclassified,
redacted, or replaced by a safer emitted representation.

- `lifecycle.target_logical_id` is required.
- `lifecycle.target_item_id` or `lifecycle.target_version_id` is required when
  the producer can identify the exact prior exported version.
- `lifecycle.reason`, `lifecycle.effective_at`,
  `privacy.redaction_profile`, and `privacy.withheld_fields` are required.
- `lifecycle.replacement_item_id` is required when a separate replacement
  `content` record is emitted in the same bundle.
- `content` must be a deterministic redaction notice or a generated synthetic
  summary allowed by the privacy tier.
- `classification.evidence_kind` must be `redaction_notice` unless the record
  contains an allowed generated summary, in which case confidence is required.

### `withheld_marker`

`withheld_marker` records state that evidence exists but its body is not
exported.

- `lifecycle.target_logical_id` is required and identifies the source object
  whose body is withheld.
- `lifecycle.target_item_id` and `lifecycle.target_version_id` may be null when
  the body has never been exported.
- `privacy.redaction_state` must be `withheld`.
- `content` must be a deterministic withheld-content notice.
- `classification.evidence_kind` must be `redaction_notice`.
- Hashes cover only the notice and emitted metadata, not the hidden body.

## Incremental Export Watermarks

V2 supports both full and incremental exports.

Full export:

- `export.mode = "full"`;
- `export.previous_bundle_id = null`;
- watermark `after` fields are null;
- all available streams covered by the manifest are represented.

Incremental export:

- `export.mode = "incremental"`;
- `export.previous_bundle_id` names the prior bundle the increment extends;
- `watermark` records source-specific lower and upper bounds;
- every changed or newly visible item is emitted with a new immutable
  `item_id`;
- removals, redactions, and source absences are represented as explicit
  tombstone or redaction records, not as mutation of prior raw evidence.

Open framing for review: the durable storage location for Striatum-side
watermarks remains a Striatum implementation decision. Engram should not become
the source of truth for Striatum export progress.

## Validation Rules

A V2 validator must fail closed on:

- missing `manifest.json`;
- invalid JSON or non-object JSONL rows;
- non-UTF-8 files;
- unknown `schema_version`;
- mismatched `bundle_sha256`;
- missing or duplicate `bundle_id` inside the same tenant/corpus ingest scope;
- incremental `export.previous_bundle_id` that is null, equals the current
  `bundle_id`, or points outside the row's tenant/corpus chain;
- mismatched file hash, byte count, or row count;
- row `tenant_id` other than `striatum`;
- row `corpus_id` that is empty, equals `personal`, or differs from
  `manifest.memory_target.corpus_id`;
- row `bundle_id` that differs from `manifest.bundle_id`;
- row `source_kind` other than `striatum`;
- row `sub_kind` not matching the manifest file entry;
- missing required item fields;
- duplicate `item_id` values inside one bundle;
- invalid `lifecycle.state`;
- missing lifecycle target identity, reason, or effective timestamp for
  `tombstone`, `redaction`, or `withheld_marker` records where this RFC
  requires it;
- malformed timestamps;
- malformed `sha256:<hex>` fields;
- missing provenance;
- missing closed nullable provenance keys;
- missing privacy tier or redaction metadata;
- unknown `classification.evidence_kind`, `authority_class`, or
  `stability_class`;
- confidence outside `0.0` through `1.0`, missing confidence for generated or
  synthetic content, or non-null confidence on raw evidence without a source
  confidence value;
- inconsistent `tenant_id`, `corpus_id`, or `source_kind` declarations;
- absolute-path leakage in display labels, root hints, provenance paths, chunk
  paths, or path references unless the manifest declares explicit operator
  opt-in;
- dirty-working-tree items without both manifest-level operator opt-in and
  row-level `provenance.dirty_working_tree=true`;
- withheld or redaction lifecycle records whose hashes, content, metadata, or
  reason strings leak hidden source bodies.

Validation must not require live model calls, network access, Striatum daemon
RPC, Engram MCP, or a hosted service.

## Compatibility

RFC 0044's V1 bundle remains valid for RFC 0044 raw retrieval. It is not a V2
bundle.

V2 readers should:

- accept only `schema_version = "striatum.corpus_export.v2"` in V2 mode;
- reject unknown major versions;
- preserve unknown optional fields in raw payloads only when the manifest
  declares a compatible minor extension;
- reject unknown required streams;
- treat V1 bundles as raw-only compatibility input through the RFC 0044 ingest
  path or an explicit compatibility adapter;
- prevent RFC 0046 projections that require V2-only fields from silently
  running on V1-only bundles.

V2 producers should:

- keep JSONL output deterministic for the same inputs;
- add optional fields rather than changing existing field meaning;
- bump the contract version for incompatible changes;
- record omitted streams and unavailable optional sources explicitly.

## Downstream Requirements

RFC 0046 needs the following fields to be stable:

- row-level `tenant_id`, `corpus_id`, `bundle_id`, `source_kind`, and
  `sub_kind`;
- `item_id`, `logical_id`, `version_id`;
- `lifecycle.state` and lifecycle target identity for tombstones, redactions,
  and withheld markers;
- `content`, `content_sha256`, `record_sha256`;
- `observed_at`, `recorded_at`, `emitted_at`;
- closed nullable provenance fields for path, logical path, commit SHA, source
  hash, run, workflow, workflow job, job, process, artifact, issue, blocker,
  and dirty-working-tree state;
- closed privacy, redaction, visibility, classification, reference, and link
  vocabularies.

RFC 0047 needs RFC 0045 to preserve the non-runtime boundary:

- bundle identity is not authorization;
- Engram availability is not stored as Striatum authoritative state;
- Striatum can export and run without Engram;
- Engram can ingest from disk without importing Striatum.

RFC 0049 needs RFC 0045 to provide deterministic fixture inputs:

- manifest and item hashes;
- `bundle_id` and `previous_bundle_id` chain assertions;
- required and optional stream declarations;
- real or committed fixture bundle validation;
- no-egress validation scope;
- negative tests for inconsistent tenant/corpus/source-kind rows;
- negative tests for invalid lifecycle records, hidden-content hash leakage,
  absolute-path leakage, dirty-working-tree export without opt-in, and
  confidence/classification violations;
- V1 rejection or compatibility-adapter assertions.

## Review Requirements

Use the multi-agent review loop before promotion:

- local-first and no-egress boundary review;
- corpus contract coherence review;
- identity and tenant/corpus isolation review;
- Striatum operator ergonomics review;
- implementation-readiness review for both repositories.

The review packet should include this RFC, a candidate V2 fixture bundle or
fixture outline, the RFC 0044 final synthesis, the RFC 0044 findings ledger,
and this RFC's author handoff.

## Acceptance Criteria

- The RFC states that V2 is a disk bundle contract, not a runtime dependency.
- The RFC defines manifest, item, source-kind, sub-kind, identity, hashing,
  bundle identity, lifecycle, privacy, redaction, visibility, watermark,
  validation, and compatibility rules.
- The contract preserves row-level `tenant_id='striatum'` and explicit
  Striatum `corpus_id` boundaries validated against the manifest.
- The contract defines `bundle_id`, `bundle_sha256`, and
  `previous_bundle_id` compatibility.
- The contract closes provenance, reference, lifecycle, redaction,
  classification, stability, authority, and confidence vocabularies enough for
  RFC 0046 and RFC 0049 fixtures.
- Identity/discovery fields are explicitly not authorization grants.
- Privacy-sensitive labels, path fields, dirty working tree export, and
  redaction metadata are constrained before downstream projection.
- Required and optional source streams are named.
- V2 validation can run locally without network, live model, Striatum daemon,
  or Engram MCP calls.
- V1 bundle handling is explicit.
- Downstream dependencies for RFC 0046, RFC 0047, and RFC 0049 are named.

## Open Decisions

1. Exact `corpus_id` grammar for per-instance corpora: stable UUID, slug, hash,
   or combined `slug:<uuid>` form.
2. Exact source of `identity.instance_id` inside Striatum and how it is created
   for existing local checkouts.
3. Exact source of `identity.repository_id` when a repository has no remote or
   has multiple remotes.
4. Whether required streams must be emitted as zero-row files or may be omitted
   with manifest declarations.
5. How much full git diff content is exported by default versus summarized.
6. Whether raw stdout/stderr excerpts are ever allowed, or only summaries.
7. Exact privacy-tier assignment policy Striatum can guarantee before export.
8. Whether V2 uses one file per sub-kind forever or later permits a single
   `items.jsonl` shard with manifest partition metadata.
9. Whether compatibility adapters should live in Engram, Striatum, or both.
10. Which V2 fixture bundle becomes the review and evaluation seed for
    RFC 0049.
