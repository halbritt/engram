# Segmentation Benchmark Specification

Status: implemented offline deterministic harness

This benchmark is a local-only, scratch-only development tool for comparing
segmentation strategies before changing production Phase 2 behavior. It does
not mutate production tables, production migrations, or the production
segmenter runtime.

## Principles

- No cloud dependency and no user data leaving the machine.
- No automatic public dataset download.
- No ik-llama, Ollama, Hugging Face, hosted service, telemetry, or production
  database call during deterministic runs or tests.
- Public datasets are local snapshots described by manifests.
- Benchmark strategy names and `StrategyKind` values are benchmark-internal;
  they are not production `segments.window_strategy` values and do not land
  deferred P-FRAG schema values from D039.

## Dataset Order

1. **SuperDialseg** is the first quality target because it has public
   supervised dialogue-boundary labels.
2. **LMSYS-Chat-1M** is the optional operational stress target. It has no
   boundary labels by default, so label-dependent metrics report
   `not_applicable`.
3. **Synthetic fixtures** are small regression traps and edge-case tests, not
   the primary benchmark substrate.

No public dataset rows are committed. The committed
`fixtures/superdialseg_shape.synthetic.jsonl` file is hand-authored shape data
for tests only and is explicitly not copied from SuperDialseg.

## Public Dataset Manifest

Manifest schema version: `segmentation-public-dataset-manifest.v1`.

```json
{
  "schema_version": "segmentation-public-dataset-manifest.v1",
  "dataset_name": "superdialseg",
  "dataset_source": "huggingface:Coldog2333/super_dialseg",
  "dataset_version": "snapshot-or-commit-id",
  "local_path": "/abs/path/to/local/jsonl-or-directory",
  "local_path_sha256": "sha256 over manifest-relevant file list",
  "license_name": "apache-2.0",
  "license_accepted_at": null,
  "preprocessing_version": "segmentation-public-preprocess.v1",
  "created_at": "2026-05-03T00:00:00Z"
}
```

Validation checks schema version, dataset name/source/version, local path
existence, license metadata, and preprocessing version. Gated datasets such as
LMSYS-Chat-1M require `license_accepted_at`.

Adapters:

- `superdialseg`: consumes JSONL local exports with `dial_id`, ordered
  `utterance`, `role`, `turn_id`, `topic_id`, and/or `segmentation_label`.
  It emits benchmark parents plus boundary positions between utterances.
- `lmsys_chat_1m`: consumes JSONL local exports with `conversation_id` and
  message rows or message arrays. It emits parents with `expected_boundaries`
  set to null.

## Fixture Schema

Fixture schema version: `segmentation-fixtures.v1`.
Expected-claims schema version: `segmentation-expected-claims.v1`.

The first JSONL line is a header:

```json
{
  "record_type": "header",
  "fixture_version": "0.1.0",
  "schema_version": "segmentation-fixtures.v1",
  "description": "Synthetic fixtures only; no real user data."
}
```

Each fixture record has ordered messages and expected segments:

```json
{
  "record_type": "fixture",
  "fixture_id": "multi_topic_reentry_001",
  "source_kind": "chatgpt",
  "parent_id": "00000000-0000-4000-8000-000000000101",
  "privacy_tier": 1,
  "messages": [
    {
      "id": "00000000-0000-4000-8000-000000001001",
      "sequence_index": 0,
      "role": "user",
      "content_text": "Synthetic text.",
      "privacy_tier": 1,
      "placeholders": []
    }
  ],
  "expected_segments": [
    {
      "segment_id": "s1",
      "message_ids": ["00000000-0000-4000-8000-000000001001"],
      "embeddable_message_ids": ["00000000-0000-4000-8000-000000001001"],
      "topic_label": "short label",
      "summary": "Expected topic summary.",
      "expected_claim_ids": ["c1"]
    }
  ]
}
```

`message_ids` are provenance. `embeddable_message_ids` are the subset whose
message bodies may contribute to benchmark segment `content_text`.
Tool/file/null/image placeholders can remain in `message_ids` without becoming
embeddable text.

