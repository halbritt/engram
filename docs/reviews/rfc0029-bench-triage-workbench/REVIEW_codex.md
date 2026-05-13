# RFC 0029 Bench Triage Workbench Review — codex
author: reviewer-codex-gpt-5.5-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0029
Decision refs: D020, D074, D-082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### F001 — Make segment records required for triage mode
Severity: blocking
Source: docs/rfcs/0029-bench-triage-workbench.md:113
Rationale: The RFC lists the candidate segment-result JSONL as optional, but the proposed classifier depends on per-segment candidate claim counts, dropped counts, predicates, and provenance status. `run.json` is aggregate metadata, while the benchmark harness documents `segments.jsonl` as the one redacted result per segment, and the code writes `claim_count`, `dropped_count`, `provenance_valid`, and redacted claim records there. Without that file, the workbench cannot deterministically build `zeroed`, `count_changed`, `predicate_mix_changed`, `high_drop_count`, or `provenance_anomaly` queues. The spec should require the `segment_records_path` referenced by `run.json` for normal review mode, with a deliberately degraded "metadata only" status view if the file is missing.

### F002 — Prior extraction selection is under-specified
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:99
Rationale: The CLI accepts only `--prior-version`, but production extraction rows are versioned by at least `extraction_prompt_version`, `extraction_model_version`, and `request_profile_version` in both `claim_extractions` and `claims`. RFC 0019 also treats backend changes as `extraction_model_version` / `request_profile_version` changes, not just prompt changes. A prompt-only selector can silently mix prior rows from different request profiles or model stamps, making count deltas and predicate deltas ambiguous. The RFC should either require a full prior version triple, derive it from an explicit prior run artifact, or define a deterministic query that rejects ambiguous matches.

### F003 — Candidate claim display cannot promise structured subject/object rows under default redaction
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:214
Rationale: The screen design promises prior and candidate claims as structured subject/predicate/object rows, but the benchmark harness intentionally omits candidate `subject_text`, `object_text`, `object_json`, and rationale unless `--include-claim-text` is explicitly passed. That default is correct for privacy, and the RFC 0028 benchmark report relies on it, but it means candidate rows can only show predicate, object kind/presence, confidence, stability class, and evidence ids by default. The RFC should define two display modes: redacted candidate mode from normal `segments.jsonl`, and private scratch mode when the operator explicitly supplies a claim-text artifact or opts into direct local replay/DB lookup. Tracked exports must stay redacted in either mode.

### F004 — Export path hardening needs acceptance tests
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:251
Rationale: The export route and CLI write a user-provided tracked path under `docs/reviews/`, but the acceptance criteria only test omission of private text. To make the redaction boundary mechanical, the spec should add path-resolution tests for absolute paths, `..` traversal, symlink escape, home-directory paths, overwriting existing files, and the difference between CLI-only `--allow-outside-reviews` and the web `POST /export` route. This matters because Phase 4 artifact rules also forbid home-directory absolute paths and private corpus values in committed reports.

### F005 — Phase placement needs a concrete alias decision before implementation
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md:260
Rationale: `engram phase3 bench-review` is coherent for the immediate RFC 0028 re-extraction review, but the RFC is also tied to PHASE-0004 and RFC 0024's pre-full-corpus benchmark gate. The open question asks whether Phase 4 gets an alias, but implementation prompts need a stable command contract. Resolve this in the follow-on spec: either keep one canonical `phase3 bench-review` command and document it as an extraction-only tool, or add an explicit `phase4 bench-review` alias only when Phase 4 benchmark artifacts are supported.

## Open questions

Should the v1 workbench allow manual decisions when candidate claim text is unavailable, or should verdicts that require semantic claim review be disabled until the operator supplies a private scratch artifact with claim text?

Should `POST /export` exist in the web UI at all for v1, or should export remain CLI-only like RFC 0027 kept export/history out of the browser surface?

verdict: needs_revision
