# Segmentation Benchmark Specification

Status: implemented offline deterministic harness with RFC 0008 Tier 0/Tier 1
early-signal support; Tier 2 decision-grade support pending

This benchmark is a local-only, scratch-only development tool for comparing
segmentation strategies before changing production Phase 2 behavior. It does
not mutate production tables, production migrations, or the production
segmenter runtime.

This specification incorporates RFC 0006 and RFC 0008. D041 makes the harness
public-first. D042 makes model-selection benchmarking tiered and
fragmentation-aware.

## Principles

- No cloud dependency and no user data leaving the machine.
- No automatic public dataset download.
- No ik-llama, Ollama, Hugging Face, hosted service, telemetry, or production
  database call during deterministic runs or tests.
- Public datasets are local snapshots described by manifests.
- Benchmark strategy names and `StrategyKind` values are benchmark-internal;
  they are not production `segments.window_strategy` values and do not land
  deferred P-FRAG schema values from D039.
- RFC 0008 / D042 Tier 0 and Tier 1 runs declare their benchmark tier and
  selection caveat. Tier 2 decision-grade runner support is pending.
- Raw boundary metrics are audit data; model-selection recommendations use
  the tier-specific verdict rules below.

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

## Benchmark Tiers

Status: implemented for `smoke` and `early_signal`; `decision` remains pending.
New result artifacts emit `benchmark_tier`, `selection_caveat`, optional
sample-plan metadata, optional threshold-set metadata, fragmentation metrics,
and Tier 1 verdict fields. Existing scratch artifacts are not backfilled.

Benchmark runs are classified by `benchmark_tier`.

### Tier 0: `smoke`

Purpose: validate that the harness and candidate model/profile can run.

Required shape:

- 10 labeled SuperDialseg validation parents;
- deterministic strategy/model configuration;
- local-only execution;
- result, score, and report artifacts written successfully.

Tier 0 reports `selection_caveat: smoke_only`. It may answer whether a
candidate is ready for a larger benchmark. It must not be used to choose a
production segmenter model/profile.

### Tier 1: `early_signal`

Purpose: provide cheap but meaningful model triage before a long run.

Required shape:

- 60-100 deterministic, stratified SuperDialseg validation parents;
- the full synthetic Engram-proxy fixture set;
- optional LMSYS-Chat-1M operational-shape sample only when the dataset has
  already been accepted and downloaded locally;
- current operational model/profile, active challenger models, and cheap
  deterministic baselines.

Tier 1 produces `early_signal_verdicts` keyed by strategy, with each verdict
set to `reject`, `defer`, `longer_run`, or `candidate`. A challenger does not
become the operational choice from Tier 1 alone; `candidate` means schedule a
Tier 2 decision run.

### Tier 2: `decision`

Purpose: support a production model/profile change.

Required shape:

- several hundred SuperDialseg parents or the full validation split;
- the full synthetic Engram-proxy fixture set;
- optional LMSYS-Chat-1M operational-stress slice when locally permitted;
- repeated runs when the local backend or candidate model shows meaningful
  variance.

Tier 2 can justify changing the production segmenter model/profile. The
current operational model may remain the default even when a challenger wins
raw boundary F1 if the challenger loses the combined verdict after
fragmentation and proxy-fixture checks.

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
  It emits benchmark parents plus boundary positions between utterances. When
  any usable `segmentation_label` values are present for a parent, labels are
  the authoritative boundary source: `segmentation_label=1` means the boundary
  is after that turn, so the recorded boundary position is
  `sequence_index + 1`, with no boundary after the final turn. `topic_id`
  changes are used only when segmentation labels are absent from that parent.
- `lmsys_chat_1m`: consumes JSONL local exports with `conversation_id` and
  message rows or message arrays. It emits parents with `expected_boundaries`
  set to null.

## Sample Plans

Status: implemented for SuperDialseg `smoke` and `early_signal` sample plans.
Decision-grade sample plans are pending.

Sample plan schema version: `segmentation-benchmark-sample-plan.v1`.

Tier 0 may use a fixed 10-parent smoke sample, but Tier 1 and Tier 2 sample
selection must be deterministic and recorded. A sample plan records:

- schema version;
- benchmark tier;
- dataset name/source/version/revision;
- split;
- fixed sample seed;
- selected parent ids in run order;
- stratum assignment per selected parent;
- expected boundary count distribution;
- message count distribution.

