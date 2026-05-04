# Benchmark Segmentation Early-Signal Spec Review

Date: 2026-05-04T02:29:39Z
Reviewer: claude-opus-4-7 (Claude Code)
Branch: build-benchmark-segmentation-harness
Reviewed commit: `dbede67` (Specify segmentation benchmark early signal)
Scope:

- `benchmarks/segmentation/SPEC.md` (tiers, sample-plan rules, Engram proxy
  fixtures, fragmentation metrics, early-signal verdict gates)
- `benchmarks/segmentation/README.md` (tier model summary)
- `DECISION_LOG.md` (D042)
- `docs/rfcs/0008-segmentation-benchmark-early-signal.md` (status →
  `specified` + promotion breadcrumb)
- `docs/rfcs/README.md` (RFC 0008 status)

Documentation-only commit. No code, fixtures, tests, or run artifacts
changed.

## Findings

### 1. minor: SPEC.md mixes "implemented today" with "specified but not implemented" sections without per-section status markers
File/line: `benchmarks/segmentation/SPEC.md:1-13, 25-27, 43-94, 133-163, 223-252, 337-355, 441-486`

The status header says "implemented offline deterministic harness; RFC 0008
early-signal revision specified, pending implementation". The new
"Benchmark Tiers", "Sample Plans", "Engram Proxy Fixtures", and
"Early-Signal Verdict" sections are aspirational; the existing "Strategies",
"CLI", and "Results" sections describe what currently runs. Both sets sit
side-by-side with the same prose voice and mostly the same level of `must`
/ `required` language.

A reviewer reading SPEC.md as the contract for today's harness will look in
`run.json` for `benchmark_tier`, `sample_plan`, and `early_signal_verdict`
fields and not find them. There is no test pinning these fields' presence
or absence either way.

Recommendation:
Tag each new subsection with a `Status: planned (RFC 0008 / D042)` line
under its heading, or move all aspirational sections under a single
"## Planned (RFC 0008 / D042)" container. The Principles bullets that say
"Every completed run declares its benchmark tier and selection caveat"
should be qualified the same way until the runner emits the field.

### 2. minor: Verdict gates use "configured" thresholds without saying where they're configured
File/line: `benchmarks/segmentation/SPEC.md:470-484`

