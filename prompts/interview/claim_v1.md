---
template_id: interview.claim.v1
template_version: interview.claim.v1.d079.initial
target_kind: claim
---

# Interview question — claim

Subject: {subject_text}
Predicate: {predicate}
Object: {object_text_or_json}

Stability class: {stability_class}
Confidence: {confidence}
Evidence: {evidence_count} message(s) over {evidence_date_span}

Q: Is this an accurate paraphrase of your situation at the time of the cited
evidence?

Pick one verdict and (optionally) one short rationale sentence.

  [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]

Verdict legend:
- true: claim is correct about the world at the cited evidence time.
- false: claim is wrong about the world at the cited evidence time.
- stale: was true at evidence time, no longer true.
- unsupported: evidence does not establish the claim, regardless of world truth.
- unsure: cannot rule.
- skip: ask me later (cooldown-free; will re-surface in the next session).
