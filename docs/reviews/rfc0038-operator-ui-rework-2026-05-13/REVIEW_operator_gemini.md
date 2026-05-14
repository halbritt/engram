author: operator [self-declared: rfc0038-review-operator-flash-retry]

# Review of RFC 0038: Operator UI Rework

**Date:** 2026-05-13
**Reviewer:** Gemini Operator
**Objective:** Review whether UI language preserves advisory labels, scratch-local bench decisions, future/backlog boundaries, and exact CLI ownership.

---

## Overall Assessment

The `ENGRAM_UI_REWORK_HANDOFF.md` document provides a comprehensive and well-reasoned design for the Engram Operator UI rework. It explicitly addresses the core review objectives regarding the preservation of advisory labels, scratch-local bench decisions, future/backlog boundaries, and exact CLI ownership. The design intent, coupled with detailed screen specifications, component inventory, truthfulness rules, and visual system guidelines, strongly indicates that the proposed UI will uphold the project's foundational mandates for local-first operation, data privacy, and clear communication of state and provenance.

The design is conservative by nature, deliberately avoiding claims that the UI should not make, which is critical for a memory-governance workbench where implicit assertions can be misleading. The emphasis on clarity, auditability, and the explicit demarcation of operational boundaries (e.g., local-only, no network egress, advisory nature of labels) is commendable.

## Specific Findings

### 1. Preservation of Advisory Labels

The design explicitly incorporates mechanisms to ensure advisory labels are preserved and clearly communicated:

-   **Explicit Advisory Messaging:** The truthfulness rules (Section 6.1) mandate that every gold-label summary row on the question page will carry the literal message: "Verdict is an advisory eval input. It does not flip belief status (D044) or gate extraction / consolidation (D069)." This directly addresses the need to clearly articulate the advisory nature of gold labels, preventing any misinterpretation of their impact on production state.
-   **Visual Distinctions:** The "Truthfulness And State Rules" (Section 6) define distinct status tokens and corresponding copy/colors for various states, including `Advisory` for gold labels. This visual differentiation reinforces the advisory nature.
-   **No Auto-Promotion:** The design reiterates that the interview UI must not render `accept` / `reject` / `promote` / `pin` controls (Section 6.1), adhering strictly to D044 and D069, which prevents gold labels from implicitly mutating belief status.

**Finding:** The UI language and design effectively preserve and communicate advisory labels. The explicit messaging and visual cues are well-aligned with the project's principles.

### 2. Preservation of Scratch-Local Bench Decisions

The design for the bench triage workbench is meticulously crafted to ensure that decisions remain scratch-local and do not imply mutation of production data:

-   **Explicit Non-Mutation Claims:** The "Design Intent" (Section 1) clearly states: "The UI never implies that a bench-review decision changes claim, belief, audit, or raw evidence rows. Decisions are framed as scratch-local review evidence (RFC 0029)." This foundational principle guides the entire bench UI design.
-   **Dedicated Scratch Storage:** Review decisions are stored in a small SQLite database (Section 3.1, "Review State"), separate from production Postgres. This architectural choice reinforces the scratch-local nature.
-   **Disabled Strong Decisions:** Section 6.2 mandates that strong decisions (`accept_candidate_change`, `flag_candidate_regression`) must render disabled when the `data_state` is problematic (e.g., `candidate_malformed`, `candidate_missing`). This prevents operators from making authoritative-looking decisions on unreliable data.
-   **Recommendation Readiness Disclaimer:** The readiness chip explicitly avoids the "ok" color for `proposed` / `recommend_promote` states and carries the copy "Scratch-local recommendation; not a gate." (Section 6.2), further reinforcing the non-authoritative nature of bench recommendations.
-   **Persistent Banner:** The literal banner "Bench review decisions do not mutate production data or bypass Phase 4 gates." is rendered on `/` and `/summary` (Section 6.2), serving as a constant reminder of the UI's read-only posture regarding production.

**Finding:** The UI language and design are highly effective in preserving the scratch-local nature of bench decisions. The multiple layers of explicit disclaimers and architectural separation prevent any ambiguity.

### 3. Future/Backlog Boundaries

The design clearly demarcates future and backlog features, preventing the UI from implying their availability or full implementation:

-   **Explicit "Future" Tabs:** Surface tabs include `Entities (future)` rendered with `data-future="true"`, a `not-allowed` cursor, and a tooltip "Phase 4: not yet built" (Section 3.4). This directly signals that the feature is not yet active.
-   **Inert Slots:** A new shared template `_future_slot.html` (Section 3.4 and 5.1) renders labeled disabled cards for future work, which will be replaced by actual implementations in later phases. This provides clear visual placeholders without implying functionality.
-   **Help Modal Disclosure:** The interview help modal explicitly states: "Promotion, acceptance, and entity canonicalization arrive in Phase 4. The interview surface never flips a belief status." (Section 3.4). This manages expectations about the current scope.
-   **Status Token:** The `future / backlog` status token (Section 6) with its corresponding copy and icon clearly flags features that are not yet implemented.

**Finding:** The UI language and design effectively communicate future/backlog boundaries, preventing premature assumptions about system capabilities.

### 4. Exact CLI Ownership

The design ensures that the UI does not usurp CLI ownership for critical actions, but rather guides the operator toward the correct CLI commands:

-   **CLI-Owned Export Paths:** Section 2.8 and 4.8 specify that the web UI never exposes export, history, coverage dashboard, or active-learning toggle. Instead, it provides *help cards* that print the exact CLI command (e.g., `Export is a CLI-owned action: copy and run <command>`). This is a strong mechanism for reinforcing CLI ownership.
-   **Explicit CLI Command Cards:** The `_cli_command_card.html` component (Section 5.1 and 5.3) is designed to display exact CLI commands with a copy-to-clipboard affordance, making it easy for operators to transition to the CLI for these actions.
-   **Save and Quit Behavior:** The `save-and-quit` function (Section 4.7) explicitly discards in-progress rationale (for CLI parity) and provides a banner with the exact CLI resume command.

**Finding:** The UI language and design effectively uphold exact CLI ownership by clearly directing the operator to the command line for specific actions, rather than replicating or abstracting them in the web interface.

## Reviewer Questions / Clarifications

None. The `ENGRAM_UI_REWORK_HANDOFF.md` document is exceptionally thorough and directly addresses all aspects of the review objective.

## Verdict

**Accept**

The RFC 0038 proposal, as detailed in `ENGRAM_UI_REWORK_HANDOFF.md`, comprehensively addresses the review objectives. The design consistently prioritizes truthfulness, clarity, and adherence to Engram's core principles, particularly local-first operation and data integrity. The explicit claims and non-claims about the UI's capabilities, coupled with robust visual and architectural distinctions, ensure that the UI language and behavior will accurately reflect advisory labels, scratch-local bench decisions, future/backlog boundaries, and CLI ownership.

The detailed specifications provide a solid foundation for implementation, and the included acceptance criteria will ensure that the final product aligns with these critical design goals.
