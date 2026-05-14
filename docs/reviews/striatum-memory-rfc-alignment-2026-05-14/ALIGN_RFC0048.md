# RFC 0048 Alignment Handoff
author: operator [self-declared: alignment-rfc0048]

Status: alignment handoff
Date: 2026-05-14
Run ID: run_169531d5568248ff8f0dfc803d955311
Job: align_rfc0048_context_policy

## Scope

This handoff records narrow proposal-text alignment for RFC 0048 only. It does
not promote RFC 0048, authorize implementation, change Striatum state, update
canonical decisions, or enable routine/default-on memory.

## Findings Addressed

- F008: Added explicit manual paste-through policy. Manual search results,
  including personal or non-primary memory, become packet context only through
  explicit per-packet selection with authorization, citations, privacy/redaction
  checks, and audit metadata.
- F010: Strengthened audit privacy inheritance. Audit records now inherit the
  maximum privacy tier and redaction constraints of selected or omitted
  candidates, with opaque request-local candidate ids for lower-tier views.
- F011: Added `identity_leak`, `citation_leak`, and
  `generated_product_blocked` omission reason codes.
- F016: Tightened default-on wording. Routine default-on automatic injection is
  blocked until accepted/promoted RFC 0045-RFC 0048 successors exist and RFC
  0049 Level 3 gates pass.
- F022: Clarified session-scope disable semantics as transient to the current
  operator or agent session unless explicitly promoted to run scope or operator
  configuration.
- F012: Made generated memory products ineligible for Level 2 and Level 3
  injection until a separate accepted privacy-inheritance, citation, audit, and
  gate contract exists.

## Findings Deferred

- F003, F004, F013: RFC 0047 response and metadata redaction alignment remains
  outside this write scope.
- F014, F015: RFC 0046 exact-reference and embedding-skip alignment remains
  outside this write scope.
- F009: RFC 0049 no-egress wording cleanup remains outside this write scope.
- F017, F018: Redaction-state open-decision cleanup and roadmap/index cleanup
  remain outside this write scope.
- F019: Collapsed no-data status ergonomics remains deferred.
- F020, F021: Current-authority conflict citations and cold-start evidence are
  gate evidence issues, not RFC 0048 text changes in this pass.

## Files Changed

- `docs/rfcs/0048-striatum-context-injection-policy.md`
- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0048.md`

## Dependency Impact

RFC promotion still requires a separate promotion decision and the remaining
cross-RFC follow-ups named in the roadmap synthesis. Implementation remains
blocked on accepted/promoted contracts and applicable RFC 0049 gates. Routine
Striatum use remains blocked for Level 3 default-on automatic injection; Level 1
manual source-evidence search remains a separate, explicit, local-only path and
does not authorize packet paste-through without RFC 0048 policy compliance.

Generated memory products remain blocked from Level 2 and Level 3 injection
until a separate accepted generated-product contract exists. Personal memory
remains outside default Striatum injection.

## Validation

- `git diff --check -- docs/rfcs/0048-striatum-context-injection-policy.md docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0048.md`: passed with exit code 0 and no output.
- `git diff --check --no-index -- /dev/null docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0048.md`: no whitespace warnings; exit code 1 is expected for a `/dev/null` comparison against a new file.
- `make check-refs`: not required because no explicit anchors or
  checker-recognized artifact references were changed.

## Friction

- The first native sub-agent launch attempted to combine `agent_type` with a
  full-history fork and was rejected by the tooling; the sub-agent was relaunched
  successfully without `agent_type`.
- Native read-only sub-agents completed successfully. No fallback-only workflow
  was needed.
- The prompt-local files
  `striatum/striatum-memory-rfc-alignment-2026-05-14/FINAL_SYNTHESIS.md`,
  `FINDINGS_LEDGER.md`, and `REVIEW_contract_coherence_repair.md` were absent.
  The matching review artifacts were read from
  `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/`.
- Pre-existing dirty worktree entries were present before this pass:
  `CHANGELOG.md`, `OPERATOR_REPORT.md`, and the untracked Striatum alignment
  prompt directory. They were not edited.
- Later status output also showed out-of-scope edits to RFC 0047 and RFC 0049.
  They were not made by this RFC 0048 patch and were left untouched.
