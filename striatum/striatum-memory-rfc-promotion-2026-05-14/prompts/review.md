# Review Prompt

Review the RFC promotion packet produced by this workflow. You are reviewing
recommendation artifacts and the underlying RFC text; do not implement code,
edit the RFC text, edit the recommendation artifacts, edit canonical docs,
or alter Striatum state.

Use a fresh context and the maximum useful number of read-only sub-agents.
Check that:

- each per-RFC recommendation honors local-only/no-cloud/no-telemetry,
  proposal-only posture, immutable raw evidence, rebuildable derived
  projections, provenance, and personal-memory deferral;
- the recommendations are coherent with the four aligned RFCs and with each
  other (no cross-RFC contradictions, no implicit promotion of dependencies);
- residual alignment-ledger items (AL-N007, AL-N008, AL-N010-AL-N015 in
  particular, plus any unresolved AL-N items) are honestly carried forward;
- deferred gates AL-D001 (RFC 0044 hardening / EG-000), AL-D002 (acceptance
  decision), AL-D003 (Level 3 / default-on), and AL-D004 (generated-product
  contract) are honored in the per-RFC recommendations;
- no recommendation silently treats a proposal RFC as accepted.

Write only the expected review artifact. Include:

- verdict: `accept`, `accept_with_findings`, or `needs_revision`;
- blocker findings, if any;
- nonblocking findings and deferred work;
- affected files and evidence paths;
- any operator workflow friction.
