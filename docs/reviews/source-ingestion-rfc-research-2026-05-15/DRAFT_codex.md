# Authoring Lane

Authoring lane: codex

# RFC 0050: Local Source Ingestion Contract And Expansion Plan

| Field | Value |
|-------|-------|
| RFC | RFC-0050 |
| Title | Local Source Ingestion Contract And Expansion Plan |
| Status | proposal |
| Date | 2026-05-15 |
| Authors | codex lane |
| Source design | `docs/design/source-ingestion-expansion-proposal-2026-05-15.md` |
| Context | `AGENTS.md`, `README.md`, `HUMAN_REQUIREMENTS.md`, `SPEC.md`, `BUILD_PHASES.md`, `ROADMAP.md`, `docs/ingestion.md`, `docs/schema/README.md`, RFC 0033-RFC 0036, RFC 0044-RFC 0049, `STRIATUM_MEMORY_E2E_BACKLOG.md`, `docs/AGENT_CONTEXT_NOTES.md` |

## Summary

Engram's current ingestion model has the correct foundational shape:

```text
sources
  -> conversations / messages / notes / captures
     immutable raw evidence
  -> segments / projections / observations
     rebuildable derived views
  -> claims / beliefs / entities / packets
     higher-level memory products with provenance
```

The limitation is not the raw-evidence principle. The limitation is that new
source families are still mostly handled by one-off parser decisions plus a
closed `source_kind` enum. That is enough for ChatGPT, Claude, Gemini, and
Striatum. It is not enough for git history, build artifacts, Markdown trees,
human communications, media, location, calendar, browser history, shell history,
and other life traces.

This RFC proposes a source contract that every new local source adapter must
declare before implementation. The contract answers four questions:

1. What is the immutable raw evidence boundary?
2. What normalized projection is safe and useful to derive from it?
3. Which downstream systems may see the projection by default?
4. What provenance, privacy, confidence, and rebuild rules protect it?

The first rollout should start with high-signal, low-egress-risk local project
evidence: git commit metadata, build/test artifacts, Striatum-aligned project
artifacts, and selected Markdown/project documents. Human communications,
browser/app activity, media, location, health, finance, and live capture remain
behind explicit source-family gates.

This is a proposal document only. It does not promote an RFC, edit the decision
log, change schema, add migrations, or authorize default ingestion of new
personal sources.

## Context

`HUMAN_REQUIREMENTS.md` defines the long arc: Engram is meant to become a
complete time-indexed biography of one human life, not only an AI chat memory.
The current V1 path validates the architecture on local AI conversation exports
and selected application-memory artifacts. V1 success is not full coverage; it
is proof that future source families can be added without violating the core
principles.

Those principles are load-bearing:

- no cloud dependency;
- no telemetry;
- no user data leaving the machine unless explicitly requested;
- no outbound network from any corpus-reading process;
- immutable raw evidence;
- rebuildable derived rows;
- evidence-backed claims and beliefs;
- privacy tier inheritance and reclassification by new raw captures;
- provenance, confidence, stability class, and auditability.

The current source coverage is:

| Source | Current shape | Status for this RFC |
|--------|---------------|---------------------|
| ChatGPT export | `sources` -> `conversations` -> `messages` | Implemented raw AI-conversation ingest. |
| Claude export | `sources` -> `conversations` -> `messages` | Implemented raw AI-conversation ingest. |
| Gemini Takeout Gemini Apps export | `sources` -> `conversations` -> `messages` | Implemented raw AI-conversation ingest, with activity rows mapped to conversation records. |
| Striatum corpus bundle | `sources` -> `captures`, with `tenant_id='striatum'` / `corpus_id='striatum'` | Implemented local application-memory raw ingest and read-only retrieval boundary. |
| Striatum exact references and packets | `striatum_references`, `striatum_projection_generations`, `striatum_packet_audits` in migrations | Implemented in the e2e Striatum memory track; generated schema docs may lag until regenerated. |
| Obsidian / notes | `source_kind='obsidian'`, `notes` table | Schema-reserved / deferred; not part of current Phase 2/3 runs. |
| Generic capture | `source_kind='capture'`, `captures` table | Used for manual/review corrections and generic raw evidence patterns; not a broad source adapter contract. |

