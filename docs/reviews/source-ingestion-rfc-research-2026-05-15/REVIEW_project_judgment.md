# Project Judgment Review: Source Ingestion Expansion

| Lane | gemini |
|------|--------|
| Role | reviewer |
| Date | 2026-05-15 |
| Status | Review complete; verdict: `accept_with_findings` |

## Summary

This artifact records the project judgment review of the source-ingestion expansion proposal and its three parallel RFC drafts (`DRAFT_claude.md`, `DRAFT_codex.md`, `DRAFT_gemini.md`) along with the prior-art dossier.

The review confirms that the drafts are highly convergent, technically sound, and strictly aligned with Engram's core mandates of local-first operation and no-egress corpus access. The "Source Contract" pattern provides a robust framework for expanding the system from an AI conversation memory into a complete biographical corpus without "folklore" implementation or privacy drift.

The package is **accepted with findings** as a candidate for synthesis. The findings below address minor policy mismatches and naming divergences that should be resolved during the final synthesis pass.

---

## 1. Scope and Design Alignment

The package demonstrates excellent alignment with the source design document. It effectively transitions from the current closed `source_kind` enum toward a contract-based expansion model.

- **Fidelity to Design:** All drafts correctly identify the four evidence lanes (Conversation, Document, Project/Execution, Observation/Life) and the four core contract questions.
- **Scope Control:** The "Scope Kept Out" sections are honest and defensive, explicitly deferring cloud APIs, continuous surveillance, and media body storage.
- **Adjacent RFCs:** The drafts correctly reference the Striatum memory track (RFC 0044-0049) and the multimodal observation layer (RFC 0033-0036), ensuring that the expansion builds upon established patterns rather than reinventing them.

---

## 2. Privacy and No-Egress Invariants

The drafts reinforce the project's load-bearing privacy constraints.

- **No-Egress Policy:** The requirement for no outbound network calls from corpus-reading processes is universal and enforced via per-adapter gates.
- **Third-Party Data:** The inclusion of an explicit extraction gate for human-to-human communication is a critical privacy protection that must survive synthesis.
- **Derived Product Security:** The `claude` draft introduces a "no-derived-product-leak" invariant (§ 5.2) which correctly identifies that generated summaries must inherit the privacy tier of their evidence and must not exit the machine. This is a vital addition for the biography-scale corpus.

---

## 3. Source Contract Coherence

The three drafts converge on an implementable contract template.

- **Convergence:** There is 90%+ agreement on mandatory fields (identity keys, temporal mapping, acquisition mode, network policy, privacy default).
- **Implementation Posture:** The recommendation to start with "documentation plus tests" (contract YAML + importer fixtures) is a pragmatic and safe way to scale before committing to a full database-backed source registry.
- **Divergence (Minor):** Minor naming differences in projection families exist but are purely lexical and easily merged.

---

## 4. Rollout and Evaluation Gates

The proposed rollout order is defensible and prioritizes highest-signal, lowest-risk sources.

- **Prioritization:** Starting with Project Execution (Git and Build artifacts) is the correct strategic move. It grounds the AI in the user's current work state with structured, local-first data before tackling sensitive human communications.
- **Gate Integrity:** The proposed evaluation gates (idempotency, no-network, rebuild, citation) are sufficient to maintain pipeline honesty.

---

## 5. Findings Ledger

| ID | Title | Affected Drafts | Finding and Suggested Edit |
|----|-------|-----------------|----------------------------|
| **R-001** | Privacy Tier Policy Mismatch | All | **Finding:** `HUMAN_REQUIREMENTS.md` suggests Tier 1 defaults for health/finance with promotion later, while the design doc and drafts recommend Tier 3/4+ by default. <br>**Suggested Edit:** Synthesize a clear policy decision. Recommend the more restrictive default (Tier 3+) to align with the "fail-closed" security posture of the project. Note that `HUMAN_REQUIREMENTS.md` may require a future clarifying update. |
| **R-002** | Projection Family Unification | `claude`, `codex` | **Finding:** Minor naming and scope divergences in projection families (e.g., `observation_metadata` vs `observation`/`place_event`). <br>**Suggested Edit:** Merge into a unified set using the more granular families from `codex` (§ Projection Families) as they provide better hooks for multimodal/life evidence. |
| **R-003** | Derived Product Leak Invariant | `claude` | **Finding:** `claude` § 5.2 is high-signal but missing from other drafts. <br>**Suggested Edit:** Include the "no-derived-product-leak" invariant explicitly in the synthesized RFC. |
| **R-004** | Gate Handle Formatting | `claude`, `codex` | **Finding:** Divergent gate numbering (e.g., `EG-S00` vs `EG-SI-000`). <br>**Suggested Edit:** Use the `EG-Sxxx` format proposed by `claude` to keep namespaces distinct from Striatum-specific `EG-xxx` gates, while adopting the descriptive categories from `codex`. |
| **R-005** | First Non-AI Chat Adapter | `claude`, `codex` | **Finding:** Different recommendations for the first non-AI adapter milestone. <br>**Suggested Edit:** Recommend `mbox` as the first milestone given its stability and the operator's end-to-end control, per `claude`'s rationale (§ 9, Q5). |

---

## 6. Verdict

**Verdict:** `accept_with_findings`

The three drafts plus the prior-art dossier constitute a high-quality candidate package for synthesis. The convergence on the "Source Contract" discipline is a significant architectural win. Synthesis should proceed by merging the projection families and resolving the minor policy tensions identified in the Findings Ledger.

---
*Lane: gemini*
*Role: reviewer*
