# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (informally, as it follows project phases).

## [Unreleased]

### Fixed
- `engram entity-grounding process-approved` now refuses to start when
  `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` is unset, matching
  `broker-daemon`. The previous operator-DSN fallback is closed; the
  network-capable materializer always runs through the restricted broker
  role. Decision recorded in
  `docs/reviews/grounding-stack-architectural-review-2026-05-20/SYNTHESIS.md`
  (D3).
- Hardened RFC 0054/0055 entity grounding after adversarial review: entity
  surface network grants now require byte-exact `search_query == surface_form`
  validation before persistence and adapter dispatch; materialization re-filters
  provider result URLs before local evidence insertion; and materialized
  evidence-attachment review actions preserve the approved query privacy tier.
- Added `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` as the restricted
  broker-authority DSN seam for `engram entity-grounding process-approved`;
  the default connection remains available only for local development and
  mocked tests.
- Added `scripts/provision_grounding_broker_role.py`,
  `scripts/check_grounding_broker_role.py`,
  `make provision-grounding-broker`, `make check-grounding-broker`, and
  `docs/runbooks/grounding-broker-role.md` to provision and verify the local
  restricted PostgreSQL role for provider-backed grounding materialization.

### Added
- `engram entity-grounding broker-daemon`, `make grounding-broker-daemon`, and
  `docs/runbooks/grounding-broker-daemon.md` scaffold the local long-running
  network-capable grounding broker workflow. The daemon requires the restricted
  broker DSN, uses a per-iteration PostgreSQL advisory lock, and skips grants
  that already have dispatch audit rows to avoid repeated provider calls.
- `striatum/entity-grounding-broker-daemon-2026-05-19/` adds a max-parallelism
  Striatum scaffold for daemon core, CLI surface, idempotency/security, docs,
  verification, synthesis, and final review lanes.
- Striatum run `run_ecf126b2e6234ae3b54958d8471e5e56` executed that daemon
  scaffold to completion with all seven jobs completed and final review
  `accept_with_findings`.
- `striatum/entity-grounding-broker-daemon-followups-2026-05-19/` scaffolds the
  residual daemon work: durable dispatch/concurrency, retry/cooldown policy,
  production daemon packaging, CLI typecheck debt, review/claim-use gate, docs,
  verification, synthesis, and final review.
- `ROADMAP.md` now records
  `ARCHITECTURE_RECOMMENDATION_EXECUTION_PLAN_2026-05-16.md` as the active
  architecture-followup supplement, freezing RFC 0050 Stage 3+ source-family
  expansion until minimal cited `context_for` and the first eval loop exist.
- Direct `PyYAML` runtime dependency plus `scripts/authority_lint.py` for
  RFC header/index status, schema-doc table coverage, and dependency checks.
- Unified `MemoryHit` retrieval contract for Striatum, git, build-artifact,
  and Markdown exact-reference lanes. `MemoryService.fetch_reference()` now
  supports non-capture references (`git_commits`, `build_artifacts`,
  `markdown_files`) with tenant/corpus re-authorization, and packet citations
  use stable source fields without raw body leakage.
- `engram no-egress probe`, `engram no-egress run -- <command>`, and
  `make no-egress-smoke` with honest unsupported reporting when OS-level
  network isolation is unavailable.
- Minimal personal `engram context-for` compiler over pinned/current beliefs,
  historical beliefs, recent captures, exact message refs, explicit gaps,
  provenance/confidence tags, privacy/sensitivity policy withholding, word
  budgets, and append-only warm snapshots.
- MCP stdio `engram.context_for` tool with explicit `memory.read_personal`
  authorization, strict local argument parsing, privacy-tier ceiling support,
  and response limiting for recent-signal and per-lane output.
- Context eval runner and `engram eval context` command over JSONL gold items,
  scoring required fact recall, stale fact hits, required gaps, citation
  coverage, unsupported-fact approximation, and token/word waste.
- Public context eval item schema at
  `docs/schemas/context_eval_item.v1.schema.json`, schema notes at
  `docs/schemas/README.md`, Python dataset validation in
  `src/engram/context_eval.py`, and external private eval dataset discovery via
  `ENGRAM_EVAL_DATASET_PATH` or `engram eval context --dataset-path`.
- Public synthetic context-eval starter dataset at
  `tests/fixtures/context_eval/gold.jsonl`, plus a seeded synthetic-corpus
  regression that runs the real `engram eval context` CLI/compiler path without
  committing owner data.
- Synthetic context-eval e2e harness at
  `tests/fixtures/context_eval/synthetic_e2e/` plus `make e2e-context-synthetic`.
  The harness seeds synthetic beliefs, captures, and local public-entity
  grounding evidence so proper nouns can be resolved as product/person/place
  through local `engram.ground_entity` without live network access.
- `docs/specs/context-serving-eval-v1.md` records the accepted `context_for`
  V1 and context eval contracts from D087.
- `docs/specs/README.md` indexes current implementation specs and
  proposal-level design contracts.
- RFC 0051 and RFC 0052 design-reference docs for the generic
  evidence/reference substrate and local entity grounding/review substrate.
- RFC 0053 proposal for the constrained claim-extraction/grounding boundary:
  versioned grounding request/response shapes, process capability split, and
  explicit prohibition on surrounding raw corpus context reaching
  network-capable broker modes.
- `src/engram/claim_grounding.py` plus public request, response, and
  network-dispatch schemas scaffold the RFC 0053 contract. The extractor
  request records network intent and grant metadata, while the dedicated
  `claim_grounding.network_dispatch.v1` shape is the minimized broker-to-adapter
  egress payload. The granted `search_query` may be private entity-name text and
  carries `query_privacy_tier`; internet search remains broker-side only and
  disabled by default.
- `make e2e-claim-grounding-synthetic` adds a deterministic synthetic
  claim-grounding gate for RFC 0053 request/dispatch/response validation,
  local ambiguity, denied network results, fake granted-broker citation,
  poisoned public evidence, and no-live-network behavior.
- Migration `024_claim_grounding_runtime.sql` adds append-only RFC 0053
  sidecars for claim-grounding requests, grants, grant uses, network dispatch
  attempts, responses, and response/claim/evidence links.
