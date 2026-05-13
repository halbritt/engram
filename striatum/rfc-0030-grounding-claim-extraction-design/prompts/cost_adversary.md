# Adversarial Cost and Operational Review of RFC 0030

Review `docs/rfcs/0030-public-dataset-entity-grounding.md` for hidden costs
in disk, latency, and operator burden that the RFC understates or ignores.

The RFC names some numbers (≤10GB total v1 storage, 100-segment bench, cap
~1000 prompt tokens per segment for candidates). Treat each number as a
hypothesis to falsify.

## Lens

1. **Storage budget.** ≤10GB total. Stress:
   - Does Wikidata "places-only" subset alone fit comfortably?
   - GeoNames adds ~350MB compressed; what's the indexed size?
   - Embedded vectors over the subset (if needed for fuzzy match): how
     much does that add?
   - How many co-existing snapshots before the budget breaks?
2. **Latency.** Resolver lookup adds time per segment. The RFC defers
   measurement to bench. Stress what "acceptable" looks like:
   - At what fraction of current extraction throughput does
     grounding stop being worth it?
   - Worst-case latency: cold cache, multiple datasets, ambiguous
     surface form. Bound it.
3. **Snapshot lifecycle.** Operator-curated snapshots:
   - Who curates? Solo operator only, or shared snapshot mirror?
   - How often? Quarterly? On-demand? Triggered by what?
   - What's the failure mode of a stale snapshot — silent
     degradation, loud refusal, or somewhere in between?
4. **Grant ops.** Per-role persistent grants:
   - Steady-state cognitive load of remembering which roles see
     what.
   - Does `engram grants` UX scale to the v1.x dataset list (the
     RFC names MusicBrainz, OpenLibrary, Open Food Facts)?
   - What's the right default — restrictive, permissive, or
     no-default-with-prompt?
5. **Bench cost.** 100-segment bench is the v1 gate. What does
   the actual full-corpus re-extraction cost (compute time, disk
   write, electricity) once grounding lands?
6. **Dataset update cadence.** Wikidata is updated continuously;
   the RFC proposes operator-controlled snapshots. Concretely:
   - When does an operator notice they're behind?
   - What's the social process for "everyone update to
     wikidata@2026-09-01"?
   - Does anything force consistency, or do snapshots fragment?
7. **Re-extraction cost.** Each grounded re-extraction is a full
   pipeline pass over a corpus. Per RFC 0017, that's expensive.
   How many re-extractions does the RFC implicitly assume?
8. **Dev/test cost.** What's the test-suite footprint? Will tests
   need fixture snapshots? How big? Where stored?

## Output

Write to your packet's expected artifact path. Use this structure:

```md
# RFC 0030 Public-Dataset Entity Grounding Adversarial Cost Review
author: <packet author line>

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Findings

### C001 - <title>
Severity: <blocking | major | minor | nit>
Source: <path:line or section>
Quantitative claim: <number, denominator, source>
Counter-claim: <number you assert instead, with rationale>
Rationale: <paragraph>
Suggested fix: <paragraph>

## Footprint summary

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Demand numbers; reject hand-waves. Do not modify the RFC.
