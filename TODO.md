# TODO

## Infrastructure

- [ ] Set up local PG with pgvector extension
- [ ] Write `db/migrations/` — adapt Stash's 20 migrations, set vector dim to 768
- [ ] Write `db/schema.py` — migration runner
- [ ] Write `config.py` — DB URL, ollama endpoint, ik-llama endpoint, batch sizes
- [ ] Write `llm/embedder.py` — nomic-embed-text via ollama, with SHA256 cache
- [ ] Write `llm/reasoner.py` — qwen3.6-35b via ik-llama, JSON extraction helpers
- [ ] Confirm nomic-embed-text returns 768-dim vectors with a test call

## Ingestion — ChatGPT (first, schema known)

- [ ] Write `sources/base.py` — Episode dataclass, shared turn-extraction logic
- [ ] Write `sources/chatgpt.py` — walk `~/chatgpt-export/`, emit episodes
- [ ] Write `pipeline/ingest.py` — embed + insert episodes
- [ ] Write `main.py` CLI skeleton
- [ ] Validate turn granularity with small batch (50 conversations)
- [ ] Full ingest: 3,048 regular + 388 project conversations across 25 projects

## Ingestion — Claude

- [ ] Download Claude export (Settings → Privacy → Export data on claude.ai)
- [ ] Inspect export schema
- [ ] Write `sources/claude.py`

## Ingestion — Gemini

- [ ] Download Gemini history via Google Takeout
- [ ] Inspect export schema
- [ ] Write `sources/gemini.py`

## Consolidation Pipeline

- [ ] Write `pipeline/consolidate.py` — orchestrator, checkpoint management
- [ ] Write `pipeline/stages/facts.py` — episodes → facts (with contradiction detection)
- [ ] Write `pipeline/stages/relationships.py` — facts → entity relationships
- [ ] Write `pipeline/stages/causal.py` — facts → causal links
- [ ] Write `pipeline/stages/patterns.py` — facts + relationships → patterns
- [ ] Write `pipeline/stages/decay.py` — confidence decay (SQL only)
- [ ] Write `pipeline/stages/goals.py` — goal progress inference
- [ ] Write `pipeline/stages/failures.py` — failure pattern detection
- [ ] Write `pipeline/stages/hypotheses.py` — hypothesis evidence scanning
- [ ] Tune all prompts for qwen3.6-35b (not GPT-4 defaults)
- [ ] Test consolidation quality on small namespace before full run
- [ ] Tune batch size (Stash default 100) for 3,400+ corpus

## Publishing (export-chatgpt)

- [ ] Post to r/ChatGPT: "Export your entire ChatGPT conversation history — including Projects and Teams accounts"
- [ ] Post to HN: "Show HN: Export all your ChatGPT conversations including Projects (Teams accounts)"
