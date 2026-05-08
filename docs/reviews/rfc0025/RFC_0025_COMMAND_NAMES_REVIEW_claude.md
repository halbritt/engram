# RFC 0025 Command-Names Review - Claude

author: reviewer-claude-opus-001
Status: review
Date: 2026-05-08
RFC refs: RFC-0025
Decision refs: D016, D020, D074, D077
Phase refs: PHASE-0002, PHASE-0003, PHASE-0004, PHASE-0005, PHASE-SMOKE

## Findings

### F001 - Bare `pipeline` fail-closed behavior should cover sibling generic Make targets

Severity: major
Source: docs/rfcs/0025-phase-scoped-command-names.md:102-112; Makefile:87-119

Rationale: RFC 0025 correctly identifies `engram pipeline` and `make pipeline`
as the uniquely dangerous generic names because they still perform Phase 2
segmentation and embedding. The current Makefile also exposes
`pipeline-docker` and `pipeline-isolated`, both of which preserve the same
generic noun and can still trigger Phase 2 writes. The isolated target is
especially relevant because it actively manipulates local services before
running the Phase 2 pipeline. The RFC should explicitly decide whether those
targets fail closed with `pipeline`, become `phase2-run-docker` /
`phase2-run-isolated`, or remain legacy aliases with warnings for one migration
window.

### F002 - Phase 4 command naming is mostly right, but the Make surface is incomplete

Severity: minor
Source: docs/rfcs/0025-phase-scoped-command-names.md:124-127; Makefile:99-103; src/engram/cli.py:166-185

Rationale: The proposed CLI names map cleanly to the existing flat Phase 4 CLI
commands, and the `phase4 smoke` wording aligns with D077's Tier 0 gate.
However, the RFC proposes Make targets for `phase4-refresh` and
`phase4-build-entities` while the current Makefile only exposes
`phase4-smoke`. That is a good change, but it should be stated as additive Make
surface, not merely a rename. Otherwise implementation can satisfy the CLI map
and leave operator docs still inconsistent for Phase 4 refresh and entity-build
work.

### F003 - Keep fail-closed implementation before database connect as an explicit invariant

Severity: major
Source: docs/rfcs/0025-phase-scoped-command-names.md:102-112; src/engram/cli.py:195-207; src/engram/cli.py:351-377

Rationale: The RFC acceptance criterion that `engram pipeline` exits before
opening a database connection is the right safety bar. It should stay
load-bearing in tests because the current implementation opens the database
inside the command branch, so the repair is feasible without broad CLI surgery.
The test should patch or poison `ENGRAM_DATABASE_URL` and assert the ambiguous
command still exits with the disambiguation text before calling `connect()`.

## Open questions

- Should `pipeline-docker` and `pipeline-isolated` fail closed in the same
  implementation slice as `pipeline`, or should they become warned compatibility
  aliases for exactly one release window?
- Should Phase 4 Make additions include Docker variants for refresh and entity
  build, or only the already-scoped local targets?

verdict: accept_with_findings
