# Phase 3 Limit-500 Still-Invalid Problem Review - claude_opus_4_7

Reviewer: claude_opus_4_7
Date: 2026-05-06
Verdict: accept_with_findings

## Summary

The problem description is well scoped, redaction-disciplined, and frames a
real semantic policy question rather than a coding bug. After repairing
model-facing schema rejection, the limit-500 gate now stops on a fully
observable case: a schema-valid response that parses cleanly, fails local
validation across every claim, gets a single repair pass, and still returns
the same redacted null-object shape. The current rule "all-invalid post-repair
-> status=failed" is what halts the run. I accept the artifact and recommend a
hybrid policy (Option C) - convert to `extracted` with `claim_count = 0` only
when the failure is fully diagnosed, redacted, and counted by the dropped-claim
gate; preserve hard failure for any unauditable path. Several findings below
tighten what "fully diagnosed" means, separate "clean zero" from "accounted
zero" downstream, and call out that the 15.7% partial drop rate is a real risk
signal that the quality gate must enforce.

## Findings

### F1 - major: define "fully diagnosed" precisely before adopting Option B or C

The decision text references "fully parsed, fully redacted, all-invalid" and
"fully diagnosed model weakness," but the problem description does not
enumerate the predicate that flips an extraction from `failed` to `extracted`
zero-claim. Without this, the policy is prompt-shaped, not code-shaped.

Affected section: "Candidate Policies" -> Option B and Option C.

Proposed fix: have the repair spec make the precondition set explicit. At
minimum:

- model response parsed without a JSON or schema-validation error;
- every entry in `dropped_claims` carries a known reason from a closed
  enumeration;
- every drop preserves the redacted object-shape diagnostics: predicate,
  stability class, object_text type, object_json type, evidence message count,
  and error class string;
- every drop contains no raw corpus text;
- `validation_repair.attempted = true` and `validation_repair.result` is in a
  closed set including `still_invalid`;
- prior and final dropped-claim error class counts are populated;
- final `claim_count == 0` after repair.

Any miss means status stays `failed`. This is the difference between Option C
and "Option B with implicit assumptions."

### F2 - major: distinguish clean-zero from accounted-zero downstream

Under Option B/C, two extraction rows can both have `claim_count = 0` but mean
different things: the model produced nothing supported, or every produced
claim was dropped after diagnostic accounting. Today's row shape collapses
these. Consumers such as the consolidator, gold-set tooling, regression diffs,
and dropped-claim quality reporting need to tell them apart without
re-deriving from `raw_payload` each time.

Affected section: Option B "Risks" notes this but does not require a fix.

Proposed fix: the spec must require an explicit indicator on the extraction
row, for example a sub-status, `extraction_kind` in
`{clean_zero, accounted_zero, populated}`, or a queryable derived flag
`dropped_claim_count > 0 AND claim_count = 0`. Document the invariant and add
a constraint or schema-doc note.

### F3 - major: the quality gate must be the safety net, not just an observation

The partial expanded dropped-claim rate at stop is 227 / 1448, about 15.7%,
above the 10% same-bound threshold. Under Option A, the run never reached the
gate because it died first; under Option C the run will progress further and
the gate becomes the binding constraint. If the gate is not reliably computed,
including numerator and denominator definitions, prior plus final drop
accounting, and deduplication if drops are recounted across repair attempts,
the policy switch can normalize real loss.

Affected section: Review Question 7 plus "Required Verification After Any
Repair."

Proposed fix: the spec must pin gate semantics: numerator =
inserted_claims_dropped_by_validation + validation_repair_prior_drops +
validation_repair_final_drops with an explicit dedup rule; denominator =
inserted_claims + numerator; threshold = 10% over the selected scope at
same-bound rerun. Acceptance must require both the no-failures condition and
the gate.

### F4 - moderate: failure_kind `trigger_violation` is misleading for this class

The failed v7 row records `failure_kind: trigger_violation`, but the failure is
local pre-validation across all drafts after a redacted repair attempt, not a
trigger violation. Operators reading progress rows will mis-classify this
incident class.

