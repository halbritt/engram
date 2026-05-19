# ENGRAM Codebase Summary

## 0. Files reviewed

Read for this summary:

- `/Users/halbritt/git/prompts/CODEBASE_SUMMARY.md`
- `AGENTS.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `CHANGELOG.md`
- `Makefile`
- `pyproject.toml`
- `docs/schema/README.md`
- `migrations/README.md`
- `migrations/001_raw_evidence.sql`
- `migrations/002_capture_reclassification.sql`
- `migrations/003_source_kind_claude.sql`
- `migrations/004_segments_embeddings.sql`
- `migrations/004_source_kind_gemini.sql`
- `migrations/005_source_kind_gemini.sql`
- `migrations/006_claims_beliefs.sql`
- `migrations/007_claim_audits.sql`
- `migrations/008_claim_extractions_request_profile_unique.sql`
- `migrations/009_phase4_entities_review.sql`
- `migrations/010_gold_labels.sql`
- `migrations/011_gold_label_session_targets.sql`
- `migrations/012_predicate_subject_kind_hint.sql`
- `migrations/013_interview_active_learning_state.sql`
- `src/engram/__init__.py`
- `src/engram/db.py`
- `src/engram/migrations.py`
- `src/engram/progress.py`
- `src/engram/chatgpt_export.py`
- `src/engram/claude_export.py`
- `src/engram/gemini_export.py`
- `src/engram/segmenter.py`
- `src/engram/embedder.py`
- `src/engram/extractor.py`
- `src/engram/consolidator/__init__.py`
- `src/engram/consolidator/transitions.py`
- `src/engram/phase4.py`
- `src/engram/cli.py`
- `src/engram/interview/__init__.py`
- `src/engram/interview/agent.py`
- `src/engram/interview/errors.py`
- `src/engram/interview/render.py`
- `src/engram/interview/sampler.py`
- `src/engram/interview/storage.py`
- `src/engram/interview/web.py`
- `src/engram/bench_review/__init__.py`
- `src/engram/bench_review/artifacts.py`
- `src/engram/bench_review/classify.py`
- `src/engram/bench_review/cli.py`
- `src/engram/bench_review/detail.py`
- `src/engram/bench_review/export.py`
- `src/engram/bench_review/storage.py`
- `src/engram/bench_review/web.py`
- `tests/conftest.py`
- test function inventories from `tests/test_cli.py`, `tests/test_phase1_raw.py`, `tests/test_phase2_segments.py`, `tests/test_phase2_embeddings.py`, `tests/test_phase3_claims_beliefs.py`, `tests/test_phase4_entities_review.py`, `tests/test_interview_storage.py`, `tests/test_interview_web.py`, `tests/test_bench_review.py`, and `tests/test_migrations.py`

Inventory-only reads:

- `rg --files` repository inventory, `find src/engram -type f`, DDL inventory for `migrations/*.sql`, and function/class inventories for the runtime Python modules and representative tests.

Skipped:

- `docs/reviews/**`, `docs/rfcs/**`, `docs/specs/**`, `docs/design/**`, `docs/operations/**`, `docs/howto/**`, `benchmarks/**`, `prompts/**` other than the executed prompt, and `striatum/**`: large design, review, workflow, and benchmark artifact sets. The prompt asks for current codebase behavior; canonical docs and source were used for architecture and runtime behavior.
- `agent-runner/**`: README marks it as an incubating generic terminal-agent orchestration tool and "not [Engram's] product boundary" (`README.md:230-240`).
- `src/engram/interview/templates/**`, `src/engram/interview/static/htmx.min.js`, `src/engram/bench_review/templates/**`, and `src/engram/bench_review/static/htmx.min.js`: package assets were inventoried, and package-data wiring was read in `pyproject.toml:35-37`, but template markup and vendored JavaScript were not needed to explain the runtime data model.

## 1. One-paragraph description

Engram is a local-first personal memory system for one person's AI conversation history. It ingests local ChatGPT, Claude, and Gemini exports into immutable raw-evidence tables, derives topic-sized conversation segments, embeds those segments with a local Ollama model, extracts structured claims with a local OpenAI-compatible LLM endpoint, consolidates those claims into bitemporal belief rows, and exposes local operator surfaces for review, correction, gold-label interviews, and benchmark triage (`README.md:5-14`, `README.md:22-36`, `pyproject.toml:5-13`). The code uses Python, PostgreSQL, pgvector, local model runtimes, and optional FastAPI/Jinja2 web UIs; the project rule is that no user corpus data leaves the machine unless the owner explicitly requests it (`AGENTS.md:3-5`, `HUMAN_REQUIREMENTS.md:64-119`).

## 2. Problem it solves

Engram addresses the repeated-work problem of making a new assistant understand the owner's prior projects, preferences, relationships, decisions, and open tasks without sending a private life-history corpus to a hosted memory service. A user points Engram at local export files, runs phase-scoped commands such as `make phase1-ingest-chatgpt`, `make phase2-run`, and `make phase3-run`, then reviews or labels derived memory with local CLI/web tools (`Makefile:39-61`, `Makefile:99-145`, `Makefile:150-172`). Without Engram, the user would manually search old conversation exports, paste context into each new assistant conversation, and maintain private memory notes by hand. The intended product surface remains `context_for(conversation)`, a local compiler that will produce a compact evidence-backed context package; the docs describe that as Phase 5 and not complete (`README.md:33-36`, `README.md:98-99`).

## 3. Architecture overview

Engram is primarily a CLI plus a PostgreSQL schema. The console script `engram = engram.cli:main` is defined in `pyproject.toml:29-30`; `src/engram/cli.py:155-681` builds the argparse command tree; `src/engram/db.py:11-16` resolves `ENGRAM_DATABASE_URL` and opens `psycopg` connections. SQL migrations are applied by `src/engram/migrations.py:61-112`, which records filenames and SHA-256 checksums in `schema_migrations`; `migrations/README.md:3-8` says changed applied migrations raise drift instead of silently no-oping.

Runtime state lives mostly in PostgreSQL. Phase 1 raw tables are `sources`, `conversations`, `messages`, `notes`, `captures`, and `consolidation_progress` (`migrations/001_raw_evidence.sql:27-108`). Triggers make raw evidence immutable after insert (`migrations/001_raw_evidence.sql:113-144`). Phase 2 adds `segment_generations`, `segments`, `embedding_cache`, and `segment_embeddings` (`migrations/004_segments_embeddings.sql:11-132`). Phase 3 adds `predicate_vocabulary`, `claim_extractions`, `claims`, `beliefs`, `belief_audit`, and `contradictions` (`migrations/006_claims_beliefs.sql:37-290`). Phase 4 adds `entities`, `entity_resolution_events`, `entity_edges`, `belief_review_actions`, `pinned_beliefs`, `current_beliefs`, and `belief_review_queue` (`migrations/009_phase4_entities_review.sql:4-209`). Gold-set interview state is stored in `gold_label_sessions`, `gold_labels`, `gold_label_session_targets`, and `gold_label_active_learning_events` (`migrations/010_gold_labels.sql:9-159`, `migrations/011_gold_label_session_targets.sql:6-59`, `migrations/013_interview_active_learning_state.sql:5-52`).

The operational architecture is a forward derivation pipeline:

```text
local export files
  -> phase1 ingest modules
  -> sources / conversations / messages / captures
  -> phase2 segmenter
  -> segment_generations / segments
  -> phase2 embedder
  -> embedding_cache / segment_embeddings
  -> phase3 extractor
  -> claim_extractions / claims
  -> phase3 consolidator
  -> beliefs / belief_audit / contradictions
  -> phase4 review + entities
  -> current_beliefs / belief_review_queue / entities / entity_edges
  -> future context_for(conversation)
```

Two local web apps exist, both optional and loopback-oriented. `src/engram/interview/web.py:710-1165` builds the FastAPI app for gold-label interviews over the same sampler/storage layer as the CLI. `src/engram/bench_review/web.py:43-215` builds a separate FastAPI workbench over a scratch SQLite review database for benchmark triage. FastAPI, Uvicorn, Jinja2, and `python-multipart` are in the `serve` optional extra, not the core dependency set (`pyproject.toml:15-27`).

## 4. Key data flows

### Ingest local exports

`engram phase1 ingest-chatgpt`, `engram phase1 ingest-claude`, and `engram phase1 ingest-gemini` are wired in `src/engram/cli.py:364-384` and dispatched in `src/engram/cli.py:705-724`. Each parser resolves local files, builds a manifest, parses conversations/messages, and inserts only raw evidence rows. ChatGPT ingestion is centered on `ingest_chatgpt_export()` (`src/engram/chatgpt_export.py:48-72`), export-root resolution (`src/engram/chatgpt_export.py:75-86`), manifest hashing (`src/engram/chatgpt_export.py:97-122`), and source/conversation/message inserts (`src/engram/chatgpt_export.py:318-468`). Claude and Gemini follow the same shape through `ingest_claude_export()` (`src/engram/claude_export.py:72-97`) and `ingest_gemini_export()` (`src/engram/gemini_export.py:60-84`). Source rows are guarded against external-id/hash conflicts in the ingestion modules, while the database enforces append-only raw evidence with triggers (`migrations/001_raw_evidence.sql:113-144`).

### Segment and embed active conversations

`engram phase2 run` calls segment batches and then embedding batches through the CLI dispatch path (`src/engram/cli.py:847-873`, `src/engram/cli.py:1420-1488`). The segmenter fetches candidate conversations that lack a current generation or have pending progress (`src/engram/segmenter.py:935-980`), probes a local ik-llama-compatible endpoint (`src/engram/segmenter.py:168-188`), sends deterministic structured chat-completion requests (`src/engram/segmenter.py:221-281`), parses strict JSON (`src/engram/segmenter.py:369-455`), and inserts `segments` under a `segment_generations` row (`src/engram/segmenter.py:506-790`, `src/engram/segmenter.py:1349-1537`). Privacy tier for a segment is derived from the parent conversation/messages during insert logic (`src/engram/segmenter.py:506-790`).

Embedding uses local Ollama through `OllamaEmbeddingClient` (`src/engram/embedder.py:61-82`). `embed_pending_segments()` selects segments without an embedding for the requested model, writes/reads `embedding_cache` by SHA-256 input hash, inserts `segment_embeddings`, and then activates completed segment generations only after every segment has an embedding (`src/engram/embedder.py:98-157`, `src/engram/embedder.py:159-294`, `src/engram/embedder.py:409-528`). The schema keeps cache and segment embedding rows immutable except activation metadata (`migrations/004_segments_embeddings.sql:178-226`).

### Extract claims and consolidate beliefs

`engram phase3 run` performs schema preflight, extractor health smoke, extraction, then consolidation (`src/engram/cli.py:875-970`, `src/engram/cli.py:1088-1375`). The extractor reads active AI-conversation segments only: `fetch_segment_payload()` joins active segments/generations and restricts `source_kind` to `chatgpt`, `claude`, and `gemini` (`src/engram/extractor.py:2014-2049`). `extract_claims_from_segment()` creates or reuses a `claim_extractions` row, chunks long segments, calls the local structured-output LLM, repairs some validation failures, inserts valid `claims`, and records extracted/failed status (`src/engram/extractor.py:788-1080`, `src/engram/extractor.py:1186-1396`, `src/engram/extractor.py:1946-2011`). Claims are insert-only and validated against segment evidence, extraction versions, predicate vocabulary, and object shape in database triggers (`migrations/006_claims_beliefs.sql:330-486`).

`consolidate_beliefs()` applies reclassification invalidations, optionally rebuilds, fetches conversations needing consolidation, and calls `consolidate_conversation()` (`src/engram/consolidator/__init__.py:109-247`). Consolidation groups active claims by subject/predicate/value (`src/engram/consolidator/__init__.py:607-683`), builds `BeliefPayload` values from claim evidence intervals and confidence means (`src/engram/consolidator/__init__.py:686-727`), and uses the transition API in `src/engram/consolidator/transitions.py:43-260` so the `beliefs` mutation trigger sees `engram.transition_in_progress` (`migrations/006_claims_beliefs.sql:488-593`). Contradictions are inserted for incompatible current values and auto-resolved when evidence intervals do not overlap (`src/engram/consolidator/__init__.py:893-960`).

### Review, correction, and gold labels

Phase 4 review commands operate on beliefs. `accept_belief()`, `reject_review_belief()`, `correct_belief()`, and `promote_to_pinned()` are in `src/engram/phase4.py:129-347`; correction creates a raw `captures` row of `capture_type='user_correction'` and records an append-only `belief_review_actions` row (`src/engram/phase4.py:221-291`). Entity construction reads `current_beliefs`, creates deterministic entities and edges, and exposes a bounded recursive neighborhood query (`src/engram/phase4.py:350-476`).

The gold-label interview sampler reads `claims` plus `current_beliefs` by default, applies cooldown/reask/strata filters, and emits `SampledTarget` rows with a candidate-pool snapshot ID (`src/engram/interview/sampler.py:185-290`, `src/engram/interview/sampler.py:417-466`). `InterviewAgent.record_verdict()` validates verdicts, renders a versioned prompt template, and inserts an append-only `gold_labels` row via storage helpers (`src/engram/interview/agent.py:40-122`, `src/engram/interview/storage.py:248-380`). The web app materializes sampled targets at session creation, routes verdict POSTs through the same agent, and enforces Origin and privacy-tier guards (`src/engram/interview/web.py:70-115`, `src/engram/interview/web.py:188-258`, `src/engram/interview/web.py:743-920`).

## 5. Entry points

- CLI console script: `engram`, mapped to `engram.cli:main` (`pyproject.toml:29-30`).
- Module invocation: Makefile targets invoke `.venv/bin/python -m engram.cli ...` (`Makefile:33-37`, `Makefile:39-61`, `Makefile:87-103`, `Makefile:129-172`, `Makefile:198-208`).
- Phase-scoped CLI commands: `phase1 ingest-*`, `phase2 segment|embed|run`, `phase3 extract|consolidate|run|re-extract|interview|bench-review`, and `phase4 refresh-current-beliefs|build-entities|smoke|review` are registered in `src/engram/cli.py:364-681`.
- Deprecated compatibility commands: top-level `ingest-*`, `segment`, `embed`, `extract`, `consolidate`, and `pipeline-3` still exist with warnings or forwarding; ambiguous `pipeline` fails closed before DB connection (`src/engram/cli.py:155-348`, `src/engram/cli.py:683-687`).
- SQL migrations: `engram migrate`, `make migrate`, and `make migrate-docker` call `migrate()` (`Makefile:33-37`, `src/engram/migrations.py:61-112`).
- Gold-label web UI: `engram phase3 interview serve --host 127.0.0.1 --port 8765` lazily imports FastAPI/Uvicorn after rejecting non-loopback hosts (`src/engram/cli.py:2275-2319`, `src/engram/interview/web.py:710-1165`).
- Bench-review web UI: `engram phase3 bench-review serve --slice ... --run ...` prepares a scratch SQLite DB and serves a local FastAPI workbench (`src/engram/bench_review/cli.py:28-60`, `src/engram/bench_review/storage.py:57-142`).
- Import surface: modules expose direct Python functions such as `engram.chatgpt_export.ingest_chatgpt_export`, `engram.segmenter.segment_pending`, `engram.embedder.embed_pending_segments`, `engram.extractor.extract_pending_claims`, `engram.consolidator.consolidate_beliefs`, and `engram.phase4.run_phase4_smoke`. `src/engram/interview/__init__.py:5-117` re-exports the interview sampler, agent, storage helpers, and a thin `GoldLabelStorage` facade.

## 6. Core abstractions

- `IngestResult` and parser rows in the export modules: per-source ingest summaries plus normalized conversation/message payloads; ChatGPT, Claude, and Gemini each transform vendor exports into the same `sources`/`conversations`/`messages` shape (`src/engram/chatgpt_export.py:48-72`, `src/engram/claude_export.py:72-97`, `src/engram/gemini_export.py:60-84`).
- `MigrationDriftError` and `migrate()`: checksum-backed forward migration machinery (`src/engram/migrations.py:13-18`, `src/engram/migrations.py:61-112`).
- `SegmenterClient`, `SegmentDraft`, `SegmentPayload`, and `segment_conversation()`: the Phase 2 structured segmentation contract and parent-conversation transaction boundary (`src/engram/segmenter.py:98-155`, `src/engram/segmenter.py:506-790`).
- `OllamaEmbeddingClient`, `embed_text()`, and `activate_completed_generations()`: local embedding fetch, cache write, segment embedding write, and generation activation (`src/engram/embedder.py:61-157`, `src/engram/embedder.py:409-528`).
- `ClaimDraft`, `ExtractorClient`, and `extract_claims_from_segment()`: structured claim extraction with validation, chunking, repair, accounting, and insert (`src/engram/extractor.py:450-542`, `src/engram/extractor.py:788-1080`).
- `ClaimRow`, `BeliefRow`, `BeliefPayload`, and the transition functions: deterministic claim grouping plus guarded belief insert/supersede/status transitions (`src/engram/consolidator/__init__.py:35-92`, `src/engram/consolidator/transitions.py:15-260`).
- Phase 4 review/entity functions: `accept_belief()`, `correct_belief()`, `build_deterministic_entities()`, and `entity_neighborhood()` make current beliefs reviewable and queryable as simple entity edges (`src/engram/phase4.py:129-476`).
- `GoldLabelSampler`, `SampledTarget`, `InterviewAgent`, and storage helpers: gold-set target selection and append-only verdict recording (`src/engram/interview/sampler.py:127-161`, `src/engram/interview/sampler.py:185-466`, `src/engram/interview/agent.py:40-122`, `src/engram/interview/storage.py:200-380`).
- Bench-review `CandidateRun`, `SegmentComparison`, and `ReviewSessionConfig`: local benchmark-artifact comparison state, stored in scratch SQLite rather than production Postgres (`src/engram/bench_review/artifacts.py:19-73`, `src/engram/bench_review/storage.py:43-59`).

## 7. External dependencies

Runtime Python dependency is `psycopg[binary]` for PostgreSQL access (`pyproject.toml:11-13`). Optional serve dependencies are FastAPI, Uvicorn, Jinja2, and `python-multipart` for the interview and bench-review web UIs (`pyproject.toml:22-27`). Dev dependencies are pytest, ruff, pyright, and the serve extra (`pyproject.toml:15-21`).

External local services are PostgreSQL with `pgcrypto` and `pgvector` extensions (`migrations/001_raw_evidence.sql:1-2`), Ollama for embeddings through `/api/embed` (`src/engram/embedder.py:61-82`), and an ik-llama/OpenAI-compatible local endpoint for segmentation and extraction through `/v1/models`, `/props`, and `/v1/chat/completions` (`src/engram/segmenter.py:168-281`, `src/engram/extractor.py:563-623`). The HTTP helpers reject non-local model URLs in the segmenter, embedder, and extractor (`src/engram/segmenter.py:1877-1923`, `src/engram/embedder.py:531-568`, `src/engram/extractor.py:563-623`).

The bench-review workbench also uses the Python standard-library `sqlite3` module for scratch review state (`src/engram/bench_review/storage.py:1-8`, `src/engram/bench_review/storage.py:57-142`). Tests use pytest and a real PostgreSQL test database supplied by `ENGRAM_TEST_DATABASE_URL`; the fixture rebuilds schema state and applies migrations before yielding a connection (`tests/conftest.py:10-89`).

## 8. Configuration and extension

Primary DB configuration is `ENGRAM_DATABASE_URL`, with `postgresql:///engram` as the default (`src/engram/db.py:11-16`). The Makefile provides local and Docker database URLs, test database URLs, and phase-scoped targets (`Makefile:1-11`, `Makefile:231-241`).

Segmentation is configured by module-level `ENGRAM_` environment variables, including ik-llama base URL, prompt/model version, max tokens, retries, timeout, context guard, window budget, overlap, adaptive split depth, and max error count (`src/engram/segmenter.py:23-52`). Embedding configuration uses `ENGRAM_OLLAMA_BASE_URL` and `ENGRAM_EMBEDDING_MODEL_VERSION` (`src/engram/embedder.py:20-24`). Extraction configuration includes `ENGRAM_EXTRACTOR_MODEL`, max tokens, timeout, retries, inflight timeout, max error count, chunk sizes, split depth, and concurrency (`src/engram/extractor.py:37-69`). Interview sampling cooldowns and reask behavior are configured with `ENGRAM_GOLD_COOLDOWN_*`, `ENGRAM_GOLD_ACTIVE_LEARNING_THRESHOLD`, and `ENGRAM_GOLD_REASK_CAP` (`src/engram/interview/sampler.py:36-55`). Interview web Origin extension uses `ENGRAM_INTERVIEW_ALLOWED_ORIGINS` while keeping default hosts loopback (`src/engram/interview/web.py:67-103`). Bench-review tuning uses `ENGRAM_BENCH_REVIEW_*` variables for rationale length, drop-count threshold, detail limits, candidate artifact size, and optional DNS suffixes (`src/engram/bench_review/storage.py:16-18`, `src/engram/bench_review/classify.py:7-9`, `src/engram/bench_review/detail.py:15-21`, `src/engram/bench_review/web.py:23-40`).

Extension points visible in the current code are source-specific ingest modules, SQL migrations, predicate vocabulary, prompt/model version constants, local model endpoint configuration, and phase-scoped CLI subcommands. The schema already has `notes`, `captures`, `obsidian`, and `capture` concepts (`migrations/001_raw_evidence.sql:4-18`, `migrations/001_raw_evidence.sql:71-98`), but README states notes/captures/Obsidian rows are future scope for Phase 2 and Phase 3 (`README.md:205-217`). Predicate expansion touches both SQL vocabulary and extractor constants because the Phase 3 preflight checks DB/code parity (`src/engram/cli.py:1176-1239`, `src/engram/extractor.py:154-391`).

## 9. What is missing or implicit

- `context_for(conversation)` is a documented product surface, not a runtime implementation in the current source tree. README and SPEC describe it (`README.md:33-36`, `SPEC.md:6-8`), and source search found no `def context_for` or `src/engram/api` package under `src/engram`.
- The canonical docs are not all synchronized to the same implementation date. `ROADMAP.md:7-15` says the current work is full Phase 2 segmentation, and `SPEC.md:54-60` says the project is at Phase 1.5/Phase 2 preflight. The runtime code and changelog include Phase 3 extraction/consolidation, gold-label interviews, Phase 4 review/entity functions, and bench-review tooling (`src/engram/extractor.py:788-1080`, `src/engram/consolidator/__init__.py:151-247`, `src/engram/phase4.py:129-505`, `CHANGELOG.md:62-93`).
- README status says "Phase 4 entity canonicalization + review | Not built yet" (`README.md:58-70`), while `migrations/009_phase4_entities_review.sql` and `src/engram/phase4.py` implement a bounded Phase 4 surface. The changelog narrows that distinction by saying Phase 4 full-corpus authorization remains blocked pending gate decisions (`CHANGELOG.md:84-93`).
- The no-egress requirement is partly code-enforced and partly environmental. Model endpoint helpers reject non-local URLs, and web serve commands refuse non-loopback bind by default (`src/engram/segmenter.py:1877-1923`, `src/engram/embedder.py:531-568`, `src/engram/cli.py:2275-2319`, `src/engram/bench_review/cli.py:25-60`). `SPEC.md:51-52` says no outbound network is enforced at the OS level; OS sandboxing or network namespace setup is not implemented inside `src/engram`.
- Obsidian and MCP capture are schema-reserved but not implemented as ingestion or serving paths in the code read. README says Obsidian and MCP live capture are deferred (`README.md:205-217`), and Phase 2/3 runtime queries currently restrict derived AI-conversation work to ChatGPT, Claude, and Gemini (`src/engram/extractor.py:2014-2049`, `src/engram/consolidator/__init__.py:328-396`).
- The database schema permits notes and captures, and segment tables allow `parent_kind IN ('conversation', 'note', 'capture')` (`migrations/004_segments_embeddings.sql:11-31`), but runtime segmentation code read in this pass centers on conversations (`src/engram/segmenter.py:506-790`, `src/engram/segmenter.py:935-980`).
- There are two historical Gemini enum migrations, `004_source_kind_gemini.sql` and `005_source_kind_gemini.sql`; both add `gemini` with `IF NOT EXISTS`. `migrations/README.md:16-24` explicitly documents the historical duplicate `004_` prefix and filename-stability rule.
- The web UIs are local operator tools, not a unified daemon. `src/engram/interview/web.py` and `src/engram/bench_review/web.py` each build their own FastAPI app, while RFC/design search results refer to a future `engramd`/MCP server path outside the current source package.
