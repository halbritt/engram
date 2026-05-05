# Pre-Phase-2 Adversarial Review

Date: 2026-04-30
Round: Round 0 (Phase 2 Segmentation + Embeddings Adversary)

## 1. Blocking before Phase 2

### Finding 1.1: KNN Pre-filtering Collapse Over Joins
*   **Description:** The proposed schema puts the `HNSW` index on `embedding_cache.embedding`. However, semantic search *must* filter out superseded segments (`segments.superseded_by IS NOT NULL`) and inaccessible privacy tiers. Postgres cannot efficiently push filters across a JOIN into an HNSW index scan. Over time, as re-segmentation creates a graveyard of superseded rows, an HNSW scan on the cache table will return vectors that join to dead segments, starving your `LIMIT K` of active results.
*   **Decision or document touched:** `docs/design/V1_ARCHITECTURE_DRAFT.md`, `prompts/P007_phase_2_segments_embeddings.md`, `BUILD_PHASES.md`, `DECISION_LOG.md` (D027).
*   **Proposed doc / schema / prompt delta:** Denormalize the vector. Move the `embedding vector` column and its index to `segment_embeddings`. Add an `is_active` boolean and `privacy_tier` to `segment_embeddings` so pgvector can utilize a partial index (`CREATE INDEX ... WHERE is_active = true AND privacy_tier <= 2`). `embedding_cache` should remain a pure deduplication cache without a vector index.
*   **Minimal experiment or inspection that would disprove the concern:** Insert 100,000 dummy vectors into a Postgres instance mimicking the 1-to-N join from `embedding_cache` to `segments`. Mark 95% of them as superseded. Apply a `LIMIT 10` vector search and measure the recall collapse and query execution time. This will instantly prove why the vector must be denormalized.
*   **Cost of being wrong if Phase 2 ships unchanged:** Vector search will silently degrade as re-segmentations occur, eventually returning zero valid results for highly-superseded topics.

### Finding 1.2: N-to-M Supersession Mapping is Impossible
*   **Description:** The `segments.superseded_by UUID REFERENCES segments(id)` schema assumes a 1-to-1 mapping. If a conversation was previously split into 3 segments and a new prompt version splits it into 4, you cannot map the old rows to the new rows with a single UUID pointer.
*   **Decision or document touched:** `prompts/P007_phase_2_segments_embeddings.md` (Schema migration), `DECISION_LOG.md` (D027).
*   **Proposed doc / schema / prompt delta:** Drop `superseded_by` from `segments`. Supersession is a property of the *generation*, not the row. Use a simple `is_active BOOLEAN` flag that gets toggled when a new segmentation batch completes for that source.
*   **Minimal experiment or inspection that would disprove the concern:** Try to write a SQL query that correctly updates the `superseded_by` column mapping 3 old segment UUIDs to 4 new segment UUIDs without inventing arbitrary relationships.
*   **Cost of being wrong if Phase 2 ships unchanged:** Resegmentation batches will crash or fail to correctly deprecate old segment rows, leaving multiple active generations of the same conversation.

### Finding 1.3: Multiple Dimensions in One Pgvector Column
*   **Description:** `embedding_cache` specifies `embedding_dimension INT` and `embedding vector`. If you mix 768d and 1536d vectors in the same unconstrained `vector` column, `CREATE INDEX ... USING hnsw` will crash, as HNSW requires a uniform dimension across the index.
*   **Decision or document touched:** `prompts/P007_phase_2_segments_embeddings.md` (Schema migration).
*   **Proposed doc / schema / prompt delta:** You must either use table partitioning by `embedding_dimension`, or mandate that the schema migration explicitly creates a partial index (`WHERE embedding_dimension = 768`) and constrain the vector column.
*   **Minimal experiment or inspection that would disprove the concern:** Attempt to create an HNSW index on a generic `vector` column containing both 768 and 1536 dimension vectors.
*   **Cost of being wrong if Phase 2 ships unchanged:** Index creation will fail during migration or crash at runtime when a new model is introduced.

### Finding 1.4: Privacy Tier Reclassification Cascade Leak
*   **Description:** D023 mandates that privacy tier reclassifications are evaluated at read time via new capture rows. However, `segments.privacy_tier` is materialized at extraction time. A Tier 1 message promoted to Tier 5 *after* segmentation will leave a Tier 1 segment exposed in the vector index indefinitely.
*   **Decision or document touched:** `prompts/P007_phase_2_segments_embeddings.md` (Segmenter contract).
*   **Proposed doc / schema / prompt delta:** The segmenter batcher must treat `capture_type='reclassification'` as a trigger to invalidate and re-segment/re-embed the affected sources.
*   **Minimal experiment or inspection that would disprove the concern:** Track whether vector search results respect a post-segmentation `reclassification` capture without explicit cache invalidation.
*   **Cost of being wrong if Phase 2 ships unchanged:** Severe privacy and security breach; redacted or highly sensitive information remains accessible to the LLM context path.

