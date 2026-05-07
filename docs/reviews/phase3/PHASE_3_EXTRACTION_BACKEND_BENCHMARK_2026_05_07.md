<a id="review-0031"></a>
# Phase 3 Extraction Backend Benchmark: RFC 0019

Review ID: REVIEW-0031

Date: 2026-05-07

Status: findings

Related artifacts:

- RFC 0019: Continuous-Batching Inference Server for Phase 3 Claim Extraction
- D020: local-only inference
- D034: JSON-schema local model response profile
- D068: review artifact IDs

## Verdict

Do not promote vLLM or sglang as the Phase 3 claim-extraction backend from this
run.

The best vLLM configuration was faster than the current `ik_llama` production
run on raw segment throughput: 0.1631 segments/sec at client concurrency 8,
versus 0.0894 segments/sec for the production `ik_llama` v10 full-corpus pass.
That is a 1.82x speedup on aggregate segment throughput.

The speedup is not usable as a production replacement because the same vLLM run
only completed 71 of 100 benchmark segments, emitted 67 inserted claims, and
failed 29 segments. The current `ik_llama` v10 production outputs for the same
100 segment ids completed all 100 segments and inserted 506 claims. The vLLM
configuration that could run on the 24 GiB GPU did so by using a 4096-token
model context; 20 of the benchmark failures were context-budget failures caused
by that cap. Attempts closer to the needed 8192-token production context either
failed readiness, exhausted KV-cache headroom, or OOMed during requests.

sglang did not reach a comparable benchmark run with the tested model
artifacts. The AWQ snapshot declares a `compressed-tensors` quantization format
that failed during sglang's Marlin repack path, and the local GGUF path did not
load through the tested sglang CLI shape.

## Privacy And Scope

This report is redacted. It records commands, aggregate counts, configuration
flags, error classes, and artifact paths only. It does not include raw message
text, segment text, prompt payloads, model completions, conversation titles,
claim values, belief values, private names, or corpus-derived prose summaries.

All benchmark servers were bound to `127.0.0.1`. Local model runtimes and model
artifacts were installed under `.scratch/`; scratch run outputs remain under
`.scratch/benchmarks/extraction-backend/` and are not tracked by git.

## Compared Backends

The production baseline is the current local `ik_llama` extraction backend using
`/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` and request profile
`ik-llama-json-schema.d034.v10.extractor-8192-accounted-zero`.

The primary candidate was vLLM 0.20.1 installed in `.scratch/venvs/vllm`,
serving the local snapshot
`.scratch/models/qwen3.6-35b-a3b-awq-cyankiwi`. The snapshot is
`cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`; its model config declares
`model_type = qwen3_5_moe`, architecture
`Qwen3_5MoeForConditionalGeneration`, and `compressed-tensors` 4-bit
quantization.

The secondary candidate was sglang 0.5.9 installed in
`.scratch/venvs/sglang`.

The 100-segment slice was generated with seed 19:

```bash
.venv/bin/python -m benchmarks.extraction.run_benchmark sample-slice \
  --output .scratch/benchmarks/extraction-backend/slices/rfc0019-seed19-100.json \
  --target-size 100 \
  --seed 19
```

The slice stratification was `source_kind_x_size_bucket` over ChatGPT, Claude,
and Gemini segments in short, medium, and long buckets.

## vLLM Sweep Results

All completed vLLM 100-segment runs used localhost serving, JSON-schema
response format, `--max-model-len 4096`, `--max-num-batched-tokens 4096`,
`--gpu-memory-utilization 0.95`, `--enable-prefix-caching`,
`--kv-cache-dtype fp8`, `--enforce-eager`, disabled multimodal profiling, and
`--structured-outputs-config '{"backend":"xgrammar"}'`.