- `src/engram/claim_grounding_runtime.py` and
  `src/engram/claim_grounding_broker.py` scaffold persisted local broker
  execution for RFC 0053. Sidecar persistence is explicit, network behavior is
  injected-adapter-only, and default execution performs no live network access.
- RFC 0053 runtime-completion scaffold: append-only grant lifecycle helpers
  now record draft/approved/denied/revoked rows and verify the latest live,
  unexpired, target-authorized persisted grant before network dispatch audit.
- `src/engram/claim_grounding_network.py` adds a disabled-by-default,
  operator-configured HTTP search-adapter scaffold with fixed GET dispatch,
  timeout/byte/result limits, private-address result filtering, and sanitized
  response-shaped candidate payloads. It is not ambient network access and is
  not enabled by default.
- RFC 0053 Tavily provider scaffold for broker-owned internet grounding:
  `ENGRAM_CLAIM_GROUNDING_SEARCH_PROVIDER=tavily` selects fixed POST dispatch to
  Tavily's HTTPS Search API, `ENGRAM_CLAIM_GROUNDING_TAVILY_API_KEY` supplies
  the secret outside the repo, and the adapter sends only the exact
  grant-bound entity surface query. Live broker invocation now requires
  persisted sidecars plus a latest-approved grant before calling any injected
  network adapter.
- RFC 0054 and RFC 0055 proposal docs split entity-wide grounding into a
  draft-only batch workflow over unresolved entities and a separate
  approved-grant materialization workflow that must write provider rows to
  append-only local grounding evidence before responses or review actions
  consume them.
- `engram entity-grounding draft` and
  `engram entity-grounding process-approved` expose the RFC 0054/0055 operator
  command names through lazy implementation-module dispatch with sanitized JSON
  output. `make e2e-claim-grounding-runtime` now includes the entity-grounding
  workflow/materialization tests when those lane files are present, and
  `make e2e-entity-grounding` aliases that gate.
- `engram claim-grounding grants list|draft|approve|deny|revoke` provides a
  CLI-first operator surface for exact grant display and append-only grant
  lifecycle decisions without performing network IO.
- `src/engram/claim_grounding_integration.py` adds disabled extraction-adjacent
  sidecar emission for accepted claim drafts, linking grounding requests to the
  extraction without mutating claim content or sending raw segment/message text.
- `tests/test_claim_grounding_security.py` adds a starter broker credential
  separation regression proving a broker role can read only minimized
  request/grant rows, write only bounded audit/evidence rows, and cannot read
  raw corpus tables.
- Local RFC 0053 entry points:
  `engram claim-grounding entity --request-json PATH` and MCP
  `engram.claim_ground_entity`, both local-only.
- `make e2e-claim-grounding-runtime` runs the request validator, broker,
  runtime sidecar, grant lifecycle, network-adapter, credential-separation,
  extraction-sidecar, migration, and synthetic no-live-network grounding tests.
- Adversarial security review for RFC 0053 documents the broker/network threat
  model and blockers required before network grounding can become default-on or
  affect extraction output.
- Canonical docs now distinguish ordinary evidence-linked claims, local
  public-entity grounding evidence, and the proposal-only RFC 0053
  extractor/grounder boundary so "grounding" does not imply approved network
  access.
- Striatum RFC 0053 review workflow added and run for six parallel Codex lanes
  over privacy/query boundary, network security, schema contract, runtime
  integration, product/MCP surface, and eval gate. The resulting ledger and
  synthesis keep RFC 0053 proposal-only while pinning blockers for exact
  entity-surface network queries, persisted grants, broker credential
  separation, sidecar/audit persistence, and the now-scaffolded
  `make e2e-claim-grounding-synthetic` /
  `make e2e-claim-grounding-runtime` gates before any live network runtime or
  extraction-affecting grounding ships.
- Proposal-level A10/A11 design specs:
  `docs/specs/local-backup-key-tier5-design-v1.md` for local encrypted
  backup, key hierarchy, restore smoke, dead-man's-switch, and Tier 5
  destruction; and `docs/specs/blob-vault-local-s3-exploration-v1.md` for the
  local S3-compatible blob-vault exploration.
- Migration `021_context_events_snapshots_feedback.sql` adds append-only
  `memory_events`, `context_snapshots`, and `context_feedback` tables plus
  `memory_epoch_seq`. `src/engram/events.py` adds memory-event and
  context-feedback helpers. Phase 4 belief review actions now emit sanitized
  `belief_changed` memory events without note/correction body leakage.
- Central deterministic `engram.policy` module with closed action/reason
  vocabulary. `context_for` uses it for privacy tier, sensitivity, and
  tenant/corpus release decisions, `MemoryService.build_packet()` now uses it
  for packet omissions and cite-only body suppression, and the shared
  interview/bench-review web tier guard plus Phase 3 interview export tier
  filtering now route through the same policy contract.
- Migration `022_generic_evidence_reference_index.sql` adds rebuildable
  `evidence_items` and `evidence_refs` projections. `src/engram/evidence.py`
  backfills current supported sources, `engram evidence refresh-index` /
  `make evidence-refresh` expose the rebuild, and exact-reference search now
  reads the generic index before falling back to source-specific lookup
  branches.
- Migration `023_entity_grounding_review.sql` adds append-only
  `entity_grounding_evidence` and `entity_identity_review_actions`.
  `src/engram/entity_grounding.py` and MCP `engram.ground_entity` provide
  authorized local-only entity grounding lookup; internet-search
  requests to that local MCP tool fail closed.
- Generated schema docs refreshed via `make schema-docs` so
  `docs/schema/README.md` includes migrations 021-023, including the context
  event tables, generic evidence/reference index, and entity grounding/review
  substrate.
- Canonical roadmap, handoff, backlog, RFC, and spec docs were scanned and
  refreshed for the D094 A8/A9 status change: stale A0-A7 summaries, RFC
  0051/0052 proposal-gate wording, old generated-product gate phrasing, and
  verification-count references now point at the current A0-A9 state.
- Top-level README/SPEC/TODO/source-ingestion/agent-context docs now describe
  the actual partial Phase 4/5 surface instead of treating `current_beliefs`,
  `context_for`, MCP serving, snapshots, feedback, generic references, and
  local grounding as wholly future work.
