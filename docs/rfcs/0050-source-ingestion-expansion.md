<a id="rfc-0050"></a>
# RFC 0050: Source Ingestion Expansion And Source Contract

Lane: codex
Role: synthesizer

| Field | Value |
|-------|-------|
| RFC | RFC-0050 |
| Title | Source Ingestion Expansion And Source Contract |
| Status | proposal |
| Date | 2026-05-15 |
| Authors | claude lane, codex lane, gemini lane |
| Synthesizer | codex lane |
| Primary input | `docs/design/source-ingestion-expansion-proposal-2026-05-15.md` |
| Review inputs | `docs/reviews/source-ingestion-rfc-research-2026-05-15/DRAFT_claude.md`, `DRAFT_codex.md`, `DRAFT_gemini.md`, `PRIOR_ART_DOSSIER.md`, `FINDINGS_LEDGER.md` |
| Context | `AGENTS.md`, `README.md`, `HUMAN_REQUIREMENTS.md`, `SPEC.md`, `BUILD_PHASES.md`, `ROADMAP.md`, `docs/schema/README.md`, `STRIATUM_MEMORY_E2E_BACKLOG.md`, `docs/AGENT_CONTEXT_NOTES.md`, RFC 0033-RFC 0036, RFC 0044-RFC 0049 |

## Summary

Engram can expand beyond AI conversation exports without weakening its core
contract only if every new source family arrives through a declared local source
contract.

This RFC proposes that contract. Each adapter must define:

1. the immutable raw evidence boundary;
2. the rebuildable projection families it emits;
3. the default downstream consumers that may see those projections;
4. the provenance, privacy, sensitivity, confidence, lifecycle, and rebuild
   rules that protect the evidence.

The near-term rollout starts with high-signal local project evidence: git commit
metadata and diff stats, build/test/lint/coverage/benchmark artifacts, Striatum
alignment where useful, and selected Markdown/project documents. Human
communication exports, browser/app activity, media, location, health, finance,
contacts, and live capture remain behind explicit later gates.

This is a proposal only. It does not add source kinds, create migrations,
promote adjacent RFCs, edit the decision log, edit the RFC index, or authorize
default ingestion of new personal sources.

## Context

The primary input is
`docs/design/source-ingestion-expansion-proposal-2026-05-15.md`. That design
frames the expansion from current AI conversation sources and Striatum bundles
to the wider local evidence set: chat logs, commit history, build artifacts,
project notes, files, media, activity logs, and life records.

Engram's load-bearing constraints remain unchanged:

- no cloud dependency;
- no telemetry;
- no user data leaving the machine unless explicitly requested;
- no outbound network from corpus-reading processes;
- immutable raw evidence;
- rebuildable derived tables and projections;
- provenance, confidence, stability class, privacy, and auditability;
- gaps and withheld material represented explicitly rather than silently absent.

Current source scope is narrow by design. ChatGPT, Claude, and Gemini exports
land as `sources -> conversations -> messages`. Striatum bundles land as
`sources -> captures` under the local application-memory boundary described by
the RFC 0044 work reflected in `README.md`, `SPEC.md`, and
`STRIATUM_MEMORY_E2E_BACKLOG.md`. Phase 2 and Phase 3 remain intentionally
limited to AI-conversation evidence. Adding a raw importer must not
automatically make that source eligible for segmentation, claim extraction,
belief consolidation, context packets, or application-memory retrieval.

The practical limitation is that `source_kind` is currently a closed enum and
source behavior is mostly implicit in importer code. That remains acceptable
for the next few concrete adapters, but it is not enough for broad expansion.
The missing artifact is a reusable contract that reviewers and tests can apply
before implementation starts.

## Goals

1. Define a reusable source contract for future local adapters.
2. Preserve append-only raw evidence and rebuildable projections.
3. Keep no-egress coverage explicit for all corpus-reading paths.
4. Define a closed initial projection vocabulary.
5. Separate audience/lifecycle privacy tiers from sensitivity classification.
6. Require source-family extraction eligibility gates.
7. Sequence adoption from lower-risk project evidence toward higher-sensitivity
   life evidence.
8. Define evaluation gates and promotion levels for new source families.
9. Keep generated summaries and memory products out of the raw-evidence and v1
   projection vocabulary.

## Non-Goals

- No hosted API ingestion.
- No automatic Gmail, Slack, GitHub, GitLab, Apple, Google, browser, or cloud
  account access.
- No telemetry, remote vector store, hosted embedding, hosted reranking, hosted
  OCR, hosted vision, hosted LLM, or SaaS persistence.
- No live capture or continuous surveillance as an initial source.
- No bidirectional sync back to source systems.
- No full media bodies, full patch bodies, full raw logs, or raw transcripts in
  context packets by default.
