# RFC 0025 Command-Names Findings Ledger

author: ledger-codex-gpt-5.5-001
Status: ledger
Date: 2026-05-08
Sources:
  - RFC_0025_COMMAND_NAMES_REVIEW_claude.md
  - RFC_0025_COMMAND_NAMES_REVIEW_codex.md
  - RFC_0025_COMMAND_NAMES_REVIEW_gemini.md

## Findings

### F001 - Generic sibling Make targets need the same migration decision as `pipeline`

Severity: major
Sources: [claude]
Affects: Makefile `pipeline-docker`, `pipeline-isolated`; RFC-0025 fail-closed scope
Rationale: The current Makefile has generic Phase 2 pipeline variants beyond `make pipeline`, and RFC 0025 should explicitly decide whether they fail closed or become phase-scoped compatibility aliases.
merged_from:
  - claude F001

### F002 - Phase 4 Make targets are additive, not only renames

Severity: minor
Sources: [claude]
Affects: Makefile Phase 4 targets; RFC-0025 command map
Rationale: RFC 0025 proposes `phase4-refresh` and `phase4-build-entities` Make targets that do not currently exist, so implementation must add them rather than merely rename existing Make entries.
merged_from:
  - claude F002

### F003 - Fail-closed `pipeline` must be tested before database connection

Severity: major
Sources: [claude]
Affects: `engram pipeline`; `make pipeline`; CLI tests
Rationale: The safety property depends on `pipeline` exiting with alternatives before opening the database, and that invariant is feasible against the current command branch shape.
merged_from:
  - claude F003

### F004 - The phase-local verb is still unresolved in the RFC text

Severity: major
Sources: [codex]
Affects: RFC-0025 proposal and open questions
Rationale: The proposal and acceptance criteria choose `phaseN run`, but the open questions still ask whether the phase-local verb should be `run` or `pipeline`, leaving a central implementation choice unsettled.
merged_from:
  - codex F001

### F005 - Nested argparse migration needs a low-risk parser plan

Severity: major
Sources: [codex]
Affects: `src/engram/cli.py`
Rationale: The current CLI is a single subparser layer; nested `phase2`, `phase3`, and `phase4` groups are practical, but the RFC should pin an incremental parser/dispatch migration to avoid broad refactor risk.
merged_from:
  - codex F002

### F006 - Operator docs, help text, and warning copy must land with fail-closed behavior

Severity: major
Sources: [codex, gemini]
Affects: README examples; CLI help; Make target output; legacy command warnings
Rationale: Once `pipeline` fails closed, README examples and command warnings need to name exact replacements and explain the write risk at the moment of use.
merged_from:
  - codex F003
  - gemini F002

### F007 - Proposed taxonomy aligns with canonical phase boundaries

Severity: minor
Sources: [codex, gemini]
Affects: RFC-0025 command taxonomy; BUILD_PHASES.md
Rationale: The proposed names keep Phase 2 as segmentation plus embedding, Phase 3 as extraction plus consolidation, and Phase 4 as current-belief/entity/review work, which addresses the motivating operator error.
merged_from:
  - codex F004
  - gemini F001

### F008 - Phase 4 `smoke` must remain distinct from any future full Phase 4 run

Severity: major
Sources: [gemini]
Affects: `engram phase4 smoke`; RFC-0024 benchmark ladder; D077
Rationale: RFC 0025 should explicitly avoid adding `phase4 run` until a later decision authorizes a full Phase 4 run command, because D077 gates full-corpus Phase 4 behind bounded smoke and preflight evidence.
merged_from:
  - gemini F003

### F009 - Phase 1 source-named ingest commands can stay out of this RFC

Severity: minor
Sources: [gemini]
Affects: `ingest-chatgpt`, `ingest-claude`, `ingest-gemini`
Rationale: The source-specific ingest commands require explicit input paths and do not carry the same ambiguous mutating-pipeline risk as bare `pipeline`.
merged_from:
  - gemini F004

## Counts

- Total findings: 9
- Severity breakdown: blocking=0, major=6, minor=3, nit=0
- Per-reviewer contributions: claude=3, codex=4, gemini=4
