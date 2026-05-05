# P028: Build Phase 3 Claims And Beliefs

> Prompt ordinal: P028. Introduced: pending first commit. Source commit: pending.

## Guard

Do not execute this prompt until:

```text
docs/reviews/phase3/markers/07_BUILD_PROMPT_SYNTHESIS.ready.md
```

exists.

This file is intentionally created as the build-prompt target. P025 must fill
it from the accepted Phase 3 spec, and P027 must apply build-prompt review
findings before any implementation agent runs it.

## Placeholder Scope

The final version of this prompt should implement Phase 3 claim extraction and
belief consolidation from `docs/claims_beliefs.md`.

Expected implementation areas:

- migrations,
- `src/engram` extraction/consolidation modules,
- CLI and Makefile targets,
- progress/resumability wiring,
- local structured LLM request client reuse,
- tests,
- generated schema docs.

## Non-Goals

- Do not run the full Phase 3 corpus.
- Do not author the gold set.
- Do not implement Phase 4 review queue or entity canonicalization.
- Do not introduce hosted services, cloud APIs, telemetry, or external
  persistence.

## Required Completion Marker

The final build prompt must require:

```text
docs/reviews/phase3/markers/08_BUILD_COMPLETE.ready.md
```

