# Engram Grounding Stack — Architectural Review by Architect-01

## Verdict
**continue-with-revisions**

The stack is architecturally sound but operationally broken. The 0% resolution rate against 281 entities proves that the current "draft-approve-dispatch" loop is a high-cost, zero-yield mechanism. The bottleneck is not the network adapter or the broker; it is the upstream signal quality and the lack of pre-dispatch filtering. We must pivot from "operator-driven validation of all unknowns" to "automated suppression of noise + targeted operator review of high-signal candidates."

## Risk Register

| ID | Risk | Likelihood | Impact | Net Severity |
|----|------|------------|--------|--------------|
| R1 | Operator burnout from reviewing unresolvable grants | High | High | High |
| R2 | False suppression of valid entities by RFC 0056 triage | Medium | High | High |
| R3 | Stale entity identity due to lack of periodic re-grounding | Medium | Medium | Medium |
| R4 | Broker DSN lock contention under high-volume batch processing | Low | High | Medium |
| R5 | Loss of provenance if triage actions are not append-only | Medium | High | High |

**R1 Elaboration:** The current workflow requires human approval for every draft. With a 0% resolution rate, every approval is wasted effort. This creates a negative feedback loop where operators lose trust in the system, leading to either blind approval (security risk) or abandonment (operational failure).

**R2 Elaboration:** RFC 0056 introduces a local LLM classifier. If this classifier is poorly tuned, it will suppress entities that *could* be resolved with better queries or context. Since the system is local-first, we cannot rely on external correction. A false suppression is a permanent loss of potential knowledge unless manually recovered.

**R3 Elaboration:** The current stack is append-only and event-driven. It does not have a mechanism to re-evaluate entities that were previously marked "unresolvable" or "ambiguous" if new local claims provide context. This leads to a static, decaying knowledge graph.

**R4 Elaboration:** The `broker-daemon` uses an advisory lock. If the batch size grows (e.g., from 5 to 500), the lock contention or transaction timeout risks increase. The current bounded iteration is safe, but scaling it requires careful transaction isolation planning.

**R5 Elaboration:** RFC 0056 proposes `entity_grounding_triage_actions`. If this table is not strictly append-only and lacks the same provenance guarantees as `entity_identity_review_actions`, we lose the audit trail for *why* an entity was suppressed. This breaks the "auditability" invariant of the grounding stack.

## Recommendations (Ranked)

1. **Action:** Implement RFC 0056 (pre-dispatch triage) with a strict "suppress-only" policy and append-only audit logging. Configure the triage classifier to aggressively filter segmentation-noise and duplicate surfaces before they reach the operator queue.
   **Why now:** This directly addresses R1 (operator burnout) and R5 (provenance). It reduces the operator load from 281 items to a manageable subset (likely <10) by eliminating the 95% of entities that are unresolvable noise.
   **Tradeoff:** Introduces false suppression risk (R2). We must accept that some valid entities may be suppressed and require a manual "un-suppress" workflow.
   **Sequencing:** Must land before any scaling of the grounding pipeline. Requires defining the triage schema and audit log format.

2. **Action:** Introduce a "confidence-thresholded auto-approval" layer for the broker daemon. If the triage classifier assigns a "high-confidence suppress" score, the entity is dropped without operator review. If it assigns "low-confidence suppress" or "pass," it enters the operator queue.
   **Why now:** This reduces operator toil further by automating the bulk of the filtering. It aligns with the constraint that per-grant human approval does not scale.
   **Tradeoff:** Increases complexity in the broker daemon and requires careful tuning of the classifier thresholds.
   **Sequencing:** Requires RFC 0056 to be stable and the triage actions table to be populated.

3. **Action:** Add a "re-grounding" trigger based on new local claim context. If a new claim references an entity previously marked "ambiguous" or "unresolvable," re-evaluate its grounding status.
   **Why now:** Addresses R3 (stale identity). This leverages the local-first advantage: we have more context now than we did when the entity was first encountered.
   **Tradeoff:** Increases computational load on the materializer and requires a mechanism to detect "new context" for existing entities.
   **Sequencing:** Requires changes to the claim ingestion pipeline to flag entities for re-evaluation.

4. **Action:** Implement a "batch review" CLI command for operators. Instead of reviewing grants one-by-one, operators review a batch of 10-20 high-signal candidates at once, with a "approve all" or "deny all" option for similar entities.
   **Why now:** Reduces context-switching overhead for operators. Aligns with the "batch review" anti-toil recommendation.
   **Tradeoff:** Requires UI/CLI changes to support batch operations and may introduce errors if the batch contains mixed-quality candidates.
   **Sequencing:** Requires the triage layer to produce a curated list of high-signal candidates.

## Anti-Recommendations

- **Do not** abandon the byte-exact `search_query == surface_form` invariant. It is the only thing keeping the network surface trustworthy. If we need disambiguation, we must solve it locally (via context) or via operator intervention, not by relaxing the query constraint.
- **Do not** implement a "cloud fallback" for grounding. This violates the local-first invariant and introduces telemetry/export risks.
- **Do not** allow the triage classifier to "resolve" entities. It can only suppress or pass. Resolution must remain the domain of the broker and the operator.
- **Do not** scale the broker daemon to process thousands of entities per iteration. Start with small batches (10-50) and monitor lock contention and error rates.

## 3-Month Plan

**Month 1: Triage & Audit Foundation**
- **Deliverable:** RFC 0056 implemented with append-only `entity_grounding_triage_actions` table.
- **Metric:** Reduction in operator review queue size (target: >90% reduction).
- **Gate:** Audit log completeness check (every suppression must have a reason).

**Month 2: Auto-Approval & Batch Review**
- **Deliverable:** Confidence-thresholded auto-approval in broker daemon + `engram entity-grounding batch-review` CLI.
- **Metric:** Operator time spent on grounding (target: <5 mins/day).
- **Gate:** False suppression rate <5% (measured via manual spot-checks).

**Month 3: Re-grounding & Stability**
- **Deliverable:** Re-grounding trigger based on new local claims + improved error handling for ambiguous responses.
- **Metric:** Resolution rate for re-grounded entities (target: >20%).
- **Gate:** No loss of provenance in re-grounding events.

## Open Architectural Questions

1. **How do we define "high-signal" for the operator queue?** Should it be based on triage confidence scores, entity frequency in local claims, or a hybrid?
2. **What is the recovery mechanism for false-suppressed entities?** Should there be a "undo suppression" CLI command, or should operators manually re-draft grants for suppressed entities?
3. **How do we handle "ambiguous" responses from the broker?** Should we retry with different queries, or mark them as "unresolvable" and wait for new context?
4. **What is the acceptable false-suppression rate for the triage classifier?** Is 1% acceptable, or must it be 0%? This decision dictates the classifier's sensitivity.