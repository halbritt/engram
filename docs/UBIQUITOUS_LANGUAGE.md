# Ubiquitous Language

> Starter glossary, drafted from SPEC.md, HUMAN_REQUIREMENTS.md,
> V1_ARCHITECTURE_DRAFT.md, and `migrations/`. Edit freely.
>
> Goal: pin terminology so future sessions don't re-litigate "what is a
> segment vs a capture vs an evidence row." When drift shows up in a
> session, update this file *inline*, not later.

## Bounded contexts

engram splits into five contexts. Keep terminology pinned within each.

| Context | Owns |
|---------|------|
| **Ingest** | Source-specific parsers (chatgpt, claude, gemini, obsidian, mcp capture) → raw_evidence rows |
| **Corpus** | Raw evidence (immutable), segments, claims, beliefs, embeddings, entities |
| **Retrieval** | `context_for` compiler, candidate lanes, ranking, snapshots, MCP serving |
| **Eval** | Gold set, smoke / tier-2 / full-corpus tiers, `context_feedback`, adversarial sweeps |
| **Lifecycle** | Privacy tiers, posthumous handoff, prompt/model versioning, re-derivation triggers |

The corpus-reading process has no network egress; the network-using
process has no direct corpus access. The wall is structural, not
disciplinary.

---

## Core distinctions (the ones that drift)

### Subject vs user vs consumer

- **Subject** — the one human whose biography this stores. Singular by design.
- **User** — colloquial alias for the subject when operating the system (CLI, review queue). Same person, different role.
- **Consumer** — a downstream model that *receives* `context_for` output. Frontier models, future local models, MCP clients. Consumers never touch the corpus directly.

Do not use "user" for consumers. The biography is *of* the user, *for* the consumers.

### Raw evidence vs `captures`

- **Raw evidence** — the collective term for the immutable layer: `sources`, `conversations`, `messages`, `notes`, `captures`. UPDATE/DELETE are blocked at trigger level.
- **`captures` (table)** — *one specific kind* of raw evidence: observations / tasks / ideas / references / person notes / user corrections / reclassifications.

A capture is evidence; not all evidence is a capture. Migration 001 is named `raw_evidence`; migration 002 reclassifies *within* it. When you mean the layer, say **raw evidence**. When you mean the table, say **captures**.

### Claim vs belief

- **Claim** — one LLM extraction from one segment, with `evidence_ids` to the raw rows that supported it. May contradict other claims; not yet adjudicated.
- **Belief** — a bitemporal, status-tracked, stability-classed assertion that survived consolidation. Has `valid_from` / `valid_to`, `confidence`, `stability_class`, `superseded_by` chain. `evidence_ids` is NOT NULL on `accepted`.
- **Current belief** — a belief with `valid_to IS NULL` (and `is_active` true per D027). Surfaced via the `current_beliefs` view.

Beliefs never derive from other beliefs. Both claims and beliefs trace back to raw evidence; that is the three-tier separation.

### Segment vs message vs conversation

- **Conversation** — one immutable row per source-side dialogue (one ChatGPT thread, etc.).
- **Message** — one immutable row per turn within a conversation. Has `role`, `sequence_index`. Raw turns are *not* embedded.
- **Segment** — a topic-coherent slice of contiguous messages, produced by LLM segmentation. The unit of embedding and the unit of claim extraction.

If something embeds a raw message directly, it's a bug — raw turns are out of the vector index by policy.

### Raw vs derived (the cache rule)

- **Raw** — the immutable layer. Source of truth. Storage is "everything forever."
- **Derived** / **cache** — segments, claims, beliefs, embeddings, entity_edges, snapshots, eval rows. Rebuildable from raw alone.

If a derivation cannot be reproduced from raw, it has become a second source of truth and the principle is broken.

### Belief supersession vs segment generation cutover

Two different non-destructive update mechanics. Don't conflate.

- **Belief supersession** (close-and-insert) — contradicting evidence closes the prior belief's `valid_to` and inserts a new row referenced by `superseded_by`. Bitemporal. Per-belief.
- **Segment generation cutover** (`is_active` flip) — re-segmenting under a new `segmenter_version` produces a *generation* of new rows; cutover flips `is_active` on segments and `segment_embeddings` only after required embeddings exist (D027 / D031). N-to-M, not 1:1.

Per D027, segment-level `superseded_by` was removed in favor of `is_active` precisely because segments don't supersede 1:1 across generations. Reach for `superseded_by` only on beliefs.

