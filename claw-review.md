# Personal AI Context Architecture — Design Notes

## 1. Knowledge Graph Architecture

**Relational is fine for v1.** At personal scale (one user, ~200 entities), graph traversal doesn't buy much that good SQL can't do. The `relationships` and `causal_links` tables with vector similarity will cover 95% of use cases.

Consider *pg_graphql* for something between pure relational and a full graph DB — graph-style querying over PostgreSQL without AGE's complexity. AGE is a maintenance burden for marginal gain at this scale.

## 2. Context Population Design

**Don't use passive MCP tools.** The AI is bad at meta-cognition about its own knowledge gaps. It won't know what it doesn't know.

Go with *active context injection via system prompt template*. Before each AI interaction, run a lightweight query returning top-N relevant facts + standing context + recency signals, and prepend to the system prompt. The LLM sees it as authoritative context rather than a tool it has to discover.

Weight by *recency × engagement × goal relevance*. A fact about your current project today matters more than one from 2022 unless explicitly referenced.

## 3. Temporal Modeling

**Version facts, don't snapshot entities.** Keep facts immutable with `valid_from` / `valid_to` timestamps. When superseded, insert a new version rather than updating.

Need:
- `valid_from` on every fact/relationship
- A view for "current" facts (`valid_to IS NULL OR valid_to > NOW()`)
- Confidence decay that soft-deletes old facts but keeps them queryable

## 4. Hallucination Compounding

**Don't let synthesized facts feed future consolidation.** This is the most important architectural decision.

Stage 1 (episodes → facts) should *only* consume raw episodes. Synthesized facts go to the wiki layer and context layer, but not back into the consolidation pipeline.

Ground every fact to its source episode IDs. If no episode supports it, lower priority. Contradiction table + manual review queue for conflicts.

## 5. Unit of Ingestion

**One episode per full conversation, not per turn.** A single turn lacks conversational context needed to extract meaningful facts. A full conversation has topic coherence, follow-up reasoning, and resolution.

If conversations are very long, segment by topic (embedding distance from conversation start), but err on the side of coarser chunks. Consolidation works better with more context per input.

## 6. What to Cut for v1

Cut stages 4–8, the wiki layer, and all graph tables.

Minimum viable path:
- Stages 1–2 only (episodes → facts, facts → relationships)
- Context injection (prepend to system prompt)
- Basic wiki output (entity pages only)
- Keep `relationships` as relational tables

**Biggest risk:** The consolidation pipeline on 3,400 conversations will be slow and expensive with a local LLM. Start with a subset (last 100 conversations) to tune prompts and pipeline before running the full corpus.

The core value — "AI has personalized context about me" — works with 30% of this design. Don't build the whole thing before proving the core loop.