Affected section: "Failed v7 extraction row" diagnostics.

Proposed fix: the spec should add or rename a failure kind such as
`local_validation_failed_post_repair` and describe how `trigger_violation`
should be reserved. Mention this even if the policy switches to Option C,
since rare hard-failure cases will keep producing this row class and need
correct labeling.

### F5 - moderate: prior-version evidence is not addressed

The schema-rejection rerun report records that the prior v5 prompt produced
7 claims for segment `1b8a501f-...`, while v7 yields zero accounted-zero. That
is direct evidence the segment is extractable and that the v7 prompt/schema
regression on this shape is reproducible, not a model fluke. The problem
description should not relitigate the prompt, but it should acknowledge this
signal so the spec authors do not write a policy that papers over a recoverable
prompt issue.

Affected section: "Current Evidence" / "Redacted Failure Shape."

Proposed fix: add a short subsection noting the v5 to v7 regression on this
segment shape, framing Option C not as the only mitigation but as the
operational floor while v7 prompt iteration continues. This lowers the risk of
"policy fix masks prompt fix."

### F6 - moderate: stop semantics on first hard failure are conflated with policy choice

Even under Option A, the run stopped at the first hard extraction failure
rather than continuing and counting failures against an extractor failure
budget. The problem description treats "halts the whole pipeline" as inherent
to Option A, but the stop policy is its own knob.

Affected section: Option A "Risks" first bullet.

Proposed fix: the spec must state explicitly whether to keep first-failure
stops behavior or move to a small failure budget. If Option C is chosen, this
is largely moot; if Option A is chosen, the spec must address it because the
brittleness is half stop-policy and half classification.

### F7 - minor: validation-repair retry depth is unspecified

The current pipeline performs a single repair attempt. The problem description
does not commit to retaining a one-shot repair, increasing depth, or making
depth configurable. Under Option A this matters most; under Option C it still
affects gate inputs.

Proposed fix: spec should pin repair depth to one, matching current behavior,
or justify any change. The gate must count drops once per draft regardless of
repair depth.

### F8 - minor: idempotence under requeue is not explicit

For the targeted rerun verification on `06dd9815-...`, the spec needs to state
the expected end-state row shape, such as `status = extracted`, `claim_count =
0`, dropped-claim count, and `validation_repair.attempted = true`, so the
verifier can assert it. Otherwise "rerun passes" is operationally vague.

## Recommended Policy

Option C (hybrid), with the precondition set from F1.

Rationale: Option A is too brittle. We already have evidence that prompt-based
repair does not reliably force `{"claims":[]}`, so retrying that approach at
full-corpus scale will keep stalling on persistent shapes. Option B is correct
in spirit but, as written, makes the conversion implicit, which risks
normalizing unauditable failures such as parse errors, missing drop
diagnostics, or redaction drift. Option C preserves Option A's safety on
unauditable problems while moving fully observable, fully accounted model
weakness onto the dropped-claim quality gate where it belongs. The 10% gate
plus the new accounted-zero accounting is the right place to expose cumulative
loss; an operational halt on a single redacted row is not.

The policy is acceptable only if F1, F2, and F3 are addressed in the repair
spec.

## Required Spec Criteria

1. Enumerate the precondition set from F1 explicitly. State that any miss
   leaves the row at `status = failed`.
2. Define the row-level distinction between clean-zero and accounted-zero (F2).
   Specify the field, its closed value set, and how it is set on insert.
3. Pin the dropped-claim quality-gate formula (F3): numerator, denominator,
   dedup rule across repair attempts, selected-scope same-bound scope, 10%
   threshold, and edge behavior.
4. State that the policy applies only when post-repair `claim_count == 0`;
   mixed-claim extractions continue to insert valid claims and account drops
   as today.
5. Specify failure-kind taxonomy updates (F4) so retained hard failures get a
   precise label.
6. Pin validation-repair depth (F7) and idempotent rerun row-shape contract
   (F8).
7. Specify `raw_payload` retention: prior drop shapes, final drop shapes,
   repair result, and error class counts; no raw corpus content.
