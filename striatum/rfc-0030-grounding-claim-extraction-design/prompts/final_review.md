# Final Review of RFC 0030 Public-Dataset Entity Grounding

Audit the revised RFC 0030 against the findings ledger, the revision
synthesis, and the revision handoff.

Output:

`docs/reviews/rfc0030-grounding-claim-extraction/FINAL_REVIEW.md`

## Acceptance check

You are deciding whether the revised RFC 0030 is ready for promotion to
a spec. The bar:

1. **Every accepted finding from the synthesis is addressed in the
   handoff.** Walk the synthesis's "Accepted findings" list; confirm
   each shows up under "Changes made" in the handoff.
2. **Every D-A through D-H position from the synthesis is reflected
   in the revised RFC text.** A position recorded in synthesis but
   absent from the RFC is a regression.
3. **No new design choices appear in the RFC that were not in the
   synthesis.** The author should not silently expand scope.
4. **The five non-negotiable constraints are preserved verbatim.** No
   softening of "no live web", "no exfil", "explicit grants",
   "raw-is-sacred", or "snapshot reproducibility".
5. **Decision refs and phase refs in the front-matter remain
   accurate.** No new D### entries unless the synthesis named them.
6. **The promotion path** (design → spec → bench → implementation)
   **survives.** The RFC must still gate implementation behind a
   100-segment bench result.

If any check fails, the verdict is `needs_revision` with the exact
edit you expect.

## Output structure

```md
# RFC 0030 Public-Dataset Entity Grounding Final Review
author: <packet author line>

Status: final_review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Acceptance check
- [ ] Every accepted finding addressed in handoff
- [ ] Every D-A..D-H position reflected in RFC
- [ ] Every Q1..Q7 position reflected in RFC
- [ ] No new design choices snuck in
- [ ] Five non-negotiable constraints preserved verbatim
- [ ] Decision refs / phase refs accurate
- [ ] Promotion path intact

## Findings

### FR001 - <title>
Severity: <blocking | major | minor | nit>
Source: <RFC section or handoff section>
Rationale: <paragraph>

## Remaining risks

## Recommendation
- [ ] Promote to spec authoring
- [ ] Hold for revision
- [ ] Reject

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Do not modify files outside `docs/reviews/rfc0030-grounding-claim-extraction/`.
