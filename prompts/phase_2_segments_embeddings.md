# Phase 2 Prompt — Segmentation + Embeddings

> Hand this to a coding agent (Claude Code, Codex, or equivalent) to
> build Phase 2 per [BUILD_PHASES.md](../BUILD_PHASES.md). Read
> BUILD_PHASES.md for the phase-plan context; this file is the
> operational handoff.

> Precondition: D026's pre-Phase-2 adversarial review has run and any
> accepted deltas have already landed. If not, stop and run/synthesize
> [ADVERSARIAL_PROMPTS.md](../docs/design/ADVERSARIAL_PROMPTS.md)
> before implementing this prompt.

## Read first, in order

1. [HUMAN_REQUIREMENTS.md](../HUMAN_REQUIREMENTS.md) — load-bearing
   principles. Especially: "Why local-first is load-bearing," "Why
   corpus access and network egress are kept separate," "Why raw
   data is sacred," "Why model portability is a first-class concern."
2. [V1_ARCHITECTURE_DRAFT.md](../docs/design/V1_ARCHITECTURE_DRAFT.md) —
   schema primitives, vector index policy (segments + accepted beliefs
   only; no raw turns), 768-dim embeddings, build order steps 3–4.
3. [DECISION_LOG.md](../DECISION_LOG.md) — accepted decisions; do not
   re-litigate. Binding for this phase: D005 (segments are the main
   embedding/extraction unit), D009 (vector index policy), D019
   (`privacy_tier` carry/inheritance on retrieval-visible derived
   units), D020 (no network egress), D021 (derivation versioning
   across the pipeline — `segmenter_version`, `embedding_model_version`,
   `superseded_by`), D026 (pre-Phase-2 adversarial review before
   implementation).
4. [BUILD_PHASES.md](../BUILD_PHASES.md) — Phase 2 row, cross-cutting
   concerns (`consolidation_progress` checkpoints, raw immutability,
   privacy_tier carry, derivation versioning).
5. [src/engram/chatgpt_export.py](../src/engram/chatgpt_export.py) and
   [src/engram/claude_export.py](../src/engram/claude_export.py) —
   the conventions to mirror (idempotent batch ingest, atomic source
   upsert, dataclasses, `IngestConflict`, dedup via natural keys).

## Scope

Phase 2 only — topic segmentation of raw messages/notes and embedding
of the resulting segments. No claim extraction, no beliefs, no entity
canonicalization, no `context_for`. Each is a separate phase prompt.

## Build