Everything else in the source expansion design is net-new or only indirectly
represented through Striatum bundle rows.

The practical limitation is `source_kind`. The enum currently provides useful
fail-closed behavior, but every new source family requires migration churn. For
the next few concrete adapters, that churn is acceptable and safer than a loose
free-text discriminator. The missing piece is a project-local source contract
template and importer-gate discipline so each source family does not invent
identity, privacy, temporal, projection, extraction, and rebuild rules
independently.

There is a second practical schema constraint: `sources` is unique on
`(source_kind, external_id)`, while tenant/corpus columns were added later.
Future multi-repository, multi-account, or multi-corpus adapters must either
namespace `external_id` in a contract-reviewed way or make a separate schema
decision before they assume the same `source_kind` can reuse an external id in
multiple local boundaries.

The current default-on LLM-derived path is also intentionally narrow. Phase 2
segmentation and Phase 3 extraction/consolidation operate on AI-conversation
sources: ChatGPT, Claude, and Gemini. New sources may become retrievable or
projected before they are eligible for claim extraction.

## Goals

1. Define a reusable local source contract for future adapters.
2. Keep raw source artifacts immutable and derived projections rebuildable.
3. Preserve local-only operation and no-egress corpus-reading paths.
4. Define a closed initial projection-family vocabulary.
5. Define privacy defaults by source family before implementation begins.
6. Sequence source adoption from lowest egress/privacy risk to highest.
7. Require RFC 0049-style evaluation gates for every new source family.
8. Make gaps, omissions, stale projections, redactions, and withheld material
   explicit rather than silent.
9. Prevent generated summaries or derived memory products from becoming raw
   evidence.

## Non-Goals

- No hosted API ingestion.
- No automatic Gmail, Slack, GitHub, Apple, Google, browser, or cloud account
  access.
- No telemetry, remote vector store, hosted embedding, hosted reranking, hosted
  OCR, hosted vision, or hosted LLM call.
- No live capture or continuous surveillance as an initial source.
- No bidirectional sync back to source systems.
- No full media bodies, full patch bodies, full raw logs, or raw transcripts in
  context packets by default.
- No human-chat or email claim extraction by default.
- No personal-memory paste-through into Striatum or any application-memory
  tenant.
- No generated memory products until a separate privacy, citation, audit, and
  gate contract is accepted.
- No replacement of the current `source_kind` enum in the first implementation
  slice unless enum churn becomes a measured migration burden.

## Source Contract Template

Every new source adapter must declare a contract before code is written.

The contract must answer the four required source questions:

| Question | Required answer |
|----------|-----------------|
| Raw boundary | The exact immutable artifact boundary: export file, repository object, file snapshot, database copy, log directory, media asset, or capture record. |
| Projection | The normalized projection families emitted from raw evidence, including identity, temporal, reference, and citation fields. |
| Default consumers | Which downstream systems may see the projection by default: segmentation, extraction, exact-reference retrieval, packet builder, daily biography compiler, or none. |
| Protection rules | Provenance, privacy, confidence, redaction, lifecycle, rebuild, invalidation, and no-egress rules. |

Mandatory contract fields:

