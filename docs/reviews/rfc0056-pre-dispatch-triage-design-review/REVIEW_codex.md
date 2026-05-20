# RFC 0056 Adversarial Design Review — GPT-5 Codex

## Verdict
reject-revise-major

## Findings

### BLOCKER: Privacy tier inheritance is non-normative and missing from schema
**Location:** Open Questions: “Privacy tier inheritance… Proposal: yes”
**Problem:** The RFC admits source claims may be higher-tier than the entity, but the table has no `privacy_tier`, `capsule_privacy_tier`, or visibility rule for rationale/review UI.
**Evidence:** The action row persists `rationale`, `decision`, and `dedupe_target_entity_id` derived from higher-tier claims. Without tier carry, high-tier context can be down-tiered into a lower-tier audit/review surface.
**Proposed fix:** Move privacy inheritance out of Open Questions into Boundary/Schema. Add `privacy_tier NOT NULL`, computed as max of entity, source claims, sibling entities, and evidence rows. Gate CLI/UI display and tests on that tier.

### BLOCKER: Dedupe attribution can bypass the target entity’s own grounding gate
**Location:** Workflow Integration step 3: “For `dedupe_of`, attribute the draft to `dedupe_target_entity_id`…”
**Problem:** A duplicate candidate can cause drafting/search for another entity even if the target has no triage action, has a suppressing action, is higher-tier, or is superseded.
**Evidence:** The schema only requires a FK. It does not enforce same tenant/corpus, target active status, non-self, no cycles, target privacy, or target `groundable`.
**Proposed fix:** Require `dedupe_target_entity_id` to be active, same tenant/corpus, non-self, non-superseded, and latest-target-triage=`groundable`; otherwise emit `needs_review` and never draft through the pointer.

### BLOCKER: The no-egress boundary is asserted, not made testable
**Location:** Boundary: “A `no_egress` smoke test should cover the triage entrypoint.”
**Problem:** A smoke test is too weak for the hard local-first constraint. The RFC does not require socket blocking, HTTP client interception, import graph checks, or refusal before client construction.
**Evidence:** The triage code will construct an OpenAI-compatible client and read corpus context. A misplaced base URL, proxy env var, accidental network import, or delayed broker-DSN check can leak data before a “smoke” assertion notices.
**Proposed fix:** Require tests that monkeypatch/block all non-loopback sockets, assert no network-adapter imports, assert broker DSN refusal happens before DB/model construction, ignore proxy env vars, and reject non-local `ENGRAM_DATABASE_URL` if remote DBs are not explicitly allowed.

### MAJOR: The JSON “schema” is not a real robust schema
**Location:** Decision Schema JSON block
**Problem:** The RFC shows an example object, not an enforceable JSON Schema. It does not specify `enum`, `maxLength`, `additionalProperties: false`, conditional `dedupe_target_entity_id`, nullable encoding, or schema version.
**Evidence:** Strict model output only helps if the schema is precise. Current wording allows extra fields, invalid confidence forms, rationale overflow, and `dedupe_of` with a malformed target until application code catches it.
**Proposed fix:** Include the actual JSON Schema in the RFC with `oneOf`/conditionals, `reason_code` enum, `schema_version`, no additional properties, and explicit rejection/downgrade behavior.

### MAJOR: Decisions are not mutually exclusive and lack precedence
**Location:** Decision Schema bullets
**Problem:** A surface can be both duplicate and not groundable, duplicate and groundable, already grounded, or insufficient-context-but-probably-groundable. The RFC does not define precedence.
**Evidence:** Noise duplicates, private artifacts with duplicate rows, and entities with existing approved grants are expected cases in this workflow.
**Proposed fix:** Add a decision precedence order and explicit cases: existing approved grant, already drafted, duplicate target invalid, private-but-public-name, malformed capsule, and model refusal.

### MAJOR: Idempotency is under-specified and race-prone
**Location:** Idempotency: “capsule hash + model id + prompt version”
**Problem:** The key is not enforced by a unique index and omits schema version, agent code version, context-builder version, model digest, generation parameters, and privacy policy version.
**Evidence:** Two concurrent runs can insert two active rows. Also, the RFC says model calls happen when prompt changes, but omits model-id changes despite naming model id as part of the key.
**Proposed fix:** Add a partial unique index over active `(tenant_id, corpus_id, entity_id, capsule_hash, model_id, prompt_version, schema_version)`, canonicalize capsule hashing, include model digest/params, and list every invalidation event.

### MAJOR: Operator override is not implementable from the CLI shown
**Location:** CLI: `--supersede --entity-id UUID`
**Problem:** The operator cannot specify the replacement decision, dedupe target, rationale, reason code, or actor. The RFC also does not define which active actions get `superseded_at`.
**Evidence:** “writes a new action with `agent_version = "operator"`” is impossible to audit safely without actor and reason, and races with a concurrent agent run.
**Proposed fix:** Add `--decision`, `--dedupe-target-entity-id`, `--reason`, `--actor`, `--force-rerun`, row locking, and “operator action wins” constraints at insert time.

### MAJOR: Default model choice ignores throughput and serving contention
**Location:** Local Model Choice
**Problem:** Reusing the 35B extractor model makes triage hundreds of local chat calls on the same backend as extraction. At 281+ entities, this becomes a scheduler/capacity problem, not a small classifier.
**Evidence:** The CLI default `--limit 50` creates partial triage batches; when `ENGRAM_TRIAGE_REQUIRED=1`, untriaged remaining entities silently block or disappear from draft eligibility. Contention with extraction is dismissed as “serving-layer concern.”
**Proposed fix:** Specify queue ordering, pagination/resume semantics, timeout/retry policy, max concurrency, backend lock/health behavior, and a load eval at 300/1000 candidates before default-on.

