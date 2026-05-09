# RFC 0030 Public-Dataset Entity Grounding Adversarial Cost Review

author: cost-adversary-codex-gpt-5.5-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

Lens: adversarial cost — disk, latency, operator burden. The RFC names
some numbers; treat each as a hypothesis to falsify.

## Findings

### C001 - 10GB v1 storage budget is plausible only with aggressive subset filtering
Severity: major
Source: § Open questions Q5; § D-A

Quantitative claim: "≤10GB total for v1, configurable."

Counter-claim: a places-only Wikidata subset is not 10GB. Wikidata's
full dump is 100GB+ uncompressed; a places-only filter (entities of
class `Q486972 human settlement`, `Q56061 administrative territorial
entity`, etc.) reduces to maybe 2-5GB depending on filter breadth.
Add GeoNames (~350MB compressed, ~1.5GB indexed) and the v1 budget is
~3-7GB if everything goes well.

But the budget has to also accommodate:
- Resolver index files (the snapshot's raw dump is not lookup-able;
  an index is required). At a minimum, a (surface_form → external_id)
  index. For Wikidata at places-only, expect ~500MB-1GB indexed.
- Optional embedded vectors for fuzzy match (RFC names this as
  potential): 768-dim float32 over a million places = ~3GB.
- Multiple co-existing snapshots (D-E recommends operators keep
  prior snapshots). Each adds its full footprint.

Realistic v1 with two co-existing snapshots, indexed, no embeddings:
~10-12GB. With embeddings: ~16-20GB. The budget is at the ragged edge.

Suggested fix: Q5 should commit to a *budget enforcement mechanism*
(refuse new snapshots if total exceeds budget) and a *budget-busting
warning* (notify when within 80% of budget). The "configurable" hand-
wave needs concrete defaults: budget = 10GB, hard-fail at 12GB.

### C002 - Resolution latency claim is missing entirely
Severity: major
Source: § D-G; § Open questions Q6

Quantitative claim: none stated.

Counter-claim: the RFC defers to bench but does not name an acceptable
latency cost. Existing extraction throughput (RFC 0023 concurrent +
RFC 0019 batching) targets a per-segment latency on the order of
hundreds of ms. A naive Wikidata lookup over a million-entity index:
~1-5ms per lookup. Per segment with say 5-10 entity-shaped phrases
that's another 5-50ms. Acceptable.

But the resolver is not just a lookup; it's:
- Surface-form normalization.
- Candidate generation (could be many candidates).
- Confidence scoring per candidate (which may involve string-distance
  or embedding ops).
- Filtering by entity-kind hint (RFC 0028 interaction).

Realistic per-segment latency: 50-200ms added. On a corpus of 100k
segments, that's 1.4-5.5 hours of additional extraction time per
re-extraction pass.

Suggested fix: Q6 must commit to (a) a latency budget per segment
(recommend ≤ 100ms), (b) a fail-fast behavior if a segment's
resolution exceeds the budget (skip resolution; emit one warning),
and (c) a per-corpus latency budget (recommend ≤ 2x current
extraction time).

### C003 - Snapshot lifecycle social process is unspecified and will not survive contact with reality
Severity: major
Source: § D-E; § Open questions Q5

The RFC says snapshots are "operator-controlled, not auto-refreshed
in the background." Operationally, this means:

- An operator running solo decides when to refresh. Most won't, until
  they notice something is wrong.
- Multiple operators on the same machine (rare for engram, but possible
  for shared dev environments) need to agree on snapshot version.
- The snapshot's upstream (Wikidata, GeoNames) keeps moving; in 18
  months the operator's pinned snapshot is meaningfully out of date.

There is no social process here. There is a wish.

Suggested fix: D-E should commit to:
- A staleness alert in run summaries (warn at >90 days old per
  dataset, configurable).
- A `engram grounding versions` command that shows: active snapshot,
  upstream's current version (queried at command-invocation time
  *only*, NOT at extraction time — preserves the privacy non-
  negotiable), age delta.
- An optional "refresh-friendly" mode where `engram grounding refresh`
  fetches the upstream's latest version and prepares it as a
  candidate snapshot, leaving activation to the operator.

### C004 - Bench cost (Step 5 in promotion path) is hours, not minutes, but framed as easy
Severity: major
Source: § Promotion path step 5

