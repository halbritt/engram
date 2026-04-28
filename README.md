# engram

> Your entire life in a knowledge graph and embeddings.

A fully local personal memory system — knowledge graph plus vector index — that
ingests your AI conversation history, notes, and day-to-day captures, then uses
it to populate the context window for every AI interaction you have.

No cloud. No data leaving the machine.

## What it does

- **Ingests** ChatGPT, Claude, and Gemini conversation history; Evernote/Obsidian
  notes; and live captures from any MCP-compatible tool
- **Consolidates** raw episodes into structured knowledge: facts, relationships,
  causal links, patterns, goals, hypotheses — with confidence scores and
  contradiction tracking
- **Serves** a personal context layer via MCP: semantic search, structured recall,
  and a `context_for` tool that assembles a relevant context package before each
  AI interaction
- **Writes back** synthesized knowledge to your Obsidian vault as human-readable
  wiki pages (entity pages, pattern pages, goal pages)

## Status

Early design. See [SPEC.md](SPEC.md) for the full architecture and
[BRAINSTORM.md](docs/design/BRAINSTORM.md) for open design questions.

## Stack

| Component | Implementation |
|-----------|----------------|
| Database | PostgreSQL + pgvector |
| Embeddings | nomic-embed-text via ollama |
| LLM reasoning | qwen3.6-35b-a3b via ik-llama |
| Language | Python |

## Inspiration

- [Stash](https://github.com/alash3al/stash) — consolidation pipeline and schema
- [OB1](https://github.com/NateBJones-Projects/OB1) — MCP tools and live capture pattern
- [Graphiti](https://github.com/getzep/graphiti) — temporal knowledge graph from conversational data
- [Mem0](https://github.com/mem0ai/mem0) — personal memory layer for AI
- Vannevar Bush's Memex (1945) — the original vision
