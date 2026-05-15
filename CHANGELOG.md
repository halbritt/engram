# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (informally, as it follows project phases).

## [Unreleased]

### Added
- RFC 0050 source-ingestion expansion proposal landed via multi-lane research
  workflow (claude/codex/gemini drafts, codex prior-art research, claude
  privacy + gemini project-judgment reviews, codex findings ledger and
  synthesis). Output is proposal-status; acceptance is a separate operator
  decision.
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