### MAJOR: Alternative model names overpromise structured-output compatibility
**Location:** “Hermes 3 8B… Llama 3.2 3B or Qwen 2.5 7B via Ollama”
**Problem:** The RFC assumes these models and serving paths support OpenAI-compatible strict JSON Schema equivalently.
**Evidence:** Ollama JSON mode, function calling, and OpenAI `response_format.json_schema strict` are not interchangeable operational contracts.
**Proposed fix:** Treat non-default models as unsupported until a compatibility test proves strict schema adherence, refusal handling, and calibration against labels.

### MAJOR: Evaluation gate is too weak for a suppressive default-on feature
**Location:** Evaluation
**Problem:** “50–100 entities” and “net-positive precision” are insufficient to justify suppressing draft candidates by default.
**Evidence:** A bad classifier can look net-positive by suppressing many obvious bad rows while silently hiding rare but important real entities. The proposed metric does not set false-suppression ceilings.
**Proposed fix:** Require per-class thresholds, especially recall for `groundable`; adversarial privacy cases; duplicate-target correctness; holdout data; confidence calibration; runtime/no-egress results; and operator override tracking before default-on.

### MINOR: The context capsule still allows sensitive short strings
**Location:** Local Context Capsule: “raw object values… public-tier and short (`<=` 80 chars)”
**Problem:** Short public-tier strings can still be secrets, names, addresses, or sensitive identifiers if tiering is wrong or stale.
**Evidence:** The RFC’s own purpose is to use local context that should not reach external search. Rationale filtering only checks quoted object text, not entity text, sibling surfaces, predicates, or evidence labels.
**Proposed fix:** Prefer no raw object values in the model capsule. If retained, scan rationale against every protected capsule string and persist only reason codes plus minimal rationale.

### MINOR: Dry-run is called the debugging path but hides the useful data
**Location:** CLI and Observability
**Problem:** `--dry-run` prints only aggregate sanitized JSON while Observability says it is the primary debugging path.
**Evidence:** Operators cannot inspect which entity was classified, why it was reused, which capsule hash changed, or why a schema downgrade happened.
**Proposed fix:** Add a redacted JSONL mode with entity id, decision, reason code, confidence, capsule hash, reused/new, elapsed time, and privacy tier; keep rationale behind tier-aware review UI.

### MINOR: Review UI requirements are absent
**Location:** CLI / Acceptance Criteria
**Problem:** The RFC says operators read rationale through “a separate review view” but never specifies it.
**Evidence:** `needs_review`, dedupe validation, contradiction with approved grants, and operator override all require human review surfaces.
**Proposed fix:** Specify UI fields: candidate surface, source claim refs, privacy tier, decision history, rationale/reason code, dedupe target comparison, existing grants/evidence, override controls, and audit actor.

### NIT: Editorial and naming clarity
**Location:** Multiple
**Problem:** “four decisions” conflicts with persisted `skip`; “mirroring how `broker-daemon` refuses without it” is confusing because triage refuses with it; “net-positive precision” is not standard metric language; model ids like `Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` should be verified/pinned exactly.
**Evidence:** These are small wording problems, but they will become implementation ambiguity.
**Proposed fix:** Clean up terminology, distinguish LLM decisions from system decisions, and use exact model artifact identifiers plus digest.

## Alternative-Design Notes
A deterministic pre-filter should run before any LLM call: canonical-text normalization, exact duplicate detection by tenant/corpus/entity kind, self/target validity checks, length thresholds, punctuation/UUID/list-title noise detection, existing grant/evidence checks, and stop-list handling. The LLM should only receive uncertain cases after the rule layer.

A safer rollout is three-stage: rules-only dry run, LLM shadow mode that never suppresses draft, then opt-in enforcement after eval thresholds and operator review are met. This preserves review effort while proving the classifier does not hide good entities.

Consider storing only structured reason codes by default and making free-text rationale optional, tiered, and redacted. The audit row should be replayable without becoming a new privacy leak.

## Acceptance-Criteria Gaps
- Add `privacy_tier` or `capsule_privacy_tier` to the migration and test max-tier inheritance.
- Add same-tenant/corpus, active-target, non-self, no-cycle, and target-`groundable` checks for `dedupe_of`.
- Add a real JSON Schema fixture and tests for extra fields, invalid enum values, bad UUIDs, overlong rationale, and conditional target requirements.
- Add a partial unique index or transaction test preventing duplicate active actions under concurrent triage runs.
- Test idempotency invalidation for model id, model digest, prompt version, schema version, context-builder version, source-claim changes, evidence changes, and privacy-tier changes.
- Test model unavailable, timeout, malformed output, and strict-schema unsupported backend behavior.
- Test no-egress with socket blocking, proxy env vars, non-loopback model URL, network-adapter import failure, and broker-DSN refusal before client construction.
- Add CLI acceptance for manual override decision, dedupe target, actor, reason, force rerun, and redacted per-entity dry-run output.
- Add review UI acceptance criteria for `needs_review`, dedupe comparison, contradictions with approved grants, and tier-aware rationale visibility.
- Add eval thresholds for false suppression of `groundable`, duplicate-target correctness, privacy leakage, runtime at 281+ entities, and default-on promotion.
