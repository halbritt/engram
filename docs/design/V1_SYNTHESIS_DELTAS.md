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
*   **Schema Additions (per principle):**
    *   **(P2 + Meta-Requirements §"Privacy & access tiers"):** `privacy_tier` must exist on `beliefs` and `captures` now to ensure v1-to-v2 stability. Retrieval-visible derived units such as `segments` and context items must either carry their own tier or inherit the maximum sensitivity of their evidence.
    *   **(P6):** A `contradictions` table is required in V1 to track belief conflicts and lay the groundwork for adversarial sweeps. User corrections may create contradiction records, but the correction substrate is the immutable `captures` row plus normal supersession.
    *   **(P4):** Derivation versioning must be explicit across the pipeline: segmenter versions on `segments`, extraction prompt/model versions on `claims`, embedding model/version metadata in `embedding_cache`, and prompt/model/run history in `belief_audit`. `beliefs.prompt_version` and `beliefs.model_version` remain required; extra `original_*` columns are optional if the audit trail preserves the full derivation chain.

## 3. The Eval-Gate Refinement (P5)
The 100-conversation random subset was universally rejected as a sufficient gold-set gate. Because the gold set queries specific entities and years, a random subset will fail the eval simply because the evidence wasn't sampled. Three reviewers (Codex, Gemini, Claude round-1) initially proposed a stratified middle tier (~1k–2k conversations matching the gold set's entities/years). That middle tier was subsequently rejected on owner review: stratifying on "conversations about Sarah" requires entity extraction to have already run, i.e., requires the pipeline the gate is supposed to gate. The regress doesn't terminate, and the local-research-lab compute budget makes "consolidate the V1 corpus" cheaper than building a correctness-validated stratifier.

**Resolution: Two-Phase Eval (post-owner-review)**

A terminology note: "V1 corpus" means the V1 ingestion set (≈5k AI conversations across ChatGPT + Claude + Gemini + Obsidian + capture). It is not the long-arc biographical corpus, which accrues over years across health, finances, locations, relationships, recipes, and other manual-capture domains and is V2-or-later.

1.  **Smoke gate (~200 random conversations) — gates V1-corpus consolidation.** Plumbing only: ingestion populates raw tables, segments embed, claims extract, beliefs land with `evidence_ids`, contradictions get flagged, build resumes after interruption. Pass/fail is schema-level, not retrieval-quality-level.
2.  **V1-corpus consolidation (~5k AI conversations + Obsidian + capture) — runs after smoke passes, not behind a quality gate.** Multi-week local-LLM compute. Absorbed by the local-research-lab posture.
3.  **Gold-set validation — runs against the consolidated V1 corpus.** The P5-binding eval. Failures drive prompt-version / model-version re-extraction cycles via the non-destructive pipeline (P4 makes this cheap). The V1 gold set is sized to what AI conversations + Obsidian + capture can ground; categories beyond V1 scope (health, finances, etc.) produce v2-or-later gold-set entries.