8. State the consolidator contract for accounted-zero rows: treated as zero
   contribution, not as a failure; consolidator progress rows must not log
   skip-due-to-extraction-failure for these rows.
9. State migration/backfill behavior for the existing failed row on segment
   `1b8a501f-...` after the policy change: requeue, re-extract, and expected
   accounted-zero or non-zero result if repair finally succeeds.
10. Reaffirm RFC 0013 redaction discipline at every persisted layer the policy
    touches.

## Required Tests And Gates

Tests to add or change:

- unit: fully diagnosed still-invalid extraction -> `status = extracted`,
  `claim_count = 0`, dropped-claim count matches accounted drops, and
  `extraction_kind = accounted_zero` or chosen field.
- unit: still-invalid with `unknown` drop reason -> `failed`.
- unit: still-invalid with redaction violation in drop diagnostics -> `failed`.
- unit: parse error path -> `failed`.
- unit: schema-rejection path -> `failed`.
- unit: mixed valid + invalid claims -> unchanged behavior; valid claims insert,
  drops account.
- unit: dropped-claim quality-gate computation matches the spec formula and
  dedup rule across repair attempts.
- unit: consolidator over accounted-zero row contributes zero beliefs and does
  not record a skip-due-to-failure progress row.
- existing test that asserts "all-invalid -> failed" must be updated, not
  deleted, with a clear comment pointing at the spec.

Live verification ladder:

1. Focused Phase 3 tests pass.
2. Full test suite passes.
3. No-work gate: `pipeline-3 --limit 0` returns zeros across the board.
4. Requeue and targeted extraction for
   `06dd9815-2298-488a-b544-39a08311dae3` returns the expected end-state row
   shape from F8, with drops persisted.
5. Bounded targeted consolidation for the same conversation returns a
   zero-contribution result without failure progress rows.
6. Same-bound rerun:
   `pipeline-3 --extract-batch-size 5 --consolidate-batch-size 5 --limit 500`
   must pass both gates: zero hard extractor/consolidator failures and expanded
   dropped-claim rate at or below 10%.
7. Pinned ready marker only after step 6 passes both gates.

The same-bound rerun must produce a fresh redacted run report and marker. The
prior 15.7% number is a risk signal, not final evidence.

## Redaction Review

The problem description complies with RFC 0013. It exposes only commands,
status values, ids as diagnostic handles, predicate name (`has_name`),
stability class (`identity`), object-shape types (`null` / `null`), error
class strings, and aggregate counts such as claims, drops, message count,
summary length, and content length. No raw text, no completions, no claim
values, no titles, no private names, no corpus prose. One borderline element,
content and summary lengths, is fact-of-shape, not content, and is acceptable.
No redaction drift observed in this artifact.

Spec authors should preserve the same boundary; in particular, error class
strings should remain human-meaningful but content-free.

## Open Questions

1. Under Option C, should consolidation skip accounted-zero rows entirely, or
   treat them as zero-contribution inputs? My recommendation is the latter for
   auditability, but it interacts with progress-ledger semantics and is worth
   confirming.
2. Does the 10% dropped-claim threshold need re-tuning once previously
   hard-failed cases become accounted drops? Recommendation: hold at 10% for
   the same-bound limit-500 evidence run, then revisit with empirical data.
3. Should there be a per-conversation circuit-breaker, such as one auto-requeue
   before final classification, separate from same-row repair? Out of scope
   here, but the still-invalid evidence suggests it could be cheap insurance.
4. Should `failure_kind = trigger_violation` be deprecated for this class,
   renamed, or left and complemented by a new
   `local_validation_failed_post_repair` value? This is a small but
   operator-visible call.
5. Is the v5-to-v7 regression on this segment shape something the prompt/schema
   team should fix in parallel, or is policy alone enough? Owner judgment.
6. Should the human checkpoint at the bottom of the problem description be
   enacted before the repair spec is drafted, given that this is a semantic
   policy decision and Codex synthesis benefits from a written owner choice
   rather than averaging Claude/Gemini?
