# Benchmark Segmentation Early-Signal Implementation Review

Date: 2026-05-04T03:32:28Z
Reviewer: claude-opus-4-7 (Claude Code)
Branch: build-benchmark-segmentation-harness
Reviewed commit: `b323eac` (Implement segmentation benchmark early signal)
Base for diff: `89d58f2` (Synthesize early signal benchmark review)
Scope: code, fixtures, tests, and SPEC/README updates promoting RFC 0008 /
D042 Tier 0 + Tier 1 from specification to executable harness:

- new modules `benchmarks/segmentation/early_signal.py`,
  `benchmarks/segmentation/sample_plan.py`;
- `run_benchmark.py`, `scoring.py`, `results.py`, `reporting.py` updated;
- `fixtures/synthetic_parents.example.jsonl` and
  `fixtures/expected_claims.example.jsonl` expanded to 10/9;
- new `fixtures/early_signal_thresholds.example.json`;
- 25 tests in `tests/test_benchmark_segmentation.py`.

## Findings

### 1. major: `sample-plan --benchmark-tier smoke` crashes with `KeyError: 'no_boundary'`
File/line: `benchmarks/segmentation/sample_plan.py:221-224`,
`benchmarks/segmentation/run_benchmark.py:55-66, 161-176`

`create_sample_plan` builds `targets = {"smoke": target_sample_size}` for
smoke tier (line 408-409), but the shortfall comprehension hardcodes
`SUPERDIALSEG_TIER1_STRATA`:

```python
shortfalls = {
    stratum: max(0, targets[stratum] - actuals[stratum])
    for stratum in SUPERDIALSEG_TIER1_STRATA
}
```

`targets["no_boundary"]` does not exist in smoke mode, so the function
raises `KeyError`. This is reachable from the user-facing CLI.

Reproduction (verified locally):

```
$ python -m benchmarks.segmentation.run_benchmark sample-plan \
    --dataset-manifest <local manifest> \
    --benchmark-tier smoke --sample-seed 1 --target-size 1 \
    --output sp.json
KeyError: 'no_boundary'
```

