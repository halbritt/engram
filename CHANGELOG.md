# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (informally, as it follows project phases).

## [Unreleased]

### Added
- Initial creation of `CHANGELOG.md` based on repository commit history and project phases.
- Mandated `CHANGELOG.md` maintenance in `AGENTS.md` and `GEMINI.md`.
- RFC 0025: Command naming review.
- RFC 0023: Concurrent extraction pipeline via `concurrent.futures`.
- RFC 0022: Server binary with HTTP API and MCP interface.
- RFC 0021: Gold-set interview curation.
- RFC 0021 implementation: migration 010_gold_labels.sql, src/engram/interview module, engram phase3 interview CLI subcommands, prompts/interview/ templates, and focused tests.
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
  final review). Synthesis-driven RFC revision incorporated 23 deltas
  (typed version triple, append-only and parent-validation triggers,
  `gold_label_sessions` parent table, fail-closed Tier 1 export ceiling,
  phase-scoped CLI under `engram phase3 interview`, opt-in active-learning
  bias). Recorded as **D079**; BUILD_PHASES gains a Phase 3 follow-on
  section.
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
