# Phase 3 Limit-500 Null-Object Repair Spec Review (Claude Opus 4.7)

Date: 2026-05-06

Reviewer: Claude Opus 4.7

Subject:
`docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_2026_05_06.md`

Verdict: `accept_with_findings`

This review follows the RFC 0013 redaction boundary. It contains commands,
counts, ids, status values, predicate names, file paths, and aggregate error
classes only. It does not include raw message text, segment text, prompt
payloads, model completions, conversation titles, claim values, belief values,
private names, or corpus-derived prose summaries.

## Scope

Reviewed files:

- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_SPEC_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_LIMIT500_FAILURE_FINDINGS_2026_05_06.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT500_2026_05_06.md`
- `src/engram/extractor.py`
- `tests/test_phase3_claims_beliefs.py`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/process/phase-3-agent-runbook.md`

The spec was not modified. Source files were not modified.

## Summary

The spec is consistent with the limit-500 failure findings, preserves strict
exact-one object-channel validation, addresses the empty-repair hiding risk
through the expanded dropped-claim gate, and routes any backend limitation back
to prompt + Python validation as authoritative enforcement. The acceptance gate
is appropriately constraining and prevents premature full-corpus expansion.

The spec is acceptable to implement. The findings below recommend tightening
several execution details that affect implementability, test coverage clarity,
and marker compliance with RFC 0013 section 5. None block implementation; all should
be resolved before implementation begins or as part of synthesis.

## Answers To Review Questions

1. **Strict exact-one validation preserved.** The Non-Goals explicitly forbid
   relaxing the exact-one validator (`src/engram/extractor.py:1216`). R5
   preserves salvage and failure semantics. R3 prompt rules and R4 repair
   feedback both reinforce, never bypass, the exact-one rule.

2. **Hidden contract failures behind empty repairs are addressed.** R5 records
   prior drops on accepted-empty repairs, R6 keeps the expanded dropped-claim
   gate counting validation-repair prior drops, and the Open Risks section
   explicitly names this hiding mode. The existing
   `retry_after_trigger_violation` already records `prior_dropped_count` and
   `prior_dropped_claims` in `parse_metadata.validation_repair`
   (`src/engram/extractor.py:826-888`), so the gate has a real numerator.

3. **Backend limitation handling is structurally safe but underspecified.**
   See F2.

4. **Null-object-sweep feedback is specific and redacted, with one minor
   gap.** See F3.

5. **Test requirements cover the known failure mode but are partly redundant
   with existing tests and miss one new behavior.** See F4.

6. **Same-bound acceptance gate prevents premature expansion.** The gate
   requires zero failed extractions, zero missing latest extractions, zero
   consolidation skips, zero failed extractor or consolidator progress rows
   in scope, zero orphan-claim active beliefs, and an expanded dropped-claim
   gate at or below 10%. This is consistent with the RFC 0013 default
   blockers and stricter than the minimum.

7. **Operational supersession steps are mostly correct but the marker schema
   is not pinned.** See F5.

## Findings

### F1 - Major: R2 does not name the JSON Schema construct or the support-detection path

`src/engram/extractor.py:267-319` constructs a strict JSON schema for the
extraction request and already has a relaxed-schema fallback path triggered
through `is_schema_construction_error`
(`src/engram/extractor.py:1062-1069`). The spec says the schema should
"enforce the exact-one object-channel shape at the claim object level if the
local JSON-schema backend supports it" without specifying:

- which JSON Schema construct will be used (`oneOf` over the two object
  channels, `if/then/else`, branched `properties`, or a discriminator);
- how backend support is verified (startup probe, schema-construction error
  catch, dedicated integration test, or live extraction smoke);
- whether the existing `is_schema_construction_error` /
  `relaxed_schema_only` fallback path applies to the new construct, and if
  so whether the relaxed schema must continue to enforce exact-one through
  some other shape, or whether enforcement strictly degrades to
  prompt-plus-Python only.

The spec's contingency clause is correct in spirit, but without a named
construct and a named detection point the implementation could easily land
in any of three different states. Recommend the spec require:

- a single named construct (the most likely choice is `oneOf` at
  `properties.claims.items` level, branching on
  `object_text`/`object_json` types) so reviewers can audit it;
- an offline unit assertion that the generated schema contains the chosen
  construct under non-relaxed mode;
- explicit text on whether `relaxed_schema=True` retains or drops the
  exact-one construct, since the relaxed path is currently used for
  message-id enum-too-large failures and could be triggered by an unrelated
  schema-construction error.

Severity: major (implementation correctness).

Required fix: the spec should name the construct, name the support-detection
path, and state the relaxed-schema interaction.

