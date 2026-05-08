# RFC 0025 Command-Names Review - Gemini

author: reviewer-gemini-3.1-pro-preview-001
Status: review
Date: 2026-05-08
RFC refs: RFC-0025
Decision refs: D016, D020, D077
Phase refs: PHASE-0002, PHASE-0003, PHASE-0004, PHASE-SMOKE

## Findings

### F001 - The taxonomy solves the motivating operator-safety problem

Severity: minor
Source: docs/rfcs/0025-phase-scoped-command-names.md:23-33; docs/rfcs/0025-phase-scoped-command-names.md:35-53

Rationale: The core proposal is right: every mutating phase pipeline should say
which phase it operates on. The current `pipeline` name is too generic for a
project where Phase 2, Phase 3, Phase 4, and the future smoke gate all have
pipeline-shaped work. Making bare `pipeline` non-mutating is a better failure
mode than preserving a fast path to accidental segmentation and embedding.

### F002 - Deprecation text needs to name the exact replacement and the write risk

Severity: major
Source: docs/rfcs/0025-phase-scoped-command-names.md:142-158; README.md:137-170

Rationale: The staged compatibility plan is reasonable, but warnings for legacy
commands should be more specific than "deprecated". For a local-first operator,
the message should say what would have happened, what to run instead, and
whether the old command is mutating. For example, `engram segment` should point
to `engram phase2 segment`, while `engram pipeline` should say it is ambiguous
and name `engram phase2 run`, `engram phase3 run`, and `engram phase4 smoke`.
That preserves ergonomics while making the safety reason visible at the moment
of use.

### F003 - Phase 4 smoke should remain distinct from a full Phase 4 run

Severity: major
Source: docs/rfcs/0025-phase-scoped-command-names.md:82-85; docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md:103-189; DECISION_LOG.md:101

Rationale: RFC 0025 correctly proposes `engram phase4 smoke`, not
`engram phase4 run`. That distinction should be explicit because D077 and
RFC 0024 gate full-corpus Phase 4 behind Tier 0, Tier 1, and Tier 2 evidence.
Adding `phase4 run` too early would reintroduce the same ambiguity at a deeper
namespace level. The RFC should state that Phase 4 gets `smoke` and specific
build/review verbs until a later decision authorizes a full Phase 4 run command.

### F004 - Phase 1 can stay source-named for this RFC

Severity: minor
Source: docs/rfcs/0025-phase-scoped-command-names.md:129-132; src/engram/cli.py:63-80

Rationale: Leaving `ingest-chatgpt`, `ingest-claude`, and `ingest-gemini`
outside this change is acceptable. They are source-specific and require a path,
so they do not present the same generic mutating-pipeline risk as `pipeline`.
Deferring `phase1 ingest-*` aliases keeps RFC 0025 focused.

## Open questions

- Should warning copy be standardized in one helper so CLI and Make output stay
  aligned?
- Should `make pipeline` print only Make alternatives, or both Make and CLI
  alternatives as the RFC example currently does for the CLI?

verdict: accept_with_findings