The Required gates section references "configured multiplier", "configured
threshold", "low" no-boundary false split rate, and "severe fragmentation"
without specifying defaults, where the values live, or who sets them.
RFC 0008 already lists this as Open Question 1 ("What sub-100/sub-200
fragment thresholds are acceptable for Engram?"), but SPEC.md silently
inherits the unresolved gate while elevating the verdict to a hard
requirement.

Risk: two implementers (or the same implementer six months apart) will
produce different verdicts on identical metrics. The verdict's audit value
comes from being reproducible.

Recommendation:
Either inline placeholder defaults in SPEC.md (e.g., "default
`tier1_segment_count_multiplier = 1.5`, override via run config"), or
explicitly state "thresholds TBD; tracked in RFC 0008 Open Question 1;
implementation must surface the threshold set in `run.json` so runs are
comparable." The latter is the smaller change.

### 3. minor: `early_signal_verdict.metric_reasons` is stringly-typed in the example with no schema discipline
File/line: `benchmarks/segmentation/SPEC.md:446-459`

The example shows `"metric_reasons": ["schema_valid_rate=1.0",
"provenance_valid_rate=1.0", "no_boundary_false_split_rate=0.02"]` — a list
of `key=value` strings. SPEC.md elsewhere is careful about JSON shape (the
manifest, sample plan, result, and report are all object-typed and
schema-versioned). The verdict object itself also has no `schema_version`
field, even though every other persisted shape does.

Risk: machine-readable consumers (the planned report tables, future
cross-run comparisons) will need to parse `key=value` strings. Two
implementers will produce different formats.

Recommendation:
Define `metric_reasons` as `dict[str, Any]` (or
`list[{name, value, threshold}]`) and add a
`schema_version: "segmentation-benchmark-early-signal-verdict.v1"` field.
Tighten the example accordingly.

### 4. minor: SPEC.md does not say what happens when a Tier 1 stratum is undersized
File/line: `benchmarks/segmentation/SPEC.md:150-163`

Eight strata are required for SuperDialseg sampling and the tier requires
60-100 parents — that's ~7-12 per stratum. SuperDialseg's validation split
has finite parents per stratum, and the "high-boundary-count" or "long
dialogues near the benchmark context budget" strata may not have enough
rows to fill a target quota.

The spec says "The harness must not implement Tier 1 as 'first N parents'
from the dataset" but does not say what to do when stratum K has fewer than
the target count: borrow from a neighbor stratum, take all available and
document the shortfall, or fail the sample plan? Different choices give
different verdicts.

Recommendation:
Add one sentence specifying the shortfall rule (recommended: take all
available, record the actual stratum sizes in the sample plan, and fail
validation only if the total falls below 60). Mention it as an Open
Question if you'd rather defer.

### 5. nit: D042 "revisit" clause leans on Phase-3 infrastructure that does not yet exist
File/line: `DECISION_LOG.md:64`

D042's revisit condition is "after Tier 1 and Tier 2 results show the
composite verdict disagrees with downstream claim/belief quality or if
public datasets prove misaligned with Engram's memory-unit needs."
Claim/belief quality measurement requires Phase 3 outputs, which D040
explicitly defers. This means D042 cannot be revisited via the stated
trigger until Phase 3 lands.

This is fine in principle (forward-looking decisions can have
forward-looking revisit triggers), but a reader following revisit clauses
to plan future work will find this one currently un-tripable.

Recommendation:
Add a near-term revisit hook too — e.g., "or after the first Tier 1 run
shows verdict gates produce no separation between candidates" — so the
decision is not paused on Phase 3 if the composite design itself turns out
to be wrong.

### 6. nit: docs/rfcs/README.md leaves RFC 0006 status as `proposal` while SPEC.md says it is incorporated
File/line: `docs/rfcs/README.md:15-16`, `benchmarks/segmentation/SPEC.md:11-13`

SPEC.md now reads "This specification incorporates RFC 0006 and RFC 0008.
D041 makes the harness public-first. D042 makes model-selection
benchmarking tiered and fragmentation-aware." Most of RFC 0006 is
implemented today; the public-first dataset order, deterministic
strategies, original fragmentation count metrics, and reproducibility
metadata are all in code. RFC 0008 is now `specified`. RFC 0006 still shows
`proposal` in the index.

Recommendation:
Bump RFC 0006 to `specified` (or `implemented` if that status convention
exists). At minimum, add the same `Promoted: benchmarks/segmentation/SPEC.md
...` breadcrumb you added to RFC 0008.

### 7. nit: README.md tier summary still cites only RFC 0006
File/line: `benchmarks/segmentation/README.md:1-7`

The opening paragraph reads "the local-only, scratch-only segmentation
benchmark harness from RFC 0006." The new "Benchmark Tiers" section a few
lines down silently relies on RFC 0008 and D042. A reader who follows the
only RFC reference in README will not land on the source-of-truth for the
tier model.

Recommendation:
Change the opening to "from RFC 0006 (refined by RFC 0008 / D042)" or add
a one-line cross-reference under the "Benchmark Tiers" heading.

## Non-Blocking Notes

- **D041 / D042 relationship is correct.** D042 refines but does not
  supersede D041, and the public-first dataset rule survives intact. The
  `DECISION_LOG.md` status header was updated coherently
  (`+ D042 segmentation benchmark early signal`, dated 2026-05-04).
- **D039 protection preserved.** SPEC.md Principles still call out that
  strategy names and `StrategyKind` are benchmark-internal and do not
  introduce P-FRAG schema values.
- **No additive contradictions.** The aspirational sections do not
  contradict the implemented code. The `run.json` field list adds new keys
  without renaming existing ones; the `score.json` schema version stays at
  v1 with a stated `SCORING_IMPLEMENTATION_VERSION` bump policy when
  implemented; the verdict object is additive.
- **Backfill of historical runs is silent.** The 2026-05-03 10-parent run
  that motivated this work is correctly retro-classified as Tier 0 /
  `smoke_only` in the RFC and DECISION_LOG, but no instruction is given
  for whether or how the existing scratch `run.json` should be amended.
  Probably out of scope (scratch artifacts are not authoritative), but
  worth a one-liner saying "existing artifacts are not backfilled."
- **Tier ladder is internally consistent.** Each tier specifies purpose,
  required shape, and a distinct output (smoke readiness vs early-signal
  verdict vs decision recommendation), which makes the verdict types
  non-overlapping.
- **Sample-plan schema version** (`segmentation-benchmark-sample-plan.v1`)
  is introduced cleanly and follows the existing schema-versioning
  convention.
- **New fragmentation metrics** ("predicted/expected segment-count ratio",
  "no-boundary false split rate", "adjacent tiny-fragment rate", "duplicate
  or near-duplicate adjacent summary/content rate", "parents with more
  than twice the expected segment count") cleanly address the
  over-fragmentation concern from the 2026-05-03 Gemma result without
  picking thresholds prematurely.
- **Engram proxy fixtures** reuse the existing `embeddable_message_ids`
  invariant and the privacy-tier-mixed-spans / tool-placeholder rules, so
  adding fixtures will not require schema changes.

## Validation

- Read every changed file in full; cross-referenced D041, RFC 0006,
  RFC 0008, and the implemented harness modules at
  `benchmarks/segmentation/{datasets,strategies,scoring,results,reporting}.py`.
- Verified that no field promised in SPEC.md is contradicted by the
  existing `run.json` shape (additive only).
- Verified D042 wording quotes (`smoke_only`, `candidate`, `longer_run`,
  `defer`, `reject`) match RFC 0008 verdicts and SPEC.md verdict list
  verbatim.
- Verified the RFC 0008 `Promoted:` line points at the actual changes in
  this commit (SPEC.md and D042).
- Did not run the harness — no code changed, no tests changed; the prior
  re-review verdict (commit `f6215b0`) still stands for executable
  behavior.

## Verdict

Pass with changes (documentation only; no blockers).

The promotion is coherent: D042 is well-formed, RFC 0008 is correctly
cross-linked, and the SPEC.md additions describe a layered benchmark
ladder that is consistent with D041 and the existing implementation. The
findings are clarifications that should land before someone starts
implementing the early-signal runner: section-level status markers
(#1), threshold/configuration locus (#2), verdict-object schema (#3), and
the stratum-shortfall rule (#4). Nits #5–#7 are housekeeping. None of
these change the architectural intent; they make the spec implementable
without further interpretation.