| Candidate | Client concurrency | Segments ok | Segments failed | Schema-valid rate | Claims inserted | Dropped claims | Wall seconds | Segment/sec | Claim/sec | Failure classes |
|-----------|--------------------|-------------|-----------------|-------------------|-----------------|----------------|--------------|-------------|-----------|-----------------|
| vLLM c4 | 4 | 70 | 30 | 0.70 | 63 | 4 | 688.65 | 0.1452 | 0.0915 | 20 context/unknown, 9 schema-invalid, 1 local-validation |
| vLLM c8 | 8 | 71 | 29 | 0.71 | 67 | 6 | 613.21 | 0.1631 | 0.1093 | 20 context/unknown, 6 schema-invalid, 3 local-validation |
| vLLM c16 | 16 | 70 | 30 | 0.70 | 53 | 5 | 752.22 | 0.1329 | 0.0705 | 20 context/unknown, 9 schema-invalid, 1 local-validation |

The best raw throughput was vLLM c8. Increasing to c16 did not improve
throughput and reduced claim throughput. c4 was slower than c8 but had a
similar failure profile.

Prefix caching was enabled but did not contribute in the best run. vLLM metrics
for the c8 run reported nonzero prefix-cache queries, but
`vllm:prefix_cache_hits_total = 0.0`,
`vllm:prompt_tokens_by_source_total{source="local_cache_hit"} = 0.0`, and
`vllm:prompt_tokens_cached_total = 0.0`. The current request layout therefore
did not realize the prefix-cache benefit assumed by RFC 0019.

## ik_llama Baseline

The current production `ik_llama` v10 full-corpus pass recorded:

| Backend | Rows | Extracted | Failed | Claims inserted | Wall seconds | Segment/sec |
|---------|------|-----------|--------|-----------------|--------------|-------------|
| ik_llama v10 | 11177 | 11167 | 10 | 38285 | 125025.88 | 0.0894 |

For the exact 100 segment ids in the benchmark slice, the latest production
`ik_llama` v10 rows recorded:

| Backend | Slice rows found | Extracted | Failed | Claims inserted | Clean zero | Populated | Accounted zero |
|---------|------------------|-----------|--------|-----------------|------------|-----------|----------------|
| ik_llama v10 | 100 | 100 | 0 | 506 | 39 | 60 | 1 |

This same-slice comparison is the decisive quality signal. The vLLM c8 run was
1.82x faster by segment throughput but produced only 13.2% as many inserted
claims as `ik_llama` on the same segment ids and failed 29% of the segment
requests.

## Failed Candidate Attempts

The local GGUF production model was not a viable vLLM candidate in this run.
vLLM rejected the GGUF architecture with:

```text
GGUF model with architecture qwen35moe is not supported yet
```

For the AWQ/compressed-tensors snapshot, forcing `--quantization awq` was not
accepted because vLLM detected the checkpoint's declared quantization as
`compressed-tensors`. The tested vLLM version also did not expose the older
`--guided-decoding-backend` flag; the equivalent tested flag was
`--structured-outputs-config '{"backend":"xgrammar"}'`.

The recommended `--gpu-memory-utilization 0.92` setting did not leave enough KV
cache for this checkpoint on the RTX 3090 in the tested configuration. Raising
GPU memory utilization and constraining batched tokens eventually produced
successful 4096-context runs, but 8192-context attempts hit readiness, KV-cache,
or request-time memory failures.

sglang did not complete a comparable benchmark run. The tested AWQ snapshot
failed during compressed-tensors Marlin handling with a tile divisibility error,
and attempts to override quantization were rejected because the model config
declares `compressed-tensors`.

## Interpretation

RFC 0019's central performance hypothesis was partially right: continuous
batching can improve aggregate segment throughput on this workload. It was not
right enough for this hardware/model pair because the candidate configuration
that fits in memory does not preserve the production extraction contract.

The tested vLLM path changes too many variables at once: serving runtime,
quantization family, effective context window, output decoding backend, and
client concurrency. The 4096-token context cap is especially material; it drops
large segments that production `ik_llama` handles under the 8192-token request
profile. The remaining schema-invalid and local-validation failures show that
xgrammar structured output did not fully close the reliability gap.