```yaml
source_kind: git
source_family: project_execution
sub_kinds:
  - commit
  - branch
  - tag
  - diff_stat
raw_artifact_boundary: local repository object database plus adapter manifest
allowed_acquisition:
  - local filesystem
  - explicit user-provided export
network_policy: no outbound calls
identity:
  source_instance_id: repository_root_identity
  item_identity_keys:
    - repository_id
    - commit_sha
  logical_identity_keys:
    - repository_id
    - ref_name
temporal_fields:
  observed_at: committer_date
  recorded_at: import_time
  emitted_at: null
deduplication:
  idempotency_key:
    - source_kind
    - repository_id
    - commit_sha
  conflict_policy: raise_on_changed_raw_artifact_hash
lifecycle:
  states:
    - content
    - tombstone
    - redaction
    - withheld_marker
privacy:
  default_tier: 1
  promotion_policy: reclassification_capture
  raw_payload_policy: no higher-tier smuggling
projection_families:
  - project_event
  - code_reference
  - artifact_reference
extraction_eligibility:
  default: metadata_only
  opt_in_required_for:
    - patch_body
    - private_author_email
    - uncommitted_worktree
raw_retention:
  required: object ids, commit metadata, changed path summaries, manifest hash
  optional: patch body
provenance:
  required:
    - source_id
    - raw row id
    - repository_id
    - commit_sha
    - content_hash
    - adapter_version
rebuild:
  projection_generation: required
  reproject_from_raw: required
  stale_projection_policy: fail_closed_or_label_stale
tests:
  - contract_validator
  - idempotent_reimport
  - conflict_on_changed_raw_hash
  - raw_evidence_immutable
  - projection_rebuild_from_raw
  - no_network_access
  - privacy_inheritance
  - exact_reference_citation
```

The contract can begin as checked-in Markdown or YAML under a future docs path.
It does not need to become a runtime registry on day one. It does need an
importer test harness that reads the declared contract and proves the adapter
honors the required invariants.

## Enforcement

Source contracts are enforced by importer tests and source-family fixtures.

Minimum enforcement:

- A contract validator fails closed on missing mandatory fields.
- The importer rejects acquisition modes not listed in `allowed_acquisition`.
- The importer uses only local files, local databases, local model runtimes, and
  local PostgreSQL.
- Re-import of the same source is idempotent.
- Re-import of the same source identity with changed raw artifact hash raises
  a conflict instead of overwriting.
- Raw rows are append-only and protected by the existing raw evidence mutation
  discipline.
- Projection rows cite raw rows and can be rebuilt from them.
- Retrieval-visible rows copy privacy tier, tenant/corpus, source identity,
  provenance, generation, active/invalidation state, and citation fields.
- `raw_payload` does not carry hidden body text, pre-redaction content, absolute
  private paths, identity labels, or higher-tier values that bypass top-level
  privacy checks.
- Corpus-reading paths have no outbound network access.

## Projection Families

Not every source should become a conversation, and not every projection should
become a claim or belief. The initial projection-family vocabulary is closed and
additive only through this RFC or an accepted successor.

| Projection family | Purpose | Early sources |
|-------------------|---------|---------------|
| `conversation_thread` | Thread, participant, message, reaction, reply, edit, attachment metadata. | AI exports, exported chat, email, transcripts. |
| `document_record` | File/path snapshot, title, headings, links, tags, frontmatter, chunks. | Markdown trees, Obsidian, project docs, saved pages. |
| `project_event` | Time-bound project action or state transition. | Git commits, branch/tag changes, Striatum run summaries, release notes. |
| `execution_artifact` | Build/test/lint/benchmark/deployment output summary with artifact references. | JUnit XML, pytest output, coverage reports, benchmark JSON, logs. |
| `code_reference` | Commit, path, symbol, diff stat, line/window, branch/tag reference. | Git history, Striatum commit rows, build reports. |
| `artifact_reference` | Content-addressed or path/hash reference to a file-like artifact. | Build artifacts, reports, generated files, media sidecars. |
| `observation` | Atomic source-backed or model-derived observation that is not a belief. | Photos, location, calendar, OCR, health/activity, receipts. |
| `place_event` | Visit, location sample cluster, place candidate, event interval. | Location exports, EXIF coordinates, calendar locations. |
| `asset_record` | Media or blob-like asset metadata without putting binary bodies in ordinary rows. | Photos, videos, screenshots, audio, PDFs. |
| `coverage_gap` | Explicit missing, disabled, withheld, stale, or unavailable source coverage. | All source families. |
| `source_audit` | Local-only import, projection, omission, and rebuild audit record. | All source families. |

Projection rows inherit privacy and provenance from raw evidence:

- The projection `privacy_tier` is the maximum of source default, raw row tier,
  parent artifact tier, cited child row tiers, observation/projection type
  default, and applicable reclassification captures.
- Redaction state and withheld fields travel with retrieval-visible rows.
- Projection rows cite raw evidence ids or raw artifact ids. They may also cite
  input projections, but they cannot be grounded only in another derived row.
