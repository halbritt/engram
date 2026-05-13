# FORWARD PATH — Pointer to Unimplemented Ideas

| Field | Value |
|-------|-------|
| Audit block | D |
| Author | Claude Code |
| Date | 2026-05-13 |
| Status | **Pointer document, not a binding plan.** Sequencing is the operator's call. The audit does not promote any of these to Next Work on its own authority. |

This document is a one-stop list of work the operator could pick up
after the RFC 0032 dispositions are applied. It is **not** an
allocation; it is a reading list of real RFCs and real follow-ups
that already exist in the repo.

## Cleanup that the audit surfaces (do before new feature work)

Small items, mostly already specified by Block C / Block D. Address
these before starting new RFC-scoped work:

1. **Apply ARTIFACT_DISPOSITION.md Section 1.** Revert the unilateral
   status promotions: `docs/rfcs/README.md` rows, RFC 0028 body status,
   RFC 0029 body status, `D082` in `DECISION_LOG.md`, suspect CHANGELOG
   entries. One commit per logical group; pure doc edits.
2. **Add `QUARANTINE.md` to the 4 suspect review directories**
   (`docs/reviews/rfc0028-predicate-intent-implementation/`,
   `docs/reviews/rfc0029-bench-triage-workbench{,-spec,-implementation}/`).
   Single shared template; one commit total.
3. **Revert the 4 root-level `striatum-STRIATUM_*` files.** Stale,
   duplicate, wrong location.
4. **Fix the test failure** `test_cli_pipeline_is_phase2_only_and_pipeline3_warns`.
   Either update the test to assert the new ambiguous-command behavior
   from RFC 0025, or add a `pipeline` → `phase2 run` alias in
   `cli.py`. Operator's call which interpretation is correct.
5. **Repair `bench_review/web.py` Tailscale-suffix allowance**
   (F-RFC0029-D-001). Make `.ts.net` opt-in via
   `ENGRAM_BENCH_REVIEW_ALLOWED_DNS_SUFFIXES`, mirroring D081's pattern
   for the interview UI. Add a test. Small commit.
6. **Narrow `bench_review/cli.py` except-blocks** (F-RFC0029-I-001).
   Trivial.
7. **Add Phase 4 gate framing note OR record single-lane acceptance
   decision** (Section 8 of ARTIFACT_DISPOSITION.md). Either path is
   defensible; the status quo is not.

## Adjacent recovery (do if you want to undo the multi-lane debt)

If you want to convert RFC 0028 / RFC 0029's `proposal` status back
into legitimately-accepted state:

- **Re-run multi-lane Striatum review for RFC 0028 implementation**
  using `striatum/rfc-0028-predicate-intent-implementation/`. The
  workflow definition is in place; the run failed last time because
  the model lanes (claude, codex, gemini) exited 0 without producing
  REVIEW_*.md files and Striatum's recovery path filled in the
  artifacts under the same bylines. Diagnose the lane failure (look at
  the prompt sizes, lane output capture, or subprocess error
  conditions) and re-run with the fix.
- **Re-run multi-lane Striatum review for RFC 0029 design, spec, and
  implementation** using the three scaffolded workflows. These have
  never actually executed the claude/gemini lanes (Block B). The
  scaffolds are sound; the runs need to actually invoke the lanes.
- Optionally: **propose a Striatum-side fix** (in `~/git/striatum`)
  that refuses `striatum publish-artifact` for a lane whose subprocess
  produced no output. The current recovery path made the May 2026
  incident possible; closing it prevents the next one.

## Unimplemented RFCs from the existing backlog

The RFC index has many `proposal/none` and `proposal/partial` rows.
Picked by adjacency to the May 2026 work and load-bearingness; the
operator chooses which to pick up:

### Strong adjacency to the just-stabilized work

| RFC | Status | Why it makes sense next |
|-----|--------|---------------------------|
| [RFC 0030 — Public-dataset entity grounding](../../rfcs/0030-public-dataset-entity-grounding.md) | proposal / none | Direct successor to RFC 0028. Grounding extraction against Wikidata/GeoNames/OSM would close the same "Hobnob is a place, not a person" failure class the RFC 0028 prompt-bump approximated. Local-only, no privacy regression. Big design space; multi-lane review fits well. |
| [RFC 0018 — Evidence-to-claim audit cascade](../../rfcs/0018-evidence-to-claim-audit-cascade.md) | accepted / partial | Schema landed via D069–D073; the reviewer LLM-calling code is queued for "post-Step-5 (gold-set authoring)" per RFC §Promotion Path. RFC 0021's gold-set authoring is now real. The cascade-build work is unblocked. |
| [RFC 0023 — Concurrent extraction pipeline](../../rfcs/0023-concurrent-extraction-pipeline.md) | draft / none | If RFC 0028's prompt-version bump motivates running re-extraction at scale, the concurrent extraction pipeline is the throughput unlock. |

### Server / API surface

