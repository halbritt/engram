# stash-ingest

> **Note:** Name is a placeholder — will be renamed once the full scope crystallizes.

A DIY Python knowledge base combining:
- Batch ingestion of AI conversation history (ChatGPT, Claude, Gemini)
- Live note capture from Obsidian and other sources
- 8-stage consolidation pipeline (Stash-inspired)
- MCP server for query + capture from any MCP-compatible tool (Claude, Obsidian, Cursor, etc.)

All running on local infrastructure. No cloud services. No data leaving the machine.

Draws design inspiration from:
- [Stash](https://github.com/alash3al/stash) — schema and consolidation pipeline
- [OB1](https://github.com/NateBJones-Projects/OB1) — MCP tools and live capture pattern

## Sources

| Source | Type | Format | Location |
|--------|------|--------|----------|
| ChatGPT | Batch | JSON export (conversations + projects) | `~/chatgpt-export/user-afXFt1wByKh5XA1L7njvUZnI/` |
| Claude | Batch | ZIP export (Anthropic data download) | TBD — needs export |
| Gemini | Batch | Google Takeout JSON | TBD — needs export |
| Obsidian | Live | Vault on disk / REST API plugin | TBD — vault location |
| MCP capture | Live | `capture` tool from any MCP client | via MCP server |

ChatGPT export schema is well-understood (3,437 conversations + 25 projects
across 388 project conversations already exported via export-chatgpt).

## Infrastructure

| Component | Implementation |
|-----------|---------------|
| Database | Local PostgreSQL + pgvector |
| Embeddings | `nomic-embed-text` via ollama at `http://127.0.0.1:11434` |
| LLM reasoning | `qwen3.6-35b-a3b` via ik-llama at `http://127.0.0.1:8081/v1` (OpenAI-compatible) |
| Language | Python |

## Why DIY Instead of Running Stash

- Stash's consolidation prompts are tuned for GPT-4-class API response formats;
  local models need prompt adjustments that require forking Go code we don't own
- Source-aware consolidation logic (weighting by model, tagging by provider,
  handling multi-turn structure differently per source) is easier in Python
- Full ownership of the stack — debug consolidation failures without reading
  someone else's Go
- Schema is the valuable artifact; the Go binary is not

## Schema

Borrowed directly from Stash's 20 migrations. Core tables:

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
| `embedding_cache` | SHA256-keyed vector cache to avoid re-embedding |
| `consolidation_progress` | Per-namespace checkpoints for resumable consolidation |
| `contexts` | Working memory (short-lived, expires) |
| `settings` | Key-value config store |

Vector columns use pgvector. HNSW indexes on episodes and facts.
nomic-embed-text produces 768-dim vectors — configure pgvector accordingly.

## Namespace Design

```
/chatgpt/conversations          # regular ChatGPT conversations
/chatgpt/projects/<slug>        # per-project conversations
/claude/conversations           # Claude conversation history
/gemini/conversations           # Gemini conversation history
/obsidian/<vault>               # Obsidian notes
/capture                        # ad-hoc captures via MCP
```

## Episode Granularity

**Conversations:** One episode per human+assistant turn. Each episode includes
a metadata preamble:

```
[ChatGPT | gpt-4o | 2025-03-15 | "Snowboarding Layering Guide"]
Human: What should I wear for a cold powder day?
Assistant: For cold powder conditions you want...
```

**Notes:** One episode per note (or per heading section for long notes).
Metadata preamble includes vault, path, and modification date.

**Live captures:** One episode per capture call, typed (observation/task/idea/
reference/person_note — from OB1).

## Consolidation Pipeline (all 8 stages)

Runs as a background batch job per namespace, resumable via checkpoints.
Prompts written for qwen3.6-35b-a3b — not GPT-4 defaults.

1. **Episodes → Facts** — cluster similar episodes by vector similarity, synthesize into grounded beliefs with confidence scores; detect contradictions in parallel
2. **Facts → Relationships** — extract entity connections with relation types and confidence
3. **Facts → Causal Links** — detect temporal and cause-effect relationships between facts
4. **Facts + Relationships → Patterns** — extract higher-level abstractions with coherence scores
5. **Confidence Decay** — age facts over time via SQL; soft-delete below threshold
6. **Goal Progress Inference** — analyze facts against goals, annotate progress, cascade completions
7. **Failure Pattern Detection** — identify recurring failures, extract lessons
8. **Hypothesis Evidence Scanning** — confirm or reject hypotheses based on accumulated evidence

## MCP Server

Exposes the knowledge base to any MCP-compatible client (Claude, Obsidian,
Cursor, etc.). Independent entrypoint, shares DB and `llm/` layers with the
ingestion pipeline.

Tools (inspired by OB1):
- `capture` — submit a new episode (note, observation, idea) with optional type tag
- `search` — semantic search across all episodes, facts, and patterns
- `recall` — structured recall: facts, patterns, goals, hypotheses for a namespace
- `stats` — counts, top topics, recent activity

Bidirectional with Obsidian: notes flow in via `capture` or the vault watcher;
consolidated facts/patterns can flow back out as generated notes.

## Repository Structure

```
db/
  migrations/          # SQL migration files (adapted from Stash's 20 migrations)
  schema.py            # migration runner

sources/
  base.py              # Episode dataclass, shared turn-extraction logic
  chatgpt.py           # walks ~/chatgpt-export/, emits episodes
  claude.py            # walks Claude ZIP export, emits episodes
  gemini.py            # walks Gemini Takeout JSON, emits episodes
  obsidian.py          # walks Obsidian vault, emits episodes

pipeline/
  ingest.py            # embed + insert episodes
  consolidate.py       # orchestrates the 8-stage pipeline per namespace
  stages/
    facts.py
    relationships.py
    causal.py
    patterns.py
    decay.py
    goals.py
    failures.py
    hypotheses.py

mcp/
  server.py            # MCP server entrypoint
  tools/
    capture.py
    search.py
    recall.py
    stats.py

llm/
  embedder.py          # ollama nomic-embed-text client with SHA256 caching
  reasoner.py          # ik-llama qwen3.6-35b client, JSON extraction helpers

config.py              # DB URL, LLM endpoints, batch sizes, namespace roots
main.py                # CLI: --source --consolidate --serve --dry-run --limit N
```

## Open Questions

- [ ] Validate turn granularity with small batch before full ingest
- [ ] Confirm nomic-embed-text dimension (expected 768) with a test call
- [ ] Test consolidation prompt quality with qwen3.6-35b on a sample namespace
- [ ] Tune consolidation batch size (Stash default 100) for 3,400+ corpus
- [ ] Obsidian integration: vault watcher vs. REST API plugin vs. both
- [ ] Obsidian bidirectional sync: how to write generated notes back without clobbering
- [ ] Claude export schema — inspect after download
- [ ] Gemini Takeout schema — inspect after download
- [ ] MCP server framework: FastMCP vs. raw modelcontextprotocol SDK
