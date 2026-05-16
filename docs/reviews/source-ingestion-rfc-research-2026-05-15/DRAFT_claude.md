# DRAFT — RFC 0050: Source Ingestion Expansion And Source Contract

> Authoring lane: **claude** (source-ingestion-rfc-research-2026-05-15).
> This is a proposal-grade draft, not an accepted architecture decision and
> not the final RFC file. A synthesizer will reconcile this with the codex
> and gemini drafts. Do not promote, do not edit `DECISION_LOG.md`, do not
> edit the RFC index.

<a id="rfc-0050"></a>

# RFC 0050: Source Ingestion Expansion And Source Contract

| Field | Value |
|-------|-------|
| RFC | RFC-0050 |
| Title | Source Ingestion Expansion And Source Contract |
| Status | proposal |
| Implementation | none |
| Created | 2026-05-15 |
| Source design | [`docs/design/source-ingestion-expansion-proposal-2026-05-15.md`](../../design/source-ingestion-expansion-proposal-2026-05-15.md) |
| Authoring lane | claude (multi-agent research workflow) |
| Context | `HUMAN_REQUIREMENTS.md`, `SPEC.md`, `BUILD_PHASES.md`, `ROADMAP.md`, `docs/schema/README.md`, `docs/ingestion.md`, RFC 0033, RFC 0034, RFC 0035, RFC 0036, RFC 0044, RFC 0045, RFC 0046, RFC 0047, RFC 0048, RFC 0049, `STRIATUM_MEMORY_E2E_BACKLOG.md` |

## 1. Summary

This RFC proposes the next stable structure for how Engram ingests new source
families. It introduces a **source contract template** that every adapter must
answer before importer code is written, a small closed **projection-family
vocabulary** that keeps retrieval/privacy/evaluation invariants enforceable as
new sources land, default **privacy tiers** per source family, a **rollout
order** that prioritizes high-signal/low-egress-risk local evidence first, a
**minimum evaluation gate set** per source family, and explicit deferrals.

It is a process and schema-direction RFC. It does not implement any importer,
does not add new `source_kind` enum values, and does not migrate the schema.
Each importer slice that follows will be its own RFC and migration sequence.

The proposal preserves Engram's load-bearing constraint: no cloud dependency,
no user data leaving the machine unless explicitly requested. It also
preserves raw-evidence immutability, rebuildable projections, and
provenance/confidence/auditability across every new source family.

## 2. Context

### 2.1 Why this matters now

Phase 1 / Phase 1.5 closed the raw-evidence layer with three AI-conversation
sources (ChatGPT, Claude, Gemini) plus the RFC 0044 Striatum disk bundle. The
schema is stable, segmentation and embedding ran across the AI-conversation
corpus, claim and belief consolidation produced a primary run, and the
Striatum-memory pipeline now has Layer 1-5 working code on master per
[`STRIATUM_MEMORY_E2E_BACKLOG.md`](../../../STRIATUM_MEMORY_E2E_BACKLOG.md).

`HUMAN_REQUIREMENTS.md` is explicit that V1 is a validation phase, not an end
state. The long-arc scope is a complete time-indexed biography, which requires
ingesting far more than AI conversation exports: chat logs, commit history,
build artifacts, project notes, document trees, calendar, location, media,
health, finance, activity, and life records. The current ingestion path
cannot grow into that scope by adding `source_kind` enum values one importer
at a time without inventing privacy, projection, and extraction rules per
adapter.

The design document at
[`docs/design/source-ingestion-expansion-proposal-2026-05-15.md`](../../design/source-ingestion-expansion-proposal-2026-05-15.md)
proposes the four-question contract, four evidence lanes
(conversation / document / project-execution / observation-and-life), a
sequenced rollout starting with project sources (git + build artifacts) and
project notes, and an explicit schema direction that keeps generic captures
as a landing zone while typed projections own retrieval, privacy, and
evaluation.

This RFC turns that design proposal into a reviewable, citable structure that
later importer RFCs can target without re-litigating contract shape on every
pass.

### 2.2 What the current schema already supports

Today's raw evidence layer (per [`docs/schema/README.md`](../../schema/README.md))
already encodes the right shape:

- `sources` with `source_kind`, `external_id`, `filesystem_path`,
  `content_hash`, `raw_payload`, `tenant_id`, `corpus_id`, `bundle_id`.
- `conversations` / `messages` for threaded chat-shaped evidence.
- `notes` for document-shaped evidence (still unpopulated for non-AI sources).
- `captures` as a generic landing zone with `capture_type` vocabulary
  (`observation`, `task`, `idea`, `reference`, `person_note`,
  `user_correction`, `reclassification` per D023).
- `privacy_tier` carried on raw rows and on retrieval-visible derived units
  (segments, beliefs) per D019 / D032.