### F2 - Major: backend rejection path interaction with the existing relaxed-schema fallback

If the backend rejects the new construct with an error matching
`is_schema_construction_error` (`grammar`, `schema construction`,
`grammar-state`), the existing fallback path
(`src/engram/extractor.py:641-663`) will retry with `relaxed_schema=True`,
which today only relaxes `evidence_message_ids.items` from `enum` to
`pattern` (`src/engram/extractor.py:272-280`). It does not currently strip
exact-one branching. If R2 adds branching only to the strict schema, the
relaxed path will still be free of branching - fine. If R2 adds branching
to both, the rejection class may flip from message-id-enum errors to
exact-one errors, masking real schema problems and silently weakening the
intended message-id constraint for every request that triggers the
fallback.

Severity: major (schema regression risk).

Required fix: the spec should require that the new exact-one construct
exist only on the strict (non-relaxed) schema, or that a new fallback
class be introduced rather than reusing the existing relaxed-schema path.
A test that exercises both schema generations and asserts which
constraints are present in each is required by R2's "implementation must
make that limitation explicit in tests or comments" clause.

### F3 - Minor: R4 covers full sweeps but not partial sweeps

R4 specifies feedback "when all dropped claims from the first pass share"
the null-null pattern. The limit-500 evidence shows the failure class is
overwhelmingly null-null (807 out of 824 latest final drops; 110 out of 110
validation-repair prior drops), so the "all" condition matches the observed
failure. However, in any future segment where the model emits a mix of
null-null sweep claims plus other validation errors (for example, predicate
requires `object_json`: 15; predicate requires non-empty `object_text`: 2),
R4 will not trigger and the repair feedback will fall back to the existing
aggregate-error-count text, which the failure findings already classify as
insufficient (F2 of `PHASE_3_LIMIT500_FAILURE_FINDINGS_2026_05_06.md`).

Severity: minor (mixed-pattern coverage gap).

Required fix or accept-as-is: either weaken the R4 condition to "majority
of drops share the null-null pattern" with a documented threshold, or
accept the current "all" condition and add a Non-Goal stating that mixed
patterns intentionally degrade to aggregate feedback.

### F4 - Minor: test requirements should distinguish new tests from existing coverage and add one missing assertion

Several listed tests already exist in
`tests/test_phase3_claims_beliefs.py`:

- accepted empty repair: `test_extractor_validation_repair_retry_can_produce_empty_success`
  (`tests/test_phase3_claims_beliefs.py:604-668`);
- still-invalid repair stays failed:
  `test_extractor_validation_repair_still_invalid_remains_failed`
  (`tests/test_phase3_claims_beliefs.py:719-747`);
- failed repair via invalid-JSON in repair attempt:
  `test_extractor_validation_repair_uses_one_attempt_even_with_extra_retries`
  (`tests/test_phase3_claims_beliefs.py:750-786`);
- salvage preservation across repair:
  `test_extractor_validation_repair_preserves_prior_drops_when_valid_claims_survive`
  (`tests/test_phase3_claims_beliefs.py:671-716`);
- predicate enum and message-id schema generation:
  `test_predicate_vocabulary_and_extractor_schema_parity`
  (`tests/test_phase3_claims_beliefs.py:203-223`).

The spec's Test Requirements section reads as if all six items are new,
which can lead an implementer to duplicate or replace existing tests.

In addition, the spec's test list is missing one assertion that would
guard the F2 risk directly: an assertion that the relaxed-schema variant
either retains or deliberately omits the exact-one construct, with the
chosen behavior recorded in code or comment.

Severity: minor (test scope clarity).

Required fix: rewrite Test Requirements to (a) reference the specific
existing tests that already cover items 3, 4, and 5 and state what new
assertions extend them, (b) add an explicit relaxed-vs-strict schema
assertion under item 1, and (c) require a provenance assertion that the
new prompt and request-profile names appear in created
`claim_extractions`, claims, and beliefs derived from the same-bound
rerun.

### F5 - Minor: marker schema for the superseding ready marker is not specified

R7 and the Same-Bound Acceptance Gate require a superseding ready marker,
but the spec does not pin a filename, family, or `supersedes` field. RFC
0013 section 5 requires:

- canonical per-loop filenames in
  `docs/reviews/phase3/postbuild/markers/<YYYYMMDD>_<run_slug>/`;
- explicit `supersedes:` front matter that names the older blocked marker;
- matching `issue_id` and `family` for the supersedes relationship to be
  recognized by automation.

The natural fits are `05_REPAIR_VERIFIED.ready.md` with
`family: repair_verified` and
`supersedes: docs/reviews/phase3/postbuild/markers/20260506_limit500_run/01_RUN.blocked.md`.

