# Run Short Public Segmentation Model Benchmark

> Hand this to an implementation/execution agent after the benchmark harness
> implementation and second re-review have landed.
>
> Branch: stay on the current benchmark branch unless the operator asks for a
> new branch. If you create one, do not use a `codex` prefix.
>
> Goal: download a local public SuperDialseg snapshot, prepare the manifest the
> benchmark harness expects, and run a short segmentation benchmark comparing
> the three current local `ik_llama` model candidates. Do not use the private
> Engram corpus.

## Read First

1. `README.md`
2. `HUMAN_REQUIREMENTS.md`
3. `DECISION_LOG.md`, especially D034, D037, D038, D039, and D041.
4. `BUILD_PHASES.md`
5. `ROADMAP.md`
6. `SPEC.md`
7. `docs/schema/README.md`
8. `docs/rfcs/0006-segmentation-model-benchmark.md`
9. `benchmarks/segmentation/README.md`
10. `benchmarks/segmentation/SPEC.md`
11. `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_IMPLEMENTATION_REREVIEW_2026_05_03.md`
12. `docs/segmentation.md`

Read `benchmarks/segmentation/*.py` before changing or running the harness.
The current reviewed harness may still have local-model strategies registered
as safe placeholders; if so, implement the smallest benchmark-local model
execution path needed for this run.

## Hard Constraints

- Engram remains local-first. No private user corpus data leaves the machine.
- The only network access explicitly allowed by this task is downloading the
  public SuperDialseg dataset metadata/files from Hugging Face. Do not upload
  anything.
- Do not write the production database.
- Do not alter production migrations.
- Do not use the private Engram corpus as benchmark input.
- Keep downloaded dataset rows out of git. Use top-level `datasets/`, whose
  contents are ignored by `datasets/.gitignore`.
- Keep benchmark outputs under `.scratch/benchmarks/segmentation/`.
- Do not use `--no-context-shift` by default. It was a prior mitigation, not
  the baseline runtime shape. If a model needs it, rerun all models with the
  same flag or clearly mark that result non-comparable.
- Do not benchmark the obsolete Qwen 3.5 prior candidate. It has been removed.

## Model Set

Use exactly these three local model files:

```text
qwen_35b_a3b_iq4_xs:
  /home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf

qwen_27b_q5_k_m:
  /home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf

gemma_26b_a4b_q4_k_m:
  /home/halbritt/models/gemma-4-26B-A4B-it-GGUF/gemma-4-26B-A4B-it-Q4_K_M.gguf
```

Use the local patched `ik_llama` binary:

```text
/home/halbritt/git/ik_llama.cpp/build/bin/llama-server
```

Use the canonical local endpoint for benchmark calls:

```text
http://127.0.0.1:8081/v1/chat/completions
```

If a separate local model server is already running on another port, inspect it
and stop it if it would distort memory/CPU/GPU availability. Restore any user
services you stop at the end of the run.

## Dataset Location

Create this local layout:

```text
datasets/
  .gitignore
  superdialseg/
    raw/
    prepared/

.scratch/
  benchmarks/
    datasets/
      superdialseg/
        manifest.json
```

Download the public dataset snapshot:

```bash
mkdir -p datasets/superdialseg/raw datasets/superdialseg/prepared
hf download Coldog2333/super_dialseg --repo-type dataset --local-dir datasets/superdialseg/raw
```

Use the actual case-sensitive Hugging Face dataset repository
`Coldog2333/super_dialseg`, with `--repo-type dataset` and
`--local-dir datasets/superdialseg/raw`. The expected public files are
`train.json`, `validation.json`, `test.json`, `README.md`, and
`super_dialseg.py`.

Record the dataset revision SHA from the Hugging Face API or `hf` output. Do
not guess the license; read the dataset card/source metadata and record what
is actually present. If the license is unclear, say so in the summary rather
than inventing one.

## Prepare Harness Input

