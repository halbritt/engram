# RFC 0056 Adversarial Design Review — adversarial-reviewer-01

## Verdict
reject-revise-major

## Findings

### BLOCKER: Privacy Tier Inheritance Violation
**Location:** Local Context Capsule / Open Questions #4
**Problem:** The RFC proposes reading source claims to build the context capsule. Source claims often have higher privacy tiers (more sensitive) than the entity row itself. The RFC states in Open Question #4 that the triage action should "inherit the maximum source tier," but the **Local Context Capsule** section explicitly allows including raw object values if they are "short (`<=` 80 chars)" and "already public-tier." This creates a contradiction: if the source claim is Tier 2 (Private) but the object value is short, the RFC implies it might be included if the *entity* is public, or it creates ambiguity about whether the *source* tier protects the object. More critically, the capsule is passed to an LLM. If the capsule contains any data from a higher-tier source claim, the LLM (even if local) is processing data it is not authorized to see based on the entity's lower tier. The RFC fails to enforce that the **capsule assembly** must filter out any data from source claims with `tier > entity.tier`, regardless of the data's own metadata.
**Evidence:** The "Local Context Capsule" section says: "raw object values are not included unless they are already public-tier and short". This logic checks the *object's* tier, not the *source claim's* tier. If a Tier 2 claim links to a Tier 1 public URL, the URL is public, but the *link* is private. Including it in the capsule leaks the existence of the private link.
**Proposed fix:** Explicitly state in the "Local Context Capsule" section: "The capsule must exclude any data derived from source claims where `source_claim.privacy_tier > entity.privacy_tier`. The capsule assembly must enforce this filter before constructing the JSON."

### BLOCKER: Idempotency Key Collision via Capsule Hash
**Location:** Idempotency / Schema
**Problem:** The idempotency key is `capsule_hash + model_id + prompt_version`. The `capsule_hash` is derived from the capsule content. The capsule includes "A bounded list of sibling entity surfaces — other active entities sharing any source claim id". If the set of sibling entities changes (e.g., a new entity is created that shares a source claim, or an existing entity is merged/superseded), the capsule content changes, invalidating the hash. This forces a re-triage. However, the RFC does not specify how the system handles the *previous* triage action when the capsule changes. If the previous action was `groundable` and the new capsule (with different siblings) results in `not_groundable`, the draft worker sees the *new* action. But if the draft was already created based on the *old* action, there is a race condition or state inconsistency. More importantly, the `capsule_hash` is not stable across re-runs if the "bounded list" order is non-deterministic (e.g., SQL `ORDER BY` without a stable tie-breaker).
**Evidence:** The schema has `superseded_at`. The workflow says "Read the latest non-superseded triage action". If the capsule changes, the old action is not superseded by the new one automatically; it's just "older". The RFC implies that a new action is created, but doesn't specify if the old one is superseded. If not, the "latest" logic might pick the wrong one if timestamps are close. If yes, the mechanism for superseding based on capsule change is missing.
**Proposed fix:** Define the capsule assembly to have a deterministic sort order for all lists (e.g., `ORDER BY id`). Explicitly state that a new triage action *supersedes* the previous one if the capsule hash changes. Add a check in the draft worker: if the entity's capsule hash has changed since the triage action was created, force a re-triage or invalidate the draft.

### BLOCKER: Dedupe Logic Circular Dependency
**Location:** Local Context Capsule / Decision Schema
**Problem:** The triage agent decides `dedupe_of` based on "sibling entity surfaces". However, the dedupe decision is advisory ("Dedupe pointers are advisory; merge/supersede decisions remain in... Phase 4 logic"). If the triage agent says "Entity A is a duplicate of Entity B", but Entity B is *also* being triaged in the same batch and is marked `not_groundable` or `dedupe_of` Entity C, the triage agent for Entity A has no visibility into the *final* state of Entity B. It only sees the "active entities" at the time of capsule assembly. This leads to inconsistent dedupe chains (A -> B, B -> C, but A is drafted because B was suppressed).
**Evidence:** The capsule includes "other active entities". It does not include the *triage decisions* of those entities. The triage step runs *before* the draft step, but the triage step for different entities might run concurrently or in an undefined order.
**Proposed fix:** The triage agent must not make `dedupe_of` decisions based solely on static entity data. It should either: 1) Defer dedupe decisions to a post-triage, pre-draft phase that has visibility into all triage decisions, or 2) Only flag potential duplicates for operator review (`needs_review`) if the target entity's triage status is unknown.

### MAJOR: Model Serving Contention and Latency
**Location:** Local Model Choice / Evaluation
**Problem:** The RFC proposes reusing the `IkLlamaExtractorClient` for triage. The extractor is used for claim extraction, which is likely a high-throughput, latency-sensitive operation. Adding triage (which requires a full LLM call per entity) to the same serving path will cause significant contention. The RFC mentions "serving-contention failure mode" in the review focus but dismisses it as a "serving-layer concern". This is a critical design flaw. If the extractor is busy, triage fails or times out, blocking the entire grounding workflow.
**Evidence:** The RFC states: "If extraction and triage workloads contend on the same ik-llama backend, that is a serving-layer concern". This is not a concern; it's a bottleneck. The RFC does not specify any queuing, prioritization, or isolation mechanism.
**Proposed fix:** Specify that the triage agent must use a separate model instance or a separate queue within the local LLM server. Or, explicitly state that triage is a low-priority background task that does not block the extractor.

