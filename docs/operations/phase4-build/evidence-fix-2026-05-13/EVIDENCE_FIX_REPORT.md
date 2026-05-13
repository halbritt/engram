---
schema_version: "striatum.handoff.v1"
artifact_kind: "handoff"
---

# Phase 4 Evidence-Fix Report Scaffold
author: operator [self-declared: phase4-evidence-fix-scaffold-codex]

Status: scaffold
Date: 2026-05-13

RFC refs:
  - RFC-0024
  - RFC-0021
  - RFC-0025

Decision refs:
  - D006
  - D007
  - D017
  - D020
  - D021
  - D044
  - D052
  - D074
  - D077
  - D078

Phase refs:
  - PHASE-0004

## Boundary

This is a bounded evidence-fix scaffold. It does not promote Phase 4, does not
authorize full-corpus Phase 4, and does not run any corpus-scale job. Future
Tier 2 work remains capped at `--limit 500` or an equivalent deterministic
fixed slice.

Committed outputs from this loop may contain aggregate counts, command shapes,
test outcomes, timing summaries, schema relation names, redacted identifiers,
and finding ids. They must not contain raw corpus text, model prompts,
completions, conversation titles, belief values, claim values, entity names,
relationship labels, private values, credentials, or home-directory absolute
paths.

Private slice files, raw operator notes, and any item-level label material stay
in ignored local scratch or diagnostics paths. The committed report only
summarizes aggregates.

## Inputs

Required inputs for the evidence-fix loop:

- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/FINAL_GATE_REVIEW.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/PROMOTION_SYNTHESIS.md`
- `docs/operations/phase4-build/tiered-gate-multilane-2026-05-13/FINDINGS_LEDGER.md`
- `docs/rfcs/0024-phase-4-pre-full-corpus-benchmark-gate.md`
- `docs/rfcs/0021-gold-set-interview-curation.md`
- `docs/rfcs/0025-phase-scoped-command-names.md`
- `migrations/009_phase4_entities_review.sql`
- `src/engram/phase4.py`
- `src/engram/cli.py`
- `tests/test_phase4_entities_review.py`
- `tests/test_cli.py`
- `tests/test_interview_cli.py`
- `tests/test_interview_sampler.py`
- `tests/test_interview_storage.py`
- `Makefile`

## Carried Findings

The evidence-fix loop starts from the prior normalized findings, not from a
promotion posture. Blocking findings P4-GATE-L001 through P4-GATE-L016 remain
open until the loop produces passing evidence or an explicit owner decision.
Positive boundary findings P4-GATE-L017 and P4-GATE-L018 remain constraints to
preserve, not promotion authority.

Priority order:

1. Resolve P4-GATE-L002 by initializing or verifying the local Python
   environment and running the Phase 4 pytest surface.
2. Resolve the executable Tier 0 gap by planning and then running only
   `make phase4-smoke LIMIT=25` after tests pass.
3. Resolve P4-GATE-L003, P4-GATE-L004, and P4-GATE-L011 with an RFC
   0021-aligned human-label and entity-pair slice.
4. Resolve P4-GATE-L005 and P4-GATE-L006 with live accept, reject, correct,
   and promote-to-pinned review-action evidence.
5. Address P4-GATE-L007 through P4-GATE-L015 with projection, provenance,
   lifecycle, append-only trigger, and CTE-scale evidence or explicit follow-up
   decisions.
6. Resolve P4-GATE-L016 with a multi-lane review of the evidence-fix result or
   an explicit owner provenance decision.

## Environment And Pytest Surface

Run from the repository root. These commands are environment and test evidence
only; they are not a Phase 4 corpus run.

```sh
test -x .venv/bin/python || make install
.venv/bin/python -V
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_phase4_entities_review.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_cli.py -k phase4
```

Optional RFC 0021 regression surface for the label substrate:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_interview_cli.py tests/test_interview_sampler.py tests/test_interview_storage.py
```

The report should capture Python version, command exit status, test counts,
and failure classes only. It should not paste full stack traces when they
contain private environment details; summarize the failure class and keep raw
logs in ignored diagnostics if needed.

## Live Tier 0 Smoke Plan

Tier 0 smoke is eligible only after the pytest surface above passes or its
failures are explicitly classified as unrelated to Phase 4 gate behavior.

Allowed live command:

```sh
make phase4-smoke LIMIT=25
```

Equivalent direct command, if Make indirection is unsuitable:

```sh
ENGRAM_DATABASE_URL="$ENGRAM_DATABASE_URL" .venv/bin/python -m engram.cli phase4 smoke --limit 25
```

Required aggregate evidence:

- command exit status;
- bounded limit used;
- current-belief count produced or refreshed;
- review-queue item count;
- entity and edge created/reused counts;
- duplicate active canonical-key count;
- duplicate active-edge count;
- review action count before and after the smoke;
- confirmation that no raw evidence row was updated or deleted;
- confirmation that the committed report includes no private values.

Forbidden in this loop: `engram phase4 run`, unbounded
`engram phase4 build-entities`, unbounded Make targets, generic `pipeline`
commands, or any hosted inference / network egress path.

## RFC 0021-Aligned Entity-Pair Slice

RFC 0021 labels claims and beliefs, while RFC 0024 needs entity-pair quality
evidence. The bridge for this evidence-fix loop is a local-only slice ledger:
item-level pair rows stay in ignored scratch, and committed artifacts report
only aggregate counts.

Minimum slice target:

- about 200 human-reviewed entity mentions, matching RFC 0024 and O003;
- a balanced same-entity vs different-entity pair set where feasible;
- coverage for identity, preference, project status, task, relationship, and
  event-shaped predicates or stability classes;
