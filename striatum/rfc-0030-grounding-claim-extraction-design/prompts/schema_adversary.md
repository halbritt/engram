# Adversarial Schema and Migration Review of RFC 0030

Review `docs/rfcs/0030-public-dataset-entity-grounding.md` for schema and
migration risks. Compare against `docs/schema/README.md`,
`docs/rfcs/0011-phase-3-claims-beliefs.md`,
`docs/rfcs/0017-extraction-prompt-versioning.md`, and
`docs/rfcs/0018-evidence-to-claim-audit-cascade.md`.

## Lens

1. **D-D placement comparison.** The RFC names three options
   (entities columns vs entity_external_references vs claim_resolutions).
   Stress-test each:
   - When an entity has refs from three datasets at once.
   - When a single claim resolves both subject and object, at
     different confidences, against different datasets.
   - When a snapshot is rolled back and the resolution should be
     un-attached.
2. **Append-only invariants.** Engram's raw evidence stays
   append-only. Does the RFC's grounding write path tempt mutation?
   Probe: snapshot revocation, grant revocation, candidate-set
   pruning, low-confidence filtering. Each of these should preserve
   immutability — if not, name the violation.
3. **RFC 0017 versioning compatibility.** Each claim already carries
   `(prompt_version, model_version, request_profile_version)`. The
   RFC proposes adding `dataset@snapshot` provenance. Does the
   composite key still produce idempotent writes per the
   `(input_id, version) -> idempotent commit` contract?
4. **RFC 0018 audit cascade.** When raw evidence is superseded, the
   audit cascade walks derived rows. Does the grounding layer
   participate? What is the cascade's behavior for an entity_external
   _reference whose entity row is superseded?
5. **Backfill semantics.** What happens to claims extracted before
   grounding existed when grounding is enabled? Are they "ungrounded"
   tombstones, or can they be retroactively grounded? RFC 0017's
   re-extraction discipline applies — does the RFC name the re-extract
   path?
6. **Migration shape.** The RFC names one migration with three
   tables. Estimate how many rows the table touches at install time
   on a corpus of 100k segments. Does an app-restart-during-migration
   leave the schema in a recoverable state?
7. **Index discipline.** Resolver lookups are read-heavy. What
   indexes does the RFC commit to? What indexes are deferred? Does
   the design admit a fast path that skips grants when no datasets
   are active?
8. **Downgrade reversibility.** If grounding is disabled mid-corpus,
   what cleanup is required? What stays in the schema as a tombstone?
   What rebuild path exists for the projection_audits view?

## Output

Write to your packet's expected artifact path. Use this structure:

```md
# RFC 0030 Public-Dataset Entity Grounding Adversarial Schema Review
author: <packet author line>

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Findings

### S001 - <title>
Severity: <blocking | major | minor | nit>
Source: <path:line or section>
Failure mode: <one paragraph: scenario, schema state, recovery>
Rationale: <paragraph>
Suggested fix: <paragraph>

## Migration footprint

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Demand schema diffs, migration step counts, and concrete failure modes.
Do not modify the RFC.
