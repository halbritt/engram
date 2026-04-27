# Engram Design Review — Claude Opus 4.7

Reviewer: Claude Opus 4.7 (1M context)
Date: 2026-04-27
Scope: BRAINSTORM.md design as of commit at review time

The through-line across questions 2-4 is that you're trying to model **truth
over time** — "what's true now," "what's relevant now," "what's load-bearing
now" are three views of the same problem. Most of the current design treats
facts as flat, atemporal, and equally weighted, and that breaks at exactly
the moment the system gets useful.

## 1. Knowledge graph architecture

Stay flat relational. Add nothing.

At your scale (~10K episodes, maybe 100K facts asymptotically) the
index-free-adjacency win that justifies a property graph store doesn't exist.
Your hot path is "given a query, retrieve relevant subgraph" — that's vector
recall + 1-2 hop expansion, which is one CTE in Postgres. Real graph
traversal (community detection, shortest paths across millions of edges) is
not what personal context retrieval looks like.

Apache AGE is the right *eventual* answer if you outgrow SQL because it sits
in the same Postgres. Don't pull it in now — you don't have the queries that
justify it. Neo4j/FalkorDB is strictly worse: another process to back up,
another consistency boundary, another auth surface.

The harder question you didn't ask: **do you need a graph at all, or do you
need entity resolution?** Most of what you'd do with a graph is "given entity
X, what do I know" — which is `WHERE entity_id = ?` with a recency sort. The
hop-2 traversals that actually need graph thinking ("who connects me to
person Y") are probably 5% of your queries. Build entity resolution well;
build graph queries on demand.

## 2. Context population — the part that matters

You're right that this is the design center, and you've under-specified it
because you're pattern-matching on retrieval (vector top-k) when the real
model is closer to **feature engineering with retrieval as one feature**.
You already know this from work — you wouldn't ship a personalization layer
that was just nearest-neighbor over user history. Don't ship one here either.

Three layers, distinct retrieval strategies:

**Layer 1 — Standing context (always-on, ~300 tokens).** Active goals,
current projects, stable identity facts. This is *not* retrieved per-turn;
it's a materialized view that updates on a slow cadence. Treat it like the
user-profile features in a prod ranker — small, dense, hand-curatable, never
noisy. Without this layer, every conversation pays the cost of re-discovering
basic facts about you, and short conversations never accumulate enough
signal to do so.

**Layer 2 — Per-turn relevance (~1000-1500 tokens).** Vector retrieval
against *the running conversation*, not just the last user message — last
3-5 turns concatenated. Score = `similarity * recency_weight * confidence`.
The recency weight is where you'll spend the most tuning effort, see #3.

**Layer 3 — Entity neighborhood (~500 tokens, conditional).** Extract named
entities from the current turn. For each, pull top-N facts and relationships.
This is bounded (entity-anchored) and only fires when entities are present.
This is the graph hop, but it's not really a graph operation — it's an
entity-keyed lookup.

The two non-obvious moves:

**Tag facts with lifespan at extraction time.** `permanent` (born in NYC),
`slow-changing` (works at $COMPANY), `transient` (working on engram in April
2026). The retrieval scorer weights these differently per query class.
Without lifespan, your context window degrades to "stuff that was once true,"
which is the failure mode you correctly fear.

**Negative space is a first-class concern.** Facts you'd want surfaced but
no query will ever target ("user has no kids," "user does not use Twitter")
need to be in standing context, not retrieved. If you only have a retrieval
layer, you have no way to surface the absence of something — and at personal
scale, absence is often the most important fact.

The thing that scares me about your current spec: `context_for(conversation)`
as a single function suggests one retrieval strategy. It needs to be three,
composed, with budgets per layer.

## 3. Temporal modeling

Confidence decay is the wrong primitive. **Bitemporal facts** are the right
primitive.

Add `valid_from` / `valid_to` (when the fact was true in the world) and
`recorded_at` (when you learned it). When a fact is contradicted, don't
soft-delete — close its `valid_to` and insert a new fact. Now "what was true
on date X" is a SQL query, "what is currently true" is `valid_to IS NULL`,
and the wiki output is trivially correct: *"works at $COMPANY (since
2024-03); previously at $PRIOR (2019-2024)."*

