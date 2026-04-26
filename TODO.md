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

## Evernote → Obsidian Migration (prerequisite to note ingestion)

- [ ] Evaluate yarle vs. enex2md for ENEX → Markdown quality
- [ ] Decide on notebook → Obsidian folder structure
- [ ] Export Evernote notebooks to ENEX
- [ ] Convert ENEX → Markdown, land in Obsidian vault
- [ ] Verify conversion quality (attachments, formatting, metadata)

## Ingestion — Obsidian / Notes

- [ ] Locate/establish vault path
- [ ] Inspect converted note structure post-migration
- [ ] Decide: vault watcher vs. REST API plugin vs. both
- [ ] Write `sources/obsidian.py` — walk vault, emit episodes (Evernote origin notes + ongoing)
- [ ] Decide on bidirectional sync strategy (writing facts/patterns back as notes)

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

## Wiki Output Layer

- [ ] Design `wiki/SCHEMA.md` — page types, naming conventions, section templates
- [ ] Write `pipeline/wiki.py` — reads facts/patterns/goals/relationships, groups by concept/entity
- [ ] Implement entity page generation (person, project, tool, concept)
- [ ] Implement pattern page generation
- [ ] Implement goal page generation with evidence of progress
- [ ] Implement topic index generation
- [ ] Add `<!-- wiki-id: <uuid> -->` marker for idempotent re-runs
- [ ] Add `## Notes` section preservation (human edits not overwritten)
- [ ] Implement lint pass: contradictions, orphaned pages, stale claims
- [ ] Wire wiki output path to Obsidian vault directory

## MCP Server

- [ ] Choose MCP framework: FastMCP vs. raw modelcontextprotocol SDK
- [ ] Write `mcp/server.py` — entrypoint
- [ ] Write `mcp/tools/capture.py` — submit episode with type tag
- [ ] Write `mcp/tools/search.py` — semantic search across episodes/facts/patterns
- [ ] Write `mcp/tools/recall.py` — structured recall by namespace
- [ ] Write `mcp/tools/stats.py` — counts, top topics, recent activity
- [ ] Add `wiki_refresh` tool — trigger wiki regeneration for a namespace or page
- [ ] Wire up Obsidian MCP plugin to server
- [ ] Wire up Claude to server

## Publishing (export-chatgpt)

- [ ] Post to r/ChatGPT: "Export your entire ChatGPT conversation history — including Projects and Teams accounts"
- [ ] Post to HN: "Show HN: Export all your ChatGPT conversations including Projects (Teams accounts)"
