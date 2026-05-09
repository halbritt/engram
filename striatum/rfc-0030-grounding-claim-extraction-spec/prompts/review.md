# Review Spec 0030

Review `docs/specs/0030-public-dataset-entity-grounding-spec.md` against
the revised RFC 0030 and the design-review synthesis. Apply the lens
named in your packet objective.

## Universal checklist (all reviewers)

1. Does every RFC 0030 "must" clause have a spec contract?
2. Does every spec contract have a test name?
3. Are the five non-negotiable constraints enforced by named code
   modules with concrete chokepoints (not just convention)?
4. Are CLI argparse shapes exact (subparser names, flag names, types,
   defaults, exit codes)?
5. Are migration steps idempotent and labeled with `CONCURRENTLY` where
   needed?
6. Are budget enforcement defaults spelled out (storage 10/12 GB,
   latency 100 ms / 2x corpus, candidate-block 1000/8000 tokens,
   cache 100k entries)?
7. Are the three bench arms, paired metric, pre-registered decision
   rule, and sample sizes preserved from the synthesis?
8. Are spec-time carryovers from the design synthesis (argparse
   shapes, fixture strategy, test matrix, grounding-bench
   automation, onboarding walkthrough) actually present?

## Output

Write to your packet's expected artifact path. Same structure as the
design-review reviewer prompt: F### findings with severity, source,
rationale, and a verdict line.

Do not modify the spec or RFC.
