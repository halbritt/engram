# RFC 0030 Spec Authoring Runbook

## Objective

Author Spec 0030 as the implementation contract for the revised
RFC 0030 (post-design-review). Run an 8-lane review on the spec.
Produce a final verdict that gates promotion to bench + implementation.

## Process

1. `draft_spec` writes `docs/specs/0030-public-dataset-entity-grounding-spec.md`
   per the prompt's required-sections list.
2. 8 reviews run in parallel (3 generic + 5 adversarial).
3. Findings ledger normalizes; synthesis takes positions; apply
   revises the spec; final review gates promotion.

## Privacy

No private corpus excerpts in any tracked artifact. Sanitize all
example fixtures. Code-side enforcement chokepoints in spec must be
grep-checkable, not just stated.

## Completion criteria

- Every RFC 0030 "must" clause has a spec contract.
- Every spec contract has a test name.
- Spec final review reaches `accept` or `accept_with_findings`.
- RFC 0030 status flips to `promoted`; spec link present.
