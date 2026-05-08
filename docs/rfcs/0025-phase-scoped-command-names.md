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
  - REVIEW-0034
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

This RFC proposes canonical phase-scoped command names, fail-closed behavior
for generic `pipeline` commands, and a staged compatibility plan for existing
single-stage commands. The phase-local verb is `run`; `pipeline` is not a
canonical verb at any phase scope.

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
2. Make generic `pipeline` commands fail closed rather than perform writes.
3. Keep command names short enough for daily operator use.
4. Preserve local-first operation and existing Makefile workflows.
5. Provide a migration path that does not silently break existing scripts.

## Non-Goals

1. This RFC does not redesign the storage schema.
2. This RFC does not change model backends, prompts, or phase gates.
3. This RFC does not authorize full-corpus Phase 4 execution; D077/RFC-0024
   still gate that path.
4. This RFC does not require renaming database tables or progress stages.
5. This RFC does not introduce `engram phase4 run`. D077/RFC-0024 must first
   accept the full Phase 4 execution contract beyond smoke and preflight gates.

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

`run` is the canonical phase-local verb for multi-stage phase execution.
`pipeline` is reserved only as a legacy or ambiguous top-level spelling that
must not perform writes.

Use phase-scoped Make targets that mirror those commands:

```sh
make phase2-segment
make phase2-embed
make phase2-run
make phase2-run-docker
make phase2-run-isolated
make phase3-extract
make phase3-consolidate
make phase3-run
make phase3-run-docker
make phase4-refresh
make phase4-build-entities
make phase4-smoke
make phase4-smoke-docker
```

The noun `pipeline` should not be a runnable top-level command. Running
`engram pipeline`, `make pipeline`, `make pipeline-docker`, or
`make pipeline-isolated` should exit nonzero before opening a database
connection and print explicit alternatives:

```text
ambiguous command: pipeline
Use one of:
  engram phase2 run
  engram phase3 run
  engram phase4 smoke
```

For Make, the alternatives should name Make targets:

```text
ambiguous target: pipeline
Use one of:
  make phase2-run
  make phase2-run-docker
  make phase2-run-isolated
  make phase3-run
  make phase4-smoke
```

Phase 4 intentionally exposes `smoke` and specific verbs, not a generic
`phase4 run`. A later accepted RFC may add `phase4 run` only after the
Tier 0/Tier 1/Tier 2 gates in RFC-0024 and D077 have established a safe
full-run contract.

## Command Map

| Phase | Current CLI | Proposed CLI | Current Make | Proposed Make |
|-------|-------------|--------------|--------------|---------------|
| Phase 2 | `segment` | `phase2 segment` | `segment` | `phase2-segment` |
| Phase 2 | `embed` | `phase2 embed` | `embed` | `phase2-embed` |
| Phase 2 | `pipeline` | `phase2 run` | `pipeline` | `phase2-run` |
| Phase 2 | none | `phase2 run` | `pipeline-docker` | `phase2-run-docker` |
| Phase 2 | none | `phase2 run` | `pipeline-isolated` | `phase2-run-isolated` |
| Phase 3 | `extract` | `phase3 extract` | `extract` | `phase3-extract` |
| Phase 3 | `consolidate` | `phase3 consolidate` | `consolidate` | `phase3-consolidate` |
| Phase 3 | `pipeline-3` | `phase3 run` | `pipeline-3` | `phase3-run` |
| Phase 3 | `pipeline-3` | `phase3 run` | `pipeline-3-docker` | `phase3-run-docker` |
| Phase 4 | `phase4-refresh` | `phase4 refresh-current-beliefs` | none | `phase4-refresh` |
| Phase 4 | `phase4-build-entities` | `phase4 build-entities` | none | `phase4-build-entities` |
| Phase 4 | `phase4-smoke` | `phase4 smoke` | `phase4-smoke` | `phase4-smoke` |
| Phase 4 | `phase4-smoke` | `phase4 smoke` | `phase4-smoke-docker` | `phase4-smoke-docker` |
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

Implementation should happen in four steps.

Step 1 adds nested phase-scoped CLI commands and phase-scoped Make targets while
keeping the old single-stage commands operational. The parser migration should
be incremental: add `phase2`, `phase3`, and `phase4` subparsers that dispatch to
the existing command helper paths before removing or hiding any legacy surface.

Step 2 changes `engram pipeline`, `make pipeline`, `make pipeline-docker`, and
`make pipeline-isolated` into fail-closed disambiguation commands. These names
are uniquely dangerous because they hide Phase 2 writes behind a generic noun.
The implementation should share warning/disambiguation copy where practical so
CLI and Make output stay aligned.

Step 3 updates README examples, CLI help text, and Make target help or failure
messages in the same change as the fail-closed behavior. Operator-facing docs
must not continue teaching commands that now fail closed.

Step 4 deprecates the remaining bare mutating commands (`segment`, `embed`,
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
2. `make pipeline`, `make pipeline-docker`, and `make pipeline-isolated` exit
   nonzero and print phase-scoped alternatives.
3. `engram phase2 run --limit N` performs the current Phase 2 pipeline.
4. `engram phase3 run --limit N` performs the current Phase 3 pipeline.
5. `engram phase4 smoke --limit N` performs the current Phase 4 smoke path.
6. `engram phase4 run` is not introduced by this RFC.
7. README operator examples and CLI help text use phase-scoped commands.
8. Tests cover fail-closed behavior before database connection.
9. Tests cover phase-scoped Make targets for Phase 2, Phase 3, and Phase 4
   smoke.

## Risks

Existing scripts may call `make pipeline`, `make pipeline-docker`, or
`make pipeline-isolated` for Phase 2. The safer failure mode is to stop and
print `make phase2-run` or the matching scoped variant rather than continue
allowing a generic command to write segmentation and embedding rows.

Nested CLI subcommands require a small argparse refactor. If that refactor is
too broad for the first implementation, the fallback should still avoid the
word `pipeline` in new names. Flat aliases such as `phase2-run`,
`phase3-run`, and `phase4-smoke` are acceptable as an intermediate step, but
the final user-facing shape should be nested and phase-scoped.

## Open Questions

1. Should bare single-stage commands eventually be removed, or kept as hidden
   compatibility aliases with warnings?
2. Should Phase 1 ingest commands be moved under `engram phase1` in the same
   implementation, or left for a later source-ingest cleanup?