The argparse subparser (`run_benchmark.py:55-66`) accepts `--benchmark-tier
smoke` per `SUPPORTED_BENCHMARK_TIERS`, and the spec lists smoke as an
implemented tier ("Sample Plans / Status: implemented for SuperDialseg
`smoke` and `early_signal` sample plans"). The bug isn't masked by tests
because the only smoke-tier test for sample plans goes through `run` with
`--limit 10` (which uses argparse default `--benchmark-tier smoke` *without*
calling `sample-plan`), and the explicit sample-plan CLI test only exercises
`early_signal`.

Recommendation:
Iterate the keys of `targets`, not `SUPERDIALSEG_TIER1_STRATA`:

```python
shortfalls = {
    stratum: max(0, targets[stratum] - actuals.get(stratum, 0))
    for stratum in targets
}
```

Add a regression test that calls `create_sample_plan(..., benchmark_tier="smoke", ...)`
and asserts the returned plan's `stratum_target_sizes` and
`stratum_shortfalls` use the smoke key only. Optionally add a CLI test that
runs `sample-plan --benchmark-tier smoke`.

### 2. minor: deterministic baselines silently get `longer_run` instead of `defer` when no threshold set is supplied
File/line: `benchmarks/segmentation/early_signal.py:332-352`

The verdict cascade checks `threshold_set is None` *before* the deterministic
kind branch:

```python
elif threshold_set is None:
    verdict = "longer_run"
    summary = "No explicit threshold set was supplied, so candidate verdicts are disabled."
elif strategy_kinds.get(strategy_name) in DETERMINISTIC_STRATEGY_KINDS:
    verdict = "defer"
    summary = "Deterministic baseline scored for comparison; it is not a model candidate."
```

Result: a Tier 1 run with `--benchmark-tier early_signal` and no
`--early-signal-thresholds` flag classifies `fixed_token_windows` and
`message_groups` as `longer_run`, which reads as "promising, but evidence
is insufficient for a production change." That is wrong — these strategies
are not model candidates at all; they exist as comparison anchors. Reproduced
locally (probe 30): a Tier 1 run with only `fixed_token_windows` and no
threshold file emits `verdict=longer_run` for the deterministic strategy.

Risk: low/medium. The verdict surfaces deterministic baselines as
"promising candidates" in reports/tooling. Operators who skim the verdict
column will be misled by the early-signal report's Strategy Comparison +
Verdict tables.

Recommendation:
Reorder the cascade so kind-based short-circuits run before the threshold
absence check, or merge them: deterministic baselines always `defer`
regardless of threshold set state, with `summary` indicating "deterministic
baseline; not a model candidate" in both threshold and no-threshold paths.
Add a regression test with no thresholds and a deterministic strategy
verifying `verdict == "defer"`.

### 3. minor: Tier 1 challenger silently `defer`s when no deterministic baseline is in the run
File/line: `benchmarks/segmentation/early_signal.py:303-330, 344-352, 399-403`

`generate_early_signal_verdicts` requires the challenger to beat
**both** `strict_f1_vs_best_deterministic` and `strict_f1_vs_operational_model`
to receive `candidate`. When no deterministic strategy is in the run,
`best_strict_f1_for_kind` returns `"not_applicable"`, `numeric()` rejects
the string, and the gate fails. The verdict logic does have a
`comparison_unavailable` branch — but it only checks the operational model,
not the deterministic baseline. So a run with only LLM strategies (operational
model present, no deterministic baselines) lands in `defer` rather than
`longer_run`, and `metric_reasons["strict_f1_vs_best_deterministic"]` shows
`{"value": 0.7, "threshold": "not_applicable", "passed": false}` without a
hard warning explaining "deterministic baseline missing."

Reproduced locally (probe 25): two LLM strategies, operational +
challenger, challenger wins F1, no deterministic baseline → `verdict=defer`,
no warning surfaced.

The spec's intent is reasonable: a challenger should beat the cheap
deterministic anchors. But a `defer` verdict without a `hard_warnings`
explanation makes the missing baseline look like a quality problem, when it
is actually a run-shape problem.

Recommendation:
Mirror the operational-comparison handling. If
`best_strict_f1_for_kind(...) == "not_applicable"`, append a hard warning
("deterministic baselines unavailable; cannot displace operational model
without an anchor"), and route the verdict to `longer_run` rather than
`defer`. Update the verdict test to cover this case.

### 4. minor: sample-plan `dataset_revision` is sourced from `local_path_sha256` and not enforced at run time
File/line: `benchmarks/segmentation/sample_plan.py:226-247`,
`benchmarks/segmentation/sample_plan.py:275-300`

`create_sample_plan` records `dataset_revision = manifest.local_path_sha256`,
which is intended to be a SHA256 of the manifest-relevant file list but is
often null in practice (the shape sample manifest writes
`local_path_sha256: null`, and the spec example uses
`"local_path_sha256": "sha256 over manifest-relevant file list"` as a
placeholder string). Then `validate_sample_plan_for_manifest` checks
`dataset_name`, `dataset_source`, `dataset_version`, and `split`, but
**not** the revision.

Risk: a sample plan saved against revision X can be replayed against
manifest Y of the same name/source/version with no warning. The point of
the plan is reproducibility, so silently accepting a revision drift
undermines the contract.

Recommendation:
- Compare `plan.dataset_revision` to the manifest revision (when both are
  set) in `validate_sample_plan_for_manifest` and refuse on mismatch.
- Stop conflating `dataset_revision` with `local_path_sha256`; either name
  the field consistently or make `create_sample_plan` derive a real revision
  identifier (e.g., `local_path_sha256` *or* `dataset_version` *or* a
  recorded snapshot id) and document the precedence.
- Add a regression test that flips `dataset_version` between plan
  generation and run-time validation.

### 5. minor: a Tier 1 `--benchmark-tier early_signal` run without `--sample-plan` skips Tier 1's stratification contract
File/line: `benchmarks/segmentation/run_benchmark.py:208-238`

The CLI accepts `--benchmark-tier early_signal` without requiring
`--sample-plan`. The run uses the entire manifest (or `--limit N`) directly,
labels `benchmark_tier: early_signal` in `run.json`, and emits a verdict —
but the run never consulted Tier 1's stratified shortfall rule and never
enforced the 60-parent minimum. The result file looks decision-graded
(`selection_caveat: early_signal_not_decision_grade`) without honoring the
tier's audit-trail contract.

Spec text: "Required shape: 60-100 deterministic, stratified SuperDialseg
validation parents…" The implementation enforces this only inside
`create_sample_plan(..., enforce_tier_minimum=True)`, which is bypassed when
the operator does not pass `--sample-plan`.

Recommendation:
Either:
- Require `--sample-plan` whenever `--benchmark-tier early_signal` is set,
  and document the smoke-without-plan default; or
- When a Tier 1 run lacks a sample plan, stamp `selection_caveat` to
  something like `early_signal_unstratified` (not the standard
  `early_signal_not_decision_grade`) and surface a hard warning in the
  verdict so reports show the gap.

### 6. nit: `CURRENT_OPERATIONAL_MODEL_STRATEGY` is a hardcoded constant with no override path
File/line: `benchmarks/segmentation/early_signal.py:21`

`CURRENT_OPERATIONAL_MODEL_STRATEGY = "qwen_35b_a3b_iq4_xs_d034"` is a
module-level constant baked into verdict generation. The internal
`build_strategy_verdict(operational_model_strategy=...)` parameter is
plumbed through `generate_early_signal_verdicts`, but the CLI surfaces no
flag. When the operational model rotates (Phase 2 has explicitly considered
Qwen 27B and Gemma in recent benchmarks), the constant becomes stale
silently and no operator-visible warning appears.

Recommendation:
Add `--operational-model-strategy` to `run` (and the verdict flow), default
to the constant, and record the chosen value in
`run.json.early_signal_verdicts.<strategy>.threshold_set` (or alongside it)
so future replay knows which baseline was used.

### 7. nit: `dataset_revision` field is reported but never compared against the manifest, and the docstring/spec do not say so
File/line: `benchmarks/segmentation/sample_plan.py:38-39, 232`

Same data flow as finding 4, viewed from the schema side: the sample plan
JSON exposes `dataset.revision` which suggests reproducibility-relevant
provenance, but the field is unused at validation time. Either document
its informational status in `SPEC.md`, or wire enforcement (per finding
4). Treating it as silent provenance is the worst of both worlds.

### 8. nit: report fragmentation table shows percentages for label-dependent rates that are `not_applicable`
File/line: `benchmarks/segmentation/reporting.py:300-331`,
`format_percent` at `reporting.py:525-528`

`format_percent` already short-circuits non-numeric values to
`format_metric` ("n/a" or `str(value)`), so for unlabeled datasets the
fragmentation table cells render as `not_applicable` instead of `0.0%`.
That's fine. But two of the cells in `markdown_fragmentation_table` use
`format_metric` (ratio_avg, abs_distance_avg,
parents_more_than_twice_expected_count) and three use `format_percent`
(no_boundary_false_split_rate, sub_100_fragment_rate, adjacent_tiny_fragment_rate,
duplicate_adjacent_rate). Mixed formatters in one table make
"not_applicable" appear inconsistently across columns; some print the
literal string, some print "n/a". Cosmetic.

Recommendation:
Pick a single sentinel string (e.g., always "n/a") for not-applicable
cells, or add a small helper that consistently maps `"not_applicable"` →
`"n/a"` before either formatter is invoked.

## Non-Blocking Notes

- **Production-boundary guarantees preserved.** No `engram.*` import, no
  network/DB/model side effects in module import path. LLM strategies
  refuse non-loopback URLs (test
  `test_llm_strategy_refuses_non_loopback_url`) and refuse to run without
  `--allow-local-models`.
- **D042 / D041 invariants intact.** Public-first dataset order survives;
  `StrategyKind` remains internal; deferred P-FRAG schema values stay out;
  result writes are scratch-only under operator-supplied `--output-dir`.
- **Synthesis cleanup landed.** Each accepted item from the spec
  synthesis is reflected in code or docs:
  - threshold sets are required for `candidate` verdicts, defaults are not
    silently used (`early_signal.py:259-264, 332-352`);
  - `metric_reasons` is structured `dict[str, {value, threshold, passed}]`,
    not `key=value` strings (`early_signal.py:210-330`);
  - sample plans record stratum target/actual/shortfall sizes;
  - tier metadata, sample-plan summary, threshold set, and
    early-signal verdicts are all present in `run.json` /
    `score.json`;
  - old-style result files without these fields still render and re-score
    (test `test_cli_validate_list_run_and_score` exercises the
    backward-compatible path).
- **Backward compatibility verified end-to-end.** Old-style `run.json`
  with no `benchmark_tier`, `selection_caveat`, `sample_plan`,
  `early_signal_thresholds`, `early_signal_verdicts`, or per-strategy
  `fragmentation` block scores and reports without errors.
- **Threshold-set roundtrip is clean.** `EarlySignalThresholdSet.to_dict()`
  → `threshold_set_from_dict(payload)` is a stable round-trip; `score`
  re-derives the verdict from the persisted run.json.
- **Sample-plan determinism verified locally.** Same seed/dataset reproduce
  the same `selected_parent_ids`; different seeds permute order; first-N
  is not the chosen output (probe 1).
- **Tier 1 minimum-parent gate fires correctly.** With 12 synthetic-shape
  parents, `create_sample_plan(..., target_sample_size=80)` raises
  `BenchmarkValidationError` with "minimum is 60"; setting
  `enforce_tier_minimum=False` allows the helper to return a smaller plan.
- **Threshold validation surfaces multiple errors cleanly.** Bad files
  (wrong type, missing `hard_gates`, non-numeric thresholds) raise
  `BenchmarkValidationError` with discrete per-field messages.
- **Fragmentation metrics correctness spot-checked.** No-boundary parent
  split into 3 segments → `no_boundary_false_split_count == 2`,
  `parents_more_than_twice_expected_count == 1`,
  `duplicate_adjacent_pair_count == 2`, `adjacent_tiny_fragment_rate ==
  1.0`. Unlabeled parent → label-dependent metrics =
  `"not_applicable"`. Token estimator at 2.5 chars/token confirmed.
- **Sharp edges to know.**
  - `usable_boundary_label` accepts `"no"`, `"yes"`, etc. as label-present
    markers; pre-existing from prior commit.
  - Synthetic fixture `single_topic_no_boundary_001` uses `parent_id =
    00000000-0000-4000-8000-000000001001`, which is also the *message id*
    of `short_clean_single_segment_001`'s first message. That's a UUID
    collision between a parent_id and a message_id across fixtures.
    Provenance scoring is parent-scoped (the `all_message_owner` map keys
    are message_ids, not parent_ids), so this is harmless today, but it
    is a hygiene smell for any future cross-fixture provenance check.
  - Run `--benchmark-tier` defaults to `smoke` in argparse regardless of
    `--limit`. A user running, say, `--limit 100` without specifying
    `--benchmark-tier` will mis-tag the run as smoke. The spec text
    suggested "default to smoke when --limit 10 is used"; the
    implementation defaults to smoke unconditionally.
- **Tests exercise the right cases.** 25/25 benchmark tests pass; full
  suite is 39 passed / 38 DB-only skips. New tests cover sample-plan
  determinism + shortfall recording, Tier 1 minimum enforcement,
  `run --sample-plan` parent-order preservation, threshold validation +
  structured verdict rules, absent-thresholds preventing `candidate`,
  fragmentation metric correctness, label-dependent `not_applicable`
  fallback, old-style result compatibility, and the LLM-strategy refusal
  paths from prior commits.

## Validation

Performed (offline only):

- `python3 -m py_compile benchmarks/segmentation/*.py` — clean.
- `python3 -m benchmarks.segmentation.run_benchmark --help` — six
  subcommands incl. `sample-plan`.
- `python3 -m benchmarks.segmentation.run_benchmark list-strategies` —
  five strategies (`fixed_token_windows`, `message_groups`, three
  `llm`).
- `python3 -m benchmarks.segmentation.run_benchmark validate-fixtures
  --fixtures ... --expected-claims ...` —
  `parents=10 fixture_version=0.2.0 expected_claims=9`.
- `.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -v` —
  25/25 passed.
- `.venv/bin/python -m pytest -q` (full suite) — 39 passed, 38 skipped
  (Phase-2 DB-only tests).
- End-to-end `sample-plan` → `run --benchmark-tier early_signal
  --sample-plan ... --early-signal-thresholds ...` → `score` →
  `report --format both` against an 80-parent SuperDialseg-shape sample
  under `tmp_path` — all four steps returned exit 0; verdict tables
  populated; threshold set roundtripped.
- Direct probes for each finding above (probes 1-31 in my notes); all
  reproduced at the line/behavior cited.

Not performed:

- `make test` outside `.venv` (system Python lacks pytest).
- Real SuperDialseg snapshot end-to-end (no local snapshot available).
- LLM strategy execution (out of scope; refused by tests).

## Verdict

Pass with changes.

The implementation lands the documented Tier 0 / Tier 1 deliverables
(deterministic sample plans, tier metadata, fragmentation metrics,
structured verdicts, threshold-set plumbing, expanded fixtures, report
sections, old-result compatibility) and stays cleanly inside the local-only
boundary. The accepted spec-synthesis clarifications are visibly applied.

Finding 1 is a real crash on a CLI path that the spec advertises as
implemented (`sample-plan --benchmark-tier smoke`) and should be fixed
before merge or the smoke sample-plan claim should be rolled back. Findings
2-5 are correctness/UX gaps that affect verdict readability and Tier 1's
audit contract; they should land in the same patch series. Findings 6-8
are nits.
