# Benchmark Segmentation Harness Implementation Review

Date: 2026-05-03T20:04:14Z
Reviewer: claude-opus-4-7 (Claude Code)
Branch: build-benchmark-segmentation-harness
Base: master at fork (review diff = 5c259d7 + b23d400 vs master), HEAD = `b23d400`
Scope: `benchmarks/segmentation/` (datasets, fixtures, strategies, scoring,
results, reporting, run_benchmark, fixtures/), `tests/test_benchmark_segmentation.py`,
`.gitignore`. 14 files, +3,544 / -406 from master. No production code,
migration, or schema is touched.

## Findings

### 1. major: strict and window-tolerant F1 return 0.0 for correct no-boundary parents
File/line: `benchmarks/segmentation/scoring.py:299-315, 318-351`
Affected callers: `score_strategy_outputs` (`scoring.py:111-129`)

`boundary_precision_recall_f1` computes precision and recall via `safe_rate`,
which returns `0.0` when the denominator is `0`. For a parent whose expected
boundary set is empty (single-segment expected) and whose predicted boundary
set is also empty, all three of TP, FP, FN are zero, so precision = recall =
F1 = 0. `window_tolerant_boundary_f1` has the same shape and the same bug.

Reproduction (verified locally):

```
expected_boundaries=()  predicted_boundaries=()  # perfect single-segment match
strict:    {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
w-f1 +/-1: {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
w-f1 +/-2: {'precision': 0.0, 'recall': 0.0, 'f1': 0.0}
pk:        0.0
windowdiff: 0.0
```

Risk: every parent that should be exactly one segment - including the
shipped synthetic fixture `short_clean_single_segment_001` (RFC 0006 family
"a conversation that should become exactly one segment") and any
SuperDialseg dialog with no internal `segmentation_label==1` - drags
macro-averaged F1 toward 0 even when the strategy is right. This systematically
penalizes strategies that correctly handle single-segment dialogs, biases
model selection toward over-segmenters, and undermines the very RFC 0006
metric the synthesis matrix was protecting (W-F1 / P_k as the "close enough"
counterweight to strict F1). P_k and WindowDiff are correct in this case
(they return 0.0 disagreement), so the contradiction is silently visible
in the report.

Recommendation:
For both strict and window-tolerant scoring, when `len(expected) == 0` and
`len(predicted) == 0`, return `precision = recall = f1 = 1.0` (perfect
agreement on "no boundary"). Alternatively return a sentinel that excludes
the parent from the macro denominator, but that changes denominators. The
simpler fix is the 1.0 case. Add a unit test that pins it:
`boundary_precision_recall_f1(set(), set())["f1"] == 1.0`.

### 2. major: SuperDialseg adapter double-counts boundaries by combining `segmentation_label` and `topic_id` rules at off-by-one positions
File/line: `benchmarks/segmentation/datasets.py:208-216`

The adapter records two independent boundary rules per row:

```
if sequence_index > 0 and truthy_boundary_label(row.get("segmentation_label")):
    boundaries.add(sequence_index)
...
if sequence_index > 0 and previous_topic is not None and topic_str != previous_topic:
    boundaries.add(sequence_index)
```

In Jiang et al. (EMNLP 2023), `segmentation_label=1` marks the LAST turn of
the current segment (i.e., the boundary lies AFTER that turn, at position
N+1). The adapter places the boundary AT that turn's `sequence_index`. The
`topic_id` rule places a boundary at the FIRST turn of the new topic, i.e.,
N+1. For a real dialog where turn N ends segment 1 (label=1, topic=A) and
turn N+1 begins segment 2 (label=0, topic=B), the adapter produces TWO
boundaries: `{N, N+1}`. The correct count is one.

Reproduction (verified locally on a 4-turn synthetic dialog with the
boundary spanning turns 2->3):

```
input: turn2 label=1 topic=A, turn3 label=0 topic=B
adapter expected_boundaries = (2, 3)   # should be (3,)
```

The shipped shape file `superdialseg_shape.synthetic.jsonl` happens to align
both signals at the same index (the topic_id is set to the new topic on the
same turn as `segmentation_label=1`), which is why the test
`test_public_dataset_manifest_and_superdialseg_adapter` passes with a single
boundary. Real SuperDialseg snapshots will not have that alignment, and the
inflated boundary count will cascade into:

