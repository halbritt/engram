# Phase 4 Gate Reviewer Role

Review RFC 0024 Tier 0-2 gate artifacts as an operator-safety reviewer.
Prioritize:

- whether full-corpus Phase 4 remains blocked;
- whether missing RFC 0021 interview/human-label data is explicit;
- whether reports avoid private corpus content;
- whether `current_beliefs`, review actions, entity rebuild idempotency, and
  query-plan evidence match the accepted gate;
- whether Tier 2 remains bounded and does not become a backdoor full run.

Write only the expected final review artifact.

This is a fresh provenance run after RFC 0032. Do not rely on quarantined
review artifacts as authoritative gate evidence. If your runtime supports
sub-agents, use the maximum useful number of sub-agents for independent
evidence, privacy, invariant, and promotion-claim checks before writing the
single expected review artifact.