Graphiti's temporal edges are the right shape. You don't need Graphiti to
get them — you need two columns and a discipline of "never UPDATE, always
close-and-insert."

This also fixes a problem you haven't hit yet but will: when you're
processing a 2022 ChatGPT conversation in 2026, the facts in it are
*historically* true but should not enter standing context as currently true.
Bitemporal modeling makes this trivial; flat confidence-decay makes it
impossible to express.

## 4. Hallucination compounding

Three circuit breakers, in order of importance:

**1. Provenance discipline.** Every fact must trace to at least one episode.
No fact-derived-only-from-facts. This is one constraint and one column
(`source_episode_ids text[]`). Without it, stage 4 (patterns) and stage 8
(hypotheses) become hallucination amplifiers — the LLM synthesizes from
synthesized content with no grounding.

**2. Adversarial re-extraction.** Periodically, take a high-confidence fact
and run a falsification prompt: "what evidence would contradict this? search
episodes for it." If contradicting evidence exists, surface as a
contradiction. This is your engagement-signal substitute — it's expensive,
but it's the only way to catch the LLM's own confirmation bias when it both
writes and reads.

**3. The wiki as the human-in-loop.** You already have it. When you read a
wiki page and see something wrong, you need a one-keystroke "this is wrong"
annotation that becomes a corrective episode. This is the actual ground
truth signal. Without it, the system has no correction mechanism and *will*
drift.

I'd **cut hypotheses (stage 8) entirely for v1**. It's the most likely
amplifier: thin-evidence beliefs get reinforced by other thin-evidence
beliefs and the LLM has no incentive to disconfirm them. Hypotheses make
sense in a system with external feedback signals; you don't have one yet.

## 5. Unit of ingestion

One episode per human+assistant turn is wrong. A turn is rarely a unit of
meaning — half your messages are clarifications, follow-ups, or tangents
that make no sense without the surrounding turns.

Right answer: **topic-segmented chunks**. Have the LLM segment each
conversation into 1-N topic chunks (most are 1-3) of ~500-2000 tokens. One
episode per chunk. Embed the chunk; preserve turn boundaries as metadata
for citation but not as the embedding unit.

For notes: per-section is fine. For captures: per-call is fine.

The reason this matters: stage 1 extracts facts from episodes. If episodes
are turn-sized, the LLM is extracting facts from fragments and inventing
context. If episodes are topic-sized, extraction is grounded in coherent
units. Same prompt, dramatically different fact quality.

For ChatGPT specifically: a meaningful number of your 3,437 conversations
are probably 2-4 turn back-and-forths that fit as a single chunk.
Segmentation is cheap there and only does real work on the long ones.

## 6. What I'd cut for v1

You have 14 tables and 8 stages. v1 has 5 tables and 1.5 stages.

**Keep:**
- `episodes`, `facts`, `goals`, `embedding_cache`, `consolidation_progress`
- Sources: ChatGPT + Obsidian + capture. Drop Claude/Gemini — same shape,
  no new signal, add later.
- Stage 1 (episodes → facts), but stripped: extract only stable identity
  facts with lifespan tagging. No clustering, no contradiction detection.
- Standing context + per-turn retrieval (Layers 1 + 2 from #2).

**Cut for v1:**
- Relationships, causal links, patterns, contradictions, hypotheses,
  failures — all of stages 2-8.
- Wiki output layer.
- Graph structure (don't model what you don't query).
- Confidence decay (use raw recency until you have data showing it's wrong).
- Layer 3 entity expansion (add when you see retrieval missing entity-keyed
  information).

The trap to avoid: building all 8 stages, running them on 3,400
conversations, discovering 30% of synthesized facts are noise, and then
having to either re-run consolidation with corrected prompts or live with
poisoned data. **Build the smallest thing that puts useful context in front
of an LLM, measure what's missing by reading the actual context packages,
then add stages targeting specific gaps.**

The wiki layer is the most tempting cut to keep — it's the prettiest part.
Cut it anyway. Your validation surface in v1 is reading the assembled
context package directly. Wiki is for v2 when the underlying knowledge is
stable enough to be worth rendering.

---

## The single highest-leverage decision

**Bitemporal facts + lifespan tagging from day one.**

Both are cheap to add and structurally impossible to backfill correctly.
Everything else in this review is reversible. Get those two right before
you write a single fact to disk.