- No human-chat, email, or meeting-transcript claim extraction by default.
- No personal-memory access from Striatum or any application-memory tenant by
  default.
- No generated-product projection family until a separate generated-product
  privacy, citation, audit, and gate contract is accepted.
- No replacement of the current closed `source_kind` enum in the first
  implementation slice unless enum churn becomes a measured migration burden.

## Source Contract

Every new source adapter must declare a contract before importer code is
written. The contract may begin as checked-in YAML or Markdown plus tests; it
does not need to be a runtime registry on day one.

### Required Questions

| Question | Required answer |
|----------|-----------------|
| Raw boundary | Which export file, local database copy, repository object, directory snapshot, media asset, or capture record is the immutable evidence boundary? |
| Projection | Which closed projection families are emitted, and which fields remain raw-only? |
| Default consumers | Which systems may see the derived projection by default: retrieval, packet builder, segmentation, extraction, daily biography, or none? |
| Protection rules | Which provenance, confidence, sensitivity, privacy, lifecycle, redaction, rebuild, and no-egress rules apply? |

An adapter that cannot answer all four questions does not pass review.

### Mandatory Fields

The source contract uses a rich field set because the fields are load-bearing,
not illustrative:

```yaml
source_kind: git
source_family: project_execution
sub_kinds:
  - commit
  - branch
  - tag
  - diff_stat

raw_artifact_boundary:
  description: local repository object database plus adapter manifest
  acquisition:
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
  edited_at: null

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
  privacy_tier_default: 1
  sensitivity_class_default: routine_project
  promotion_policy: reclassification_capture
  raw_payload_policy: no higher-tier or higher-sensitivity smuggling

projection_families:
  - project_event
  - code_reference

operational_families:
  - source_audit
  - coverage_gap

extraction_eligibility:
  default: metadata_only
  participant_third_party: false
  opt_in_required_for:
    - patch_body
    - private_author_email
    - uncommitted_worktree

raw_retention:
  required:
    - object ids
    - commit metadata
    - changed path summaries
    - manifest hash
  optional:
    - patch body

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
  - third_party_extraction_off_by_default
  - exact_reference_citation
```

### Identity Split

New adapters must not rely only on `(source_kind, external_id)` once they cross
multi-repository, multi-account, or multi-corpus boundaries. Contracts must
separate:

- `source_instance_id`: the enrolled local source instance, such as a repository
  root identity, mail account export identity, workspace export identity, vault
  root identity, or media library export identity;
- item identity keys: the immutable item version, such as commit SHA, message
  id, file content hash, artifact hash, asset id, or calendar uid plus version;
- logical identity keys: the stable conceptual object, such as branch name,
  document path, email thread id, recurring event id, or media album id.

Open question OQ-SI-008 covers whether the `sources` uniqueness boundary must
expand to include `tenant_id` and `corpus_id` before multi-repo or
multi-account adapters land.

## Projection Vocabulary

Projection families are closed. A new source adapter must declare existing
families, or a successor RFC must add a new family. This prevents unreviewed
JSON folklore from becoming retrieval and privacy infrastructure.

This RFC separates evidence-shape families from operational families.

### Evidence Projection Families

| Family | Purpose | Early sources |
|--------|---------|---------------|
| `conversation_thread` | Thread, participant, message, edit/delete, reaction, reply, and attachment metadata. | AI exports, exported chat, email, meeting transcripts. |
| `document_record` | File or document identity, path snapshot, title, frontmatter, headings, links, tags, chunks, and content hash. | Markdown trees, Obsidian, project docs, saved pages, text exports. |
| `project_event` | Time-bound project action or state transition. | Git commits, branch/tag changes, Striatum runs, issue/PR exports, release notes. |
| `execution_artifact` | Build/test/lint/coverage/benchmark/deployment output summaries. | JUnit XML, pytest output, coverage reports, benchmark JSON, logs. |
| `code_reference` | Repository, commit, path, symbol, diff stat, line/window, branch, or tag reference. | Git history, source trees, build reports, Striatum commit rows. |
| `artifact_reference` | Content-addressed or path/hash reference to a file-like artifact. | Build artifacts, reports, generated files, media sidecars. |
| `observation` | Atomic source-backed or local-model-derived observation that is not a belief. | Calendar, photos, location, OCR, health/activity, receipts. |
| `place_event` | Visit, location sample cluster, place candidate, or event interval. | Location exports, EXIF coordinates, calendar locations, manual check-ins. |
| `asset_record` | Media or blob-like asset metadata without storing binary bodies in ordinary rows. | Photos, videos, screenshots, audio, PDFs. |

### Operational Families

