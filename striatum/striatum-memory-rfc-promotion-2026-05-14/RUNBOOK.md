# Striatum Memory RFC Promotion Workflow

This workflow follows the completed Striatum memory RFC alignment workflow
(`docs/reviews/striatum-memory-rfc-alignment-2026-05-14/FINAL_SYNTHESIS.md`).
It is a promotion-recommendation packet only: it does not edit RFC text,
does not record an acceptance decision, and does not authorize
implementation.

Initial parallel lanes (one per RFC):

- RFC 0046 projection/index schema promotion recommendation
- RFC 0047 retrieval augmentation boundary promotion recommendation
- RFC 0048 context injection policy promotion recommendation
- RFC 0049 evaluation gates promotion recommendation

After the four recommendations land, run the independent review fan-out
across `codex` (contract coherence), `claude` (privacy/no-egress boundary),
and `gemini` (operator ergonomics), then the findings ledger and final
synthesis.

The synthesis must name the human decision required to record AL-D002
acceptance in `DECISION_LOG.md`. The workflow does not record that decision
itself.

Deferred prerequisites carried from the alignment ledger:

- `AL-D001` RFC 0044 hardening / EG-000 evidence (gates implementation)
- `AL-D002` recorded acceptance decision (gates promotion as binding)
- `AL-D003` Level 3 / default-on automatic memory (gates routine use)
- `AL-D004` generated-product contract (gates generated-product injection)

Do not use this workflow to promote RFCs, edit RFC text, or implement code.
