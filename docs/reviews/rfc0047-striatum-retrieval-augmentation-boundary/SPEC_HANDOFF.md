---
schema_version: "striatum.spec_handoff.v1"
artifact_kind: "spec_handoff"
---

# RFC 0047 Striatum Retrieval Augmentation Boundary Handoff
author: operator [self-declared: roadmap-rfc-author-d]

Status: ready_for_review
Date: 2026-05-14
RFC: 0047
Run ID: run_500d0f049ea04038b0e19d6045daf918
Workflow job ID: rfc0047_augmentation_boundary_handoff
Job ID: job_run_500d0f049ea04038b0e19d6045daf918_rfc0047_augmentation_boundary_handoff
Session ID: sess_cd3830aa0c164905b5fbfba62d9f50a1
Lease ID: lease_dc5d7ce9dca647e099af6b23dc65d1db

## Summary

RFC 0047 has been moved from scaffold to a reviewable Striatum/Engram
retrieval augmentation boundary. The revised RFC defines retrieval as optional
local read-only augmentation, not a Striatum runtime dependency.

The spec preserves RFC 0045 as the upstream corpus contract and states that
memory availability must not be authoritative Striatum state. Engram absence,
failure, timeout, stale indexes, malformed responses, or authorization refusal
degrade to the existing Striatum path.

## Changed Files

- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md`
- `docs/reviews/rfc0047-striatum-retrieval-augmentation-boundary/SPEC_HANDOFF.md`

## Scope Confirmed

- Documentation/RFC authoring only.
- No code, migrations, generated schema docs, tests, review findings, commits,
  `.striatum/`, `DECISION_LOG.md`, `CHANGELOG.md`, or `OPERATOR_REPORT.md`
  were intentionally changed.
- Existing unrelated worktree changes were left untouched.

## Read Context

Required context was read before writing, including:

- `AGENTS.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `STRIATUM_MEMORY_ROADMAP.md`
- `docs/schema/README.md`
- `docs/rfcs/README.md`
- `docs/process/multi-agent-review-loop.md`
- `docs/process/project-judgment.md`
- `docs/rfcs/0045-striatum-corpus-contract-v2.md`
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/FINAL_SYNTHESIS.md`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/FINDINGS_LEDGER.md`
- `/home/halbritt/git/striatum/ENGRAM_DEVELOPER_REQUEST.md`
- `/home/halbritt/git/striatum/docs/rfcs/0044-engram-phase-1-implementation-spec.md`

Read-only sub-agent context gathering covered:

- canonical Engram constraints and review-process expectations;
- RFC 0045 dependency surface and terminology;
- Striatum/Engram runtime-boundary implications and compatibility risks.

## Material Spec Deltas

- Defined the boundary statement and control flow for optional local retrieval.
- Added forbidden control flows that would make Engram authoritative or
  workflow-critical.
- Added allowed invocation surfaces and explicit forbidden surfaces.
- Added logical retrieval request and response contracts.
- Added failure behavior for disabled, unavailable, unhealthy, unauthorized,
  timed out, stale, malformed, uncited, mismatched, low-confidence, and error
  responses.
- Added bounded timeout and retry policy.
- Added no-egress and no-hosted-service boundaries.
- Added tenant/corpus isolation rules, including default Striatum capabilities
  and cross-boundary requirements.
- Added citation, provenance, confidence, stability, authority, freshness,
  cache, rebuild, invalidation, operator UX, and compatibility requirements.

## Deferred Questions

- Exact per-instance `corpus_id` grammar remains with RFC 0045 acceptance or a
  follow-up decision.
- Projection generation identifiers depend on RFC 0046.
- Context-injection budgets, section order, and prompt formatting remain RFC
  0048 scope.
- No-egress sandbox probes, fixture bundles, latency gates, and golden
  retrieval query sets remain RFC 0049 scope.
- Whether a one-shot CLI wrapper should exist in addition to MCP stdio remains
  an implementation-planning decision.
- Whether stale memory should be shown automatically or only on explicit
  operator request should be reviewed with RFC 0048 ergonomics.

## Review Recommendations

Review RFC 0047 as a package with this handoff and RFC 0045. Recommended lanes:

- Striatum runtime independence review.
- Engram capability and tenant/corpus boundary review.
- No-egress and local-only review.
- Operator UX and truthfulness review.
- Recovery-path and failure-mode review.
- RFC 0045 dependency coherence review.
- Implementation-readiness review for both repositories.

Specific review pressure should target RFC 0044 residual risks:

- single-pair authorization and `--allow-pair` semantics;
- `fetch_reference` reauthorization;
- `describe_corpus` and `health` metadata leakage;
- malformed reference handling;
- no-egress evidence scope;
- real or fixture bundle smoke evidence before routine operator use.

## Validation Evidence

Passed docs-only whitespace validation:

```sh
git diff --check -- docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md docs/reviews/rfc0047-striatum-retrieval-augmentation-boundary/SPEC_HANDOFF.md
```

Additional untracked-file whitespace probe for this handoff produced no
whitespace findings. `git diff --check --no-index /dev/null <handoff>` exits
1 because the file differs from `/dev/null`.
