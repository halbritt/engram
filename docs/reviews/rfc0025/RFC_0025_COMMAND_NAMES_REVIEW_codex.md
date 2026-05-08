# RFC 0025 Command-Names Review - Codex

author: reviewer-codex-gpt-5.5-001
Status: review
Date: 2026-05-08
RFC refs: RFC-0025
Decision refs: D016, D020, D074, D077
Phase refs: PHASE-0002, PHASE-0003, PHASE-0004, PHASE-SMOKE

## Findings

### F001 - The RFC leaves the phase-local verb unresolved while acceptance uses `run`

Severity: major
Source: docs/rfcs/0025-phase-scoped-command-names.md:73-100; docs/rfcs/0025-phase-scoped-command-names.md:211-216

Rationale: The proposal section and acceptance criteria standardize on
`engram phaseN run` and `make phaseN-run`, but the open questions still ask
whether the preferred phase-local verb should be `run` or `pipeline`. That is
too central to leave unresolved before implementation. The RFC should either
promote `run` as the accepted operator verb, or explicitly choose
`phaseN pipeline`. My recommendation is `run`: it is shorter, avoids
reintroducing the overloaded word, and matches the operator examples already in
the RFC.

### F002 - Nested argparse is feasible, but compatibility aliases need a pinned parser plan

Severity: major
Source: src/engram/cli.py:57-195; src/engram/cli.py:351-496

Rationale: The current CLI is a single argparse subparser layer, so nested
`phase2`, `phase3`, and `phase4` groups are practical but will touch the parser
and dispatch shape together. The RFC should pin a low-risk implementation plan:
add nested commands first, route each nested command to the existing branch
logic or helper functions, then convert only the dangerous bare `pipeline` to a
fail-closed parser action. That avoids a broad refactor while still making the
new command surface testable.

### F003 - README examples must change in the same commit as fail-closed `pipeline`

Severity: major
Source: README.md:137-170; docs/rfcs/0025-phase-scoped-command-names.md:189-197

Rationale: The README currently teaches `make pipeline` for Phase 2 and
`make pipeline-3` for Phase 3. Once `make pipeline` fails closed, docs and
operator muscle memory must move in the same change. The acceptance criteria
already mention README examples, but implementation should treat README and
`--help` text as part of the behavioral change, not cleanup after the fact.

### F004 - Phase names align with the canonical phase boundaries

Severity: minor
Source: BUILD_PHASES.md:120-227; BUILD_PHASES.md:229-253

Rationale: The proposed names keep Phase 2 as segmentation plus embedding,
Phase 3 as extraction plus consolidation, and Phase 4 as current-belief/entity
and review work. That directly addresses the concrete operator mistake that
started Phase 2 work while the intent was Phase 4 belief extraction/review
follow-up. The command taxonomy is directionally sound once the open verb and
alias migration questions are closed.

## Open questions

- Should hidden compatibility aliases be visible in `--help`, or should help
  show only phase-scoped names after the first implementation?
- Should old commands print warnings to stderr only, or should they require an
  explicit `--legacy-command` flag immediately after `pipeline` fails closed?

verdict: accept_with_findings
