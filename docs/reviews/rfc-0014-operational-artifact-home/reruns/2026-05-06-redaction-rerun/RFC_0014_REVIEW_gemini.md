# RFC 0014 Review

Author: reviewer / gemini / Gemini 3.1 Pro Preview / review_gemini

## Findings

1. **Blocking: Unresolved Path Layout Decisions (Consistency / Workflow-State Risk)**
   The RFC leaves critical structural details in the "Open Questions" section,
   such as the exact root name (`docs/operations/`, `docs/ops/`, or
   `docs/operational/`) and the scoping strategy (`phase3-postbuild` vs
   `postbuild/phase3`). Because this RFC's primary purpose is to define a
   stable layout for future agent implementation, these path layouts must be
   explicitly chosen. Leaving them as open questions prevents a clean handoff to
   an implementation agent.

2. **Blocking: Contradiction on File Separation (Consistency Risk)**
   The "Open Questions" section asks whether reports and markers should be
   separate files, yet the "Proposal" section explicitly defines a layout with
   separate `reports/` and `markers/` directories. This ambiguity creates a
   conflict in the specification. The RFC must commit to one approach before
   acceptance.

3. **Moderate: Retrospective Modification of Accepted RFC 0013 (Process Risk)**
   Step 1 of the "Migration Plan If Accepted" dictates: "Update RFC 0013 to
   point committed operational reports and markers to `docs/operations/`".
   Accepted RFCs should act as immutable point-in-time architectural records.
   RFC 0014 should explicitly supersede the layout definitions in RFC 0013
   rather than prescribing inline edits to an accepted document, unless
   clarifying that the update is solely adding a deprecation cross-reference.

4. **Minor: Legacy Marker Compatibility Specificity (Process Ergonomics)**
   Step 4 of the Migration Plan ("Add compatibility handling for the existing
   legacy path") lacks implementation specificity. The RFC should explicitly
   state that tooling like `scripts/phase3_tmux_agents.sh` must scan both the
   new operations path and the legacy
   `docs/reviews/<area>/postbuild/markers/` paths, computing the newest marker
   state across both locations using the precedence rules from RFC 0013
   Section 5.

## Evaluation Summary

- **Separation of state:** The RFC cleanly separates operational run state
  (`docs/operations/`) from model review feedback (`docs/reviews/`).
- **Precedence and redaction:** RFC 0013 marker precedence and redaction rules
  survive intact. The RFC explicitly copies and enforces these constraints.
- **Migration plan specificity:** Requires more specificity regarding
  compatibility handling (Finding 4) and finalized structural decisions
  (Findings 1 and 2) to be a viable implementation prompt.
- **Private corpus content risk:** No new privacy risk is introduced. The RFC
  maintains the strict prohibition on committing private corpus content,
  preserving the safety constraints established in RFC 0013.
- **Agent validation target:** Once the open questions are resolved and the
  structural contradictions are fixed, this RFC represents an excellent,
  bounded target for `agent_runner` validation.

Verdict: needs_revision
