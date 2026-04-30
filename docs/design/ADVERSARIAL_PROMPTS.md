# Adversarial Review Prompts

These prompts support two review gates:

- **Pre-Phase-2 gate (D026):** run before segmentation + embeddings are
  implemented, while the first model-derived schema is still cheap to change.
- **Post-smoke gate:** run later against V1 + principles + gold set + smoke
  inventory.

Each round should specialize. Do not ask every model for another broad
architecture review.

## Pre-Phase-2 Usage

For D026, run **Round 0** against the current canonical docs before Phase 2
implementation. Optionally run Round C (temporal/provenance) or Round F
(evaluation) if Round 0 surfaces uncertainty that needs specialist pressure.
Save the broader graph, context_for, and V1 scope rounds for the post-smoke
gate unless a finding directly blocks segmentation + embeddings.

Focus on decisions that affect Phase 2 or become expensive after Phase 2 lands:

- segment schema and versioning;
- topic-boundary safety;
- embedding cache/index policy;
- privacy-tier inheritance on retrieval-visible derived units;
- whether later claims, beliefs, entities, context snapshots, and evals have
  the identifiers and provenance they will need.

Archive the raw review outputs under `docs/reviews/` or summarize them in a
dated synthesis document. Accepted deltas should update DECISION_LOG,
V1_ARCHITECTURE_DRAFT, BUILD_PHASES, or the Phase 2 prompt before coding
begins.

Every D026 finding must be classified as exactly one of:

- **Blocking before Phase 2** — must change docs, schema, or prompt before
  implementation starts.
- **Non-blocking but document now** — should be captured before coding, but does
  not block implementation.
- **Defer** — useful later, but not a Phase 2 gate.

For each finding, include:

1. Decision or document touched.
2. Proposed doc / schema / prompt delta.
3. Minimal experiment or inspection that would disprove the concern.
4. Cost of being wrong if Phase 2 ships unchanged.

## Shared Context For Every Round

```text
You are reviewing Engram, a fully local personal memory system.

Engram ingests AI conversation history, notes, live captures, and eventually
other personal signals. It builds a memory layer with embeddings, temporal
beliefs, entity relationships, and context assembly. The primary product surface
is context_for(conversation): a compact context package for the next AI
interaction.

Important context:
- This runs on my own hardware.
- Offline token burn is acceptable. Long-running local inference jobs are fine if
  they improve correctness, temporal cleanup, graph quality, provenance, or evals.
- Live context must remain concise, precise, and useful.
- Do not optimize primarily for API cost.
- Do not default to "single-user means simple." My corpus is complex, and I may
  want the design to scale.
- I professionally work on IR and personalization systems for a frontier model.
  Assume I care about ranking, freshness, feature-store-like signals, evals,
  feedback, and context packing.
- This is both a useful personal system and a local research lab for memory,
  graph retrieval, temporal modeling, and context engineering.

Inputs:
- README.md
- HUMAN_REQUIREMENTS.md
- DECISION_LOG.md
- BUILD_PHASES.md
- ROADMAP.md
- SPEC.md
- TODO.md
- docs/design/V1_ARCHITECTURE_DRAFT.md
- docs/design/ARCHITECTURE_EVOLUTION_DELTA_2026_04_29.md
- docs/design/GOLD_SET_TEMPLATE.md
- prompts/phase_2_segments_embeddings.md, for the D026 pre-Phase-2 gate
- docs/reviews/v1/CONSENSUS_REVIEW.md, as historical synthesis context
- Prior model reviews, if relevant

Be adversarial. Argue the assigned position strongly. Identify failure modes,
irreversible choices, and experiments that would disprove your recommendation.
```

## Round 0: Phase 2 Segmentation + Embeddings Adversary

```text
Review only the pre-Phase-2 boundary: topic segmentation, segment schema,
embedding cache/index policy, derivation versioning, privacy inheritance, and
future compatibility with claims, beliefs, entities, context snapshots, and evals.

Your job is to break the Phase 2 handoff before it becomes code.

Attack:
- topic segments as the first derived unit;
- whether a message may belong to multiple segments, zero segments, or only one;
- segment identity and ordering across re-segmentation;
- message-span provenance and whether downstream claims can cite raw evidence
  precisely enough;
- segment schema fields, including source_kind, parent ids, sequence_index,
  content_text, summary_text, raw_payload, privacy_tier, prompt/model versions,
  and superseded_by;
- privacy-tier inheritance across mixed-tier message spans;
- exact text used for embeddings, SHA256 cache keying, duplicate text, and model
  dimension migration;
- pgvector index placement, HNSW/ivfflat fallback, and join shape from segments
  to embedding_cache;
- coexistence of segment embeddings now and belief embeddings later;
- resumability, partial failures, and no-op behavior under the same
  prompt/model versions;
- source-specific edge cases from ChatGPT, Claude, Gemini, future Obsidian
  notes, and live MCP captures;
- eval hooks needed before full-corpus segmentation.

Do not redesign V1 broadly. Do not argue for graph-first architecture unless
the graph decision changes the Phase 2 schema before implementation.

Output:
1. Blocking before Phase 2
2. Non-blocking but document now
3. Defer
4. Concrete schema deltas, if any
5. Concrete prompt / implementation-contract deltas, if any
6. Minimal experiments or inspections before coding
7. Explicit proceed / do-not-proceed recommendation
```

