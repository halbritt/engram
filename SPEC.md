# engram

A local-first personal memory system. Given a new AI conversation, it produces
a compact, evidence-backed context package drawn from your own history.

The primary product surface is `context_for(conversation)` — a multi-lane
compiler that retrieves relevant beliefs, entities, and recent signals and
renders them as a sectioned context block for injection into an AI assistant.

All data stays on-device. No cloud services. No outbound network from any
corpus-reading process.

## What it ingests (V1)

| Source | Format | Status |
|--------|--------|--------|
| ChatGPT | JSON export | ingested (3,437 conversations) |
| Claude | ZIP export | ingested (78 conversations) |
| Gemini | Google Takeout JSON | ingested (4,401 conversations) |
| Obsidian | Vault on disk | Phase 1.5+ |
| MCP capture | Live via MCP tool | Phase 4+ |

## Architecture in one diagram

```text
sources
  → conversations / messages / notes / captures   (immutable raw evidence)
  → segments                                       (topic-segmented, embedded)
  → claims                                         (LLM-extracted, grounded)
  → beliefs                                        (bitemporal, stability-classed)
  → current_beliefs view
  → context_for(conversation)                      (multi-lane, sectioned output)
  → context_snapshots                              (hot state for low-latency serving)
```

Raw evidence is immutable after insert. Every downstream derivation is
versioned and non-destructive — re-segmentation and re-extraction supersede
prior rows without overwriting them.

## Key design properties

- **Three-tier separation:** raw evidence → claims → beliefs. No synthesis
  without grounding; accepted beliefs require at least one evidence id.
- **Bitemporal beliefs:** `valid_from/valid_to` + `observed_at/recorded_at`.
  Contradictions close the prior row and insert a new one — never UPDATE.
- **Topic segments as the embedding unit:** whole conversations are too broad;
  single turns lack context. LLM segmentation before extraction.
- **Simple weighted scorer in the live path:** no LLM reranker at serve time.
- **Privacy tiers:** carried on raw rows and derived units. Reclassification
  is a new capture row, not a column update.
- **No outbound network** from any corpus-reading process — enforced at the
  OS level, not just by discipline.

## Build order

Five phases with a smoke gate at the end. Currently at **Phase 1.5 complete**
(all three AI conversation sources ingested, schema stable).

See [BUILD_PHASES.md](BUILD_PHASES.md) for the full phase breakdown and
acceptance criteria.

## What is explicitly not in V1

- Auto wiki writeback to Obsidian (deferred — belief review queue instead)
- Goal / failure / hypothesis / pattern inference (cut — hallucination risk)
- LLM cross-encoder reranker in the live path (deferred — latency)
- Apache AGE / graph backend (deferred — relational entity edges sufficient)
- Bulk Evernote → Obsidian migration (deferred)
- Bidirectional Obsidian sync (deferred)

## Key documents

| Document | Purpose |
|----------|---------|
| [HUMAN_REQUIREMENTS.md](HUMAN_REQUIREMENTS.md) | Load-bearing principles. Read before anything else. |
| [DECISION_LOG.md](DECISION_LOG.md) | All accepted, deferred, and rejected decisions with rationale. |
| [BUILD_PHASES.md](BUILD_PHASES.md) | Five-phase build plan with acceptance criteria per phase. |
| [ROADMAP.md](ROADMAP.md) | Current step and what follows. |
| [docs/design/V1_ARCHITECTURE_DRAFT.md](docs/design/V1_ARCHITECTURE_DRAFT.md) | Schema primitives, build order, vector index, ranking formula. |
| [docs/design/ARCHITECTURE_EVOLUTION_DELTA_2026_04_29.md](docs/design/ARCHITECTURE_EVOLUTION_DELTA_2026_04_29.md) | Hot state / context snapshot promotion into V1. |
| [docs/schema/README.md](docs/schema/README.md) | Live ER diagram and column reference (auto-generated). |

## Infrastructure

| Component | Implementation |
|-----------|---------------|
| Database | PostgreSQL 16 + pgvector, local, 127.0.0.1 only |
| Embeddings | `nomic-embed-text` via Ollama |
| LLM (segmentation / extraction) | `qwen3.6-35b-a3b` via ik-llama |
| Language | Python 3.11+ |
| Schema migrations | Plain SQL files via custom runner |
