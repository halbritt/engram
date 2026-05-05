# RFC 0005: Supervisor Event Triggers and Queue Prioritization
Status: proposal
Date: 2026-05-02
Context: Augments RFC 0001 (Supervisor Controller Loop)

This RFC augments the supervisor controller pattern proposed in RFC 0001. It resolves specific computational and operational bottlenecks regarding semantic observation, re-derivation prioritization, and context state thrashing. 

## 1. Vector-Grounded Observers (Resolving Semantic Drift Detection)

RFC 0001 introduces the concept of "observers" to detect when desired state shifts independently of system actions (e.g., semantic tension emerging between previously independent beliefs). 

**The Flaw:** Continuous, passive observation of semantic drift is computationally intractable. A deterministic loop cannot magically detect tension without forcing an LLM to re-evaluate the entire graph against every new piece of evidence.

**The Augmentation:** Observers must be structurally tethered to vector proximity triggers rather than unbounded polling. 
* Semantic drift detection becomes a triggered derivation step within the supervisor loop.
* When new raw evidence is ingested and embedded into `segment_embeddings`, the system executes an immediate `pgvector` nearest-neighbor (HNSW) scan against the existing belief index.
* Only if a high-similarity match surpasses a defined distance threshold does the supervisor queue an LLM worker to evaluate for tension, contradiction, or reinforcement.

## 2. Stability-Class Priority Heuristic (Resolving Re-derivation Queues)

RFC 0001 notes the risk of wasting compute by re-embedding archival material after a model bump, suggesting a "recent-and-active" priority signal.

**The Flaw:** Naive recency violates the bitemporal validity established in D004. An `identity` belief extracted five years ago is structurally more critical to context rendering than a highly recent `task` preference. 

**The Augmentation:** The supervisor's reconciliation queue must natively integrate the `stability_class` enum defined in D008. 
* Re-derivation queues resulting from prompt or model version bumps sort strictly by stability classification before recency.
* **Sort Order:** `identity` > `relationship` > `preference` > `goal` > `project_status` > `mood` > `task`.
* This guarantees that fundamental, long-lived canonical context is restored first when compute is constrained, while ephemeral signals fall to the background or maintenance tier.

## 3. Debounced and JIT Context Snapshotting (Resolving State Thrashing)

RFC 0001 proposes immediate snapshot refreshes when a newly ingested conversation contradicts a high-confidence belief.

**The Flaw:** During rapid, multi-turn AI interactions (e.g., active coding sessions or long design prompts), the supervisor will continuously trigger context snapshot refreshes after every individual ingestion. This causes state thrashing, burning local GPU cycles on intermediate, ephemeral conversational states before the user's thought is complete.

**The Augmentation:** The supervisor must implement a Debounce and Just-In-Time (JIT) refresh architecture for context snapshots.
* **Dirty Flags:** When underlying beliefs or segments change, the affected context snapshot is marked `is_dirty = true` but is *not* immediately regenerated.
* **Debounce Window:** The supervisor enforces a configurable idle debounce window (e.g., 5 minutes since the last related ingestion event) before initiating a background refresh.
* **JIT Execution:** If a consumer scope explicitly requests `context_for` a conversation while the snapshot is flagged `dirty` and within the debounce window, the supervisor bypasses the wait, executes a synchronous hot compile, serves it, and clears the flag. 

## Consequences

* **Compute Efficiency:** Vector-grounded triggers and JIT snapshotting mathematically bound the amount of local LLM inference required, preventing runaway queue inflation.
* **Schema Additions:** Requires an `is_dirty` boolean and `last_ingest_timestamp` on the context snapshot materialization layer.
* **Reversibility:** High. These are scheduling and queue-sorting optimizations that sit entirely within the supervisor logic and do not mutate raw evidence schemas.