---

## Glossary by context

### Ingest

- **Source** — top-level `sources` row; one per ingested artifact (an export file, a Takeout zip, an MCP capture call). Discriminated by `source_kind`.
- **`source_kind`** — enum: `chatgpt | claude | gemini | obsidian | capture | future`. Not "platform," "vendor," "origin."
- **`external_id`** — the source-side identifier preserved verbatim; uniqueness with `source_id`.
- **`raw_payload`** — the original JSONB payload, untransformed. Always preserved; typed columns are optional projections of it.
- **Reclassification** — a `captures` row with `capture_type = 'reclassification'`, used to change a tier or category on prior rows without mutating them. See migration 002.

### Corpus

- **Generation** — a versioned cohort of segments produced under one `segmenter_version`. Tracked in `segment_generations`. The unit of cutover; not the unit of retrieval.
- **`segment_embeddings`** (D027) — the retrieval-visible vector table. HNSW index lives here so it can push down on `is_active` and `privacy_tier`. Distinct from `embedding_cache`.
- **`embedding_cache`** — pure API cache; SHA256-keyed input + `embedding_model_version` + `embedding_dimension`. Re-running an unchanged model is free. No retrieval index lives here.
- **Embedding** — vector representation of a segment or accepted belief. Versioned by `embedding_model_version`. Storage is dimension-flexible per D033; ANN indexes are scoped per active model/dimension.
- **Bounded / windowed segmentation** (D029) — over-budget parents are split into deterministic overlapping windows. `window_strategy` records how, so re-derivation is reproducible. Resumable per intra-parent checkpoint.
- **`is_active`** — flag on `segments` and `segment_embeddings`. Marks the row as part of the currently retrieval-visible generation. Flipped at generation cutover, never updated piecemeal.
- **Active sequence uniqueness** (D030) — at most one active segment per `(parent, sequence_index)`. Enforced at the database boundary, not by LLM JSON discipline.
- **Stability class** — one of `identity | preference | project_status | goal | task | mood | relationship`. Drives currentness decay in ranking. Identity decays slowly; mood decays fast.
- **Belief audit** — `belief_audit` table; one row per state transition (candidate → provisional → accepted → superseded → rejected).

### Retrieval

- **`context_for(conversation)`** — the primary product surface. Given a conversation, returns a sectioned context package. Pure read; no network egress.
- **Lane** — one candidate stream feeding `context_for`. Lanes: semantic belief, semantic segment, keyword/BM25, recent activity, active projects, mentioned-entity neighborhood, pinned profile facts, open contradictions, missing-data detection.
- **Section** — a labeled chunk in rendered output (Standing Context, Active Projects, Relevant Beliefs, Recent Signals, Entity Context, Raw Evidence Snippets, Uncertain / Conflicting, Missing Data / Gaps). Each has an explicit token budget.
- **Snapshot** (`context_snapshots`) — a precomputed rendered context, served warm via MCP. Refreshed asynchronously after capture / review / feedback / belief change.
- **Warm read** — serving from a fresh snapshot. Default path.
- **Cold compile** — synchronous full `context_for` recomputation when no fresh snapshot exists. Fallback.

### Eval

- **Gold set** — the subject-authored prompts that define what good looks like. The *actual* specification per the eval-as-oracle principle. Authoring cannot be delegated.
- **Smoke tier** — eval over ~100 conversations. Catches catastrophic pipeline failures.
- **Tier-2 / Gold-set validation** — eval over a 1,000–2,000 stratified, target-closed corpus slice. The true eval gate.
- **Full corpus** — 3,400+ conversations. Runs only after tier-2 passes without regression.
- **Eval gate** — the policy that full-corpus consolidation cannot proceed until tier-2 passes. Not relaxed under schedule pressure.
- **`context_feedback`** — table; one row per `useful` / `wrong` / `stale` / `irrelevant` annotation on a `context_for` output. References the belief and segment ids that produced the offending section. Treated as evolving ground truth.
- **Adversarial sweep** / **falsification sweep** — periodic multi-model pass over high-confidence beliefs ("what raw evidence would contradict this — find it"). Substitutes for engagement signal in a single-user system.
- **Preflight probe** — a small, phase-specific empirical check run *before* implementation, to validate assumptions the prompt is making (e.g., effective context window, structured-output behavior, cache conflict semantics). Cheaper than eval; runs once per phase. Distinct from a disproof probe.
- **Disproof probe** — a falsification challenge attached to an adversarial review finding ("what would have to be true for this not to be a problem"). Lives in the review document, not in the implementation prompt.