- Projection generations are idempotent by `(input_id, version)` and
  generation-scoped natural keys.
- Serving queries read only active, non-invalidated projection rows.
- A privacy promotion, tombstone, redaction, or raw artifact conflict
  invalidates affected projection rows before lower-tier retrieval can serve
  them.

## Privacy Defaults

The table below proposes default minimum privacy tiers for new adapters. A user
or later policy may promote any source to a stricter tier. Higher tiers are
more restrictive.

| Source family | Default privacy tier | Default posture |
|---------------|----------------------|-----------------|
| Explicitly selected project git repositories | Tier 1 | Metadata and diff stats first. Patch bodies opt-in. Author emails hashed or tier-promoted where needed. |
| Striatum application-memory bundles | Tier 1 within `tenant_id='striatum'` | Application-memory boundary only; no personal memory by default. |
| Build/test/lint/benchmark artifacts | Inherit project tier, minimum Tier 1 | Summaries and failure signatures first. Full logs opt-in because logs can contain secrets. |
| Project docs, RFCs, changelogs, READMEs | Tier 1 | Good early retrieval candidates when explicitly selected. |
| AI conversation exports | Current source default unless promoted; proposed Tier 1 or Tier 2 by user setting | Existing AI conversation extraction can remain the only default-on extraction path. |
| Selected Markdown / notes trees | Project docs Tier 1; personal vaults Tier 2+ | Markdown/plain text before binary formats. Journals and personal notes stricter by default. |
| User corrections / manual captures | Inherit target or explicit capture tier; personal corrections Tier 2+ | Corrections are raw evidence, not direct row updates. |
| Email and human messaging exports | Tier 2+; private/direct communications Tier 3 by default | Import may be allowed from local exports; claim extraction requires source-specific approval. |
| Calendar, contacts, reminders | Tier 3 by default | Event intervals may be useful; contacts and invitees are third-party data. |
| Browser, shell, window, and app activity | Tier 3 by default | Defer. Backfills only; no continuous live capture initially. |
| Photos, videos, screenshots, OCR | Tier 3 by default | Metadata-first. Binary bodies stay as local file references or managed local content-addressed store. |
| Exact coordinates, face embeddings/clusters, health, finance, contacts | Tier 4+ by default | Strict handling; no ordinary assistant context without explicit grant. |

No-egress rule:

- Importers, validators, projection workers, local model stages, embedding
  stages, retrieval services, packet builders, and evaluators that read corpus
  content must not make outbound network calls.
- A process with network tools must not have direct Engram corpus access.
- If freshness requires external lookup, Engram emits a gap or operator action
  hint. It does not call the network itself.

No-derived-product-leak rule:

- Generated summaries, packet text, daily biographies, OCR outputs, captions,
  and source-specific summaries are derived products.
- They inherit privacy from cited evidence.
- They require citations.
- They do not become raw evidence.
- They are not eligible for default injection into another application-memory
  tenant until a generated-product privacy, citation, audit, and gate contract
  is accepted.

## Rollout Order

### Stage 0: Source Contract And Fixture Harness

Deliverables:

- Source contract template.
- Closed vocabulary for source family, sub-kind, acquisition mode, network
  policy, lifecycle state, projection family, extraction eligibility, and
  privacy default.
- Tiny contract validator.
- Fixture format for source adapters.

Success criteria:

- A fixture-only adapter can run contract validation, import no-op, projection
  no-op, and no-egress checks locally.
- Failure reports include fixture path, manifest hash, row count, contract
  version, adapter version, commands run, and residual limits.

### Stage 1: Project Execution Sources

Adopt first:

1. Local git commit metadata and diff stats.
2. Local build/test/lint/coverage/benchmark artifact directories.
3. Striatum artifact/reference alignment where the new source contract improves
   the existing application-memory path.

Success criteria:

- Importing the same repository or artifact directory twice is idempotent.
- Rewritten or changed source evidence is represented as new evidence or a
  conflict, never an in-place rewrite.
- Commit SHA, path, run id, artifact hash, and failure signature exact-reference
  retrieval work without vector search.
