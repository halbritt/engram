# Benchmark Segmentation Harness Implementation Re-Review

Date: 2026-05-03T21:39:21Z
Reviewer: claude-opus-4-7 (Claude Code)
Branch: build-benchmark-segmentation-harness
Reviewed commit: `f6215b0` (review-finding fixes); HEAD `7ac43f6` adds the
prior Codex re-review document only and changes no code.
Base for diff: implementation-review HEAD `b23d400` (post-implementation,
pre-fix). Independent verification of all eight prior findings.

## Findings

No blocking, major, minor, or nit findings.

All eight items from `BENCHMARK_SEGMENTATION_HARNESS_IMPLEMENTATION_REVIEW.md`
are resolved with matching tests. Independently reproduced each one against
the live code:

1. **Major: no-boundary F1 returns 1.0.** `boundary_precision_recall_f1(set(),
   set())` and `window_tolerant_boundary_f1((), (), tolerance=k)` both return
   `precision=recall=f1=1.0`; non-empty/empty pairs still degrade to F1=0
   with the right TP/FP/FN counts. The single-segment fixture
   `short_clean_single_segment_001` round-trips to F1=1.0 end-to-end.
   Implemented at `scoring.py:307-316, 335-344`; pinned by the new
   assertions in `test_boundary_metrics_known_case`.

2. **Major: SuperDialseg paper-faithful boundary derivation.** The adapter
   now does a parent-wide `has_segmentation_labels` scan
   (`datasets.py:181-183`); when labels are present, `segmentation_label=1`
   places a boundary at `sequence_index + 1` with a final-turn guard,
   and `topic_id` is ignored on that branch. Verified four cases:
   (a) the disagreement test from the fix prompt yields `(2,)` and not
   `(2,3)` or `(1,2)`; (b) `segmentation_label=1` on the final turn yields
   `()`; (c) parents without any labels fall back to `topic_id` change at
   the new-topic position; (d) parents with mixed-label rows still treat
   labels as authoritative. Documented in `SPEC.md:62-69` and
   `README.md:26-29`; pinned by
   `test_superdialseg_prefers_segmentation_label_after_labeled_turn`.

3. **Minor: deterministic schema_valid_rate.** `schema_valid_rate` is now
   `"not_applicable"` for non-LLM strategies (`scoring.py:139-143` via
   `first_strategy_kind`); `provenance_valid_rate` correctly remains a real
   float because deterministic strategies can still cite bad ids. End-to-end
   `run.json` confirms both deterministic strategies report
   `schema_valid_rate: not_applicable` while LLM kind would still report a
   rate.

4. **Minor: token estimator alignment.** `estimate_text_tokens` is now
   `ceil(chars / 2.5)` (`strategies.py:21,275`), matching production's
   default `ENGRAM_SEGMENTER_CONTEXT_GUARD_CHARS_PER_TOKEN`.
   `TOKEN_ESTIMATOR_VERSION` bumped to `segmentation-benchmark-token-
   estimator.v2`. SPEC.md cross-references the production calibration.
   Verified `len=5 -> 2` and `len=100 -> 40`.

5. **Minor: SHA256 manifest wording.** `model_sha256_manifest_policy` now
   reads "Local model SHA256 capture is deferred until local-model
   strategies are implemented. Planned policy: write a scratch sidecar
   manifest under the run directory keyed by absolute path, mtime, and
   size." (`results.py:100-104`, mirrored in `SPEC.md:226-230`). The field
   no longer claims an unimplemented capability.

6. **Minor: dataset source exact-match.** `validate_dataset_source` now uses
   `dataset_source not in allowed` (`datasets.py:382-388`). Verified seven
   cases including the two regression cases the prior review flagged
   (`local:superdialseg-personal-fork`, `local:superdialseg-experimental`)
   correctly fail; the three legitimate sources for SuperDialseg pass; and
   `Coldog2333/super_dialseg/extra` and `huggingface:fake/super_dialseg`
   correctly fail. Pinned by `test_dataset_source_validation_rejects_
   substring_forks`.

7. **Nit: empty environment capture.** `relevant_segmenter_environment`
   returns `{"_note": "no ENGRAM_SEGMENTER_* env vars set"}` when no
   matching env vars are set (`results.py:305-312`). End-to-end run.json
   shows the note. Pinned by
   `test_token_estimator_matches_production_default_and_empty_env_is_explicit`.

8. **Nit: --allow-local-models help text.** The flag now documents
   "Allow future local-model strategies to be selected. In this
   implementation they still raise NotImplementedError before any model or
   network call." (`run_benchmark.py:53-60`). Verified via `run --help`
   output. Pinned by an assertion inside `test_cli_validate_list_run_and_score`.

## Non-Blocking Notes

- **Production-boundary guarantees preserved.** No `engram.*` import, no
  network/DB/model side effects at import or run time, no migration touched.
  Production segmenter contract (D034 request profile, D037 context-budget
  fail-closed posture, D038 tool/file placeholder rule) remains unaffected.
- **D041 public-first stance preserved.** SuperDialseg remains the labeled
  quality target; LMSYS-Chat-1M remains stress-only with
  `expected_boundaries=None`; synthetic fixtures remain regression-only.
