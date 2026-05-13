# Adversarial Usability Review for RFC 0029

Review `docs/rfcs/0029-bench-triage-workbench.md` as an adversarial usability
reviewer. Assume the operator is already overloaded and progress is blocked on
their ability to trust or reject benchmark deltas quickly.

Focus on:

1. Does every primary screen answer "what changed, why should I care, what do I
   do next" without forcing memory load?
2. Are verdict labels obvious enough, or do they encode project jargon?
3. Can a tired reviewer accidentally batch-accept risky cases?
4. Does the UI make uncertain cases easier to park and resume?
5. Are shortcuts helpful without becoming required knowledge?
6. Does "safe to promote" risk false confidence?
7. Is the workbench scoped tightly enough to avoid becoming another complex
   dashboard?
8. Are privacy notices actionable rather than decorative?
9. Are acceptance tests strong enough to catch usability regressions such as
   hidden decisions, ambiguous states, and raw-text export mistakes?

Write to:

`docs/reviews/rfc0029-bench-triage-workbench-design-2026-05-13/REVIEW_usability_adversary.md`

Use this structure:

```md
# RFC 0029 Bench Triage Workbench Adversarial Usability Review
author: <packet author line>

Status: review
Date: 2026-05-13
RFC refs: RFC-0029
Decision refs: D020, D074
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Findings

### U001 - <title>
Severity: <blocking | major | minor | nit>
Source: <path:line or section>
Rationale: <paragraph>
Suggested fix: <paragraph>

## Open questions

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Do not modify the RFC or implementation files.
