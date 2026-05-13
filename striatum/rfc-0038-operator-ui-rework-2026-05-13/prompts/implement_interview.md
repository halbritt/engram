# Implement RFC 0038 Interview UI Slice

Read first:

- `AGENTS.md`
- `ENGRAM_UI_REWORK_HANDOFF.md`
- `docs/rfcs/0038-operator-ui-rework.md`
- `docs/specs/0027-interview-web-ui-spec.md`
- `docs/rfcs/0028-predicate-intent-surfacing.md`

Use the maximum useful number of native sub-agents internally if your runtime
supports them. Keep ownership inside the interview slice.

Implement only the gold-set interview UI rework:

- Update interview templates/static and only the route/render helpers needed
  for the handoff's session list, question page, evidence/message reveal,
  rationale capture, status chips, predicate intent, warning, and responsive
  behavior.
- Preserve closed-session guards, Tier 1 evidence guards, exact Origin/Sec-Fetch
  posture, and CLI parity.
- Do not change bench-review files.
- Do not add export/history/coverage/active-learning web mutations.

Required artifact:

`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/IMPLEMENT_INTERVIEW_HANDOFF.md`

Use this shape:

```md
# RFC 0038 Interview UI Handoff
author: <packet author line>

Status: implemented
Date: 2026-05-13
RFC refs: RFC-0038, RFC-0027, RFC-0028

## Summary
## Files Changed
## Interview Flow Changes
## Truthfulness / Guard Preservation
## Tests Run
## Residual Risk
```
