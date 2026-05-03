# Short Public Segmentation Model Benchmark Run - 2026-05-03

## Scope

This run executed the benchmark-local segmentation harness on the public
SuperDialseg validation split. It did not use the private Engram corpus, did
not write the production database, and did not alter production migrations.

## Dataset

| Field | Value |
| --- | --- |
| Source | `huggingface:Coldog2333/super_dialseg` |
| Revision | `3adf26a8241078ddd5f8731f778c1e76ca851d2b` |
| License | `apache-2.0` |
| Raw snapshot | `datasets/superdialseg/raw/` |
| Prepared JSONL | `datasets/superdialseg/prepared/superdialseg.jsonl` |
| Prepared SHA256 | `8bdc3870d3f6efcef380460d282b488a3681745a4b166fe4a5c9dd9f2c0b1e17` |
| Manifest | `.scratch/benchmarks/datasets/superdialseg/manifest.json` |
| Split and limit | `validation`, `limit=10` |
| Rows prepared | `125746` turns across `9478` dialogues |

Prepared rows are ignored by `datasets/.gitignore`. The benchmark interpreted
`segmentation_label=1` as a boundary after the labeled turn, with `topic_id`
only as fallback when labels are absent.

## Harness Change

The local-model strategies were no longer placeholders for this run. The
benchmark harness now provides a benchmark-local OpenAI-compatible HTTP client
using the standard library, refuses non-loopback base URLs, keeps
`--allow-local-models` as the opt-in gate, and sends D034-style deterministic
JSON-schema requests with:

- `stream=false`
- `temperature=0`
- `top_p=1`
- bounded `max_tokens`
- `chat_template_kwargs={"enable_thinking": false}`
- strict `SegmentationResult` JSON schema
- `message_ids` enum-constrained to the current parent

The parser reads only `choices[0].message.content` and records model path, file
size, `/v1/models`, `/props`, server args, request profile, failures, and
per-parent latency in scratch results. Model GGUF SHA256 values were not
computed for this short run.

## Models

| Strategy | Model path | Size bytes | SHA256 |
| --- | --- | ---: | --- |
| `qwen_35b_a3b_iq4_xs_d034` | `/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` | `18806446400` | not computed |
| `qwen_27b_q5_k_m_d034` | `/home/halbritt/models/Qwen3.6-27B-Q5_K_M.gguf` | `19509790944` | not computed |
| `gemma_26b_a4b_q4_k_m_d034` | `/home/halbritt/models/gemma-4-26B-A4B-it-GGUF/gemma-4-26B-A4B-it-Q4_K_M.gguf` | `16796015136` | not computed |

Server binary:
`/home/halbritt/git/ik_llama.cpp/build/bin/llama-server`
(`8750288` bytes).

Server args for each manual launch:

```text
--host 127.0.0.1
--port 8081
--gpu-layers 99
--ctx-size 49152
--flash-attn on
--threads 8
--parallel 1
--batch-size 2048
--ubatch-size 256
--cache-type-k q8_0
--cache-type-v q8_0
--jinja
```

No obsolete `qwen_candidate_d034` or Qwen 3.5 profile was run.

## Service Handling

Before the model runs, no active `engram.cli segment`, `make segment`, or
`make pipeline` process was found. `ik-llama-server.service` was active on the
normal Qwen 35B model and was stopped before manual launches.
`ik-llama-watchdog.timer` and `openclaw-gateway.service` were already inactive
and were left in that prior state.

Each model was launched manually on `127.0.0.1:8081`, checked with
`/v1/models`, smoke-tested with a tiny D034 JSON-schema completion, benchmarked,
and stopped. The normal `ik-llama-server.service` was restored afterward and
confirmed serving `/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf`.

Gemma's first smoke used `max_tokens=128` and returned truncated invalid JSON.
The smoke was retried with bounded `max_tokens=512`, passed, and the benchmark
then ran successfully. No model benchmark used `--no-context-shift`.

## Results

All rows are the 10-parent SuperDialseg validation slice. Throughput is parent
calls per second for the measured strategy.

| Strategy | Schema valid | Provenance valid | Segments | Parent/s | Strict F1 | Strict P | Strict R | W-F1 +/-1 | W-F1 +/-2 | Pk | WindowDiff |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `fixed_token_windows` | n/a | `1.000` | `29` | `11189.975` | `0.230` | `0.317` | `0.192` | `0.612` | `0.646` | `0.389` | `0.389` |
| `message_groups` | n/a | `1.000` | `29` | `12655.137` | `0.230` | `0.317` | `0.192` | `0.612` | `0.646` | `0.389` | `0.389` |
| `qwen_35b_a3b_iq4_xs_d034` | `1.000` | `0.900` | `25` | `0.159` | `0.349` | `0.508` | `0.317` | `0.399` | `0.472` | `0.353` | `0.361` |
| `qwen_27b_q5_k_m_d034` | `1.000` | `1.000` | `28` | `0.039` | `0.552` | `0.675` | `0.517` | `0.552` | `0.552` | `0.234` | `0.234` |
| `gemma_26b_a4b_q4_k_m_d034` | `1.000` | `1.000` | `39` | `0.149` | `0.735` | `0.825` | `0.725` | `0.735` | `0.735` | `0.234` | `0.234` |

Backend error counts, timeout counts, runaway counts, and schema-invalid counts
were zero for all completed benchmark runs. Qwen 35B had one provenance
ordering failure in `public:superdialseg:004c3a9f9f24203151aa259f8db7a8f8`.

## Artifacts

| Run | `run.json` |
| --- | --- |
| Deterministic baselines | `.scratch/benchmarks/segmentation/short-public-model-benchmark/deterministic/20260503T224756Z.superdialseg.6e38602c/run.json` |
| Qwen 35B | `.scratch/benchmarks/segmentation/short-public-model-benchmark/qwen_35b_a3b_iq4_xs_d034/20260503T224958Z.superdialseg.192e1989/run.json` |
| Qwen 27B | `.scratch/benchmarks/segmentation/short-public-model-benchmark/qwen_27b_q5_k_m_d034/20260503T225501Z.superdialseg.b39b169c/run.json` |
| Gemma 26B | `.scratch/benchmarks/segmentation/short-public-model-benchmark/gemma_26b_a4b_q4_k_m_d034/20260503T225742Z.superdialseg.d3e9cec5/run.json` |

Markdown and HTML reports were written next to each `run.json`. Server logs
were written under `.scratch/benchmarks/model-server/`.

## Verdict

Qwen 27B Q5 is worth a longer benchmark as a Qwen-family candidate because it
substantially improved strict boundary F1 over the current Qwen 35B profile and
kept schema/provenance validity at `1.000` on this slice. It is not the leading
candidate from this short run: it was much slower than Qwen 35B, and Gemma 26B
produced the strongest boundary metrics at roughly Qwen 35B throughput. A
longer benchmark should include both Qwen 27B and Gemma 26B rather than
promoting Qwen 27B alone.

## Validation

Completed:

```text
python3 -m py_compile benchmarks/segmentation/*.py
.venv/bin/python -m pytest tests/test_benchmark_segmentation.py -q
python3 -m benchmarks.segmentation.run_benchmark validate-dataset --manifest .scratch/benchmarks/datasets/superdialseg/manifest.json --split validation --limit 10
.venv/bin/python -m pytest -q
```

Final test result: `32 passed, 38 skipped`.
