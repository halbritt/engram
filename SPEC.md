# stash-ingest

A DIY Python implementation of a Stash-inspired conversation history knowledge
base. Borrows [Stash's](https://github.com/alash3al/stash) schema and
8-stage consolidation pipeline design, reimplemented in Python against local
infrastructure with prompts tuned for local LLMs.

## Goal

Turn years of AI conversation history from multiple providers into a
queryable, self-consolidating knowledge base running entirely on local
infrastructure. No cloud services. No data leaving the machine.

## Sources

| Source | Format | Location |
|--------|--------|----------|
| ChatGPT | JSON export (conversations + projects) | `~/chatgpt-export/user-afXFt1wByKh5XA1L7njvUZnI/` |
| Claude | ZIP export (Anthropic data download) | TBD — needs export |
| Gemini | Google Takeout JSON | TBD — needs export |

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
| `episodes` | Raw conversation turns with embeddings |
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
```

## Episode Granularity

One episode per human+assistant turn (not per message, not per whole
conversation). Each episode content includes a metadata preamble:

```
[ChatGPT | gpt-4o | 2025-03-15 | "Snowboarding Layering Guide"]
Human: What should I wear for a cold powder day?
Assistant: For cold powder conditions you want...
```

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

## Repository Structure

```
db/
  migrations/          # SQL migration files (adapted from Stash's 20 migrations)
  schema.py            # migration runner

sources/
  chatgpt.py           # walks ~/chatgpt-export/, emits episodes
  claude.py            # walks Claude ZIP export, emits episodes
  gemini.py            # walks Gemini Takeout JSON, emits episodes
  base.py              # shared Episode dataclass and turn-extraction logic

pipeline/
  ingest.py            # embed + insert episodes
  consolidate.py       # orchestrates the 8-stage pipeline per namespace
  stages/
    facts.py           # stage 1: episodes → facts
    relationships.py   # stage 2: facts → relationships
    causal.py          # stage 3: facts → causal links
    patterns.py        # stage 4: facts + relationships → patterns
    decay.py           # stage 5: confidence decay (SQL only)
    goals.py           # stage 6: goal progress inference
    failures.py        # stage 7: failure pattern detection
    hypotheses.py      # stage 8: hypothesis evidence scanning

llm/
  embedder.py          # ollama nomic-embed-text client with caching
  reasoner.py          # ik-llama qwen3.6-35b client, JSON extraction helpers

config.py              # DB URL, LLM endpoints, batch sizes, namespace roots
main.py                # CLI: --source --consolidate --dry-run --limit N
```

## Open Questions

- [ ] Validate turn granularity with small batch before full ingest
- [ ] Confirm nomic-embed-text dimension (expected 768) with a test call
- [ ] Test consolidation prompt quality with qwen3.6-35b on a sample namespace
      before running full pipeline
- [ ] Stash consolidation default batch size is 100 — tune for 3,400+ corpus
- [ ] Claude export schema — inspect after download
- [ ] Gemini Takeout schema — inspect after download