| Family | Purpose | Applicability |
|--------|---------|---------------|
| `coverage_gap` | Explicit missing, disabled, withheld, stale, unavailable, or intentionally uncollected coverage. | All source families. |
| `source_audit` | Local-only import, projection, omission, conflict, reclassification, rebuild, and gate evidence records. | All source families. |

Operational families are not claims, beliefs, or generated products. They exist
so downstream packets and biography compilers can say "no data", "disabled",
"withheld", "stale", or "not imported" with provenance.

### Projection Invariants

Every projection family follows these invariants:

- projection rows are caches over raw evidence;
- projection rows cite raw row ids or raw artifact ids;
- projection rows may cite input projections, but they cannot be grounded only
  in another derived row;
- projections carry `tenant_id`, `corpus_id`, source identity, generation,
  derivation version, active/invalidation state, and citation fields;
- retrieval-visible rows inherit the raw row's effective privacy tier and
  sensitivity handling, or become stricter;
- serving queries read only active, non-invalidated projection rows;
- privacy promotion, redaction, tombstone, withheld markers, raw conflicts, and
  changed raw hashes invalidate affected retrieval-visible rows before lower
  tier or lower sensitivity retrieval can serve them.

The Striatum projection work described by RFC 0046 and implemented in the
current Striatum e2e track is the main local precedent: raw captures remain
canonical, projections are generation-scoped, and retrieval reauthorizes
against stored tenant/corpus/source identity.

## Privacy And Sensitivity

The synthesized decision is to keep `privacy_tier` anchored to
`HUMAN_REQUIREMENTS.md`, not to use it as a generic sensitivity scale.

Current canonical tiers are audience/lifecycle tiers:

- Tier 1: only me, only on this machine;
- Tier 2: surfaceable to my AI assistants for context;
- Tier 3: shareable with partner or chosen heirs;
- Tier 4: posthumous-only release;
- Tier 5: redact-on-death.

Under that vocabulary, "higher number" does not mean "stricter" in ordinary
runtime use. Health, finance, exact coordinates, contacts, biometrics, and
third-party communications should not be silently assigned to Tier 4 or Tier 5
as a sensitivity shortcut. This RFC therefore proposes a separate contract
field, `sensitivity_class_default`, while leaving the schema-level question
open.

Initial sensitivity classes are closed for contracts:

```text
routine_project
personal_private
third_party_communication
calendar_contact
exact_location
biometric
health
finance
credential_or_secret_reference
raw_media
behavioral_activity
```

The effective default consumer decision is the combination of:

- `privacy_tier_default`;
- `sensitivity_class_default`;
- `extraction_eligibility`;
- retrieval surface authorization;
- packet or biography rendering policy.

### Source Defaults

| Source family | Default privacy tier | Default sensitivity class | Default posture |
|---------------|----------------------|---------------------------|-----------------|
| AI conversation exports: ChatGPT, Claude, Gemini | Current behavior, Tier 1 as implemented | `personal_private` unless operator later configures otherwise | Existing AI-conversation segmentation and extraction behavior remains unchanged. |
| Striatum application-memory bundles | Tier 1 within `tenant_id='striatum'` / authorized corpus | `routine_project` unless exported rows say otherwise | Application-memory boundary only; no personal memory by default. |
| Explicitly selected project git repositories | Tier 1 | `routine_project` | Commit metadata, parent links, messages, changed paths, and diff stats first; patch bodies opt-in. |
| Build/test/lint/coverage/benchmark artifacts | Inherit selected project source, minimum Tier 1 | `routine_project`, promoted if logs contain secrets or private paths | Summary projections first; full logs reference-only by default. |
| Project docs, RFCs, changelogs, READMEs | Tier 1 | `routine_project` | Good early retrieval candidates when explicitly selected. |
| Selected Markdown or notes trees | Project docs Tier 1; personal vaults Tier 1 unless explicitly promoted to assistant-visible Tier 2 | `routine_project` or `personal_private` | Markdown/plain text before binary formats; journals opt-in for extraction. |
| User corrections and manual captures | Explicit capture tier or inherited target tier | Inherit target or declared at capture time | Corrections are raw evidence, not direct row updates. |
| Email and human messaging exports | Tier 1 by default, with assistant exposure blocked until explicit opt-in | `third_party_communication` | Import from local exports may be useful; claim extraction off by default. |
| Team chat exports | Tier 1 by default, with assistant exposure blocked until explicit workspace opt-in | `third_party_communication` | Metadata-first; extraction off by default. |
| Meeting transcripts | Tier 1 by default | `third_party_communication` when participants include others; `personal_private` when solo/operator-only | `participant_third_party` controls extraction eligibility. |
| Calendar, contacts, reminders | Tier 1 by default | `calendar_contact` | Metadata-first; per-calendar opt-down to assistant-visible Tier 2 only when operator-only and low sensitivity. |
| Browser, shell, window, and app activity | Tier 1 by default | `behavioral_activity` | Deferred; explicit local backfills only; no continuous live capture initially. |
| Photos, videos, screenshots, OCR | Tier 1 by default | `raw_media`, plus specialized classes for OCR, faces, or location | Metadata-first; defer to RFC 0033/RFC 0034. |
| Exact coordinates and place traces | Tier 1 by default | `exact_location` | Defer to RFC 0035; ordinary assistant context uses coarser renderings unless explicitly authorized. |
| Health and biometrics | Tier 1 by default | `health` or `biometric` | Manual/imported local evidence only; no ordinary assistant context without explicit grant. |
| Finance, receipts, tax records | Tier 1 by default | `finance` | Manual/imported local evidence only; no ordinary assistant context without explicit grant. |
| Credential or secret references | Tier 1 by default | `credential_or_secret_reference` | Engram should reference vault/document identities, not store secrets. |

