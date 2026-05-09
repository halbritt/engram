# Adversarial Eval-as-Oracle Review of RFC 0030

Review `docs/rfcs/0030-public-dataset-entity-grounding.md` § D-H. The RFC's
hypothesis is that public-dataset grounding improves extraction quality;
the proposed primary oracle is operator-false-rate on entity-mismatch
claims (drawn from RFC 0028's failure taxonomy).

Your job: take that oracle apart. The eval-as-oracle principle gives this
dispute final say — if the oracle is gameable or confounded, every
downstream "this works" claim is suspect.

## Lens

1. **Confounders.** What changes between the v8 baseline and the
   grounded run other than grounding itself? Stress:
   - `EXTRACTION_PROMPT_VERSION` bumps per RFC 0017 — could a prompt
     fix masquerade as a grounding win?
   - The candidate-block context inflation could itself improve or
     hurt extraction independently of resolution.
   - Interaction with RFC 0028's `subject_kind_hint` heuristic — does
     enabling grounding effectively double up on the same fix?
2. **Gaming.** Find a way the system could "improve" the metric
   without improving extraction. Examples to probe:
   - The resolver suppresses risky claims (lower false-rate, lower
     recall, no actual quality gain).
   - The candidate set always picks the most popular Wikidata QID,
     which happens to also be the most popular operator default.
   - The metric is gathered through interview UX that nudges
     "true" verdicts on grounded claims.
3. **Sample size.** Is 100 segments large enough to detect a
   meaningful effect on the entity-mismatch class? RFC 0028's
   re-extraction bench used 100 — is it the right ceiling here?
4. **Slice representativeness.** Is the 100-segment slice
   representative of the failure class? Does it over-/under-represent
   entity-rich content?
5. **Negative-result definition.** What does "no improvement, abort"
   look like? What threshold? Decided by whom? With what budget for
   re-design?
6. **Secondary signals.** PHASE-0004 entity-consolidation merge-rate
   is named as a secondary. Stress: grounding feeds external refs into
   consolidation, so the secondary may be polluted by the change
   under test.
7. **Gold-set interaction.** RFC 0021's gold set is operator-curated
   advisory. Will grounding shift the operator's verdict patterns
   enough to destabilize the gold set as an oracle on this question?
8. **Baseline drift.** The "v8 baseline" — what is its provenance,
   and how reproducible is it in May 2026 vs. when the bench is run?

## Output

Write to your packet's expected artifact path. Use this structure:

```md
# RFC 0030 Public-Dataset Entity Grounding Adversarial Eval Review
author: <packet author line>

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Findings

### E001 - <title>
Severity: <blocking | major | minor | nit>
Source: <path:line or section>
Falsification model: <one paragraph: what would constitute proof against?>
Rationale: <paragraph>
Suggested fix: <paragraph>

## Oracle assessment

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Be precise about thresholds, sample sizes, and falsification criteria.
Do not modify the RFC.
