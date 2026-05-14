---
schema_version: "striatum.handoff.v1"
artifact_kind: "spec_handoff"
---

# RFC 0048 Context Injection Policy Handoff
author: operator [self-declared: roadmap-rfc-author-e]

Status: ready_for_review
Date: 2026-05-14
RFC: RFC 0048
Run: run_500d0f049ea04038b0e19d6045daf918
Workflow job: rfc0048_context_policy_handoff
Job: job_run_500d0f049ea04038b0e19d6045daf918_rfc0048_context_policy_handoff
Session: sess_2805f55919b040b69a3d8a4b9eca3463
Lease: lease_7bba165deee54e4b8c55de77feb71752

## Summary

RFC 0048 was moved from scaffold to a reviewable context-injection policy
handoff. The revised RFC defines when retrieved Striatum memory may enter
operator or workflow-agent context and preserves the central constraint:
retrieved memory is evidence/context only, never instructions and never
authoritative Striatum state.

The RFC remains a proposal. It does not implement code, migrations, schema
docs, tests, review findings, decisions, or Striatum UI.

## Changed Files

- `docs/rfcs/0048-striatum-context-injection-policy.md`
- `docs/reviews/rfc0048-striatum-context-injection-policy/SPEC_HANDOFF.md`

## Scope Observed

Allowed write scope was respected:

- RFC 0048 was updated.
- The RFC 0048 review directory was created and this handoff was added.

Forbidden write scope was not touched:

- no `.striatum/` writes;
- no `src/`, `tests/`, or `migrations/` writes;
- no `DECISION_LOG.md`, `CHANGELOG.md`, `OPERATOR_REPORT.md`, or other RFC
  writes.

The existing worktree already had unrelated modified files before this pass;
they were left untouched.

## Context Read

Required context read before writing:

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
- `docs/rfcs/0046-striatum-projection-index-schema.md`
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md`
- `docs/rfcs/0048-striatum-context-injection-policy.md`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/FINAL_SYNTHESIS.md`
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/FINDINGS_LEDGER.md`
- `/home/halbritt/git/striatum/ENGRAM_DEVELOPER_REQUEST.md`

Read-only sub-agent context was used for:

- canonical Engram constraints;
- RFC 0047 runtime-boundary implications;
- RFC 0046 projection/context surfaces;
- Striatum operator ergonomics;
- RFC 0044 tenant/corpus isolation lessons.

## Material Policy Content Added

RFC 0048 now specifies:

- eligible context surfaces;
- manual versus automatic augmentation;
- section labels and packet shape;
- authority and precedence rules;
- instruction-safety and prompt-injection containment;
- citation requirements;
- tenant/corpus, primary-pair, cross-corpus, cross-tenant, personal-memory,
  privacy-tier, visibility, and redaction rules;
- per-surface token budgets and truncation behavior;
- freshness and stale-memory handling;
- disabled, unavailable, unauthorized, timeout, stale, malformed, no-data, and
  error behavior;
- audit-trail fields and omission reason codes;
- per-run, per-session, and per-packet disable controls;
- RFC 0049 gate dependencies before routine default-on automatic injection.

## Validation Evidence

Docs-only validation required before finish:

```sh
git diff --check -- docs/rfcs/0048-striatum-context-injection-policy.md docs/reviews/rfc0048-striatum-context-injection-policy/SPEC_HANDOFF.md
```

Result:

```text
passed with no output
```

Because `SPEC_HANDOFF.md` is a new untracked file, an additional no-index
whitespace check was run against it; it also produced no output.

## Deferred Questions

1. Exact accepted per-instance `corpus_id` grammar remains upstream to RFC 0045.
2. Exact projection generation and chunk identifiers remain upstream to RFC
   0046.
3. Exact Striatum CLI/UI names for disable controls belong to Striatum
   implementation planning.
4. Whether routine automatic injection is default-on for all five non-search
   purposes should wait for RFC 0049 latency and ergonomics evidence.
5. Whether stale memory should enter `operator_startup` automatically needs
   ergonomics review.
6. Whether generated memory products can enter automatic injection before
   separate audit gates remains deferred.
7. Whether citations live inline only or also in a structured sidecar depends
   on future packet format.

## Review Recommendations

Review RFC 0048 as a package with this handoff and the upstream proposal RFCs.
Recommended lanes:

- operator ergonomics and context-quality review;
- provenance/truthfulness review;
- prompt-injection and instruction-safety review;
- tenant/corpus and privacy-boundary review;
- Striatum runtime-independence review;
- packet-budget and truncation review;
- RFC 0049 gate-readiness review.

Blocker candidates for review:

- any path where memory can become instructions;
- any path where memory can override current repository or Striatum state;
- any uncited injected memory;
- any default personal-memory injection;
- any hidden cross-corpus or cross-tenant read;
- any prompt dump or raw log injection path;
- any routine automatic injection before RFC 0049 evidence gates.
