# RFC 0030 Public-Dataset Entity Grounding Final Review

author: reviewer-claude-opus-002

Status: final_review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

Lens: audit the revised RFC 0030 against the findings ledger, the
revision synthesis, and the revision handoff.

## Acceptance check

- [x] **Every accepted finding addressed in handoff.** Walked the
  synthesis's "Accepted findings" disposition (all 30) against the
  handoff's "Findings addressed" table. Each ledger entry maps to at
  least one Edit number; spot-checks of L001 (code-side enforcement),
  L002 (snapshot hash), L004 (D-H rewrite), L007 (D-D append-only)
  confirm the change landed in the RFC text.
- [x] **Every D-A..D-H position reflected in RFC.** Each section of
  RFC 0030's design space now opens with "Position (synthesis
  2026-05-09)" or equivalent and contains the prescribed text. D-H
  is the largest single change and is materially rewritten.
- [x] **Every Q1..Q7 position reflected in RFC.** "§ Open questions
  for the design loop" was retitled "§ Open questions, resolved";
  each Q1-Q7 carries the synthesis position. Q4's
  `private_aliases` schema sketch made it through.
- [x] **No new design choices snuck in.** Walked the revised RFC for
  text not traceable to either the prior draft or a synthesis
  position. None found. The author obeyed the synthesis discipline
  ("do not introduce new design choices not listed in this synthesis").
- [x] **Five non-negotiable constraints preserved verbatim.** § Non-
  negotiable constraints lists the same five bullets in the same
  order with the same wording as the prior draft. The additions are
  enforcement (Code-side enforcement subsection) and locking
  (DECISION_LOG paragraph), not modifications to the constraints
  themselves.
- [x] **Decision refs / phase refs accurate.** Front-matter Decision
  refs lists D020/D044/D068/D076/D080 explicitly with one-line
  expansions. Phase refs unchanged (PHASE-0003 / PHASE-0004). Context
  entry expanded to include RFC 0018.
- [x] **Promotion path intact.** Step 3 still requires a 100-segment
  bench (now correctly framed as sanity precondition, not
  promotion gate); step 5 still requires running grounded re-extraction
  on the consolidated corpus; step 6 still records outcome in
  DECISION_LOG. The path is the same; step 4 is now four sub-steps
  rather than three (per L029 / cost_adversary:C008).

## Findings

### FR001 - DECISION_LOG entry for locked non-negotiables is operator-only carryover (intentional)
Severity: minor
Source: RFC § Non-negotiable constraints / Locked in DECISION_LOG;
REVISION_HANDOFF Residual risk
Rationale: The RFC commits to promoting the five non-negotiables to
a new `D###` entry on RFC acceptance. apply_findings did not write
to `DECISION_LOG.md` because the workflow forbids it (write_scope
forbidden_paths includes DECISION_LOG.md). This is correct behavior
— synthesis recognized the carryover and the handoff records it.
The risk is that the operator forgets to apply the lock; the RFC's
own text now creates a paper trail that makes that omission visible.

### FR002 - Spec-time carryovers are clearly named
Severity: nit
Source: REVISION_HANDOFF § Open carryover for spec
Rationale: The handoff names six spec-time obligations (argparse
shapes, fixture strategy, test matrix, grounding-bench automation,
onboarding command, D### allocation). Each is reasonable and
appropriate to defer to the spec. The spec-authoring run will
inherit a clear todo list.

### FR003 - D-H rewrite quality is unusually high for an apply-findings pass
Severity: nit
Source: RFC § D-H
Rationale: D-H was the largest single change required (eval_adversary's
five blocking findings collapsed into one section rewrite). The
rewrite preserves all five blocker fixes (three-arm bench, paired
metric, pre-registered decision rule, sample size with power
derivation, independent secondary signal) and adds an honest cost
statement. This is the most consequential edit in the run and it
landed cleanly.

### FR004 - The "iteration cost" paragraph in promotion path step 4 is honest in a way the prior draft was not
Severity: nit
Source: RFC § Promotion path step 4 closing paragraph
Rationale: 6-12 operator-hours plus 2-6 wall-clock compute hours per
bench cycle is a real cost the prior draft elided. Surfacing it
prevents the eval-as-oracle principle from quietly softening to "we
benched once, then never again."

## Remaining risks

1. **DECISION_LOG entry not written.** The operator must apply the
   locked-non-negotiables `D###` entry separately. Until they do,
   the lock is convention rather than reference. (FR001)
2. **Spec-authoring run is the next gate.** The synthesis named
   spec scope; if the spec punts on any of the six spec-time
   obligations, that's a spec-loop concern.
3. **Bench has not run.** Even with a clean RFC and a clean spec
   downstream, the D-H bench is the actual oracle. Until Arm B vs
   Arm C produces the predicted false-rate-reduction-with-coverage-
   preservation on the 600-segment slice, the RFC's central
   hypothesis is unverified.
4. **The revision pass did not loop.** The workflow has a
   `final_review needs_revision → apply_findings (max 1)` cycle
   available. This review's verdict is `accept_with_findings`; the
   cycle is unused. If something needs to come back here, the
   operator can bump the cycle counter and re-trigger.

## Recommendation

- [x] **Promote to spec authoring.**
- [ ] Hold for revision.
- [ ] Reject.

The revised RFC is ready for spec promotion. The blocking findings
from eval_adversary and privacy_adversary are addressed in the RFC
text; the privacy posture is now grep-checkable rather than
convention-checkable; the eval methodology is restructured to a
defensible three-arm bench with pre-registered thresholds. Spec
authoring should pick up the six carryovers named in the handoff.

verdict: accept_with_findings