The current harness reads JSONL rows, not raw JSON arrays. Inspect
`super_dialseg.py`, `train.json`, `validation.json`, and `test.json`, then
write a local prepared JSONL export under:

```text
datasets/superdialseg/prepared/superdialseg.jsonl
```

Each row must match the harness adapter expectations:

```json
{
  "split": "validation",
  "dial_id": "public-dialog-id",
  "turn_id": 0,
  "role": "speaker",
  "utterance": "text",
  "topic_id": "optional-topic",
  "segmentation_label": 0
}
```

Preserve the paper-faithful boundary rule already reviewed in the harness:
when a parent has usable `segmentation_label` values, label `1` means a
boundary after that turn (`sequence_index + 1`), with no boundary after the
final turn. `topic_id` is only a fallback when labels are absent.

Create the manifest at:

```text
.scratch/benchmarks/datasets/superdialseg/manifest.json
```

Use:

```json
{
  "schema_version": "segmentation-public-dataset-manifest.v1",
  "dataset_name": "superdialseg",
  "dataset_source": "huggingface:Coldog2333/super_dialseg",
  "dataset_version": "<huggingface revision sha>",
  "local_path": "<absolute path to datasets/superdialseg/prepared/superdialseg.jsonl>",
  "local_path_sha256": "<sha256 of prepared JSONL>",
  "license_name": "<actual license or clearly marked unknown>",
  "license_accepted_at": null,
  "preprocessing_version": "segmentation-public-preprocess.v1",
  "created_at": "<UTC timestamp>"
}
```

Validate before any model run:

```bash
python3 -m benchmarks.segmentation.run_benchmark validate-dataset \
  --manifest .scratch/benchmarks/datasets/superdialseg/manifest.json \
  --split validation \
  --limit 10
```

Use `validation` and `--limit 10` for the first short run. If validation has
too few usable parents, use `test`; record the split decision.

## Local Model Harness Work

If the reviewed harness still raises `NotImplementedError` for local-model
strategies, add benchmark-local support only under `benchmarks/segmentation/`
and tests under `tests/`. Do not import or mutate production database code.

Requirements:

- Keep `--allow-local-models` as the explicit opt-in.
- Refuse non-local base URLs.
- Use standard-library HTTP unless an existing project dependency already
  covers the need.
- Send a D034-compatible, schema-constrained request to `ik_llama`:
  `stream=false`, `temperature=0`, `top_p=1`, bounded `max_tokens`,
  `chat_template_kwargs={"enable_thinking": false}`, and strict JSON schema
  requiring `segments[].message_ids`, `summary`, `content_text`, and `raw`.
- Constrain `message_ids` to the current parent's message ids where the local
  endpoint supports the schema.
- Parse only `choices[0].message.content`.
- Convert model output into existing `SegmentProposal` / `StrategyOutput`
  structures so existing scoring/reporting remains the authority.
- Record model path, model SHA256 if feasible, `ik_llama` `/v1/models`,
  `/props`, server args, request profile version, failures, retries, and
  per-parent latency in benchmark metadata.
- Add tests for URL locality, model opt-in, schema parsing, failed model
  responses, and result metadata. Tests must not require network, GPU, or a
  running model.

Prefer explicit strategy names:

```text
qwen_35b_a3b_iq4_xs_d034
qwen_27b_q5_k_m_d034
gemma_26b_a4b_q4_k_m_d034
```

Do not keep or run an obsolete `qwen_candidate_d034` profile unless it has
been renamed/repointed to the 27B Q5 model with clear metadata.

## Server Orchestration

Run models one at a time on `127.0.0.1:8081`. Do not leave multiple large
servers contending for the same hardware.

Before the benchmark:

1. Check for active `engram.cli segment`, `pipeline`, or manual
   `llama-server` processes.
2. Pause/stop any active segmentation run cleanly and record what you stopped.
3. Stop `ik-llama-watchdog.timer` and `openclaw-gateway.service` if they would
   interfere with long single-slot requests. Restore them at the end.
4. Stop `ik-llama-server.service` before launching alternate models manually.