Tier 1 SuperDialseg selection must be stratified across:

- no-boundary parents;
- 1-2 boundary parents;
- 3-5 boundary parents;
- high-boundary-count parents;
- short dialogues;
- medium dialogues;
- long dialogues near the benchmark context budget;
- mixed role patterns when present in the dataset.

The harness must not implement Tier 1 as "first N parents" from the dataset.
The selected parent ids are part of the audit trail and must be stable for a
given dataset revision, split, seed, and sample-plan implementation version.
If a stratum has fewer parents than its target quota, the sample plan takes all
available parents from that stratum, records the actual stratum sizes and
shortfall, and fails validation only if the total Tier 1 sample falls below 60
parents.
Tier 1 `run` requires `--sample-plan`; otherwise the run would not satisfy the
stratification and shortfall audit contract.
`dataset.revision` records the manifest's `local_path_sha256` when available.
Run-time validation rejects a plan when both plan and manifest revisions are
set and disagree.

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

## Engram Proxy Fixtures

Status: implemented as a small public synthetic fixture set. It remains a
regression/proxy layer, not the primary benchmark substrate.

Tier 1 and Tier 2 include the full synthetic fixture set. Fixtures remain
small, public, and hand-authored; they are not a replacement for private
corpus evaluation.

The fixture set must cover these Engram-specific memory-unit failure modes:

- long coding/debugging threads;
- topic re-entry after interruption;
- repeated or near-duplicate facts;
- quiet durable preference inside noisy conversation;
- tool/file artifact placeholders;
- null/image/tool-only messages;
- privacy-tier mixed spans;
- JSON-looking content;
- one-segment conversations;
- conversations near the context guard.

Proxy fixture scoring reports:

- expected span F1;
- expected segment-count distance;
- provenance validity;
- embeddable text validity;
- sub-floor fragment counts;
- whether tool/file placeholders stayed provenance-only.

Proxy fixtures do not dominate public boundary metrics, but they may veto a
candidate whose output is incompatible with Engram's memory-unit requirements.

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
Token estimator version: `segmentation-benchmark-token-estimator.v2`.

- `fixed_token_windows`: groups messages into deterministic estimated-token
  windows. It preserves message order, does not split a single message, records
  over-target single-message segments in raw metadata, and builds
  `content_text` only from embeddable messages.
- `message_groups`: groups contiguous messages up to the target token budget
  while keeping adjacent user/assistant turns together when possible.
- `qwen_35b_a3b_iq4_xs_d034`, `qwen_27b_q5_k_m_d034`,
  `gemma_26b_a4b_q4_k_m_d034`: benchmark-local model strategies. They refuse
  to run unless `--allow-local-models` is provided, refuse non-loopback base
  URLs, and call the operator-managed local OpenAI-compatible endpoint with the
  D034 deterministic JSON-schema request profile.

The estimator is deliberately local and simple; it does not import production
segmenter code. It uses `ceil(chars / 2.5)`, matching production's default
`ENGRAM_SEGMENTER_CONTEXT_GUARD_CHARS_PER_TOKEN` calibration.

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
  --operational-model-strategy qwen_35b_a3b_iq4_xs_d034 \
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

Current implemented `run.json` records:

- git commit;
- benchmark tier and selection caveat;
- operational model strategy used for early-signal comparisons;
- dataset manifest/schema version, dataset name/source/snapshot/version,
  preprocessing version, and license metadata;
- fixture version/schema version and expected-claims schema version when
  fixtures are included;
- sample plan summary when supplied;
- early-signal threshold set when supplied;
- early-signal verdicts for Tier 1 runs;
- strategy name/kind/config/version;
- scoring implementation version;
- token estimator version;
- relevant `ENGRAM_SEGMENTER_*` environment variables;
- dataset kind/name/snapshot;
- UTC creation timestamp;
- explicit deterministic-run model fields with null or `not_run` values, or
  local model metadata for local-model strategies.

Existing scratch artifacts are not backfilled when planned fields are added.

Local model SHA256 capture is opt-in with `--compute-model-sha256` because the
GGUF files are large enough that hashing can materially extend a short run.

Report schema version: `segmentation-benchmark-report.v1`.

Reports include:

- run metadata;
- strategy comparison table;
- segment-length and sub-floor fragment table;
- fragmentation quality table;
- early-signal verdict table when present;
- backend error count table;
- per-parent boundary diagrams comparing expected and predicted boundaries.

