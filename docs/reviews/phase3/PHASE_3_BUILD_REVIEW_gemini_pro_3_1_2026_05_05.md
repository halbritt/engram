# Phase 3 Build Review

Reviewer: Gemini Pro 3.1 (`gemini_pro_3_1`)
Date: 2026-05-05

## Summary

The Phase 3 implementation accurately translates the bitemporal claims and beliefs specification into a robust, localized pipeline. The SQL migration, Python extraction loop, deterministic consolidator, and transition APIs demonstrate strict adherence to the defined architecture, particularly around data immutability, provenance, and privacy-tier inheritance.

## Detailed Findings

1. **Schema & Spec Parity:**
   - `migrations/006_claims_beliefs.sql` correctly implements the schema and constraints, including the `predicate_vocabulary` table with its exact seeds and cardinality classes.
   - The constraints on `claims` (subset check for evidence) and `beliefs` (non-empty evidence, correct bitemporal state guards via `engram.transition_in_progress`) are present and accurate.
   - Normalization logic parity between PL/pgSQL and Python is well aligned and confirmed by tests.

2. **Provenance & Evidence Bugs:**
   - No issues observed. Empty evidence is blocked at the schema level (`cardinality(evidence_ids) > 0`). Evidence is tracked explicitly via `claim_ids` and `evidence_message_ids`.

3. **Immutability & Non-Destructive Derivation:**
   - Raw tables are untouched.
   - Belief row lifecycle strictly uses the bitemporal fields (`status`, `closed_at`, `superseded_by`, `valid_from`, `valid_to`) without destructive in-place data modifications.

4. **Audit Log:**
   - `belief_audit` table captures all transitions. The `transitions.py` API correctly sets the `request_uuid` GUC and pairs mutations with audit insertions in the same transaction.

5. **Local LLM Contract:**
   - The extractor correctly enforces the `ik-llama-json-schema.d034.v2.extractor-8192` request profile.
   - Prompt construction manages context budget and uses placeholders for tool messages.

6. **Retry / Resumability:**
   - Progress is correctly tracked per-conversation in `consolidation_progress`.
   - The extractor correctly reaps stale extractions to `failed` without deleting rows, preserving the required diagnostic data.

7. **Privacy-Tier Propagation:**
   - Privacy tiers are accurately inherited from segments to claims, and maximally aggregated from claims to beliefs.
   - `apply_phase3_reclassification_invalidations` handles invalidating the extraction outputs, ensuring recomputes conform to the three-branch decision tree (D054).

8. **Tests & Hazards:**
   - Test coverage effectively mocks LLM dependencies and rigorously checks all bitemporal logic, triggers, and CLI commands.
   - Operator commands (`engram pipeline-3`, `engram consolidate --rebuild`) cleanly isolate Phase 3 from the preexisting Phase 1/2 workflow.

## Conclusion

The build passes review. No architectural mismatches or critical gaps were found.

Status: Accepted.
