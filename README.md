# engram

> A local-first memory layer for one human life.

Engram is a personal memory system for AI-assisted work and reflection. It
ingests local conversation exports, preserves the raw evidence, derives
topic-level segments, extracts grounded claims, consolidates those claims into
bitemporal beliefs, and eventually serves compact context packages through
`context_for(conversation)`.

The core promise is simple: no cloud dependency, no telemetry, and no user data
leaving the machine unless the owner explicitly asks for that. Corpus-reading
processes are designed to run against local files, local Postgres, and local
model runtimes.

## What It Does

Engram is meant to answer "what should the next assistant know about me, this
project, this relationship, this preference, or this prior decision?" without
turning private history into an opaque remote service.

It currently does four things:

- **Ingests AI conversation exports** from ChatGPT, Claude, and Gemini into an
  immutable raw evidence layer.
- **Segments and embeds conversation history** so retrieval works over coherent
  topics rather than whole conversations or isolated turns.
- **Extracts grounded claims** from active segments using a deterministic local
  structured-output LLM contract.
- **Consolidates claims into bitemporal beliefs** with provenance, confidence,
  stability class, contradiction tracking, and append-only audit history.

The intended product surface is still `context_for(conversation)`: a local
context compiler that will retrieve relevant beliefs, entities, recent signals,
and explicit gaps, then render them as a sectioned context block for an AI
assistant. That serving layer is Phase 5 and is not complete yet.

## How It Behaves

Engram is conservative by design.

- Raw evidence is append-only. Re-ingestion must be idempotent or fail; it must
  not silently overwrite prior evidence.
- Derived data is rebuildable. Segments, embeddings, extractions, and beliefs
  carry prompt/model/version metadata so newer derivations supersede older ones
  without destroying history.
- Claims and beliefs keep evidence links back to raw messages. The system pays
  for provenance so future review and correction can explain why a memory
  exists.
- Empty extraction is a real result. "No claim found" can be recorded as clean
  zero or accounted zero; unauditable parse/schema paths remain failures.
- Phase 3 beliefs are candidates. Human acceptance, correction, entity
  canonicalization, and the `current_beliefs` view arrive in Phase 4.
- The live serving path will avoid LLM reranking. V1 favors a simple weighted
  scorer with explicit confidence, provenance, and "no data" markers over false
  precision.

## Current Status

The project is currently between Phase 3 runtime validation and the Phase 4
entity/review build.

| Area | Status |
|------|--------|
| Phase 1 raw evidence | Implemented for ChatGPT exports. |
| Phase 1.5 multi-source ingestion | Implemented for Claude and Gemini exports. |
| Phase 2 segmentation + embeddings | Implemented for the AI-conversation corpus. |
| Phase 3 claims + bitemporal beliefs | Implemented and in bounded/full-corpus operational validation. |
| Phase 4 entity canonicalization + review | Not built yet. |
| Phase 5 `context_for` + MCP serving | Not built yet. |

Phase 3 has already moved through several runtime repair loops. The same-bound
`pipeline-3 --limit 500` gate completed with zero extraction failures and zero
consolidation skips after schema, validation-repair, and D064 accounted-zero
repairs. The first unbounded Phase 3 run then surfaced a JSON-null group-key
consolidator mismatch; that repair has targeted regression coverage, the full
test suite passed, and the unbounded run was intentionally stopped before
restart. The fast-moving Phase 3 runtime trail lives under
[docs/reviews/phase3/](docs/reviews/phase3/).

Gold-set authoring waits until claims and beliefs have stabilized enough to be
used as a memory aid. Segmentation alone is not the gold-set substrate.

## Architecture

```text
local exports / local captures
  -> sources / conversations / messages / notes / captures
     immutable raw evidence
  -> segments
     topic-bounded, versioned, embedded units
  -> claims
     atomic extracted assertions with raw evidence ids
  -> beliefs
     bitemporal consolidated state with audit and contradictions
  -> entities / current_beliefs
     Phase 4 canonicalization and review surface
  -> context_for(conversation)
     Phase 5 local context compiler and MCP serving path
```

The storage model separates evidence, extraction, and belief state because
mixing those layers is the fastest way to manufacture confident nonsense. A
bad extraction should be diagnosable, a bad consolidation should be possible
to supersede, and the raw message that caused either should still be available
unchanged.

## Operator Quick Start

Install the local Python environment:

```sh
make install
```

Start Postgres however you normally do, or use the Docker helper:

```sh
make db-up
make migrate-docker
```

For a local non-Docker database:

```sh
make migrate
```

Ingest local exports:

```sh
make phase1-ingest-chatgpt PATH=/path/to/chatgpt-export
make phase1-ingest-claude PATH=/path/to/claude-export-or-zip
make phase1-ingest-gemini PATH=/path/to/google-takeout
```

Run Phase 2:

```sh
make phase2-segment
make phase2-embed
make phase2-run
make phase2-run LIMIT=25
```

Run Phase 3:

```sh
make phase3-extract
make phase3-consolidate
make phase3-run
make phase3-run LIMIT=50
```

Useful bounded operator commands:

```sh
.venv/bin/python -m engram.cli phase2 segment --limit 10
.venv/bin/python -m engram.cli phase2 embed --limit 100
.venv/bin/python -m engram.cli phase2 run --limit 25
.venv/bin/python -m engram.cli phase3 extract --limit 25
.venv/bin/python -m engram.cli phase3 consolidate --limit 25
.venv/bin/python -m engram.cli phase3 run --limit 50
.venv/bin/python -m engram.cli phase4 smoke --limit 25
make phase4-smoke LIMIT=25
```

