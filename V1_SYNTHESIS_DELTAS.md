# V1 Synthesis: Principle Deltas
**Date:** 2026-04-28
**Status:** Synthesized from 4-Model Review (Claude, Codex, Qwen, Gemini)

This document synthesizes the Round 2 principle reviews against the V1 Architecture Draft. The models evaluated V1's adherence to the seven foundational principles in `HUMAN_REQUIREMENTS.md`.

## 1. Universal Principle Adherence (Locked)
All 4 models agree that V1 successfully structurally honors:
*   **Time-indexed biography:** Bitemporal validity (`valid_from`, `valid_to`) and close-and-insert on contradiction are fundamentally correct.
*   **Three-tier separation:** The progression of immutable raw evidence → claims → beliefs with `evidence_ids NOT NULL` successfully implements "Raw data is sacred."
*   **Corpus/Network Separation:** The structural design of `context_for` as a pure read emitting a text package to an external agent honors the network egress boundary.

## 2. Necessary Delta Identifiers (Gaps found in V1)
The reviews identified critical silences and violations in V1 that must be fixed to comply with the principles:
*   **Corrections are Raw Evidence (P4):** A UI "correction" cannot mutate a belief in-place or simply add a metadata flag. User corrections MUST be logged as immutable `captures` rows that then trigger the standard supersession pipeline.
*   **Missing Data / Gaps Lane (P7):** To honor "Refusal of false precision," the `context_for` package cannot just be silent when it lacks data on a queried topic. It must explicitly emit "No data / insufficient evidence" to prevent the consuming model from hallucinating or assuming a negative.
*   **Process Isolation (P3):** The corpus/network separation must be enforced at the OS level (e.g., Linux network namespace, macOS sandbox) for the `context_for` process, and the MCP server must bind only to `127.0.0.1`.
*   **Schema Additions (P5, P6, P7):** 
    *   `privacy_tier` must exist on `beliefs` and `captures` now to ensure v1-to-v2 stability.
    *   A `contradictions` table is required in V1 to support user corrections and lay the groundwork for adversarial sweeps.
    *   `original_prompt_version` and `original_model_version` on beliefs to track derivation trails across multiple re-extractions.

## 3. The Eval-Gate Refinement (P5)
The 100-conversation random subset was universally rejected as a sufficient gate before full-corpus consolidation. Because the gold set queries specific entities and years, a random subset will fail the eval simply because the evidence wasn't sampled. 

**Resolution: Tiered Eval Structure**
1.  **Smoke Test (~100 conversations):** Catches catastrophic pipeline failures, broken segmentation, and parsing errors.
2.  **Gold-Set Validation (~1,000-2,000 stratified conversations):** A target-closed subset containing the actual entities, projects, and years referenced by the 25-50 gold prompts. *This is the true gate.*
3.  **Full Corpus (5,000+ conversations):** Proceeds only after Tier 2 passes without regressions.