## Round A: Graph Maximalist

```text
Argue the strongest case that Engram should use a graph-native architecture
early.

Assume:
- local hardware
- unlimited offline token burn
- complex personal corpus
- research and experimentation are explicit goals
- vector search alone may miss multi-hop personal context

Design:
- graph data model
- canonical vs derived storage
- temporal edges and temporal attributes
- entity canonicalization
- edge confidence and provenance
- traversal use cases
- graph retrieval for context_for(conversation)
- graph algorithms worth trying
- what breaks if I stay relational too long

Also identify the minimum safety mechanisms needed to keep graph extraction from
becoming a hallucination amplifier.

Output:
1. Strongest graph-native architecture
2. Required schema primitives
3. Retrieval use cases that need a graph
4. Failure modes if graph is deferred
5. Safety gates for graph writes and graph-derived context
6. Recommendation: Apache AGE, Neo4j, FalkorDB, Kuzu, or another option
7. Migration path from relational prototype to graph-native system
```

## Round B: Graph Skeptic And Safety Adversary

```text
Argue the strongest case against making graph memory central in v1.

Assume I am tempted by graph-native retrieval and have enough hardware to do it.

Attack:
- hallucination compounding
- entity and edge noise
- stale self-modeling
- overfitted personal narratives
- operational complexity
- evaluation difficulty
- false confidence from graph visualizations
- graph-derived context contaminating live AI interactions

Then propose the minimum graph-compatible design that preserves optionality
without contaminating the canonical memory store.

Output:
1. Strongest argument against graph-first v1
2. The specific ways a personal graph can become wrong
3. Canonical store design that preserves graph optionality
4. Minimum edge model, if any, for v1
5. Safety gates before graph context can be injected live
6. Experiments that would justify promoting graph retrieval
```

## Round C: Temporal And Provenance Specialist

```text
Review only temporal modeling and provenance.

Design the belief lifecycle for Engram:
- raw evidence
- segments
- claims
- beliefs
- supersession
- contradiction handling
- confidence
- temporal validity
- source quality
- audit log
- rollback after bad extraction prompts
- model and prompt versioning

Assume:
- all accepted beliefs must be traceable to raw evidence
- derived beliefs may help candidate generation but cannot become ground truth
  without raw evidence
- old facts are not necessarily stale
- fresh facts are not necessarily true
- "who I was in 2022" and "who I am now" must both be representable

Do not discuss UI, wiki generation, or graph backend except where temporal design
requires it.

Output:
1. Recommended temporal model
2. Table/schema primitives
3. Claim-to-belief promotion lifecycle
4. Supersession and contradiction rules
5. Confidence and source-quality model
6. Audit and rollback strategy
7. How current_beliefs should be derived
8. How historical beliefs should be exposed to context_for
```

## Round D: Context_For Specialist

```text
Review only context_for(conversation).

Design:
- inputs
- intent detection
- entity extraction
- candidate generation
- vector retrieval
- graph expansion
- recency and freshness features
- ranking features
- diversity controls
- token budgeting
- stale fact suppression
- historical context rules
- evidence citation
- feedback signals
- eval harness
- live latency vs offline precomputation

Assume:
- offline processing can be expensive
- live context must be compact and high precision
- the system may have temporal beliefs, entity edges, raw episodes, notes, goals,
  projects, patterns, and speculative hypotheses
- not all of those should be eligible for live context by default

Output:
1. context_for architecture
2. Candidate lanes
3. Ranking formula or feature list
4. Token budget strategy
5. Context package format
6. Freshness and stale-memory controls
7. Use of graph neighborhood expansion
8. Feedback and eval design
9. Failure modes and mitigations
```

## Round E: V1 Scope Killer

```text
You are the v1 scope adversary.

Given the full Engram vision and all prior reviews, identify what must be cut
from v1 to avoid building a beautiful unusable system.

Assume:
- I want research optionality
- I am comfortable with local offline inference
- I still need a working system that improves my next AI interaction

Output:
1. Essential v1
2. Explicitly deferred
3. Dangerous to build now
4. Dependencies between components
5. Shortest path to a working context_for(conversation)
6. What to measure before expanding scope
7. The smallest schema that preserves future graph and wiki options
8. A 30-day implementation sequence
```

## Round F: Evaluation And Benchmarking Specialist

```text
Review only evaluation.

Design an eval harness for Engram that can replace the missing ground-truth
feedback signals normally available in production personalization systems.

Assume:
- one user
- private local corpus
- long offline jobs are acceptable
- evals should cover context_for, temporal correctness, graph retrieval, and
  hallucination resistance

Output:
1. Gold-set construction strategy
2. Prompt/task categories
3. Metrics
4. Negative examples and stale-memory tests
5. Human feedback workflow
6. Automated LLM-as-judge checks and their failure modes
7. Regression testing after prompt/model/schema changes
8. Minimal eval set before full corpus consolidation
```