- `tenant_id` / `corpus_id` for local application-memory isolation (the
  Striatum tenant uses this; future application-memory tenants will too).
- Append-only triggers on raw tables (P4 / D002).
- The Striatum-side projection scaffold from migration `015` and
  `016_striatum_packet_audits.sql`, which is the live example of a typed
  projection family layered over generic captures.

### 2.3 The practical limitation

`source_kind` is a closed Postgres `ENUM`. Migrations `003`, `004` (twice;
filename-stability artifact), `005`, and `014` extended it one value at a
time. That worked for the AI-conversation set, and it can keep working for
the next few importers, but two real costs are already visible:

1. **Per-adapter invention.** Each new importer currently invents its own
   privacy default, its own extraction posture, its own dedup keys, and its
   own re-import semantics. The Claude/Gemini importers happen to agree on
   most of that with the ChatGPT importer because the same engineer/agent
   wrote them. Git, build artifacts, Obsidian, mbox, and Maildir adapters
   will not agree by accident.
2. **No contract gate.** There is no place in the codebase where a reviewer
   can read "here is what every adapter must declare." That gap is the
   structural reason adversarial review keeps surfacing the same questions
   on every new source family (privacy defaults, third-party data, raw
   retention, network policy, projection shape).

The fix this RFC proposes is **not** an immediate schema rewrite. It is a
documented contract template plus importer test conventions, with the
schema direction queued for the medium term once enum churn or projection
divergence becomes a real migration burden.

## 3. Source Contract Template

Every new source adapter must answer **four required questions** before
code is written. The answers land as a YAML contract document in the
repository at `docs/source-contracts/<source_kind>.yaml`, alongside the
importer module that implements it.

### 3.1 The four required questions

These are the questions the design doc names. Each is a contract gate:

1. **What is the immutable raw evidence boundary?** What artifact, file,
   directory, object database, or export bundle is the canonical raw
   evidence? Where does that artifact live, how is its identity stable, and
   what does "the same evidence" mean for re-import?
2. **What normalized projection is safe and useful to derive from it?**
   Which closed projection family applies (see § 4)? Which fields are
   projected? Which fields stay only in `raw_payload`?
3. **Which downstream systems may see the projection by default?** What
   `privacy_tier` does the adapter set on raw rows and on derived
   projections? What is the default extraction posture (default-on,
   metadata-only, opt-in)? Which retrieval surfaces (MCP search, packet
   builder, context_for) may see the projection at the default tier?
4. **What provenance, privacy, confidence, and rebuild rules protect it?**
   Which fields constitute the provenance chain back to raw evidence? Which
   confidence is asserted on which derivations? Which rebuild operations
   are deterministic, and which require recompute under a new derivation
   version?

An adapter that cannot answer all four does not pass review.

### 3.2 Mandatory contract fields

The YAML contract MUST include at least these fields. They mirror the
shape in § Proposed Source Contract of the design document and align with
the existing Striatum corpus contract semantics in RFC 0045.

```yaml
source_kind: <closed identifier, e.g. git, build_artifact, obsidian, mbox>
sub_kinds:
  - <closed list per source_kind, e.g. commit, branch, tag, diff_stat>
raw_artifact_boundary:
  description: <one-line: what is the canonical immutable artifact>
  acquisition:
    - <local filesystem | explicit local export | user-provided copy>
  network_policy: no outbound calls
identity_keys:
  - <fields that determine deduplication; e.g. repository_root_hash, commit_sha>
temporal_fields:
  observed_at: <which source field maps to observed_at>
  recorded_at: <typically import_time>
  edited_at: <optional; for sources with edit history>
privacy_default: <integer tier; see § 5 defaults>
projection_families:
  - <closed values from § 4>
extraction_eligibility:
  default: <off | metadata_only | text_first | full>
  opt_in_required: <true | false>
raw_retention:
  policy: <reference-only | content-hashed-store | inline-raw_payload>
  attachments_policy: <metadata-first | reference-only | opt-in-text-extraction>
tenant_id_default: <personal | striatum | future-local-application>
corpus_id_default: <personal | <named local corpus>>
contract_tests:
  - idempotent_reimport
  - hash_conflict_raises
  - projection_rebuild_from_raw
  - no_network_access
  - privacy_tier_inheritance
  - extraction_off_by_default_for_third_party_data  # where applicable
```

### 3.3 How the contract is enforced

The contract is enforced by importer tests, not by a runtime registry on
day one. Each adapter ships a `tests/test_<source_kind>_contract.py` (or
adds its cases to a shared parametrized test) that asserts the contract's
core invariants directly against the importer behavior:

- **Idempotent re-import.** Importing the same artifact twice with the
  same content produces no new raw rows and no new projection rows. The
  shape mirrors `tests/test_chatgpt_export.py`, `tests/test_claude_export.py`,
  `tests/test_gemini_export.py`, and `tests/test_striatum_ingest.py` today.
