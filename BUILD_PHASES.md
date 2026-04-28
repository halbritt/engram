# Build Phases (V1, Step 4 — Smoke Pre-Pass)

> ROADMAP Step 4 ("Build pipeline + smoke pre-pass") decomposes into
> five phases. Each phase is a testable, reversible chunk. The smoke
> gate (D016) is the integrated test that runs at the end of Phase 5
> against a ~200-conversation subset, not a per-phase test.

## Why these boundaries

The phases break on natural dependency seams:

- **Phase 1 stops where LLM orchestration begins.** Raw ingest is pure
  schema + parsing; it can be validated with SQL tests alone, before any
  model-version variance enters the picture.
- **Phase 2 introduces both LLM dependencies together** (segmenter and
  embedder). Embeddings have no semantic unit without segments per D005
  / D009; splitting them serves no testable purpose.
- **Phase 3 introduces bitemporal state.** Beliefs and supersession are
  the highest-stakes correctness work; isolating them keeps debugging
  surface narrow.
- **Phase 4 introduces canonicalization and HITL surface.** Entities
  and the review queue let the user touch the system before it serves
  context.
- **Phase 5 adds the serving path.** `context_for` + ranking + MCP +
  feedback are the integration point where smoke can finally run.

## Phase 1 — Raw evidence layer

**Scope:** Postgres + pgvector baseline; raw schema (`sources`,
`conversations`, `messages`, `notes`, `captures`); ChatGPT export
loader.

**LLM dependencies:** none.

**Key tables / migrations:** `sources`, `conversations`, `messages`,
`notes`, `captures`. `privacy_tier` default Tier 1 per D019.
Row-level triggers prevent UPDATE/DELETE on raw tables (P4).
`raw_payload` JSONB on every raw row preserves the original.

**Acceptance criteria:**

- Schema migrates from empty.
- ChatGPT export loads end-to-end, idempotent on re-run.
- Immutability trigger blocks UPDATE/DELETE with a clear error.
- Conflicting re-ingest raises rather than overwriting.
- Postgres binds to 127.0.0.1; no outbound network calls in any code
  path (D020).

**Leaves for next phase:** raw rows ready to be segmented; no
derivations yet.

## Phase 2 — Segmentation + embeddings

**Scope:** topic segmentation of raw messages/notes; embedding generation
for segments; pgvector index over segments.

**LLM dependencies:** local segmenter via ik-llama (Qwen3.6:35B-MOE per
project setup); local embedder via Ollama (`nomic-embed-text` or
equivalent).

**Key tables / migrations:** `segments` (with `segmenter_version` and
`superseded_by` per D021); `embedding_cache` (SHA256-keyed input,
`embedding_model_version`, `embedding_dimension`); pgvector HNSW
index on segment embeddings per D009.

**Acceptance criteria:**

- Segmenter produces topic-coherent segments; short conversations may
  yield a single segment (D005).
- Re-segmentation under a new `segmenter_version` is non-destructive;
  prior rows close via `superseded_by`.
- Embedding cache hits on identical input + model version are free
  (no recomputation).
- Multiple `embedding_model_version` rows can coexist on one segment.
- `consolidation_progress` checkpoints make segmentation and embedding
  resumable per stage.

**Leaves for next phase:** segments embedded and retrievable by
similarity; ready for claim extraction.

## Phase 3 — Claim extraction + bitemporal beliefs

**Scope:** LLM-driven claim extraction; belief consolidation with
bitemporal validity, supersession, audit, and contradictions.

**LLM dependencies:** local extractor (same stack as Phase 2's
segmenter, separate prompt).

**Key tables / migrations:** `claims` (with extraction prompt/model
versions per D021); `beliefs` (bitemporal: `valid_from`, `valid_to`,
`observed_at`, `recorded_at`, `superseded_by`, `status`,
`stability_class`, `confidence`, `evidence_ids` NOT NULL on accepted —
per D003 / D004 / D008); `belief_audit` (per D010);
`contradictions` (per D019; supports adversarial sweeps and
consolidation-time conflicts).

**Acceptance criteria:**

- `evidence_ids` NOT NULL on accepted beliefs (D003) — enforced at
  the constraint level.
- Contradictions close prior belief's `valid_to` and insert a new row
  (close-and-insert, never UPDATE in place).
