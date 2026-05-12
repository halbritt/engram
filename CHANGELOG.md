# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (informally, as it follows project phases).

## [Unreleased]

### Added
- RFC 0035 provenance-recovery proposal: extends RFC 0031's one-burst
  audit to the entire suspect process window in which autonomous
  agents fabricated review bylines, bypassed the Striatum workflow
  contract (D074), collapsed originator / reviewer / implementer
  roles into one execution context, and left no mechanical link
  from artifact text to Striatum evidence. Proposes a single
  load-bearing disposition ledger keyed on RFC 0031's vocabulary
  (accept / repair / quarantine / supersede / revert), a three-pass
  backward audit (inventory → Striatum cross-reference →
  independent re-review with operator signoff), three forward
  enforcement layers (byline attestation, workflow attestation,
  role-separation enforcement, all gated by `make check-provenance`),
  and explicit sunset criteria. Promotion of in-window RFCs / `D###`
  decisions / specs is paused until disposition lands; operation of
  shipped code is not paused. RFC 0034's Striatum-tenant ingest is
  the recovery's first real `context_for` consumer ("which review
  artifacts cite a workflow with no matching Striatum row?").
  Self-bootstrap rule: the recovery RFC and its decisions are
  operator-authored and operator-signed, since the same failed
  process cannot bless its own outputs as recovered.
- RFC 0034 generalized-memory-scope proposal: holds the
  personal-biography mission as load-bearing while reframing engram
  as a general memory architecture and adopting Striatum as the
  first dogfood tenant alongside the personal corpus (via RFC 0033
  tenant isolation). Software-development memory is grounded in
  commits, decision logs, RFCs, and Striatum SQLite state, so most
  claims are mechanically derivable and verifiable — giving a fast
  path to a real PHASE-0005 serving surface and an evaluation
  harness that lifts back into the personal tenant. Local-first and
  the biography mission stay verbatim; explicit kill criteria
  guard against scope drift.
- RFC 0033 tenant isolation proposal: schema-per-tenant within one
  Postgres database, with a shared `engram_common` schema for
  reference data and a `search_path`-scoped `connect()`. Lets
  multiple engram instances co-locate on one host and one cluster
  without cross-tenant contamination, under the explicit threat
  model that all tenants share root authority (hygiene isolation,
  not hostile-tenant defense). Includes migration-runner extension,
  CLI / Makefile `--tenant` / `TENANT=` plumbing, and per-tenant
  Striatum / operations-artifact / export-blob layout.
- RFC 0032 Claude Code session history ingest proposal: pulls
  `~/.claude/projects/` `.jsonl` transcripts from every host via an
  rsync-to-proximal mirror, then ingests them through a new
  `claude_code_sessions` ingester onto the existing
  `sources`/`conversations`/`messages` tables (new `source_kind =
  'claude_code'` via a follow-on migration), so Claude Code becomes
  a first-class memory source alongside the Claude desktop export,
  ChatGPT export, and Gemini export, and so engram retains sessions
  past Claude Code's silent pruning.
- RFC 0031 suspect autonomous work audit proposal: marks the recent
  autonomous RFC 0028 / RFC 0029 / Striatum-driven checkpoint as suspect
  pending provenance, byline, code, benchmark, and artifact-disposition
  review before further promotion.
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
- RFC 0028 / D082 implementation slice: migration 012 adds nullable
  `predicate_vocabulary.subject_kind_hint` metadata and seeds the
  existing vocabulary; the extractor prompt version bumps to
  `extractor.v9.d082.predicate-intent` and renders predicate
  descriptions plus subject-kind hints; interview CLI/web rendering now
  places predicate intent on its own line, adds a local heuristic warning
  for obvious subject/predicate mismatches, and broadens the `false`
  rationale prompt beyond "correct value." No claims, beliefs, or
  gold-label row contracts change, and full-corpus re-extraction remains
  gated on a bounded bench.
- RFC 0029 bench triage workbench proposal and Striatum design workflow:
  a local-only FastAPI/Jinja2/htmx UI proposal for reducing cognitive
  overhead when validating extraction/re-extraction benchmark deltas.
  The completed review run includes Claude/Codex/Gemini lanes plus an
  adversarial usability review; accepted findings tightened segment
  data-availability semantics, full prior version identity, CLI-only
  redacted export, RFC 0027-style local web security, promotion readiness,
  resume state, and UI contract tests.
- Spec 0029 and Striatum spec workflow for the bench triage workbench:
  promotes RFC 0029 into a buildable implementation contract covering
  artifact inputs, data-availability states, classification tags,
  scratch SQLite review state, CLI commands, loopback-only web routes,
  redacted exports, and focused acceptance tests.
- RFC 0029 implementation: `engram phase3 bench-review serve|status|export`,
  `src/engram/bench_review/` FastAPI/Jinja2 workbench, scratch SQLite review
  state, deterministic artifact normalization, redacted Markdown exports,
  loopback/cross-origin guards, and focused loader/storage/export/web/CLI tests.
- RFC 0024 Phase 4 tiered gate execution artifacts:
  Tier 0 bounded smoke, Tier 1 non-human evidence, Tier 2 bounded
  preflight scaffold, final gate review, and run summary under
  `docs/operations/phase4-build/tiered-gate/`. The gate remains
  blocked on human-labeled entity precision/recall and review-queue UX
  evidence before any full-corpus Phase 4 promotion.
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
- Striatum scaffolds at `striatum/rfc-0021-gold-set-review/` (multi-agent
  review run: claude / codex / gemini reviewers + ledger + claude
  synthesis + codex final review) and
  `striatum/rfc-0021-gold-set-implementation/` (implement → verify →
  final review code-change run).
- Run artifacts at `docs/reviews/rfc0021/` (3 reviews, ledger, synthesis,
  final review, evidence, run summary, coordinator-continue decision)
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
  driving the multi-agent review run (claude / codex / gemini reviewers
  + ledger + claude synthesis + codex final review).
- Run artifacts at `docs/reviews/rfc0027/` (3 reviews, ledger with 29
  findings — 2 blocking + 19 major + 7 minor + 1 nit, synthesis
  recommending revise-rfc with full spec deltas, final review
  `accept_with_findings`, evidence + run summary).
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
- Accepted RFC 0021 (gold-set interview curation) after Striatum-orchestrated
  multi-agent review (claude/codex/gemini reviewers + ledger + synthesis +
  final review; root-review needs_revision verdicts resolved through a
  recorded coordinator continue-decision). The synthesis recommended
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
- Promoted RFC 0027 (interview web UI) to spec 0027 after a second
  Striatum-orchestrated multi-agent review. Synthesis recommended
  `revise-rfc`; 29 accepted deltas applied to the RFC text and
  consolidated into the buildable spec at
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
- SWAPPED UUIDs in span-expansion audit.
- Swapped consolidator null group keys.
- Swapped message IDs constraint to window schema.

## [Phase 1.5] - 2026-04-30

### Added
- Pre-Phase-2 adversarial gate (D026) synthesis.
- Claude.ai export ingestion.
- Gemini Takeout ingestion.
- Cleanup and multi-source ingestion refinements.

## [Phase 1] - 2026-03-15

### Added
- Raw evidence layer and initial ingestion pipeline.
- Initial specification for stash-ingest pipeline.
- Foundational principles, README, SPEC.md, and ROADMAP.md.
- Multi-AI design review orchestration artifacts.

### Changed
- Refined V1 architecture based on iterative multi-agent reviews (Claude, Codex, Gemini, Qwen).
- Consolidated `consolidation_progress` table into Phase 1 schema baseline.
- Formalized BUILD_PHASES.md.