### No-Egress Invariant

Every corpus-reading process must run without outbound network calls:

- importer;
- validator;
- projection worker;
- local model helper;
- embedding stage;
- retrieval service;
- packet builder;
- evaluator;
- MCP serving path;
- biography or generated-product compiler once those exist.

If freshness requires an external lookup, Engram emits a gap or operator action
hint. The Engram-reading process does not perform the lookup.

### No-Derived-Product-Leak Invariant

Generated summaries, packet text, daily biographies, OCR text, captions,
source-specific summaries, and context renderings are derived products. They
inherit privacy, sensitivity, citation, and audit requirements from the
evidence they cite. They are not raw evidence. They are not eligible for a
`generated_product` projection family until a separate generated-product
contract is accepted.

### Third-Party Data Gate

Sources with third-party participant content must declare
`participant_third_party: true` unless the adapter can prove otherwise.

For those sources:

- extraction defaults to off;
- attachment bodies are metadata-first unless the contract opts into text
  extraction;
- the CLI must expose an explicit opt-in flag before extraction;
- `describe-corpus` or an equivalent local description surface must show
  extraction eligibility;
- a separate third-party privacy policy remains an open prerequisite before
  Step 3 extraction becomes routine.

## Rollout Order

Rollout is staged. Each source family must pass its contract and gate level
before promotion.

### Stage 0: Contract And Taxonomy

Create the source contract template, closed vocabularies, fixture harness, and
gate reporting shape. This RFC is the proposal for that work.

Success criteria:

- contract template exists;
- closed projection and operational family vocabularies exist;
- fixture-only adapter can run contract validation, no-op import, no-op
  projection, and no-egress checks locally;
- gate reports include fixture path, manifest hash, row count, contract
  version, adapter version, commands run, outcome, and residual limits.

### Stage 1: Project Execution Sources

Adopt in this order:

1. local git commit metadata and diff stats;
2. local build/test/lint/coverage/benchmark artifact directories;
3. Striatum artifact/reference alignment where the source contract improves the
   existing application-memory path.

Success criteria:

- re-import is idempotent;
- changed or rewritten source evidence becomes new evidence or a conflict, not
  an in-place rewrite;
- commit SHA, path, run id, artifact hash, and failure signature
  exact-reference retrieval work without vector search;
- full patch bodies and full logs are omitted from packets unless explicitly
  requested;
- project projections rebuild from raw rows;
- validation, ingest, projection, retrieval, and packet paths have no outbound
  network.

### Stage 2: Project Documents And Markdown Trees

Adopt Markdown directories, project docs, READMEs, RFCs, changelogs, TODO
files, design notes, and selected personal notes with explicit source-level
privacy/sensitivity choices.

Success criteria:

- file identity uses root id, normalized relative path, content hash, and
  import manifest;
- re-import is idempotent when content is unchanged;
- file movement or content drift is detected without rewriting raw rows;
- headings, links, tags, frontmatter, path references, and chunks rebuild from
  raw file snapshots;
- personal vault extraction is opt-in.

### Stage 3: Exported Communication Logs

Adopt only after Stages 0-2 are boring:

- email from local `mbox`, Maildir, or explicit export;
- Slack, Discord, Matrix, Signal, Telegram, iMessage, SMS, IRC, and similar
  exports when they are local files or copied local databases;
- meeting transcripts and voice transcription files.

Success criteria:

- thread, message, participant, edit/delete, reply, reaction, and attachment
  metadata semantics are source-specific and tested;
- `participant_third_party` is machine-checkable;
- claim extraction is disabled unless the source contract and operator approval
  enable it;
- attachments are metadata-first unless text extraction is explicitly allowed;
- duplicate exports from multiple devices are deduplicated.

### Stage 4: Observation And Life Sources

Adopt after project/document/communication lanes prove the contract:

