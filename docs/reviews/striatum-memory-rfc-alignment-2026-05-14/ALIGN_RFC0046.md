# RFC 0046 Alignment Handoff
author: operator [self-declared: alignment-rfc0046]

Status: alignment_handoff
Date: 2026-05-14
Run ID: run_169531d5568248ff8f0dfc803d955311
Workflow job ID: align_rfc0046_projection_index
Scope: RFC 0046 proposal text only

## Summary

This alignment updates RFC 0046 proposal text after the Striatum memory roadmap
final synthesis and contract-coherence repair re-review. It does not implement
code, migrations, tests, generated schema docs, runtime behavior, RFC promotion,
Striatum state transitions, or default operator use.

The edits align RFC 0046 with the current RFC 0045/RFC 0049 vocabulary for
workflow/job exact references, make `striatum_embedding_skips` directly
invalidation-addressable, and mirror RFC 0045 dirty-working-tree opt-in
semantics into projection behavior.

## Findings Addressed

- F014 / CC-007 / CC-010: added `workflow_job_id` and `job_id` to RFC 0046's
  exact-reference vocabulary, query surface wording, validation expectations,
  and downstream RFC 0049 dependency text.
- F015 / CC-004: added `is_active`, `invalidated_at`, and
  `invalidation_reason` to `striatum_embedding_skips`; clarified that skip rows
  satisfy activation/completeness only when active, non-invalidated, and joined
  to same-generation active chunk/item rows.
- F002: added projection-side dirty-working-tree behavior. RFC 0046 now states
  that dirty evidence projects only after RFC 0045 validation accepts manifest
  opt-in and row-level `provenance.dirty_working_tree=true`; derived rows copy
  `source_dirty_working_tree=true` and must remain distinguishable from clean
  committed evidence.

## Findings Deferred

- F001, F003, F004, F008, F010, F011, F013, F016, F019, and F022 remain outside
  this RFC 0046 write scope and belong to RFC 0047/RFC 0048 or later privacy,
  audit, and operator-ergonomics work.
- F007 remains an implementation prerequisite rather than a text gap: RFC 0044
  Phase 0 hardening or RFC 0049 EG-000-equivalent evidence is still required
  before projection implementation.
- F017 and F018 remain cleanup items for a later promotion packet or roadmap
  cleanup workflow.

## Files Changed

- `docs/rfcs/0046-striatum-projection-index-schema.md`
- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0046.md`

## Dependency Impact

RFC promotion: RFC 0046's known projection/index alignment blockers from F014,
F015, and the RFC 0046 side of F002 are addressed at proposal-text level. This
does not promote RFC 0046 and does not resolve unrelated RFC 0047/RFC 0048/RFC
0049 follow-ups.

Implementation: no implementation is authorized. Later migration/projection
work must still prove RFC 0044 Phase 0 or EG-000-equivalent hardening,
RFC 0045 final V2 contract acceptance, no-egress evidence, dirty-export
fixtures, skip invalidation tests, and exact workflow/job lookup coverage.

Routine Striatum use: unchanged. Default-on Level 3 automatic memory remains
blocked until accepted/promoted RFC 0045-RFC 0048 successors exist and all
applicable RFC 0049 gates pass.

## Validation

Command:

```sh
git diff --check -- docs/rfcs/0046-striatum-projection-index-schema.md docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0046.md
```

Result: passed with exit code 0 and no output.

References/anchors: no existing references or anchors were changed, so
`make check-refs` was not required.

## Workflow Friction

- The first native sub-agent spawn attempt used both a full-history fork and an
  explicit explorer role; the tool rejected that combination. The retry used
  isolated read-only explorer agents successfully.
- The requested input synthesis/review artifacts live under
  `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/`, while the requested
  alignment artifact path is
  `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/`. This handoff writes
  the requested alignment path and cites the roadmap-review inputs by scope.
