# RFC 0021 Final Review — Task

Read `RFC_0021_GOLD_SET_SYNTHESIS.md` plus
`RFC_0021_GOLD_SET_FINDINGS_LEDGER.md` and RFC 0021.

The synthesis is the artifact the owner will read to decide whether to accept
or revise RFC 0021. Your job is to audit it: is it supported by the ledger,
does it preserve privacy / append-only / D044 / D069 invariants, and does it
recommend an appropriate next step?

## Audit checklist

1. **Synthesis-to-ledger consistency.** Does every accepted/deferred/rejected
   ledger finding have a reason aligned with the ledger severity?
2. **Recommendation grounding.** Does the recommendation match what the
   findings support?
3. **Privacy invariants.** Does the synthesis preserve the privacy-tier
   carry rule and the no-egress requirement on export?
4. **D044 / D069 invariants.** Does the synthesis preserve the
   advisory-only stance — gold labels do not auto-flip belief status and
   do not gate extraction or consolidation?
5. **Acceptance deltas (if accept-rfc).** Are the migration number,
   BUILD_PHASES insert, and DECISION_LOG entry concrete and consistent
   with the current state of those files?
6. **Implementation readiness.** If acceptance is recommended, are the
   next implementation steps concrete enough to hand to an engineer?
7. **Provenance carry.** Are RFC, decision, and phase references used
   correctly?

## Output

Write to `docs/reviews/rfc0021-rerun-2026-05-13/RFC_0021_GOLD_SET_FINAL_REVIEW.md`:

```md
# RFC 0021 Gold-Set Interview Curation Final Review

Status: final-review
Date: <YYYY-MM-DD>
RFC refs: RFC-0021
Decision refs: ...
Phase refs: ...

## Audit findings

### A001 — <one-line title>
Severity: <blocking | major | minor | nit>
Source: <synthesis section or ledger ID>
Rationale: <one paragraph>

verdict: <accept | accept_with_findings | needs_revision | reject>
```

A `needs_revision` verdict sends the synthesis back once. A `reject` verdict
means the review cycle itself is not trustworthy enough to use.

Do not modify any other file.