- `docs/runbooks/striatum-memory-e2e-2026-05-15.md` documents the local
  real-bundle Striatum ingest/projection/index/MCP packet smoke path.
- Striatum packet audit reconstruction helper and regression coverage for
  dirty working-tree packet labels and selected/omitted packet-audit replay
  without loading raw memory content.
- D094 records operator approval to proceed with the narrow RFC 0051/0052
  implementation slices while keeping generated products, remote grounding
  fetches, high-risk source families, backup, and blob-vault implementation
  separately gated.
- RFC 0050 source-ingestion expansion proposal landed via multi-lane research
  workflow (claude/codex/gemini drafts, codex prior-art research, claude
  privacy + gemini project-judgment reviews, codex findings ledger and
  synthesis), and was later accepted as design reference by D084.
- `SOURCE_INGESTION_BACKLOG.md` layer-by-layer execution plan derived from
  RFC 0050.
- Source-contract template at `docs/source-contracts/README.md` and example
  contracts (`git.yaml`, `build_artifact.yaml`).
- Source-contract validator (`src/engram/source_contract.py`) with a closed
  error vocabulary.
- Migration `017_source_kind_git.sql` adds `source_kind='git'` plus
  append-only `git_commits` and `git_commit_paths` tables.
- Local git metadata + diff-stat importer (`src/engram/git_import.py`) with
  closed git-verb allowlist, no-egress invariant, idempotent re-import,
  rename detection, and coverage-gap emission.
- `engram import git <repo-path>` CLI verb with `--dry-run`, `--allow-dirty`,
  `--repo-label`, tenant/corpus overrides, and reserved `--full-patch=false`.
- 32 new tests across contract validation, git import behaviour, and
  no-egress invariants.
- Migration `018_source_kind_build_artifact.sql` adds
  `source_kind='build_artifact'` plus append-only `build_artifacts` and
  `build_artifact_findings` tables.
- Build-artifact importer (`src/engram/build_artifact_import.py`) parses
  JUnit XML, coverage JSON, benchmark JSON, ruff/eslint/pyright lint
  output, and plain logs; emits redaction markers and promotes
  sensitivity to `credential_or_secret_reference` when secret-shaped
  content is detected; emits `coverage_gap` rows for unrecognized
  artifact kinds.
- `engram import build-artifacts <dir>` CLI verb with `--run-id`,
  `--commit-sha`, `--repo-label`, and `--dry-run`.
- Migration `019_source_kind_markdown_tree.sql` adds
  `source_kind='markdown_tree'` plus append-only `markdown_files` /
  `markdown_file_chunks` / `markdown_file_links` tables with
  tombstone+supersede lifecycle for content drift and file deletion.
- Markdown importer (`src/engram/markdown_import.py`) walks a directory
  tree, splits frontmatter, projects heading anchors, chunks, inline /
  reference / wiki / autolink / image / tag links; tombstones missing
  files; recognizes title from frontmatter or H1.
- `engram import markdown <root>` CLI verb.
- 18 new tests across build-artifact and Markdown importers (no-egress,
  idempotency, content drift, redaction, link detection).
- DECISION_LOG entries D083-D086 record operator acceptance: RFC 0046-0049
  and RFC 0050 as design reference (resolves AL-D002 / AL-D004), default-on
  Level 3 Striatum operator memory authorization within the Striatum
  tenant boundary (resolves AL-D003), and an explicit deferral of the
  generated-product contract until a concrete forcing use case lands
  (AL-D004 deferred). RFC index status updated to
  `accepted_as_design_reference` for RFC 0046-0050.
- Layer 6 source_audits + EG-SI-090 audit reconstruction: migration 020
  adds append-only `source_audits` capturing every importer invocation
  (source_kind, source_id, adapter_version, input_signature, outcome,
  rows_inserted/skipped/tombstoned, coverage_gap_count, started_at,
  completed_at, raw_payload). All three Layer 1-3 importers
  (`git_import`, `build_artifact_import`, `markdown_import`) record one
  audit row per invocation inside the same transaction as the inserts.
  EG-SI-090 reconstructs the importer outcome history without reading
  importer raw_payload bodies. No-derived-product-leak test asserts
  body text never lands in the audit payload.
- Layer 5 exact-reference retrieval extension: `MemoryService.search`
  filter `exact_refs` now surfaces project-execution rows (`commit_sha`
  -> `git_commits`, `source_hash` -> `build_artifacts.content_hash`,
  `run_id` -> `build_artifacts.run_id`, `path` -> active
  `markdown_files`) alongside the existing Striatum projection path,
  without introducing vector search. 5 new tests.
- Layer 4 EG-SI evaluation gates: `tests/test_source_ingestion_gates.py`
  exercises EG-SI-000 (no-egress), EG-SI-010 (contract validator),
  EG-SI-020 (idempotency + conflict), EG-SI-040 (redaction + sensitivity
  promotion), EG-SI-050 (projection rebuild), EG-SI-060 (exact-reference
  citation by commit_sha / artifact_hash / markdown path), EG-SI-080
  (coverage gaps + tombstones), and EG-SI-100 (fixture matrix).
  Surfaced via `make eval-source-ingestion-gates`.
- Example source contracts at `docs/source-contracts/markdown_tree.yaml`
  (Layer 3) added alongside `git.yaml` and `build_artifact.yaml`.
- Source ingestion expansion proposal covering chat logs, commit history,
  build artifacts, notes/docs, project evidence, media/location/life records,
  source contracts, privacy defaults, rollout order, and evaluation gates.
- Striatum memory roadmap documenting how Engram should evolve from RFC 0044
  raw Striatum bundle ingestion into a full local memory system for Striatum
  operator logs, workflow agents, designs, reports, changelogs, git history,
  blockers, and generated artifacts.
- Striatum-first roadmap RFC scaffolds for RFC 0045 through RFC 0049, covering
  the Striatum Corpus Contract V2, Engram Striatum projections/indexes,
  retrieval augmentation boundary, context-injection policy, and evaluation /
  no-egress / retrieval-quality gates, plus a Striatum workflow queue packet
  that preserves the dependency order and review lanes.