- **Shape file co-edited with the rule.** The committed shape sample
  `superdialseg_shape.synthetic.jsonl` was updated so
  `segmentation_label=1` lands on turn 1 (not turn 2). Under the new
  paper-faithful rule, this still yields `expected_boundaries=(2,)`
  (boundary after turn 1, at position 2). The legacy assertion
  `parents[0].expected_boundaries == (2,)` in
  `test_public_dataset_manifest_and_superdialseg_adapter` continues to
  hold, so the shape file edit is internally consistent rather than a
  hidden test relaxation.
- **End-to-end behavior is sensible.** On the updated shape sample with
  `target_tokens=20`, `message_groups` produces strict F1=1.0 (it lands
  one boundary at position 2 for dialog 1 and zero for dialog 2, both
  matching expected); `fixed_token_windows` correctly over-segments
  (F1=0.25) because 20-token windows cannot match the 2-segment expectation.
  This is the kind of separation the harness exists to surface.
- **Sharp edge worth knowing.** `usable_boundary_label` accepts strings
  like `"no"`, `"yes"`, `"boundary"`, `"b"` as "label-present" markers, and
  `usable_boundary_label(2) -> False` while `truthy_boundary_label(2) ->
  True`. For real SuperDialseg (which uses 0/1) this is a non-issue. For an
  exotic export where every row has `segmentation_label="no"` and topic_ids
  change, the parent would record zero boundaries because labels are
  considered authoritative. Probably never a real input; flagging only as
  context, not a finding.
- **First-strategy-kind heuristic.** `first_strategy_kind` reads the kind
  off `next(iter(outputs_by_parent.values()))`. Each call to
  `score_strategy_outputs` already scores one strategy at a time, so the
  heuristic is sound. If the function were ever extended to score multiple
  strategies in one call the heuristic would need revisiting; not a current
  defect.
- **Test coverage strengthened.** Three new tests
  (`test_superdialseg_prefers_segmentation_label_after_labeled_turn`,
  `test_dataset_source_validation_rejects_substring_forks`,
  `test_token_estimator_matches_production_default_and_empty_env_is_explicit`)
  plus expanded assertions in two existing tests (boundary metrics
  no-boundary case, CLI help-text inspection) lock in the fixes.
- **Residual risk.** None of the fixes were exercised against a real local
  SuperDialseg snapshot - only the hand-authored shape sample. The
  paper-faithful rule should still be checked against an actual snapshot
  before any decision-grade run; the disagreement test gives high
  confidence in the rule's intent, but real SuperDialseg may carry
  edge cases the synthetic shape does not (e.g., conversations whose
  final turn has `segmentation_label=1`, malformed rows, or label-only
  parents without `topic_id`). The adapter's behavior on the first three
  is verified by my offline probes; broader confidence requires the real
  snapshot.

## Validation

Performed (offline only, no external services):

- `python3 -m py_compile benchmarks/segmentation/*.py` - clean.
- `python3 -m benchmarks.segmentation.run_benchmark --help` - shows all six
  subcommands.
- `python3 -m benchmarks.segmentation.run_benchmark list-strategies` -
  five strategies with correct kinds.
- `python3 -m benchmarks.segmentation.run_benchmark run --help` - confirms
  the `--allow-local-models` help text rewrite.
- `.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -v` -
  15/15 passed (was 12/12 before fix; +3 tests).
- `.venv/bin/python -m pytest -q` (full suite) - 29 passed, 38 skipped
  (skips are Phase-2 DB tests requiring `ENGRAM_TEST_DATABASE_URL`,
  unrelated).
- End-to-end `run` -> `score` -> `report --format both` against the
  SuperDialseg shape sample under `tmp_path`: produced `run.json`,
  `parents.jsonl`, `score.json`, `report.md`, `report.html`. Metrics
  showed `schema_valid_rate: not_applicable`, `expected_boundaries=[2]`
  on dialog 1, `message_groups` strict F1=1.0, full backend-error class
  enum present, `_note` form for empty environment, deferred SHA256
  wording in `model_sha256_manifest_policy`.
- Independent probes for each prior finding:
  - finding 1: empty/empty -> 1.0, empty/non-empty and non-empty/empty
    correctly degrade with right TP/FP/FN counts;
  - finding 2: disagreement (label at turn 1, topic shift at turn 2) ->
    `(2,)`; final-turn label=1 -> `()`; topic-only fallback works;
    mixed-label parent uses labels;
  - finding 3: deterministic strategies report `not_applicable`; LLM kind
    output (synthesized) still reports a rate;
  - finding 4: `estimate_text_tokens('x'*5) == 2` and `'x'*100 == 40`;
  - finding 5: `run.json.model_sha256_manifest_policy` is the deferred
    wording verbatim;
  - finding 6: seven sources tested, including two prior-passing forks
    that now correctly fail;
  - finding 7: empty-env capture is the `_note` form;
  - finding 8: `--allow-local-models` help text contains
    "NotImplementedError" and "before any model or network call".

Not performed: real SuperDialseg snapshot, local-model strategies
(`--allow-local-models` end-to-end through `run` is implicit via the prior
unit test), full corpus benchmarks. All explicitly out of scope.

## Verdict

Pass. The fixes resolve every accepted finding from the prior implementation
review, including both major scoring-correctness defects on the primary D041
public dataset path. The patches are localized, paper-faithful where the
literature applies, and each one is locked in by a regression test. The
harness is ready for merge from the perspective of the previous review's
findings; the only remaining gap is validation against a real SuperDialseg
snapshot, which requires data that is not available in this review
environment.
