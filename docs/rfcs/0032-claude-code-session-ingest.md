<a id="rfc-0032"></a>
# RFC 0032: Claude Code Session History Ingest

| Field | Value |
|-------|-------|
| RFC | 0032 |
| Title | Claude Code Session History Ingest |
| Status | proposal |
| Implementation | none |
| Date | 2026-05-12 |
| Owner | heath |
| Context | `src/engram/claude_export.py` (Claude desktop export ingester); `src/engram/chatgpt_export.py`; `src/engram/gemini_export.py`; `migrations/001_raw_evidence.sql` (`sources`, `conversations`, `messages`, `source_kind` enum); `migrations/003_source_kind_claude.sql` (`source_kind` extension precedent); `migrations/004_source_kind_gemini.sql`; `migrations/004_segments_embeddings.sql` (segment / embedding pipeline); engram principles: local-first, raw-is-sacred, derived tables rebuildable, hybrid retrieval |

Decision refs:
  - none yet (proposal)

Review refs:
  - none

Phase refs:
  - PHASE-0001-5 (Phase 1.5 — multi-source ingestion; this RFC extends the
    same posture to a fourth AI-conversation source)
  - PHASE-0002 (Phase 2 — segmentation + embeddings; existing infra is the
    target for chunked retrieval, not a parallel `cc_chunks` table)

## Summary

Pull Claude Code session transcripts from every machine where the operator
runs the CLI into engram's raw-evidence layer, so Claude Code becomes a
first-class memory source alongside the Claude desktop export, the ChatGPT
export, and Google Takeout. The same ingest also defends against Claude
Code's silent auto-pruning of old `.jsonl` session files: once a session
file has been mirrored to proximal it is durable, even if the originating
host evicts it.

This is a new ingester on top of existing engram infrastructure. It is not
a new retrieval stack, not a new embedding model, and not a new schema
universe.

## Motivation

- **Lossy by default.** Claude Code prunes session files under
  `~/.claude/projects/` over time. Anything not archived is gone.
- **Siloed.** Sessions live per-machine, per-project-path. There is no
  cross-host, cross-project search today.
- **High-signal content.** These transcripts capture actual engineering
  reasoning: why a particular CCT was chosen, why the Krieger was swapped
  back, how a PCB net list was reorganized, the dead-ends on the DMLS
  valve. That belongs in engram next to the chat exports it already
  ingests.
- **Infra already exists.** pgvector + `nomic-embed-text:latest` + hybrid
  retrieval already run in production. Segmentation and embedding for
  raw `messages` is already wired (PHASE-0002). The Claude desktop export
  ingester (`src/engram/claude_export.py`) is the closest template; the
  ChatGPT and Gemini ingesters are the next closest. Adding Claude Code
  is a new ingester, not new architecture.

## Source format

- `~/.claude/projects/<encoded-cwd>/<session-uuid>.jsonl` — one session
  per file, one JSON event per line. Events include user messages,
  assistant messages (with structured content blocks), tool uses, tool
  results, and metadata.
- `~/.claude.json` — index of projects and recent prompts. Useful for
  resolving encoded directory names back to real paths, and for tying
  a session to its working directory at the time of use.
- `~/.claude/history.jsonl` — global flat list of typed prompts. Lower
  priority; mostly redundant with project transcripts but useful for
  reconstructing a typed-prompt timeline independent of full sessions.

## Architecture

```
[dev box, laptop, proximal itself]
        |
        | systemd timer, hourly
        v
   rsync --archive --no-delete
   ~/.claude/projects/  --->  proximal:/var/lib/engram/claude-code/<hostname>/
                              ~/.claude.json
                              ~/.claude/history.jsonl
        |
        | engram-cc-ingest (new ingester, sibling to claude_export.py)
        v
   parse JSONL --> dedup --> normalize --> upsert
        |
        v
   postgres: sources, conversations, messages
   (segmentation + embedding follow the existing Phase 2 pipeline)
```

Key properties:

- **Pull-style, idempotent.** Each source host pushes its `~/.claude/`
  to a hostname-scoped directory on proximal. `--no-delete` is required:
  Claude Code's pruning is exactly what we are defending against, so
  proximal becomes the durable copy.
- **Dedup by `(host, session_uuid, event_index)`.** Re-ingesting the same
  session is a no-op. Append-only growth during a live session is
  handled by re-reading the file and emitting only events past the last
  seen index.
