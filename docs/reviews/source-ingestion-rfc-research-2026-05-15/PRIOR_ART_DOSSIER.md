# Source Ingestion RFC Prior-Art Dossier

author: operator
Lane: codex
Role: researcher
Date: 2026-05-15
Status: research artifact for RFC drafting; not an RFC, decision, or promotion packet

<a id="scope"></a>
## Scope

This dossier maps local prior art for the source-ingestion expansion RFC. It
does not propose architecture. It records existing contracts, adjacent RFC
coverage, Striatum boundary implications, privacy concerns, and questions for
the RFC drafters and reviewers.

Input evidence came from:

- Project canon: `AGENTS.md`, `README.md`, `HUMAN_REQUIREMENTS.md`,
  `SPEC.md`, `BUILD_PHASES.md`, `ROADMAP.md`, `docs/schema/README.md`,
  `STRIATUM_MEMORY_E2E_BACKLOG.md`, and `docs/AGENT_CONTEXT_NOTES.md`.
- Design prompt: `docs/design/source-ingestion-expansion-proposal-2026-05-15.md`.
- Ingestion docs and code: `docs/ingestion.md`, importer modules under
  `src/engram/`, and migrations under `migrations/`.
- RFC prior art: RFC 0033-RFC 0036 and RFC 0045-RFC 0049.

Scope note: `docs/rfcs/0044-*.md` is not present in this checkout. The local
RFC index lists RFC 0045-RFC 0049 and says those are proposal/review
provenance only, with current follow-up including RFC 0044 hardening and
EG-000 evidence (`docs/rfcs/README.md:59-69`). RFC 0044 evidence is therefore
cited through the current README/SPEC/backlog and review artifacts where the
checkout exposes it.

<a id="load-bearing-project-constraints"></a>
## Load-Bearing Project Constraints

Engram's source expansion is constrained by the local-first rule: no cloud
dependency, no telemetry, and no user data leaving the machine unless the
owner explicitly asks for that (`README.md:11-17`). `SPEC.md` repeats the
stricter serving posture: all data stays on-device and corpus-reading
processes have no outbound network (`SPEC.md:10-11`).

Raw evidence remains canonical. The README describes raw evidence as
append-only and derived data as rebuildable (`README.md:42-50`). The initial
schema encodes this with raw tables `sources`, `conversations`, `messages`,
`notes`, and `captures`, each carrying `raw_payload`, and triggers that reject
UPDATE/DELETE (`migrations/001_raw_evidence.sql:27-98`,
`migrations/001_raw_evidence.sql:113-144`).

The human requirements extend that discipline beyond the V1 source set:
future biographical records need temporal validity, provenance, confidence,
contradiction handling, privacy tiers, gaps-as-data, and manual capture as a
first-class path (`HUMAN_REQUIREMENTS.md:586-616`,
`HUMAN_REQUIREMENTS.md:650-716`).

<a id="current-source-contracts"></a>
## Current Source Contracts In Code

<a id="closed-source-kind"></a>
### Closed `source_kind`

The current database vocabulary is a PostgreSQL enum. Assuming all migrations
are applied, accepted values are:

```text
chatgpt
obsidian
capture
future
claude
gemini
striatum
```

Evidence:

- Base enum values are defined in `migrations/001_raw_evidence.sql:4-9`.
- `claude` is added in `migrations/003_source_kind_claude.sql:1`.
- `gemini` is added idempotently in `migrations/004_source_kind_gemini.sql:1`
  and `migrations/005_source_kind_gemini.sql:1`.
- `striatum` is added in `migrations/014_striatum_tenant_corpus.sql:3-5`.
- Raw tables enforce the enum on `sources`, `conversations`, `messages`,
  `notes`, and `captures` (`migrations/001_raw_evidence.sql:29`,
  `migrations/001_raw_evidence.sql:41`, `migrations/001_raw_evidence.sql:55`,
  `migrations/001_raw_evidence.sql:74`, `migrations/001_raw_evidence.sql:88`).

The source-expansion proposal accurately identifies this as a practical
limitation: `source_kind` is closed, and broad expansion will otherwise require
one migration per concrete family
(`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:56-59`).

<a id="raw-lanes"></a>
### Raw Evidence Tables

Current raw landing zones are:

- `sources`: source manifest boundary, filesystem path, content hash, and
  raw manifest payload (`migrations/001_raw_evidence.sql:27-36`;
  generated schema at `docs/schema/README.md:1007-1020`).
- `conversations` and `messages`: threaded text evidence, with Tier 1 default
  privacy (`migrations/001_raw_evidence.sql:38-66`).
- `notes`: document-like evidence, later given `privacy_tier`
  (`migrations/001_raw_evidence.sql:71-83`,
  `migrations/002_capture_reclassification.sql:2-3`;
  generated schema at `docs/schema/README.md:896-907`).
- `captures`: generic raw captures with `capture_type`, `content_text`,
  `observed_at`, Tier 1 default privacy, and later tenant/corpus/bundle
  fields (`migrations/001_raw_evidence.sql:85-98`,
  `docs/schema/README.md:562-579`).

The source-expansion proposal's four evidence lanes map onto these only
partly: conversation evidence has a mature table path, document/note evidence
has reserved schema but deferred runtime, project/build evidence currently
uses `captures` for Striatum, and observation/life evidence is mostly RFC
proposal material (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:101-210`).

<a id="closed-processing-scopes"></a>
### Closed Processing Scopes

Phase 2/3 processing is code-closed to AI conversations. Claim extraction
queries require `s.source_kind IN ('chatgpt', 'claude', 'gemini')` and
`conversation_id IS NOT NULL` (`src/engram/extractor.py:2016-2033`,
`src/engram/extractor.py:2546-2554`, `src/engram/extractor.py:2836-2856`).
README states Phase 2 and Phase 3 intentionally operate only on ChatGPT,
Claude, and Gemini; notes/captures/Obsidian remain future scope
(`README.md:220-222`).

This is important prior art for new source families: adding a raw importer
does not automatically make the evidence eligible for segmentation,
extraction, belief consolidation, retrieval, or context injection.

<a id="importer-patterns"></a>
## Existing Importer Patterns

<a id="ai-conversation-importers"></a>
### AI Conversation Importers

All three AI exporters use the same broad pattern:

1. Resolve an explicit local export path.
2. Build a source manifest with `source_kind`, `external_id`,
   `filesystem_path`, content hash, file count, and per-file hashes.
3. Insert or reuse a `sources` row keyed by `(source_kind, external_id)`.
4. Raise `IngestConflict` if the same source key points to changed content.
5. Insert `conversations` and `messages` with `ON CONFLICT DO NOTHING`.
6. Rely on raw table Tier 1 privacy defaults rather than setting a custom tier.

ChatGPT evidence:

- Accepts classic and split export layouts
  (`docs/ingestion.md:77-83`, `src/engram/chatgpt_export.py:89-130`).
- Source manifest and source key are based on the resolved export root path
  (`src/engram/chatgpt_export.py:97-122`,
  `src/engram/chatgpt_export.py:318-367`).
- Conversation id comes from `conversation_id` or `id`; message id is
  `<conversation-id>:<message-id>` (`src/engram/chatgpt_export.py:166-196`).

Claude evidence:

- Accepts zip or extracted directory; hashes `conversations.json`,
  `users.json`, `projects.json`, and `memories.json`, but Phase 1.5 ingests
  only `conversations.json` (`docs/ingestion.md:99-135`,
  `src/engram/claude_export.py:99-174`).
- Source key is the zip/directory identity path
  (`src/engram/claude_export.py:147-174`,
  `src/engram/claude_export.py:320-369`).
- Conversation key is Claude `uuid`; message key is
  `<conversation-uuid>:<message-uuid-or-index>`
  (`src/engram/claude_export.py:188-214`).

Gemini evidence:

- Accepts Google Takeout `Takeout/My Activity/Gemini Apps/MyActivity.json` and
  a direct `Gemini Apps/MyActivity.json` directory
  (`docs/ingestion.md:141-176`, `src/engram/gemini_export.py:87-130`).
- Source key is the Takeout/Gemini Apps identity path; content hash is over
  `MyActivity.json` (`src/engram/gemini_export.py:115-130`,
  `src/engram/gemini_export.py:320-369`).
- Each activity row becomes one conversation; `time` is the external id when
  present, otherwise a payload hash; user/assistant messages use
  `<conversation-id>:user` and `<conversation-id>:assistant`
  (`src/engram/gemini_export.py:143-161`,
  `src/engram/gemini_export.py:173-212`).

<a id="striatum-importer"></a>
### Striatum Bundle Importer

Striatum differs from AI conversation import:

- It validates a local disk bundle with `manifest.json` plus fixed JSONL
  streams such as `rfcs.jsonl`, `decision_log_rows.jsonl`,
  `operator_reports.jsonl`, `run_summaries.jsonl`, `audit_chain.jsonl`,
  `changelog.jsonl`, `ubiquitous_language.jsonl`,
  `harness_friction_patterns.jsonl`, and `commits.jsonl`
  (`src/engram/striatum_ingest.py:13-30`).
- It validates manifest schema version, optional `source_kinds ==
  ['striatum']`, closed sub-kind order, file metadata, row counts, and row
  `source_kind='striatum'` (`src/engram/striatum_ingest.py:107-166`,
  `src/engram/striatum_ingest.py:229-258`,
  `src/engram/striatum_ingest.py:261-268`).
- It stores rows as `captures`, not as conversations/messages, with
  `tenant_id='striatum'`, `corpus_id='striatum'`, `capture_type='reference'`,
  and `bundle_id` (`src/engram/striatum_ingest.py:271-330`,
  `src/engram/striatum_ingest.py:333-409`).
- Source key is `striatum:{repo}:bundle:{since_ref}:{bundle_id}`;
  capture key is `{repo}:{sub_kind}:{row.external_id}`
  (`src/engram/striatum_ingest.py:412-420`).
- Current ingest hard-codes `privacy_tier` to `1`; projection later copies the
  capture column tier (`src/engram/striatum_ingest.py:380-396`,
  `src/engram/striatum_projection.py:217-233`,
  `src/engram/striatum_projection.py:441-491`).

Striatum is the closest existing precedent for non-conversation local evidence:
it uses `captures` as the immutable raw lane and a separate projection layer
for retrieval.

<a id="projection-precedent"></a>
## Projection Contract Precedent

<a id="striatum-layer-1"></a>
### Implemented Striatum Layer 1

The active Striatum backlog defines Layer 1 as materializing
`striatum_references` from raw Striatum captures so retrieval no longer scans
`captures.raw_payload`; it also defines `striatum_projection_generations`,
idempotent `(capture_id, generation_id)` behavior, and tenant/corpus/privacy
carry from captures (`STRIATUM_MEMORY_E2E_BACKLOG.md:42-76`).

Migration 015 implements a narrower but concrete subset:

- `striatum_projection_generations` stores tenant/corpus, parent identity,
  bundle id, contract/schema/code versions, input manifest hash, item count,
  status, activation/supersession timestamps, embedding profile, and
  `raw_payload` (`migrations/015_striatum_projection.sql:3-49`).
- Generation idempotency is unique on tenant/corpus/bundle/schema/code/input
  hash (`migrations/015_striatum_projection.sql:51-59`).
- Only one active generation is allowed per tenant/corpus/parent
  (`migrations/015_striatum_projection.sql:61-63`).
- `striatum_references` stores a capture FK, tenant/corpus, closed `ref_kind`,
  normalized value, content hash, generation id, active flag, observed time,
  privacy tier, source sub-kind, scope, and payload
  (`migrations/015_striatum_projection.sql:72-121`).
- The parent-validation trigger requires generation tenant/corpus match,
  active references to cite an activated generation, cited captures to be
  `source_kind='striatum'`, and capture tenant/corpus match
  (`migrations/015_striatum_projection.sql:140-217`).

The worker follows generation-scoped rebuild: it loads raw captures only for
`source_kind='striatum'` inside the requested tenant/corpus, derives closed
reference kinds, computes a deterministic input manifest, reuses the active
generation when the input hash matches, inserts references idempotently, and
atomically activates a new generation while superseding old rows
(`src/engram/striatum_projection.py:58-117`,
`src/engram/striatum_projection.py:120-164`,
`src/engram/striatum_projection.py:167-240`,
`src/engram/striatum_projection.py:314-359`,
`src/engram/striatum_projection.py:386-575`).

<a id="rfc-0046-proposal-precedent"></a>
### RFC 0046 Proposal Precedent

RFC 0046 is broader than the implemented migration. It proposes that raw
Striatum evidence remains append-only, while projection rows are rebuildable
caches carrying raw capture references, V2 item identity, hashes,
privacy/redaction metadata, and derivation versions
(`docs/rfcs/0046-striatum-projection-index-schema.md:17-25`). It also states
that projection jobs are corpus-reading processes with no outbound network
(`docs/rfcs/0046-striatum-projection-index-schema.md:129-145`) and defines
generation-scoped idempotency plus active serving rules
(`docs/rfcs/0046-striatum-projection-index-schema.md:257-291`).

For generic source ingestion, the important prior-art fact is not the whole
Striatum schema. It is the local pattern already present in code: raw evidence
lands first; references/projections are rebuildable; active rows are
generation-scoped; retrieval reauthorizes against stored tenant/corpus/source
identity.

<a id="retrieval-boundary"></a>
### Retrieval And Packet Boundary

`MemoryService.search()` authorizes the requested tenant/corpus pair before
reading (`src/engram/memory.py:241-253`). Exact-reference search validates a
closed `ref_kind` vocabulary, filters active `striatum_references` by
tenant/corpus, and joins back to same-pair Striatum captures
(`src/engram/memory.py:37-61`, `src/engram/memory.py:430-507`,
`src/engram/memory.py:800-866`). `fetch_reference()` decodes an opaque
reference id, loads the stored row, and reauthorizes the row's own
tenant/corpus before returning content (`src/engram/memory.py:509-552`).

Packet audits are append-only and intentionally do not store raw memory
content. Migration 016 rejects payload-shaped keys such as `raw_payload`,
`content`, `excerpt`, `summary`, `body`, or `transcript` inside selected or
omitted audit JSON (`migrations/016_striatum_packet_audits.sql:3-72`,
`migrations/016_striatum_packet_audits.sql:74-158`,
`migrations/016_striatum_packet_audits.sql:236-250`).

<a id="no-egress"></a>
## No-Egress And Local-Only Evidence

The project-level requirement is stronger than ordinary "local files only":
corpus access and network access must remain structurally separated
(`HUMAN_REQUIREMENTS.md:123-165`). Build phases repeat local-only execution
and no outbound network as cross-cutting criteria (`BUILD_PHASES.md:393-406`).

Current code evidence is partial and path-specific:

- Segmenter calls a local LLM endpoint through `ENGRAM_IK_LLAMA_BASE_URL`,
  defaulting to `http://127.0.0.1:8081`, and rejects non-loopback hostnames
  (`src/engram/segmenter.py:23-30`, `src/engram/segmenter.py:1880-1923`).
- Embedder calls a local Ollama endpoint through `ENGRAM_OLLAMA_BASE_URL`,
  defaulting to `http://127.0.0.1:11434`, and rejects non-loopback hostnames
  (`src/engram/embedder.py:20-24`, `src/engram/embedder.py:535-568`).
- The local web surfaces display local-only/no-egress audit footer copy
  (`src/engram/web/chrome.py:12-17`), and serve CLIs refuse non-loopback binds
  (`src/engram/cli.py:2394-2415`).
- RFC 0047 forbids hosted Engram, hosted model calls, cloud embedding or
  reranking APIs, telemetry, remote cache, web search, and network-accessible
  Engram MCP (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:496-532`).
- RFC 0049 makes no-egress an explicit gate over validator, ingest,
  projection, embedding, retrieval, MCP, and context-assembly paths
  (`docs/rfcs/0049-striatum-evaluation-gates.md:404-453`).

Evidence gap for drafters: current code has loopback URL checks for local
model runtimes, but RFC 0049 distinguishes that from OS-level no-egress
sandbox proof (`docs/rfcs/0049-striatum-evaluation-gates.md:442-457`).

<a id="adjacent-rfc-coverage"></a>
## Adjacent RFC Coverage By Proposed Source

Coverage terms:

- **Covered**: adjacent RFCs or implemented code already define the relevant
  source shape for the proposed use.
- **Partly covered**: adjacent RFCs define a substrate or Striatum-specific
  variant, but concrete generic source ingestion remains new.
- **Net-new**: no concrete adjacent adapter/projection contract exists in the
  required RFC set.

| Proposed source family | Coverage | Evidence and boundary notes |
|---|---|---|
| AI conversation exports | Covered by existing code, not by RFC 0033-0036/0045-0049. | Current source scope lists ChatGPT, Claude, and Gemini as implemented (`README.md:209-222`; `SPEC.md:13-22`). |
| Generic source contract/taxonomy | Partly covered. | RFC 0045 is a Striatum-specific disk-bundle contract, with `source_kind='striatum'` and tenant/corpus limits (`docs/rfcs/0045-striatum-corpus-contract-v2.md:46-66`). The generic source contract in the design is new (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:61-99`). |
| Human chat logs, email, team chat, transcripts | Partly covered. | Conversation tables and AI importers provide shape. Source-specific privacy, edits/deletes, attachments, and extraction approval are new (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:106-131`, `docs/design/source-ingestion-expansion-proposal-2026-05-15.md:214-237`). |
| Git commit history | Partly covered. | Striatum V1 already ingests `commit` sub-kind rows (`src/engram/striatum_ingest.py:19-30`). RFC 0045 includes `commits.jsonl` and `git_diff_summaries.jsonl` streams (`docs/rfcs/0045-striatum-corpus-contract-v2.md:141-165`, `docs/rfcs/0045-striatum-corpus-contract-v2.md:341-343`). RFC 0046 proposes `striatum_git_refs` (`docs/rfcs/0046-striatum-projection-index-schema.md:616-656`). A direct `source_kind='git'` importer is net-new. |
| Build/test artifacts, coverage, benchmarks, logs | Partly covered. | RFC 0046 proposes Striatum run, agent, artifact, issue, chunk, and log-summary projections (`docs/rfcs/0046-striatum-projection-index-schema.md:548-614`, `docs/rfcs/0046-striatum-projection-index-schema.md:657-732`). Generic build artifact import remains new (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:263-282`). |
| Striatum bundles/workflow artifacts | Covered for Striatum scope. | README/SPEC describe RFC 0044 local Striatum tenant and four read-only tools (`README.md:224-232`, `SPEC.md:59-75`). Backlog says RFC 0044 Phase 1 read-only API exists and EG-000 baseline closed (`STRIATUM_MEMORY_E2E_BACKLOG.md:20-34`). RFC 0045-RFC 0049 remain proposal/reference in the RFC index (`docs/rfcs/README.md:65-69`). |
| Notes, Markdown trees, project docs | Partly covered. | `notes` exists and `source_kind='obsidian'` is reserved, but README says Obsidian/note extraction is deferred (`README.md:217-222`, `README.md:276-282`). RFC 0046 proposes Striatum document projections for RFCs, designs, reviews, syntheses, handoffs, prompts, and packets (`docs/rfcs/0046-striatum-projection-index-schema.md:511-546`). Generic Markdown/plain-text import remains new. |
| Browser, shell, app/window activity | Net-new with broad observation adjacency. | RFC 0033 names activity traces among future non-text observations (`docs/rfcs/0033-multimodal-observation-layer.md:28-43`), but no concrete adapter/projection exists. The design itself marks these as high-risk and deferred (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:297-314`). |
| Photos, videos, screenshots, OCR, EXIF | Covered conceptually, not implemented. | RFC 0034 directly covers local photo/library ingestion, raw media asset records, metadata observations, local vision, OCR, face clusters, and photo events (`docs/rfcs/0034-photo-library-ingestion.md:68-179`). It is post-V1 proposal material, not accepted implementation (`docs/rfcs/0034-photo-library-ingestion.md:251-274`). |
| Location timelines, GPX/activity tracks, place visits | Covered conceptually, not implemented. | RFC 0035 covers local location sources, immutable raw exports, derived samples, place candidates, visit intervals, timezone handling, privacy granularity, and no online reverse geocoding (`docs/rfcs/0035-location-timeline-place-model.md:72-203`). It remains proposal material (`docs/rfcs/0035-location-timeline-place-model.md:236-258`). |
| Calendar exports | Partly covered. | RFC 0035 names calendar events with local exported locations as a location source (`docs/rfcs/0035-location-timeline-place-model.md:72-87`), and RFC 0036 includes calendar events in day packets (`docs/rfcs/0036-daily-biography-compiler.md:105-119`). A calendar-specific adapter is not specified. |
| Health, finance, contacts, receipts, reservations, warranties | Partly covered to net-new. | RFC 0033 proposes a generic observation layer for multimodal/life evidence (`docs/rfcs/0033-multimodal-observation-layer.md:11-21`, `docs/rfcs/0033-multimodal-observation-layer.md:104-155`). Concrete adapters and privacy defaults are unresolved. |
| Daily biography projections | Covered conceptually, not implemented. | RFC 0036 defines day packets, evidence collection across source families, candidate episodes, gaps, summary generation, and privacy-aware rendering (`docs/rfcs/0036-daily-biography-compiler.md:68-215`). |
| Live/manual/MCP/file/audio/screenshot capture | Partly covered. | `captures` exists, reclassification/corrections-as-captures exist, and manual capture is first-class in human requirements (`migrations/001_raw_evidence.sql:85-98`, `migrations/002_capture_reclassification.sql:1`, `HUMAN_REQUIREMENTS.md:690-716`). The design's live capture sequence remains new and deferred (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:387-397`). |

<a id="striatum-boundary"></a>
## Striatum Corpus Boundary Touches

Striatum is an application-memory tenant, not a generic project-memory grant.
README states RFC 0044 adds `tenant_id='striatum'`, `corpus_id='striatum'`,
and only four read-only MCP stdio tools; default Striatum operator access has
`memory.read_striatum` and `memory.describe` only, while personal memory is
outside that boundary (`README.md:224-232`).

RFC 0045 keeps `source_kind='striatum'` as the Striatum ingest/parser
discriminator and says default Striatum operator access cannot read personal
memory or secondary corpora without explicit Engram-local capabilities
(`docs/rfcs/0045-striatum-corpus-contract-v2.md:46-66`). RFC 0047 repeats
that bundle identity, instance identity, repository identity, labels, paths,
and discovery fields are not authorization grants
(`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:534-576`).

Boundary-sensitive source families:

- Git commits and build/test artifacts overlap strongly with Striatum because
  RFC 0045/RFC 0046 already model Striatum-exported commits, diff summaries,
  runs, agents, artifacts, issues, and blockers. Direct git/build importers
  must be distinguishable from Striatum exported evidence by source kind,
  tenant/corpus, and authorization boundary.
- Project docs and Markdown trees overlap with Striatum documents where the
  docs are exported by Striatum, but ordinary project docs are not
  automatically Striatum corpus evidence.
- Human chat, email, calendars, browser/app activity, photos, location,
  health, finance, contacts, and daily biography evidence are personal/life
  memory by default. They should not become visible to Striatum default
  retrieval unless an explicit personal-memory or cross-boundary authorization
  path exists.

<a id="privacy-prior-art"></a>
## Privacy Prior Art And Concerns

Current raw tables default `privacy_tier` to 1 for conversations, messages,
captures, notes, and segments/embeddings by carry or inheritance
(`migrations/001_raw_evidence.sql:45`,
`migrations/001_raw_evidence.sql:60`,
`migrations/001_raw_evidence.sql:92`,
`migrations/002_capture_reclassification.sql:2-3`,
`migrations/004_segments_embeddings.sql:46-74`). Human requirements define
Tier 1 through Tier 5 and explicitly say category defaults need a decision;
health, finances, and beliefs default to Tier 1 with explicit promotion only
(`HUMAN_REQUIREMENTS.md:607-616`).

Privacy reclassification is itself raw evidence. D023 adds
`capture_type='reclassification'` so tier promotion/redaction requests are new
captures, not raw-row updates (`DECISION_LOG.md:45`,
`migrations/002_capture_reclassification.sql:1`). Segment invalidation code
then finds reclassification captures and invalidates affected parent segments
(`src/engram/segmenter.py:1701-1769`).

Source-family privacy observations:

- Human communications introduce third-party data, edits/deletes, duplicated
  exports, and attachments. The source design says human communications should
  require source-specific approval before claim extraction and attachment
  bodies should be metadata-first unless explicitly opted in
  (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:123-131`,
  `docs/design/source-ingestion-expansion-proposal-2026-05-15.md:232-237`).
- Git and build artifacts look low-risk when project-selected, but patch
  bodies, long logs, stack traces, stdout/stderr, absolute paths, dirty working
  trees, and secrets are recurring privacy edges
  (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:246-282`,
  `docs/rfcs/0046-striatum-projection-index-schema.md:643-656`).
- Notes/project docs split sharply between project Tier 1 material and
  personal vault/journal material that the design marks Tier 2+ by default
  (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:284-295`).
- Browser, shell, app/window activity reveal attention and behavior at high
  granularity; the design sets them Tier 3 by default and says not to start
  with continuous live capture
  (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:297-314`).
- Photos/media include biometric face embeddings and clusters; RFC 0034 says
  face embeddings/clusters default to Tier 1 and forbids hosted vision/OCR/face
  recognition (`docs/rfcs/0034-photo-library-ingestion.md:149-179`,
  `docs/rfcs/0034-photo-library-ingestion.md:251-259`).
- Location exact coordinates are sensitive; RFC 0035 says no online reverse
  geocoding and default context should generally surface coarser location
  (`docs/rfcs/0035-location-timeline-place-model.md:72-87`,
  `docs/rfcs/0035-location-timeline-place-model.md:179-203`).
- Daily packets must not leak exact coordinates, face clusters, OCR, health,
  or finance through summaries simply because those inputs helped compile the
  day (`docs/rfcs/0036-daily-biography-compiler.md:196-215`).

Notable tension for drafters: the source-ingestion proposal says
`privacy_default: 1` for the sample git contract, Tier 1 for selected project
repos, Tier 3 for browser/app activity, and Tier 3+ for location/health/
finance/contacts/raw media
(`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:79`,
`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:252-254`,
`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:309`,
`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:330-331`).
Human requirements say health, finances, and beliefs default Tier 1 with
explicit promotion only (`HUMAN_REQUIREMENTS.md:615-616`). That is an
unresolved policy mismatch, not an implementation detail.

<a id="net-new-work-surface"></a>
## Net-New Work Surface

These source-expansion items have no concrete current importer/projection
contract in the required prior art:

- Generic source contract template outside Striatum.
- Direct `source_kind='git'` importer for local repositories.
- Direct `source_kind='build_artifact'` importer for JUnit, coverage,
  benchmark, and log directories.
- Generic Markdown/plain-text tree importer for selected project docs and
  notes.
- Human-chat/email importers beyond AI conversation exports.
- Browser/shell/app activity adapters.
- Calendar-specific importer.
- Health, finance, contacts, receipts, travel records, warranties, home
  inventory, genealogy, reading/media, and government-record adapters.
- Live watcher/audio/screenshot capture policy and implementation.

The design's initial deliverable recommendation explicitly places source
contract, git metadata/diff stats, build artifacts, and project-event
projection before human chat and life-record sources
(`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:445-463`).

<a id="open-questions"></a>
## Questions For Drafters And Reviewers

1. Should generic source expansion keep using the PostgreSQL enum with
   deliberate `ALTER TYPE` migrations, or introduce a source registry before
   broad importer work? The current enum is closed
   (`migrations/001_raw_evidence.sql:4-9`), and the design names the enum as
   an expansion limitation
   (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:56-59`,
   `docs/design/source-ingestion-expansion-proposal-2026-05-15.md:413-414`).

2. Which raw lane owns each early project source: specialized tables, `notes`,
   `captures`, or a new typed raw table? Current precedent is conversations
   for threaded AI exports and captures for Striatum rows
   (`src/engram/striatum_ingest.py:380-396`).

3. What is the exact identity contract for direct git import so it does not
   collide with Striatum-exported `commit` and `git_diff_summary` evidence?
   RFC 0045/0046 already define Striatum commit-related streams and reference
   kinds (`docs/rfcs/0045-striatum-corpus-contract-v2.md:141-165`,
   `docs/rfcs/0046-striatum-projection-index-schema.md:616-656`).

4. Are patch bodies retained as raw evidence by default, metadata plus diff
   stats only, or opt-in full body capture? The design leaves this open
   (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:465-466`).

5. Should build logs be copied into a managed content-addressed local store or
   referenced by path/hash? The design leaves this open
   (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:467-468`).

6. How should raw-output sources prevent secret/path leakage before projection
   and packet audit? RFC 0048 forbids whole transcripts, raw logs, raw model
   output, and broad logs as automatic injection
   (`docs/rfcs/0048-striatum-context-injection-policy.md:686-688`), while
   migration 016 forbids payload-shaped audit content
   (`migrations/016_striatum_packet_audits.sql:74-158`).

7. How will default privacy tiers be reconciled for health, finance, contacts,
   location, raw media, and personal notes? Human requirements and the source
   proposal currently use different default-tier framing
   (`HUMAN_REQUIREMENTS.md:607-616`,
   `docs/design/source-ingestion-expansion-proposal-2026-05-15.md:330-331`).

8. What approval gate blocks human chat/email extraction, and does that gate
   apply to work chats and exported issue/PR comments that include third-party
   text? The design says human communications need source-specific approval
   before claim extraction
   (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:123-131`).

9. Does the generic source contract inherit RFC 0046-style generation-scoped
   projections, or only source-specific tests for idempotency, conflict, and
   rebuildability? Current implemented Striatum Layer 1 provides a small
   concrete precedent (`migrations/015_striatum_projection.sql:3-139`).

10. What evidence is required before claiming "no network access" for new
    importers and derived stages? Current code has loopback checks for local
    model runtimes, but RFC 0049 separates that from OS-level no-egress probe
    evidence (`src/engram/segmenter.py:1918-1923`,
    `src/engram/embedder.py:563-568`,
    `docs/rfcs/0049-striatum-evaluation-gates.md:404-457`).

11. Should `docs/schema/README.md` be treated as current for migration 015/016
    research? It documents tenant/corpus fields on raw tables
    (`docs/schema/README.md:562-579`, `docs/schema/README.md:1007-1020`), but
    current project context says generated schema docs may not yet be refreshed
    for recent Striatum layers (`docs/AGENT_CONTEXT_NOTES.md:146-154`).

12. Which local export format is the first non-AI chat adapter? The design
    leaves that open and names mbox, Maildir, Slack export JSON, Discord JSON,
    and Matrix JSON as candidates
    (`docs/design/source-ingestion-expansion-proposal-2026-05-15.md:377-385`,
    `docs/design/source-ingestion-expansion-proposal-2026-05-15.md:473-475`).

13. Where is the boundary between Engram and a password/document vault?
    Human requirements say this remains open and likely means Engram references
    documents/secrets rather than storing the secret itself
    (`HUMAN_REQUIREMENTS.md:720-724`).

<a id="citation-index"></a>
## Citation Index

- `docs/design/source-ingestion-expansion-proposal-2026-05-15.md`
- `docs/ingestion.md`
- `docs/rfcs/0033-multimodal-observation-layer.md`
- `docs/rfcs/0034-photo-library-ingestion.md`
- `docs/rfcs/0035-location-timeline-place-model.md`
- `docs/rfcs/0036-daily-biography-compiler.md`
- `docs/rfcs/0045-striatum-corpus-contract-v2.md`
- `docs/rfcs/0046-striatum-projection-index-schema.md`
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md`
- `docs/rfcs/0048-striatum-context-injection-policy.md`
- `docs/rfcs/0049-striatum-evaluation-gates.md`
- `migrations/001_raw_evidence.sql`
- `migrations/002_capture_reclassification.sql`
- `migrations/003_source_kind_claude.sql`
- `migrations/004_source_kind_gemini.sql`
- `migrations/005_source_kind_gemini.sql`
- `migrations/014_striatum_tenant_corpus.sql`
- `migrations/015_striatum_projection.sql`
- `migrations/016_striatum_packet_audits.sql`
- `src/engram/chatgpt_export.py`
- `src/engram/claude_export.py`
- `src/engram/gemini_export.py`
- `src/engram/striatum_ingest.py`
- `src/engram/striatum_projection.py`
- `src/engram/memory.py`
- `src/engram/segmenter.py`
- `src/engram/embedder.py`
- `README.md`
- `SPEC.md`
- `HUMAN_REQUIREMENTS.md`
- `BUILD_PHASES.md`
- `STRIATUM_MEMORY_E2E_BACKLOG.md`
- `docs/AGENT_CONTEXT_NOTES.md`
- `docs/schema/README.md`