### Finding 1.5: Poison-Pill Infinite Loops
*   **Description:** The `segment_pending` resumable batcher targets "all conversations with no active segment row". A conversation that consistently crashes the segmenter (e.g., context window overflow, unparseable characters) will repeatedly fail, crashing the batcher forever.
*   **Decision or document touched:** `prompts/P007_phase_2_segments_embeddings.md` (Schema migration, Segmenter contract).
*   **Proposed doc / schema / prompt delta:** Add an `error_count INT DEFAULT 0` and `last_error TEXT` to `consolidation_progress` to allow the batcher to skip poison pills after N retries.
*   **Minimal experiment or inspection that would disprove the concern:** Run the proposed `ik-llama` segmenter prompt on the single largest ChatGPT message in the raw corpus. Verify whether it hallucinates, truncates silently, or throws an error.
*   **Cost of being wrong if Phase 2 ships unchanged:** The ingestion pipeline will halt permanently on the first unparseable conversation.

## 2. Non-blocking but document now

### Finding 2.1: Sub-Note/Sub-Message Provenance Loss
*   **Description:** For long Obsidian notes (e.g., 10,000 words) or large ChatGPT single turns, pointing to `note_id` or `message_id` as provenance loses the specific span. Downstream claims will cite the entire massive artifact, wasting tokens when rendered in `context_for`.
*   **Decision or document touched:** `prompts/P007_phase_2_segments_embeddings.md` (Docs section).
*   **Proposed doc / schema / prompt delta:** Document that V1 accepts this coarse provenance, trading token efficiency for schema simplicity.
*   **Minimal experiment or inspection that would disprove the concern:** Verify if the LLM can reliably extract and cite a specific 3-sentence claim from a 10,000-word raw message without character-level spans.
*   **Cost of being wrong if Phase 2 ships unchanged:** Context windows will fill up quickly with entire long notes instead of precise spans, leading to token waste and potential context eviction.

### Finding 2.2: Duplicate Text Vector Domination
*   **Description:** `embedding_cache` deduplicates vectors for identical text. If the same 5-word greeting is segmented 1,000 times, a cache KNN search will return 1 row that joins to 1,000 segments, instantly filling the context limit with duplicates.
*   **Decision or document touched:** `docs/design/V1_ARCHITECTURE_DRAFT.md` (Context_For Shape/Ranking).
*   **Proposed doc / schema / prompt delta:** Document that the candidate ranking formula must deduplicate by text/topic or the vector query must group by unique content.
*   **Minimal experiment or inspection that would disprove the concern:** Run semantic search on a dataset containing 1,000 identical "Hello, how can I help you?" segments.
*   **Cost of being wrong if Phase 2 ships unchanged:** Meaningful semantic retrieval will be crowded out by duplicate conversational filler.

## 3. Defer

### Finding 3.1: Unified Vector Index
*   **Description:** Searching segments and beliefs via separate HNSW queries is acceptable for V1. Unifying them into a single polymorphic index or inheritance table can be deferred.
*   **Decision or document touched:** `docs/design/V1_ARCHITECTURE_DRAFT.md`
*   **Proposed doc / schema / prompt delta:** N/A (Deferred)
*   **Minimal experiment or inspection that would disprove the concern:** Measure query latency and recall differences between two separate HNSW indexes vs. one unified index on the same dataset.
*   **Cost of being wrong if Phase 2 ships unchanged:** Minor performance/latency overhead that can be optimized in V2 without schema breakage.

### Finding 3.2: Character-level Span Tracking
*   **Description:** Tracking exact start/end offsets (`source_spans JSONB`) within raw sources can be deferred until specific eval failures prove the coarse `message_id` provenance is actively degrading context quality.
*   **Decision or document touched:** `prompts/P007_phase_2_segments_embeddings.md`
*   **Proposed doc / schema / prompt delta:** N/A (Deferred)
*   **Minimal experiment or inspection that would disprove the concern:** Eval testing showing unacceptable token waste or loss of context resolution due to whole-message provenance.
*   **Cost of being wrong if Phase 2 ships unchanged:** Context window inefficiency in V1, which is an accepted tradeoff for simplicity.

## 7. Explicit proceed / do-not-proceed recommendation

**PROCEED WITH DELTAS**

The current specification for the vector index (`embedding_cache` JOIN `segments` filtered by `superseded_by`) fundamentally misunderstood how pgvector executes HNSW scans. If implemented as initially written, the vector search would silently degrade as re-segmentations occur, eventually returning zero valid results for highly-superseded topics. The N-to-M supersession mapping was also structurally impossible with the initial column definitions. With the schema deltas outlined above applied to the canonical documents and Phase 2 prompt, the project is clear to proceed to Phase 2 coding.