- doubled segment count expectation -> wrong P_k window size
  (`boundary_window_size` divides `message_count / (boundaries+1) / 2`),
- inflated false-negative count for any candidate that emits the correct
  single boundary,
- distorted WindowDiff (counts boundary mismatches in each window),
- unreliable over-/under-split totals.

Per D041 SuperDialseg is the first quality dataset; corrupted boundaries
here would silently invalidate the harness's primary public benchmark.

Recommendation:
Pick one rule. The paper-faithful option is to drop the `topic_id` rule and
shift `segmentation_label` to the next position
(`boundaries.add(sequence_index + 1)` for non-final turns), with a final-turn
guard. Keep the `topic_id` rule only as a fallback when `segmentation_label`
is absent, applied with the same off-by-one shift. Add a unit test that
pins the paper convention on a synthetic two-segment dialog where the two
signals would otherwise disagree. Document the chosen rule in
`benchmarks/segmentation/SPEC.md` with a citation.

### 3. minor: `schema_valid_rate` always reports 100% for deterministic strategies, masking the metric's intent
File/line: `benchmarks/segmentation/scoring.py:79-81, 138`

`schema_valid_count` only increments when no failure of `kind == "schema_invalid"`
is present, but neither `FixedTokenWindowsStrategy` nor `MessageGroupsStrategy`
ever emits a `schema_invalid` failure (their outputs are constructed
in-process and cannot fail JSON schema validation). The result is that
`schema_valid_rate` is always `1.0` for deterministic strategies, regardless
of whether the segments are useful. For the future LLM strategies the rate
would carry information; today it carries none.

Risk: a reviewer skimming the report sees "schema_valid_rate: 100.0%" and
treats it as a quality signal. It is a placeholder.

Recommendation:
For deterministic strategies, emit `schema_valid_rate = "not_applicable"`
(consistent with `token_throughput`, `peak_vram`, `steady_vram`). Either
gate on `strategy_kind != "llm"` in `score_strategy_outputs`, or have the
strategy itself record `schema_kind = "constructed"` in metadata and let
scoring branch on that. Same treatment is appropriate for the
`provenance_valid_rate` field if you decide it only carries information
once an LLM strategy can break it; provenance can also be broken by a
deterministic strategy citing the wrong ids, so leave that one as-is.

### 4. minor: benchmark token estimator (`chars / 4`) diverges from production estimator (`chars / 2.5`); sub-floor counts at 50/100/200 are not directly comparable to production
File/line: `benchmarks/segmentation/strategies.py:272-275`,
`docs/segmentation.md:140-141`,
`src/engram/segmenter.py:41-42`

`estimate_text_tokens` uses `max(1, ceil(len(text) / 4))`. Production
segmenter context-budget guard uses
`ENGRAM_SEGMENTER_CONTEXT_GUARD_CHARS_PER_TOKEN`, default `2.5`. This means
"a 200-token sub-floor segment" in the benchmark corresponds to ~800 chars,
while the production estimator would call the same text ~320 tokens. The
benchmark is internally consistent (`TOKEN_ESTIMATOR_VERSION` is recorded),
but RFC 0006 sub-floor thresholds (50/100/200) lose their interpretive link
to production reality.

Risk: an operator looking at `sub_floor_fragment_counts` will read it as
"how many segments are below production-token thresholds" and act on a
miscalibrated number. Comparison against production windowing decisions
(D037 context-guard) is not 1:1.

Recommendation:
Either align the benchmark estimator to `chars / 2.5` and bump
`TOKEN_ESTIMATOR_VERSION`, or document in
`benchmarks/segmentation/SPEC.md` that the sub-floor thresholds are in
benchmark-token units and that comparison against production thresholds
must apply a conversion factor. The latter is cheaper but the former is
clearer.

### 5. minor: `model_sha256_manifest_policy` field in `run.json` describes a sidecar manifest that is never written or read
File/line: `benchmarks/segmentation/results.py:100-104`

`run.json` ships a `model_sha256_manifest_policy` string that says SHA256
values "are read from a scratch sidecar manifest keyed by absolute path,
mtime, and size; stale entries must be invalidated before model strategies
run." No code in this implementation reads or writes such a manifest;
`strategy_metadata.model.model_sha256` and `model_sha256_sidecar` are
hard-coded to `"not_run"`. This is acceptable for the no-LLM-strategy
posture today, but the policy string oversells the implementation.

