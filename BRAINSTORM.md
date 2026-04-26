# Design Review: Personal Knowledge Base / Life-in-Embeddings

## The Vision

A fully local system that:
1. Ingests everything — AI conversation history (ChatGPT, Claude, Gemini), notes
   (Evernote → Obsidian), day-to-day activities, and live captures from any tool
2. Builds a structured personal knowledge graph + vector index over all of it
3. Automatically populates the context window for every AI interaction with
   relevant personal facts, current goals, patterns, and entity relationships
4. Writes synthesized knowledge back to Obsidian as human-readable wiki pages
   (Karpathy's LLM Wiki pattern as output layer)

The end state: every AI I interact with has coherent, current, personalized
context about me — preferences, goals, history, failures, relationships — without
me manually managing any of it.

---

## Current Design (stash-ingest)

### Infrastructure

| Component | Implementation |
|-----------|---------------|
| Database | Local PostgreSQL + pgvector |
| Embeddings | `nomic-embed-text` via ollama (768-dim) |
| LLM reasoning | `qwen3.6-35b-a3b` via ik-llama (OpenAI-compatible local endpoint) |
| Language | Python |

### Sources (current scope)

| Source | Type | Format |
|--------|------|--------|
| ChatGPT | Batch | JSON export — 3,437 conversations + 388 project conversations across 25 projects |
| Claude | Batch | ZIP export (Anthropic data download) |
| Gemini | Batch | Google Takeout JSON |
| Evernote | Batch (migration) | ENEX → Markdown via yarle/enex2md, lands in Obsidian |
| Obsidian | Live | Vault on disk / REST API plugin |
| MCP capture | Live | `capture` tool from any MCP client |

Future sources not yet specced: calendar, email, health data, git activity, etc.

### Schema (borrowed from Stash's 20 migrations)

| Table | Purpose |
|-------|---------|
| `namespaces` | Logical partitions by source/project |
| `episodes` | Raw conversation turns and notes with embeddings |
| `facts` | LLM-synthesized beliefs with confidence scores |
| `relationships` | Entity connections extracted from facts |
| `causal_links` | Cause-effect pairs between facts |
| `patterns` | Higher-level abstractions over facts + relationships |
| `contradictions` | Conflicts between facts, with resolution tracking |
| `hypotheses` | Uncertain beliefs with evidence tracking |
| `goals` | Intended outcomes with parent/child hierarchy |
| `failures` | Failure records with lessons learned |
| `embedding_cache` | SHA256-keyed vector cache |
| `consolidation_progress` | Per-namespace checkpoints for resumable runs |
| `contexts` | Working memory (short-lived, expires) |
| `settings` | Key-value config store |

HNSW indexes on `episodes` and `facts`. 768-dim vectors throughout.

The `relationships` and `causal_links` tables are proto-graph — entities and edges
stored relationally, not in a proper graph structure. I haven't decided whether to
add Apache AGE (graph extension for PG), use a separate graph store, or just query
the relational tables with graph-style SQL.

### Episode Granularity

**Conversations:** One episode per human+assistant turn, with metadata preamble:
```
[ChatGPT | gpt-4o | 2025-03-15 | "Snowboarding Layering Guide"]
Human: What should I wear for a cold powder day?
Assistant: For cold powder conditions you want...
```

**Notes:** One episode per note (or per heading section for long notes).

**Live captures:** One episode per call, typed: observation / task / idea / reference / person_note.

### Namespace Design

```
/chatgpt/conversations
/chatgpt/projects/<slug>
/claude/conversations
/gemini/conversations
/notes/evernote/<notebook>
/notes/obsidian/<vault>
/capture
```

### Consolidation Pipeline (8 stages, prompts tuned for qwen3.6-35b-a3b)

1. **Episodes → Facts** — cluster by vector similarity, synthesize grounded beliefs with confidence scores; detect contradictions in parallel
2. **Facts → Relationships** — extract entity connections with relation types and confidence
3. **Facts → Causal Links** — detect temporal and cause-effect relationships
4. **Facts + Relationships → Patterns** — extract higher-level abstractions with coherence scores
5. **Confidence Decay** — age facts via SQL; soft-delete below threshold
6. **Goal Progress Inference** — analyze facts against goals, annotate progress, cascade completions
7. **Failure Pattern Detection** — identify recurring failures, extract lessons
8. **Hypothesis Evidence Scanning** — confirm or reject hypotheses based on accumulated evidence

### Context Population (the personalization layer)

Currently specced as passive MCP tools — the AI calls `search` or `recall` when it
wants context. The real vision is active: a `context_for(conversation)` tool that
automatically assembles a context package before each interaction:
- Semantically relevant facts and episodes
- Standing context (current goals, active projects, key relationships)
- Recency signal (what happened in the last N days)
- Entity graph neighborhood (who/what is mentioned → what does the graph say about them)

I haven't designed this layer properly yet. It's the most important part.

### Wiki Output Layer (Karpathy LLM Wiki pattern)

After consolidation, a wiki stage reads structured tables and writes human-readable
Markdown pages to the Obsidian vault: entity pages, pattern pages, goal pages,
topic index. Pages carry `<!-- wiki-id: uuid -->` markers for idempotent re-runs.
Human edits in `## Notes` sections are preserved.

### Prior art I'm aware of

- **[Graphiti](https://github.com/getzep/graphiti)** — temporal knowledge graph from conversational data, open source, by Zep
- **[Mem0](https://github.com/mem0ai/mem0)** — personal memory layer for AI, vector + graph hybrid, has MCP server
- **[Stash](https://github.com/alash3al/stash)** — consolidation pipeline inspiration (Go, but schema is the artifact)
- **[OB1](https://github.com/NateBJones-Projects/OB1)** — MCP tools and capture pattern

---

## What I Want From You

I'm in design, not build. Engage critically. These are the actual questions:

### 1. Knowledge graph architecture

The `relationships` and `causal_links` tables are flat relational. Should I add
Apache AGE and model this as a proper property graph in PG, use a dedicated store
(Neo4j, FalkorDB), or is relational sufficient for a single-person corpus of this
size? What does graph traversal actually buy me at personal scale that good SQL
can't approximate?

### 2. Context population design

This is the part I've specced least and care about most. I run a personalization
layer professionally. At scale, feature stores, real-time signals, and ranking
models do this. At personal scale, with one user and a local LLM, what's the right
architecture for `context_for(conversation)`? How do I assemble a context package
that's relevant without being noisy — and how do I avoid the context window
becoming a wall of stale facts about who I was 3 years ago?

### 3. Temporal modeling

My professional system has strong temporal signals — query recency, engagement
decay, freshness scores. This design has confidence decay (stage 5) but it's naive:
SQL-based age decay with a soft-delete threshold. For a personal knowledge graph
where "who I was in 2022" is different from "who I am now," what's the right
temporal model? Should facts be versioned? Should entity state be snapshotted?
Graphiti handles this with temporal edges — is that the right primitive?

### 4. Hallucination compounding

The consolidation pipeline synthesizes facts from episodes. Those facts feed future
consolidation. If early extractions are wrong, they compound. At work, this is
handled by ground truth signals (clicks, engagement) that correct bad inferences
over time. I have no equivalent feedback signal. What's the right circuit breaker
for a system where the LLM is both writer and reader of its own knowledge base?

### 5. The right unit of ingestion

I've chosen one episode per human+assistant turn. Is that right? At work, document
chunking strategy is a major tuning surface. For personal conversation history,
should the unit be: a single turn, a full conversation, a topic-segmented chunk,
or something else? What does the consolidation pipeline actually need as input to
produce good facts?

### 6. What would you cut for v1?

Given the goal is "populate my context window with personal knowledge," what's the
minimum viable path? What of the 8 consolidation stages, the wiki layer, and the
graph structure is essential vs. nice-to-have for a first working version?

---

Be direct. Skip the caveats. I'd rather have a hard architecture critique now
than discover the wrong structural choice after running consolidation on 3,400
conversations.