- explicit counts for false merge, false split, uncertain/tiebreak, excluded
  unsupported target, and reviewed-clean pairs.

Slice construction:

1. Use `current_beliefs` as the default candidate source, preserving D077
   status filtering.
2. Stratify candidates by `stability_class`, predicate shape, confidence band,
   recency band, and belief status.
3. For each pair, require the underlying claim or belief targets to have an
   RFC 0021 gold-label verdict where practical. If no label exists, either
   collect it through `engram phase3 interview start` or mark the pair
   `label_missing` and keep it out of promotion denominators.
4. Store local item-level pair decisions in ignored scratch. Each row should
   carry redacted pair ids, target kinds, target ids, version triples,
   human pair verdict (`same`, `different`, `uncertain`, or `exclude`),
   optional false-merge or false-split classification, and source gold-label
   session ids.
5. Commit only aggregate coverage tables and denominator definitions.

Allowed RFC 0021 commands:

```sh
engram phase3 interview start --n 50 --seed 20260513 --non-interactive
engram phase3 interview start --n 50 --seed 20260513
engram phase3 interview coverage --strata stability_class
engram phase3 interview export --format jsonl
```

The default export ceiling is Tier 1. Higher tiers require explicit operator
opt-in and must not be copied into committed reports.

## Review-Action Evidence

Collect one bounded action sample across all Phase 4 review primitives:

- accept;
- reject;
- correct;
- promote-to-pinned.

Allowed command shape:

```sh
engram phase4 review-belief <redacted-belief-id> accept --actor local --note "<redacted note>"
engram phase4 review-belief <redacted-belief-id> reject --actor local --note "<redacted note>"
engram phase4 review-belief <redacted-belief-id> correct --actor local --note "<redacted correction>"
engram phase4 review-belief <redacted-belief-id> promote-to-pinned --actor local --note "<redacted note>"
```

The committed report should publish only:

- action counts by action kind and action status;
- `belief_audit` row count by transition kind;
- `belief_review_actions` row count by action kind and status;
- correction `captures` count and queued reprocessing count;
- pinned-belief count;
- p50/p95 action latency, if measured;
- current/review projection counts before and after refresh.

Do not commit notes, correction text, belief values, entity names, or raw ids.

## Projection And Provenance Gaps

This scaffold cannot edit code or canonical docs. It should still force each
projection/provenance gap into one of three outcomes: resolved by evidence,
requires code/spec change, or explicit owner decision required.

Minimum gap ledger:

| Finding | Required evidence or decision |
|---|---|
| P4-GATE-L007 | Prove provisional and accepted inclusion plus rejected, closed, superseded, and historical exclusion from `current_beliefs`. |
| P4-GATE-L008 | Decide whether candidate-derived graph state must carry source belief status or be filtered before graph build. |
| P4-GATE-L009 | Decide whether pending corrections are surfaced, filtered, or accepted as temporarily visible until reprocessing. |
| P4-GATE-L010 | Prove entity/edge reuse provenance completeness or define arrays as seed provenance and add append-only reuse evidence elsewhere. |
| P4-GATE-L012 | Run realistic synthetic one-hop and two-hop recursive CTE p50/p95 timing, separate from private corpus labels. |
| P4-GATE-L013 | Record that stale `BUILD_PHASES.md` wording remains a documentation fix outside this write scope. |
| P4-GATE-L014 | Prove rejected/superseded reactivation is impossible, correctly clears lifecycle fields, or is intentionally invisible. |
| P4-GATE-L015 | Verify append-only triggers, not just append-only functions, for `entity_resolution_events`, `belief_review_actions`, and `pinned_beliefs`. |
| P4-GATE-L016 | Use multi-lane review or owner decision before any promotion claim relies on this evidence. |

## Tier 2 Guardrail

Tier 2 remains ineligible until this evidence-fix loop records Tier 0 and Tier
1 passing evidence or explicitly carries unresolved blockers forward. If Tier
2 becomes eligible, it must use a bounded command shape:

```sh
engram phase4 build-entities --limit 500
make phase4-build-entities LIMIT=500
```

Equivalent fixed-slice alternatives are acceptable only if the deterministic
slice definition is recorded and the committed report remains aggregate-only.

Tier 2 must still prove:

- no failed or in-flight Phase 4 jobs after completion;
- no duplicate active canonical entities for the same canonical key;
- no entity or edge row loses D021 provenance/version metadata;
- `current_beliefs` refreshes cleanly after the bounded run;
- review queue size and distribution remain human-operable;
- correction actions remain queued for reprocessing, not silent mutation;
- p95 query latency for `current_beliefs` and entity neighborhood queries is
  reported against the chosen target.

## Result Template

When the loop executes, replace this scaffold status with one of:

- `blocked` - environment, tests, smoke, label substrate, review actions, or
  projection/provenance evidence could not complete;
- `findings` - evidence was collected but one or more blockers remain;
- `ready-for-tier2-bounded-preflight` - Tier 0 and Tier 1 evidence pass with
  no blocking finding and Tier 2 remains capped at `--limit 500`;
- `human-checkpoint` - owner decision is needed before proceeding.

The result must not be labeled `promotion` unless RFC 0024 promotion criteria
are all satisfied by later evidence and a final committed review says so.

## Evidence Artifacts

This scaffold pairs with:

- `striatum/phase-4-evidence-fix-2026-05-13/workflow.json`

Future workflow outputs should remain under:

- `docs/operations/phase4-build/evidence-fix-2026-05-13/`
