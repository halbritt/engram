# RFC 0029 Bench Triage Workbench Design Re-Review
author: operator [self-declared: focused-gemini-1]

Status: review
Date: 2026-05-13
RFC refs: RFC-0029
Decision refs: D020, D074

## Overall Assessment

This is a re-review of the RFC 0029 design revision, evaluating whether the prior review findings have been resolved in the updated text. The revision successfully addresses the critical flaws identified in the earlier multi-agent reviews (Claude, Codex, Gemini, and Usability Adversary). The design is now robust, persistable, and adheres strictly to the project's local-first, evidence-only, and privacy-preserving mandates.

## Findings

### 1. Persistable Prior-Run Artifacts
**Resolved.** The design now makes prior-run artifact mode first-class and persistable. The `review_sessions` schema includes explicit `prior_comparison_mode` (database vs. artifact) and explicitly stores prior artifact paths and hashes (`prior_run_path`, `prior_segment_records_path`, and their hashes). Startup strictly validates that candidate and prior artifacts reference the same slice and segment order, failing closed on mismatch.

### 2. Queue Fingerprints
**Resolved.** The `queue_fingerprint` is now rigorously defined as a SHA256 over a canonical JSON object covering the workbench schema version, slice schema/version, artifact hashes, prior comparison mode, classifier tunables (e.g., `high_drop_count_threshold`), and data-availability rule versions. Mismatches explicitly fail closed for `serve`, `status`, and `export`, preventing stale decisions from applying to a mutated queue.

### 3. Redacted Identifiers
**Resolved.** The export contract correctly treats operator-provided identifiers as hostile. Run IDs, backend names, artifact filenames, reviewer labels, and model-version strings are all sanitized. Values containing paths or `$HOME` are replaced with stable `sha256` tokens. The `reviewer_label` avoids defaulting to OS usernames, cleanly resolving previous privacy leak risks.

### 4. Read-Only DB Enforcement
**Resolved.** The RFC mandates both a dedicated read-only Postgres role (`engram_bench_review_readonly`) and the use of `SET TRANSACTION READ ONLY`. Missing read-only privileges cause a fail-closed startup or request failure. Crucially, the provisioning ambiguity is resolved by introducing an idempotent `engram phase3 bench-review provision-readonly-role` command, leaving no gaps for manual setup drift.

### 5. Follow-Up Queues
**Resolved.** The UI design now requires explicit decision-state queues (Follow-up, Regressions, Excluded blockers, Accepted) in addition to risk-tag queues. The landing page implements blocker-first resume behavior, ensuring that parked items, regressions, and out-of-scope blockers remain highly visible and require resolution before recommendation.

### 6. Readiness Language and Recommendation-vs-Promotion Wording
**Resolved.** The authoritative "promote" wording has been entirely replaced with scratch-local recommendation language (`recommend_promote`, `recommend_do_not_promote`). The schema uses `run_recommendation` and states like `ready_for_owner_gate_recommendation`. The text repeatedly reinforces that this state is explicitly non-authoritative support evidence, aligning perfectly with D074's requirement that Striatum holds the actual gate state.

### 7. Exclusion Semantics
**Resolved.** The generic "exclude from review" action was split. A narrow `exclude_unchanged_from_review` action is restricted to complete, unchanged, no-risk rows. Risky, missing, or malformed rows require `mark_blocking_out_of_scope`, which mandates a rationale note and leaves the row clearly visible in the unresolved blocker queues. This effectively prevents the UI from burying difficult decisions.

## Verdict

verdict: accept