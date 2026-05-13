# RFC 0029 Bench Triage Workbench Review - codex
author: operator [self-declared: rfc0029-design-review-codex]

Status: review
Date: 2026-05-13
RFC refs: RFC-0029
Decision refs: D020, D074
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### F001 - Prior-Run Artifact Mode Is Not Persistable
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:140; docs/rfcs/0029-bench-triage-workbench.md:177; docs/rfcs/0029-bench-triage-workbench.md:492
Rationale: RFC 0029 allows direct run-to-run comparison via an explicit prior benchmark run artifact, but the CLI surface does not name that flag and the proposed `review_sessions` table stores only the candidate run paths plus prior version fields. A restarted `serve`, `status`, or `export` command cannot reconstruct prior artifact rows, validate the prior run's segment order, or prove the prior artifact still matches the review queue. The follow-on spec should freeze explicit prior-artifact flags, store the prior run/segment artifact identity in scratch SQLite, and require same-slice/same-order validation tests for DB-prior and artifact-prior modes.

### F002 - Queue Fingerprint Contract Is Underspecified
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:188; docs/rfcs/0029-bench-triage-workbench.md:299; docs/rfcs/0029-bench-triage-workbench.md:441
Rationale: The schema has a `queue_fingerprint`, and startup resolves a single active session from external scratch artifacts, but the RFC never defines what the fingerprint covers or how mismatches fail. Since scratch run files can be regenerated, moved, or replaced while the SQLite decisions persist, stale decisions could be applied to a different queue or to different classifier parameters such as the high-drop threshold. The spec should define the fingerprint inputs: slice schema/version, ordered segment IDs, candidate run identity or artifact hash, prior identity or prior artifact hash, classifier thresholds, and data-availability rules, then require startup/status/export to fail closed on mismatch.

### F003 - Redacted Export Treats Run ID As Safer Than It Is
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:515; docs/rfcs/0029-bench-triage-workbench.md:517; benchmarks/extraction/run_benchmark.py:2295
Rationale: The export contract excludes raw path basenames because operator-chosen filenames can contain private names, but it still exports the benchmark run ID. The current benchmark harness derives `run_id` from the operator-provided `--backend-name`, only replacing unsafe characters, so a backend label containing a private person, project, client, or corpus clue would leak into tracked docs. The export contract should treat run IDs as untrusted too: either export a derived public artifact ID/hash or require the exporter to sanitize and validate run IDs with the same standard used for path basenames.

### F004 - Read-Only Database Enforcement Needs One Consistent Rule
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md:162; docs/rfcs/0029-bench-triage-workbench.md:592; docs/rfcs/0029-bench-triage-workbench.md:688
Rationale: The proposal first says the server should use a read-only role when available and read-only transactions for every production-table access, failing closed if either guard cannot apply. Later it says read-only role and/or read-only transactions, and the provisioning path remains an open question. That leaves implementers unsure whether v1 can ship with transaction-level protection only, or whether a missing read-only role is a startup failure. Before implementation, the spec should choose one rule and add the corresponding CLI/setup and failure-mode tests.

## Open questions

1. Should `segment_reviews` have a composite foreign key to `segment_queue(session_id, segment_id)` so scratch storage cannot contain out-of-slice decisions even if a route or manual SQLite edit bypasses UI validation?
2. Should the high-drop threshold be a fixed v1 constant, a CLI flag recorded in `review_sessions`, or an `ENGRAM_` module-level tunable included in the queue fingerprint?
3. Should `candidate_redacted + accept_candidate_change` remain possible for count-only deltas, or should every semantic acceptance require either local source context or private-detail candidate artifacts?

verdict: accept_with_findings
