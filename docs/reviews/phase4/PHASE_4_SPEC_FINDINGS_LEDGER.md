# Phase 4 Build-Spec Findings Ledger

author: ledger-codex-gpt-5.5-001
Status: ledger
Date: 2026-05-08
Sources:
  - PHASE_4_SPEC_REVIEW_claude.md
  - PHASE_4_SPEC_REVIEW_codex.md
  - PHASE_4_SPEC_REVIEW_gemini.md

## Findings

### F001 — `current_beliefs` lacks status-aware SQL and refresh semantics
Severity: major
Sources: [claude, codex]
Affects: BUILD_PHASES.md PHASE-0004; D044; D048; D052; D055
Rationale: The Phase 4 row defines `current_beliefs` only by `valid_to IS NULL`, but Phase 3 separates fact validity from lifecycle state and keeps unreviewed beliefs as candidates.
merged_from:
  - claude § F001
  - codex § F001

### F002 — Entity canonicalization lacks schema, provenance, and rebuild rules
Severity: major
Sources: [claude, codex]
Affects: BUILD_PHASES.md PHASE-0004; HUMAN_REQUIREMENTS.md provenance requirements; D021; RFC-0011
Rationale: `entities` and `entity_edges` are named but not specified with canonical keys, alias/merge/split audit, confidence, privacy tier, version metadata, or rebuild behavior.
merged_from:
  - claude § F002
  - codex § F002

### F003 — Local-LLM entity tiebreaks are not bounded or audited
Severity: major
Sources: [claude]
Affects: BUILD_PHASES.md PHASE-0004; D020; RFC-0024
Rationale: The inputs allow local-LLM disambiguation but do not define invocation criteria, evidence bounds, advisory versus load-bearing status, or persisted request metadata.
merged_from:
  - claude § F003

### F004 — Review actions lack transition-safe lifecycle semantics
Severity: major
Sources: [claude, codex, gemini]
Affects: BUILD_PHASES.md PHASE-0004; D006; D017; D052
Rationale: `accept`, `reject`, `correct`, and `promote-to-pinned` need allowed transitions, audit rows, idempotency behavior, and stale/concurrent action handling.
merged_from:
  - claude § F004
  - codex § F004
  - gemini § F003

### F005 — Advisory audit cascade signals are not integrated into review
Severity: minor
Sources: [claude, gemini]
Affects: RFC-0018; D069; BUILD_PHASES.md PHASE-0004
Rationale: Audit verdicts remain advisory, but the review queue should still expose invalidated-claim counts, reasons, and same-family warnings as sort/detail signals.
merged_from:
  - claude § F005
  - gemini § F005

### F006 — RFC-0024 is relevant but omitted from root-review packet inputs
Severity: minor
Sources: [claude]
Affects: striatum/phase-4-spec-review/workflow.json; striatum/phase-4-spec-review/SOURCES.md; RFC-0024
Rationale: The source list identifies RFC-0024 as Phase 4 context, but the workflow inputs list only RFC-0007, RFC-0011, and RFC-0018.
merged_from:
  - claude § F006

### F007 — Recursive CTE entity-neighborhood queries need an index and cycle plan
Severity: major
Sources: [codex]
Affects: BUILD_PHASES.md PHASE-0004; D007; RFC-0024
Rationale: The row accepts 1-2 hop recursive CTEs but does not require edge direction/type semantics, endpoint indexes, cycle prevention, depth caps, or EXPLAIN-backed latency targets.
merged_from:
  - codex § F003

### F008 — Phase 4 needs a smoke and bounded preflight gate
Severity: major
Sources: [codex]
Affects: RFC-0024; D074
Rationale: RFC-0024's Tier 0/Tier 1/Tier 2 ladder should be part of the build handoff before full-corpus entity or review queue writes.
merged_from:
  - codex § F005

### F009 — Review queue UX must show enough evidence for trust
Severity: major
Sources: [gemini]
Affects: BUILD_PHASES.md PHASE-0004; D006; D044
Rationale: A human reviewer needs confidence, stability class, evidence, contradictions, audit warnings, and action consequences, not only a list of possible actions.
merged_from:
  - gemini § F001

### F010 — Correction capture needs an explicit reprocessing lifecycle
Severity: major
Sources: [gemini]
Affects: D017; HUMAN_REQUIREMENTS.md provenance requirements
Rationale: The review queue must distinguish "correction captured" from "replacement memory derived" and queue downstream reprocessing rather than silently mutating beliefs.
merged_from:
  - gemini § F002

### F011 — Privacy-tier handling must be visible in review and entity outputs
Severity: major
Sources: [gemini]
Affects: HUMAN_REQUIREMENTS.md privacy tiers; D023; RFC-0024
Rationale: Phase 4 surfaces belief and entity data, so it needs tier labels, reclassification behavior, and redacted reporting rules for review and entity artifacts.
merged_from:
  - gemini § F004

### F012 — Long-lived review outputs may need REVIEW IDs
Severity: nit
Sources: [codex]
Affects: D068; docs/process/artifact-id-conventions.md
Rationale: Operational artifacts can remain unnumbered, but any accepted synthesis that becomes durable architecture should either get a registered review ID or stay clearly scoped as run output.
merged_from:
  - codex § F006

### F013 — The review harness needs a stricter no-egress story
Severity: minor
Sources: [gemini]
Affects: HUMAN_REQUIREMENTS.md local-first/no-egress; D020; striatum/phase-4-spec-review/workflow.json
Rationale: Workflow lanes name hosted-model CLIs while declaring `network: forbidden`; future runs need local reviewer lanes or an explicit owner-approved export.
merged_from:
  - gemini § F006

## Counts

- Total findings: 13
- Severity breakdown: blocking=0, major=9, minor=3, nit=1
- Per-reviewer contributions: claude=6, codex=6, gemini=6
