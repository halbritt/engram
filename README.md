# engram

> A local-first memory layer for one human life.

Engram ingests AI conversation history, notes, and live captures, then produces
compact, evidence-backed context packages for AI assistants through MCP.

No cloud. No data leaving the machine.

## What It Does

- **Ingests** ChatGPT, Claude, and Gemini conversation exports, then expands to
  Obsidian notes and live MCP captures.
- **Preserves raw evidence** in immutable PostgreSQL tables.
- **Derives memory** through topic segments, claims, and bitemporal beliefs with
  provenance, confidence, stability class, and audit history.
- **Serves context** through `context_for(conversation)`, a multi-lane compiler
  that emits sectioned, token-budgeted context with citations.
- **Caches hot state** as versioned context snapshots for low-latency MCP
  serving. Prefix / KV-cache optimization is a later local-agent path, not a V1
  assumption.

## Current Status

Phase 1 / 1.5 is complete: raw ingestion exists for ChatGPT, Claude, and Gemini.

The D026 pre-Phase-2 adversarial review is synthesized. Current work is Phase
2 preflight probes, then topic segmentation + embeddings. See
[BUILD_PHASES.md](BUILD_PHASES.md),
[docs/reviews/v1/PRE_PHASE_2_ADVERSARIAL_SYNTHESIS_2026_04_30.md](docs/reviews/v1/PRE_PHASE_2_ADVERSARIAL_SYNTHESIS_2026_04_30.md),
and [prompts/phase_2_segments_embeddings.md](prompts/phase_2_segments_embeddings.md).

## Architecture

```text
sources
  -> conversations / messages / notes / captures   (immutable raw evidence)
  -> segments                                       (topic-segmented, embedded)
  -> claims                                         (LLM-extracted, grounded)
  -> beliefs                                        (bitemporal, stability-classed)
  -> current_beliefs view
  -> context_for(conversation)                      (multi-lane compiler)
  -> context_snapshots                              (hot state for MCP serving)
```

Derived projections are rebuildable from canonical evidence-backed state. Raw
evidence is never overwritten in place.

## Canonical Docs

Read these before older brainstorm/review material:

| Document | Purpose |
|----------|---------|
| [HUMAN_REQUIREMENTS.md](HUMAN_REQUIREMENTS.md) | Load-bearing principles and long-arc ambition. |
| [DECISION_LOG.md](DECISION_LOG.md) | Accepted, rejected, superseded, and deferred decisions. |
| [BUILD_PHASES.md](BUILD_PHASES.md) | Current V1 build phases and acceptance criteria. |
| [ROADMAP.md](ROADMAP.md) | Owner sequencing and current step. |
| [SPEC.md](SPEC.md) | Current V1 architecture summary. |
| [docs/design/V1_ARCHITECTURE_DRAFT.md](docs/design/V1_ARCHITECTURE_DRAFT.md) | Working target architecture for V1. |
| [docs/design/ARCHITECTURE_EVOLUTION_DELTA_2026_04_29.md](docs/design/ARCHITECTURE_EVOLUTION_DELTA_2026_04_29.md) | Hot state / context snapshot delta. |
| [docs/schema/README.md](docs/schema/README.md) | Generated schema diagram and table reference. |

## Explicitly Not V1

- Auto wiki writeback to Obsidian.
- Goal / failure / hypothesis / pattern inference.
- Causal-link mining.
- LLM cross-encoder reranker in the live path.
- Apache AGE / Neo4j / Kuzu / FalkorDB graph backend.
- Bidirectional Obsidian sync.
- Bulk Evernote migration.

## Stack

| Component | Implementation |
|-----------|----------------|
| Database | PostgreSQL + pgvector |
| Embeddings | `nomic-embed-text` via Ollama |
| LLM reasoning | `qwen3.6-35b-a3b` via ik-llama |
| Language | Python |

## Inspiration

- Stash — early consolidation-pipeline inspiration; not the current schema.
- OB1 — MCP capture/tooling pattern.
- Graphiti, Mem0, Letta, GraphRAG, and older Memex-style systems — reference
  points, not direct architecture templates.
