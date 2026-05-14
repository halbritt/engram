# Findings Ledger Prompt

Normalize the review outputs for the RFC alignment workflow into one ledger.
Do not edit RFCs or canonical docs.

Use read-only sub-agents where useful to verify that findings are not duplicated
and that blocker classifications match the evidence. For each finding include
ID, source review, severity, affected artifact, required action, and whether it
blocks promotion, implementation, routine Striatum use, or only future personal
memory.

Write only the expected ledger artifact and run `git diff --check` for it.

