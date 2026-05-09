# Adversarial Usability Review of RFC 0030

Review `docs/rfcs/0030-public-dataset-entity-grounding.md` from the perspective
of an operator running engram on their own laptop, who has many other things
to manage.

Focus on places where this proposal will impose ongoing operator burden, hide
state, or invite mistakes. Be concrete; cite specific RFC text.

## Lens

1. **Grants you forget you have.** A persistent grant model with no
   periodic re-confirmation: when does an operator notice they granted
   role X dataset Y last month? Could they accidentally extend grants
   across machines via dotfile sync?
2. **Snapshot drift you can't see.** The RFC says snapshots are
   operator-curated. What surface tells the operator their active
   snapshot is six months stale? Does the system warn before extraction,
   or after?
3. **Silent downgrade.** D-7 in open questions recommends silent
   downgrade if grants are missing. Is silent the right default? When
   does the operator find out grounding stopped working?
4. **Candidate-set ambiguity at the interview UI.** D-C recommends
   attaching the full candidate set with confidences. The RFC 0027
   interview is the disambiguation surface. Does the proposal specify
   how the interview presents candidates without overwhelming the
   operator with choices?
5. **Naming.** Are dataset names ("wikidata", "geonames") and CLI verbs
   ("grants list", "grounding snapshot") legible to a tired operator,
   or do they encode jargon?
6. **Reversibility.** If grounding goes wrong, what is the operator's
   undo button? "Re-extract under no-grant configuration" is what
   the RFC names — is that ergonomic, or a multi-hour CLI dance?
7. **First-run friction.** What is the new operator's path from
   `engram install` to first grounded extraction? How many decisions
   do they have to make before getting value?

## Output

Write to your packet's expected artifact path. Use this structure:

```md
# RFC 0030 Public-Dataset Entity Grounding Adversarial Usability Review
author: <packet author line>

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Findings

### U001 - <title>
Severity: <blocking | major | minor | nit>
Source: <path:line or section>
Rationale: <paragraph>
Suggested fix: <paragraph>

## Open questions

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Do not modify the RFC. Do not include private corpus excerpts.
