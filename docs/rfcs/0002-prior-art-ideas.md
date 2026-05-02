# RFC 0002: Prior-Art Ideas To Revisit

Status: proposal
Date: 2026-05-02

This RFC captures useful ideas from a generated prior-art note that appears to
conflate this Engram project with unrelated systems. Treat the source note as an
idea pile, not as evidence about Engram's current architecture or capabilities.

Nothing here changes the accepted build plan. These are candidate design prompts
for later phases or eval-driven experiments.

## Useful Ideas

### Temporal Anchoring

Relative phrases such as "yesterday," "last week," or "recently" should be
normalized against source timestamps when claims are extracted.

Engram fit: Phase 3 claim extraction. Store the original text and normalized
candidate dates with confidence, then let belief consolidation decide how much
to trust them.

Why it matters: personal memory is temporal. If relative time survives into the
belief layer, it will drift. "Yesterday" is only meaningful while the source
timestamp is nearby.

Disproof probe: sample claims with relative time from ChatGPT / Claude /
Gemini exports and measure whether a local extractor can normalize them against
conversation timestamps without inventing dates.

### Embedding Migration Behavior

Engram already records embedding model versions and supports multiple vector
dimensions. Serving still needs an explicit policy for partially migrated
embedding spaces.

Engram fit: Phase 5 retrieval. Query only compatible vector spaces, fan out
across configured models when necessary, or fall back to lexical/BM25 lanes
when dense coverage is incomplete.

Why it matters: vector spaces from different embedding models are not directly
comparable. A partial migration should degrade retrieval gracefully rather than
mix incompatible distances.

Disproof probe: simulate a corpus where only half of active segments have the
new embedding model and verify `context_for` never compares a query vector
against incompatible model rows.

### Hierarchical Obsidian Ingestion

Obsidian notes should preserve heading paths and section hierarchy. A note is
rarely a flat document; section path is often the semantic address.

Engram fit: Obsidian ingest and segmentation. Section hierarchy can become
provenance context for segments and later raw evidence snippets.

Why it matters: the same sentence under different headings can mean different
things. Heading path helps retrieval, citation rendering, and review.

Disproof probe: ingest a small vault slice both flat and heading-aware, then
compare retrieval and raw-snippet rendering on questions that depend on section
context.

### Triples Plus Narrative Context

Subject-predicate-object-like extraction can be useful if treated as claim
shape, not as final truth.

Engram fit: Phase 3 claims. A claim may have structured fields, but it remains
untrusted until consolidated into a belief with evidence and temporal validity.

Why it matters: structured claims make consolidation, contradiction detection,
and entity linking easier. They are dangerous only if promoted directly to
beliefs without adjudication.

Disproof probe: compare free-text claims vs structured claim candidates on a
small labeled segment set. Measure unsupported claim rate, duplicate rate, and
consolidation usefulness.

### Retrieval Gating

Not every consumer interaction needs memory. Serving should decide whether to
retrieve, return a warm snapshot, compile fresh context, or explicitly say
"insufficient evidence."

Engram fit: Phase 5 `context_for`. This pairs with D018 and D025.

Why it matters: memory injection has a cost. Irrelevant context can dilute the
consumer model's attention and leak unnecessary private context.

Disproof probe: run gold-set and distractor prompts through a simple retrieval
gate and measure false positives, false negatives, context token waste, and
answer quality.

### Adaptive Thresholds

Fixed top-k retrieval will sometimes underfill or flood context. Adaptive score
thresholding should be evaluated once real retrieval logs exist.

Engram fit: Phase 5 ranking experiments. Do not implement before there are
gold-set and feedback signals.

Why it matters: a query with one very strong match should not carry nine weak
neighbors just because `k=10`; a broad query may need more than a fixed small
set.

Disproof probe: compare fixed top-k against score-gap or distribution-aware
thresholds on the gold set. Measure recall, token waste, and stale/irrelevant
item rate.

### Controller-Managed Maintenance

The prior-art note uses "dream" language for background consolidation. The
useful version is a controller-managed maintenance class, not an unbounded
autonomous loop.

Engram fit: RFC 0001 supervisor controller loop.

Possible maintenance classes:

- re-embed stale rows after embedding model changes;
- refresh stale context snapshots;
- rerun claim extraction for a target slice after prompt upgrades;
- scan high-confidence beliefs for contradictory raw evidence;
- rebuild derived summaries for long notes or conversations;
- run eval probes on known failure slices.

## Ideas Not Promoted

### Ebbinghaus Decay As Deletion Or Confidence Decay

Engram's bitemporal validity model remains the safer default. Old facts may
remain true; recent facts may be wrong. Recency and truth are separate axes.

Potential future use: ranking can include currentness features by stability
class, but that is not the same as deleting or lowering belief confidence
because time passed.

### Procedural Skill Libraries In V1

Procedural memory belongs to consuming agents or to a later, separately
grounded skill layer. Engram's near-term product is personal memory, not an
autonomous skill-acquisition system.

### Graph-Native Global Search In V1

Entity edges and SQL should be exhausted before adding a graph backend or
community-summary layer. Graph-shaped retrieval becomes interesting only after
claims, beliefs, and entities exist and evals show SQL/entity-neighborhood
retrieval is inadequate.

### Unbounded Dream Replay

Background maintenance must be scheduled, inspectable, versioned, and bound by
the same provenance/privacy/eval constraints as foreground work.

## Relationship To Existing Docs

- RFC 0001 owns the supervisor/controller-loop shape.
- D025 owns hybrid async hot state for Phase 5.
- D004 owns bitemporal validity over naive age decay.
- D009 owns the current vector-index policy.
- D018 and D022 own missing-data and provenance/confidence rendering.

Promote individual items from this RFC only after an eval or implementation
need appears. Do not turn the whole prior-art pile into architecture.
