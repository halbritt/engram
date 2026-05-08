<a id="rfc-0024"></a>
# RFC 0024: Phase 4 Pre-Full-Corpus Benchmark Gate

Status: proposal
Date: 2026-05-08
Context: Phase 4 entity canonicalization, `current_beliefs`, and belief review queue preflight before a full-corpus build
Decision refs:
  - D006
  - D007
  - D017
  - D020
  - D021
  - D034
  - D044
  - D052
  - D055
  - D068
  - D069
  - D074
Review refs:
  - REVIEW-0032
  - REVIEW-0033
Phase refs:
  - PHASE-0003
  - PHASE-0004

## Summary

Phase 4 should not begin with an unbounded full-corpus entity/review build.
Before processing the complete Phase 3 belief set, run a bounded benchmark
gate over the Phase 4 surfaces: entity canonicalization, entity-edge queries,
`current_beliefs`, and the belief review queue.

The gate should answer whether the Phase 4 design is correct, fast enough, and
reviewable at human scale before it can create a large review backlog or bake a
bad canonicalization policy into downstream `context_for` work.

This RFC does not authorize changing inference backends, model profiles, or
Phase 3 extraction defaults. The recent local speed findings only support
larger fixed-slice validation of the `max_tokens=6144` extraction candidate;
they do not justify promoting `ubatch=2048`, request concurrency, or a new
segmentation profile.

## Background

