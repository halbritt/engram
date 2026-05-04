# Segmentation Benchmark Harness

This directory contains the local-only, scratch-only segmentation benchmark
harness from RFC 0006, refined by RFC 0008 / D042. It compares public dataset
snapshots and deterministic baseline strategies before any change to the
production Phase 2 segmenter contract.

The harness does not download datasets, call hosted services, call ik-llama or
Ollama, write the production database, or import production segmenter runtime
code. Public datasets are prepared by explicit operator action outside the
harness and referenced through local manifests.

## Dataset Order

1. SuperDialseg is the first quality target. It has public supervised dialogue
   boundary labels, so strict boundary F1, window-tolerant F1, P_k, and
   WindowDiff can be scored.
2. LMSYS-Chat-1M is the optional operational stress target. It has no boundary
   labels by default, so label-dependent metrics report `not_applicable`.
3. Synthetic fixtures are small edge-case and regression tests. They are not
   the primary benchmark substrate.

The committed `superdialseg_shape.synthetic.jsonl` file is hand-authored shape
data for tests only. It is not copied from SuperDialseg.

For SuperDialseg local exports, `segmentation_label=1` is interpreted as a
boundary after the labeled turn (`sequence_index + 1`). `topic_id` changes are
only a fallback when a parent has no usable segmentation labels.

## Benchmark Tiers

The tier model is specified by RFC 0008 / D042. Runner support exists for
Tier 0 smoke metadata and Tier 1 early-signal sample plans, threshold-set
metadata, fragmentation metrics, and structured verdicts. Tier 2 decision-grade
model switching remains pending.

- `smoke`: 10 labeled SuperDialseg validation parents. This validates the
  harness and a candidate model/profile only; reports must mark the run
  `smoke_only`.
- `early_signal`: 60-100 deterministic, stratified SuperDialseg validation
  parents plus the full synthetic Engram-proxy fixture set. This tier produces
  `reject`, `defer`, `longer_run`, or `candidate`.
- `decision`: several hundred SuperDialseg parents or the full validation
  split, plus fixtures and optional local LMSYS operational stress. This is
  the first tier that can justify changing the production segmenter model.

Raw boundary F1 is not enough for model selection. Early-signal and decision
runs must also surface fragmentation, no-boundary false splits, proxy-fixture
quality, provenance safety, and operational reliability.

## CLI

```bash
python3 -m benchmarks.segmentation.run_benchmark validate-dataset \
  --manifest .scratch/benchmarks/datasets/superdialseg/manifest.json

python3 -m benchmarks.segmentation.run_benchmark validate-fixtures \
  --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl \
  --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl

python3 -m benchmarks.segmentation.run_benchmark list-strategies

python3 -m benchmarks.segmentation.run_benchmark sample-plan \
  --dataset-manifest .scratch/benchmarks/datasets/superdialseg/manifest.json \
  --split validation \
  --benchmark-tier early_signal \
  --sample-seed 42 \
  --target-size 80 \
  --output .scratch/benchmarks/segmentation/sample-plans/superdialseg-tier1.json

python3 -m benchmarks.segmentation.run_benchmark run \
  --dataset-manifest .scratch/benchmarks/datasets/superdialseg/manifest.json \
  --benchmark-tier smoke \
  --strategy fixed_token_windows \
  --strategy message_groups \
  --output-dir .scratch/benchmarks/segmentation

python3 -m benchmarks.segmentation.run_benchmark run \
  --dataset-manifest .scratch/benchmarks/datasets/superdialseg/manifest.json \
  --benchmark-tier early_signal \
  --sample-plan .scratch/benchmarks/segmentation/sample-plans/superdialseg-tier1.json \
  --early-signal-thresholds benchmarks/segmentation/fixtures/early_signal_thresholds.example.json \
  --strategy fixed_token_windows \
  --strategy message_groups \
  --output-dir .scratch/benchmarks/segmentation

python3 -m benchmarks.segmentation.run_benchmark score \
  --results .scratch/benchmarks/segmentation/<run_id>/run.json

python3 -m benchmarks.segmentation.run_benchmark report \
  --results .scratch/benchmarks/segmentation/<run_id>/run.json \
  --format both \
  --max-parents 25
```

`--allow-local-models` is the model execution opt-in flag. Local-model
strategies refuse to run without it and also refuse non-loopback base URLs.
They use the benchmark-local D034 JSON-schema request profile against an
operator-managed local OpenAI-compatible endpoint.

## Strategies

- `fixed_token_windows`: deterministic fixed estimated-token windows with
  configurable `--target-tokens` and `--overlap-messages`.
- `message_groups`: deterministic contiguous role-turn grouping that keeps
  adjacent user/assistant turns together when possible.
- `qwen_35b_a3b_iq4_xs_d034`,
  `qwen_27b_q5_k_m_d034`,
  `gemma_26b_a4b_q4_k_m_d034`: local-model strategies for the public short
  benchmark. They require `--allow-local-models`, constrain `message_ids` to
  the current parent in the JSON schema, parse only
  `choices[0].message.content`, and record request/model metadata.

`StrategyKind` is benchmark-internal. It is not production
`segments.window_strategy` and does not introduce deferred P-FRAG schema values
from D039.

## Results

Runs write only under the caller's output directory:

```text
<output-dir>/<run_id>/
  run.json
  parents.jsonl
  score.json   # written by the score command
  report.md    # written by the report command
  report.html  # written by the report command when requested
```

`run.json` records git commit, dataset manifest metadata, strategy config,
benchmark tier, selection caveat, sample-plan summary when supplied,
threshold-set metadata when supplied,
scoring version, token estimator version, relevant `ENGRAM_SEGMENTER_*`
environment variables, model metadata for local-model strategies, and explicit
`not_run` model fields for deterministic runs. Empty environment capture is
recorded explicitly with a note.
Claim-utility metrics currently report `not_run` with denominators; no
benchmark extractor is implemented in this pass. Deterministic strategies
report schema validity as `not_applicable` because they do not exercise LLM
JSON/schema parsing.
Tier 1 `run.json` and `score.json` include `early_signal_verdicts` keyed by
strategy. If thresholds are absent, verdict generation cannot emit
`candidate`.

`report` reads only the existing result artifacts. It writes strategy
comparison tables, segment-length tables, fragmentation tables, early-signal
verdict tables when present, backend error counts, and per-parent boundary
diagrams. `--max-parents` bounds per-parent detail for large public snapshots.

## Fixtures

Synthetic parent fixtures and expected claims use JSONL with a required header.
Expected segments include both `message_ids` and `embeddable_message_ids` so
tool/null/image placeholders can remain provenance without becoming embedded
text. Claim matching normalization is pinned to Unicode NFKC, `casefold()`,
whitespace collapse, and no punctuation stripping.

The committed threshold file is non-normative fixture/example data for tests.
RFC 0008 Open Question 1 still owns real Engram threshold selection.