### Lifecycle

- **Privacy tier** — integer column on raw rows and derived units. Tier 1 (only-me, only-this-machine) is the default; tiers 2–5 per HUMAN_REQUIREMENTS.md. Reclassification is a new capture row, not a column update.
- **As-recorded tier** vs **effective tier** — the as-recorded tier is what was written to the raw row at insert time. The effective tier is computed at read time as the as-recorded tier overridden by the most-recent reclassification capture targeting that row (D023). They are not the same value, and forms that surface tier should say which.
- **Privacy inheritance** (D032) — a segment's privacy tier is `max(parent conversation/note/capture tier, all constituent raw-row tiers)`. Not just the parent, not just the rows.
- **Parent scope** — the unit of reclassification invalidation per D032. Reclassifying one message invalidates derived rows for its parent conversation/note/capture only — not the whole source export.
- **Posthumous handoff** — encrypted dead-man's-switch. After confirmed inactivity, keys release to designated successors per the privacy-tier model. Tier-5 categories are cryptographically destroyed pre-release.
- **`prompt_version` / `model_version`** — required on every belief. Pin which extraction prompt and which model produced it; re-derivation must be auditable.
- **Request profile** (D034) — the deterministic local-LLM call contract for derived stages: pinned endpoint and model id, streaming and thinking disabled, deterministic sampling, JSON schema response format, parse only `choices[0].message.content` (not `reasoning_content`). Recorded in derivation version metadata so re-runs are reproducible.
- **Re-derivation trigger** — capability change, not calendar. Four canonical triggers: new embedding model, new extraction prompt/model, new segmentation heuristic, targeted slice upgrade.

---

## Forbidden / corrected terms

| Don't say | Say instead | Why |
|-----------|-------------|-----|
| "memory" (as the noun for a unit) | belief / claim / segment / capture (be specific) | Collapses three-tier separation |
| "fact" | belief (with confidence + validity) | Hides uncertainty and time |
| "user data" | raw evidence, or the specific table | Obscures the layer |
| "extract a memory" | extract a *claim*, then consolidate to a *belief* | Skips adjudication |
| "delete the bad belief" | supersede via new raw evidence | Beliefs are never destructively updated |
| "the model decides" | the extraction prompt at `prompt_version=X` produced | Pin which version did it |
| "the model defaults" (for local-LLM call shape) | the request profile at D034 specifies | D034 forbids relying on model defaults for derivation calls |
| segment "supersedes" prior segment | segment generation cutover via `is_active` | Segments don't supersede 1:1; D027 removed `superseded_by` from segments |
| "send this to the cloud" | (rejected — local-first) | Refusal, not phrasing |
| "engram queries the web" | (rejected — corpus/network separation) | Same |

---

## Open terminology questions

Decisions still owed:

1. **"Episode"** — used in HUMAN_REQUIREMENTS.md and V1_ARCHITECTURE_DRAFT.md ("raw episode / message / note / capture id") but no `episodes` table exists. Alias for one of {conversation, message, segment}, or a deferred primitive? Pin or remove.
2. **"Hot state" vs "snapshot"** — used interchangeably in the 2026-04-29 delta. If they're the same, pick one. If hot state is broader (KV-cache prefix + snapshot + memory_events), say so.
3. **"Subject"** — the schema has `subject_entity_id` on beliefs. Is *the* subject (the person) the same concept as a *belief subject* (any entity), or are these distinct levels that happen to share a word?
4. **"Pinned"** — appears in "pinned facts," "pinned profile facts," and "promote-to-pinned" (review queue). Define the table-level mechanic.
5. **"Active"** — partially resolved. `is_active` on `segments` and `segment_embeddings` is now the canonical flag for "part of the current generation" (D027 / D031). "Active goals/projects" remains a colloquial use in the `context_for` lane vocabulary. If a third use creeps in (e.g., on captures), pin distinct names then.
6. **Generation** — used informally in the synthesis ("segment generation," "belief generation") but only `segment_generations` is a real table. Decide whether "belief generation" stays metaphorical or becomes a primitive.
7. **`reasoning_content` vs `content`** — D034 says parse `content` only, but a glossary entry on the assistant-message shape (and *why* `reasoning_content` exists) would help future implementers not silently drift back to it.
