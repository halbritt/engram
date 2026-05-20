# Engram Grounding Stack — Architectural Review by GPT-5

## Verdict

restructure

The core primitives are correct: append-only evidence, explicit grants, restricted broker DSN, and the RFC 0053 byte-exact `search_query == surface_form` rule. The current workflow is not correct: it spends scarce operator attention before the system has proved a candidate is broker-worthy, and then measures success by dispatch/evidence creation rather than identity resolution.

## Risk Register

| ID | Risk | Likelihood | Impact | Net Severity |
|----|------|------------|--------|--------------|
| R1 | Upstream unknown-entity noise dominates grounding | H | H | H |
| R2 | Per-grant approval bottleneck blocks scale | H | H | H |
| R3 | Exact-query boundary cannot disambiguate alone | H | M | H |
| R4 | False suppression hides real entities | M | H | H |
| R5 | No labeled eval masks regressions | H | H | H |
| R6 | Context leakage pressure erodes privacy boundary | M | H | H |
| R7 | Evidence rows mistaken for resolution | H | M | H |
| R8 | Broker privilege expansion increases network blast radius | M | H | H |
| R9 | Local LLM prompt drift weakens auditability | M | M | M |
| R10 | Tavily-only behavior creates provider lock-in | M | M | M |

R1: Phase 4 is producing too many `unknown` entities that are not meaningful broker candidates: personal artifacts, segmentation noise, duplicates, and locally ambiguous surfaces. RFC 0054 and RFC 0055 are downstream of that noise, so they cannot fix the root problem.

R2: `claim_grounding_grants` makes consent explicit, but one human action per grant does not scale. With 281 unresolved entities and 0 resolved after five approved grants, the current approval model consumes operator time before expected value is known.

R3: The RFC 0053 byte-exact rule is privacy-preserving and should remain load-bearing, but it means the broker cannot receive local claim context. Ambiguous public surfaces will remain ambiguous unless resolution happens locally after evidence retrieval.

R4: RFC 0056 is directionally right, but suppression becomes a correctness risk. A high-confidence local classifier can still hide a real entity, especially for rare names, nicknames, personal projects, and malformed segmenter output.

R5: The stack has no durable labeled set, no tracked resolution rate, no false-suppression rate, and no per-stage error budget. Without that, the team cannot tell whether RFC 0056, batching, or resolver changes improve the system.

R6: The obvious way to improve network results is to add context to queries. That would silently break the local-first privacy model unless explicitly redesigned. Pressure to “just add qualifiers” will grow as ambiguity remains visible.

R7: RFC 0055 can successfully materialize `entity_grounding_evidence` while resolving zero entities. If evidence count becomes the success metric, the system will look healthier while becoming noisier for downstream memory lookup.

R8: `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` is a good seam, but it becomes more dangerous once auto-approval or daemonized processing grows. The broker role must stay narrow and testable.

R9: RFC 0056 introduces local LLM classification. That is acceptable only if prompt version, model identity, input digest, confidence, and reason codes are captured in `entity_grounding_triage_actions`.

R10: Tavily is currently the only network provider. The stdlib POST shape is appropriately boring, but provider-specific result semantics can leak into resolver behavior unless replay fixtures and adapter boundaries are made explicit.

## Recommendations (Ranked)

1. **Action:** Build a grounding evaluation baseline before broadening automation. Label the current 281 Phase 4 unknowns, or a representative fixed sample, into categories: broker-eligible public entity, duplicate, segmentation noise, personal artifact, local-only entity, sensitive/private, ambiguous-but-real, and ungroundable. Track draft rate, approval rate, dispatch success, evidence materialization, resolution rate, false suppression, and operator actions per resolved entity.  
   **Why now:** The observed 0% resolution rate is not diagnosable without stage metrics. This addresses R1, R5, and R7.  
   **Tradeoff:** It costs operator labeling time up front. That is still cheaper than approving grants blindly.  
   **Sequencing:** Land before RFC 0056 auto-suppression and before confidence-thresholded approval.

2. **Action:** Reframe RFC 0056 as a triage policy gate, not just a classifier. Keep the rule-based prefilter, add the local LLM only for cases rules cannot classify, and persist every decision in `entity_grounding_triage_actions` with `prompt_version`, `model_id`, confidence, reason code, input digest, and sampled audit eligibility. Auto-suppress only high-confidence noise, duplicates, and personal artifacts; send medium-confidence cases to batch review.  
   **Why now:** Operator toil has to move left of `claim_grounding_grants`. This addresses R1, R2, R4, and R9.  
   **Tradeoff:** False suppression becomes a real failure mode, so sampled audit and rollback paths are mandatory.  
   **Sequencing:** Requires the labeled baseline and a defined false-suppression budget.

3. **Action:** Fix the Phase 4 output contract so `unknown entity` is not treated as `grounding candidate`. Emit candidate features needed for local triage: occurrence count, source count, entity type, duplicate cluster, segmenter confidence, local claim IDs, stability class, and sensitivity flags. Keep local context inside the database; do not send it to the broker.  
   **Why now:** The root cause is upstream signal quality, not RFC 0055 materialization. This addresses R1 and R6.  
   **Tradeoff:** It expands the Phase 4 interface and may require migrations or backfills.  
   **Sequencing:** Should follow the eval taxonomy so the new fields directly support measured decisions.