Quantitative claim: 100-segment slice for v1 bench (Step 3); full-corpus
re-extraction (Step 5) for production.

Counter-claim: 100-segment slice is small. Step 5's "full-corpus
re-extraction" on a 100k-segment corpus, with grounding adding 50-200ms
per segment (per C002), is a 1-5 hour batch operation. At Step 6's
"re-run interview against the grounded rows," the operator faces
hundreds-to-thousands of new claims to verdict.

The promotion path's framing ("Iterate dataset coverage only after v1
is producing measured value") suggests this is a casual loop. It is
not. Each iteration is a multi-day operator commitment.

Suggested fix: the promotion path should explicitly note iteration
cost. "Each promotion-path iteration takes the operator approximately
N hours of compute and M hours of interview time." Without the
acknowledgment, the loop will be quietly skipped after iteration 1,
and the eval-as-oracle principle softens to "we benched once, then
never again."

### C005 - Per-role grant matrix scales worse than the RFC implies
Severity: minor
Source: § D-F; § Open questions Q7

The RFC names the v1.x extension to MusicBrainz, OpenLibrary, Open
Food Facts as candidates. With ~5 datasets and ~5 striatum lanes
(codex, claude, gemini, plus possible specialist roles), the grant
matrix is 25 cells. Per cell: granted, revoked, or "default" (whatever
that means).

The cognitive load to remember "the codex extractor sees Wikidata and
GeoNames but not MusicBrainz, the claude extractor sees Wikidata and
MusicBrainz but not GeoNames" is real. The matrix is 25 cells; 99% of
operators will set them all the same way and forget the rest.

Suggested fix: D-F should commit to a "grant template" surface:
- `engram grants set --role-template default --datasets wikidata
  geonames`.
- `engram grants apply-template default <role>`.
- Sane default templates ship with engram (`places-only`,
  `places-and-companies`, `everything-public`).

This reduces the matrix to "pick one of N templates per role" —
manageable cognition.

### C006 - Test-suite footprint missing
Severity: minor
Source: § Promotion path step 4c

`tests/test_grounding.py` is named but the fixture footprint is not.
For meaningful tests, the suite likely needs:
- A toy snapshot (~100 entities) committed to the repo or downloaded
  on test setup.
- A larger fixture for integration tests.

Wikidata's licensing permits redistribution but committing even 100MB
to git is undesirable. The snapshot fixture needs a download-on-first-
test or content-hash-pinned URL approach.

Suggested fix: spec should commit to fixture strategy: "tests use a
~10MB synthetic snapshot in fixtures, content-addressed; integration
tests opt-in via env var to download a real subset."

### C007 - Index rebuild cost on snapshot upgrade not stated
Severity: minor
Source: § D-E

When the operator upgrades to a new snapshot, the resolver's index has
to be rebuilt. For a million-entity Wikidata subset, indexing time is
on the order of minutes to tens of minutes (depending on index type).

The RFC implies indexing is part of `engram grounding snapshot`; it
does not commit to whether indexing happens at snapshot-fetch time
(operator waits) or at first-use time (silent slow-down on first
extraction).

Suggested fix: D-E should commit to "indexing happens at fetch time;
extraction never indexes lazily."

### C008 - Dev/test cost on touched code paths underweighted
Severity: minor
Source: § Promotion path step 4c

Adding grounding touches:
- `src/engram/extractor.py` (prompt construction, post-extraction).
- `src/engram/consolidator.py` (PHASE-0004 — uses external refs).
- `src/engram/cli.py` (new commands).
- New `src/engram/grounding/` module (~500-1500 lines new code).
- Migrations.
- Tests.

Realistic implementation footprint: 1500-3000 net lines, including
tests. RFC frames Step 4 as three commits; this is more like a
five-commit landing.

Suggested fix: the promotion path should be honest about
implementation scope. Step 4 should be split: 4a migrations, 4b
grounding module + grants CLI, 4c extractor integration + prompt-
version bump + tests, 4d consolidator integration + projection_audits
update.

## Footprint summary

The RFC's stated cost numbers are roughly defensible for a *minimum*
v1 (Wikidata-places only, no embeddings, single snapshot, single role).
The first realistic extension breaks the budget, the latency budget,
or both.

The proposal is implementable. The cost story it tells the operator is
optimistic by a factor of ~2x in disk and ~3x in operator-time.

verdict: accept_with_findings
