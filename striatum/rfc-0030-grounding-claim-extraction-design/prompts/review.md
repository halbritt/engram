# Review RFC 0030 Public-Dataset Entity Grounding

Review `docs/rfcs/0030-public-dataset-entity-grounding.md` against Engram's
local-first principles, the non-negotiable constraints stated in the RFC, and
the lens specified in your job packet objective.

## Checklist

1. Are the five non-negotiable constraints (no live web at extraction time;
   no corpus exfil; explicit grants; raw-is-sacred; snapshot reproducibility)
   sufficient and unambiguous? Can each be enforced by code, or do any rely
   on convention?
2. Are the eight design choices (D-A through D-H) presented with enough
   information to decide between options, or do some need more analysis
   before the loop can converge?
3. Does the recommended seed for each design choice align with prior
   Engram decisions (D020 LLM-local-only, D044 gold-set advisory, D068
   artifact-id model, D076 32k context budget, D080 RFC 0027 promotion)?
4. Does the proposal materially address the failure class motivating it
   (RFC 0028's entity-mismatch operator-false rationales)?
5. Is the scope vs. out-of-scope boundary defensible? Are private-entity
   resolution and remote-LLM calls correctly excluded?
6. Are the seven open questions answerable by the review loop, or do some
   require operator-only decisions (storage budget, dataset choice)?
7. Is the promotion path realistic — design review → spec → 100-segment
   bench → implementation? What gates each step?
8. Are there conflicts with RFC 0011 (claims/beliefs schema), RFC 0017
   (prompt versioning), RFC 0018 (audit cascade), RFC 0028 (predicate
   intent / subject-kind hint), or any decision in `DECISION_LOG.md`?
9. Is the `EXTRACTION_PROMPT_VERSION` bump path stated correctly per
   RFC 0017? Does it preserve the immutability of prior prompts?
10. Are there hidden assumptions about model behavior (e.g., the LLM will
    use candidate hints correctly) that need empirical validation before
    promotion?

## Output

Write to the exact path in your packet. Use this structure:

```md
# RFC 0030 Public-Dataset Entity Grounding Review - <lane>
author: <packet author line>

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Findings

### F001 - <title>
Severity: <blocking | major | minor | nit>
Source: <path:line or section>
Rationale: <paragraph>

## Open questions

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Do not modify files outside the path specified by the job packet. Do not
include private corpus excerpts, raw segment text, or raw claim text.