- Full patch bodies and full logs are omitted from packets unless explicitly
  requested.
- Project projections rebuild from raw rows.
- No network calls occur during validation, ingest, projection, or retrieval.

### Stage 2: Project Documents And Markdown Trees

Adopt next:

- Markdown directories.
- Project docs, README files, RFCs, changelogs, TODO files, design notes.
- Selected personal notes only with explicit source-level privacy selection.

Success criteria:

- File identity uses root id, normalized relative path, content hash, and import
  manifest.
- Re-import is idempotent when content is unchanged.
- File movement or content drift is detected without rewriting raw rows.
- Headings, links, tags, frontmatter, path references, and chunks rebuild from
  raw file snapshots.
- Personal vaults default to stricter privacy than project docs.

### Stage 3: Exported Communication Logs

Adopt only after Stages 0-2 are boring:

- Email from local mbox/Maildir or explicit export.
- Slack/Discord/Matrix/Signal/Telegram/iMessage/SMS exports when they are local
  files or copied local databases.
- Meeting transcripts and voice transcription files.

Success criteria:

- Thread, message, participant, edit/delete, reply, reaction, and attachment
  metadata semantics are source-specific and tested.
- Third-party data defaults to Tier 2+ or stricter.
- Claim extraction is disabled unless the source contract and user approval
  enable it.
- Attachments are metadata-first unless text extraction is explicitly allowed.

### Stage 4: Observation And Life Sources

Adopt after project/document/communication lanes prove the contract:

- Calendar exports.
- Photo/video/screenshot libraries.
- Location timelines, GPX tracks, and activity exports.
- Receipts, travel records, reservations, warranties, home inventory.
- Health and finance exports only behind stricter privacy policy.

Success criteria:

- RFC 0033 observation semantics are used before claims/beliefs.
- RFC 0034 photo/media and RFC 0035 location/place constraints are preserved.
- Exact coordinates, face data, health, finance, contacts, and third-party data
  do not enter ordinary assistant context by default.
- Coverage gaps are explicit.
- Daily-biography downstream needs from RFC 0036 are preserved without
  generating authoritative prose as raw evidence.

### Stage 5: Live Capture

Adopt last:

- Manual capture.
- MCP capture.
- Local watcher-based file capture.
- Optional local audio/screenshot capture only with explicit visibility and
  local disable controls.

Success criteria:

- Live capture is explicit, visible, locally disabled by default, and
  immediately auditable.
- Backfill importers are already reliable for the same source family.
- Disable controls and coverage gaps are tested.
- No continuous surveillance capture is enabled by default.

## Evaluation Gates

Gate outcomes follow RFC 0049 style:

```text
pass
fail
blocked_upstream
not_run
accepted_with_scope_limit
```

Promotion levels:

| Level | Meaning |
|-------|---------|
| Level 0 | Developer fixture smoke only. |
| Level 1 | Explicit local manual ingest/search for a named source. |
| Level 2 | Opt-in automatic projection or context use for a named source. |
| Level 3 | Routine/default source-family enablement. |

No source family reaches Level 3 until all gates required for that family pass
through actual importer/retrieval paths.

