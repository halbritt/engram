# V1 Synthesis: Principle Deltas
**Date:** 2026-04-28
**Status:** Synthesized from 4-Model Review (Claude, Codex, Qwen, Gemini)

This document synthesizes the Round 2 principle reviews against the V1 Architecture Draft. The models evaluated V1's adherence to the seven foundational principles in `HUMAN_REQUIREMENTS.md`.

## 1. Universal Principle Adherence (Locked)
All 4 models agree that V1 successfully structurally honors:
*   **Time-indexed biography:** Bitemporal validity (`valid_from`, `valid_to`) and close-and-insert on contradiction are fundamentally correct.
*   **Three-tier separation:** The core progression of immutable raw evidence → claims → beliefs with `evidence_ids NOT NULL` structurally honors "Raw data is sacred," subject to the correction-path delta below.
*   **Corpus/Network Separation:** The structural design of `context_for` as a pure read emitting a text package to an external agent honors the network egress boundary.

## 2. Necessary Delta Identifiers (Gaps found in V1)
The reviews identified critical silences and violations in V1 that must be fixed to comply with the principles:
*   **Corrections are Raw Evidence (P4):** A UI "correction" cannot mutate a belief in-place or simply add a metadata flag. User corrections MUST be logged as immutable `captures` rows that then trigger the standard supersession pipeline.
*   **Missing Data / Gaps Lane (P7):** To honor "Refusal of false precision," the `context_for` package cannot just be silent when it lacks data on a queried topic. It must explicitly emit "No data / insufficient evidence" to prevent the consuming model from hallucinating or assuming a negative.
*   **Process Isolation (P3):** The corpus/network separation must be enforced at the OS level (e.g., Linux network namespace, macOS sandbox) for the `context_for` process, and the MCP server must bind only to `127.0.0.1`.
*   **Schema Additions (P5, P6, P7):** 
    *   `privacy_tier` must exist on `beliefs` and `captures` now to ensure v1-to-v2 stability. Retrieval-visible derived units such as `segments` and context items must either carry their own tier or inherit the maximum sensitivity of their evidence.
    *   A `contradictions` table is required in V1 to track belief conflicts and lay the groundwork for adversarial sweeps. User corrections may create contradiction records, but the correction substrate is the immutable `captures` row plus normal supersession.
    *   Derivation versioning must be explicit across the pipeline: segmenter versions on `segments`, extraction prompt/model versions on `claims`, embedding model/version metadata in `embedding_cache`, and prompt/model/run history in `belief_audit`. `beliefs.prompt_version` and `beliefs.model_version` remain required; extra `original_*` columns are optional if the audit trail preserves the full derivation chain.

## 3. The Eval-Gate Refinement (P5)
The 100-conversation random subset was universally rejected as a sufficient gate before full-corpus consolidation. Because the gold set queries specific entities and years, a random subset will fail the eval simply because the evidence wasn't sampled. 

**Resolution: Tiered Eval Structure**
1.  **Smoke Test (~100 conversations):** Catches catastrophic pipeline failures, broken segmentation, and parsing errors.
2.  **Gold-Set Validation (~1,000-2,000 stratified conversations):** A target-closed subset containing the actual entities, projects, and years referenced by the 25-50 gold prompts. *This is the true gate.*
3.  **Full Corpus (5,000+ conversations):** Proceeds only after Tier 2 passes without regressions.