Phase 3 produced grounded candidate beliefs and made no automatic promotion to
`accepted` per [D044](../DECISION_LOG.md#d044). Phase 4 is where those beliefs
become human-reviewable and queryable through canonical entities:

- `entities` and `entity_edges`;
- a `current_beliefs` materialized view;
- a review queue with `accept`, `reject`, `correct`, and
  `promote-to-pinned`;
- 1-2 hop entity-neighborhood queries using recursive CTEs;
- optional local-LLM entity-disambiguation tiebreaks.

Those surfaces have a different risk profile from Phase 3. A bad extractor run
can be retried and superseded. A bad Phase 4 run can flood the human review
queue, merge unrelated people or projects, hide duplicate identities behind a
single canonical row, or make `current_beliefs` appear authoritative before
its status and refresh semantics are correct.

[REVIEW-0033](../reviews/v1/LOCAL_INFERENCE_SPEED_FINDINGS_2026_05_08.md)
also showed that local inference speed changes need same-slice quality gates.
For extraction, the only promising speed change was reducing max output tokens
from `8192` to `6144` on the current single-slot `ik_llama` profile; that was
measured on only 24 segments and requires a larger validation slice. For
segmentation and server flags, the recent benchmark rejected `ubatch=2048` and
multi-slot serving as production changes.

The Phase 4 benchmark should therefore focus on Phase 4 quality and operating
shape, while keeping the known-good local runtime profile unless a separate
same-slice benchmark promotes a narrower change.

## Goals

1. Gate full-corpus Phase 4 execution behind bounded evidence.
2. Measure entity canonicalization precision, merge/split behavior, and audit
   provenance before entity rows become downstream dependencies.
3. Verify `current_beliefs` semantics, refresh behavior, and query plans
   before Phase 5 consumes the view.
4. Validate the review queue as a human workflow, including correction-as-
   capture and status transitions through the D052 transition API.
5. Benchmark 1-2 hop recursive CTE entity-neighborhood queries at realistic
   V1 scale without introducing a graph backend.
6. Preserve Engram's local-first and redaction contracts: no corpus text,
   prompts, completions, titles, or belief values in committed artifacts.

## Non-Goals

1. Do not run the full Phase 4 corpus as the benchmark itself.
2. Do not auto-promote beliefs to `accepted`.
3. Do not introduce hosted inference, web search, telemetry, or external
   persistence.
4. Do not promote `ubatch=2048`, parallel serving, vLLM, sglang, or any new
   inference backend from the Phase 4 gate.
5. Do not require a graph database for V1.
6. Do not use private corpus content in committed benchmark reports. Aggregate
   counts, timings, error classes, ids, and redacted examples are sufficient.

<a id="benchmark-ladder"></a>
## Benchmark Ladder

### Tier 0: Schema And Workflow Smoke

Purpose: prove the Phase 4 implementation can run end-to-end on a tiny slice
without corrupting Phase 3 data.

Recommended scope:

- 25-50 candidate beliefs;
- deterministic slice file recorded under `.scratch/`;
- local-only runtime;
- no full-corpus writes unless the command supports a dry-run or scratch mode.

Required checks:

- migrations apply from an empty and upgraded database;
- `current_beliefs` returns status-aware current rows only;
- review actions produce the expected `belief_audit` rows;
- `correct` inserts a new `captures` row and does not mutate raw evidence;
- entity rows and edges can be rebuilt from the same inputs without duplicate
  active rows;
- no raw content appears in committed reports.

Verdict: smoke pass or fail only. Tier 0 cannot authorize full-corpus Phase 4.

### Tier 1: Bounded Quality And UX Gate

Purpose: decide whether the Phase 4 implementation is ready for a larger
operational run.

Recommended scope:

- about 200 hand-labeled or human-reviewed entity mentions, matching O003's
  evidence target;
- 50 review-queue items, matching O005's feedback-richness question;
- a fixed belief slice that includes identity, preference, project status,
  task, relationship, and event-shaped predicates;
- deterministic synthetic graph rows large enough to stress 1-2 hop recursive
  CTEs without depending on private corpus labels.

Required metrics:

- entity pair precision/recall on same-entity vs different-entity labels;
- false-merge count, false-split count, and uncertain/tiebreak count;
- local-LLM tiebreak invocation rate, if used;
- entity-edge insert/update counts and rebuild idempotency;
- `current_beliefs` refresh wall time and query p50/p95;
- recursive CTE p50/p95 for one-hop and two-hop neighborhood queries;
- review action latency and audit completeness;
- correction capture count and downstream reprocessing queue count;
- queue item count by action outcome.

Promotion gates:

- zero known false merges in the hand-labeled set;
- false splits are reviewable and do not hide evidence;
- `current_beliefs` filters out rejected, superseded, and closed beliefs;
- all review actions preserve D017 and D052 invariants;
- no recursive CTE query has a pathological plan on the synthetic scale test;
- no local-LLM tiebreak result becomes unaudited load-bearing state.

### Tier 2: Bounded Production Preflight

Purpose: exercise the real database shape with production code, but still
avoid a full-corpus commitment.

Recommended scope:

- `--limit 500` or an equivalent bounded Phase 4 run;
- the same production database and model endpoint intended for the full run;
- aggregate-only committed report under `docs/operations/phase4-build/`;
- Striatum state as the authoritative gate state per D074.

Required checks:

- no failed or in-flight Phase 4 jobs after completion;
- no duplicate active canonical entities for the same canonical key;
- no entity row loses provenance/version metadata required by D021;
- `current_beliefs` refreshes cleanly after the run;
- review queue size and item distribution are human-operable;
- all correction actions remain queued for reprocessing, not silent mutation;
- p95 query latency for `current_beliefs` and 1-2 hop entity queries remains
  within the target set by the implementation spec.

Only after Tier 2 passes should an operator consider full-corpus Phase 4.

## Inference Recommendations

Phase 4 may need local LLM calls for entity-disambiguation tiebreaks, but the
default path should be deterministic candidate generation plus auditable
tiebreak only where deterministic evidence is insufficient.

Use the current conservative `ik_llama` systemd profile for Phase 4 preflight:

```text
--ctx-size 49152
--parallel 1
--batch-size 2048
--ubatch-size 512
--cache-type-k q8_0
--cache-type-v q8_0
```

Do not promote the recently tested alternatives:

- `ubatch=2048` improved raw prefill in `llama-bench` but failed end-to-end
  segmentation gates and slowed extraction on the tested slice;
- `parallel=2` and higher client concurrency did not improve extraction wall
  time and reduced claim throughput;
- segmentation `max_tokens=2048` is only a 10-parent smoke signal, not a
  decision-grade result.

The one promising extraction optimization, `max_tokens=6144`, should get its
own 100-segment fixed-slice validation before any future Phase 3 re-extraction
or Phase 4-dependent rebuild relies on it. That validation is adjacent to this
RFC, not a prerequisite for Phase 4 schema and review-queue benchmarking.

## Artifact And Privacy Rules

Committed Phase 4 benchmark artifacts may include:

- run ids, commit ids, command lines, environment variables, and server flags;
- aggregate counts, timings, status distributions, and error classes;
- redacted ids for entity/belief rows where needed for reproducibility;
- EXPLAIN summaries with table/index names and row counts.

Committed artifacts must not include:

- raw corpus text;
- model prompts or completions containing private data;
- conversation titles;
- belief values, claim values, entity names, or relationship labels from the
  private corpus;
- home-directory absolute paths.

Scratch artifacts with private content remain under ignored `.scratch/` or
`logs/operational/` paths and are summarized through redacted reports only.

## Required Report Shape

Each benchmark tier should produce a report with:

```md
# Phase 4 Benchmark <tier> Findings

Status: findings
Date: YYYY-MM-DD
RFC refs:
  - RFC-0024
Decision refs:
  - D006
  - D007
  - D017
  - D044
  - D052
  - D069
Phase refs:
  - PHASE-0004

## Redaction Boundary
## Inputs
## Commands
## Results
## Findings
## Recommendation
## Evidence Artifacts
```

Top-level review-style benchmark reports should receive a `REVIEW-####` id and
an entry in `docs/artifacts/review-id-registry.md`. Operational run reports
should live under `docs/operations/phase4-build/<loop_id>/reports/`.

## Promotion Criteria

Full-corpus Phase 4 execution is ready only when all of the following hold:

1. The Phase 4 spec has passed the multi-agent review loop in
   `prompts/phase4/workflow.json`.
2. Tier 0 and Tier 1 pass with no blocking findings.
3. Tier 2 bounded production preflight completes with no failed jobs and no
   human-checkpoint blocker.
4. Entity canonicalization has zero known false merges on the labeled set.
5. `current_beliefs` semantics are status-aware and verified against Phase 3
   lifecycle rules.
6. Review queue actions preserve correction-as-capture and transition-audit
   invariants.
7. Recursive CTE neighborhood queries are fast enough on realistic scale data.
8. The final recommendation is recorded in a committed findings report, with
   any accepted architectural deltas promoted through `DECISION_LOG.md`.

## Open Questions

1. What exact latency targets should Phase 4 set for `current_beliefs` and
   1-2 hop entity-neighborhood queries?
2. What is the minimum human-labeled entity set that gives enough confidence
   to catch false merges before full-corpus processing?
3. Should the review queue benchmark use only candidate beliefs, or include a
   small number of provisional/accepted fixtures to test status transitions?
4. Does Phase 4 need a separate entity-audit table, or is provenance on
   `entities` / `entity_edges` plus `belief_audit` sufficient?
5. Should local-LLM entity tiebreaks write a dedicated raw diagnostic payload
   or a first-class audit row?
