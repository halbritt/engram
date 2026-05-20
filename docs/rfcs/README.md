# RFCs

RFCs are proposal documents for ideas that may become accepted decisions later.
They are not binding until promoted into `DECISION_LOG.md`, `BUILD_PHASES.md`,
a phase prompt, or an accepted spec named by a recorded project decision.

When an RFC produces an accepted spec handoff, mark the RFC `promoted` or
`superseded`, link to the accepted spec, and target future implementation work
at the spec. The RFC remains provenance; it should not keep being reviewed as
the implementation contract.

The **Status** column tracks document state (proposal / specified / accepted /
accepted_as_design_reference / promoted / superseded). The **Implementation** column tracks whether the
proposal's deliverables exist in the codebase as of the last index sweep
(2026-05-19): `implemented`, `partial`, `none`, or `n/a` for idea-capture docs
without a concrete code deliverable. Implementation status is descriptive, not
prescriptive — a `none` here is not a TODO unless promoted via
`BUILD_PHASES.md` or `DECISION_LOG.md`.

| RFC | Status | Implementation | Topic |
|-----|--------|----------------|-------|
| [0001](0001-supervisor-controller-loop.md) | proposal | none | Supervisor controller loop |
| [0002](0002-prior-art-ideas.md) | proposal | n/a | Prior-art ideas to revisit |
| [0003](0003-segmenter-soc.md) | proposal | none | Segmenter separation of concerns |
| [0004](0004-segmenter-work-boundary.md) | proposal | partial | Segmenter worker boundary |
| [0005](0005-supervisor-event-triggers.md) | proposal | none | Supervisor event triggers and queue prioritization |
| [0006](0006-segmentation-model-benchmark.md) | specified | implemented | Public-first segmentation model benchmark |
| [0007](0007-artifact-id-and-subref-model.md) | promoted | implemented | Artifact ID and subref model |
| [0008](0008-segmentation-benchmark-early-signal.md) | specified | implemented | Segmentation benchmark early-signal revision |
| [0009](0009-distributed-segmenter-work-leasing.md) | proposal | partial | Distributed segmenter work leasing |
| [0010](0010-segmenter-server-throughput-profile.md) | proposal | partial | Segmenter server throughput profile |
| [0011](0011-phase-3-claims-beliefs.md) | proposal | implemented | Phase 3 claims and bitemporal beliefs |
| [0012](0012-python-agentic-coding-standard.md) | proposal | partial | Python agentic coding standard |
| [0013](0013-development-operational-issue-loop.md) | superseded | n/a | Development operational issue loop |
| [0014](0014-operational-artifact-home.md) | accepted | implemented | Operational artifact home (markers retired by D074) |
| [0015](0015-test-coverage-improvements.md) | proposal | partial | Test coverage improvements |
| [0016](0016-context-lane-reranker-slot.md) | proposal | none | Context lane reranker slot |
| [0017](0017-extraction-prompt-versioning.md) | proposal | implemented | Extraction prompt versioning and cross-corpus dry-run |
| [0018](0018-evidence-to-claim-audit-cascade.md) | accepted | partial | Evidence-to-claim audit cascade |
| [0019](0019-extraction-batching-server.md) | proposal | partial | Continuous-batching inference server for Phase 3 claim extraction |
| [0020](0020-segmentation-batching-server.md) | proposal | none | Continuous-batching inference server for Phase 2 segmentation |
| [0021](0021-gold-set-interview-curation.md) | accepted | partial | Gold-set interview curation |
| [0022](0022-server-binary-api-mcp.md) | proposal | none | Server binary with HTTP API and MCP interface |
| [0023](0023-concurrent-extraction-pipeline.md) | draft | none | Concurrent extraction pipeline via Python concurrent.futures |
| [0024](0024-phase-4-pre-full-corpus-benchmark-gate.md) | accepted | partial | Phase 4 pre-full-corpus benchmark gate |
| [0025](0025-phase-scoped-command-names.md) | accepted | partial | Phase-scoped command names |
| [0027](0027-interview-web-ui.md) | promoted | scaffolded | Interview web UI (promoted to [spec 0027](../specs/0027-interview-web-ui-spec.md) via D080) |
| [0028](0028-predicate-intent-surfacing.md) | proposal | implemented | Predicate-intent surfacing across extraction and interview |
| [0029](0029-bench-triage-workbench.md) | proposal | none | Bench triage workbench for extraction/re-extraction validation (fresh design review pass; prior review chain quarantined by [RFC 0032](0032-suspect-autonomous-work-recovery.md)) |
| [0030](0030-public-dataset-entity-grounding.md) | proposal | none | Public-dataset entity grounding for claim extraction |
| [0031](0031-suspect-autonomous-work-audit.md) | superseded | none | Suspect autonomous work audit (authored inside the suspect commit; superseded by [RFC 0032](0032-suspect-autonomous-work-recovery.md)) |
| [0032](0032-suspect-autonomous-work-recovery.md) | proposal | none | Recovery and audit of the suspect autonomous work checkpoint |
| [0033](0033-multimodal-observation-layer.md) | proposal | none | Multimodal observation layer |
| [0034](0034-photo-library-ingestion.md) | proposal | none | Photo library ingestion and local vision derivations |
| [0035](0035-location-timeline-place-model.md) | proposal | none | Location timeline and place model |
| [0036](0036-daily-biography-compiler.md) | proposal | none | Daily biography compiler |
| [0037](0037-outputguard-segmentation-structured-output.md) | proposal | none | OutputGuard for segmentation structured output |
| [0038](0038-operator-ui-rework.md) | proposal | none | Operator UI rework for interview and bench-review surfaces |
| [0045](0045-striatum-corpus-contract-v2.md) | proposal | none | Striatum Corpus Contract V2 |
| [0046](0046-striatum-projection-index-schema.md) | accepted_as_design_reference | landed via Layers 1-5 of `STRIATUM_MEMORY_E2E_BACKLOG.md` (migration 015, `MemoryService`) | Engram Striatum projection and index schema |
| [0047](0047-striatum-retrieval-augmentation-boundary.md) | accepted_as_design_reference | landed via `MemoryService.search` filters.exact_refs | Striatum retrieval augmentation boundary |
| [0048](0048-striatum-context-injection-policy.md) | accepted_as_design_reference | landed via `MemoryService.build_packet`, `engram.build_packet` MCP tool, `striatum_packet_audits` | Striatum context-injection policy |
| [0049](0049-striatum-evaluation-gates.md) | accepted_as_design_reference | landed in part via `make eval-gates`; full gate matrix is incremental | Striatum evaluation, no-egress, and retrieval-quality gates |
| [0050](0050-source-ingestion-expansion.md) | accepted_as_design_reference | landed via Layers 1-6 of `SOURCE_INGESTION_BACKLOG.md` (migrations 017-020) | Source-ingestion expansion and source-contract template |
| [0051](0051-generic-evidence-reference-index.md) | accepted_as_design_reference | partial (migration 022, generic backfill/search substrate) | Generic evidence and reference index |
| [0052](0052-entity-identity-review-and-grounding.md) | accepted_as_design_reference | partial (migration 023, local MCP grounding lookup substrate) | Entity identity review and grounding |
| [0053](0053-claim-extraction-grounding-boundary.md) | proposal | partial (request/response/network-dispatch schemas, validators, sidecar migration/helpers, grant lifecycle/product CLI, disabled extraction sidecars, constrained generic HTTP/Tavily adapter scaffolds, broker credential tests, synthetic/runtime e2e; no default live provider) | Claim extraction grounding boundary |
| [0054](0054-entity-grounding-batch-workflow.md) | proposal | implemented (batch worker, CLI seam, and runtime gate coverage present) | Entity grounding batch workflow |
| [0055](0055-grounding-evidence-materialization.md) | proposal | implemented (materializer, broker-DSN CLI seam, and runtime gate coverage present) | Grounding evidence materialization |