Validation reports all discovered errors: invalid UUIDs, duplicate message
ids, unordered message ids, unknown parent-local references,
`embeddable_message_ids` not contained in `message_ids`, and bad expected-claim
references.

## Claim Matching

Claim matching normalization is fixed for reproducibility:

1. Unicode NFKC normalization.
2. `casefold()`.
3. Collapse whitespace runs to one space.
4. Preserve punctuation.

Changing this rule requires a scoring implementation version bump.

Claim utility metrics currently report `not_run` with denominators because no
benchmark extractor is implemented in this pass.

## Strategies

Strategy implementation version: `segmentation-benchmark-strategy.v1`.
Token estimator version: `segmentation-benchmark-token-estimator.v1`.

- `fixed_token_windows`: groups messages into deterministic estimated-token
  windows. It preserves message order, does not split a single message, records
  over-target single-message segments in raw metadata, and builds
  `content_text` only from embeddable messages.
- `message_groups`: groups contiguous messages up to the target token budget
  while keeping adjacent user/assistant turns together when possible.
- `current_qwen_d034`, `qwen_candidate_d034`, `gemma_candidate_d034`: registered
  local-model strategies. They refuse to run unless `--allow-local-models` is
  provided, and even then raise `NotImplementedError` before any network or
  model access in this implementation.

The estimator is deliberately local and simple; it does not import production
segmenter code.

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

`run` validates the dataset manifest first, runs requested deterministic
strategies over the local snapshot, writes scratch artifacts, and prints the
`run.json` path. Unknown strategies and unavailable LLM strategies exit
nonzero.

`report` reads existing result files only. It does not load dataset snapshots,
rerun strategies, call models, or touch production state.

## Results

Result schema version: `segmentation-benchmark-result.v1`.

```text
<output-dir>/<run_id>/
  run.json
  parents.jsonl
  score.json
  report.md
  report.html
```

`run.json` records:

- git commit;
- dataset manifest/schema version, dataset name/source/snapshot/version,
  preprocessing version, and license metadata;
- fixture version/schema version and expected-claims schema version when
  fixtures are included;
- strategy name/kind/config/version;
- scoring implementation version;
- token estimator version;
- relevant `ENGRAM_SEGMENTER_*` environment variables;
- dataset kind/name/snapshot;
- UTC creation timestamp;
- explicit deterministic-run model fields with null or `not_run` values.

Large local model SHA256 values are not recomputed on every run. Future model
strategies must use a scratch sidecar manifest keyed by absolute path, mtime,
and size; stale entries invalidate when mtime or size changes.

Report schema version: `segmentation-benchmark-report.v1`.

Reports include:

- run metadata;
- strategy comparison table;
- segment-length and sub-floor fragment table;
- backend error count table;
- per-parent boundary diagrams comparing expected and predicted boundaries.

`--max-parents` bounds per-parent detail so large public snapshots do not
produce unreviewable reports by default.

## Scoring

Scoring implementation version: `segmentation-benchmark-scoring.v1`.

Operational metrics:

- schema-valid rate;
- provenance-valid rate;
- unknown, cross-parent, and unordered message id counts;
- empty embeddable segment count;
- sub-floor fragment counts at 50, 100, and 200 estimated tokens;
- parent throughput for deterministic strategies;
- timeout, runaway, and backend error counts.

Backend error classes:

```text
connect_refused
read_timeout
http_5xx
grammar_stack_empty
cuda_oom
backend_wedge_post_smoke
unknown
```

Segmentation metrics:

- segment count per parent;
- p10/p50/p90 segment estimated token length;
- strict boundary precision/recall/F1;
- window-tolerant F1 at +/-1 and +/-2 message positions;
- P_k;
- WindowDiff;
- boundary over-split and under-split counts.

For unlabeled datasets such as LMSYS-Chat-1M, label-dependent metrics report
`not_applicable`, never zero.

## Schema Version Discipline

`schema_version` bumps on breaking JSON shape changes: field rename, removal,
new required field, or type narrowing. Backward-compatible additions stay on
the same schema version. Semantic scoring changes bump
`SCORING_IMPLEMENTATION_VERSION`.
