# Design Review: Personal Knowledge Base / Life-in-Embeddings
**Reviewer:** Gemini CLI
**Date:** April 27, 2026

Here is a direct, hard-architecture critique of your design. You are building a closed-loop LLM system without exogenous grounding, which is the most dangerous kind of data system. We need to structurally defend against drift, staleness, and noise.

### 1. Knowledge Graph Architecture: Stick to Postgres

**Critique:** Do not add Apache AGE, Neo4j, or FalkorDB. A relational model with recursive CTEs is entirely sufficient for a single-human corpus.

At personal scale, you are dealing with tens of thousands of entities and maybe a few hundred thousand edges. Postgres can execute a 2- or 3-hop graph traversal using `WITH RECURSIVE` in milliseconds. 

**What graph actually buys you:** The only thing a dedicated graph DB offers here is a slightly more ergonomic query language (Cypher) for highly recursive path-finding (e.g., "find the shortest path between my dog and my last AWS deployment"). You don't need this for context population. You only need 1-hop or 2-hop neighborhood expansion ("I mentioned X, what is related to X?"). Relational tables (`source`, `edge_type`, `target`, `weight`) with indexing handle this perfectly. Don't take on the operational overhead of a polyglot persistence layer until SQL literally fails you.

### 2. Context Population Design: The "Active Assembly" Pattern

**Critique:** Passive MCP tools (`search`, `recall`) are a failure mode for personalization. The LLM won't know what to search for if it doesn't know what it doesn't know. You need a deterministic context assembler that runs *before* the prompt hits the LLM.

Do not dump raw search results into the context window. Use a multi-tiered context assembly strategy:

1. **Core Identity (Static):** A tiny, hardcoded system prompt block (who you are, core constraints). 
2. **Working Memory (Time-bound):** The last 7 days of synthesized summaries and currently active goals.
3. **Semantic Retrieval (Dynamic):** Vector search on your current prompt against the `facts` table.
4. **Graph Neighborhood (Associative):** Fast Entity Extraction (NER) on your prompt -> `SELECT target FROM relationships WHERE source IN (entities)`.

**The crucial missing piece in your spec is Re-ranking.** To prevent the context window from becoming a wall of noise, you must take the outputs of Tiers 3 & 4 and run them through a lightweight cross-encoder or an LLM-as-a-judge to score relevance against the immediate user prompt. Aggressively cull anything below a high threshold. Quality over quantity.

### 3. Temporal Modeling: Validity Periods, Not Confidence Decay

**Critique:** Naive SQL-based age decay is dangerous. If you declare a peanut allergy in 2022, or that your wife's name is Sarah, it should not decay and soft-delete in 2024. 

"Confidence" and "Time" are orthogonal axes. Do not conflate them. 
You must model **validity periods**. Every fact needs a `valid_from` and `valid_until` timestamp. 

When your pipeline detects a contradiction (e.g., "I live in New York" vs "I just moved to SF"), it should not just overwrite the fact or average the confidence. It should close the temporal window on the old fact (`valid_until = now`) and insert the new one. 

Graphiti gets this right with temporal edges. In SQL, this is Type 2 Slowly Changing Dimensions (SCD2). When retrieving context, you append `WHERE valid_until IS NULL` to ensure the AI only sees current state, but you preserve historical state for lineage.

### 4. Hallucination Compounding: The Wiki is the Circuit Breaker

**Critique:** An LLM reading its own synthesized facts to synthesize higher-order facts, with no user click-stream to course-correct, is a recipe for catastrophic hallucination compounding. It will inevitably write fan-fiction about you.

You need a strong grounding signal. **Your Obsidian Wiki Output layer is not just an output layer; it is your Human-in-the-Loop Control Plane.**

1. **State of Record:** The Obsidian Markdown files must be the source of truth, not just a downstream projection. 
2. **Bi-directional Sync:** If the LLM synthesizes a fact, it writes it to the Wiki. If you (the human) read it and delete it, alter it, or tag it as `status: incorrect`, your ingest pipeline MUST read that diff and invalidate the fact in the database. This replaces the "clicks/engagement" signal you have at work.
3. **Provenance:** Every row in `facts`, `relationships`, and `patterns` must have an array of `source_episode_ids`. If a fact cannot cite the exact raw text that generated it, it gets purged.

### 5. Unit of Ingestion: Do Not Embed Raw Turns

**Critique:** One episode per turn is the wrong granularity. Raw conversation embeddings are terrible for retrieval because they are full of conversational filler ("Sure, I can help with that," "What about the other one?"). If you embed "What about the other one?", the vector is semantically meaningless.

**Recommendation:** Do not embed raw conversations for retrieval. 
1. **Chunking:** Group conversations into sliding windows (Human -> AI -> Human) to preserve coreference resolution.
2. **Transformation before Embedding:** Run a fast LLM over the chunk to extract atomic facts and summaries, and *embed those*. 
Keep the raw turns in Postgres for provenance and rendering, but your vector index should only contain dense, synthesized assertions (Facts) and concise summaries (Episodes), never raw conversational dialogue.

### 6. What to Cut for V1 (MVP)

Your 8-stage consolidation pipeline is too ambitious for v1 and will be impossible to debug. Cut the top half of the pyramid.

**Keep for V1:**
- **Stage 1:** Episodes → Facts (Atomic extraction).
- **Stage 2:** Facts → Relationships (Entity mapping).
- **The Wiki Layer:** (Crucial for your human feedback loop).
- **Active Context Population:** (Tiered assembly + Re-ranking).

**Cut for V1:**
- **Stage 3 & 4 (Causal Links & Patterns):** Abstract reasoning over synthesized facts is exactly where hallucinations compound fastest.
- **Stage 6, 7 & 8 (Goals, Failures, Hypotheses):** These require high-level reasoning and massive token spend. You will spend all your time tuning prompts for "Failure Pattern Detection" instead of getting basic fact retrieval working.
- **MCP passive tools:** Build the active context assembler first.

Get the system to reliably know where you live, what project you are working on, and what you talked about yesterday, and render that accurately to Obsidian. Once that loop is stable and hallucination-free, you can start building the higher-order reasoning pipelines.