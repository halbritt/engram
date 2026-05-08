<a id="rfc-0025"></a>
# RFC 0025: Phase-Scoped Command Names

Status: proposal
Date: 2026-05-08
Context: Operator command names for Phase 2 segmentation, Phase 3 extraction,
Phase 4 review/entity work, and future phase pipelines
Decision refs:
  - D016
  - D020
  - D074
  - D077
Review refs:
  - none
Phase refs:
  - PHASE-0001
  - PHASE-0002
  - PHASE-0003
  - PHASE-0004
  - PHASE-0005
  - PHASE-SMOKE

## Summary

Engram's mutating operator commands should be phase-scoped. The current CLI and
Make surface uses `pipeline` for Phase 2 (`segment -> embed`) while Phase 3 is
named `pipeline-3`, and Phase 4 has a separate `phase4-smoke` command. That
asymmetry is unsafe: an operator asking to run "the pipeline" for Phase 4 can
accidentally start segmentation and embedding.

This RFC proposes canonical phase-scoped command names, a fail-closed behavior
for the bare `pipeline` command, and a staged compatibility plan for existing
single-stage commands.

## Problem

The word `pipeline` is overloaded. In the project architecture, every phase has
one or more pipelines:

- Phase 2 runs segmentation and embeddings.
- Phase 3 runs claim extraction and belief consolidation.
- Phase 4 builds current-belief projections, entity scaffolding, review
  actions, and gated smoke/preflight runs.
- Phase 5 will build `context_for` and serving/smoke paths.

The command name `pipeline` currently means only Phase 2. That name does not
carry enough information for an operator, agent, or script to infer the phase.
It also contradicts the way `pipeline-3` already names the Phase 3 path
explicitly.

This ambiguity caused a concrete operational error: a Phase 4 follow-up request
started Phase 2 segmentation/embedding work because the generic `pipeline`
command looked like the canonical "start the pipeline" command.

## Goals

1. Make every mutating phase pipeline name include the phase.
2. Make `pipeline` fail closed rather than perform writes.
3. Keep command names short enough for daily operator use.
4. Preserve local-first operation and existing Makefile workflows.
5. Provide a migration path that does not silently break existing scripts.

## Non-Goals

1. This RFC does not redesign the storage schema.
2. This RFC does not change model backends, prompts, or phase gates.
3. This RFC does not authorize full-corpus Phase 4 execution; D077/RFC-0024
   still gate that path.
4. This RFC does not require renaming database tables or progress stages.

## Proposal

Use phase-scoped command groups in the CLI:

```sh
engram phase2 segment
engram phase2 embed
engram phase2 run
engram phase3 extract
engram phase3 consolidate
engram phase3 run
engram phase4 refresh-current-beliefs
engram phase4 build-entities
engram phase4 smoke
engram phase4 review-belief
```

Use phase-scoped Make targets that mirror those commands:

```sh
make phase2-segment
make phase2-embed
make phase2-run
make phase3-extract
make phase3-consolidate
make phase3-run
make phase4-refresh
make phase4-build-entities
make phase4-smoke
```

The noun `pipeline` should not be a runnable top-level command. Running
`engram pipeline` or `make pipeline` should exit nonzero before opening a
database connection and print the explicit alternatives:

```text
ambiguous command: pipeline
Use one of:
  engram phase2 run
  engram phase3 run
  engram phase4 smoke
```

## Command Map

| Phase | Current CLI | Proposed CLI | Current Make | Proposed Make |
|-------|-------------|--------------|--------------|---------------|
| Phase 2 | `segment` | `phase2 segment` | `segment` | `phase2-segment` |
| Phase 2 | `embed` | `phase2 embed` | `embed` | `phase2-embed` |
| Phase 2 | `pipeline` | `phase2 run` | `pipeline` | `phase2-run` |
| Phase 3 | `extract` | `phase3 extract` | `extract` | `phase3-extract` |
| Phase 3 | `consolidate` | `phase3 consolidate` | `consolidate` | `phase3-consolidate` |
| Phase 3 | `pipeline-3` | `phase3 run` | `pipeline-3` | `phase3-run` |
| Phase 4 | `phase4-refresh` | `phase4 refresh-current-beliefs` | none | `phase4-refresh` |
| Phase 4 | `phase4-build-entities` | `phase4 build-entities` | none | `phase4-build-entities` |
| Phase 4 | `phase4-smoke` | `phase4 smoke` | `phase4-smoke` | `phase4-smoke` |
| Phase 4 | `review-belief` | `phase4 review-belief` | none | none |

Phase 1 ingestion commands may remain source-named for now because they are
less ambiguous (`ingest-chatgpt`, `ingest-claude`, `ingest-gemini`). A later
cleanup may add `phase1 ingest-chatgpt` aliases, but this RFC focuses on the
LLM-derived phases where accidental writes are more expensive.

Phase 5 should follow the same rule when implemented:

```sh
engram phase5 context-for
engram phase5 smoke
make phase5-smoke
```

## Deprecation And Compatibility

Implementation should happen in three steps.

Step 1 adds the new phase-scoped commands and Make targets while keeping the
old single-stage commands operational.

Step 2 changes `engram pipeline` and `make pipeline` into fail-closed
disambiguation commands. These two names are uniquely dangerous because they
hide Phase 2 writes behind a generic noun.

Step 3 deprecates the remaining bare mutating commands (`segment`, `embed`,
`extract`, `consolidate`, `pipeline-3`, `phase4-refresh`,
`phase4-build-entities`, `phase4-smoke`, and `review-belief`) by printing a
warning that names the phase-scoped replacement. After one accepted decision or
release window, they may be hidden from help or require an explicit
`--legacy-command` flag.

## Operator Examples

Bounded Phase 2 run:

```sh
engram phase2 run --limit 25
make phase2-run LIMIT=25
```

Bounded Phase 3 extraction and consolidation:

```sh
engram phase3 run --limit 50
make phase3-run LIMIT=50
```

Phase 4 Tier 0 smoke:

```sh
engram phase4 smoke --limit 25
make phase4-smoke LIMIT=25
```

Phase 4 review action:

```sh
engram phase4 review-belief BELIEF_ID accept --actor local
```

## Acceptance Criteria

1. `engram pipeline` exits nonzero without opening a database connection.
2. `make pipeline` exits nonzero and prints phase-scoped alternatives.
3. `engram phase2 run --limit N` performs the current Phase 2 pipeline.
4. `engram phase3 run --limit N` performs the current Phase 3 pipeline.
5. `engram phase4 smoke --limit N` performs the current Phase 4 smoke path.
6. README operator examples use only phase-scoped commands.
7. Tests cover the fail-closed `pipeline` behavior.

## Risks

Existing scripts may call `make pipeline` for Phase 2. The safer failure mode
is to stop and print `make phase2-run` rather than continue allowing a generic
command to write segmentation and embedding rows.

Nested CLI subcommands require a small argparse refactor. If that refactor is
too broad for the first implementation, flat aliases such as
`phase2-pipeline`, `phase3-pipeline`, and `phase4-smoke` are acceptable as an
intermediate step, but the final user-facing shape should be phase-scoped and
consistent.

## Open Questions

1. Should bare single-stage commands eventually be removed, or kept as hidden
   compatibility aliases with warnings?
2. Should `run` or `pipeline` be the preferred phase-local verb
   (`engram phase2 run` versus `engram phase2 pipeline`)?
3. Should Phase 1 ingest commands be moved under `engram phase1` in the same
   implementation, or left for a later source-ingest cleanup?
