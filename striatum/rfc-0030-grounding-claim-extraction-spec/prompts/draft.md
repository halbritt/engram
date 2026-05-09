# Draft Spec 0030: Public-Dataset Entity Grounding Implementation Contract

Author `docs/specs/0030-public-dataset-entity-grounding-spec.md` as the
implementation contract derived from the revised RFC 0030 and its
design-review synthesis. Pattern: `docs/specs/0027-interview-web-ui-spec.md`
is the most recent comparable spec.

## Inputs (authoritative)

- `docs/rfcs/0030-public-dataset-entity-grounding.md` — the *what* and *why*.
- `docs/reviews/rfc0030-grounding-claim-extraction/REVISION_SYNTHESIS.md`
  — the design positions on D-A through D-H and Q1 through Q7.
- `docs/reviews/rfc0030-grounding-claim-extraction/REVISION_HANDOFF.md`
  — the section-by-section change record + spec-time carryovers.

## Required spec sections

1. **Front-matter** with status `accepted`, source RFC link, decision
   refs (D020, D044, D068, D076, D080), phase refs.
2. **Purpose** — one paragraph naming the operator outcome.
3. **Out of scope** — list, lifted from RFC § Scope plus any spec-time
   exclusions.
4. **Architecture / Modules** — concrete file layout under
   `src/engram/grounding/` (`__init__.py`, `snapshot.py`, `resolver.py`,
   `attachment.py`, `grants.py`, `private_aliases.py`); each module's
   responsibilities; AST-walk test name; single-accessor chokepoint.
5. **Schema** — full DDL for `entity_external_references`,
   `grounding_resolution_set`, `private_aliases` (in production PG);
   `grants`, `grants_audit` (in scratch SQLite). Include indexes,
   triggers, and `superseded_by` semantics.
6. **CLI surface** — exact argparse subparser definitions for:
   `engram grants {list,grant,revoke,apply-template}`;
   `engram grounding {snapshot,rollback,detach,versions,onboarding}`;
   `engram phase3 grounding-bench`. Include exit codes per command.
7. **Resolver contract** — input/output dataclasses; surface-form
   normalization rule (NFKC + lowercase + collapse whitespace);
   determinism contract; cache shape (per-process LRU, 100k entries).
8. **Extractor integration** — exact `EXTRACTION_PROMPT_VERSION` bump,
   candidate-block assembly with the prompt-shape guard sentence,
   per-segment / per-batch budget enforcement, run-summary
   `grounding_status` field.
9. **Bench mechanics** — three-arm bench (Arm A v8, Arm B v9-disabled,
   Arm C v9-grounded), paired metric (false-rate AND coverage),
   pre-registered decision rule (≥30% reduction, ≤5% coverage drop),
   sample sizes (100 sanity / 600 promotion gate), slice spec, gold
   set construction, baseline reproducibility check.
10. **Acceptance criteria** — every "must" clause has a corresponding
    test name (`tests/test_grounding.py::test_*`). At minimum:
    grant enforcement; AST-walk no-http-clients; resolver determinism;
    snapshot integrity; tombstone supersession; cascade integration;
    silent downgrade; lock-file detection.
11. **Test fixture strategy** — synthetic ~10MB content-hashed
    snapshot committed to repo; integration tests opt-in via env var.
12. **Migration plan** — exact migration filename(s),
    `CREATE TABLE`/`CREATE INDEX CONCURRENTLY` annotations,
    idempotency confirmation. Snapshot-internal indexes outside
    production PG (under `~/.engram/grounding/<snapshot>/index/`).
13. **Operator onboarding** — six-step walkthrough specified as the
    `engram grounding onboarding` flow.
14. **Promotion path** — same as RFC; spec authoring → bench (Arm B
    vs Arm C on 600-segment slice) → implementation; explicit
    operator-time cost.

## Discipline

- Every spec contract names the RFC section it implements.
- Do not introduce design choices not present in the RFC or
  synthesis. Carryovers from the synthesis (argparse exact shapes,
  test fixture strategy, test matrix, grounding-bench automation,
  onboarding walkthrough) become spec content.
- Do not include private corpus excerpts.

After the spec, write `docs/reviews/rfc0030-grounding-claim-extraction-spec/SPEC_HANDOFF.md`
with structure:

```md
# Spec 0030 Authoring Handoff
author: <packet author line>

Status: drafted
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Spec sections written

## RFC sections each spec section implements

## Spec-time carryovers from synthesis (now resolved)

## Open spec questions for the review loop

## Validation
- Every RFC 'must' clause has a spec contract.
- Every spec contract has a test name.
- The five non-negotiables are enforced by named code modules.

## Residual risk
```

Update `docs/rfcs/README.md` row for RFC 0030 to status `promoted`
with link to the new spec.

Do not modify implementation files (`src/engram/`, `tests/`,
`migrations/`).
