# stash-ingest

Ingestion pipeline for loading multi-source AI conversation history into
[Stash](https://github.com/alash3al/stash) — a local PostgreSQL + pgvector
knowledge base with an 8-stage consolidation pipeline (episodes → facts →
relationships → patterns → causal links → contradictions → goals/failures →
hypotheses).

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
| Knowledge base | [Stash](https://github.com/alash3al/stash) — run as-is |
| Database | Local PostgreSQL + pgvector |
| Embeddings | `nomic-embed-text` via ollama at `http://127.0.0.1:11434` |
| LLM reasoning | `qwen3.6-35b-a3b` via ik-llama at `http://127.0.0.1:8081/v1` |
| Ingestion language | Python |

Stash is configured to use OpenAI-compatible endpoints for both embeddings
and LLM reasoning — both ollama and ik-llama expose these.

## Namespace Design

Namespaces partition the Stash knowledge base by source and project:

```
/chatgpt/conversations          # regular ChatGPT conversations
/chatgpt/projects/<slug>        # per-project conversations
/claude/conversations           # Claude conversation history
/gemini/conversations           # Gemini conversation history
```

## Granularity

Episodes are submitted at **conversation-turn granularity** — one episode per
human+assistant exchange, not one per message and not one per whole
conversation. This gives the consolidation pipeline meaningful units to reason
over without drowning it in single-sentence fragments.

Each episode includes:
- The human message
- The assistant response
- Metadata in the content preamble: source, model, conversation title, date

Example episode content:
```
[ChatGPT | gpt-4o | 2025-03-15 | "Snowboarding Layering Guide"]
Human: What should I wear for a cold powder day?
Assistant: For cold powder conditions you want...
```

## Architecture

```
sources/
  chatgpt.py      # walks ~/chatgpt-export/, emits episodes
  claude.py       # walks Claude ZIP export, emits episodes
  gemini.py       # walks Gemini Takeout JSON, emits episodes

pipeline/
  ingest.py       # takes episodes, POSTs to Stash remember API
  normalize.py    # shared turn-extraction and formatting logic

config.py         # stash URL, namespace roots, batch size, dry-run flag
main.py           # CLI: --source chatgpt|claude|gemini|all --dry-run --limit N
```

## Stash API

Episodes are submitted via Stash's MCP `remember` tool or directly to the
Stash CLI. The Python ingestion pipeline will call the Stash HTTP/MCP API:

```
POST /mcp (or stash remember CLI)
{
  "namespace": "/chatgpt/projects/meal-planning",
  "content": "...",
  "occurred_at": "2025-03-15T10:30:00Z"
}
```

Stash handles embedding generation, storage, and background consolidation.
The ingestion pipeline's only job is normalization and submission.

## Stash Configuration

Stash needs to be pointed at local endpoints instead of OpenAI:

```yaml
# stash config
embedder:
  base_url: http://127.0.0.1:11434/v1   # ollama
  model: nomic-embed-text
  dimensions: 768                         # nomic-embed-text output dims

reasoner:
  base_url: http://127.0.0.1:8081/v1     # ik-llama
  model: qwen3.6-35b-a3b
```

## Ingestion Order

1. ChatGPT (schema known, export on disk, highest volume — good for shakeout)
2. Claude (needs export download first)
3. Gemini (needs Takeout export first)

## Open Questions

- [ ] Does Stash expose an HTTP REST API directly, or only MCP + CLI? Need to
      confirm the calling convention for the Python client.
- [ ] Stash consolidation batch size (default 100 episodes) — may need tuning
      for 3,400+ conversation corpus.
- [ ] Turn granularity vs. message granularity — validate with a small batch
      before full ingest.
- [ ] nomic-embed-text dimension: confirm ollama returns 768-dim vectors and
      that Stash's dynamic dimension setting handles this correctly.
- [ ] Stash's LLM prompts were written for GPT-4-class models — test
      consolidation quality with qwen3.6-35b before full run.
