# RFC 0053 Review -- Task

You are reviewing RFC 0053, the claim-extraction/grounding boundary, and the
current scaffold around it. Your lane objective in the Striatum packet names
the exact focus. Do not broaden beyond that focus except for blocking issues.

## Required Inputs

- `docs/rfcs/0053-claim-extraction-grounding-boundary.md`
- `docs/reviews/rfc0053-claim-grounding-boundary/ADVERSARIAL_SECURITY_REVIEW.md`
- `src/engram/claim_grounding.py`
- `docs/schemas/claim_grounding_request.v1.schema.json`
- `docs/schemas/claim_grounding_response.v1.schema.json`
- `tests/test_claim_grounding.py`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `ROADMAP.md`

## Non-Negotiable Context

- The claim extractor is a corpus-reading process and remains no-egress.
- The grounding broker is expected to have an internet-search-capable mode.
- The broker's search input is `network_grant.search_query`; it can include
  private entity-name text.
- Surrounding raw segment/message/capture text must not cross into the
  network-capable broker.
- The current scaffold validates the contract only; it does not implement an
  internet-search runtime.

## Output

Write your review to the path in your job packet.

Use this structure:

```md
# RFC 0053 Claim Grounding Boundary Review -- <lane>

Status: review
Date: 2026-05-18
Lane: <lane id>
Role: reviewer
RFC refs: RFC-0053
Decision refs: D020, D090, D094

## Findings

### F001 -- <one-line title>
Severity: <blocking | major | minor | nit>
Source: <path>:<line or section>
Rationale: <one paragraph>
Proposed fix: <one paragraph or "none">

## Open Questions

- <questions to resolve before implementation or promotion>

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Do not modify any file outside the path your packet specifies.
