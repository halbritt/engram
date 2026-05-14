# RFC 0049 Alignment Handoff
author: operator [self-declared: alignment-roadmap-index]

Status: alignment handoff
Date: 2026-05-14
Run ID: run_169531d5568248ff8f0dfc803d955311
Job ID: align_rfc0049_evaluation_gates
Scope: RFC 0049 proposal-text alignment only. This artifact does not promote,
accept, implement, publish, complete, verdict, commit, push, or authorize
routine Striatum memory use.

## Findings Addressed

- F009 / CC-009 follow-up: EG-020 now distinguishes banned external,
  non-loopback, or unpaired HTTP/network dependencies from paired loopback
  HTTP/local runtimes with explicit no-egress evidence.
- F009 gate-status consistency: EG-020 now uses `not_run` for unattempted
  sandbox evidence and reserves `blocked_upstream` for unresolved upstream
  contracts.
- F014 / CC-010 follow-up: RFC 0049 now requires exact-reference coverage to
  mirror RFC 0045's `ref_kind` vocabulary, including `workflow_job_id` and
  `job_id`, and prevents lexical/vector fallback from satisfying exact-reference
  gates.
- F017 cleanup: RFC 0049 no longer treats the redaction-state vocabulary as an
  open RFC 0045 decision; the remaining open issue is exact privacy-tier
  assignment policy before export.
- Cross-RFC gate consistency: RFC 0049 now aligns withheld fixtures with RFC
  0045, adds RFC 0046 health signals for embedding skips and copied-field
  mismatches, scopes `identity_leak`/`citation_leak` as gate-local until RFC
  0048 reconciles them, avoids `omitted` as a packet status, and separates Level
  2 opt-in audit reconstruction from Level 3 default-on reconstruction.

## Findings Deferred

- RFC 0046 still needs the actual `striatum_references` vocabulary alignment for
  `workflow_job_id` and `job_id`; RFC 0049 only tightens the gate dependency.
- RFC 0046 still owns `striatum_embedding_skips` invalidation semantics; RFC
  0049 now requires health evidence but does not define the projection schema.
- RFC 0047 bundle identity examples, unauthorized metadata redaction, and
  pair-mismatch response shape remain RFC 0047 follow-up.
- RFC 0048 audit/default-on wording, manual paste-through policy, omission
  reason vocabulary, and session-disable persistence remain RFC 0048 follow-up
  or explicit deferral.
- Generated memory products remain blocked from Level 2/Level 3 injection until
  a separate accepted privacy-inheritance, citation, and audit contract exists.
- Roadmap/index cleanup and any binding architecture decisions remain out of
  this job's write scope.

## Files Changed

- `docs/rfcs/0049-striatum-evaluation-gates.md`
- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0049.md`

## Dependency Impact

- RFC promotion: RFC 0049's text blockers for EG-020 wording, exact-reference
  coverage, and stale redaction open-decision text are reduced. Promotion still
  depends on accepted/promoted RFC 0045-RFC 0048 successors or explicit scoped
  successors, plus passing gates.
- Implementation: no implementation is authorized. Future implementation must
  still prove local no-egress for every corpus-reading caller and paired runtime,
  exact-reference coverage, redaction behavior, stale-index health, audit
  privacy, and disable controls.
- Routine Striatum use: unchanged. Level 3 default-on automatic memory remains
  blocked; Level 1 manual/local search remains only a future scoped possibility
  under RFC 0049 constraints.

## Validation

- `git diff --check -- docs/rfcs/0049-striatum-evaluation-gates.md`: passed
  with exit code 0 and no output before this handoff was written.
- `make check-refs`: passed with exit code 0; summary was 0 errors, 5 existing
  warnings, 191 checks ok.
- `git diff --check -- docs/rfcs/0049-striatum-evaluation-gates.md
  docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0049.md`:
  passed with exit code 0 and no output after this handoff was written.
- `git diff --check --no-index -- /dev/null
  docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0049.md`:
  produced no whitespace output; exit code 1 is expected for a no-index diff
  comparing `/dev/null` with a present file.
- Final `make check-refs`: passed with exit code 0; summary was 0 errors, 5
  existing warnings, 191 checks ok.

## Workflow Friction

- Native read-only sub-agents were available and used for four independent
  checks: RFC 0049 wording, cross-RFC consistency, synthesis/ledger disposition,
  and reference integrity. No sub-agent edited files.
- The prompt-named review inputs were not at
  `striatum/striatum-memory-rfc-alignment-2026-05-14/`; the workflow file points
  to `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINAL_SYNTHESIS.md`,
  `FINDINGS_LEDGER.md`, and `REVIEW_contract_coherence_repair.md`, which were
  used.
- The target review directory did not exist and was created for this required
  handoff artifact.
- The shared worktree contained out-of-scope changes outside this job's allowed
  paths during final status checks, including `CHANGELOG.md`,
  `OPERATOR_REPORT.md`, RFC 0047/RFC 0048 files, and the Striatum run input
  directory. They were left untouched.
