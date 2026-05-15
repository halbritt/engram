# Source Ingestion Expansion Proposal

Status: proposal
Date: 2026-05-15
Context: `HUMAN_REQUIREMENTS.md`, `SPEC.md`, `BUILD_PHASES.md`,
`ROADMAP.md`, `docs/ingestion.md`, RFC 0033-RFC 0036, RFC 0044-RFC 0049

This is a planning artifact, not an accepted architecture decision. It
proposes how Engram should expand beyond the current ChatGPT / Claude /
Gemini / Striatum source set into the wider set of local evidence sources:
chat logs, commit history, build artifacts, notes, files, media, activity
logs, and life records.

The proposal preserves the project constraint: no cloud dependency and no
user data leaving the machine unless explicitly requested.

## Goal

Engram should be able to ingest every useful local trace of a person's work
and life without turning every trace into the same kind of memory.

The ingestion layer should answer four questions for every source before code
is written:

1. What is the immutable raw evidence boundary?
2. What normalized projection is safe and useful to derive from it?
3. Which downstream systems may see the projection by default?
4. What provenance, privacy, confidence, and rebuild rules protect it?

The first expansion should prioritize high-signal, low-egress-risk sources
already present on disk: git history, build/test artifacts, project notes, and
exported chat logs.

## Current Starting Point

The current raw evidence model already has the right shape:

```text
sources
  -> conversations / notes / captures
  -> messages
  -> segments
  -> claims
  -> beliefs
  -> context / memory packets
```

The important constraints are still correct:

- raw evidence is immutable;
- derived rows are rebuildable;
- evidence references must survive every projection;
- generated summaries are never ground truth;
- corpus-reading processes do not make outbound network calls.

The practical limitation is that `source_kind` is currently a closed enum.
Adding many source families one by one will work for the next few importers,
but the expansion needs a stable source contract so each new family does not
invent its own identity, privacy, projection, and extraction rules.

## Proposed Source Contract

Every source adapter should declare a small contract before it can import:

```yaml
source_kind: git
sub_kinds:
  - commit
  - branch
  - tag
  - diff_stat
raw_artifact_boundary: local repository object database plus adapter manifest
identity_keys:
  - repository_root_hash
  - commit_sha
temporal_fields:
  observed_at: committer_date
  recorded_at: import_time
privacy_default: 1
allowed_acquisition:
  - local filesystem
  - explicit user-provided export
network_policy: no outbound calls
raw_retention: keep object references and normalized metadata; optional patch body
projection_families:
  - project_event
  - code_reference
  - artifact_reference
extraction_eligibility: metadata and commit message first; patch bodies opt-in
tests:
  - idempotent re-import
  - conflict on changed raw artifact hash
  - projection rebuild from raw evidence
  - no network access
```

The contract should become a project-local template before broad importer
work begins. It does not need to be a runtime registry on day one, but importer
tests should assert the contract's core invariants.

## Evidence Lanes

Not every source should land as a conversation. Engram should use four raw
evidence lanes:

### 1. Conversation Evidence

Threaded communication where participants, turns, timestamps, and attachments
matter.

Examples:

- existing ChatGPT, Claude, and Gemini exports;
- local exports from Slack, Discord, Matrix, Signal, WhatsApp, Telegram,
  iMessage, SMS, and IRC logs;
- email from Maildir, mbox, Apple Mail exports, or user-provided Gmail
  Takeout;
- meeting transcripts and voice transcription files.

Default projection:

- conversations, participants, messages, attachment metadata, thread links,
  quoted/replied-to references, and privacy tier inheritance.

Extraction posture:

- current AI-conversation extraction can remain the only default-on path;
- human communications should require a source-specific approval gate before
  claim extraction, because they contain third-party data and private content;
- attachment bodies should be metadata-first unless the source contract opts in
  to text extraction.

### 2. Document And Note Evidence

User-authored or user-retained documents where file identity, revisions, and
local paths are the important evidence.

Examples:

- Obsidian vaults and plain Markdown directories;
- project docs, READMEs, design notes, RFCs, changelogs, and TODO files;
- PDFs, text exports, office documents, web clips, bookmarks, and saved pages;
- journals, daily notes, standing facts, and manual corrections.

Default projection:

- document records keyed by path, content hash, title, frontmatter, local
  links, outbound links, headings, and timestamp metadata.

Extraction posture:

- local project docs and user-authored notes are good early candidates for
  segmentation and retrieval;
- personal journals and sensitive docs should default to a higher privacy tier;
- user corrections are raw evidence, not direct database rewrites.

### 3. Project And Execution Evidence

Developer and operator traces that explain what changed, why it changed, and
whether it worked.

Examples:

- git commits, branches, tags, reflog snapshots, submodules, and worktree
  status snapshots;
- GitHub/GitLab issue and PR exports, review comments, and release notes when
  provided as local exports;
- Striatum bundles and workflow artifacts;
- build logs, test reports, coverage data, benchmark results, lint output,
  packaging manifests, CI summaries, and deployment logs;
- generated reports, operator handoffs, and task plans.

