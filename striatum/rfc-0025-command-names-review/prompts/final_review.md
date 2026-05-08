# RFC 0025 Final Review — Task

Read `RFC_0025_COMMAND_NAMES_SYNTHESIS.md` plus
`RFC_0025_COMMAND_NAMES_FINDINGS_LEDGER.md` and RFC 0025.

The synthesis is the artifact the owner will read to decide whether to accept
or revise RFC 0025. Your job is to audit it: is it supported by the ledger,
does it preserve operator safety, and does it recommend an appropriate next
step?

## Audit checklist

1. **Synthesis-to-ledger consistency.** Does every accepted/deferred/rejected
   ledger finding have a reason aligned with the ledger severity?
2. **Recommendation grounding.** Does the recommendation match what the
   findings support?
3. **Fail-closed invariant.** Does the synthesis preserve the key safety
   requirement that a generic `pipeline` command must not perform writes?
4. **Implementation readiness.** If acceptance is recommended, are the next
   implementation steps concrete enough to hand to an engineer?
5. **Provenance carry.** Are RFC, decision, and phase references used
   correctly?

## Output

Write to `docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_FINAL_REVIEW.md`:

```md
# RFC 0025 Command-Names Final Review

Status: final-review
Date: <YYYY-MM-DD>
RFC refs: RFC-0025
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