- calendar exports;
- photo/video/screenshot libraries;
- location timelines, GPX tracks, and activity exports;
- receipts, travel records, reservations, warranties, home inventory;
- health and finance exports only behind stricter sensitivity policy.

RFC 0033, RFC 0034, RFC 0035, and RFC 0036 remain the design references for
this stage. This RFC does not promote them into accepted implementation.

Success criteria:

- observation semantics are used before claims/beliefs;
- exact coordinates, face data, health, finance, contacts, OCR, and third-party
  data do not enter ordinary assistant context by default;
- coverage gaps are explicit;
- daily-biography downstream needs preserve provenance and gaps without
  treating generated prose as evidence.

### Stage 5: Live Capture

Adopt last:

- manual capture;
- MCP capture;
- local watcher-based file capture;
- optional local audio/screenshot capture only with explicit visibility and
  local disable controls.

Success criteria:

- live capture is explicit, visible, locally disabled by default, and auditable;
- backfill importers for the same source family are already reliable;
- disable controls create coverage gaps rather than silent absence;
- no continuous surveillance capture is default-on.

## Evaluation Gates

Gate ids use the `EG-SI-NNN` namespace. This avoids collision with RFC 0049
Striatum gates while making the source-ingestion scope explicit.

Gate outcomes use the RFC 0049-style vocabulary:

```text
pass
fail
blocked_upstream
not_run
accepted_with_scope_limit
```

### Promotion Levels

| Level | Meaning |
|-------|---------|
| Level 0 | Developer fixture smoke only. |
| Level 1 | Explicit local manual ingest and search for a named source. |
| Level 2 | Opt-in automatic projection or context use for a named source. |
| Level 3 | Routine or default source-family enablement. |

No source family reaches Level 3 until every gate required for that family
passes through actual importer, projection, retrieval, packet, and MCP paths
where applicable.

### Gate Matrix

| Gate | Purpose | Required by |
|------|---------|-------------|
| `EG-SI-000 No-Egress` | Prove validator, ingest, projection, embedding/model helpers, retrieval, packet building, evaluation, and MCP serving paths make no outbound calls. | All levels for the covered path; OS-level evidence for Level 3. |
| `EG-SI-010 Source Contract Validator` | Prove every adapter declares mandatory fields and closed vocabulary values. | Level 0+ |
| `EG-SI-020 Raw Ingest Idempotency And Conflict` | Prove idempotent re-import, conflict rejection, immutable raw rows, and deterministic manifests. | Level 1+ |
| `EG-SI-030 Tenant/Corpus/Source Isolation` | Prove source identity, tenant/corpus, and source-family boundaries through actual service/CLI/MCP paths where applicable. | Level 1+ where retrieval exists |
| `EG-SI-040 Privacy, Sensitivity, Redaction, And `raw_payload` Leakage` | Prove projections, packet items, and audits do not smuggle higher-tier, higher-sensitivity, withheld, absolute-path, identity-label, or pre-redaction content. | Level 1+ |
| `EG-SI-050 Projection Rebuild And Activation` | Prove projections rebuild from raw evidence, activate all-or-prior, invalidate stale rows, and preserve prior active rows on failure. | Level 2+ |
| `EG-SI-060 Exact Reference And Citation` | Prove known ids, paths, commit SHAs, run ids, artifact hashes, message ids, or asset ids retrieve cited rows without vector search. | Level 1+ where exact refs exist |
| `EG-SI-070 Extraction Eligibility` | Prove sensitive and third-party source families do not enter claim extraction unless explicitly enabled. | Level 2+ for extraction |
| `EG-SI-080 Coverage, Gaps, And Lifecycle` | Prove missing streams, disabled sources, tombstones, redactions, withheld markers, stale projections, and coverage gaps are explicit. | Level 2+ |
| `EG-SI-090 Audit Reconstruction` | Prove import/projection/packet omission audits reconstruct selected and omitted candidates without loading unauthorized content. | Level 2+ for packet use |
| `EG-SI-100 Source-Family Fixture Matrix` | Prove deterministic fixtures cover positive, negative, malformed, redacted, privacy, sensitivity, stale, conflict, and no-data cases. | Level 2+ |

### No-Egress Evidence Levels

`EG-SI-000` must report which evidence level passed:

- Level A: code/dependency inspection plus monkeypatched socket or equivalent
  process-local failure tests;
- Level B: sandboxed-process evidence, such as network namespace, firewall,
  OS sandbox, or equivalent deny-by-default egress proof.

Level A is sufficient for early fixture and explicit manual work. Level B is
required before any source family becomes Level 3 or default-on extraction.

### Source-Family Extra Cases

