# Phase 3 Build Review Synthesis

Date: 2026-05-05
Synthesis owner: Codex GPT-5.5 (`codex_gpt5_5`)
Subject: Phase 3 claims / beliefs build review findings after marker
`08_BUILD_COMPLETE.ready.md`.

## Review Marker Check

The configured build review markers were present:

- `docs/reviews/phase3/markers/09_BUILD_REVIEW_gemini_pro_3_1.ready.md`
- `docs/reviews/phase3/markers/09_BUILD_REVIEW_codex_gpt5_5.ready.md`
- `docs/reviews/phase3/markers/09_BUILD_REVIEW_claude_opus_4_7.ready.md`

The coordinator used the expected reviewer set. No alternate reviewer set was
substituted.

## Inputs Read

- `docs/reviews/phase3/PHASE_3_BUILD_REVIEW_gemini_pro_3_1_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_BUILD_REVIEW_codex_gpt5_5_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_BUILD_REVIEW_claude_opus_4_7_2026_05_05.md`
- `docs/reviews/phase3/markers/08_BUILD_COMPLETE.ready.md`
- `docs/claims_beliefs.md`
- `prompts/P028_build_phase_3_claims_beliefs.md`
- Phase 3 implementation files and tests

`git status --short` was inspected before writing. The worktree already
contained Phase 3 implementation, prompt, schema-doc, review, and migration
changes. This synthesis only adds the accepted fix deltas, this document, and
the synthesis marker.

## Synthesis Verdict

Gemini accepted the build as-is. Codex rejected it for revision before pipeline
start. Claude judged the build safe for single-process usage, but unsafe for
concurrent extractor / consolidator operation until transaction-boundary fixes
landed.

The Codex P1 findings and Claude B1-B4 findings were accepted as pipeline-start
blockers or near-blockers because they could shape the first belief inventory
with extraction-order artifacts, failed local-model retries, or partial
close/insert side effects.

After the fixes below and the passing verification run, Phase 3 pipeline start
is allowed for a single operator process, subject to the migration-ledger
condition in *Residual Conditions*. Do not run concurrent Phase 3 workers until
the deterministic two-connection acceptance test lands.

## Accepted Fixes Applied

1. `pipeline-3` no longer consolidates partial conversations.
   `engram pipeline-3 --limit N` still selects N conversations, but each
   selected conversation now runs extraction until no pending segment remains
   before consolidation starts for that conversation.

2. Extractor retry budget now applies to normal retryable failures.
   Parse, schema, service, timeout, and context failures retry through the
   configured budget. The relaxed S-F013 schema path is still reserved for
   grammar / schema-construction failures.

3. D035 health smoke now wraps operator extraction runs.
   The `extract` / `pipeline-3` operator paths issue a tiny D034-profile
   schema-valid completion before and after real extraction work.

4. `claims` provenance is now structurally tied to its parent
   `claim_extractions` row.
   The migration trigger validates matching extraction id, segment id,
   generation id, extraction prompt version, extraction model version, and
   request profile version.

5. Relaxed extractor schema keeps the predicate enum.
   Relaxed mode now relaxes only evidence ids from enum to UUID pattern;
   predicate remains constrained to the V1 vocabulary.

6. Different-value contradiction transitions are atomic across close, insert,
   and contradiction creation.
   Rule 3 now wraps the transition in one transaction/savepoint and retries
   unique conflicts without rolling back the caller's outer transaction.

7. D054 reclassification recompute close/insert/contradiction is atomic and
   retries unique conflicts.

8. D054 same-value recompute for `multi_current` and `event` predicates now
   follows the spec's group-key equality rule instead of full JSON equality.

9. Orphan-rule result counts now propagate out of `consolidate_conversation`.
   This was found while adding the D054 recompute test; the operation itself
   ran, but the batch counters previously dropped non-reject orphan outcomes.

## Deferred Findings

- Same-value supersession audit anchoring: deferred. The current spec allows a
  single audit row anchored on the prior belief. This is an operator-query
  ergonomics issue, not a pipeline-start blocker.
- `failure_kind='privacy_reclassification'` docs: deferred. The value is
  intentionally written by the invalidation hook but should be documented
  before operator-facing diagnostics are polished.
- Per-segment invalidation hook inside `extract_claims_from_segment`: deferred.
  It is inefficient for large batches but not correctness-blocking.
- `cause_capture_id` singular cause recording: deferred. The current field
  records the most recent reclassification capture; multi-capture lineage can
  be expanded later.
- Text-predicate `group_object_keys=ARRAY['text']`: deferred as table
  readability cleanup.
- GUC/audit enforcement hardening beyond the transition API: deferred. D052
  intentionally makes the Python transition API load-bearing.
- Remaining acceptance-test gaps for orphan causes, lineage traversal,
  claim-count parity, requeue CLI, and deterministic two-connection concurrency:
  deferred before the 50-conversation pilot gate, not before the first
  single-process pipeline start.

## Residual Conditions

The uncommitted migration rename
`004_source_kind_gemini.sql` -> `005_source_kind_gemini.sql` remains a handoff
condition from the build review. Do not run migrations against a non-scratch
database whose `schema_migrations` ledger already records
`004_source_kind_gemini.sql` unless the coordinator has explicitly sanctioned
that migration-ledger transition. A fresh database, or a database whose ledger
already matches `005_source_kind_gemini.sql`, is acceptable.

No Phase 3 corpus pipeline was started during synthesis.

## Verification

Commands run after fixes:

```text
.venv/bin/python -m py_compile src/engram/extractor.py src/engram/consolidator/__init__.py src/engram/cli.py tests/test_phase3_claims_beliefs.py
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/pytest tests/test_phase3_claims_beliefs.py -q
make schema-docs DATABASE_URL=postgresql:///engram_test
make test
```

Final passing results:

```text
tests/test_phase3_claims_beliefs.py: 19 passed
make test: 99 passed in 34.29s
```

During the red/green loop, an added D054 recompute test initially exposed the
missing orphan-result count propagation. That was fixed before the final
passing run above.