Index note: RFC 0045 stays proposal-only. RFC 0046-0052 are accepted as
the design reference for their respective implementation lanes per
[D083](../../DECISION_LOG.md#d083), [D084](../../DECISION_LOG.md#d084), and
[D094](../../DECISION_LOG.md#d094).
RFC 0053 remains proposal-only; it documents the missing extractor/grounder
boundary, including a constrained network-capable broker contract. The current
code scaffolds persisted grants, a CLI grant lifecycle, disabled extraction
sidecars, credential tests, and disabled configured generic HTTP/Tavily adapter
scaffolds, but does not enable a default live provider or allow the extractor to
use network.
Its 2026-05-18 Striatum review accepted blockers around exact entity-surface
network queries, persisted grants, broker credential separation, sidecar/audit
persistence, and a dedicated claim-grounding gate before extraction output may
depend on grounding. The starter gates are `make e2e-claim-grounding-synthetic`
and `make e2e-claim-grounding-runtime`.
RFC 0054 and RFC 0055 split the next entity-wide grounding workflow into a
draft-only batch selection/grant flow and a separate approved-grant
materialization flow that must write local grounding evidence before responses
or review actions consume provider rows. The operator command names are wired as
`engram entity-grounding draft` and `engram entity-grounding process-approved`;
both dispatch lazily to the dedicated implementation modules and sanitize JSON
output so provider secrets are not displayed. The 2026-05-19 Striatum run added
post-review hardening for byte-exact entity-surface queries, broker-DSN
materializer authority, materializer-side public URL filtering, and
privacy-tier preservation on evidence-attachment review actions.
Acceptance as design reference does not freeze the proposal text against
future implementation drift — when code diverges, the RFC text gets a
patch, not a new acceptance.

## Implementation notes

- **0007** — promoted via D068 to spec at `docs/process/artifact-id-conventions.md`.
  RFC headers, file-level anchors, `D###` row anchors in `DECISION_LOG.md`,
  `PHASE-####` anchors in `BUILD_PHASES.md`, `REVIEW-####` registry at
  `docs/artifacts/review-id-registry.md`, prompt status headers, and the local
  reference checker at `scripts/check_artifact_refs.py` (`make check-refs`)
  all landed in the same sweep. Existing `D###` IDs stay canonical; no file
  renames.
- **0002** — non-implementable as a single deliverable; constituent ideas land
  separately (e.g. dimension-flexible embeddings via D033, predicate vocabulary
  via D046/D057). Marked `n/a` in the table.
- **0004** — `segment_conversation()` accepts explicit `prompt_version` /
  `model_version` and stamps `SEGMENTER_REQUEST_PROFILE_VERSION` on payloads;
  segmenter still calls `upsert_progress()` directly, so the supervisor seam
  from §3.1 is unfinished.
- **0006 / 0008** — benchmark harness lives in `benchmarks/segmentation/`;
  Tier 0/1 verdicts (D041/D042) are operational; Tier 2 decision-grade run
  pending per `SPEC.md`.
- **0009** — leasing schema present in `agent-runner/` for job orchestration,
  not Engram parent-level work division. Not required for current Phase 2.
- **0010** — tiered model-selection gate is wired (D042); the server-flag
  microbenchmark ladder (ubatch 256→2048, parallel slots, q8 KV) is not
  exercised in code.
- **0011** — full schema landed in `migrations/006_claims_beliefs.sql`;
  extractor, consolidator, transitions, and tests in place; D043–D047 accepted.
- **0012** — Phase 0 wired (2026-05-07): ruff and pyright pinned in
  `pyproject.toml` with permissive baselines, `make lint`, `make format`,
  `make typecheck` targets in place. Baseline scan: 211 ruff findings (107
  E501 line-too-long, 46 RUF059, 23 I001, balance smaller categories) and
  51 pyright errors at `typeCheckingMode = "basic"`. Phase 1 (green-on-touch),
  Phase 2 (bounded sweeps), and Phase 3 (gate) follow incrementally per the
  RFC's adoption plan.
- **0013** — superseded by D074 (2026-05-07): the marker mechanism is
  retired in favor of Striatum SQLite as the authoritative gate state.
  The redaction and report-layout guidance carries forward via
  `docs/process/operational-artifact-home-spec.md`. Legacy Phase 3 markers
  under `docs/reviews/phase3/postbuild/markers/` are preserved as audit
  provenance; `scripts/phase3_tmux_agents.sh` continues to scan them so
  in-flight Phase 3 gates remain operational.
- **0014** — directory home populated 2026-05-07; amended same day by
  D074: `docs/operations/<area>/<loop>/reports/` stays as the canonical
  destination for redacted operational reports, but the `markers/` subtree
  is retired. Striatum SQLite (`.striatum/state.sqlite3`) is now the
  authoritative gate state. The privacy carry, the directory layout
  (S001–S005, S008, S009 of the spec), and the legacy-marker preservation
  rule all stand unchanged. Striatum is wired in via `make
  install-striatum` / `make striatum-init`; Phase 4 multi-agent review
  workflow lives at `striatum/phase-4-spec-review/workflow.json` (validates clean
  against `striatum.workflow.v1`). See `docs/process/multi-agent-review-
  loop.md` § Striatum-orchestrated reviews.
- **0015** — top-priority gaps and most secondary gaps landed 2026-05-07:
  `tests/test_cli.py` (16 tests, all CLI subcommands except `pipeline-3`),
  `tests/test_canonicalize_and_sanitize.py` (44 tests locking
  `canonicalize_embeddable_text` and the `sanitize_*` family),
  `tests/test_embedder_http_errors.py` (11 tests, mocked HTTP error paths),
  `tests/test_gemini_html.py` (26 tests on `TextHTMLParser` + activity-id
  helpers), `tests/test_progress.py` (9 tests on `upsert_progress`),
  `tests/test_token_budget.py` (19 tests on context-budget math), and
  `tests/test_pipeline_smoke.py` (1 compound 3-conversation e2e wiring
  test). Total +126 tests; full suite 283 passed in 72s. Gaps 6 (loader
  helpers, three loaders) and 7 (migration safety, touches conftest)
  deferred as follow-ups.
- **0017** — fully implemented 2026-05-07. Part 1 versioning contract was
  already live (`EXTRACTION_PROMPT_VERSION` in `src/engram/extractor.py`).
  Part 2: `engram phase3 re-extract --version <new>` CLI subcommand with
  `--dry-run`, `--limit`, `--source-id`, `--batch-size`, `--diff-sample`;
  reuses the existing per-segment extraction path, preserves prior claim
  rows, reports row counts / coverage gaps / sample diffs; consolidation is
  intentionally NOT auto-triggered. Part 3: `scripts/cross_corpus_dryrun.py`
  harness with `--self-test` mode, plus the findings template at
  `docs/reviews/phase3/PHASE_3_CROSS_CORPUS_DRYRUN_TEMPLATE.md`. Privacy
  contract enforced via tests — no raw corpus content reaches committed
  findings docs.
- **0018** — schema-level adoption landed 2026-05-07:
  `migrations/007_claim_audits.sql` creates `audit_reason_vocabulary` (13
  reasons seeded; `trace_broken` / `evidence_synthesized` /
  `predicate_misrouted` flagged `precludes_supported`), `claim_audits`, and
  `projection_audits`, all append-only with stage/verdict and per-row
  reason validation triggers. D069–D073 record the five proposed decisions.
  Reviewer LLM-calling code is **not** built — per RFC §Promotion Path,
  the cascade build prompt is scheduled post-Step-5 (gold-set authoring).
- **0019** — benchmark-only extraction backend harness lives in
  `benchmarks/extraction/`. It can create fixed active-segment slices, smoke a
  loopback OpenAI-compatible endpoint, run concurrent scratch-only extraction
  requests, and compare control/candidate artifacts. Production extraction
  remains on the current request profile until benchmark evidence is promoted
  through `DECISION_LOG.md` and RFC 0017 re-extraction handling.
- **0028** — owner-directed implementation landed in a fresh 2026-05-13 pass:
  migration 012 adds nullable `predicate_vocabulary.subject_kind_hint`; the
  extractor runtime vocabulary and Phase 3 schema preflight compare
  `description` plus `subject_kind_hint`; `EXTRACTION_PROMPT_VERSION` is
  `extractor.v9.d082.predicate-intent`; extraction prompts render an
  `intent:` line per predicate; shared CLI/web interview rendering shows
  predicate intent on its own line, adds advisory subject-kind mismatch
  warnings, and broadens the `false` rationale prompt. Status remains
  `proposal` until fresh review accepts or revises promotion; no decision row
  is recorded by the implementation pass.