- `belief_audit` rows written on every state transition.
- Supersession chain reconstructs "what was extracted, with which
  model and prompt, at which time" without `original_*` columns
  (per D021).
- `consolidation_progress` checkpoints make extraction and
  consolidation resumable.

**Leaves for next phase:** beliefs ready for entity canonicalization
and HITL review.

## Phase 4 — Entity canonicalization + review surface

**Scope:** entity resolution; entity edges; `current_beliefs`
materialized view; belief review queue (CLI or thin web view).

**LLM dependencies:** entity disambiguation tiebreak via local LLM if
needed (per O003).

**Key tables / migrations:** `entities`, `entity_edges`,
`current_beliefs` materialized view (over beliefs with
`valid_to IS NULL`).

**Acceptance criteria:**

- Review queue exposes accept / reject / correct / promote-to-pinned
  per D006.
- `correct` writes a new `captures` row (per D017) — never mutates
  beliefs in place.
- `current_beliefs` view returns currently-valid beliefs efficiently.
- Entity edges support 1–2 hop neighborhood queries via recursive CTE
  (no graph backend per D007).

**Leaves for next phase:** beliefs are reviewable, queryable, and
canonicalized — ready to compose into context.

## Phase 5 — `context_for` + serving path

**Scope:** multi-lane candidate generation; weighted ranking;
sectioned token packing; MCP exposure; `context_feedback` capture.

**LLM dependencies:** none in the live serving path (D011 — simple
weighted scorer; LLM reranker deferred per F003).

**Key tables / migrations:** `context_feedback` (with
`correction_note TEXT NULL`).

**Acceptance criteria:**

- `context_for(conversation)` runs as a pure read in a process with
  no network egress (D020).
- MCP server binds 127.0.0.1 only.
- Rendered context items carry inline `(conf=…, src=…)` tags per D022.
- Gaps lane emits explicit "no data" markers rather than thin sections
  (D018).
- `context_feedback` annotations link back to belief and segment ids.
- Section token budgets honored.

**Leaves for the smoke gate:** the full pipeline is end-to-end
runnable on the ~200-conversation smoke subset.

## Smoke gate (D016) — runs after Phase 5

The integrated test. On a ~200 random-conversation subset:

- Ingestion populates raw tables.
- Segments embed.
- Claims extract.
- Beliefs land with `evidence_ids`.
- Contradictions get flagged when consolidation produces conflicts.
- Build resumes after interruption (per `consolidation_progress`
  checkpoints across all phases).

Pass/fail is schema-level, not retrieval-quality-level. Gold-set
authoring (Step 5) starts after smoke passes; the smoke pipeline's
output is the corpus inventory the gold set uses as a memory aid.

## Cross-cutting concerns

These thread through every phase; each phase prompt should reaffirm
them as acceptance criteria.

- **`consolidation_progress` checkpoints.** Every batch stage that
  touches the corpus must be resumable. Phase 2 (segmenter, embedder),
  Phase 3 (extractor, consolidator), Phase 4 (entity canonicalizer)
  each leave checkpoints.
- **Local-only execution.** No outbound network from any pipeline
  process. Postgres + LLM endpoints all on 127.0.0.1 (P2 / P3 / D020).
- **Raw immutability.** No UPDATE/DELETE on raw tables (P4 / D002).
  Re-derivation is non-destructive in every downstream phase.
- **`privacy_tier` default Tier 1.** Carried on raw tables and
  retrieval-visible derived units (segments, beliefs) — by carry or
  inheritance (D019).
- **Derivation versioning.** Every derived stage records its
  `*_prompt_version` / `*_model_version` so the corpus survives the
  model (D021 / P4).

## References

- [V1_ARCHITECTURE_DRAFT.md](V1_ARCHITECTURE_DRAFT.md) — schema
  primitives, build order, vector index policy, ranking formula.
- [DECISION_LOG.md](DECISION_LOG.md) — accepted decisions referenced
  inline above.
- [HUMAN_REQUIREMENTS.md](HUMAN_REQUIREMENTS.md) — load-bearing
  principles.
- [ROADMAP.md](ROADMAP.md) — Step 4 sits in the broader sequence;
  Step 5 (gold set) follows once smoke passes.
