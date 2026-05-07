# Phase 3 Extraction Backend Benchmark Harness

This directory contains the RFC 0019 benchmark-only harness for comparing
local OpenAI-compatible extraction backends. It uses the production Phase 3
extractor prompt, schema, parser, chunking, and validation salvage code, but it
writes only scratch artifacts. It does not insert or update production
`claim_extractions`, `claims`, or `beliefs` rows.

The harness is for evidence gathering only. A production switch from
`ik-llama-server` to vLLM or sglang still requires benchmark review evidence,
`DECISION_LOG.md`, a new `request_profile_version`, a new
`extraction_model_version`, and RFC 0017 re-extraction handling.

## Commands

Create a fixed active-segment slice from the local production database:

```bash
ENGRAM_DATABASE_URL=postgresql:///engram \
.venv/bin/python -m benchmarks.extraction.run_benchmark sample-slice \
  --target-size 1000 \
  --seed 19 \
  --output .scratch/benchmarks/extraction-backend/slices/phase3-seed19-1000.json
```

Smoke an operator-managed local endpoint:

```bash
.venv/bin/python -m benchmarks.extraction.run_benchmark smoke \
  --allow-local-models \
  --base-url http://127.0.0.1:18081 \
  --model-id qwen-extraction-vllm-bench \
  --context-window 49152
```

Run a control or candidate backend over the fixed slice:

```bash
ENGRAM_DATABASE_URL=postgresql:///engram \
.venv/bin/python -m benchmarks.extraction.run_benchmark run \
  --allow-local-models \
  --slice .scratch/benchmarks/extraction-backend/slices/phase3-seed19-1000.json \
  --backend-name vllm-awq-int4-prefix-cache-n8 \
  --base-url http://127.0.0.1:18081 \
  --model-id qwen-extraction-vllm-bench \
  --model-path /abs/path/to/qwen-awq-or-gptq-snapshot \
  --request-profile-version vllm-json-schema.d034.extraction-benchmark.v1 \
  --concurrency 8 \
  --metrics-url http://127.0.0.1:18081/metrics \
  --output-dir .scratch/benchmarks/extraction-backend
```

Compare a control run and a candidate run:

```bash
.venv/bin/python -m benchmarks.extraction.run_benchmark compare \
  --control-run .scratch/benchmarks/extraction-backend/<control-run>/run.json \
  --candidate-run .scratch/benchmarks/extraction-backend/<candidate-run>/run.json \
  --output-dir .scratch/benchmarks/extraction-backend \
  --review-id REVIEW-NNNN \
  --review-output docs/reviews/phase3/PHASE_3_EXTRACTION_BACKEND_BENCHMARK_2026_05_07.md
```

The tracked review output is aggregate-only. Raw segment-level records stay in
`.scratch/` by default and omit claim text unless `--include-claim-text` is
explicitly passed. If the comparison report is written under `docs/reviews/`,
assign and register a `REVIEW-####` ID in `docs/artifacts/review-id-registry.md`
before committing the report.

## Optional Server Runtimes

Do not add vLLM or sglang to Engram's normal dependencies. Install them in
ignored scratch virtual environments and run them as external localhost
servers. Keep telemetry disabled where the server supports it.

Example vLLM shape:

```bash
python3.12 -m venv .scratch/venvs/vllm
. .scratch/venvs/vllm/bin/activate
pip install -U pip uv
uv pip install vllm --torch-backend=auto

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
CUDA_VISIBLE_DEVICES=0 vllm serve /abs/path/to/qwen-awq-or-gptq-snapshot \
  --host 127.0.0.1 \
  --port 18081 \
  --served-model-name qwen-extraction-vllm-bench \
  --enable-prefix-caching \
  --max-num-seqs 8 \
  --max-model-len 49152 \
  --gpu-memory-utilization 0.85 \
  --no-enable-log-requests
```

Example sglang shape:

```bash
python3.12 -m venv .scratch/venvs/sglang
. .scratch/venvs/sglang/bin/activate
pip install -U pip uv
uv pip install sglang

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export SGLANG_DISABLE_REQUEST_LOGGING=true
CUDA_VISIBLE_DEVICES=0 sglang serve \
  --model-path /abs/path/to/qwen-awq-or-gptq-snapshot \
  --host 127.0.0.1 \
  --port 18082 \
  --served-model-name qwen-extraction-sglang-bench \
  --mem-fraction-static 0.80 \
  --max-running-requests 8
```

## Artifacts

Runs write this shape under the chosen output directory:

```text
<output-dir>/<run-id>/
  run.json
  segments.jsonl
  server.log      # only when --server-command launches a managed server

<output-dir>/<comparison-id>/
  comparison.json
  report.md
```

`run.json` records backend name, model metadata, request settings,
`/v1/models`, pre-run and post-run empty-claims smokes, optional metrics
snapshots, slice metadata, aggregate validity and throughput metrics,
predicate/stability distributions, and failure counts. `segments.jsonl` records
one redacted result per segment.

When `--server-command` is used, the command must visibly bind to the same
loopback host and port as `--base-url`. The harness also sets offline /
no-telemetry environment defaults for the managed process. This is not a
replacement for an OS-level no-egress sandbox. Server stdout/stderr is discarded
by default because request logs can contain corpus text; pass
`--capture-server-log` only when request logging is disabled and the log is safe
to archive.