Useful targeted Phase 3 recovery commands:

```sh
.venv/bin/python -m engram.cli phase3 extract --segment-id UUID
.venv/bin/python -m engram.cli phase3 extract --conversation-id UUID --requeue
.venv/bin/python -m engram.cli phase3 consolidate --conversation-id UUID --batch-size 1 --limit 1
.venv/bin/python -m engram.cli phase3 consolidate --rebuild
```

### Phase 3 follow-on: Gold-set interview (RFC 0021)

`engram phase3 interview` is the append-only gold-label authoring surface.
See [docs/howto/gold-set-interview.md](docs/howto/gold-set-interview.md)
for the operator guide (verdict glossary, cooldowns, privacy-tier export
defaults, v1 Python harness for verdict capture).

Generic `pipeline` targets intentionally fail closed with phase-scoped
alternatives. Use Docker variants (`make phase2-segment-docker`,
`make phase2-embed-docker`, `make phase2-run-docker`,
`make phase3-extract-docker`, `make phase3-consolidate-docker`,
`make phase3-run-docker`, `make phase4-smoke-docker`) when the database is the
compose-managed Postgres instance.

Run tests:

```sh
make test
```

Regenerate schema docs after schema changes:

```sh
make schema-docs
```

Do not edit [docs/schema/README.md](docs/schema/README.md) by hand.

## Source Scope

| Source | V1 status | Notes |
|--------|-----------|-------|
| ChatGPT JSON export | Implemented | Phase 1 ingestion and Phase 2/3 AI-conversation substrate. |
| Claude export ZIP/directory | Implemented | Added in Phase 1.5 before LLM-derived stages. |
| Gemini Google Takeout | Implemented | Added in Phase 1.5 before LLM-derived stages. |
| Obsidian vault | Schema-reserved / deferred | Not part of current Phase 2 or Phase 3 runs. |
| MCP live capture | Schema-reserved / deferred | Capture and serving work return in later phases. |

Phase 2 and Phase 3 intentionally operate on the AI-conversation corpus only:
ChatGPT, Claude, and Gemini. Notes, captures, and Obsidian-derived rows remain
future scope even where the schema already has room for them.

## Stack

| Component | Implementation |
|-----------|----------------|
| Database | PostgreSQL + pgvector, local-only |
| Migrations | Plain SQL with filename + checksum identity |
| Embeddings | `nomic-embed-text` via Ollama |
| Local LLM stages | `qwen3.6-35b-a3b` via ik-llama |
| Application code | Python |
| Tests | pytest |

## Repository Map

| Path | Purpose |
|------|---------|
| [src/engram](src/engram) | Python package and CLI implementation. |
| [migrations](migrations) | Forward SQL migrations. |
| [tests](tests) | Unit and integration tests. |
| [docs](docs) | Design docs, RFCs, reviews, runbooks, and generated schema docs. |
| [prompts](prompts) | Phase handoff prompts and implementation prompts. |
| [benchmarks](benchmarks) | Evaluation and benchmark scaffolding. |
| [agent-runner](agent-runner) | Incubating generic terminal-agent orchestration tool; Engram is a reference use case, not its product boundary. |

## Canonical Docs

Read these before older brainstorm, review, and prior-art material:

| Document | Purpose |
|----------|---------|
| [HUMAN_REQUIREMENTS.md](HUMAN_REQUIREMENTS.md) | Load-bearing principles and long-arc ambition. |
| [DECISION_LOG.md](DECISION_LOG.md) | Accepted, rejected, superseded, and deferred decisions. |
| [BUILD_PHASES.md](BUILD_PHASES.md) | V1 phase boundaries and acceptance criteria. |
| [ROADMAP.md](ROADMAP.md) | Owner sequencing and attention artifact. |
| [SPEC.md](SPEC.md) | Current architecture summary. |
| [docs/README.md](docs/README.md) | Map of design docs, RFCs, reviews, and historical material. |
| [docs/segmentation.md](docs/segmentation.md) | Phase 2 segmentation behavior and operations. |
| [docs/claims_beliefs.md](docs/claims_beliefs.md) | Phase 3 claim extraction and belief consolidation contract. |
| [docs/schema/README.md](docs/schema/README.md) | Generated schema diagram and table reference. |
| [docs/reviews/phase3/](docs/reviews/phase3/) | Phase 3 build, review, and runtime validation trail. |

## Explicitly Deferred

- Auto wiki writeback to Obsidian.
- Goal, failure, hypothesis, pattern, and causal-link inference.
- LLM cross-encoder reranking in the live path.
- Apache AGE, Neo4j, Kuzu, FalkorDB, or another graph backend.
- Bidirectional Obsidian sync.
- Bulk Evernote migration.
- Note/capture/Obsidian claim extraction.
- Belief embeddings, `current_beliefs`, `context_for`, MCP serving, and
  `context_feedback` until their scheduled phases.

## Inspiration

- Stash: early consolidation-pipeline inspiration; not the current schema.
- OB1: MCP capture/tooling pattern.
- Graphiti, Mem0, Letta, GraphRAG, and older Memex-style systems: reference
  points, not direct architecture templates.