- **Raw-is-sacred.** The original `.jsonl` line goes into
  `messages.raw_payload` unmodified. Display-friendly flattening lives
  in `content_text`. Re-derivation is always possible from the raw line.

## Schema approach

The original draft proposed a parallel `engram.cc_sessions`,
`engram.cc_events`, `engram.cc_chunks` schema. **The repository audit
this RFC was written against argues against that.** The existing
`sources` / `conversations` / `messages` triad (`migrations/001_raw_evidence.sql`)
already models exactly this shape, and the existing segment / embedding
pipeline (`migrations/004_segments_embeddings.sql`) already produces
hybrid-retrievable chunks keyed by `source_kind`. The Gemini and Claude
desktop ingesters set the precedent: extend the `source_kind` enum,
reuse the canonical tables, and let Phase 2 handle chunking.

Concretely:

1. Add a new `source_kind` value via a migration parallel to
   `migrations/003_source_kind_claude.sql` and `migrations/004_source_kind_gemini.sql`:

   ```sql
   ALTER TYPE source_kind ADD VALUE IF NOT EXISTS 'claude_code';
   ```

2. Each `.jsonl` file becomes one `conversations` row with
   `source_kind = 'claude_code'`, `external_id = "<host>/<session_uuid>"`,
   `raw_payload` carrying session-level metadata (project path, host,
   started_at, ended_at, event_count, token totals when present).
3. Each event line becomes one `messages` row, `sequence_index = event_index`,
   `role` mapped from `user | assistant | tool | system`, `content_text`
   flattened from content blocks for display + FTS, full original line
   preserved in `raw_payload`.
4. Tool calls land in `messages.raw_payload` under a stable shape (event
   type, tool name, args, tool-result correlation). They are
   structured-searchable from JSONB without occupying their own table.
5. Segmentation and embedding then run the existing pipeline; chunks
   land in `segments` / `segment_embeddings`, joined to retrieval via
   the same paths used by `chatgpt`, `claude`, and `gemini` sources.

Schema extensions worth a follow-on migration once the ingester lands:

- `sources.host_origin TEXT NULL` — explicit host attribution. Currently
  the host is encoded into `external_id`; promoting it to a column
  enables per-host filters and reporting without JSONB extraction.
- `conversations.project_path TEXT NULL` — the decoded CWD, useful for
  per-project query scoping.

If a future analytics need genuinely cannot be served from this layout
(e.g. tool-call rollups across millions of events), a derived
projection table can be added later — derived tables are rebuildable
from raw, which is exactly the engram pattern. The proposal here is to
**not** front-load that table when nothing yet reads it.

## Chunking strategy

Per-event embedding is too noisy: tool calls fragment meaning across
many tiny chunks. Per-session is too coarse: sessions can be 50K+
lines.

Proposed: **conversational turn windows.** Group contiguous events into
~500–1500 token chunks, breaking on natural boundaries:

- New user message after a long assistant turn.
- Topic shift detected by simple heuristic (long pause between events,
  `/clear`-style commands, or new working directory).
- Tool-result blocks attach to the preceding assistant turn rather
  than producing standalone chunks.

This is a per-source segmenter window strategy — it slots into the
existing `segments.window_strategy` column (`whole | windowed`) without
introducing a new pipeline. The exact heuristic should be tuned once
Phase 2 starts producing chunks for real sessions.

