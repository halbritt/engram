# Spec 0030 Authoring Handoff

author: author-codex-gpt-5.5-001

Status: drafted
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Spec sections written

The spec at `docs/specs/0030-public-dataset-entity-grounding-spec.md`
contains the following sections, all required by the draft prompt's
required-sections list:

1. Front-matter (Status / Source RFC / Decision refs).
2. Purpose.
3. Non-negotiable invariants (preserved verbatim from RFC).
4. Out of scope (lifted from RFC § Scope plus spec-time exclusions).
5. Architecture / Modules — exact file layout under
   `src/engram/grounding/`; HTTP-client-forbidden modules named;
   AST-walk test name.
6. Code-side enforcement — three chokepoints (forbidden imports,
   sanctioned-network module, single-accessor for grants).
7. DECISION_LOG lock — spec carries the obligation; operator applies.
8. Schema — full DDL for production PG tables and scratch SQLite
   grants tables. Includes triggers, indexes (`CONCURRENTLY`),
   `superseded_by` semantics.
9. Snapshot storage layout — directory tree, mode bits 0700/0600.
10. Resolver contract — `SurfaceFormSpan`, `Candidate`, `SnapshotPin`
    dataclasses; `normalize_surface_form` pinned; determinism
    contract; LRU cache shape.
11. Extractor integration — `EXTRACTION_PROMPT_VERSION` bump rule;
    candidate-block assembly with verbatim guard sentence;
    `CANDIDATE_BATCH_CAP` enforcement; `grounding_status` JSON field;
    silent-downgrade-with-lock-detection; sanitizer.
12. CLI surface — exact argparse definitions for
    `engram grants {list,grant,revoke,apply-template}`,
    `engram grounding {snapshot,rollback,detach,versions,onboarding}`,
    `engram phase3 grounding-bench`. All subparsers have exit-code
    documentation.
13. Bench mechanics — three arms, paired metric, pre-registered
    decision rule (≥30% false-rate reduction, ≤5% coverage drop),
    sample sizes, gold set construction, baseline reproducibility.
14. Operator onboarding — six-step `engram grounding onboarding`
    flow.
15. Test matrix — 22 named tests covering every must-clause.
16. Test fixture strategy — synthetic 10MB snapshot committed; real
    subset opt-in.
17. Migration plan — single migration `013_grounding_external_refs.sql`
    with idempotent steps and `CONCURRENTLY` annotations.
18. Promotion path — 4-commit implementation gated by 600-segment
    bench.
19. Acceptance criteria — concrete checks the implementation must
    satisfy.

## RFC sections each spec section implements

| Spec section | RFC section |
|---|---|
| Non-negotiable invariants | § Non-negotiable constraints (verbatim) |
| Code-side enforcement | § Non-negotiable constraints / Code-side enforcement |
| DECISION_LOG lock | § Non-negotiable constraints / Locked in DECISION_LOG |
| Architecture / Modules | § D-B (module split) |
| Schema → entity_external_references | § D-D (option 2 with tombstones) |
| Schema → grounding_resolution_set | § D-E (provenance shape sidecar) |
| Schema → private_aliases | § Q4 (per-corpus alias suppression) |
| Schema → grounding_snapshots | § D-E (content-hashed snapshot id) |
| Schema → grants/grants_audit | § D-F (scratch SQLite grants) |
| Snapshot storage layout | § D-E (mode bits, fetch-time indexing) |
| Resolver contract | § D-B (module split + normalization) |
| Extractor integration → prompt-version bump | § D-G |
| Extractor integration → candidate block | § D-B (prompt-shape guard) |
| Extractor integration → run-summary status | § D-F (run-summary JSON) |
| Extractor integration → silent downgrade | § Q7 (lock-file detection) |
| Extractor integration → sanitizer | § D-B (dataset content sanitization) |
| CLI surface → engram grants | § D-F |
| CLI surface → engram grounding | § D-A, § D-E, § Q4 |
| CLI surface → grounding-bench | § D-H |
| Bench mechanics | § D-H (three-arm rewrite) |
| Operator onboarding | § Q5 / § Promotion path step 4 |
| Test matrix | § Promotion path step 4c (test obligations) |
| Test fixture strategy | spec-time carryover from REVISION_HANDOFF |
| Migration plan | § Promotion path step 4a |
| Promotion path | § Promotion path |