Default projection:

- project events, artifact references, code references, run identifiers,
  result summaries, path references, commit references, and failure signatures.

Extraction posture:

- start here after the current Striatum work because the data is local,
  structured, high signal, and mostly project-scoped;
- do not push full patches or long logs into prompts by default;
- use summaries, file/path references, line references, hashes, and citations;
- retain raw logs locally so later parsers can rebuild better projections.

### 4. Observation And Life Evidence

Dense records of location, media, calendar, transactions, health, and physical
world context.

Examples:

- calendar exports, task/reminder exports, contacts, address books;
- photo libraries, videos, screenshots, OCR outputs, EXIF metadata;
- location timelines, GPX tracks, activity/fitness exports;
- receipts, travel records, reservations, warranties, home inventory;
- browser history, shell history, window/app activity, and local OS logs.

Default projection:

- observations, intervals, assets, places, events, people candidates, coverage
  gaps, and redaction-aware summaries.

Extraction posture:

- treat this as post-project-source work;
- exact coordinates, health, finance, contacts, and third-party data need
  stricter default privacy than project artifacts;
- RFC 0033-RFC 0036 should remain the design reference for multimodal,
  photo, location, and daily-biography sources.

## Source Family Map

### Chat Logs

Chat logs are not one source. They split into AI conversations, private human
messages, group workspaces, email, and transcripts.

Recommended contract:

- raw boundary: export file or local database copy plus import manifest;
- identity: source platform, workspace/account identity, thread id, message id;
- temporal model: message timestamp as observed time, import time as recorded
  time, edit timestamp when available;
- projection: conversation, message, participant, attachment, reaction, reply
  edge;
- privacy default: AI exports tier 1 or 2 depending on user setting; human
  communications tier 2+ by default;
- first milestone: add a generic exported-chat adapter shape, then specialize
  per platform.

Risks:

- third-party privacy;
- deleted/edited message semantics;
- duplicated exports from multiple devices;
- attachments with hidden sensitive data.

### Commit History

Git history is a strong next source because it creates a durable timeline of
project intent and outcome.

Recommended contract:

- raw boundary: repository path, git object ids, adapter manifest, and optional
  patch/body capture policy;
- identity: repository root content identity plus commit SHA;
- temporal model: author date and committer date preserved separately;
- projection: commit event, parent edges, changed paths, diff stats, commit
  message, refs, tag/release association;
- privacy default: tier 1 for explicitly selected project repos, configurable
  upward;
- first milestone: commit metadata and diff stats only; patch bodies opt-in.

Derived retrieval should answer:

- "What changed around this date?"
- "Which commits touched this file?"
- "What issue, RFC, or decision does this commit mention?"
- "What build/test evidence followed this commit?"

### Build Artifacts

Build artifacts explain whether work actually ran and what failed. They should
not be treated as chat or notes.

Recommended contract:

- raw boundary: artifact directory plus manifest of file path, size, mtime,
  content hash, media type, and parser version;
- identity: project id, run id, commit SHA when available, artifact path hash;
- temporal model: run started/finished timestamps and import timestamp;
- projection: run summary, test suite summary, failure signatures, coverage
  summary, benchmark measurements, lint diagnostics, produced files;
- privacy default: inherit from project/repo source unless artifact declares a
  stricter tier;
- first milestone: local directories containing JUnit XML, pytest output,
  coverage JSON/XML, benchmark JSON, logs, and Striatum reports.

Long logs should be summarized and cited, not pasted into context by default.
Raw artifact files remain local evidence so summaries can be rebuilt.

### Notes, Docs, And File Trees

Notes and docs carry explicit human meaning and should reach retrieval early.

Recommended contract:

- raw boundary: file content hash and path snapshot at import time;
- identity: vault/root id plus normalized relative path and content hash;
- temporal model: filesystem mtime, frontmatter dates, git dates when available;
- projection: headings, links, tags, frontmatter, document chunks, path refs;
- privacy default: project docs tier 1, personal vaults tier 2+ by default;
- first milestone: Markdown and plain text directories before binary formats.

### Browser, Shell, And App Activity

These sources are high value but high risk. They reveal attention and behavior
at a granularity that can swamp memory.

Recommended contract:

- raw boundary: explicit local export or copied local database snapshot;
- identity: profile id plus event id/path/url/command hash;
- temporal model: event time and import time;
- projection: coarse sessions, visited domains/pages, command summaries,
  project/path references;
- privacy default: tier 3 by default;
- first milestone: defer until project-source and note-source foundations are
  stable.

Never start with continuous live capture. Backfills from explicit local exports
are safer and easier to audit.

### Media, Location, Calendar, And Life Records

This family should follow RFC 0033-RFC 0036. It is central to the long-term
biography goal, but it needs stronger privacy and specialized projections.

Recommended contract:

- raw boundary: local export, file reference, content hash, and sidecar
  metadata;
- identity: content hash, source asset id, event id, calendar uid, or sample id;
- temporal model: created/observed time, source timezone, import time, valid
  interval when applicable;
