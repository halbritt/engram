# V1 Architecture Review: engram
**Reviewer:** Gemini CLI
**Date:** April 28, 2026

This review evaluates the [V1_ARCHITECTURE_DRAFT.md](V1_ARCHITECTURE_DRAFT.md) against the seven foundational principles defined in [HUMAN_REQUIREMENTS.md](HUMAN_REQUIREMENTS.md).

---

## 1. Per-principle assessment

### P1: The distinguishing property: time-indexed biography
- **Status:** Honors.
- **Reasoning:** V1 explicitly includes `valid_from` and `valid_to` on the `beliefs` table and adopts the bitemporal close-and-insert pattern. This allows the system to reconstruct state at any point in time, satisfying the "spine" of the requirements.
- **Delta:** None required.

### P2: Why local-first is load-bearing
- **Status:** Honors.
- **Reasoning:** V1 commits to local inference only and local hardware. The "Implications" (no telemetry, encrypted backups) are respected as constraints, though implementation details are deferred to SECURITY.md.
- **Delta:** None for architecture; see Security implications for implementation mandates.

### P3: Why corpus access and network egress are kept separate
- **Status:** Honors.
- **Reasoning:** The `context_for` compiler is designed as a pure read-and-package operation. The separation is structurally enforced by the output being a text package for a separate consuming model.
- **Delta:** None.

### P4: Why raw data is sacred (model portability)
- **Status:** Honors.
- **Reasoning:** V1 adopts the three-tier separation (`episodes → claims → beliefs`) and enforces `evidence_ids NOT NULL` on accepted beliefs. The requirement that user corrections are "raw evidence" (captures) rather than metadata flags is a critical adherence to this principle.
- **Delta:** None.

### P5: Why eval is the only objective oracle
- **Status:** Honors.
- **Reasoning:** V1 gates full-corpus consolidation on an eval pass. However, the current "100-conversation subset" gate is technically too weak to satisfy the principle's intent for a "complete biography" (see Tiered Eval section below).
- **Delta:** Adopt the **Tiered Eval Alternative** (Smoke → Gold-set → Full) to ensure the gate is actually meaningful for the specific entities in the gold set.

### P6: Why adversarial review is a permanent feature
- **Status:** Silent.
- **Reasoning:** V1 defers "Adversarial re-extraction sweeps" to the research/experimental section. While the schema (contradictions, audit log) supports it, V1 doesn't name it as part of the post-launch operational cycle.
- **Delta:** Name "V1.1: First Falsification Sweep" in the build order. The system should run at least one automated check for contradictions between new ChatGPT data and existing Obsidian notes before v1 is considered "validated."

### P7: Why refusal of false precision is a contract
- **Status:** Honors.
- **Reasoning:** V1 includes `confidence` in the ranking formula and a dedicated "Uncertain / Conflicting" section in the context package. 
- **Delta:** Propose an explicit "Missing Data" response pattern. If a query targets a known entity with no current beliefs, `context_for` should emit a "No data found for [Entity]" marker rather than omitting the section, to satisfy the principle's "not silence" requirement.

---

## 2. Schema or build-order additions

### Schema additions
- **`missing_context` lane:** Add a lane to `context_for` that identifies when a query mentions a canonical entity but retrieves zero current beliefs. This prevents "silence" being mistaken for "nothingness."
- **`privacy_tier` column:** Add to the `beliefs` table now. Even if V1 only uses Tiers 1 and 2, the principle-derived security model (see below) requires this for v1-to-v2 stability.

### Build-order additions
- **Step 14a: Stratified Gold-Set Validation.** Insert between "Small-batch evals" and "Full-corpus consolidation." This ensures the ~1,000-2,000 conversations relevant to the gold-set prompts are processed and verified before the 3-week compute burn begins.
- **Step 17: Initial Falsification Sweep.** Run a cross-source contradiction check (ChatGPT vs Obsidian) to validate the "Adversarial review" principle in production.

---

## 3. Security implications

Based on the principle review, the following must be added to [SECURITY.md](SECURITY.md):

- **Process Sandboxing (P3):** The process executing `context_for` (the retrieval/compiler side) MUST be executed within an OS-level sandbox (e.g., `bubblewrap` on Linux, `sandbox-exec` on macOS) with no network interface. This is not a "TBD" but a requirement derived from the "separation" principle.
- **Cryptographic Erasure for Tier-5 (P2):** Any belief tagged with Tier-5 (redact-on-death) must be encrypted with a key that is never shared with successors and is explicitly deleted upon the dead-man's-switch trigger.
- **Provenance Integrity:** The `evidence_ids` in a belief must be immutable. An attacker should not be able to "re-parent" a hallucinated belief to legitimate evidence.

---

## 4. Position changes

My round-1 position has shifted on the following:

- **The Wiki as Control Plane:** In round 1, I argued the Wiki was the essential HITL surface. However, the principle **"Raw data is sacred"** clarifies that user corrections MUST be raw evidence. This makes the **Belief Review Queue** a superior architectural choice for V1, as it focuses human attention on the extraction boundary rather than the narrative projection. I now support deferring the Wiki writeback.
- **LLM Reranker:** I previously pushed for an LLM reranker for quality. The principle **"Refusal of false precision"** favors a transparent, weighted scorer where `confidence` and `provenance` are visible and tunable. I support "weighted scorer first," keeping the reranker as an offline experiment.

---

## 5. The Eval Gate Subset Size (Tiered Alternative)

The proposed tiered alternative correctly identifies the gap. A random 100-conversation sample is statistically likely to miss the specific people and projects authored into a high-quality gold set. 

**Recommendation:**
1. **Smoke Test (100 random):** Validates the pipeline doesn't crash and extraction isn't gibberish.
2. **Gold-Set Validation (1,000-2,000 stratified):** Process only the episodes/notes referenced in the 25-50 gold set prompts. If the pipeline cannot retrieve the "ground truth" answers from this targeted set, it will certainly fail on the full corpus. **This is the true gate.**
3. **Full Corpus (5,000+):** Only proceeds after Tier 2 achieves the required precision/recall targets.

---

## 6. Strongest residual concern

The single most important issue is the **"silence as data"** implementation. While V1 handles bitemporal validity well, it lacks a mechanism to distinguish between "I don't know" and "There is nothing to know." If the context package is silent about a major life gap (e.g., a missing year of health records), the consuming AI will assume the user has no health history. The system needs a "Gap Registry" or a "Silence Lane" to fulfill the "Refusal of false precision" contract, ensuring the AI knows precisely where the biography's blind spots are.

---