Severity: minor (process compliance).

Required fix: name the canonical filename, family, `state`, `gate`, and
`supersedes` field for the post-rerun ready marker. Confirm whether
`scripts/phase3_tmux_agents.sh` will recognize the supersedes relationship
without manual intervention.

### F6 - Minor: R3 should distinguish new prompt rules from existing rules

`build_extraction_prompt` (`src/engram/extractor.py:1476-1524`) already
states:

- "Exactly one of object_text/object_json must be non-null";
- "If a required object value is unknown, omit the claim instead of
  emitting a partial or null object";
- "Prefer omitting uncertain or low-salience details over emitting invalid
  JSON or claims without direct evidence";
- text vs JSON predicate emission rules.

R3 partly restates these and partly adds new instructions ("Do not
enumerate the predicate vocabulary", "Do not create skeleton claims to
show possible predicates", "If no valid claims remain, return exactly an
empty claim list"). Without distinguishing additive language from
existing language, an implementer may rewrite the entire prompt block,
which would force a fresh reviewer pass over text that has already been
audited.

Severity: minor (clarity of change scope).

Required fix: in R3, mark each rule as "existing (retain)" or "new
(add)". The same-bound rerun is the load-bearing evidence either way, but
distinguishing additive changes reduces churn in subsequent reviews.

### F7 - Minor: same-bound rerun assumes the selected scope is stable across runs

`fetch_phase3_conversation_batch`
(`src/engram/cli.py:822-837`) selects "the first 500 active AI-conversation
conversations" by `conversation_id::text` ordering. The spec implicitly
assumes that the same 500 ids are selected on rerun. New ingestion between
runs could shift the boundary. This is unlikely on a same-day repair, but
the spec's gate pins the count to "selected conversations: 500" without
asserting boundary stability.

Severity: minor (acceptance gate robustness).

Required fix or accept-as-is: either add an explicit assertion that no
ingestion happens between the blocked run and the same-bound rerun, or
specify that the rerun must record the boundary conversation id and the
prior boundary conversation id and assert they match.

### F8 - Informational: R4 redacted feedback may include up to ~29 predicate names

R4 lists "predicate names" in the redacted repair feedback. The known
limit-500 segment had 28 distinct predicates dropped, which is nearly the
entire vocabulary (29 entries in
`src/engram/extractor.py:73-103`). The predicate vocabulary is fixed
schema metadata, not corpus content, so listing names does not violate
the RFC 0013 redaction boundary. In smaller drop sets, listing one or two
predicate names also does not constitute corpus disclosure because the
vocabulary is a public enum.

No fix required. Recommend the spec say so explicitly under R4 to
forestall later re-review concerns.

## Cross-Cutting Observations

- Audit history immutability (R7) is consistent with the existing
  prompt-version-keyed dedup in `find_existing_extraction`
  (`src/engram/extractor.py:1349-1371`) and the supersede-on-success block
  in `extract_claims_from_segment`
  (`src/engram/extractor.py:563-577`), which only marks same-prompt-version
  extractions superseded. Bumping prompt and request-profile versions (R1)
  re-extracts every selected segment under the new provenance while keeping
  failed v5/v7 rows untouched. The cost of re-extracting all 593
  successfully-extracted segments is implicit but not hidden.

- Failed extractor and consolidator progress rows from the interrupted run
  are overwritten by `upsert_progress` on a successful rerun
  (`src/engram/progress.py`). The existing requeue path
  (`src/engram/extractor.py:1644-1685`, exposed as
  `extract --requeue --conversation-id`) is not strictly required for the
  current case because the failed extraction is already in `failed`
  status and the failed progress row's `error_count` is at 1 (below
  `MAX_EXTRACTION_ERROR_COUNT=3`). The verification ladder's "if progress
  rows require it" hedge is correct but could be sharpened to "no requeue
  is required unless a stale `extracting` row is present".

- The hiding-by-empty-repair risk is real: the existing test
  `test_extractor_validation_repair_retry_can_produce_empty_success`
  (`tests/test_phase3_claims_beliefs.py:604-668`) demonstrates that an
  initially all-invalid extraction can become a zero-claim "extracted"
  status. The spec's R6 expanded gate is the only thing that prevents this
  pattern from passing the next-bound gate at scale.

## Recommendation

`accept_with_findings`. Implement after F1, F2, and F5 are resolved and F3,
F4, F6, F7 are addressed in synthesis. The spec correctly classifies the
issue, preserves strict validation, and gates expansion. The findings are
about implementation precision and process compliance, not about the
direction of the repair.