| Source family | Required extra cases |
|---------------|----------------------|
| Git | Same repository imported twice has no duplicate commit events; changed repository identity is not silently merged; rewritten history is new evidence or conflict; dirty worktree is labeled and opt-in. |
| Build artifacts | Run links to commit SHA when present; long logs do not enter packets by default; failure signatures cite artifact and line/window; secret-shaped output is redacted or sensitivity-promoted. |
| Markdown/docs | Path and content hash identity; moved files do not overwrite raw rows; heading/link/frontmatter projections rebuild; personal vault extraction remains opt-in. |
| Human communication | Deleted/edited message semantics tested; duplicate exports handled; participant and third-party defaults hold; extraction disabled by default. |
| Media/location/life | Exact coordinate and biometric defaults hold; binary bodies not stored in ordinary rows; local model stages are versioned and no-egress; observation and coverage-gap rows exist before claims. |
| Live capture | Capture is visibly enabled, locally disabled by default, and auditable; disable creates coverage gaps rather than silent absence. |

## Initial Implementation Slice

The next implementation slice should remain narrow:

1. add a source contract template and example contracts for `git`,
   `build_artifact`, and `exported_chat`;
2. add `source_kind='git'` only when a local git importer is ready;
3. import commit metadata, parent links, commit messages, changed paths, and
   diff stats first; keep patch bodies opt-in;
4. add `source_kind='build_artifact'` only when a local artifact directory
   importer is ready;
5. import JUnit XML, coverage JSON/XML, benchmark JSON, lint output, and plain
   logs as local artifacts with content hashes;
6. project both into `project_event`, `execution_artifact`, `code_reference`,
   `artifact_reference`, and operational audit/gap rows, or accepted concrete
   table equivalents;
7. expose exact-reference retrieval by commit SHA, path, run id, artifact hash,
   and failure signature;
8. keep full patch bodies, full logs, generated summaries, and human
   communications out of memory packets by default.

This slice deliberately avoids human-chat extraction, media bodies, cloud APIs,
live capture, generated products, and generic source-registry migration.

## Schema Direction

This section is direction, not a migration commitment.

### Short Term

- Continue adding `source_kind` enum values deliberately for concrete importers.
- Use `captures` as the landing zone for generic project/build artifacts where
  no specialized raw table exists.
- Keep `conversations` and `messages` for threaded chat-shaped evidence.
- Keep `notes` for document-shaped evidence where it fits the existing schema.
- Do not collapse all future sources into one generic JSON table.

### Medium Term

- Add a `source_contract_manifest` JSONB column on `sources` or a
  `source_contracts` table keyed by `source_kind` when runtime code needs to
  query contract metadata.
- Consider supplementing or replacing the closed `source_kind` enum with
  `source_kind TEXT` plus a checked registry only if enum churn becomes a real
  migration burden.
- Add projection tables per projection family only when generic `captures` plus
  source-specific projection tables no longer preserve queryability or
  invariants.

### Long Term

- Promote source contracts from docs/tests into a runtime registry after several
  source families prove the field set stable.
- Decide whether projection-family vocabulary should be schema-enforced through
  a registry table or remain documentation-plus-test convention.
- Reconcile source ingestion with future generated-product and biography
  compilers without treating generated prose as raw evidence.

## Scope Kept Out

These items are explicitly outside this RFC and the first implementation slice:

- **Cloud APIs and hosted services.** No direct account access or hosted model
  calls. Local exports and local files only.
- **Continuous live capture.** Backfills first; live capture later, explicit,
  visible, disabled by default, and auditable.
- **Media bodies.** Image, video, and audio bodies are deferred to RFC 0033 and
  RFC 0034 follow-up work. The first slice may store references and hashes, not
  ordinary retrieval-visible binary payloads.
- **Generated products.** Summaries, daily briefs, packet prose, wiki pages, and
  biographies remain out of the projection vocabulary until a generated-product
  contract is accepted.
- **Belief bypass.** No `belief_projection` family and no generated assertion
  path that skips claims and raw evidence citation.
- **Personal-memory paste-through.** Arbitrary pasted text does not inherit
  packet authority. It must be a manual capture or excluded.
- **Cross-tenant projection coupling.** Application-memory tenants such as
  `striatum` cannot read personal memory or secondary corpora without explicit
  Engram-local capabilities.
- **Closed enum replacement.** Do not replace the current closed enum in the
  first implementation slice unless enum churn becomes a measured migration
  burden.
- **Cross-tenant projection rules.** Generic source expansion does not authorize
  projections in one tenant to reach raw rows in another tenant.
- **Bidirectional sync.** Engram is a local read consumer of sources. It does
  not mutate Obsidian, git, mailboxes, calendars, chat exports, photo libraries,
  or source systems.
- **Password manager or document vault replacement.** Engram may reference
  credential/document identities, but secret storage belongs elsewhere unless a
  later RFC explicitly draws that boundary.

