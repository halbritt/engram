# Apply RFC 0028 Review Findings

Read `FINDINGS_LEDGER.md`, `REVISION_SYNTHESIS.md`, and the current diff.
Apply accepted or accepted-with-modification findings only. Do not apply
deferred or rejected findings.

This is a fresh provenance run after RFC 0032. Do not rely on quarantined
review artifacts as authoritative evidence. If your runtime supports
sub-agents, use the maximum useful number of sub-agents for independent
implementation, test, and documentation checks, with disjoint file ownership.

Update tests and docs as needed, rerun focused checks, and write
`docs/reviews/rfc0028-predicate-intent-promotion-2026-05-13/REVISION_HANDOFF.md`
with the exact lowercase `author:` line from the work packet.

If the synthesis says no code change is needed, write the handoff explaining
that and record the verification commands run.