| Gate | Purpose | Required by | Failure action |
|------|---------|-------------|----------------|
| EG-SI-000 No-Egress | Prove validator, ingest, projection, embedding/model helpers, retrieval, packet building, and evaluation make no outbound network calls. | All levels for covered path; OS-level evidence for Level 3. | `fail` blocks the covered corpus-reading path. |
| EG-SI-010 Source Contract Validator | Prove every adapter declares mandatory fields and closed vocabulary values. | Level 0+ | `fail` blocks implementation beyond fixture smoke. |
| EG-SI-020 Raw Ingest Idempotency And Conflict | Prove idempotent re-import, conflict rejection, immutable raw rows, and deterministic manifests. | Level 1+ | `fail` blocks source import. |
| EG-SI-030 Tenant/Corpus/Source Isolation | Prove source identity, tenant/corpus, and source-family boundaries through actual service/CLI/MCP paths where applicable. | Level 1+ where retrieval exists | `fail` blocks retrieval and packet use. |
| EG-SI-040 Privacy, Redaction, And `raw_payload` Leakage | Prove projection rows and packet/audit rows do not smuggle higher-tier content, withheld content, absolute paths, identity labels, or pre-redaction data. | Level 1+ | `fail` blocks retrieval-visible projection. |
| EG-SI-050 Projection Rebuild And Activation | Prove projections rebuild from raw evidence, activate all-or-prior, invalidate stale rows, and preserve prior active rows on failure. | Level 2+ | `fail` blocks automatic projection use. |
| EG-SI-060 Exact Reference And Citation | Prove known ids, paths, commit SHAs, run ids, artifact hashes, message ids, or asset ids retrieve cited rows without vector search. | Level 1+ where exact refs exist | `fail` blocks quality claims for the source. |
| EG-SI-070 Extraction Eligibility | Prove sensitive and third-party source families do not enter claim extraction unless explicitly enabled. | Level 2+ for extraction | `fail` blocks extraction for the source. |
| EG-SI-080 Coverage, Gaps, And Lifecycle | Prove missing streams, disabled sources, tombstones, redactions, withheld markers, stale projections, and coverage gaps are represented explicitly. | Level 2+ | `fail` blocks downstream packets or biography projections. |
| EG-SI-090 Audit Reconstruction | Prove import/projection/packet omission audit can reconstruct selected and omitted candidates without leaking unauthorized content. | Level 2+ for packet use | `fail` blocks packet injection. |
| EG-SI-100 Source-Family Fixture Matrix | Prove the named source family has deterministic fixtures covering positive, negative, malformed, redacted, privacy, stale, conflict, and no-data cases. | Level 2+ | `blocked_upstream` until fixture coverage exists. |

Minimum source-family gate set:

| Source family | Required extra cases |
|---------------|----------------------|
| Git | Same repository imported twice has no duplicate commit events; changed repository identity is not merged silently; rewritten history is new evidence or conflict; dirty working tree is labeled and opt-in. |
| Build artifacts | Run links to commit SHA when present; long logs do not enter packets by default; failure signatures cite artifact and line/window; secret-shaped output is redacted or tier-promoted. |
| Markdown/docs | Path and content hash identity; moved files do not overwrite raw rows; heading/link/frontmatter projections rebuild; personal vault privacy defaults hold. |
| Human communication | Deleted/edited message semantics tested; duplicate exports from multiple devices handled; participant and third-party privacy defaults hold; extraction disabled by default. |
| Media/location/life | Exact coordinate and biometric defaults hold; binary bodies not stored in ordinary rows; local model stages are versioned and no-egress; observation and coverage-gap rows exist before claims. |
| Live capture | Capture is visibly enabled, locally disabled by default, and auditable; disable creates coverage gaps rather than silent absence. |

## Initial Implementation Slice

The next implementation slice should be narrow:

1. Add a source contract template and example contracts for `git`,
   `build_artifact`, and `exported_chat`.
2. Add `source_kind='git'` only when a local git importer is ready.
3. Import commit metadata and diff stats first; patch bodies opt-in.
4. Add `source_kind='build_artifact'` only when a local artifact directory
   importer is ready.
5. Import JUnit XML, coverage JSON/XML, benchmark JSON, lint output, and plain
   logs as local artifacts with content hashes.
6. Project both into `project_event`, `execution_artifact`, `code_reference`,
   and `artifact_reference` rows or their accepted concrete table equivalents.
7. Expose exact-reference retrieval by commit SHA, path, run id, and artifact
   hash.
8. Keep full patch bodies, full logs, and human communications out of memory
   packets by default.

This slice deliberately avoids human-chat extraction, media bodies, cloud APIs,
live capture, and generic source registry migration.

## Cross-References

