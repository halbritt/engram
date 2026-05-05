# Phase 3 Build Review

Reviewer: Codex GPT-5.5 (`codex_gpt5_5`)
Date: 2026-05-05
Review completed: 2026-05-05T17:19:35Z

## Verdict

Reject for revision before `prompts/P031_begin_phase_3_pipeline.md`.

The implementation has the right broad shape and `make test` passes, but there
are pipeline-start blockers around extraction retry behavior, long-run health
gating, and `pipeline-3` processing semantics. I did not patch code.

## Findings

### P1 - `pipeline-3` consolidates partial conversations

`engram pipeline-3 --limit N` is specified to cap conversations processed
end-to-end (`prompts/P028_build_phase_3_claims_beliefs.md:412`) and the
consolidator is supposed to run after a conversation's extractor stage finishes
(`prompts/P028_build_phase_3_claims_beliefs.md:365`). The current CLI fetches
conversation IDs, then for each conversation runs one extraction batch capped
to `extract_batch_size`, and immediately consolidates that conversation
(`src/engram/cli.py:284`, `src/engram/cli.py:294`, `src/engram/cli.py:301`).

For any conversation with more active segments than the extraction batch size,
this creates candidate beliefs from an incomplete claim set. Later runs can
then reinforce, supersede, or contradict those partial beliefs as the remaining
segments arrive. That is non-destructive at the row level, but it is an
operator hazard before the first Phase 3 corpus run because the initial belief
inventory will encode extraction-order artifacts.

Expected fix: make `pipeline-3` finish extraction for each selected
conversation before consolidation, or make it explicitly stage-only and avoid
consolidating partial conversations.

### P1 - The extractor retry budget is not applied to normal extractor failures

The spec requires parse failures to retry up to the configured budget and
persist full D035 diagnostics on exhaustion (`docs/claims_beliefs.md:1082`).
`call_extractor_with_retries()` loops over `retries + 1`, but the exception
handler immediately re-raises every non schema-construction error on the first
attempt (`src/engram/extractor.py:584`, `src/engram/extractor.py:597`,
`src/engram/extractor.py:599`). The relaxed-schema retry path is only reached
for grammar/schema-construction failures.

Impact: transient HTTP, empty-content, fenced-JSON, parse, schema-invalid, and
context-path failures do not get the configured retry budget. A single bad
local completion can mark the extraction failed and increment
`consolidation_progress.error_count`, causing parents to freeze earlier than
specified.

Expected fix: retry all retryable extractor failures through the configured
budget, reserving relaxed schema only for the S-F013 grammar-state fallback.

### P1 - D035 health smoke is missing from extraction and `pipeline-3`

The contract requires a tiny D034-profile health completion before and after
long extraction/preflight slices (`docs/claims_beliefs.md:987`,
`docs/claims_beliefs.md:1072`). I found no Phase 3 health-smoke call in the
extractor path or CLI. The `extract` and `pipeline-3` commands enter real
extraction work directly (`src/engram/cli.py:187`, `src/engram/cli.py:275`;
`src/engram/extractor.py:412`).

This was added because Phase 2 found `/v1/models` and `/props` can remain
healthy while chat completions are wedged. Without this gate, the operator can
start Phase 3 against a broken local inference backend and accumulate failed
or timed-out extraction rows before the system proves schema-valid completion
works.

### P2 - Claim provenance is not structurally tied to parent `claim_extractions`

The build prompt requires claim derivation columns to exactly match the parent
`claim_extractions` row (`prompts/P028_build_phase_3_claims_beliefs.md:459`).
The migration trigger validates segment membership, segment generation,
conversation, predicate vocabulary, object shape, and evidence subset
(`migrations/006_claims_beliefs.sql:330`), but it does not validate that
`claims.extraction_id` belongs to the same segment/generation or that
`claims.extraction_prompt_version`, `claims.extraction_model_version`, and
`claims.request_profile_version` match the referenced extraction row.

The normal Python path writes matching values (`src/engram/extractor.py:790`),
but `claims` are canonical insert-only provenance rows. A fixture, repair
script, or future operator path can currently insert a claim whose evidence
points at one extraction lifecycle row while its version columns describe
another.

Expected fix: add a trigger check against `claim_extractions` for
`extraction_id`, segment/generation, and all three version columns; add a
negative test.

### P2 - Same-value supersession leaves the successor belief without a direct audit row

`insert_belief()` writes a `belief_audit` row for the inserted belief
(`src/engram/consolidator/transitions.py:36`). In contrast,
`supersede_belief()` inserts the successor via private `_insert_belief_row()`
and writes one audit row against the prior belief only
(`src/engram/consolidator/transitions.py:64`, `src/engram/consolidator/transitions.py:84`,
`src/engram/consolidator/transitions.py:93`).

That means an active successor created by same-value reinforcement has no
`belief_audit` row under its own `belief_id`. A forensic query starting from
the active belief cannot see the transition that created it without traversing
backward through `superseded_by` from an older row. If this one-row logical
audit model is intentional, the spec and tests should pin that traversal.
Otherwise, add an insert audit for the successor or record the successor ID in
the supersede audit payload.

### P2 - Relaxed extractor schema drops the predicate enum

The S-F013 fallback is documented as relaxing evidence IDs to a UUID pattern
while retaining the predicate enum (`docs/claims_beliefs.md:1168`). The current
schema builder removes the predicate enum whenever `relaxed_schema=True`
(`src/engram/extractor.py:266`). Invalid predicates are later dropped by
Python salvage, but that is a drift from D046's "schema constrains the local
LLM output before it reaches the DB" contract.

Expected fix: keep `predicate` enum-constrained in relaxed mode and relax only
the evidence UUID list as specified.

## Test Coverage Gaps

The Phase 3 test file covers important happy paths and several guards, and the
full suite passes. It does not yet cover several acceptance items that are
explicitly listed in the spec:

- D035 health smoke before/after extraction preflight.
- Retry budget for parse/schema/service failures.
- `pipeline-3 --limit N` processing conversations end-to-end rather than one
  segment batch.
- D054 same-value and different-value reclassification recompute branches
  (`docs/claims_beliefs.md:1119`).
- D053 two-connection concurrent consolidator conflict retry
  (`docs/claims_beliefs.md:1151`).
- Negative DB test for claim version mismatch against parent
  `claim_extractions`.
- Relaxed-schema fallback retaining the predicate enum.

## Checks Without Findings

- No hosted service or cloud API dependency was introduced in the Phase 3
  implementation. The extractor reuses the local ik-llama URL guard.
- I did not find raw evidence table mutation in Phase 3 code.
- Belief evidence and claim IDs are non-empty at the schema level.
- Segment -> claim -> belief privacy tier propagation is implemented on the
  normal consolidation path.
- `engram pipeline` remains Phase 1/2 only.

## Verification Run

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/pytest tests/test_phase3_claims_beliefs.py -q` -> 13 passed.
- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/pytest tests/test_phase2_segments.py -q` -> 30 passed.
- `make test` -> 93 passed in 35.09s.

I also initially tried the Phase 2 and Phase 3 pytest files in parallel, but
that was invalid because both reset the same `engram_test` database. The
sequential runs above are the meaningful results.