- **Hash conflict raises.** Re-importing the same `external_id` with a
  different content hash raises `IngestConflict` rather than overwriting.
- **Projection rebuild from raw.** Dropping the derived projection rows
  and running `engram phase-projection run --tenant <t> --corpus <c>`
  reproduces structurally equivalent projection rows (RFC 0046-style
  activation invariant; equivalent to the Striatum projection contract
  in migration `015`).
- **No network access.** A test that monkeypatches the importer's HTTP
  client to fail loud asserts the importer never reaches it. For Python,
  this is a `socket.socket` patch or a fixture that runs the importer
  with `ENGRAM_DENY_NETWORK=1` and asserts no outbound calls.
- **Privacy tier inheritance.** Derived rows (segments, projections,
  packet items) inherit the raw row's `privacy_tier` and never relax it.
- **Extraction-off-by-default for third-party data.** Where the source
  contains messages from people other than the operator (chat exports,
  email, meeting transcripts, message attachments), the importer ships
  with claim extraction disabled by default and a documented
  per-source-family opt-in switch.

A future runtime registry (`source_contracts` table or manifest column on
`sources`) is queued for the medium term in § 11.3. It is not required
for the first importer slices, because each adapter test suite already
pins the invariants.

## 4. Projection Families (Closed Vocabulary)

Projection families are the typed lanes that retrieval, privacy gates,
and evaluation gates can rely on. The vocabulary is **closed**. Adding a
new family requires its own RFC. Each new source adapter declares one or
more existing projection families; if no family fits, that is a signal
the vocabulary needs a deliberate extension, not a quiet expansion.

The proposed initial vocabulary, derived from the design doc's four
evidence lanes and the existing Striatum-side projection example:

| Family | Lane | Typical raw evidence | Typical projection rows |
|--------|------|----------------------|-------------------------|
| `conversation_event` | conversation | `messages`, mbox, Maildir, Slack/Discord/Matrix exports, IRC logs | conversation, message, participant, attachment metadata, thread link, reply edge |
| `document_chunk` | document/note | Obsidian vault, Markdown trees, PDFs, text exports | document record, content hash, title, frontmatter, links, headings, chunks, path refs |
| `project_event` | project/execution | git history, GitHub/GitLab issue exports, Striatum bundle items | project event (commit/PR/issue), parent edges, changed paths, run id refs, RFC/decision/issue refs |
| `code_reference` | project/execution | git, build manifests, source trees | path ref, line/window ref, file content hash, repository root id |
| `artifact_reference` | project/execution | build/test/benchmark/coverage artifacts, log files, Striatum reports | run summary, suite summary, failure signature, coverage summary, benchmark measurement, produced-file ref |
| `observation_metadata` | observation/life | EXIF, location samples, calendar events, health samples, activity samples, browser/shell history exports | metadata observation, interval, asset, place candidate, event candidate, coverage gap |

Two invariants apply to every projection family without exception:

1. **Projection rows are caches over raw evidence.** Dropping all
   projection rows for a family and rebuilding from raw evidence
   reproduces structurally equivalent rows. No projection row is ground
   truth; the raw row is.
2. **Privacy and provenance inherit from raw.** Each projection row
   carries the same `tenant_id`, `corpus_id`, and `privacy_tier` as its
   parent raw row (or stricter, never weaker), plus a `generation_id`,
   `derivation_version`, and a back-reference to the raw row(s) it was
   derived from. The Striatum projection in migration `015`
   (`striatum_references`, `striatum_projection_generations`) is the
   reference implementation.

Two families that are deliberately **out of scope** for this vocabulary:

- `generated_product` (a derived memory product such as a synthesized
  daily brief or a summary packet). The AL-D004 generated-product
  contract in `STRIATUM_MEMORY_E2E_BACKLOG.md` is the home for that. It
  must not become a projection family until that contract lands.
- `belief_projection`. Beliefs already have their own pipeline; the
  source contract does not authorize a new path that bypasses claims.

## 5. Privacy Defaults

Privacy defaults are **per source family**, not per source adapter. New
adapters in a family inherit the family's default unless they declare
stricter (never weaker) defaults in their contract. The default values
below align with `HUMAN_REQUIREMENTS.md` § Privacy & access tiers and
with the D019 carry-or-inherit rule.