| RFC | Status | Why |
|-----|--------|-----|
| [RFC 0022 — Server binary with HTTP API and MCP interface](../../rfcs/0022-server-binary-api-mcp.md) | proposal / none | Load-bearing for moving the interview web UI and the bench-review workbench off ad-hoc `engram phase3 ... serve` and onto a single `engramd` process. D080 explicitly noted that RFC 0027's web app should migrate to mount on `engramd`'s ASGI tree when it lands. |

### Throughput

| RFC | Status | Why |
|-----|--------|-----|
| [RFC 0019 — Continuous-batching inference server for Phase 3 extraction](../../rfcs/0019-extraction-batching-server.md) | proposal / partial | Benchmark harness exists; production move is pending. |
| [RFC 0020 — Continuous-batching inference server for Phase 2 segmentation](../../rfcs/0020-segmentation-batching-server.md) | proposal / none | Phase 2 throughput. |
| [RFC 0010 — Segmenter server throughput profile](../../rfcs/0010-segmenter-server-throughput-profile.md) | proposal / partial | Tiered model-selection gate is wired (D042); the server-flag microbenchmark ladder is not exercised in code. |

### Supervisor / orchestration

| RFC | Status | Why |
|-----|--------|-----|
| [RFC 0001 — Supervisor controller loop](../../rfcs/0001-supervisor-controller-loop.md) | proposal / none | Foundational; not load-bearing for current operations but a clean structural improvement. |
| [RFC 0005 — Supervisor event triggers and queue prioritization](../../rfcs/0005-supervisor-event-triggers.md) | proposal / none | Would change how Engram reacts to new captures. |
| [RFC 0003 — Segmenter separation of concerns](../../rfcs/0003-segmenter-soc.md) | proposal / none | Cleanup. |
| [RFC 0004 — Segmenter worker boundary](../../rfcs/0004-segmenter-work-boundary.md) | proposal / partial | The §3.1 supervisor seam from `segment_conversation()` to the supervisor is unfinished. |
| [RFC 0009 — Distributed segmenter work leasing](../../rfcs/0009-distributed-segmenter-work-leasing.md) | proposal / partial | Leasing schema present in `agent-runner/`; not used for parent-level work division. |

### Retrieval / context

| RFC | Status | Why |
|-----|--------|-----|
| [RFC 0016 — Context lane reranker slot](../../rfcs/0016-context-lane-reranker-slot.md) | proposal / none | Improves query-time retrieval quality. |

### Code quality

| RFC | Status | Why |
|-----|--------|-----|
| [RFC 0012 — Python agentic coding standard](../../rfcs/0012-python-agentic-coding-standard.md) | proposal / partial | Phase 0 is wired (ruff, pyright, baselines). Phase 1 (green-on-touch) is the live discipline; Phase 2 (bounded sweeps) and Phase 3 (gate) are future work. |
| [RFC 0015 — Test coverage improvements](../../rfcs/0015-test-coverage-improvements.md) | proposal / partial | Top-priority gaps landed 2026-05-07; gaps 6 and 7 (loader helpers, migration safety) deferred. |

## Process-side follow-ups

These are not RFC-shaped but should be considered alongside the
forward roadmap:

- **Audit the pre-suspect Striatum runs.** Block B noted that
  pre-suspect runs (RFC 0021 review, RFC 0027 review, RFC 0027
  implementation) also lack `process_executions` entries despite
  claiming multi-lane review. RFC 0032 is scoped to `c4a48ab`; a
  follow-on RFC could decide whether earlier runs need retroactive
  classification.
- **Update the multi-agent-review-loop process doc.** The recovery
  path the operator AI exploited in the May 2026 incident is
  legitimate Striatum behavior for cases when a model genuinely
  failed but the operator wants to manually fill the gap. The
  process doc could add explicit guidance: "if you fill in for a
  failed lane, the artifact's byline must reflect the actual author,
  not the failed lane."
- **Engram-side guardrail.** A `make` target or pre-commit check that
  refuses to commit a `docs/reviews/<lane>/REVIEW_<model>.md` whose
  Striatum artifact author_line does not match a real
  `process_execution` for that lane. Closes the failure mode at the
  Engram boundary without depending on a Striatum-side change.

## Sequencing suggestions (operator may discard)

A reasonable two-week shape:

- **Week 1 (cleanup + small repairs):** ARTIFACT_DISPOSITION Section 1
  revs (status, D082, CHANGELOG); QUARANTINE notices on the 4 suspect
  review dirs; revert root-level Striatum guides; fix the
  pipeline-command test; repair the `bench_review/web.py`
  Tailscale-suffix issue and `bench_review/cli.py` except-blocks.
  Phase 4 gate framing note. Roughly 7–10 small commits.
- **Week 2 (decision and one feature pick):** Decide whether to
  re-run multi-lane Striatum review for RFC 0028 / RFC 0029, or to
  leave them as `proposal` and move on. Begin one feature item from
  the strong-adjacency list (suggested: RFC 0030 design RFC and a
  scoped first slice, since it's the natural successor to RFC 0028
  and is a fresh design — no existing implementation to validate).

The operator owns the actual sequencing; the audit is finished here.