## Spec-time carryovers from synthesis (now resolved)

The design-review revision handoff named six spec-time carryovers; the
spec resolves each:

1. **Argparse exact shapes (L022)** — § CLI surface ships full
   subparser definitions with arguments, types, defaults, and exit
   codes for every CLI verb.
2. **Test fixture strategy (L026)** — § Test fixture strategy commits
   to a synthetic ~10MB content-hashed fixture in
   `tests/fixtures/grounding/`; integration tests opt in via
   `ENGRAM_GROUNDING_INTEGRATION=1`.
3. **Test matrix (L022/L023)** — § Test matrix lists 22 named tests
   covering grant enforcement, AST-walk no-http-clients, resolver
   determinism, snapshot integrity, tombstone supersession, cascade,
   silent downgrade, sanitizer, prompt budgets, private aliases,
   bench mechanics, baseline pin, storage budget, latency.
4. **Grounding-bench automation (L018)** — § Bench mechanics + § CLI
   surface → `engram phase3 grounding-bench` with `--slice` flag,
   per-arm reports, decision-rule verdict.
5. **Onboarding walkthrough (L010)** — § Operator onboarding ships
   the six-step flow.
6. **D### allocation (L003)** — § DECISION_LOG lock notes that the
   operator must apply this on spec acceptance; the spec carries the
   obligation but cannot itself write to DECISION_LOG.md.

## Open spec questions for the review loop

1. **Migration filename:** the spec proposes `013_grounding_external_refs.sql`
   based on the highest existing migration (`012_predicate_subject_kind_hint.sql`,
   currently uncommitted on the predecessor branch). If the actual
   next-available number is higher when this spec is implemented, the
   spec can renumber freely.
2. **Initial DECISION_LOG D### number:** the spec does not pre-allocate;
   the operator picks the next sequential when applying.
3. **Prompt-version next value:** the spec says "advances from current
   value to next sequential" but does not pin the next number; the
   implementer should look up the current value and ship the bump in
   the same commit.
4. **Resolver index format:** the spec names "SQLite or Lance" without
   committing. Schema-adversary review may want this pinned.
5. **Onboarding command implementation language:** the six-step flow
   is described prose; the spec does not commit to interactive vs
   `--non-interactive` stdin format.

## Validation

- Every RFC 0030 "must" clause has a corresponding spec contract
  (cross-referenced in § RFC sections each spec section implements
  above).
- Every spec contract (chokepoint, schema row, CLI verb, bench arm)
  has a named test in § Test matrix.
- The five non-negotiable constraints are enforced by named code
  modules (`resolver.py`, `attachment.py`, `extractor.py`,
  `grants.py`, `private_aliases.py`, `bench.py` — HTTP-client-forbidden;
  `snapshot.py` — sanctioned-network exception with bounded surface;
  `grants.GrantStore.read_active` — single-accessor chokepoint).
- No private corpus excerpts in the spec; all examples are synthetic
  (`Q42`, `geoname:5391959`, `wikidata@2026-04-15@sha256:abcd...`).
- `docs/rfcs/README.md` row update for RFC 0030 → `promoted` is
  pending (see Open question 1; happens in this draft job's RFC row
  update step below).

## Residual risk

- **Spec is large** (~520 lines). Spec reviewers should verify
  RFC-to-spec coverage one section at a time.
- **The spec does not pre-allocate D### or migration numbers.** This
  is intentional (avoid conflicts) but operators applying the spec
  must allocate during implementation.
- **Bench gold set construction** is named but not staffed: who curates
  the 100-segment held-out gold set with `(surface_form, expected_dataset,
  expected_external_id)` triples? The spec assumes operator-curated under
  RFC 0021's discipline; the operator is the bottleneck.
- **The spec does not specify** the resolver index format (SQLite vs
  Lance vs in-memory dict). Spec-adversary review will likely flag
  this; synthesis should pick.
- **DECISION_LOG D### lock is operator-applied,** not spec-applied.
  Until the operator writes the entry, the lock is convention.