4. **Action:** Replace per-grant human approval with tiered batch review. Preserve `claim_grounding_grants` as the audit record, but allow policy-approved batch actions: auto-deny/suppress Tier 0 noise, auto-approve Tier 1 low-risk public exact surfaces under an operator-approved policy, batch-review Tier 2 ambiguous surfaces, and require explicit handling for Tier 3 sensitive/private surfaces.  
   **Why now:** The current approval gate is both the trust mechanism and the bottleneck. This addresses R2 and R8.  
   **Tradeoff:** Auto-approval increases the chance of an unintended broker query. Mitigate with dry-run previews, exact byte display of `search_query`, batch size limits, and sampled post-hoc audit.  
   **Sequencing:** Broker DSN hardening and triage audit must land first.

5. **Action:** Add a local-only identity adjudication stage after `entity_grounding_evidence` materialization. The broker retrieves candidates with exact `surface_form`; a local resolver then combines those candidates with local claim context to mark resolved, ambiguous, denied, or needs operator review. This should be a separate stage from `engram entity-grounding process-approved`.  
   **Why now:** The network adapter cannot resolve ambiguity without violating RFC 0053. Local adjudication addresses R3, R6, and R7.  
   **Tradeoff:** Some resolution logic becomes local-model or heuristic dependent, so confidence and provenance must be stored.  
   **Sequencing:** Requires materialized evidence, candidate features from Phase 4, and an eval set with expected outcomes.

6. **Action:** Harden the RFC 0053 boundary as automation increases. Add invariant checks around `search_query == surface_form`, keep `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` mandatory for broker execution, test restricted-role access, and ensure `broker-daemon` cannot read broad local memory tables.  
   **Why now:** Batch approval and daemonized processing raise blast radius. This addresses R6 and R8.  
   **Tradeoff:** More database-role and migration testing. Worth it before any auto-approval.  
   **Sequencing:** Land before Tier 1 policy auto-approval.

7. **Action:** Introduce provider replay fixtures and a narrow search adapter contract. Keep the current Tavily stdlib POST implementation, but store sanitized provider responses for deterministic tests and make resolver logic consume provider-neutral candidate fields.  
   **Why now:** This prevents Tavily result quirks from becoming architecture. It addresses R10 and supports R5.  
   **Tradeoff:** Adds fixture maintenance and adapter discipline.  
   **Sequencing:** Can land after the first eval baseline, before adding a second provider.

## Anti-Recommendations

1. **Do not weaken RFC 0053 by adding local claim context to broker queries.** Query refinement would improve search quality, but it changes the consent and privacy model. Any future change to `search_query == surface_form` needs a new RFC and a visibly different approval surface.

2. **Do not scale the current process by approving more grants manually.** That converts architecture debt into operator toil. The next quarter should reduce approvals per useful resolution, not run a larger approval queue.

3. **Do not treat `entity_grounding_evidence` row count as success.** Five successful dispatches and 25 rows produced zero resolutions. The success metric is resolved identities with preserved provenance, not evidence volume.

4. **Do not put an LLM inside the network adapter.** LLM interpretation belongs in local triage or local adjudication, where provenance and prompt versions can be audited without expanding network behavior.

5. **Do not introduce hosted identity services, cloud vector stores, telemetry, SDK agents, or browser automation.** They violate or pressure the local-first invariant and make the RFC 0053 broker boundary harder to reason about.

## 3-Month Plan

- **Month 1:** Deliver a grounding eval baseline over the current 281 unknown entities or a fixed representative sample. Metric improved: visibility into resolution rate, false-suppression risk, and operator actions per resolved entity. Review surface: `docs/reviews/grounding-eval-baseline.md`, updated `DECISION_LOG.md`, deterministic tests run through `make test`.

- **Month 1:** Harden RFC 0053 invariants around `claim_grounding_requests`, `claim_grounding_grants`, `claim_grounding_network_dispatches`, and `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL`. Metric improved: broker boundary safety before automation. Review surface: migration/test review plus explicit byte-exact query test cases.

- **Month 2:** Land revised RFC 0056 as a triage policy gate with `entity_grounding_triage_actions` and `engram entity-grounding triage`. Metric improved: reduction in broker-eligible queue size and grants drafted from noise. Review surface: RFC 0056 approval, sampled audit report, false-suppression threshold.

- **Month 2:** Add batch/tiered review to `engram claim-grounding grants {list,draft,approve,deny,revoke}` without removing per-grant audit rows. Metric improved: operator actions per approved broker query. Review surface: CLI workflow review on the labeled corpus and `CHANGELOG.md`.

- **Month 3:** Add the local-only adjudication stage that resolves identities from `entity_grounding_evidence` plus local claim context without changing broker queries. Metric improved: resolution rate among broker-eligible candidates. Review surface: new resolver RFC, eval report comparing pre/post resolution, and append-only provenance review.

- **Month 3:** Add provider replay fixtures and provider-neutral candidate fields for resolver tests. Metric improved: deterministic regression coverage and reduced Tavily lock-in. Review surface: fixture review ensuring no sensitive local data is stored, plus `make test`.

## Open Architectural Questions

- What false-suppression rate is acceptable for RFC 0056 before a suppressed sample must be routed back to human review?

- Should Tier 1 auto-approval be opt-in per corpus, per operator session, or a persistent local policy?

- What minimum local evidence should allow adjudication to mark an entity resolved without operator review?

- How should revoked or expired `claim_grounding_grants` affect already-materialized `entity_grounding_evidence` in downstream lookup?

- Should personal or local-only entities receive a separate local identity workflow instead of being repeatedly suppressed from grounding?

- Does the team want one unified review queue for identity review, triage audit, and grounding grants, or separate CLIs optimized for each stage?