| Proposed source or concern | Existing reference | Implication for RFC 0050 |
|----------------------------|--------------------|--------------------------|
| General non-text expansion | RFC 0033 | Use observations and interpretations before claims/beliefs for multimodal and dense activity data. |
| Photos, videos, screenshots, OCR | RFC 0034 | Preserve raw media metadata; use local-only vision/OCR; face recognition requires stricter review and privacy. |
| Location, places, visits | RFC 0035 | Exact coordinates are sensitive observations; place/visit projections stay rebuildable; coverage gaps are first-class. |
| Daily biography outputs | RFC 0036 | Source adapters must preserve temporal, coverage, people/place, provenance, and gap data for future day packets. |
| Striatum raw application memory | RFC 0044 boundary as reflected in README/SPEC/tests | Keep application memory separate from personal memory; read-only, local, cited, tenant/corpus scoped. |
| Striatum bundle contract | RFC 0045 | Reuse manifest, item identity, hashing, lifecycle, privacy, visibility, classification, and validation vocabulary. |
| Striatum projection generation | RFC 0046 | Reuse generation-scoped idempotency, active serving, exact references, copied authorization fields, and invalidation rules. |
| Retrieval boundary | RFC 0047 | Retrieval is optional, bounded, local, cited, non-authoritative, and failure-tolerant. |
| Context injection | RFC 0048 | Retrieved memory is evidence, never instructions or authority; omission audit and packet labels apply. |
| Evaluation gates | RFC 0049 | Use named gates, outcome vocabulary, fixture evidence, no-egress, isolation, redaction, freshness, and audit reconstruction. |
| Current AI conversation exports | `docs/ingestion.md`, `README.md`, `BUILD_PHASES.md` | Keep ChatGPT/Claude/Gemini as conversation evidence; do not force all future sources into conversations. |
| Current schema | `docs/schema/README.md`, migrations | Raw tables already support sources/conversations/messages/notes/captures; `source_kind` enum is the near-term extension point. |
| Striatum e2e backlog | `STRIATUM_MEMORY_E2E_BACKLOG.md` | Treat RFC 0045-RFC 0049 as design reference for working layers; do not make paper promotion a blocker for narrow, tested local code. |

## Open Questions

### OQ-SI-001: Patch Body Retention

Should git patch bodies be retained as raw evidence by default, or should the
first importer retain only commit metadata, parent links, messages, changed
paths, and diff stats with patch capture opt-in?

Default recommendation: metadata and diff stats first; patch bodies opt-in.

### OQ-SI-002: Build Log Storage

Should build logs be copied into a managed local content-addressed store, or
referenced by path and hash with drift detection?

Default recommendation: path/hash references first, with content-addressed
storage reserved for logs that must survive source-directory cleanup.

### OQ-SI-003: Privacy Tier Defaults

Which source families should default to Tier 1, Tier 2, Tier 3, or stricter?

Default recommendation: project evidence Tier 1 when explicitly selected;
personal notes and human communications Tier 2+; browser/app activity Tier 3;
exact location, health, finance, contacts, and biometrics Tier 4+.

### OQ-SI-004: `source_kind` Enum Versus Registry

When should Engram replace or supplement the closed enum with an extensible
source registry?

Default recommendation: keep adding enum values deliberately for the next few
adapters; revisit when migration churn becomes a real blocker.

### OQ-SI-005: First Non-AI Chat Adapter

Which local export format should be the first non-AI communication adapter:
mbox, Maildir, Slack export JSON, Discord export JSON, Matrix export JSON, or
another source?

Default recommendation: choose the simplest local file export with good
fixtures and clear third-party privacy handling, not the most popular platform.

### OQ-SI-006: Contract Storage Shape

Should source contracts remain documentation plus tests, or become a database
table / manifest column before broad importer work?

Default recommendation: documentation plus importer tests for the first slice;
add a table or manifest column only when projections need to query contract
metadata at runtime.

### OQ-SI-007: Human Communication Extraction Gate

Should human chat and email claim extraction be blocked until a separate
third-party privacy policy exists?

Default recommendation: yes. Import and retrieval may be useful earlier, but
claim extraction should remain source-specific and opt-in.

## Proposal Status

This RFC draft recommends accepting the source contract discipline before adding
more source families. It does not recommend accepting every proposed source
family now. The only near-term implementation path proposed here is the narrow
local project-source slice: git metadata/diff stats, build artifacts, and
project-document ingestion behind source contracts and RFC 0049-style gates.
