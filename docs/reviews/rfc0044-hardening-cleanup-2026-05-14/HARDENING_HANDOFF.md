---
schema_version: "engram.handoff.v1"
artifact_kind: "hardening_handoff"
status: "implementation-ready handoff"
date: "2026-05-14"
run_ref: "run_500d0f049ea04038b0e19d6045daf918"
job_ref: "rfc0044_hardening_handoff"
author: operator [self-declared: roadmap-rfc-author-a]
---

# RFC 0044 Hardening Cleanup Handoff

## Status And Scope

This artifact is the operator-driven retry for Striatum run
`run_500d0f049ea04038b0e19d6045daf918`, job
`rfc0044_hardening_handoff`. The original process adapter exited `0` without
publishing the required handoff artifact.

RFC 0044 Engram-side Phase 1 is already accepted with findings. This handoff
turns the residual findings F002-F011 into implementation-ready follow-up
lanes. It does not implement the fixes, perform a review, or make binding
architecture decisions.

Changed file for this retry:

- `docs/reviews/rfc0044-hardening-cleanup-2026-05-14/HARDENING_HANDOFF.md`

## Source Artifacts

Primary sources read for this handoff:

- `AGENTS.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `docs/schema/README.md`
- `STRIATUM_MEMORY_ROADMAP.md`
- `striatum/striatum-memory-roadmap-rfcs-2026-05-14/SOURCES.md`
- `striatum/striatum-memory-roadmap-rfcs-2026-05-14/prompts/rfc_author.md`
- `striatum/striatum-memory-roadmap-rfcs-2026-05-14/roles/author.md`
- `striatum/striatum-memory-roadmap-rfcs-2026-05-14/workflow.json`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/FINAL_SYNTHESIS.md`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/FINDINGS_LEDGER.md`

Additional context sources from `SOURCES.md` were also read, including
`CHANGELOG.md`, `OPERATOR_REPORT.md`, `docs/rfcs/README.md`,
`docs/rfcs/0012-python-agentic-coding-standard.md`, RFC 0045-0049 scaffolds,
`docs/process/multi-agent-review-loop.md`, `docs/process/project-judgment.md`,
`/home/halbritt/git/striatum/ENGRAM_DEVELOPER_REQUEST.md`, and
`/home/halbritt/git/striatum/docs/rfcs/0044-engram-phase-1-implementation-spec.md`.

## Findings Map

| Finding | Residual | Suggested lane | Required evidence | Dependencies |
|---|---|---|---|---|
| F002 | `describe-corpus` shorthand collapses tenant and corpus outside the sanctioned `striatum` convenience case. | CLI/operator polish | CLI tests proving `striatum` maps to `tenant_id='striatum', corpus_id='striatum'`, and non-sanctioned shorthand either requires `--tenant` or fails clearly. | Independent. |
| F003 | MCP/reference failures distinguish authorization, existence, visibility, malformed reference, and missing capability cases. | MCP/reference hardening | Service and MCP-handler tests proving unauthorized, not-found, malformed, and hidden-reference paths return a uniform boundary message without content leakage. | Pair with F009; can share fixtures with F006. |
| F004 | Striatum tenant/source-kind consistency is not structurally enforced. | Tenant/source-kind isolation | Migration or service-level guard tests proving Striatum rows cannot drift outside `source_kind='striatum'`, plus `fetch_reference()` rejects inconsistent stored rows. | Coordinate with migration safety and future RFC 0046 projection work. |
| F005 | `engram-mcp-stdio --capability` accepts arbitrary strings. | MCP CLI validation | CLI/parser tests proving unknown capabilities are rejected or warned on against the known Engram `memory.*` vocabulary. | Independent; keep vocabulary Engram-local. |
| F006 | MCP stdio frame reader lacks `Content-Length` cap and JSON-RPC parse-error response path. | MCP/reference hardening | Framing tests for oversized content, malformed headers, invalid JSON, and parse-error response shape. | Pair with F003/F009. |
| F007 | Reciprocal Striatum-side augmentation-not-dependency checks were outside the Engram evidence set. | Striatum reciprocal boundary | Separate Striatum-repo artifact or tests proving no Engram client import, no daemon RPC dependency, no `memory.*` daemon capability, and graceful degradation when Engram is unavailable. | External repo dependency; blocks full cross-repo RFC 0044 contract claims. |
| F008 | `health()` reports schema version by lexicographic migration filename. | Health/version reporting | Test fixture with migration names that would misorder lexicographically; evidence that reported version follows numeric prefix or applied ordering. | Independent. |
| F009 | Malformed decoded UUID references can bypass `MemoryReferenceError` wrapping. | MCP/reference hardening | Tests for decoded non-UUID row ids before DB lookup, or tests proving relevant database UUID errors are caught and rewrapped. | Pair with F003. |
| F010 | No OS-level no-egress sandbox was exercised in the evidence pass. | Local-only evidence | Either a sandboxed no-egress probe artifact for the RFC 0044 runtime surface, or an explicit acceptance note scoping evidence to code/test inspection only. | Depends on acceptance bar for D020 structural evidence. |
| F011 | Capability and manifest evidence used synthetic fixtures, not a real or committed fixture bundle smoke. | Real-bundle smoke | Local smoke artifact against a non-private real bundle or committed fixture bundle, covering ingest, describe, MCP health, search, and fetch. | Should land before routine operator use and before broader RFC 0045+ contract claims rely on Phase 1 evidence. |

## Dependency Order

1. Preserve the repaired F001 baseline before any follow-up work. `--allow-pair`
   grants visibility only; cross-corpus and cross-tenant reads still require
   `memory.read_cross_corpus` or `memory.read_cross_tenant`.
2. Produce evidence that gates routine use: F007 reciprocal Striatum boundary
   and F011 real/fixture bundle smoke. These do not need to block narrow
   Engram code hardening, but they block claims that the full cross-repo
   augmentation contract is independently verified.
3. Bundle MCP/reference hardening: F003, F006, and F009 share the same failure
   boundary and should be implemented and reviewed together.
4. Add structural tenant/source-kind protection: F004 should land before
   RFC 0046 projections or future non-personal tenants multiply the same risk.
5. Apply independent CLI and health polish: F002, F005, and F008 can proceed
   in any order after the F001 baseline is protected.
6. Decide the F010 evidence bar. If structural D020 evidence is required for
   this phase, run the sandbox probe; otherwise record that RFC 0044 Phase 1
   evidence remains code/test inspection plus local runtime constraints.

## Suggested Implementation Lanes

Lane A: MCP/reference hardening. Suggested future write scope:
`src/engram/mcp_stdio.py`, `src/engram/memory.py`, `tests/test_mcp_stdio.py`,
and focused service tests. Owns F003, F006, and F009.

Lane B: tenant/source-kind isolation. Suggested future write scope:
the next migration, `src/engram/memory.py`, Striatum ingest/service tests, and
schema docs regenerated by `make schema-docs` if the schema changes. Owns F004.

Lane C: CLI/operator polish. Suggested future write scope:
`src/engram/cli.py`, `src/engram/mcp_stdio.py`, `src/engram/memory.py`, and
CLI/health tests. Owns F002, F005, and F008.

Lane D: evidence and smoke. Suggested future write scope:
review/evidence artifacts, fixture placement if approved, and focused smoke
scripts or tests. Owns F010 and F011 evidence production.

Lane E: reciprocal Striatum boundary. Suggested future write scope is in the
Striatum repository, not Engram: tests and review artifacts proving Engram is
optional augmentation. Owns F007.

Keep these lanes disjoint where possible. If multiple lanes touch
`src/engram/memory.py`, serialize integration or split by clearly owned
helpers to avoid competing edits.

## Evidence Required

Minimum evidence for a hardening cleanup closeout:

- Focused regression tests for F003/F006/F009 through service and MCP-handler
  paths.
- Focused migration/service tests for F004, including an inconsistent-row
  negative case for `fetch_reference()`.
- CLI tests or equivalent command evidence for F002 and F005.
- Health-version ordering test for F008.
- Real or committed fixture Striatum bundle smoke for F011.
- Separate Striatum-repo reciprocal boundary artifact for F007.
- Explicit F010 disposition: sandbox probe evidence, or an accepted scope note
  that the phase relies on code/test inspection rather than OS-level no-egress
  enforcement.
- `git diff --check`, focused pytest commands, and `make check-refs`.
- `make test` or a documented reason it was not run.
- `CHANGELOG.md` update in the implementation pass for notable changes.
- `DECISION_LOG.md` update only if the implementation introduces a new binding
  architecture decision; otherwise leave decisions unchanged.

## Non-Goals

- No source code, tests, migrations, RFC source, `CHANGELOG.md`,
  `DECISION_LOG.md`, or `OPERATOR_REPORT.md` changes in this handoff retry.
- No new hosted service, cloud API, telemetry, external persistence, or network
  dependency.
- No personal-memory exposure to Striatum by default.
- No write-side Striatum-to-Engram memory mutation.
- No claims or beliefs generated from Striatum data in this cleanup.
- No MCP write/admin tools, raw SQL tools, or Striatum mutation passthrough.
- No Striatum runtime dependency on Engram.
- No hand editing of generated schema docs.
- No RFC 0045-0049 design decisions in this artifact.

## Acceptance And Exit Record

This handoff retry exits when this file exists at the expected artifact path
with the exact author line above and the residual F002-F011 queue mapped into
implementation-ready lanes.

The future RFC 0044 hardening cleanup exits only when each residual finding has
one of:

- implemented fix plus focused evidence;
- explicit accepted deferral with rationale and owner-visible risk;
- explicit scope note where the residual is evidence-only rather than behavior.

Before routine Striatum operator use depends on RFC 0044 memory, F007 and F011
need concrete evidence. Before claiming structural D020 enforcement, F010 needs
a sandboxed no-egress probe or a narrower acceptance statement.

## Residual Risks

- Uniform MCP error messages reduce probing leakage but can make local
  debugging harder unless detailed causes stay in local-only logs or test
  assertions.
- Tenant/source-kind checks should avoid overfitting `tenant_id='striatum'` in
  a way that blocks later local application-memory tenants.
- Capability validation can drift if the known `memory.*` vocabulary is
  duplicated instead of centralized.
- A real-bundle smoke may expose private Striatum operator content if the
  fixture is not deliberately redacted or generated.
- The reciprocal Striatum boundary can regress independently of Engram unless
  Striatum owns a durable test or review artifact.
- If F010 remains scoped to code/test inspection, no-egress evidence should not
  be overstated as OS-enforced isolation.
