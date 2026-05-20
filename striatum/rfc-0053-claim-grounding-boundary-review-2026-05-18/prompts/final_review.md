# RFC 0053 Final Review -- Task

Audit the completed review package:

- `docs/reviews/rfc0053-claim-grounding-boundary/FINDINGS_LEDGER.md`
- `docs/reviews/rfc0053-claim-grounding-boundary/SYNTHESIS.md`
- `docs/reviews/rfc0053-claim-grounding-boundary/APPLY_HANDOFF.md`
- `docs/rfcs/0053-claim-extraction-grounding-boundary.md`

Check that accepted findings were applied, deferred findings are explicitly
tracked, and the RFC still preserves the network/corpus split while allowing an
internet-search-capable grounding broker under explicit grant.

## Output

Write `docs/reviews/rfc0053-claim-grounding-boundary/FINAL_REVIEW.md`:

```md
# RFC 0053 Claim Grounding Boundary Final Review

Status: final-review
Date: 2026-05-18
Lane: codex_final
Role: final_reviewer
RFC refs: RFC-0053
Decision refs: D020, D090, D094

## Audit Findings

### A001 -- <one-line title>
Severity: <blocking | major | minor | nit>
Source: <synthesis section, ledger ID, or applied file>
Rationale: <one paragraph>

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Do not edit any other file.
