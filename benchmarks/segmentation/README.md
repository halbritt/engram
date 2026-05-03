# Segmentation Benchmark Harness

This directory contains the local-only, scratch-only segmentation benchmark
harness from RFC 0006. It compares public dataset snapshots and deterministic
baseline strategies before any change to the production Phase 2 segmenter
contract.

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

## CLI

```bash
python3 -m benchmarks.segmentation.run_benchmark validate-dataset \
  --manifest .scratch/benchmarks/datasets/superdialseg/manifest.json

python3 -m benchmarks.segmentation.run_benchmark validate-fixtures \
  --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl \
  --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl

python3 -m benchmarks.segmentation.run_benchmark list-strategies

python3 -m benchmarks.segmentation.run_benchmark run \
  --dataset-manifest .scratch/benchmarks/datasets/superdialseg/manifest.json \
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

`--allow-local-models` is the only model opt-in flag. In this implementation,
LLM strategies still raise `NotImplementedError` before any model or network
call.

## Strategies

- `fixed_token_windows`: deterministic fixed estimated-token windows with
  configurable `--target-tokens` and `--overlap-messages`.
- `message_groups`: deterministic contiguous role-turn grouping that keeps
  adjacent user/assistant turns together when possible.
- `current_qwen_d034`, `qwen_candidate_d034`, `gemma_candidate_d034`: registered
  future local-model strategies that refuse to run unless explicitly opted in,
  and still do not call a model in this pass.

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
scoring version, token estimator version, relevant `ENGRAM_SEGMENTER_*`
environment variables, and explicit `not_run` model fields for deterministic
runs. Empty environment capture is recorded explicitly with a note.
Claim-utility metrics currently report `not_run` with denominators; no
benchmark extractor is implemented in this pass. Deterministic strategies
report schema validity as `not_applicable` because they do not exercise LLM
JSON/schema parsing.

`report` reads only the existing result artifacts. It writes strategy
comparison tables, segment-length tables, backend error counts, and per-parent
boundary diagrams. `--max-parents` bounds per-parent detail for large public
snapshots.

## Fixtures

Synthetic parent fixtures and expected claims use JSONL with a required header.
Expected segments include both `message_ids` and `embeddable_message_ids` so
tool/null/image placeholders can remain provenance without becoming embedded
text. Claim matching normalization is pinned to Unicode NFKC, `casefold()`,
whitespace collapse, and no punctuation stripping.