## Cross-References

| Area | Reference | Relevance |
|------|-----------|-----------|
| Multimodal observation substrate | RFC 0033 | Stage 4 uses observations before claims/beliefs for dense non-text sources. |
| Photo libraries and local vision | RFC 0034 | Media ingestion remains local-only, metadata/observation-first, and post-v1. |
| Location and places | RFC 0035 | Exact coordinates, visits, place candidates, and gaps require specialized privacy and projection handling. |
| Daily biography compiler | RFC 0036 | Source contracts must preserve temporal, coverage, people/place, provenance, and gap data for future day packets. |
| Striatum Phase 1 boundary | RFC 0044 as reflected in `README.md`, `SPEC.md`, and backlog docs | Application-memory is separate from personal memory; read-only, local, cited, tenant/corpus scoped. |
| Striatum corpus contract | RFC 0045 | Useful precedent for manifest, identity, hashing, lifecycle, privacy, redaction, and validation vocabulary. |
| Striatum projection schema | RFC 0046 | Reference pattern for generation-scoped, rebuildable, retrieval-visible projections over immutable captures. |
| Retrieval augmentation boundary | RFC 0047 | Retrieval is optional, bounded, local, cited, non-authoritative, and failure-tolerant. |
| Context injection policy | RFC 0048 | Retrieved memory is evidence, not instruction or authority; packet labels and omission audit apply. |
| Evaluation gates | RFC 0049 | Source ingestion uses compatible promotion levels, outcomes, no-egress evidence, isolation, redaction, freshness, and audit reconstruction. |
| Current AI exports | `docs/ingestion.md`, `README.md`, `BUILD_PHASES.md` | ChatGPT/Claude/Gemini remain conversation evidence and the only default-on extraction path today. |
| Current schema | `docs/schema/README.md` and migrations | Raw tables already support sources/conversations/messages/notes/captures; enum source kinds are the near-term extension point. |
| Striatum e2e backlog | `STRIATUM_MEMORY_E2E_BACKLOG.md` | Treat RFC 0045-RFC 0049 as design reference for working layers, not paper-promotion blockers. |

## Synthesis Notes

This RFC synthesizes the three author drafts, prior-art dossier, and findings
ledger. The choices below resolve the flagged divergences.

| Ledger item | Resolution | Reason |
|-------------|------------|--------|
| SI-L-001 tier vocabulary | `privacy_tier` remains the `HUMAN_REQUIREMENTS.md` audience/lifecycle scale; `sensitivity_class_default` is added to the source contract. | Avoids using Tier 4/Tier 5 as a sensitivity shortcut and preserves posthumous/redact-on-death semantics. |
| SI-L-002 projection vocabulary | Adopt the granular Codex vocabulary, but split `coverage_gap` and `source_audit` into an operational band. | Keeps the vocabulary closed while satisfying the privacy review's concern that operational rows are not evidence-shape families. |
| SI-L-003 identity boundary | Adopt `source_instance_id`, item identity keys, and logical identity keys; preserve a uniqueness open question. | Multi-repo and multi-account adapters need more than `(source_kind, external_id)`. |
| SI-L-004 gate namespace | Use `EG-SI-NNN`. | Avoids RFC 0049 collisions and makes source-ingestion gate scope explicit. |
| SI-L-005/SI-L-006 deferrals | Scope-kept-out names enum timing, cross-tenant projection rules, and bidirectional sync. | Prevents omissions from being read as permission. |
| SI-L-007/SI-L-008 no-egress | The no-egress process list is complete and `EG-SI-000` has Level A/Level B evidence. | Distinguishes monkeypatched socket tests from OS-level denial. |
| SI-L-009 AI defaults | ChatGPT/Claude/Gemini remain current behavior, Tier 1 as implemented. | This RFC does not drift existing AI-conversation behavior. |
| SI-L-010 participant split | Add `participant_third_party`. | Meeting transcripts and communication exports need machine-checkable extraction defaults. |
| SI-L-011 calendar defaults | Calendar/contact sources default to Tier 1 plus `calendar_contact` sensitivity and blocked assistant exposure unless explicitly opted down/up for use. | Aligns with the canonical tier model while making calendars stricter in consumer eligibility. |
| SI-L-012 human extraction | Extraction off by default, CLI opt-in, `describe-corpus` visibility, and third-party policy open question. | Combines mechanism and policy instead of relying on prose. |
| SI-L-013/SI-L-014 derived products | Add the no-derived-product-leak invariant and exclude `generated_product` and `belief_projection`. | Prevents summaries, OCR, captions, packets, or biographies from becoming evidence shortcuts. |
| SI-L-015/SI-L-016 contract fields/tests | Use the richer contract template and the union test set. | Makes the fields enforceable rather than illustrative. |
| SI-L-017/SI-L-018 rollout | Preserve Stage 0-5 sequence and Stage 1 sub-order: git, build artifacts, Striatum alignment. | Matches convergent review guidance. |
| SI-L-019 first chat adapter | Preserve as open question; `mbox` is a strong candidate, not a decision. | The reviews disagreed and the operator should choose based on fixture and privacy handling. |
| SI-L-020/SI-L-021 promotion | Add Level 0-3 promotion and `accepted_with_scope_limit`. | Allows bounded partial evidence without flattening to pass/fail. |
| SI-L-022 gaps | Include `coverage_gap` as an operational family and gate. | Biography-scale recall needs explicit absence and disabled-source evidence. |
| SI-L-023 open questions | Carry forward the ledger's open questions as first-class RFC output. | Keeps operator decisions visible. |

