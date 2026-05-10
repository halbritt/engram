# Adversarial Usability Review for Spec 0029

Review `docs/specs/0029-bench-triage-workbench-spec.md` as an adversarial
usability reviewer. Assume the operator is already overloaded and progress is
blocked on their ability to trust or reject benchmark deltas quickly.

Focus on:

1. Does the spec force every primary screen to answer "what changed, why should
   I care, what do I do next"?
2. Are verdict labels obvious enough?
3. Can a tired reviewer accidentally accept risky cases?
4. Does the UI make uncertain cases easy to park and resume?
5. Are incomplete data states clear and actionable?
6. Does "safe to promote" risk false confidence?
7. Are acceptance tests strong enough to catch usability regressions?

Write to:

`docs/reviews/rfc0029-bench-triage-workbench-spec/REVIEW_usability_adversary.md`

Use this structure:

```md
# Spec 0029 Bench Triage Workbench Adversarial Usability Review
author: <packet author line>

Status: review
Date: 2026-05-09
RFC refs: RFC-0029
Spec refs: SPEC-0029
Decision refs: D020, D074, D082
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

Do not modify the spec or implementation files.