- Striatum memory roadmap execution handoffs for RFC 0044 hardening cleanup,
  RFC 0045 Corpus Contract V2, RFC 0046 projection/index schema, RFC 0047
  retrieval augmentation boundary, RFC 0048 context-injection policy, and RFC
  0049 evaluation gates. The workflow completed multi-lane reviews, a bounded
  contract-coherence repair and re-review, a findings ledger, and final
  synthesis; the artifacts remain proposal evidence and keep Striatum memory as
  optional, local-only augmentation rather than authoritative workflow state.
- Striatum memory RFC alignment follow-up workflow scaffold, queued from the
  roadmap final synthesis, with five initial lanes for RFC 0046-RFC 0049
  alignment and roadmap/RFC index cleanup before independent review, findings
  ledger, and final synthesis.
- Striatum memory RFC alignment handoffs and independent review artifacts under
  `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/`. The run remains
  proposal/document alignment only: it does not implement code, promote RFCs,
  change runtime behavior, or authorize default-on Striatum memory. Contract and
  privacy reviews returned `accept_with_findings`; the ergonomics recovery review
  returned `needs_revision` and queued a bounded RFC 0046 provenance repair.
- Striatum memory RFC alignment workflow final synthesis. The RFC 0046
  provenance/authorization repair was accepted on fresh re-review, the original
  ergonomics `needs_revision` was superseded to `accept_with_findings`, the
  findings ledger and final synthesis were published, and the run completed with
  no open blockers or checkpoints. Remaining work is carried as promotion,
  implementation, and deferred gate findings.
- Operator handoff summary for the alignment run was recorded in
  `OPERATOR_REPORT.md` with the current backlog extracted from the findings
  ledger for the next operator.
- Applied alignment findings ledger nonblocking items `AL-N001`, `AL-N002`,
  `AL-N003`, `AL-N004`, `AL-N005`, `AL-N006`, and `AL-N009` to RFC 0046,
  RFC 0047, RFC 0048, and RFC 0049 as proposal-text edits: generic
  `filters.exact_refs` shape on the retrieval request; canonical
  `omitted[]` audit-event shape with closed reason vocabulary; embedding
  activation manifest and XOR invariant; `raw_payload` privacy-inheritance
  rule and EG-060 proposal fixture; `dirty_working_tree` surfacing in
  retrieval, packet freshness label, and EG-050/EG-110 sub-cases; aligned
  loopback/local-runtime no-egress wording; and EG-120 disable-control
  restart/promotion gate cases. The RFC package remains proposal/default-off;
  promotion still depends on the deferred `AL-D001` RFC 0044 hardening /
  EG-000 evidence, `AL-D002` recorded acceptance decision, and `AL-D003`
  Level 3 / default-on authority gates.
- Striatum memory RFC promotion workflow scaffold queued at
  `striatum/striatum-memory-rfc-promotion-2026-05-14/`. Four per-RFC
  promotion-recommendation lanes (RFC 0046-RFC 0049, codex), three
  independent reviewer lanes (codex contract coherence, claude
  privacy/no-egress boundary, gemini operator ergonomics), findings ledger,
  and final synthesis. Output destination is
  `docs/reviews/striatum-memory-rfc-promotion-2026-05-14/`. The workflow
  does not edit RFC text, does not record an AL-D002 acceptance decision,
  and does not authorize implementation.
- Engram Striatum control plane migrated from repo-local SQLite
  (`.striatum/state.sqlite3`) to daemon-backed PostgreSQL on
  `2026-05-14`, then rolled back to repo-local SQLite under
  `STRIATUM_TEST_HARNESS=1` after daemon client-token bootstrap issues.
  Pre-migration SQLite restored from `.striatum/state.sqlite3.bak`; the
  Postgres-side registration `repo_b63673a288c64bb987d29bafffaed578`
  remains but is unused.