| Source family | Default `privacy_tier` (raw) | Default extraction posture | Notes |
|---------------|------------------------------|----------------------------|-------|
| AI conversation exports (ChatGPT, Claude, Gemini) | 1 | default-on (today's behavior) | Existing behavior, unchanged. |
| Project notes / markdown trees (Obsidian, READMEs, RFCs, design docs) | 1 | default-on segmentation; extraction default-on for project docs | Project docs are first-party authored. |
| Personal journals / private notes | 2 | opt-in extraction per vault | Even on a personal machine, journals are not project artifacts. |
| Git history (project repos the operator explicitly enrolls) | 1 | metadata + commit message default-on; patch bodies opt-in | Diff stats yes, patch bodies no. |
| Build / test / benchmark / coverage artifacts | 1 | summary projections default-on; raw logs reference-only | Long logs never enter context packets by default. |
| Striatum bundle | per RFC 0044 | per RFC 0044 / RFC 0048 | Unchanged. |
| Exported email (mbox, Maildir, Apple Mail) | 2 | metadata-only default; text extraction opt-in per account | Third-party data inside. |
| Exported team chat (Slack, Discord, Matrix, IRC) | 2 | metadata-only default; extraction opt-in per workspace | Third-party participants. |
| Exported personal messaging (iMessage, SMS, Signal, WhatsApp, Telegram) | 3 | metadata-only default; extraction blocked until § 5.2 gate | Highest third-party sensitivity. |
| Meeting transcripts, voice transcription | 2-3 | opt-in extraction per source | Depends on whether the operator was the only speaker. |
| Calendar / contacts / reminders | 2 | metadata-only default | Contains other people's details. |
| Photo libraries, EXIF, OCR | 3 | per RFC 0034 | Defer to RFC 0034 / RFC 0033. |
| Location timeline / GPX / activity | 3 | per RFC 0035 | Defer to RFC 0035. |
| Health, biometrics, lab panels | 3 | manual capture only | Highest-stakes category per HUMAN_REQUIREMENTS. |
| Finance, receipts, tax records | 3 | manual capture only | Highest-stakes category. |
| Browser / shell / app activity | 3 | deferred per § 6 | Reveals attention/behavior at swamp scale. |

Two privacy invariants apply across every family:

### 5.1 No-egress invariant

Every corpus-reading process (importer, projection worker, retrieval
worker, packet builder, MCP server) MUST run with no outbound network
calls. This is the D020 / HUMAN_REQUIREMENTS § "Why corpus access and
network egress are kept separate" rule. The source contract test for
`no_network_access` is a per-adapter restatement of the same invariant.

### 5.2 No-derived-product-leak invariant

A derived projection MAY NOT exit the machine, even when the
corresponding raw evidence has a sharing carve-out, unless the operator
explicitly requests that export. Derived rows are projections of the
raw evidence; the same hostage-situation logic in HUMAN_REQUIREMENTS
applies to them. Sharing a derived product through an MCP tool that
hits the network, an automatic backup, or a third-party assistant
context is disqualifying. This is the structural reason the AL-D004
generated-product contract is required before any `generated_product`
family is added.

### 5.3 Third-party-data extraction gate

Sources that contain messages, transcripts, attachments, or records
from people other than the operator default to extraction-off. They
require an explicit `--enable-extraction` opt-in (or equivalent
contract field) plus a third-party-data acknowledgment recorded in the
adapter's contract YAML. The extraction-eligibility flag MUST be
visible in the importer CLI help and in `engram describe-corpus`
output, so the operator can see at a glance which sources are
extraction-on.

## 6. Rollout Order

The rollout sequence below is the design doc's Implementation Sequence,
restated as RFC steps with explicit success criteria per stage. Steps
are sequential. Each step lands as its own importer RFC and migration
sequence (one `00NN_source_kind_<name>.sql` per adapter).

### Step 0 — Source contract and projection vocabulary (this RFC)

Land the contract template at `docs/source-contracts/TEMPLATE.yaml`,
the closed projection-family vocabulary at
`docs/source-contracts/projection-families.md`, and the contract test
conventions documented above. No `source_kind` enum changes. No
schema migrations. No code changes beyond test helpers.

Success criteria:

- Contract template merged.
- Projection-family vocabulary merged.
- Reviewers can cite this RFC when reviewing future importer slices.

### Step 1 — Project sources (highest signal, lowest egress risk)

Two adapters in priority order:

1. **`source_kind='git'`** — local git history importer.
   - Raw evidence: repository root content identity + commit SHA +
     adapter manifest.
   - Projection families: `project_event`, `code_reference`.
   - Privacy default: tier 1 for enrolled repos.
   - Extraction: metadata + commit message default-on; patch bodies opt-in.
   - First milestone retrieval: exact-reference by commit SHA, by path,
     by RFC/decision/issue mention.
2. **`source_kind='build_artifact'`** — local directory importer for
   JUnit XML, pytest reports, coverage JSON/XML, benchmark JSON,
   plain logs, and Striatum reports already on disk.
   - Raw evidence: artifact directory + per-file content hash + parser
     version.
   - Projection family: `artifact_reference`.
   - Privacy default: tier 1, inherits from project/repo source if
     more restrictive.
   - Extraction: summary projections default-on; raw logs
     reference-only and never enter context packets by default.

Step 1 success criteria:

- Both adapters pass the contract test suite (§ 3.3).
- A small `project_events` (or equivalent) projection answers:
  "what changed around this date", "which commits touched this file",
  "what build/test evidence followed this commit", "what
  issue/RFC/decision does this commit cite".
- The retrieval surface returns commit SHAs, file paths, and run ids
  as exact references; no patch bodies or long logs in context by
  default.
- All importer/projection tests run with `ENGRAM_DENY_NETWORK=1` (or
  equivalent) without retries.

### Step 2 — Project notes and Markdown trees

`source_kind='obsidian'` (already in the `source_kind` enum slot
reserved at `001_raw_evidence.sql`) and equivalent generic
`markdown_tree` adapter for non-Obsidian Markdown directories.

- Raw evidence: file content hash + path snapshot at import time.
- Projection family: `document_chunk`.
- Privacy default: tier 1 for project docs; tier 2 for personal
  vaults until an explicit promotion capture lands.
- Extraction: default-on segmentation; default-on extraction for
  project docs; opt-in for personal journals.

Step 2 success criteria:

- Obsidian vault and a generic Markdown directory both ingest with
  the same projection family.
- Document chunks are retrievable by exact path, by content hash, and
  by lexical match.
- Reclassification capture (D023) demotes a vault from tier 1 to
  tier 2 without rewriting raw rows.

### Step 3 — Exported communication logs

Local exports, never live account access. Start with the formats that
are plain files on disk and that have widely available export tooling
the operator already controls: mbox, Maildir, Apple Mail export, Slack
JSON export, Discord JSON export, Matrix JSON export.

- Raw evidence: export file or local database copy + import manifest.
- Projection family: `conversation_event`.
- Privacy default: per § 5 table (email tier 2; team chat tier 2;
  personal messaging tier 3).
- Extraction: off by default. Opt-in per source family with a
  documented third-party-data acknowledgment.

Step 3 success criteria:

- At least one email adapter (mbox) and at least one team-chat
  adapter (Slack JSON or Matrix JSON) pass the contract test suite.
- Both adapters refuse to run extraction without `--enable-extraction`.
- Both adapters dedupe correctly across multi-device exports
  (same conversation imported from laptop + phone export).

### Step 4 — Life and observation sources

Defer to RFC 0033 (multimodal observation layer), RFC 0034 (photo
library), RFC 0035 (location timeline), and RFC 0036 (daily biography
compiler). Those RFCs already propose the projection shapes for the
`observation_metadata` family; this RFC names them as the design
references for Step 4 and explicitly defers detailed source-by-source
contracts to the implementation slices that follow their
acceptance/promotion.

Step 4 success criteria (per source family within the step):

- Privacy defaults match § 5.
- Projection rows are rebuildable from raw evidence.
- The daily biography compiler (RFC 0036) can answer a sample
  "this day N years ago" query without retrieving raw evidence at a
  tier above the operator's default authorization.

### Step 5 — Live capture

Only after Step 4 backfill adapters are reliable should Engram add
live capture: manual capture (already partially present via the
MCP capture path), local watcher-based file capture, and optional
local audio/screenshot capture. Live capture is always explicit,
visible, and locally disabled by default per the
HUMAN_REQUIREMENTS § "Capabilities are per-task, not blanket" rule.

Step 5 success criteria:

- Live capture cannot enter the corpus without an explicit operator
  enable for the capture surface in question.
- Every live-captured row carries the same provenance and privacy
  metadata as backfill rows from the same source family.

## 7. Evaluation Gates

Every new source adapter ships with a **minimum gate set**. The gates
borrow shape from RFC 0049 (Striatum evaluation gates) but specialize
to source-family invariants. The gate set is intentionally small;
adapters that need more gates may add them, but every adapter must at
least clear the minimum.

### 7.1 Minimum gate set (applies to every source family)

| Gate | What it asserts |
|------|-----------------|
| `EG-S00 local-only acquisition` | The importer reads only local files or explicitly user-provided local exports. No outbound calls. Equivalent to the RFC 0049 no-egress evidence shape. |
| `EG-S01 idempotent re-import` | Re-importing the same artifact with the same content produces zero new raw rows and zero new projection rows. |
| `EG-S02 conflict detection` | Re-importing the same `external_id` with a different content hash raises `IngestConflict`. |
| `EG-S03 raw evidence immutability` | Attempting `UPDATE` or `DELETE` on a raw row raises the existing trigger. The adapter never bypasses this. |
| `EG-S04 projection rebuild from raw` | Truncating projection rows for the source's projection families and rerunning the projection worker produces structurally equivalent rows under the active generation. |
| `EG-S05 privacy tier inheritance` | Projection rows carry the raw row's `privacy_tier`. Packet items and context items never include a row above the caller's authorization. |
| `EG-S06 attachment/blob retention policy` | The adapter retains attachments per its contract (`metadata-first` / `reference-only` / `opt-in-text-extraction`). The gate asserts no attachment body leaks into a default-on projection when the contract says `metadata-first`. |
| `EG-S07 extraction opt-in for third-party data` | Where the contract sets `extraction_eligibility.default != default-on`, running the extractor without `--enable-extraction` produces zero claim rows for that source family. |
| `EG-S08 packet citation back to raw` | Any packet item produced from a projection row in this source family cites the raw evidence id (`message_id`, `capture_id`, `commit_sha`, `path`, `run_id`) the projection derived from. |

### 7.2 Per-source-family specializations

Three concrete examples drawn directly from the design document's
"For git and build artifacts" gate list. Other source families add
their own equivalents.

For `source_kind='git'`:

- `EG-S10 commit-event dedup` — the same repository imported twice
  produces no duplicate commit events.
- `EG-S11 rewritten-history representation` — rewritten history is
  represented as new evidence under a new manifest; the prior
  evidence remains immutable.
- `EG-S12 patch-body-not-in-packet-by-default` — patch bodies do not
  enter context packets unless the operator passes an explicit
  inclusion flag.

For `source_kind='build_artifact'`:

- `EG-S20 build-to-commit linkage` — a build run links to a commit
  SHA when the run's artifact manifest carries one.
- `EG-S21 long-log-not-in-packet-by-default` — raw logs do not enter
  context packets; failure signatures cite the log artifact and
  line/window reference instead.

For `source_kind in {'mbox','slack_export','matrix_export', ...}`:

- `EG-S30 third-party-data extraction blocked by default` — running
  `engram pipeline` against an importer of this family without
  `--enable-extraction` produces zero new claims.
- `EG-S31 multi-device dedup` — the same conversation present in two
  exports from different devices results in one conversation row,
  one set of messages, and idempotent re-import.

### 7.3 How gates land

The minimum gate set lands as `tests/test_source_contract_gates.py`
parametrized over registered adapters. Per-family specializations land
in `tests/test_<source_kind>_gates.py`. A new top-level Make target,
`make source-gates`, prints a per-gate pass/fail summary (mirror of
`make eval-gates` from `STRIATUM_MEMORY_E2E_BACKLOG.md` Layer 4).

## 8. Scope Kept Out (Explicit Deferrals)

These are out of scope for this RFC and for the first three rollout
steps. Each is named here so a later proposal cannot quietly slip them
in under "source ingestion expansion."

- **Media bodies (image, video, audio).** Image / video / audio
  *content* (not metadata) is deferred to RFC 0033 / RFC 0034 and
  Step 4. The first source-ingestion expansion must not push image,
  video, or audio bodies into any retrieval-visible projection.
- **Cloud APIs of any shape.** No Gmail IMAP, no Slack API, no
  GitHub/GitLab API, no Apple/Google account access, no Plaid, no
  cloud calendar, no hosted vision API, no remote embedding service,
  no remote LLM. Every adapter starts from local exports or local
  filesystem state. Per HUMAN_REQUIREMENTS § Why local-first is
  load-bearing.
- **Derived memory products.** Synthesized daily briefs, summaries,
  packet exports, wiki pages, and any other generated-product family
  are out of scope until the AL-D004 generated-product contract lands
  per `STRIATUM_MEMORY_E2E_BACKLOG.md`. Until then, retrieval surfaces
  cite raw rows or rebuildable projection rows; they do not surface
  synthesized text as if it were evidence.
- **Personal-memory paste-through.** The operator cannot paste an
  arbitrary text blob into a packet and have it inherit packet
  authority. Per the AL-N015 fixture proposal in
  [`docs/reviews/striatum-memory-rfc-alignment-2026-05-14/FINDINGS_LEDGER.md`](../striatum-memory-rfc-alignment-2026-05-14/FINDINGS_LEDGER.md),
  paste-through stays as a manual capture row, not as a packet-shaped
  authority.
- **Live continuous capture.** Live capture is Step 5 and is gated on
  Steps 1-4. Continuous surveillance capture (screen, mic) is out of
  scope until an explicit RFC argues for it. Backfill from explicit
  local exports is the only path until then.
- **Cross-tenant projection coupling.** A projection in one
  application-memory tenant (`personal`) may not reach into another
  application-memory tenant (`striatum`) without explicit Engram-local
  capabilities. The existing tenant/corpus boundary in RFC 0044 holds.
- **Replacing the closed `source_kind` enum.** This RFC does not
  replace the enum. It declares the medium-term schema direction in
  § 11.3 but does not migrate.
- **Bidirectional sync back to source systems.** Engram is a read-only
  consumer of its sources; mutating Obsidian, git, or any source from
  Engram code is out of scope. Belief review writes new captures
  rather than mutating sources, per D017.

## 9. Open Questions

These are the named open questions for human decision. They are not the
full list of design tradeoffs; they are the items where this RFC
deliberately declines to choose without operator input.

1. **Patch body retention.** Should `source_kind='git'` retain patch
   bodies in raw evidence by default, or only commit metadata plus
   diff stats with patch bodies opt-in per-repo? The design doc
   recommends opt-in. The trade-off: retaining patch bodies preserves
   evidence for future model generations (per the
   HUMAN_REQUIREMENTS "corpus survives the model" rule) at the cost
   of larger raw storage; not retaining them means a future model
   improvement cannot re-extract from richer raw evidence without a
   re-import pass. Recommendation: store patch bodies in a
   content-addressed local store referenced by hash, default to
   reference-only in `raw_payload`, and allow per-repo opt-in for
   inline patch bodies. Operator decision required.

2. **Build-log retention.** Should build logs be copied into a
   content-addressed local store (the same store from Q1), or
   referenced by path and content hash to wherever the build system
   wrote them? Same trade-off: copying preserves evidence even if the
   original is garbage-collected by the build system; referencing
   keeps the disk footprint smaller. Recommendation: content-addressed
   store with retention configurable per adapter contract. Operator
   decision required.

3. **Closed `source_kind` enum vs. extensible source registry.** When
   should the closed Postgres `ENUM` be replaced or supplemented by
   an extensible `TEXT` source_kind plus a checked source registry
   table? The design doc says "only if enum churn becomes a real
   migration burden." The threshold is hard to choose in advance.
   Recommendation: a six-importer rule — if Steps 1-3 land six or
   more `source_kind` values without architectural friction, keep the
   enum; if any of those importers requires extending the enum
   mid-feature or proposes a per-customer/per-repo sub-vocabulary,
   migrate to a `source_kind TEXT` plus a `source_kind_registry`
   table at that point. Operator decision required.

4. **Third-party-data extraction policy.** Should human chat/email
   extraction (per Step 3) be blocked entirely until a separate
   third-party-privacy policy exists, or should the per-source
   opt-in gate in § 5.3 suffice? Recommendation: per-source opt-in
   gate is sufficient for the operator's own machine *if* the
   resulting beliefs are tier 2 or higher and never enter packets
   that exit the machine. A separate third-party-privacy policy
   document is still worth writing before Step 3 lands, even if it
   does not change the gate logic. Operator decision required.

5. **First non-AI chat adapter.** Which local export format should
   be the first non-AI chat adapter — mbox, Maildir, Slack JSON,
   Discord JSON, or Matrix JSON? Recommendation: mbox first, because
   it is the most stable on-disk format with the longest history of
   third-party tooling, and email is the chat lane the operator most
   often controls end-to-end. Operator decision required.

6. **Source contract registry timing.** When should the YAML
   contract template become a runtime `source_contracts` table or a
   `source_contract_manifest` column on `sources`? Recommendation:
   defer until Step 3 lands, then promote the YAML files into a
   manifest column the same way RFC 0044 migration `014` introduced
   `bundle_id` for Striatum bundles. Operator decision required.

(At least three named open questions were required by the task
prompt; this RFC names six to leave room for the synthesizer.)

## 10. Cross-References

The table below maps proposed sources / projection families to the
adjacent RFCs. The synthesizer should pin the table when reconciling
the three drafts.

| Proposed source / family | Adjacent RFC | Relationship |
|--------------------------|--------------|--------------|
| `conversation_event` family generally | (none yet; this RFC) | New: extends today's AI-conversation pipeline to non-AI conversation exports under the same projection lane. |
| `document_chunk` family generally | (none yet; this RFC) | New: covers Obsidian, Markdown trees, PDFs, text exports. |
| `project_event` family generally | RFC 0044, RFC 0046 | Same shape as the Striatum projection example (`striatum_references`); generalizes that shape to git history, issue exports, and project artifacts. |
| `code_reference` family | RFC 0046 | Same projection-shape pattern. Reuses the activation-invariant from migration `015`. |
| `artifact_reference` family | RFC 0046, RFC 0047 | Build artifacts feed retrieval as exact references; long bodies stay out of packets per the same rule as RFC 0048's "no raw_payload above caller authorization." |
| `observation_metadata` family | RFC 0033 | Defines the observation layer for non-text evidence. Step 4 sources project into this family. |
| Photo library | RFC 0034 | Step 4 dependency; this RFC defers detailed contract to RFC 0034. |
| Location timeline / places | RFC 0035 | Step 4 dependency; this RFC defers detailed contract to RFC 0035. |
| Daily biography compiler | RFC 0036 | Consumer of `observation_metadata` and cross-family projections. This RFC does not change the compiler's shape. |
| Striatum bundle | RFC 0044, RFC 0045 | Existing. This RFC formalizes the per-source contract that RFC 0044 already implements implicitly, and aligns its terms with the Striatum corpus contract V2 in RFC 0045. |
| Striatum projection lane | RFC 0046 | Reference implementation for `project_event` / `code_reference` / `artifact_reference`. |
| Retrieval / packet behavior | RFC 0047, RFC 0048 | New source families plug into the same retrieval and packet boundary. This RFC does not change RFC 0047 / RFC 0048; it adds families they have to respect. |
| Evaluation gates | RFC 0049 | The minimum gate set in § 7 borrows shape from RFC 0049. The RFC 0049 gate ids (`EG-000`, `EG-010`, ...) remain Striatum-specific; the new source-contract gates use `EG-S00..EG-S31` to keep namespaces distinct. |
| User correction / belief review | D017, RFC 0021 | Unchanged. User corrections remain new `captures` rows, not in-place updates. The interview substrate continues to read claims/beliefs regardless of the new source families that produced them. |
| Privacy tier discipline | D019, D023, D032 | Inherited. New projections carry `privacy_tier` from raw rows; reclassification remains a capture row, not a column update. |
| No-network policy | D020 | Inherited. Every new importer/projection worker runs with no outbound calls. Per-adapter `no_network_access` gate enforces it. |

## 11. Schema Direction

This section restates the design doc's schema direction so reviewers
have a single citable target. It is **not** a migration commitment.

### 11.1 Short term

- Continue adding `source_kind` enum values one importer at a time
  (`git`, `build_artifact`, `obsidian` (already reserved), then
  `mbox`, `slack_export`, etc.).
- Use `captures` as the landing zone for generic project/build
  artifacts where no specialized raw table exists. Migration `015`
  shows the pattern: raw lands in `captures`; projections live in a
  separate per-source projection table with explicit
  generation/activation invariants.
- Keep `conversations` / `messages` for threaded chat-shaped sources.
- Keep `notes` for document-shaped evidence where it fits the existing
  schema.

### 11.2 Medium term

- Add a `source_contract_manifest` JSONB column on `sources` (or a
  `source_contracts` table keyed by `source_kind`) that records the
  adapter version, source family, sub-kind vocabulary, acquisition
  mode, raw artifact policy, and projection-family list. Use the
  RFC 0044 / migration `014` `bundle_id` pattern as the precedent for
  adding new manifest columns.
- Replace the closed `source_kind` enum with `source_kind TEXT` plus a
  `source_kind_registry` table **only if** enum churn becomes a real
  migration burden per Open Question 3.
- Add projection tables per projection family **only when** generic
  `captures` plus per-source projection tables (like
  `striatum_references`) no longer preserve queryability or
  invariants. Do not collapse all future sources into one generic
  JSON projection table.

### 11.3 Long term

- Promote the YAML contract files to a runtime registry once the
  third or fourth source family lands and the contract fields have
  proven stable across re-reviews.
- Re-evaluate whether projection-family vocabulary itself should be
  enforced at the schema boundary (e.g., a CHECK constraint on
  projection rows referencing a `projection_families` table) or
  remain a documentation-plus-test convention.

## 12. What This RFC Is Not

- Not an importer for any new source family.
- Not a migration. No `source_kind` enum changes.
- Not an acceptance of RFC 0033, RFC 0034, RFC 0035, or RFC 0036 as
  binding architecture. Those remain proposals; this RFC names them
  as the design references for Step 4.
- Not an acceptance of RFC 0045-RFC 0049 as binding architecture per
  the 2026-05-15 pivot in `STRIATUM_MEMORY_E2E_BACKLOG.md`. Those
  RFCs are design references for the projection / retrieval / packet /
  gate shapes that this RFC generalizes.
- Not a runtime registry. The contract lives as YAML in
  `docs/source-contracts/` plus importer tests until § 11.2 lands.
- Not a license to bypass the operator. New importers ship disabled
  by default until the operator enables them.

## 13. Authoring Notes (lane: claude)

This draft was authored by the **claude** lane of the
`source-ingestion-rfc-research-2026-05-15` multi-agent research
workflow. It is one of three parallel drafts; a synthesizer agent will
reconcile this draft with the codex and gemini lanes into the final
RFC body. Per the workflow contract:

- This file is a proposal-text draft, not an accepted decision.
- This file does not edit `DECISION_LOG.md`, the RFC index, or the
  source design document.
- This file does not introduce new code, migrations, or schema.
- The author byline names the claude lane and does not impersonate
  another lane (load-bearing per Engram's anti-fabrication discipline).

Reviewers should treat the section structure as the load-bearing
contract: the four-question template (§ 3.1), the closed
projection-family vocabulary (§ 4), the per-family privacy defaults
(§ 5), the rollout order with explicit success criteria (§ 6), and the
minimum evaluation gate set (§ 7) are the parts that must survive
synthesis. The schema-direction text (§ 11) and the open questions
(§ 9) are negotiable; the synthesizer is encouraged to merge across
drafts on those sections without losing the invariants.
