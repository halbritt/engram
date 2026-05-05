# Phase 3 Build Prompt Review

Date: 2026-05-05
Model: gemini_pro_3_1
Target artifact: `prompts/P028_build_phase_3_claims_beliefs.md`

## Verdict
The build prompt (P028) is structurally sound, safe, and closely aligned with the amended spec (`docs/claims_beliefs.md`). It correctly establishes boundaries to prevent full-corpus runs, prohibits external LLM calls, and sets explicit versioning constraints.

However, there is a minor omission regarding explicit implementation instructions for the privacy reclassification decision tree, which could lead to ambiguity during execution.

## Findings

### 1. Missing Implementation Tasks & Ambiguities
- **Reclassification Recompute Logic:** The build prompt lists "privacy reclassification recompute's three branches" under the **Test Plan** section, but omits explicit implementation instructions in the **Consolidator Requirements** section. The implementer might overlook this logic (Empty surviving set -> reject, Same-value -> supersede, Different-value -> close-and-insert + contradiction) if it is not spelled out alongside Decision Rules 1, 2, and 3. The prompt should explicitly instruct the implementation of the three-branch decision tree defined in D054.
- **Group Object Key for `single_current`:** The prompt clearly defines how to construct `group_object_key` for text and JSON predicates, but does not explicitly remind the implementer that `single_current` predicates use an empty string `''`. While this is covered in the spec, adding a brief note in the build prompt would reduce the risk of implementation errors.

### 2. Hidden Architecture Decisions
None found. The prompt faithfully propagates the architecture decisions established in the spec (e.g., `ENGRAM_EXTRACTOR_INFLIGHT_TIMEOUT_SECONDS`, transition API, deterministic Python consolidator).

### 3. Unsafe Migration or Mutation Instructions
None found. The instructions regarding existing Phase 3 files (e.g., `src/engram/extractor.py`, `migrations/006_claims_beliefs.sql`) are robust. The prompt explicitly instructs the implementer to treat them as scaffolding to be brought into alignment rather than treating them as authoritative, which prevents stale decisions from leaking into the new implementation.

### 4. Inadequate Tests
The testing requirements are rigorous and exhaustive. The prompt successfully translates all major acceptance criteria from the spec into concrete test requirements, including specific edge cases like bitemporal close math, re-extraction blast radius, and per-claim salvage.

### 5. Local-First / Privacy Violations
Appropriate guardrails are in place. The prompt enforces `127.0.0.1` binding, explicit endpoint constraints, and forbids cloud APIs, telemetry, and external persistence.

### 6. Full-Corpus Run Risks
Fully mitigated. The prompt contains explicit instructions ("Do not run the full Phase 3 corpus") and requires the use of fake extractor clients and synthetic DB fixtures for unit tests. `engram pipeline-3` is also isolated properly.

## Recommendation
The build prompt is ready for synthesis. Adding explicit implementation steps for the reclassification 3-branch logic to the "Consolidator Requirements" section is recommended to clear up the identified ambiguity.
