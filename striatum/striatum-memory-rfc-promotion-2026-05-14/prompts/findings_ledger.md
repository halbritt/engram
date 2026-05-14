# Findings Ledger Prompt

Normalize the review outputs for the RFC promotion workflow into one ledger.
Do not edit RFCs, recommendation handoffs, or canonical docs.

Use read-only sub-agents where useful to verify findings are not duplicated
and that promotion dispositions match the evidence. For each finding include
ID, source review, severity, affected RFC, required action, and whether it
blocks promotion of the affected RFC, implementation, routine Striatum use,
or only future personal/generated memory.

Also produce a per-RFC summary table naming the promotion disposition
(`ready_for_promotion`, `ready_with_findings`, `blocked_on_deferred`, or
`needs_revision`) for RFC 0046, RFC 0047, RFC 0048, and RFC 0049 with the
deferred AL-D001/AL-D002/AL-D003/AL-D004 gates explicitly listed.

Write only the expected ledger artifact and run `git diff --check` for it.