Risk: a future implementer adds an LLM strategy and does not realize the
manifest helper does not exist. The field gives a false sense that policy
is implemented.

Recommendation:
Either reword the field to "Local model SHA256 capture is deferred until
LLM strategies run; planned policy is a sidecar manifest keyed by
(absolute_path, mtime, size_bytes) under <output-dir>/<run_id>/", or add
a stub `model_sha256_sidecar.py` with the documented load/save shape and
refer to it. The first is cheaper.

### 6. minor: `validate_dataset_source` uses substring matching, allowing unrelated forks to pass
File/line: `benchmarks/segmentation/datasets.py:356-374`

The check is `if not any(value in dataset_source for value in allowed)`,
which is a substring test. A `dataset_source` of
`"local:superdialseg-personal-fork"` will pass because `"local:superdialseg"`
is a substring. The test is permissive enough that an operator who
accidentally points at a private/forked snapshot still satisfies the
manifest validator.

Risk: limited (manifests are user-authored, local-only) but the manifest
is the only structural check that the snapshot is the public dataset and
not something else.

Recommendation:
Tighten to `dataset_source in allowed` or split into a known-prefix list
(`startswith` set) so `"local:superdialseg"` matches but
`"local:superdialseg-fork"` does not.

### 7. nit: `relevant_segmenter_environment` is silently empty when no `ENGRAM_SEGMENTER_*` vars are set
File/line: `benchmarks/segmentation/results.py:304-309`

The reproducibility metadata field appears as `"environment": {}` for any
run where the operator has not exported segmenter variables. This is
correct behavior, but a reviewer skimming `run.json` may interpret an empty
dict as "the field is missing" rather than "no relevant variables were set
on this machine."

Recommendation:
Replace the empty-dict default with `{"_note": "no ENGRAM_SEGMENTER_* env
vars set"}`, or include a top-level `environment_captured_at` UTC timestamp
so the empty dict is unambiguous.

### 8. nit: `--allow-local-models` help text understates current behavior
File/line: `benchmarks/segmentation/run_benchmark.py:52-57`

The help text says "Permit future local-model strategies. This
implementation still does not call models." It is correct, but the
behavior at runtime is that the LLM strategies raise `NotImplementedError`
*after* the flag is set true, mid-loop, with no result file written. That
is intentional fail-closed behavior, but the help text could lead an
operator to expect a no-op success.

Recommendation:
Tighten to "Allow future local-model strategies to be selected. This
implementation will still raise NotImplementedError at strategy
invocation; no model or network call is made."

## Non-Blocking Notes

- **Boundaries verified**: no module imports `engram.*`; no network, model,
  or production-DB side effects at import or run time. The CLI never opens
  a connection. `tests/test_benchmark_segmentation.py` is fully offline.