The prefix-cache result also weakens the expected upside. The stable extraction
prompt should be a strong fit for caching, but the observed cache-hit counters
were zero in the best run. That means the measured speedup came from concurrent
batching under a smaller context budget, not from the prompt-prefix amortization
that would be needed for a clean production win.

## Decision

Keep Phase 3 production extraction on `ik_llama` for this model and single RTX
3090 setup.

Do not add a production `ENGRAM_INFERENCE_BASE_URL` abstraction or change the
production extractor request profile based on this evidence. RFC 0019 should
remain an experiment/harness result, not an accepted backend migration.

## Follow-Ups

Revisit vLLM only if a candidate can run the production-sized context window
with enough KV headroom and then pass a same-slice quality comparison against
`ik_llama`. That comparison should require 100% segment completion on the
bounded slice, materially similar claim count and predicate/stability
distribution, and no provenance or schema-validity regression before any
larger benchmark.

Investigate prompt layout only if another vLLM candidate is otherwise viable.
The c8 run's zero prefix-cache hits suggest the current chat/request shape is
not cache-friendly in vLLM, but prompt reordering would be an
`EXTRACTION_PROMPT_VERSION` event under RFC 0017 and should not be done just to
rescue this candidate.

Revisit sglang with a model artifact it supports natively. The tested
compressed-tensors snapshot was not a useful sglang signal.

If the goal is still shorter extraction wall-clock on this hardware, prioritize
multi-instance sharding or future multi-GPU sharding once the production
extraction path is stable, because those options keep the known-good `ik_llama`
quality profile while attacking wall-clock through parallelism.

## Evidence Artifacts

Scratch artifacts retained locally:

- `.scratch/benchmarks/extraction-backend/slices/rfc0019-seed19-100.json`
- `.scratch/benchmarks/extraction-backend/20260507T185034Z.vllm-awq-cyankiwi-skip-mm-gmem95-smoke-n1-ctx4k.22128532/run.json`
- `.scratch/benchmarks/extraction-backend/20260507T191745Z.vllm-compressed-gmem95-fp8-xgrammar-c4-batch4096-n100-ninjapath.9f4347d3/run.json`
- `.scratch/benchmarks/extraction-backend/20260507T193146Z.vllm-compressed-gmem95-fp8-xgrammar-c8-batch4096-n100-ninjapath.9cd9aae3/run.json`
- `.scratch/benchmarks/extraction-backend/20260507T194322Z.vllm-compressed-gmem95-fp8-xgrammar-c16-batch4096-n100-ninjapath.d6286967/run.json`
- `.scratch/benchmarks/extraction-backend/20260507T183807Z.vllm-gguf-prefix-cache-smoke-n1.e9c903c8/server.log`
- `.scratch/benchmarks/extraction-backend/20260507T191231Z.vllm-awq-override-gmem92-fp8-xgrammar-c16-n100.6aee596f/server.log`
- `.scratch/benchmarks/extraction-backend/20260507T191258Z.vllm-compressed-gmem92-fp8-xgrammar-c16-n100.4c801960/server.log`
- `.scratch/benchmarks/extraction-backend/20260507T185640Z.sglang-awq-cyankiwi-smoke-n1-ctx4k-ninjapath.0f1c972b/server.log`
- `.scratch/benchmarks/extraction-backend/20260507T185737Z.sglang-awq-cyankiwi-smoke-n1-ctx4k-abspath.b574046c/server.log`
- `.scratch/benchmarks/extraction-backend/20260507T185849Z.sglang-awq-cyankiwi-moe-wna16-smoke-n1-ctx4k.293e8ec8/server.log`
- `.scratch/benchmarks/extraction-backend/20260507T185923Z.sglang-gguf-iq4xs-smoke-n1-ctx4k.87146dfe/server.log`
