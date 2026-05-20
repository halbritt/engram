# RFC 0056 Adversarial Design Review — Gemini

## Verdict
reject-revise-major

## Findings

### BLOCKER: Missing Privacy Tier in Audit Schema
**Location:** Section `Schema` and `Open Questions` (Item 4)
**Problem:** The RFC acknowledges in Open Question 4 that the agent reads source claims with potentially higher privacy tiers and proposes mirroring the `query_privacy_tier` carry rule. However, the proposed `entity_grounding_triage_actions` SQL schema lacks a `privacy_tier` column completely. 
**Evidence:** In Engram's append-only architecture, any derived data must carry a privacy tier. Without this column, triage actions derived from tier-3 (secret) sources will default to the standard connection visibility. If a tier-3 claim's details leak into the `rationale` or influence a dedupe pointer, lower-tier UI views querying the triage table will expose high-tier metadata.
**Proposed fix:** Add `privacy_tier TEXT NOT NULL` to the `entity_grounding_triage_actions` table schema. Update the "Local Context Capsule" section to mandate calculating the `max()` of all input source claim tiers, and update the Acceptance Criteria to explicitly test this boundary.

### BLOCKER: Verbatim-Only Privacy Filter Permits Paraphrase Leaks
**Location:** Section `Decision Schema`
**Problem:** The RFC states: "If `rationale` contains a verbatim segment of object text, the decision is downgraded to `needs_review`".
**Evidence:** LLMs frequently paraphrase or summarize input text. A verbatim match filter will miss cases where the model writes "The user's password is roughly X..." instead of quoting X exactly. Because the capsule contains private summaries, allowing free-text `rationale` generation creates an unmitigated exfiltration path into the audit logs.
**Proposed fix:** Drop the free-text `rationale` field from the LLM schema entirely. Replace it with a fixed `reason_code` Enum (e.g., `["personal_artifact", "segmentation_noise", "too_broad"]`).

### MAJOR: UUID Hallucination and Foreign Key Crashes
**Location:** Section `Decision Schema`
**Problem:** The schema requires `dedupe_target_entity_id: "uuid | null"` for `dedupe_of` decisions. The RFC provides no validation layer to ensure the LLM-generated UUID actually belongs to the "sibling entity surfaces" provided in the capsule.
**Evidence:** LLMs are notoriously bad at emitting exact UUIDs. If the model hallucinates a UUID, drops a character, or invents an ID not in the capsule, the insert into `entity_grounding_triage_actions` will trigger a PostgreSQL `REFERENCES entities(id)` foreign key violation, crashing the batch worker. Worse, if it hallucinates an ID that *does* exist but wasn't in the capsule, it will silently attribute the dedupe incorrectly.
**Proposed fix:** The agent must strictly validate that `dedupe_target_entity_id` is a member of the capsule's provided sibling IDs. If it is not, the action must be gracefully downgraded to `needs_review` with reason `agent_hallucinated_uuid`.

### MAJOR: Capsule Hash Invalidation Defeats Operator Override
**Location:** Section `Idempotency`
**Problem:** The RFC states the model is called when "the capsule hash changed (entity was rebuilt with new source claims)". It also states the draft worker uses "the latest non-superseded triage action" and that "The agent never overrides an `agent_version = "operator"` action".
**Evidence:** In an append-only system, if an operator writes an override action, it becomes the latest action. If a new source claim is subsequently attached to the entity, the capsule hash changes. On the next run, the agent will see the new capsule hash, evaluate the LLM, and append a *new* action row. This new row becomes the "latest", silently ignoring the operator's prior override.
**Proposed fix:** Change the idempotency logic: if the most recent action for an entity has `agent_version = 'operator'`, the agent must skip evaluation entirely and preserve the operator's decision, regardless of `capsule_hash` drift, unless an explicit `--ignore-overrides` flag is passed.

### MINOR: Target Entity Lifecycle Race Condition
**Location:** Section `Workflow Integration`
**Problem:** Step 3 states: "attribute the draft to `dedupe_target_entity_id` if it has no active draft/grant".
**Evidence:** Between the time the triage agent runs and the draft worker acts, Phase 4 entity resolution might have merged or superseded the `dedupe_target_entity_id`. The draft worker will attempt to attach a draft to a dead entity.
**Proposed fix:** The draft worker must recursively resolve `superseded_by` pointers on the `dedupe_target_entity_id` before attributing the draft, or drop the dedupe attribution if the target is no longer active.

### MINOR: Serving Contention on Single GPU
**Location:** Section `Local Model Choice`
**Problem:** The RFC dismisses serving contention as a "serving-layer concern", expecting to reuse the pinned extractor model.
**Evidence:** If Phase 4 extraction (high token generation) and pre-dispatch triage (high prompt evaluation) execute concurrently against a single local `ik-llama` instance, they will continuously evict each other's KV caches, drastically reducing throughput for the entire pipeline.
**Proposed fix:** Acknowledge this contention explicitly. Implement a worker-side concurrency lock or enforce that the batch pipeline strictly sequences Phase 4 extraction completion *before* Triage begins.

### NIT: Schema Float Strictness 
**Location:** Section `Decision Schema`
**Problem:** The JSON schema specifies `confidence` as `0.0` (implied Float).
**Evidence:** OpenAI-compatible strict JSON schema parsing frequently fails when local models output `1` or `0` instead of `1.0` or `0.0`.
**Proposed fix:** Specify `type: number` rather than strict float format, and handle cast-to-float gracefully in the Python client.

## Alternative-Design Notes

*   **Rule-Based Pre-filter:** Using an LLM to detect `"Local Grocery Shopping List X"` is expensive. A cheaper, deterministic alternative is to stage a rule-based filter *before* the LLM. Length thresholds, regex for stop-words (e.g., "shopping list", "my "), and exact Levenshtein similarity to existing entities would capture 80% of the noise at 0% of the inference cost, reserving the LLM only for edge cases.
*   **Defer Deduplication to Phase 4:** Asking a triage agent to emit `dedupe_target_entity_id` splits entity resolution logic between the core Phase 4 engine and an LLM pre-filter. A cleaner architecture would restrict the triage agent strictly to `groundable` vs `not_groundable`, and enhance Phase 4's `entity_resolution_events` to handle the duplicate detection using its existing graph.

## Acceptance-Criteria Gaps

*   No acceptance criteria for migrating or testing the `privacy_tier` inheritance. A test must prove that a tier-3 source claim produces a tier-3 triage action.
*   No acceptance criteria validating that `dedupe_target_entity_id` hallucination is caught and correctly downgraded to `needs_review` rather than crashing the worker.
*   No acceptance criteria proving that an operator override (`--supersede`) survives a subsequent change to the entity's `capsule_hash`.
*   No acceptance criteria verifying the `no_egress` test actually blocks outbound requests from the LLM client (the AC only says it "covers the triage entrypoint", it must explicitly assert network partition).
