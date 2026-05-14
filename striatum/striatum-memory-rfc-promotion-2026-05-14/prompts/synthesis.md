# Final Synthesis Prompt

Synthesize the RFC promotion workflow ledger into an operator-ready closeout.
Do not promote RFCs, authorize implementation, or alter Striatum state.

Use read-only sub-agents where useful to classify per-RFC dispositions. The
synthesis must state:

- per-RFC promotion disposition for RFC 0046, RFC 0047, RFC 0048, and
  RFC 0049 (`ready_for_promotion`, `ready_with_findings`,
  `blocked_on_deferred`, or `needs_revision`);
- the specific human decision required (typically an AL-D002 acceptance
  entry in `DECISION_LOG.md`) and what evidence the human would cite;
- the deferred AL-D001 RFC 0044 hardening / EG-000 evidence path that must
  precede implementation handoff;
- which findings remain carried forward as nonblocking or deferred,
  including generated-product (AL-D004) and Level 3 default-on (AL-D003)
  blocks;
- the next operator's recommended starting point if the promotion packet
  is accepted, and a separate recommended starting point if it is not.

Write only the expected synthesis artifact and run `git diff --check` for it.