`--max-parents` bounds per-parent detail so large public snapshots do not
produce unreviewable reports by default.

## Scoring

Scoring implementation version: `segmentation-benchmark-scoring.v2`.

The early-signal revision is a semantic scoring change and must bump
`SCORING_IMPLEMENTATION_VERSION` when implemented. The implementation may keep
the JSON schema version when it only adds backward-compatible fields.

Operational metrics:

- schema-valid rate for LLM JSON/schema outputs. Deterministic constructed
  strategies report `not_applicable`; provenance-valid rate remains meaningful
  for every strategy.
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
- average and median segments per parent;
- p10/p50/p90 segment estimated token length;
- strict boundary precision/recall/F1;
- window-tolerant F1 at +/-1 and +/-2 message positions;
- P_k;
- WindowDiff;
- boundary over-split and under-split counts.

Fragmentation metrics:

Status: implemented for public and fixture parents. Label-dependent metrics
report `not_applicable` for unlabeled datasets.

- predicted/expected segment-count ratio for labeled parents;
- absolute segment-count distance from expected;
- no-boundary false split count and rate;
- sub-50, sub-100, and sub-200 estimated-token fragment rates;
- adjacent tiny-fragment rate;
- duplicate or near-duplicate adjacent summary/content rate;
- count of parents with more than twice the expected segment count.

Engram proxy fixture metrics:

- expected span precision/recall/F1;
- expected segment-count distance;
- provenance-valid rate;
- embeddable-text-valid rate;
- sub-floor fragment counts;
- tool/file placeholder leakage count.

For unlabeled datasets such as LMSYS-Chat-1M, label-dependent metrics report
`not_applicable`, never zero.

## Early-Signal Verdict

Status: implemented for Tier 1 early-signal verdicts. Threshold values remain
explicit input via `--early-signal-thresholds`; the example threshold file is
non-normative test/example data.

Tier 1 `score.json` and `run.json` include an `early_signal_verdicts` object
keyed by strategy. Each strategy value has this shape:

```json
{
  "schema_version": "segmentation-benchmark-early-signal-verdict.v1",
  "verdict": "longer_run",
  "selection_caveat": "early_signal_not_decision_grade",
  "summary": "Promising boundary quality, but requires Tier 2 before model change.",
  "hard_warnings": [],
  "blocking_failures": [],
  "metric_reasons": {
    "schema_valid_rate": {"value": 1.0, "threshold": 1.0},
    "provenance_valid_rate": {"value": 1.0, "threshold": 1.0},
    "no_boundary_false_split_rate": {"value": 0.02, "threshold": "tbd"}
  },
  "threshold_set": {
    "schema_version": "segmentation-benchmark-early-signal-thresholds.v1",
    "status": "tbd",
    "source": "RFC 0008 Open Question 1"
  }
}
```

Allowed verdicts:

- `reject`: fails schema/provenance safety, has unacceptable backend failures,
  or shows severe fragmentation.
- `defer`: valid, but not enough improvement to justify more compute.
- `longer_run`: promising, but evidence is insufficient for a production
  change.
- `candidate`: strong enough on Tier 1 to schedule a Tier 2 decision run.

Required gates:

- schema-valid rate is 1.0 for local-model strategies, or every failure is
  explained in `blocking_failures`;
- provenance-valid rate is 1.0;
- no backend wedge, CUDA OOM, or runaway completion on Tier 1;
- no-boundary false split rate is low and called out whenever nonzero;
- average segment count does not exceed expected count by more than the
  configured multiplier unless proxy metrics justify it;
- sub-100 fragment rate stays below the configured threshold unless expected
  by fixture labels;
- boundary metrics beat deterministic baselines and the current operational
  model after fragmentation penalties before a challenger can receive
  `candidate`.

Threshold defaults for fragmentation gates are not specified yet; they are
tracked by RFC 0008 Open Question 1. The implementation must write the
threshold set, source, and any overrides into `run.json` and `score.json` so
verdicts are reproducible across runs.

Tier 0 reports only smoke readiness, not `candidate`. Tier 2 reports a
decision recommendation rather than an early-signal verdict.

## Schema Version Discipline

`schema_version` bumps on breaking JSON shape changes: field rename, removal,
new required field, or type narrowing. Backward-compatible additions stay on
the same schema version. Semantic scoring changes bump
`SCORING_IMPLEMENTATION_VERSION`.