- **Synthesis cleanup landed**: `--allow-local-models` replaces `--offline`
  (synthesis #1), `embeddable_message_ids` is wired through fixtures and
  scoring (#2), claim normalization is exactly NFKC + casefold + whitespace
  collapse (#3), `model_sha256_manifest_policy` is documented (#4 - see
  finding 5 for the gap), schema versions are pinned and validated
  (`segmentation-fixtures.v1`, `segmentation-expected-claims.v1`,
  `segmentation-public-dataset-manifest.v1`,
  `segmentation-benchmark-result.v1`, `segmentation-benchmark-score.v1`,
  `segmentation-benchmark-report.v1`) (#5), `__init__.py` files exist (#6),
  `StrategyKind` carries an explicit "not production
  segments.window_strategy" comment (`strategies.py:16-18`) (#7), and the
  full backend error class taxonomy is enumerated and bucketed (#8).
- **D041 public-first**: SuperDialseg is the only dataset wired for
  expected-boundary derivation; LMSYS-Chat-1M propagates
  `expected_boundaries=None` and the test confirms label-dependent metrics
  fall to `not_applicable`. License-acceptance gating for LMSYS works.
- **D034 / D037 / D038 / D039 boundaries preserved**: The strategies
  module mirrors production marker/tool-placeholder rules (`MARKER_ONLY_RE`
  copied locally, `is_embeddable_message` excludes role=tool), `StrategyKind`
  is benchmark-internal, no migration touched.
- **P_k and WindowDiff implementations**: half-open window
  (`start < b <= end`) and `boundary_window_size = round(avg_segment_length /
  2)` match the literature definitions. The known-case test
  (`pk_score((2,), (3,), 5) == 0.5` and `windowdiff_score((2,), (3,), 5) ==
  0.5`) is consistent with hand calculation.
- **Strategies handle edge cases reasonably**: oversize messages emit a
  single segment with `single_message_over_target=True`; overlap clamps to
  `len(current) - 1` so an oversize-only segment does not back-track;
  empty parents return zero segments without raising; tool/marker-only
  messages are excluded from `content_text` and `embeddable_message_ids`.
- **Result reproducibility**: `run.json` carries git commit, dataset
  snapshot/source/version/license, fixture versions, schema versions, both
  scoring and token-estimator implementation versions, full strategy
  config/metadata, and explicit `not_run` markers for unused model fields.
  `score_run_file` re-scores from `parents.jsonl` without needing the
  in-memory objects, satisfying the "reproducible enough to re-score"
  requirement.
- **Test coverage** is solid for happy paths and several failure modes
  (multi-error fixture validation, invalid claim refs, license gating,
  tool-body suppression, message-pair grouping, provenance unknown/cross-
  parent/unordered, claim normalization, full CLI round-trip). Gaps:
  no test for the no-boundary single-segment scoring case (related to
  finding 1), no SuperDialseg `segmentation_label`/`topic_id` disagreement
  test (finding 2), and no test for empty parents or all-tool parents at
  the strategy level.
- **`.gitignore`** correctly ignores `.scratch/` only; no source files are
  hidden. Benchmark fixtures and the SuperDialseg shape sample are
  committed under `benchmarks/segmentation/fixtures/`, all hand-authored.

## Validation

Performed (offline only, no external services):

- `python3 -m py_compile benchmarks/segmentation/*.py` - clean.
- `python3 -m benchmarks.segmentation.run_benchmark --help` - shows
  `validate-dataset`, `validate-fixtures`, `list-strategies`, `run`,
  `score`, `report`.
- `python3 -m benchmarks.segmentation.run_benchmark list-strategies` -
  emits all five expected strategies with correct kinds.
- `.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -v` -
  12/12 passed in 0.04s.
- `.venv/bin/python -m pytest -q` (full suite) - 26 passed, 38 skipped
  (skips are Phase-2 DB tests that require `ENGRAM_TEST_DATABASE_URL`).
- End-to-end `run` against the SuperDialseg shape sample under
  `tmp_path` - produced `run.json`, `parents.jsonl`, and the
  follow-up `score` command produced `score.json`. No network or model
  calls.
- Direct probes confirming findings 1 and 2 (single-segment perfect match
  scoring 0.0; SuperDialseg double-counted boundaries on a synthetic
  dialog where `segmentation_label` and `topic_id` disagree by one turn).

Not performed (out of scope or unavailable):
- `make test` outside `.venv` (system Python lacks pytest); used `.venv`
  pytest instead, equivalent for benchmark-specific tests.
- Real SuperDialseg snapshot validation - no local snapshot exists on
  this machine; the prompt explicitly allows skipping this and reporting
  the limitation.
- LLM strategy execution; `--allow-local-models` was not exercised end-to-
  end through `run` (the strategy refusal path is covered by the unit
  test `test_llm_strategy_refuses_without_local_model_opt_in`).

## Verdict

Pass with changes. Two `major` findings affect scoring correctness on
exactly the dataset class the benchmark exists to evaluate: finding 1
biases macro-F1 against strategies that correctly identify single-segment
dialogs, and finding 2 will inflate boundary counts on real SuperDialseg
data once the live snapshot is wired in. Both are local fixes in
`scoring.py` and `datasets.py` with small, testable scopes. The rest of
the harness is otherwise architecturally sound, isolated from production,
faithful to the synthesis cleanup list, and aligned with D041's
public-first posture. Resolve findings 1 and 2 (and add the matching
tests) before any decision-grade SuperDialseg run; the minor and nit items
can land alongside or shortly after.
