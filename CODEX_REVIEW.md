# Engram Design Review

Reviewer: Codex

Date: 2026-04-27

## Bottom Line

The design is pointed at the right long-term shape, but the current plan builds
too much consolidation machinery before proving the only product surface that
matters: `context_for(conversation)`.

The first version should not be "Stash in Python plus wiki plus graph." It should
be a temporal, evidence-backed memory compiler that produces a compact context
package for the next AI interaction.

The important architectural correction is:

```text
raw evidence -> claims -> beliefs/current_beliefs -> context_for()
```

Do not let synthesized facts become the substrate for more synthesis unless every
accepted belief remains grounded in raw episodes. That is the main circuit
breaker.

## Repo-Specific Observations

This repo is still design-only: `README.md`, `SPEC.md`, `TODO.md`, and
`BRAINSTORM.md`. That is good timing. The structural choices can still be changed
before migrations and prompts make them expensive.

The current `TODO.md` puts infrastructure, migrations, and the 8-stage
consolidation pipeline ahead of the retrieval/context layer. I would invert that.
Design the database only far enough to support a high-quality `context_for`.
Everything else should be downstream of that.

## 1. Knowledge Graph Architecture

Do not add Apache AGE, Neo4j, FalkorDB, or another graph store for v1.

For a single-person corpus, PostgreSQL plus pgvector plus relational edge tables
is sufficient. Graph traversal buys you:

- multi-hop expansion across people, projects, goals, tools, and events
- entity neighborhood retrieval for mentioned entities
- path explanations for why a memory was selected

All three can be implemented with typed edge tables, indexes, and recursive CTEs.
You do not need Cypher yet.

The current `relationships` and `causal_links` tables are too flat because there
is no explicit entity layer in the spec. Add entities before adding a graph
database.

Recommended v1 graph-ish schema:

```text
entities
  id
  canonical_name
  entity_type
  aliases
  summary_current
  created_at
  updated_at

entity_edges
  id
  source_entity_id
  target_entity_id
  relation_type
  valid_from
  valid_to
  observed_at
  confidence
  status
  evidence_ids
```

Keep the storage relational. Make the model graph-capable.

The decision rule should be: add a true graph backend only after you have at
least 10 concrete retrieval queries that are both valuable and ugly/slow in SQL.
Until then, a graph database is an operational tax and a distraction from the
ranking problem.

## 2. Context Population Design

`context_for(conversation)` should be the center of the system.

It should not be passive search. It should be a compiler:

```text
conversation
  -> intent detection
  -> entity extraction
  -> candidate generation
  -> ranking
  -> diversity and token-budget packing
  -> context package with provenance
```

Candidate generation should pull from multiple lanes:

```text
semantic belief search
semantic episode/segment search
keyword/BM25 search
active goals/projects
recent events
mentioned entity neighborhoods
pinned profile facts
open contradictions that affect the topic
```

Ranking should be explicit and inspectable. Use a simple weighted scorer before
you use an LLM reranker:

```text
score =
  relevance
  * currentness
  * confidence
  * specificity
  * source_quality
  * recurrence
  * task_fit
  - redundancy
  - stale_penalty
```

Then pack by section, not by raw score alone:

```text
Standing Context
Active Goals / Projects
Relevant Beliefs
Recent Signals
Entity Context
Raw Evidence Snippets
Uncertain / Conflicting
```

Hard token budgets are mandatory. Suggested initial budget:

```text
standing_context: 800 tokens
active_goals: 700
entity_context: 900
retrieved_beliefs: 1200
recent_signals: 600
raw_evidence_snippets: 1000
```

Default to current beliefs. Historical beliefs should appear only when the
conversation asks for history or when an old fact is highly relevant and clearly
marked as historical.

The central serving object should be a `current_beliefs` view or materialized
view. `context_for` should not search the entire historical fact table by
default.

## 3. Temporal Modeling

SQL age decay is the wrong primitive.

Some old facts remain true. Some fresh facts are wrong. Preferences drift. Goals
expire. Relationships change. You need temporal validity, not simple decay.

Use three layers:

```text
episodes       immutable raw evidence
claims         extracted statements from evidence
beliefs        consolidated assertions with temporal validity
```

Recommended `beliefs` shape:

```text
beliefs
  id
  subject_entity_id
  predicate
  object_entity_id
  value_text
  value_json
  valid_from
  valid_to
  observed_at
  extracted_at
  superseded_by
  confidence
  stability_class
  status
  evidence_ids
```

This is essentially slowly changing dimension type 2 / bitemporal thinking,
applied to personal memory.

Do not snapshot whole entities in v1. Store temporal beliefs and derive current
entity state from currently valid beliefs.

Use different temporal policies by belief type:

```text
identity: stable, low decay
preference: drift-prone, supersession-aware
project_status: medium-lived
goal: expires unless refreshed
task: short-lived
mood/opinion: local and usually not standing context
relationship: valid-time edge
```