- projection: assets, observations, visits, place candidates, event intervals,
  person candidates, coverage gaps;
- privacy default: tier 3+ for location, health, finance, contacts, and raw
  media; tier 2+ for calendar depending on corpus;
- first milestone: do not begin until the source contract and project/document
  lanes are proven.

## Implementation Sequence

### Step 0: Source Contract And Taxonomy

Create a canonical source contract template and a small closed vocabulary for:

- source family;
- sub-kind;
- raw artifact boundary;
- acquisition mode;
- network policy;
- temporal field mapping;
- identity and deduplication keys;
- privacy default;
- projection family;
- extraction eligibility.

This step can be documentation plus tests for new adapters. It does not need a
large schema migration immediately.

### Step 1: Project Sources

Implement the first concrete importers for local developer evidence:

1. git commit history importer;
2. build artifact directory importer;
3. Striatum artifact/reference alignment where the new source contract helps.

This gives Engram a high-signal local work memory without touching private chat
apps, location, finance, or health data.

### Step 2: Project Notes And Markdown Trees

Add Markdown/plain-text tree ingestion for project docs and selected notes.
This should reuse the same source contract, content hashing, path reference,
and privacy inheritance mechanisms from Step 1.

### Step 3: Exported Communication Logs

Add local-export adapters for email and team chat. Start with formats that are
plain files on disk, such as mbox, Maildir, Slack export JSON, Discord export
JSON, or Matrix export JSON.

Extraction from these sources should remain opt-in per source family.

### Step 4: Life And Observation Sources

Add calendar, photos, location, and other life-record importers after the
projection and privacy gates are boring. This is where RFC 0033-RFC 0036
should be revisited and either accepted, revised, or split into executable
implementation slices.

### Step 5: Live Capture

Only after backfill adapters are reliable should Engram add live capture:

- manual capture;
- MCP capture;
- local watcher-based file capture;
- optional local audio/screenshot capture.

Live capture should always be explicit, visible, and locally disabled by
default.

## Schema Direction

Short term:

- continue adding `source_kind` enum values deliberately for concrete importers;
- use `captures` for generic project/build artifacts where no specialized raw
  table exists;
- keep conversations/messages for threaded chat;
- keep notes for document-like evidence where it fits the existing schema.

Medium term:

- add a source contract table or manifest column that records adapter version,
  source family, sub-kind vocabulary, acquisition mode, and raw artifact policy;
- consider replacing the closed `source_kind` enum with an extensible
  `source_kind` text plus checked source registry only if enum churn becomes a
  real migration burden;
- add projection tables per source family only when generic `captures` no
  longer preserves queryability or invariants.

Do not collapse all future sources into one generic JSON table. Generic raw
capture is useful as a landing zone, but retrieval, privacy, and evaluation
need typed projections.

## Evaluation Gates

Every new source adapter should ship with gates for:

- local-only acquisition and no network calls;
- idempotent re-import;
- conflict detection when the same external id has different raw content;
- raw evidence immutability;
- projection rebuild from raw evidence;
- privacy tier inheritance;
- attachment/blob retention policy;
- extraction opt-in where source data includes third-party or sensitive data;
- packet/retrieval citation back to raw evidence.

For git and build artifacts, add specific gates:

- the same repository imported twice produces no duplicate commit events;
- rewritten history is represented as new evidence, not an in-place rewrite;
- a build run links to the commit SHA when present;
- long logs do not enter context packets unless explicitly requested;
- failure signatures cite the log artifact and line/window reference.

## Initial Deliverable Recommendation

The next implementation slice should be:

1. add a source contract template under docs, with draft contracts for `git`,
   `build_artifact`, and `exported_chat`;
2. add `source_kind='git'` and a local git importer for commit metadata and
   diff stats;
3. add `source_kind='build_artifact'` and a directory importer for JUnit,
   coverage, benchmark, and plain-log artifacts;
4. project both into a small `project_events` or equivalent typed projection;
5. expose exact-reference retrieval by commit SHA, path, run id, and artifact
   hash;
6. keep full patch bodies and full logs out of memory packets by default;
7. keep human chat import and extraction disabled until the exported-chat
   privacy and third-party-data gates are explicit.

This sequence maps chat logs, commit history, and build artifacts together,
while starting implementation with the lowest-risk project evidence first.

## Open Decisions

- Should patch bodies be retained in raw evidence by default, or only commit
  metadata plus diff stats?
- Should build logs be copied into a managed content-addressed store or
  referenced by path and hash?
- Which source families default to privacy tier 1, 2, or 3?
- Should human chat/email extraction be blocked until a separate third-party
  privacy policy exists?
- When should the closed `source_kind` enum be replaced or supplemented by a
  source registry?
- Which local export format should be the first non-AI chat adapter?

## Non-Goals

- No cloud sync or hosted API ingestion.
- No automatic Gmail, Slack, GitHub, Apple, Google, or browser account access.
- No continuous surveillance capture.
- No bidirectional sync back to source systems.
- No automatic deletion or mutation of raw evidence.
- No turning generated summaries into authoritative source records.