## Open Questions

<a id="oq-si-001"></a>
### OQ-SI-001: Patch Body Retention

Should git patch bodies be retained as raw evidence by default, retained only
by opt-in, or represented as metadata and diff stats only?

Default recommendation: metadata and diff stats first; patch bodies opt-in.

<a id="oq-si-002"></a>
### OQ-SI-002: Build Log Storage

Should build logs be copied into a managed local content-addressed store, or
referenced by path and content hash with drift detection?

Default recommendation: path/hash references first; content-addressed storage
only for logs the operator wants Engram to preserve after source cleanup.

<a id="oq-si-003"></a>
### OQ-SI-003: Privacy Tier And Sensitivity Storage

Should the source contract's `sensitivity_class_default` remain documentation
plus tests, become a database field, or replace some current uses of
`privacy_tier` in retrieval-visible rows?

Default recommendation: keep `privacy_tier` as audience/lifecycle and add
sensitivity class first in contracts/tests; promote to schema when retrieval or
packet policy needs to query it.

<a id="oq-si-004"></a>
### OQ-SI-004: Source Kind Enum Versus Registry

When should the closed `source_kind` enum be supplemented or replaced by an
extensible source registry?

Default recommendation: keep deliberate enum additions for the next few
adapters; revisit when migration churn becomes a real blocker.

<a id="oq-si-005"></a>
### OQ-SI-005: First Non-AI Chat Adapter

Which local export format should be the first non-AI communication adapter:
`mbox`, Maildir, Slack export JSON, Discord export JSON, Matrix export JSON, or
another local format?

Default recommendation: choose the simplest local file export with good
fixtures and clear third-party privacy handling. `mbox` is a strong candidate,
not a decision.

<a id="oq-si-006"></a>
### OQ-SI-006: Third-Party Privacy Policy

What third-party privacy policy must exist before human communication extraction
can be enabled?

Default recommendation: import and metadata retrieval may precede the policy;
claim extraction should remain blocked until the policy exists.

<a id="oq-si-007"></a>
### OQ-SI-007: Contract Storage Shape

Should contract storage start as YAML/docs plus tests, a database table, or
both?

Default recommendation: docs/tests for the first slice; runtime registry only
when source metadata must be queried by production code.

<a id="oq-si-008"></a>
### OQ-SI-008: Source Uniqueness Boundary

Should `sources` uniqueness expand to include `tenant_id` and `corpus_id`
before multi-repo or multi-account adapters land?

Default recommendation: namespace `external_id` carefully for the first slice;
make a schema decision before broad multi-account import.

<a id="oq-si-009"></a>
### OQ-SI-009: Operational Families

Should `coverage_gap` and `source_audit` remain operational projection families,
or become schema-level tables shared by all source families?

Default recommendation: operational family vocabulary first; shared tables only
after two or more adapters need the same query shape.

<a id="oq-si-010"></a>
### OQ-SI-010: No-Egress Evidence Level

What no-egress evidence level is required before a source family can become
default-on?

Default recommendation: Level B OS-level evidence for Level 3/default-on and
for any default-on extraction path.

<a id="oq-si-011"></a>
### OQ-SI-011: Calendar Assistant Exposure

When may a calendar be explicitly made assistant-visible?

Default recommendation: only for operator-only, low-sensitivity calendars with
per-calendar opt-in and visible `describe-corpus` status.

<a id="oq-si-012"></a>
### OQ-SI-012: Credential And Document Vault Boundary

Where is the boundary between Engram and a password manager or document vault?

Default recommendation: Engram references credential/document identities and
provenance, but does not store secrets or become the vault.

## Proposal Status

This RFC recommends accepting the source-contract discipline before adding
more source families. It does not recommend accepting every proposed source
family now. The only near-term implementation path proposed here is the narrow
local project-source slice: source contract template, git metadata/diff stats,
build artifacts, project-document ingestion, and exact-reference retrieval
behind source contracts and `EG-SI-NNN` gates.
