# Phase 3 Claims and Beliefs Spec Review (Gemini Pro 3.1)

**Summary Verdict:** `accept_with_findings`

The specification provides a strong, local-first foundation for extracting and consolidating bitemporal beliefs. However, it contains critical flaws in its bitemporal time semantics and its handling of active claim lifecycles during re-extraction. These must be addressed to preserve historical queryability and consistency.

## Findings

### 1. [P0] `valid_to` Conflates Transaction Time and Valid Time
* **Affected Section:** `Time semantics` and `Stage B — Belief consolidation` -> `Decision rules` (Contradiction).
* **Issue:** The bitemporal design defines `valid_from` as valid-time ("the interval the belief asserts as true") but uses `valid_to = now()` for supersession, which is transaction-time. If a contradiction occurs (e.g., new evidence from 2020 arrives in 2026), the old belief gets `valid_to = 2026` and the new belief gets `valid_from = 2020`.
* **Consequence:** The validity intervals will overlap (2020 to 2026), meaning the temporal ordering auto-resolution rule will fail, and true "as-of" bitemporal historical queries will be broken.
* **Proposed Fix:** Separate valid-time from transaction-time. Supersession should be tracked via `status = 'superseded'` and `superseded_by` (or a new `superseded_at` column), not by modifying `valid_to`. `valid_to` should STRICTLY represent the end of the fact's validity in the real world. On a contradiction, the old belief's `valid_to` should be set to the `MIN(messages.created_at)` of the contradicting evidence, not `now()`.

### 2. [P0] Missing Consolidation Rule for Orphaned Beliefs
* **Affected Section:** `Stage B — Belief consolidation (deterministic Python)` -> `Decision rules`
* **Issue:** The decision rules specify behavior when an active claim matches or contradicts an existing belief. There is no rule for an existing active belief whose supporting claims vanish from the active set entirely (e.g., due to a new, empty extraction for the parent segment, or a prompt version bump that no longer emits the claim). The consolidator only loops over "active claims".
* **Consequence:** Orphaned beliefs will remain active indefinitely, breaking the foundational rule that active beliefs must be backed by active evidence.
* **Proposed Fix:** Add a Decision Rule 0: Before processing the active claims for a conversation, the consolidator must identify all active beliefs for that conversation whose `claim_ids` are no longer fully present in the active claim set. These must be closed via close-and-insert or rejected.

### 3. [P1] "Same Value" Close-and-Insert Destroys Valid-Time History
* **Affected Section:** `Stage B — Belief consolidation` -> `Decision rules` (Existing belief, same value).
* **Issue:** When a same-value claim arrives, the spec dictates closing the prior row (`valid_to = now()`) and inserting a new one. As in Finding 1, using `valid_to = now()` implies the fact ended today.
* **Consequence:** A fact that has been true since 2018 will be fragmented into dozens of artificial intervals bounded by `now()`, destroying the continuity of the valid-time history.
* **Proposed Fix:** When executing a "same value" close-and-insert to comply with raw immutability (P4), the old row should be closed via `status = 'superseded'` and `superseded_by`, but its `valid_to` must REMAIN UNCHANGED (e.g., `NULL`). The new row inherits the `valid_from` and `valid_to` of the fact it represents.

### 4. [P2] Empty Extractions Discard Auditable Model Output
* **Affected Section:** `Stage A — Claim extraction` -> `Per-segment lifecycle`
* **Issue:** The spec states that empty extractions produce "zero claims rows. No failure diagnostics are written."
* **Consequence:** If a model emits an empty extraction due to prompt misalignment or refusal (but returns a valid empty JSON array), the `raw_payload` is lost. Debugging recall failures becomes impossible.
* **Proposed Fix:** `claim_extractions.raw_payload` should store the raw LLM output (including `reasoning_content` if available) on ALL extractions, not just failures.

### 5. [P3] Tool Message Placeholders Blind the Extractor
* **Affected Section:** `Extractor prompt construction`
* **Issue:** The extractor replaces tool message bodies with placeholders (D038), blinding it to the actual contents of artifacts or tool outputs.
* **Consequence:** High recall loss for predicates like `uses_tool`, `working_on`, and `project_status_is`, which often depend entirely on the contents of those artifacts.
* **Proposed Fix:** Note this limitation clearly. Consider allowing the extractor to request artifact resolution or defining artifact extraction as a separate future stage.

## Open Questions for the Owner

1. **`valid_from` derivation (OQ2):** The use of `MIN(messages.created_at)` vs `MAX(messages.created_at)`. `MIN` accurately captures the start of the valid-time interval. However, if evidence is discovered late, the bitemporal model needs to know when we *learned* it vs when it *happened*. Ensure the schema distinction between `observed_at` and `valid_from` satisfies your requirements for historical state queries.
2. **Auto-resolution Scope (OQ4):** Is temporal ordering sufficient for Phase 3? If identity beliefs arrive out of order, they might incorrectly auto-resolve based on a late-arriving old message.

## Test or Acceptance-Criteria Gaps

*   **Missing Case Test:** There is no acceptance criterion verifying that when a segment is re-extracted and produces *fewer* claims than before, the downstream beliefs previously supported by the dropped claims are properly superseded/rejected.
*   **Bitemporal Ordering Test:** There is no test verifying that late-arriving historical evidence correctly orders intervals without causing invalid overlaps due to `valid_to` logic.

## Contradictions with RFC 0011

*   **Consolidator Parallelism:** RFC 0011 OQ8 asked if consolidation could run per-conversation. The spec mandates a per-conversation pipeline. However, the spec states that cross-conversation group keys are handled by joining globally. This implies that parallel consolidators working on different conversations could hit race conditions when trying to close-and-insert the *same* global belief simultaneously. The spec should intentionally supersede RFC 0011 by requiring lock-based concurrency control on the group key, or enforcing sequential consolidation.