For each model profile, launch the patched server with a comparable baseline
configuration. Start from the current Qwen service shape:

```bash
/home/halbritt/git/ik_llama.cpp/build/bin/llama-server \
  --model "$MODEL_PATH" \
  --host 127.0.0.1 \
  --port 8081 \
  --gpu-layers 99 \
  --ctx-size 49152 \
  --flash-attn on \
  --threads 8 \
  --parallel 1 \
  --batch-size 2048 \
  --ubatch-size 256 \
  --cache-type-k q8_0 \
  --cache-type-v q8_0 \
  --jinja
```

If a model fails to load with this shape, make the smallest necessary change
and record it. Do not silently compare results with different context,
offload, KV-cache, or context-shift settings.

For each model:

1. Start server and write logs to `.scratch/benchmarks/model-server/`.
2. Wait for `/v1/models` to return the exact model path.
3. Run a tiny schema-valid completion smoke.
4. Run the short benchmark for that model on the same manifest/split/limit.
5. Stop the server cleanly before starting the next model.

## Benchmark Command Shape

Include cheap deterministic anchors unless doing so complicates local-model
execution:

```bash
python3 -m benchmarks.segmentation.run_benchmark run \
  --dataset-manifest .scratch/benchmarks/datasets/superdialseg/manifest.json \
  --split validation \
  --limit 10 \
  --strategy fixed_token_windows \
  --strategy message_groups \
  --strategy qwen_35b_a3b_iq4_xs_d034 \
  --strategy qwen_27b_q5_k_m_d034 \
  --strategy gemma_26b_a4b_q4_k_m_d034 \
  --allow-local-models \
  --output-dir .scratch/benchmarks/segmentation/short-public-model-benchmark
```

If the runner can only execute one live local model profile per server launch,
run one model strategy per invocation with the same manifest, split, limit,
and output root, then add a small benchmark-local merge/report step or write a
manual comparison summary from the three `score.json` files. Do not change the
dataset slice between models.

After each run:

```bash
python3 -m benchmarks.segmentation.run_benchmark score \
  --results <run-json>

python3 -m benchmarks.segmentation.run_benchmark report \
  --results <run-json> \
  --format both \
  --max-parents 10
```

## Output Summary

Write a concise summary document under:

```text
docs/reviews/v1/BENCHMARK_SEGMENTATION_SHORT_PUBLIC_MODEL_RUN_2026_05_03.md
```

Include:

- dataset source, revision, prepared JSONL SHA256, split, limit, and license
  status;
- exact model file paths, file sizes, and SHA256 values if computed;
- `ik_llama` binary path and server arguments for each model;
- whether watchdog/openclaw/other local services were stopped and restored;
- strict boundary F1, window-tolerant F1, P_k, WindowDiff, provenance-valid
  rate, schema-valid rate, failures, and latency summary for each strategy;
- any model-specific deviations, crashes, retries, invalid JSON, backend
  errors, or context-budget failures;
- clear verdict about whether Qwen 27B Q5 is worth a longer benchmark.

Keep raw dataset rows and bulky model/server logs out of git. Commit only code,
tests, prompts, small manifests if appropriate, and the written summary when
the operator asks for a commit.

## Validation

At minimum run:

```bash
python3 -m py_compile benchmarks/segmentation/*.py
.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -q
python3 -m benchmarks.segmentation.run_benchmark validate-dataset \
  --manifest .scratch/benchmarks/datasets/superdialseg/manifest.json \
  --split validation \
  --limit 10
```

If you changed production-adjacent segmenter assumptions or shared test
helpers, run the broader relevant test subset and explain why.

Before finishing:

1. Stop any manually launched benchmark model server.
2. Restore `ik-llama-server.service` to the normal Qwen 3.6 35B service on
   `8081`, unless the operator asks otherwise.
3. Restore any stopped watchdog/openclaw services, unless they were already
   stopped before you began.
4. Verify `git status --short --branch`.
5. Report where the scratch results and summary document are.