1. **Investigate the actual local LLM stack first.** Per
   [SPEC.md](../SPEC.md#infrastructure) the stack is `nomic-embed-text`
   via Ollama at `http://127.0.0.1:11434` and `qwen3.6-35b-a3b` via
   ik-llama at `http://127.0.0.1:8081/v1` (OpenAI-compatible). Probe
   both before assuming — confirm models, dimensions, and endpoint
   shapes. Do not assume from external documentation that may be
   stale; read the running services.

2. **Schema migration** (`migrations/004_segments_embeddings.sql`).
   Two new tables; no changes to raw tables.

   `segments`:
   - `id UUID PK`
   - `source_id UUID NOT NULL REFERENCES sources(id)`
   - `source_kind source_kind NOT NULL` — segments inherit the kind
     of their source row.
   - `conversation_id UUID NULL REFERENCES conversations(id)` — set
     for segments derived from messages; NULL for note/capture
     segments.
   - `note_id UUID NULL REFERENCES notes(id)` and
     `capture_id UUID NULL REFERENCES captures(id)` — for the future
     non-conversation paths; NULL for now. (The columns land now so
     downstream phases don't need a migration; nothing in this phase
     populates them.)
   - `message_ids UUID[] NOT NULL` — the raw messages this segment
     spans (in order). Empty array allowed only for note/capture
     segments.
   - `sequence_index INT NOT NULL` — order of this segment within
     its parent conversation/note.
   - `content_text TEXT NOT NULL` — the segment text fed to the
     embedder, with role/source markers as the segmenter chose.
   - `summary_text TEXT NULL` — optional segmenter-emitted topic
     label or short summary, if it produces one.
   - `segmenter_prompt_version TEXT NOT NULL`
   - `segmenter_model_version TEXT NOT NULL`
   - `superseded_by UUID NULL REFERENCES segments(id)` — D021. NULL =
     currently active. Re-segmentation under a new prompt/model
     version inserts new rows and back-points the prior rows.
   - `privacy_tier INT NOT NULL DEFAULT 1` — carry from the source
     conversation/message; max() across the message set if they
     diverge (D019).
   - `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
   - `raw_payload JSONB NOT NULL` — the segmenter's raw output for
     this segment, including any rationales or scores it emits.
   - Subject to the immutability trigger in the same shape as raw
     tables: UPDATE allowed only on `superseded_by`; DELETE blocked.
     Implement as a trigger that lets `superseded_by` transition from
     NULL to a UUID and rejects every other column change.
   - Indexes: `(conversation_id, sequence_index)` partial WHERE
     `superseded_by IS NULL`; GIN on `message_ids`.

   `embedding_cache`:
   - `id UUID PK`
   - `input_sha256 TEXT NOT NULL` — SHA256 over the exact embedded
     text (not the segment id — the cache is content-keyed so beliefs
     in Phase 3 can share it).
   - `embedding_model_version TEXT NOT NULL`
   - `embedding_dimension INT NOT NULL`
   - `embedding vector(?) NOT NULL` — dimension matches what the
     probed embedder returns (768 for nomic-embed-text; verify).
   - `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
   - `UNIQUE (input_sha256, embedding_model_version)` — same input
     can have multiple model rows; same input + model is unique.
   - Fully immutable (no UPDATE, no DELETE — same trigger as raw
     tables).

   `segment_embeddings`:
   - `segment_id UUID NOT NULL REFERENCES segments(id)`
   - `embedding_cache_id UUID NOT NULL REFERENCES embedding_cache(id)`
   - `embedding_model_version TEXT NOT NULL`
   - `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
   - `PRIMARY KEY (segment_id, embedding_model_version)` — multiple
     model versions can coexist on one segment (D021).
   - HNSW index over the joined `embedding_cache.embedding` column —
     concretely, `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`
     on `embedding_cache`, plus a covering join path. Verify the
     pgvector version supports HNSW; if not, fall back to ivfflat
     and document the choice. (D009.)

3. **Segmenter** (`src/engram/segmenter.py`).
   - `segment_conversation(conn, conversation_id) -> SegmentationResult`.
     Pulls the conversation + ordered messages, builds the prompt,
     calls ik-llama, parses the structured response into 1..N
     segments. Short conversations may return a single segment
     (D005).
   - Output contract: a list of `{message_ids: [...], summary: str | None,
     content_text: str, raw: dict}`. The agent picks the prompt
     shape; record `segmenter_prompt_version` and
     `segmenter_model_version` on every row written.
   - `segment_pending(conn, batch_size, model_version) ->
     BatchResult`. Drives segmentation across all conversations
     with no active segment row under the current
     (`segmenter_prompt_version`, `segmenter_model_version`).
     Resumable per `consolidation_progress` (`stage='segmenter'`,
     `scope` = `source_id` or batch identifier; `position` records
     the last completed conversation_id).
   - Re-segmentation under a new prompt/model version inserts new
     rows and back-points the prior rows via `superseded_by`. Never
     UPDATE existing segment columns other than `superseded_by`.
     Re-running with the **same** versions is a no-op.

4. **Embedder** (`src/engram/embedder.py`).
   - `embed_text(text, model_version) -> EmbeddingResult` — checks
     `embedding_cache` by `(sha256(text), model_version)`. Cache hit
     returns the existing row id; cache miss calls Ollama, inserts
     the cache row, returns the new id.
   - `embed_pending_segments(conn, batch_size, model_version) ->
     BatchResult`. Drives embedding across active segments
     (`superseded_by IS NULL`) lacking a `segment_embeddings` row
     for the current model version. Resumable per
     `consolidation_progress` (`stage='embedder'`).
   - Multiple `embedding_model_version` rows can coexist on one
     segment. Re-embedding with a new model version is additive,
     not destructive.

5. **CLI subcommands** in `cli.py`:
   - `engram segment [--source-id ID] [--batch-size N] [--limit N]`
   - `engram embed [--model-version V] [--batch-size N] [--limit N]`
   - `engram pipeline` — convenience: run `segment` then `embed` with
     defaults.

6. **Makefile targets** parallel to existing ingest targets:
   `segment`, `embed`, `pipeline`, plus `-docker` variants.

7. **Tests** (`tests/test_phase2_segments.py`,
   `tests/test_phase2_embeddings.py`):
   - Segmenter end-to-end against a stubbed ik-llama response
     (mock the HTTP client at the boundary; do not call the real
     model in tests).
   - Idempotent re-segmentation under the same versions: count
     before == count after.
   - Version bump produces new active rows, supersedes prior rows
     via `superseded_by`, and prior rows are no longer
     `superseded_by IS NULL`.
   - Immutability trigger blocks UPDATE on segment columns other
     than `superseded_by`; DELETE blocked outright.
   - Embedder cache hit on identical input + model version (one
     model call, one cache row, two `segment_embeddings` rows).
   - Two distinct `embedding_model_version` rows coexist on the
     same segment.
   - Resumability: simulate a mid-batch interrupt by raising after
     N segments; re-running picks up at the recorded
     `consolidation_progress` position with no duplicates.
   - `privacy_tier` on segments inherits the max tier across the
     constituent messages.

8. **Docs** (`docs/segmentation.md`, sibling to
   `docs/ingestion.md`): how to run, what the segmenter prompt
   looks like (in-repo path), what counts as a segment, how
   versioning works, how supersession works, what's deferred
   (re-embedding existing rows is operator-driven; no automatic
   re-embed on segment supersession in this phase).

## Constraints (load-bearing — do not relax)

- Local only. No outbound network calls. Both LLM endpoints on
  127.0.0.1 (D020).
- Postgres binds to 127.0.0.1 (already enforced in Phase 1).
- Raw tables remain immutable. Segments are *also* immutable except
  for the `superseded_by` transition.
- Re-derivation is non-destructive: new rows + supersession, never
  in-place UPDATE.
- `privacy_tier` carries onto segments (D019).
- Every derived row records its `*_prompt_version` /
  `*_model_version` (D021).
- `consolidation_progress` checkpoints make both stages resumable.
  Phase 1 created the empty table; Phase 2 is the first writer.

## Acceptance criteria

- `make migrate` brings up the new tables from a Phase-1.5 schema.
- `make segment` segments all conversations end-to-end. Re-running
  with the same versions is a no-op (zero new rows).
- `make embed` embeds all active segments end-to-end. Re-running
  with the same model version is a no-op.
- Bumping `segmenter_prompt_version` produces new active segments
  and supersedes the prior generation; old `segment_embeddings`
  rows remain pointing at the old (now superseded) segments —
  re-embedding the new generation is a separate `embed` run.
- `consolidation_progress` has rows for `stage='segmenter'` and
  `stage='embedder'` after a run; `status='completed'` on a clean
  finish.
- All Phase 1 tests still pass; new tests cover the criteria
  above.
- HNSW (or ivfflat fallback) index exists and a similarity query
  returns sensible neighbors on the smoke subset.

## Non-goals (do not build in this phase)

- Claim extraction, beliefs, contradictions, `belief_audit` (Phase
  3).
- Entity canonicalization, `current_beliefs` view, review queue
  (Phase 4).
- `context_for`, ranking, MCP, `context_feedback` (Phase 5).
- Embedding raw turns or full conversations (D009 — segments only).
- Embedding beliefs (Phase 3 — beliefs don't exist yet).
- LLM cross-encoder reranker (F003 — deferred).
- Auto-re-embed on segment supersession. The new generation embeds
  on the next `embed` run.
- Obsidian / capture segmentation. Same pipeline shape, separate
  phase or follow-up prompt; the schema columns are present but
  unused here.

## When in doubt

Prefer the smallest change that satisfies the principles and the
acceptance criteria. Reach for DECISION_LOG and V1_ARCHITECTURE_DRAFT
before inventing. If a question isn't answered there, stop and ask
rather than guessing — Phase 2 is where model-version variance
enters the pipeline, and the wrong default propagates everywhere
downstream.
