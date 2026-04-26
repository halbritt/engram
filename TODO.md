# TODO

## Immediate

- [ ] Confirm Stash calling convention — REST API vs MCP-only vs CLI wrapper
- [ ] Stand up Stash locally against local PG
- [ ] Configure Stash to use ollama (nomic-embed-text) + ik-llama (qwen3.6-35b-a3b)
- [ ] Confirm nomic-embed-text returns 768-dim vectors; verify Stash dynamic dimension config

## Ingestion — ChatGPT (first, schema known)

- [ ] Write `sources/chatgpt.py` — walk `~/chatgpt-export/`, extract turns
- [ ] Validate turn granularity with small batch (50 conversations) before full run
- [ ] Full ingest: 3,048 regular + 388 project conversations across 25 projects

## Ingestion — Claude

- [ ] Download Claude conversation export (Settings → Privacy → Export data)
- [ ] Inspect export schema
- [ ] Write `sources/claude.py`

## Ingestion — Gemini

- [ ] Download Gemini history via Google Takeout
- [ ] Inspect export schema
- [ ] Write `sources/gemini.py`

## Consolidation validation

- [ ] Test consolidation quality with qwen3.6-35b (prompts written for GPT-4-class)
- [ ] Tune Stash consolidation batch size (default 100) for 3,400+ conversation corpus

## Infrastructure

- [ ] Write `config.py` — stash URL, namespace roots, batch size, dry-run flag
- [ ] Write `main.py` CLI — `--source chatgpt|claude|gemini|all --dry-run --limit N`
- [ ] Write `pipeline/normalize.py` — shared turn-extraction and formatting logic
- [ ] Write `pipeline/ingest.py` — episode submission to Stash

## Publishing

- [ ] Post to r/ChatGPT: "Export your entire ChatGPT conversation history — including Projects and Teams accounts"
- [ ] Post to HN: "Show HN: Export all your ChatGPT conversations including Projects (Teams accounts)"
