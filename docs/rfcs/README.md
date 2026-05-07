# RFCs

RFCs are proposal documents for ideas that may become accepted decisions later.
They are not binding until promoted into `DECISION_LOG.md`, `BUILD_PHASES.md`,
a phase prompt, or an accepted spec named by a recorded project decision.

When an RFC produces an accepted spec handoff, mark the RFC `promoted` or
`superseded`, link to the accepted spec, and target future implementation work
at the spec. The RFC remains provenance; it should not keep being reviewed as
the implementation contract.

The **Status** column tracks document state (proposal / specified / accepted /
promoted / superseded). The **Implementation** column tracks whether the
proposal's deliverables exist in the codebase as of the last index sweep
(2026-05-07): `implemented`, `partial`, `none`, or `n/a` for idea-capture docs
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
| [0013](0013-development-operational-issue-loop.md) | accepted | partial | Development operational issue loop |
| [0014](0014-operational-artifact-home.md) | proposal | partial | Operational artifact home (spec handoff) |
| [0015](0015-test-coverage-improvements.md) | proposal | none | Test coverage improvements |
| [0016](0016-context-lane-reranker-slot.md) | proposal | none | Context lane reranker slot |
| [0017](0017-extraction-prompt-versioning.md) | proposal | partial | Extraction prompt versioning and cross-corpus dry-run |
| [0018](0018-evidence-to-claim-audit-cascade.md) | proposal | none | Evidence-to-claim audit cascade |
| [0019](0019-extraction-batching-server.md) | proposal | none | Continuous-batching inference server for Phase 3 claim extraction |
| [0020](0020-segmentation-batching-server.md) | proposal | none | Continuous-batching inference server for Phase 2 segmentation |

## Implementation notes (2026-05-07 sweep)

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
- **0012** — code already follows the language rules (`from __future__
  import annotations`, `SegmentationError` family, `ENGRAM_*` env vars), but
  Phase 0 toolchain (ruff/pyright in `pyproject.toml`, `make lint|format|
  typecheck` targets) is not wired.
- **0013** — marker gates are scripted in `scripts/phase3_tmux_agents.sh`;
  redacted-report authoring and repair-plan synthesis remain coordinator-
  driven rather than fully automated.
- **0014** — spec accepted (D066) and `phase3_tmux_agents.sh` already scans
  `docs/operations/phase3-postbuild/`, but the directory is not yet populated;
  legacy RFC 0013 per-loop paths still hold live markers.
- **0017** — Part 1 versioning contract is live
  (`EXTRACTION_PROMPT_VERSION = "extractor.v8.d064.accounted-zero"` in
  `src/engram/extractor.py`); Part 2 (`engram re-extract` CLI) and Part 3
  (cross-corpus dry-run gate) are unbuilt.
