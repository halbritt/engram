---
template_id: interview.belief.v1
template_version: interview.belief.v1.d079.initial
target_kind: belief
---

# Interview question — belief

Subject: {subject_text}
Predicate: {predicate}
Object: {object_text_or_json}

Stability class: {stability_class}
Confidence: {confidence}
Belief status: {belief_status}
Valid from: {valid_from}
Valid to: {valid_to}
Evidence: {evidence_count} message(s) over {evidence_date_span}

Q: Is this currently true?

Pick one verdict and (optionally) one short rationale sentence.

  [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]

Verdict legend:
- true: belief is currently true about the world.
- false: belief is wrong about the world right now.
- stale: was true between valid_from and valid_to, no longer true.
- unsupported: evidence does not establish the belief, regardless of world truth.
- unsure: cannot rule.
- skip: ask me later (cooldown-free; will re-surface in the next session).