Tool calls remain in `messages.raw_payload` for structured search ("when
did I last edit `claw-pcb/schematic.sch`?"), but only their
human-readable text contributes to the embedded chunk.

## Phasing

**Phase 1 — durable copy (1 evening).**
rsync timer on each host → proximal. No DB writes yet. This alone
removes the auto-deletion risk and is the highest-priority part of
the proposal: data not yet captured is data engram can never have.

**Phase 2 — minimal ingester.**
Parse JSONL → `sources` + `conversations` + `messages` with
`source_kind = 'claude_code'`. No embeddings yet. Enables `psql` /
`jq` search and proves the schema choice.

**Phase 3 — embeddings + hybrid retrieval.**
Wire Claude Code conversations into the existing Phase 2 segmenter
and embedder so chunks land in `segments` / `segment_embeddings`. At
this point Claude Code is queryable through the same path as every
other source.

**Phase 4 — enrichment.**

- Lazy per-session summaries via the local model.
- File-path cross-reference: when a `messages.raw_payload` mentions a
  file path, link to a normalized `files` table (Phase 4 follow-on,
  not Phase 4-the-engram-build-phase).
- Tool-call analytics: most-edited files, longest-running sessions,
  recurring tool-error patterns. Useful for a proactive nudge layer.

## Considerations and open questions

- **Secrets in transcripts.** Sessions often contain pasted API keys,
  IPs, and config snippets. Two options: scrub at ingest (regex +
  entropy heuristics) into a derived `content_text` while preserving
  the raw payload, or store unscrubbed and rely on engram being a
  closed local system. Leaning unscrubbed (proximal is air-gapped from
  cloud, Tailscale-only, single-operator), but flagging for explicit
  decision before Phase 2 lands. A `privacy_tier` column already
  exists on `messages` and can be used to mark sessions known to
  contain credentials.
- **`~/.claude/history.jsonl` priority.** Skip in Phase 2. It is
  mostly redundant with project transcripts. Reconsider in Phase 4 if
  a clean timeline of prompts independent of full sessions is wanted.
- **Multi-host project deduplication.** The same project cloned on
  the dev box and on proximal will produce two encoded directory
  paths and so two distinct session streams. Options: canonicalize by
  git remote at ingest, or accept that they remain separate streams
  and let the agent layer reconcile when querying. Proposed default
  is "separate streams"; canonicalization is a Phase 4 derived
  projection if it earns its keep.
- **Long sessions and token cost.** Some sessions will be 50K+ lines.
  Embedding cost is fine (local Ollama). Per-session summary
  generation in Phase 4 needs a hierarchical strategy — chunk
  summaries roll up to a session summary — rather than a single
  pass over the whole transcript.
- **Schema overlap with existing exporters.** The repository already
  models AI-conversation sources via `sources` / `conversations` /
  `messages` keyed on `source_kind`, with precedent migrations for
  `claude` and `gemini`. Reusing those tables (rather than a parallel
  `cc_*` family) is the recommendation of this RFC; the original
  draft listed this as open. Treating it as resolved here.
- **Ingester home in the repo.** A sibling module to
  `src/engram/claude_export.py`, `src/engram/chatgpt_export.py`, and
  `src/engram/gemini_export.py` — proposed name
  `src/engram/claude_code_sessions.py`. CLI wiring follows the
  existing per-source subcommand pattern in `src/engram/cli.py`.

## Non-goals

- Real-time streaming. Hourly batch is fine; sessions are not
  time-critical to ingest.
- Replacing Claude Code's built-in `/resume`. This is read-only
  archival plus search.
- Exposing transcripts outside proximal. Local-only, identical
  posture to the rest of engram.
- A new retrieval surface. Existing hybrid retrieval is what serves
  these chunks.

## Acceptance criteria

A Phase 2 implementation lands when:

1. `migrations/NNN_source_kind_claude_code.sql` adds the new
   `source_kind` value and any host / project columns the ingester
   needs.
2. `src/engram/claude_code_sessions.py` ingests one or more
   `~/.claude/projects/` trees idempotently into `sources`,
   `conversations`, and `messages` with `source_kind = 'claude_code'`.
3. `engram ingest claude-code <path>` (or the existing per-source CLI
   convention) is wired in `src/engram/cli.py`.
4. Tests under `tests/` cover: idempotent re-ingest, append-only
   growth of a live session file (re-read tail-only), event-type
   coverage (user / assistant / tool_use / tool_result / system),
   and content-flattening for tool-call payloads.
5. Existing tests stay green (`make test`).
6. `CHANGELOG.md` and `DECISION_LOG.md` updated per AGENTS.md.

Phase 3 (embeddings + retrieval) is a follow-on RFC update or
decision-log entry once the segmenter window strategy for Claude Code
sessions is chosen.

## Risks

- **Privacy boundary on raw transcripts.** Mitigated by local-only
  posture, `privacy_tier`, and the option to scrub at ingest if the
  unscrubbed path is rejected.
- **Schema drift across exporters.** Mitigated by reusing the
  canonical tables rather than forking a parallel `cc_*` family.
- **rsync misconfiguration deleting upstream copy.** Mitigated by
  `--no-delete` on the proximal side and a documented invariant that
  proximal is the durable copy.

## Next step

Phase 1: write the rsync unit + timer on the dev box. Two files,
~30 lines. Once roughly a week of data has accumulated on proximal,
move to Phase 2 (the ingester) under this RFC.