- Striatum memory RFC promotion run
  `run_c16bd15778f6473e800af5378d609449` was prepared on master, started
  under `STRIATUM_TEST_HARNESS=1`, and reached step 1 with four codex
  author sessions claimed and supervised before stalling on a Striatum
  supervisor-stdin-EOF integration bug. The four hung lanes were
  SIGTERM'd and the run was canceled with reason
  `blocked_on_striatum_18_codex_stdin_eof; new run after fix`. Filed
  upstream as [striatum#18](https://github.com/halbritt/striatum/issues/18)
  for the supervisor stdin fix and
  [striatum#20](https://github.com/halbritt/striatum/issues/20) for the
  operator-watchdog / runner-side timeouts gap. The scaffold remains
  valid for a fresh `striatum run prepare` once #18 lands or the
  workflow lane command is changed away from stdin delivery.
- Migration 012 comment reverted from `D-082` to `D082` to match the
  decision-ID style used by the rest of the migration and review docs
  and to unblock the migration drift check (`make migrate` was refusing
  because the on-disk hash diverged from the applied hash).
- `ROADMAP.md` and `TODO.md` refreshed to reflect the actual Phase 2 and
  Phase 3 state. Phase 2 segmentation/embedding is complete across the
  full AI-conversation corpus (7916 conversations, 11266 active embedded
  segments). Phase 3 primary extraction run is complete (43812 claims,
  42558 beliefs, last extraction 2026-05-07). Step 5 (gold-set authoring)
  is now the active step; Phase 3 cleanup of 149 unextracted active
  segments and 22 failed extractions is residual.
- Durable agent context notes landed at
  `docs/AGENT_CONTEXT_NOTES.md`. Replaces per-session auto-memory for
  cross-session continuity: behavioral feedback rules (no fabricated
  provenance, subprocess delegation discipline, supervisor watchdog
  must catch heartbeat stalls, doc-only branch policy), active project
  context (2026-05-15 e2e pivot, Striatum daemon transition in
  test-harness mode, pipeline state, RFC 0027 UI polish deferred,
  predicate-intent polish queued), references (Striatum repo
  location, upstream bug pointers), and maintenance rules.
  `AGENTS.md` start-here list now points at it.
- Striatum-memory e2e backlog execution plan landed at
  `STRIATUM_MEMORY_E2E_BACKLOG.md`, superseding the paper-promotion
  sequencing for execution order: build forward layer by layer
  (projection → retrieval → packet → gates → MCP smoke) treating RFC
  0045-RFC 0049 as design reference, not as contract gates. Records
  the 2026-05-15 pivot and explicit sequencing through AL-D002, with
  the nonblocking RFC polish (AL-N007/N008/N010-N015) and AL-D003 /
  AL-D004 carried as cross-cutting items.
- RFC 0044 hardening / EG-000 baseline evidence landed at
  `docs/reviews/eg-000-evidence-2026-05-15/EG_000_EVIDENCE.md`, closing
  `AL-D001` from the alignment findings ledger. The evidence covers all
  eight EG-000 pass criteria: primary-pair search/fetch enforcement,
  MCP `--allow-pair` not granting cross-tenant/corpus reads, restricted
  `describe-corpus` positional shorthand, rejection of unknown
  `--capability memory.*` names, applied-ordering schema version,
  committed non-private fixture round-trip, and Striatum-side
  zero-Engram-coupling. Supporting code: `KNOWN_MEMORY_CAPABILITIES`
  vocabulary in `src/engram/memory.py`; capability validation in
  `src/engram/mcp_stdio.py::build_token`; describe-corpus CLI guard;
  applied-ordering schema query in `MemoryService.health`. Supporting
  fixture: `tests/fixtures/striatum_eg000/` (committed bundle plus a
  deterministic regeneration script). New tests in
  `tests/test_striatum_ingest.py`, `tests/test_mcp_stdio.py`, and
  `tests/test_cli.py`. The evidence does not by itself authorize RFC
  0046-RFC 0049 implementation; the AL-D002 acceptance decision and the
  remaining nonblocking promotion items remain prerequisite.
- Striatum-memory e2e implementation advanced through the first retrieval
  layers. Layer 1 added migration 015 with `striatum_projection_generations`
  and `striatum_references`, the deterministic Striatum projection worker,
  `engram phase-projection run`, and the `make project` target. Layer 2 added
  exact-reference retrieval via `filters.exact_refs`, MCP search filter
  parsing/schema support, and per-hit `dirty_working_tree` / `freshness`
  fields while preserving the lexical fallback. Layer 3 added packet building,
  privacy-safe `striatum_packet_audits`, and the `engram.build_packet` MCP
  tool. EG-010 fixture groundwork now lives under
  `tests/fixtures/striatum_v2/` with a reusable builder/validator and
  committed `minimal`, `multi_corpus_isolation`, `redaction`, and `tombstone`
  scenarios. The `eval-gates` and `e2e-striatum` targets cover the current
  fixture/retrieval/packet gates and the EG-000 ingest → projection → MCP
  search/packet smoke.
- RFC 0038 operator UI rework proposal and Striatum implementation workflow
  scaffold, derived from `ENGRAM_UI_REWORK_HANDOFF.md`, covering a three-lane
  UI implementation split plus the normal review cycle augmented with an
  ergonomics design review.
- RFC 0038 repair workflows were queued after correctness and ergonomics review
  findings, including a follow-up workflow for the DB-backed interview route
  evidence blocker, parallel correctness, security, and ergonomics re-reviews,
  and a corrected review-only pass after the first follow-up review packets
  omitted the current evidence artifacts.
- RFC 0038 accept-with-findings follow-up workflow was queued to address the
  corrected review residuals across three implementation lanes: interview
  navigation/security/audit behavior, bench keyboard/tier cleanup, and shared
  chrome drift cleanup.
- RFC 0038 second repair workflow was queued after the accept-with-findings
  correctness review found two remaining blockers: bench FastAPI-generated
  docs/openapi routes still exposed CDN-backed assets, and interview IPv6
  loopback bind support did not yet align with same-origin POST validation.
- RFC 0038 second repair workflow completed: bench generated docs/openapi
  routes are disabled, configured interview IPv6 loopback POSTs are accepted
  without widening the default Origin allowlist, evidence passed, and fresh
  correctness, security, and ergonomics reviews all returned `accept`.
- RFC 0044 Engram-side Phase 1 implementation: migration 014 adds
  `source_kind='striatum'`, local `tenant_id` / `corpus_id` boundaries, and
  bundle identifiers for Striatum raw captures; `engram ingest-striatum`
  validates and idempotently ingests Striatum JSONL corpus bundles from disk;
  `engram describe-corpus` reports authorized corpus metadata; and
  `engram-mcp-stdio` exposes the four read-only MCP tools
  `engram.search`, `engram.fetch_reference`, `engram.describe_corpus`, and
  `engram.health` with Engram-local `memory.*` capability checks.
- RFC 0044 review, repair, ledger, and final-synthesis artifacts under
  `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/`,
  plus focused-review ledger artifacts that reconcile the RFC 0027/RFC 0028
  checkpoint cleanup without promoting RFC 0028 or accepting D082.
- RFC 0028 predicate-intent surfacing implementation is now present in the
  fresh 2026-05-13 author pass: migration 012 adds nullable
  `predicate_vocabulary.subject_kind_hint`, the extractor prompt version is
  `extractor.v9.d082.predicate-intent`, `build_extraction_prompt` renders
  predicate descriptions and subject-kind hints, and the shared CLI/web
  interview renderer now shows predicate intent, advisory subject-mismatch
  warnings, and the broadened `false` rationale prompt. RFC status remains
  proposal pending fresh review; `D082` is only a proposed prompt-version slot
  reservation, not an accepted promotion decision.
- RFC 0032 completed the independent recovery audit for commit `c4a48ab`
  (suspect autonomous work checkpoint): inventory, provenance audit,
  independent code/design reviews, artifact disposition, final decision, and
  forward-path documentation now live under
  `docs/reviews/rfc0032-suspect-work-audit/`. RFC 0031 is preserved unchanged
  as quarantined historical evidence and superseded by RFC 0032.
- RFC 0030 public-dataset entity grounding exists as proposal-only design
  work, with a dangling-branch audit and operator-driven Striatum review
  scaffold. It is not accepted and has no implementation in the current tree.
- Fresh Striatum rerun scaffolds were added for legitimate RFC 0028 promotion,
  RFC 0029 design/spec/implementation review, Phase 4 multi-lane gate review,
  and pre-suspect RFC 0021/RFC 0027 provenance reruns. A first execution probe
  exposed noninteractive lane commands that could exit without artifacts; those
  probe runs were canceled and the fresh scaffolds now launch Codex, Claude, and
  Gemini in explicit noninteractive write-capable modes. A second probe found
  Gemini's headless trust gate, so the scaffolds now pass `--skip-trust` for
  clean automation worktrees.
- Fresh rerun artifacts now exist for RFC 0021, RFC 0027, RFC 0028, RFC 0029
  design, and the Phase 4 multi-lane gate. The reruns are evidence, not
  promotion authority: RFC 0021, RFC 0027, RFC 0028, and RFC 0029 design all
  surfaced `needs_revision` findings, RFC 0028's Gemini lane was blocked by
  Gemini model-capacity errors, and the Phase 4 multi-lane gate completed as a
  bounded evidence package rather than authorization for full-corpus execution.
- RFC 0044 Engram memory Phase 1 tenant-isolation queue scaffold was added
  under
  `striatum/rfc-0044-engram-memory-phase1-tenant-isolation-2026-05-13/`.
  It validates as a queued Striatum workflow requiring tenant terminology
  before implementation, then capability-boundary tests, independent reviews,
  findings ledger, and final synthesis. No implementation or workflow run was
  started.
- Fresh backlog execution outputs now exist for the RFC 0028 prompt-provenance
  and subject-kind-warning fixes, RFC 0027 web/privacy/session-state fixes,
  RFC 0021 contract revision, RFC 0029 design revision, and Phase 4
  evidence-fix scaffold. Focused re-review artifacts now exist for RFC 0021,
  RFC 0027, RFC 0028, RFC 0029, and the Phase 4 evidence-fix follow-up; they
  are review evidence only and carry no promotion authority.
- Focused recovery/re-review artifacts were added for RFC 0027, RFC 0028, and
  the Phase 4 evidence-fix scaffold under
  `docs/reviews/rerun-backlog-focused-reviews-2026-05-13/` and
  `docs/operations/phase4-build/evidence-fix-2026-05-13/`. RFC 0028's
  prompt-literal repair and RFC 0027's web-state repair now have fresh accepted
  focused re-review evidence, but neither artifact is a promotion decision.
- RFC 0027 implementation: FastAPI + htmx web UI for the gold-set
  interview surface, served by `engram phase3 interview serve` (RFC
  0027 / spec 0027 / D080). Loopback-only with no escape clause;
  Origin-allowlist enforces CSRF posture; Tier 1 ceiling on
  full-message and context routes; vendored htmx (no CDN). Verdict
  commit single-click for `true`/`skip` and two-click rationale-required
  for `false`/`stale`/`unsupported`/`unsure`; the CLI loop continues to
  exist and shares the new `engram.interview.render` helpers landed in
  Pass A. Migration 011 materializes the sampled order at session
  creation so CLI- and web-started sessions are mutually resumable.
  FastAPI / Uvicorn / Jinja2 ship under the `engram[serve]` optional
  extra; headless installs unchanged.
- Origin allowlist on the RFC 0027 web UI is operator-extensible via
  `ENGRAM_INTERVIEW_ALLOWED_ORIGINS` (comma-separated host names,
  appended to the default loopback set) — recorded as **D081**.
  Defaults remain loopback-only; the bind stays loopback-only (D080
  unchanged). The env var only extends which `Origin` header values
  are accepted on POST routes, so a user-space TCP forwarder bridging
  a trusted-network interface (e.g., a Tailscale tailnet) to the
  loopback bind can reach the UI from another device the operator
  controls. The howto guide gains a "Tailnet access" section.
  Non-loopback bind plus token auth remains the F005 follow-on.
- RFC 0024 Phase 4 tiered-gate notes:
  Tier 0 bounded smoke, Tier 1 non-human evidence, Tier 2 bounded
  preflight scaffold, final gate review, and run summary under
  `docs/operations/phase4-build/tiered-gate/`. RFC 0032 reframes these as
  single-lane Codex notes and a truthful Striatum export, not a multi-lane
  RFC 0024 gate verdict. Fresh multi-lane gate evidence now exists under
  `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/` and was
  accepted only as a privacy-safe bounded evidence package. Phase 4 promotion
  and full-corpus authorization remain blocked pending evidence-fix work and
  explicit gate decisions.
- Initial creation of `CHANGELOG.md` based on repository commit history and project phases.
- Mandated `CHANGELOG.md` maintenance in `AGENTS.md` and `GEMINI.md`.
- RFC 0025: Command naming review.
- RFC 0023: Concurrent extraction pipeline via `concurrent.futures`.
- RFC 0022: Server binary with HTTP API and MCP interface.
- RFC 0021: Gold-set interview curation.
- RFC 0021 implementation: migration 010_gold_labels.sql
  (`gold_label_sessions`, `gold_labels`, `gold_label_strata_vocabulary`,
  `gold_label_verdict_vocabulary`, three named triggers
  `fn_gold_labels_append_only` / `fn_gold_labels_validate_target` /
  `fn_gold_labels_carry_privacy_tier`, `current_gold_label` view),
  `src/engram/interview/` Python module (errors, storage, sampler with
  `ENGRAM_GOLD_COOLDOWN_*` env vars, agent), seven phase-scoped CLI
  subcommands under `engram phase3 interview`, seven `phase3-interview-*`
  Make targets, two versioned `prompts/interview/{claim,belief}_v1.md`
  templates per RFC 0017, and 32 new tests covering CLI dispatch, sampler
  determinism, append-only / parent-validation / privacy-tier triggers,
  and migration 010 application.
- Striatum scaffolds at `striatum/rfc-0021-gold-set-review/` (historical
  review workflow: claude / codex / gemini reviewer bylines + ledger +
  synthesis + final review; model-lane provenance pending rerun) and
  `striatum/rfc-0021-gold-set-implementation/` (implement → verify →
  final review code-change run).
- Historical run artifacts at `docs/reviews/rfc0021/` (3 reviews, ledger,
  synthesis, final review, evidence, run summary, coordinator-continue
  decision; independent lane bylines later found unattested)
  and `docs/reviews/rfc0021-gold-set-implementation/` (handoff,
  verification report, final review, evidence, run summary).
- Operator guide for the gold-set interview surface at
  `docs/howto/gold-set-interview.md` (six-verdict glossary, cooldown
  defaults table + env vars, fail-closed Tier 1 export ceiling, v1
  Python harness for verdict capture until the interactive loop lands,
  trigger-error troubleshooting, cold-start clone+install
  prerequisites). README points at the guide instead of inlining the
  example commands.
- RFC 0027: Interview web UI proposal (FastAPI + Jinja2 + htmx,
  loopback-only, in-process Origin-allowlist CSRF posture).
- Spec 0027 at `docs/specs/0027-interview-web-ui-spec.md` (1230-line
  implementation contract; RFC 0027 promoted via D080).
- Striatum scaffold at `striatum/rfc-0027-interview-web-ui-review/`
  for the historical interview-web review workflow (claude / codex / gemini
  reviewer bylines + ledger + synthesis + final review; model-lane provenance
  pending rerun).
- Historical run artifacts at `docs/reviews/rfc0027/` (3 reviews, ledger with
  29 findings — 2 blocking + 19 major + 7 minor + 1 nit, synthesis
  recommending revise-rfc with full spec deltas, final review
  `accept_with_findings`, evidence + run summary; independent lane bylines
  later found unattested).
- `.claude/skills/` populated by `striatum skills install --profile
  claude_code --scope project` (5 lazily-loadable skills:
  striatum-workflow, striatum-scaffold, striatum-claim-loop,
  striatum-supervise, striatum-recover; striatum 1.1.0).
- RFC 0018: Evidence-to-claim audit schema.
- Phase 4 spec review scaffolding and smoke build.
- RFC 0024 Phase 4 Tier 0-2 Striatum gate scaffold.
- Extraction backend benchmark harness.
- Phase 2/3 pipeline smoke tests.
- CLI tests and lint targets.
- Token budget helper tests.
- RFC 0015 gap coverage tests.

### Changed
- RFC 0032 cleanup quarantines the suspect RFC 0028/RFC 0029 review
  directories and RFC 0029 Striatum scaffolds, demotes RFC 0028/RFC 0029
  status claims back to proposal/draft, and removes the unauthorized
  RFC 0028/RFC 0029 decision row. It also removes the stale root-level
  Striatum 1.14 guide files. Existing code remains reviewable implementation
  work, not decision authority.
- RFC 0028 predicate-intent surfacing is now `proposal` / `implemented`: the
  implementation is present and focused tests pass, while acceptance and any
  decision-log promotion remain pending fresh legitimate review.
- RFC 0029 bench triage workbench is reset to `proposal` / `none` and revised
  as design-only scratch tooling. Focused re-review accepted the revised
  design, but no implementation is present or promoted.
- Pre-suspect RFC 0021/RFC 0027 review artifacts are now marked for
  provenance rerun because their multi-lane bylines are not backed by
  Striatum process execution evidence in `.striatum/state.sqlite3`.
- Bench-review workbench host validation now rejects non-loopback configured
  hosts at app creation, requires explicit
  `ENGRAM_BENCH_REVIEW_ALLOWED_DNS_SUFFIXES` opt-in for tailnet DNS suffixes,
  and narrows status/export CLI exception handling to expected storage,
  artifact, export, and filesystem errors.
- Phase 3 interview sessions now persist active-learning enablement in local
  Postgres, stamp the signal onto materialized targets and labels, support
  `start --strata key=value,...`, enforce the default three-reask cap, honor
  `history --since`, and let CLI `resume` continue open materialized sessions.
- The interview web UI now checks all evidence rows on "show all", rejects
  blank rationales server-side for rationale-required verdicts, preserves
  materialized target confidence in resumed headers, and prevents message
  routes from rendering conversations that are not reachable from the session's
  cited evidence.
- The RFC 0027 interview web/storage surface now rejects closed-session resume
  and mutation paths, enforces the parent-target Tier 1 ceiling for
  `evidence/all`, bases completion on remaining frozen version-matching targets
  rather than URL position, reports progress from the same frozen predicate, and
  returns a diagnostic for targetless open sessions that require explicit
  abandon.
- RFC 0028's governed `extractor.v9.d082.predicate-intent` prompt artifact now
  stores the rendered runtime zero-claim JSON literal (`{"claims":[]}`) instead
  of f-string escaped braces; focused tests pin both the file artifact and
  runtime prompt behavior.
- Project Striatum workflow skill bundles for Codex and Claude were refreshed
  from Striatum `1.14.0` templates to the Engram venv's `striatum 1.37.0`
  templates, including the new MCP helper skill.
- Added phase-scoped `engram phase3 re-extract` / `make phase3-re-extract`
  surfaces and marked the top-level `engram re-extract` command as legacy,
  aligning RFC 0017 re-extraction with the RFC 0025/D078 command naming
  contract.
- Phase 4 accept/reject/promote-to-pinned review actions now refresh the
  `current_beliefs` materialized view before returning, so callers no longer
  need a separate refresh to observe review-queue changes.
- `make phase3-interview-serve` now passes `ENGRAM_DATABASE_URL`, matching
  the other database-aware interview targets.
- Moved Phase 4 spec review into `striatum/`.
- Wired Striatum for Phase 4 multi-agent review.
- Retired operational markers (D074) in favor of Striatum SQLite state.
- Implemented RFC 0014 (Ops Home) and RFC 0017 (Parts 2/3).
- Implemented RFC 0007: Artifact ID and subref model.
- Tracking RFC implementation status in index.
- Accepted RFC 0025 as the phase-scoped operator command-surface contract:
  legacy bare mutating commands warn then get removed, and Phase 1 ingest
  commands move under `engram phase1`.
- Implemented the first RFC 0025 command-surface slice: phase-scoped CLI
  commands, phase-scoped Make targets, and fail-closed generic `pipeline`
  commands.
- Historical RFC 0021 (gold-set interview curation) review artifacts are
  preserved as provenance, but they are not authoritative independent
  multi-lane evidence until superseded by fresh reruns because their lane
  bylines are unattested. The historical synthesis recommended
  revise-rfc with 24 ledger findings (3 blocking, 15 major, 5 minor, 1
  nit); 23 accepted deltas were applied to the RFC text (typed claim and
  belief version triples, append-only and parent-validation triggers,
  `gold_label_sessions` parent table, fail-closed Tier 1 export ceiling,
  phase-scoped CLI under `engram phase3 interview`, opt-in active-learning
  bias, per-stability-class cooldown defaults, separated `evidence_excerpt`
  for redaction, six-verdict vocabulary table, typed strata columns).
  Recorded as **D079**; BUILD_PHASES gains a `PHASE-0003-FOLLOWON`
  index entry and a Phase 3 follow-on section. Migration filename
  renumbered from `008` to `010_gold_labels.sql`. Implementation final
  review and verification both returned `accept_with_findings`; the
  deferred `fn_gold_labels_block_synthetic_audit_input` D044-foothold
  trigger and the (since-fixed) missing
  `phase3-interview-enable-active-learning` Make target are documented
  as the only residual gaps.
- Historical RFC 0027 (interview web UI) review artifacts are preserved as
  provenance, but they are not authoritative independent multi-lane evidence
  until superseded by fresh reruns because their lane bylines are unattested.
  The historical synthesis recommended `revise-rfc`; 29 accepted deltas
  applied to the RFC text and consolidated into the buildable spec at
  `docs/specs/0027-interview-web-ui-spec.md`. Recorded as **D080**;
  BUILD_PHASES Phase 3 follow-on gains a web-UI subsection. Blocking
  findings resolved: fictional `striatum serve` precedent replaced
  with RFC 0022 (`engramd`) as the actual D020 anchor, and the
  RFC 0022 parallel-surface concern resolved via an explicit
  forward-compat path (when `engramd` lands, web routes migrate from
  direct module calls to `engramd` HTTP endpoints).
- Documented corrected RFC 0023 slot-aware extraction benchmark findings:
  1 worker / 1 server slot = 546.90s, 2 / 2 = 226.44s, 4 / 4 = 190.84s, and
  8 / 8 = 522.19s on the 20-segment slice.
- Selected the local `ik_llama` extraction service setting to validate next:
  `--parallel 4 --ctx-size 131072 --metrics`, yielding four 32,768-token
  server slots for the Qwen3.6-35B-A3B-IQ4_XS local model.

### Fixed
- Repaired the RFC 0044 single-pair memory serving authorization boundary:
  `MemoryService.search`, `MemoryService.fetch_reference`, and MCP tool calls
  now require `memory.read_cross_corpus` for a secondary Striatum corpus and
  `memory.read_cross_tenant` for a non-primary tenant even when the token lists
  the target pair as visible. Added service-path and MCP-handler regressions.
- Hardened extraction benchmark reporting.
- Closed Phase 3 validation repair failures.
- Ignored `llama.log` local model output.
- Corrected the RFC 0023 Phase 1A speed conclusion: the initial 100-slice run
  used a single-slot `ik_llama` server and is retained only as
  dispatcher/idempotency stress evidence, not as a concurrency speed result.
- Added the `phase3-interview-enable-active-learning` Make target,
  closing finding A010 from the RFC 0021 implementation final review.
- Clarified the gold-set interview guide's prerequisites: stated that
  all commands run from the engram repo root, added the cold-start
  `git clone` → `cd engram` → `make install` → `make migrate` sequence,
  and explained the `.venv/bin/engram` vs activated-venv invocation.

## [striatum-extraction-2026-05-07] - 2026-05-07

### Added
- Phase 3: Claim extraction and bitemporal beliefs pipeline (RFC 0011).
- Agent Runner V1 MVP.
- RFC 0014: Agent Runner validation and dogfooding fixes.
- RFC 0012: Python agentic coding standard.
- Durable runner state evidence.
- Agent runner tmux design and automation helpers.
- Phase 3 agent runbook and prompts.

### Changed
- Promoted RFC 0014 operational artifact home.
- Defined RFC to spec promotion process.
- Generalized system paths and established project instructions (`AGENTS.md`).
- Refreshed README and artifact bylines.
- Normalized RFC status headers.
- Pin Phase 3 agents to specific models (Gemini Pro Preview, GPT-5.5, Claude Opus).

### Fixed
- Phase 3 schema rejections and null-object extraction repairs.
- Consolidator null group keys.
- Swapped UUIDs in span-expansion audit and Qwen 27B A/B prompt.
- Agent runner review gates and one-shot prompts.

## [Phase 2] - 2026-05-02

### Added
- Implementation of Phase 2 segmentation and embeddings pipeline.
- Segmentation benchmark harness, visualization, and reporting.
- Early-signal benchmark for segmentation.
- Distributed segmenter leasing RFC.
- Supervisor terminology and controller RFCs.
- `UBIQUITOUS_LANGUAGE` glossary.
- Deterministic local LLM request profile documentation.
- Schema visualization via Mermaid ER diagram.

### Changed
- Hardened segmenter runs with socket timeouts, request deadlines, and error diagnostics.
- Segmenter now retries and splits oversized windows.
- Committed pipeline progress per batch.
- Reorganized repository structure (moved many markdown files from root).

### Fixed
- Constrained segmenter message IDs to the active window schema.

## [Phase 1.5] - 2026-04-30

### Added
- Pre-Phase-2 adversarial gate (D026) synthesis.
- Claude.ai export ingestion.
- Gemini Takeout ingestion.
- Cleanup and multi-source ingestion refinements.

## [Phase 1] - 2026-04-26..2026-04-28

### Added
- Raw evidence layer and initial ingestion pipeline.
- Initial specification for stash-ingest pipeline.
- Foundational principles, README, SPEC.md, and ROADMAP.md.
- Multi-AI design review orchestration artifacts.

### Changed
- Refined V1 architecture based on iterative multi-agent reviews (Claude, Codex, Gemini, Qwen).
- Consolidated `consolidation_progress` table into Phase 1 schema baseline.
- Formalized BUILD_PHASES.md.