### MAJOR: "Needs Review" Path is a Dead End
**Location:** Decision Schema / Workflow Integration
**Problem:** The `needs_review` decision holds the entity out of the draft queue. The RFC says it is "surfaced in the operator UI for manual triage". However, the RFC does not specify *how* the operator interacts with this. Does the operator click a button to re-triage? To force ground? To force not-ground? The CLI has `--supersede`, but that requires knowing the entity ID and running a command. The UI is not specified. If the operator cannot easily resolve `needs_review` items, they will accumulate, blocking the workflow.
**Evidence:** The CLI only has `--supersede --entity-id UUID`. This is not ergonomic for an operator reviewing a list of `needs_review` items.
**Proposed fix:** Define the UI interaction for `needs_review` items. At minimum, the UI must allow the operator to select multiple `needs_review` entities and apply a batch decision (e.g., "Force Ground", "Force Not Ground").

### MAJOR: Capsule Size Limit is Arbitrary and Fragile
**Location:** Local Context Capsule
**Problem:** The capsule is capped at 4 KiB JSON. This is a hard limit. If an entity has many source claims or siblings, the capsule will be truncated. The RFC does not specify *which* claims/siblings are kept. This introduces non-determinism and potential bias in the triage decision.
**Evidence:** "At most 6 source claim summaries... At most 6 sibling entity surfaces". No priority is defined.
**Proposed fix:** Define a deterministic priority for including claims/siblings (e.g., highest confidence first, or most recent first). Document this priority in the RFC.

### MINOR: Rationale Text Length Limit
**Location:** Decision Schema
**Problem:** `rationale` is limited to 280 chars. This is insufficient for explaining complex dedupe or not-groundable decisions, especially when multiple factors are involved.
**Evidence:** "rationale": "<= 280 chars".
**Proposed fix:** Increase the limit to 1000 chars or remove the limit, relying on the "no quoted private text" constraint for safety.

### MINOR: No Egress Test Surface
**Location:** Boundary
**Problem:** The RFC mentions a `no_egress` smoke test. It does not specify how this test is implemented. Is it a network monitor? A static analysis of imports? Static analysis is insufficient (dynamic calls can bypass imports). Network monitoring is fragile (localhost traffic might be missed).
**Evidence:** "A `no_egress` smoke test should cover the triage entrypoint."
**Proposed fix:** Specify that the test must use a network-level block (e.g., iptables/firewall rule) on the test environment to ensure no outbound connections are made, in addition to import checks.

### NIT: Typo in Model ID
**Location:** Local Model Choice
**Problem:** `Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` has a redundant "Qwen_".
**Evidence:** `~/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf`
**Proposed fix:** Correct to `Qwen3.6-35B-A3B-IQ4_XS.gguf` or verify the actual filename.

### NIT: CLI Output Ambiguity
**Location:** CLI
**Problem:** The CLI output includes `decisions: {groundable: N, ...}`. It does not specify if this is a count of *actions created* or *actions reused*. The RFC mentions `actions_reused` separately, but the breakdown is ambiguous.
**Evidence:** `decisions: {groundable: N, not_groundable: N, dedupe_of: N, needs_review: N, skip: N}`
**Proposed fix:** Clarify that these counts refer to the *new* actions created in this run, not the total active actions.

## Alternative-Design Notes

1.  **Rule-Based Pre-Filter:** Before the LLM triage, implement a lightweight rule-based filter (length < 5 chars, stop-list, exact string match against existing entities). This would reduce the number of LLM calls by 50-80%, mitigating the serving contention issue. The LLM should only handle ambiguous cases.
2.  **Batch Triage:** Instead of one LLM call per entity, batch 10-20 entities into a single LLM call with a structured output format. This reduces latency and cost (if using paid models later) and allows the model to compare entities against each other for dedupe detection more effectively.
3.  **Separate Triage Model:** Use a smaller, dedicated model for triage (e.g., Hermes 3 8B) on a separate GPU or queue. This isolates the triage workload from the extractor workload, preventing contention.

## Acceptance-Criteria Gaps

-   **Deterministic Capsule Assembly:** No acceptance criterion ensures that the capsule assembly is deterministic (sorted lists, consistent truncation).
-   **Dedupe Chain Resolution:** No acceptance criterion for how dedupe chains are resolved when multiple entities are triaged in the same batch.
-   **Operator UI for `needs_review`:** No acceptance criterion for the UI interaction to resolve `needs_review` items.
-   **Capsule Priority Logic:** No acceptance criterion for which source claims/siblings are included when the capsule is truncated.
-   **Idempotency Superseding:** No acceptance criterion for how old triage actions are superseded when the capsule changes.