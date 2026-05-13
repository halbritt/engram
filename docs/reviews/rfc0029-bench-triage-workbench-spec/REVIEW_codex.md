# Spec 0029 Bench Triage Workbench Review - reviewer-codex-gpt-5.5-001
author: reviewer-codex-gpt-5.5-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0029
Spec refs: SPEC-0029
Decision refs: D020, D074, D-082
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### F001 - Artifact field mapping remains implicit
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md § Candidate run artifact; § Segment records
Rationale: The spec says the loader must tolerate benchmark artifact shapes already used by `benchmarks/extraction/`, but it only defines the normalized dataclasses and accepted container formats. It does not define accepted source field aliases, type coercions, duplicate segment handling, run-id derivation, count reconciliation, or what makes a row shape "unusable." Implementers would need to rediscover those rules from current benchmark code, which reopens design and can produce non-deterministic behavior across implementations.

### F002 - Data-state precedence is not deterministic
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md § Data Availability; § Classification
Rationale: The contract says each row has exactly one `data_state`, but several states overlap. A row with candidate counts and prior counts can be both `complete` and `candidate_zero`; a redacted candidate with counts and prior data can be both `complete` and `candidate_redacted`; `prior_missing` can overlap with candidate missing, zero, redacted, or malformed cases. The queue order also mixes data states and tags while rows may have multiple tags, but no precedence or stable tie-breaker is specified. This blocks deterministic classification, queue ordering, and rendered-control behavior.

### F003 - Scratch SQLite can still store raw private text through rationale
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md § Scratch SQLite State; § Redacted Export
Rationale: The scratch database is described as containing no raw private text, but `rationale TEXT` is free-form and persisted for segment and run reviews. The spec warns that rationale must not include private excerpts and says export sanitizes it, but it does not define a storage-side constraint, sanitizer, length cap, or narrower invariant such as "no automatically copied raw segment, claim, excerpt, or LLM text." As written, the implementation can satisfy the schema while still storing private excerpts in scratch state.

### F004 - CLI failure behavior is only partially specified
Severity: minor
Source: docs/specs/0029-bench-triage-workbench-spec.md § CLI
Rationale: The serve command has a precise non-loopback exit status of `8`, but export/status behavior is less testable. Unsafe export output paths, missing or malformed review databases, unwritable outputs, invalid artifact paths, and malformed input artifacts do not have specified exit codes or stdout/stderr expectations. The spec should either assign explicit codes or state that these use the existing CLI framework's standard nonzero validation/error behavior.

### F005 - Acceptance tests miss the highest-risk determinism cases
Severity: major
Source: docs/specs/0029-bench-triage-workbench-spec.md § Tests; § Acceptance
Rationale: The required tests cover important behavior, but they do not require cases for data-state precedence, multi-tag queue ordering, stable tie-breaking, duplicate segment rows, redacted-candidate control behavior, or `prior_missing` control behavior. They also test that raw text columns are absent, but not that route/template/export code never copies private text into scratch or tracked artifacts. These gaps leave the main implementation risks from RFC 0029 under-specified for review.

## Open questions

No direct conflict with RFC 0017, RFC 0019, RFC 0024, RFC 0027, or RFC 0028 is apparent from the supplied packet, assuming the loopback-only posture is intentional for this narrower workbench and the request-profile filters remain exact-version filters.

verdict: accept_with_findings
