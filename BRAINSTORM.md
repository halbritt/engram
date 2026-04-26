# Design Review: Personal Knowledge Base (stash-ingest)

I'm designing a personal, fully local knowledge base that ingests my AI conversation
history (ChatGPT, Claude, Gemini), my notes (Evernote → Obsidian), and live captures
from any MCP-compatible tool. A consolidation pipeline synthesizes raw episodes into
structured knowledge (facts, patterns, goals, hypotheses). A wiki output layer writes
that knowledge back as human-readable Markdown pages to my Obsidian vault.

The full spec follows. Please read it, then answer the questions at the bottom.
Don't build anything — I'm still in design. I want your honest critical take.

---

## The Spec

### What it is

A DIY Python knowledge base combining:
- Batch ingestion of AI conversation history (ChatGPT, Claude, Gemini)
- Live note capture from Obsidian and other sources
- 8-stage consolidation pipeline (inspired by [Stash](https://github.com/alash3al/stash))
- MCP server for query + capture from any MCP-compatible tool
- Wiki output layer that writes synthesized knowledge back to Obsidian as Markdown

All local. No cloud services. No data leaving the machine.

### Infrastructure

| Component | Implementation |
|-----------|---------------|
| Database | Local PostgreSQL + pgvector |
| Embeddings | `nomic-embed-text` via ollama (768-dim) |
| LLM reasoning | `qwen3.6-35b-a3b` via ik-llama (OpenAI-compatible local endpoint) |
| Language | Python |

### Sources

| Source | Type | Format |
|--------|------|--------|
| ChatGPT | Batch | JSON export — 3,437 conversations + 388 project conversations across 25 projects |
| Claude | Batch | ZIP export (Anthropic data download) |
| Gemini | Batch | Google Takeout JSON |
| Evernote | Batch (migration) | ENEX → Markdown via yarle/enex2md, lands in Obsidian vault |
| Obsidian | Live | Vault on disk / REST API plugin |
| MCP capture | Live | `capture` tool from any MCP client |

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

### Episode Granularity

**Conversations:** One episode per human+assistant turn, with metadata preamble:
```
[ChatGPT | gpt-4o | 2025-03-15 | "Snowboarding Layering Guide"]
Human: What should I wear for a cold powder day?
Assistant: For cold powder conditions you want...
```

**Notes:** One episode per note (or per heading section for long notes).

**Live captures:** One episode per capture call, typed: observation / task / idea / reference / person_note.

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

### Wiki Output Layer (Karpathy LLM Wiki pattern)

After consolidation, a wiki stage reads from the structured tables and writes
human-readable Markdown pages back to the Obsidian vault.

**Flow:** Consolidation → wiki stage groups by concept/entity → Markdown pages land in `wiki/` folder in vault → lint pass checks for contradictions, orphans, stale claims.

**Page types:** Entity pages (person/project/tool/concept), pattern pages, goal pages, topic index.

**Schema document:** `wiki/SCHEMA.md` in the vault defines page structure and naming conventions. The LLM reads this before writing to maintain consistency.

**Idempotency:** Pages carry a `<!-- wiki-id: <uuid> -->` marker for overwrite on re-runs. Human edits in a `## Notes` section are preserved.

### MCP Server

Tools:
- `capture` — submit an episode with optional type tag
- `search` — semantic search across episodes/facts/patterns
- `recall` — structured recall by namespace
- `stats` — counts, top topics, recent activity
- `wiki_refresh` — trigger wiki regeneration for a namespace or page

### Repository Structure

```
db/migrations/        # SQL (adapted from Stash's 20 migrations)
db/schema.py          # migration runner

sources/base.py       # Episode dataclass, shared turn-extraction
sources/chatgpt.py
sources/claude.py
sources/gemini.py
sources/obsidian.py

pipeline/ingest.py    # embed + insert episodes
pipeline/consolidate.py
pipeline/wiki.py      # reads consolidated tables, writes Markdown to vault
pipeline/stages/      # facts, relationships, causal, patterns, decay, goals, failures, hypotheses

mcp/server.py
mcp/tools/            # capture, search, recall, stats

llm/embedder.py       # nomic-embed-text via ollama, SHA256 cache
llm/reasoner.py       # qwen3.6-35b via ik-llama, JSON extraction helpers

config.py
main.py               # CLI: --source --consolidate --wiki --serve --dry-run --limit N
```

---

## Open Questions (what I'm genuinely uncertain about)

- **Turn vs. conversation granularity:** I've chosen one episode per human+assistant turn. Is that the right unit for semantic search and consolidation? Or should whole conversations (or topic-delimited chunks) be the episode unit?
- **Consolidation on a local MoE model:** qwen3.6-35b-a3b is capable but not GPT-4. Which of the 8 consolidation stages is most likely to produce garbage on a local model, and how would you de-risk it?
- **Wiki vs. structured DB — duplication:** The wiki layer writes out what's already in PG tables. Is that redundant, or is the Markdown layer genuinely additive? What does it give me that a good MCP `recall` tool doesn't?
- **Hallucination becoming permanent:** The consolidation pipeline synthesizes facts from raw episodes. Those facts then influence future consolidation runs. How do I prevent early bad extractions from compounding? What's the right circuit breaker?
- **Episode provenance:** Once a fact is synthesized from 50 episodes, can I trace it back? The schema has confidence scores but I don't see a clean fact → source_episodes link. Is that a gap worth filling?
- **What's overengineered?** Given this is a personal tool for one person's history, what would you cut from the schema or pipeline to get to something that actually works vs. something that's architecturally complete but never ships?

## What I Want From You

1. **Critical assessment** — where does this design have blind spots, failure modes, or hidden complexity I'm not accounting for?
2. **Concrete alternatives** — for any part you'd redesign, say specifically what you'd do instead and why.
3. **Cut list** — what would you drop entirely for a first working version?
4. **The wiki question** — Karpathy's pattern applied here: genuinely valuable output layer, or does it add maintenance burden without enough payoff for a single-user system?
5. **Prompt engineering risk** — consolidation prompts tuned for qwen3.6-35b-a3b. What's the most likely failure mode and how would you design around it?

Be direct. I'd rather have a hard design critique now than debug a wrong architecture at 3,400 conversations.