Graphiti's temporal edges are the right intuition for relationships, but you need
temporal assertions more broadly, not just edges.

## 4. Hallucination Compounding

The current design's highest-risk path is:

```text
episodes -> facts -> relationships/patterns/goals/failures -> future facts
```

That creates a self-referential memory system where early extraction errors can
become "truth."

The circuit breaker should be an invariant:

```text
Every accepted belief must cite raw evidence.
```

Not another fact. Not a pattern. Raw episode, note, capture, email, calendar
event, etc.

Use statuses:

```text
candidate
provisional
accepted
superseded
rejected
```

Promotion rules should privilege source quality:

```text
explicit user statement > user-authored note > repeated behavior > assistant inference
recent explicit statement > old inferred pattern
capture/task note > casual brainstorming conversation
```

Before inserting or promoting a belief, retrieve existing beliefs with the same
subject/predicate and check for contradictions or supersession. Do not silently
merge conflict.

Add an audit trail:

```text
belief_audit
  belief_id
  operation
  model
  prompt_version
  input_claim_ids
  evidence_episode_ids
  score_breakdown
  created_at
```

This lets you roll back damage from a bad prompt version or bad model behavior.

## 5. Unit Of Ingestion

One human+assistant turn is too small as the primary unit.

Keep raw turns for provenance, but do not make them the main embedding and
extraction unit. Use a hierarchy:

```text
conversation
  topic_segment
    turn
      message
```

Embed and extract from topic segments. A single turn often lacks enough context
to distinguish a durable personal fact from local conversation state. A full
conversation is too broad. Topic segments are the right compromise.

For conversations, store:

```text
raw message: exact provenance
turn: local dialogue unit
topic segment: embedding and extraction unit
conversation: metadata/project/source container
```

For notes:

```text
note
  heading section
    paragraph/block
```

Use heading sections as the default unit, with whole-note fallback for short
notes.

The extraction prompt should see the segment plus surrounding metadata:

```text
source
conversation title
project
date
participants
segment text
previous segment summary
next segment summary
```

This will produce better claims than turn-level extraction.

## 6. What To Cut For V1

Cut most of the 8-stage pipeline from v1.

The v1 goal should be:

```text
Given a new AI conversation, produce a compact, useful, current personal context package.
```

Essential v1 pieces:

```text
ingestion for ChatGPT and Obsidian
topic segmentation
embeddings for segments and beliefs
claim extraction with raw evidence ids
belief consolidation with supersession
entities and typed entity_edges
current_beliefs view
context_for(conversation)
feedback log
```

Defer:

```text
causal_links
patterns
hypotheses
failures
goal progress inference
confidence decay job
Apache AGE / Neo4j / FalkorDB
full automatic wiki generation
large Obsidian writeback
```

Goals are worth keeping only if they are manually declared or explicitly
captured. Do not infer goal progress in v1. That is likely to create plausible
but wrong self-narratives.

For the wiki layer, start with preview output or one controlled page such as:

```text
wiki/Memory Index.md
```

Do not let the system spray synthesized pages into Obsidian until belief quality
is measured.

## Recommended V1 TODO Rewrite

I would reorder `TODO.md` around the serving path:

```text
1. PostgreSQL + pgvector baseline
2. ChatGPT ingestion into raw conversations/messages
3. Topic segmentation
4. Segment embeddings
5. Claims table with evidence references
6. Beliefs table with temporal validity and status
7. Entities and entity_edges
8. current_beliefs view
9. context_for() candidate generation
10. context_for() ranking and token packing
11. MCP tool exposing context_for
12. Feedback capture: useful / wrong / stale / irrelevant
13. Small-batch evaluation before full consolidation
```

Only after that should you add relationships beyond entity edges, patterns,
failure analysis, hypotheses, and wiki generation.

## Evaluation Harness

Before running consolidation on all conversations, build a small evaluation set.
You need this more than you need another pipeline stage.

Create 25-50 realistic prompts:

```text
help me continue a current project
remind me what I decided about X
draft a reply in my style
what do I already know about person Y
what are my active goals around Z
what have I tried before that failed
```

For each prompt, record:

```text
expected memories
must-not-include stale memories
acceptable historical memories
desired token budget
```

Then measure:

```text
precision of included context
recall of known-important facts
stale fact rate
unsupported belief rate
token waste
contradiction rate
```

This is the practical replacement for click/engagement signals in a
single-person system.

## Final Architecture Call

The durable bet is not graph storage. It is temporal, evidence-backed belief
modeling plus a strong context compiler.

Postgres can carry v1 and probably v2. A graph store can be added later if
retrieval queries prove it is needed. Bad provenance and temporal modeling will
be much harder to fix after the first full consolidation run.

Build the smallest system that can answer:

```text
What should the next model know about me for this conversation, and why?
```

Everything else is secondary.
