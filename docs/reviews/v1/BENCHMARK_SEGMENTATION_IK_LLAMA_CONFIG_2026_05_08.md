<a id="review-0032"></a>
# Segmentation ik_llama Config Benchmark

Review ID: REVIEW-0032
Status: findings
Date: 2026-05-08
RFC refs:
  - RFC-0008
  - RFC-0010
Decision refs:
  - D034
  - D042
Phase refs:
  - PHASE-0002

## Redaction Boundary

This report records only commands, aggregate metrics, server flags, error
classes, and scratch artifact paths. It does not include private corpus data,
SuperDialseg dialogue text, synthetic fixture text, prompt payloads, model
completions, conversation titles, claim values, or user-derived prose
summaries.

All model endpoints were bound to `127.0.0.1`. Dataset-backed runs used the
local public SuperDialseg validation snapshot and committed synthetic
segmentation fixtures only. No production database tables were written.

## Scope

The goal was to test whether the Phase 2 segmentation server profile should
move beyond the RFC 0010 control shape, especially after the Phase 3 extraction
run showed better prefill behavior with larger physical micro-batches.

The tested model was the current Qwen 35B A3B IQ4_XS local GGUF. The control
shape was:

```text
--ctx-size 49152
--parallel 1
--batch-size 2048
--ubatch-size 256
--cache-type-k q8_0
--cache-type-v q8_0
--flash-attn on
--threads 8
--gpu-layers 99
--jinja
```

The benchmark did not test vLLM or sglang. The recent Phase 3 extraction
backend benchmark showed that vLLM's raw throughput win came with unacceptable
context and correctness regressions on this hardware/model setup.

## Raw llama-bench Ladder

The committed `benchmarks.segmentation.run_benchmark llama-bench` wrapper
failed against the local `ik_llama` `llama-bench` binary because it passes a
`-c` context-size argument that this binary does not accept. The raw binary was
therefore run directly with the same model, `-p 2048`, `-n 512`, `-r 3`,
`-b 2048`, q8 KV cache, flash attention, and four `-ub` values.

| `ubatch` | Prompt tokens/sec | Generation tokens/sec | Status |
| ---: | ---: | ---: | --- |
| 256 | 2564.69 | 166.17 | ok |
| 512 | 3488.00 | 165.98 | ok |
| 1024 | 4331.07 | 166.05 | ok |
| 2048 | 4916.40 | 166.29 | ok |

The raw prefill result is clear: `ubatch=2048` was about `1.92x` faster than
`ubatch=256` for prompt processing. Generation throughput was effectively
unchanged.

## Public Smoke Matrix

Each profile ran 10 SuperDialseg validation parents through the public
segmentation benchmark harness. All runs used D034-style JSON-schema requests
with `max_tokens=4096`.

| Profile | Wall sec | Wall parent/s | Schema valid | Provenance valid | Strict F1 | Pk | WindowDiff | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `parallel=1 batch=2048 ubatch=256` | 63 | 0.159 | 1.000 | 0.900 | 0.349 | 0.353 | 0.361 | one unordered-id provenance failure |
| `parallel=1 batch=2048 ubatch=512` | 62 | 0.161 | 1.000 | 0.900 | 0.283 | 0.364 | 0.364 | one unordered-id provenance failure |
| `parallel=1 batch=2048 ubatch=1024` | 62 | 0.161 | 1.000 | 0.900 | 0.349 | 0.353 | 0.361 | one unordered-id provenance failure |
| `parallel=1 batch=2048 ubatch=2048` | 62 | 0.161 | 1.000 | 1.000 | 0.423 | 0.309 | 0.309 | cleanest 10-parent smoke |

The larger `ubatch` values did not materially improve end-to-end wall
throughput on this small segmentation slice. `ubatch=2048` was the only
single-stream smoke profile that preserved both schema and provenance validity
at `1.000`, so it advanced to Tier 1.

## Concurrency Smoke

Because production segmentation does not have work leasing for concurrent
workers and uses process-global timeout state, concurrency was tested only
against the public benchmark harness with concurrent HTTP requests. It was not
a production pipeline run.

| Profile | Client concurrency | Wall sec | Wall parent/s | Schema valid | Provenance valid | Strict F1 | Pk | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `parallel=2 batch=2048 ubatch=512` | 2 | 69 | 0.145 | 1.000 | 0.900 | 0.350 | 0.352 | slower than single-slot |
| `parallel=2 batch=2048 ubatch=2048` | 2 | 75 | 0.133 | 1.000 | 0.900 | 0.349 | 0.353 | slower than single-slot |
| `parallel=4 batch=2048 ubatch=2048` | 4 | 80 | 0.125 | 1.000 | 1.000 | 0.459 | 0.320 | slower than single-slot |

On this workload and single RTX 3090, extra server slots made wall throughput
worse rather than better. This supports RFC 0010's caution that segmentation
parallelism should be treated as experimental and context-budget constrained.

## Tier 1 Early-Signal Run

The best smoke profile, `parallel=1 batch=2048 ubatch=2048`, ran the existing
Tier 1 sample plan: 80 SuperDialseg validation parents plus 10 synthetic
Engram-proxy fixtures.

| Metric | Value |
| --- | ---: |
| Wall seconds | 546 |
| Wall parent/s | 0.165 |
| Schema valid rate | 0.9889 |
| Provenance valid rate | 0.9667 |
| Schema-invalid requests | 1 |
| Unordered message-id count | 3 |
| Timeout count | 0 |
| Backend error count | 0 |
| Strict boundary F1 | 0.468 |
| Window F1 +/-1 | 0.487 |
| Window F1 +/-2 | 0.506 |
| Pk | 0.300 |
| WindowDiff | 0.306 |
| Predicted/expected segment ratio | 0.874 |
| No-boundary false-split rate | 0.421 |
| Sub-100-token fragment rate | 0.355 |
| Adjacent tiny fragment rate | 0.244 |
| Tier 1 verdict | reject |

The rejection was caused by benchmark hard gates:

- schema-valid rate below `1.0`;
- provenance-valid rate below `1.0`;
- no-boundary false-split rate above the example Tier 1 threshold.

The schema-invalid request was an invalid JSON response with an unterminated
string. There were no timeouts, CUDA failures, HTTP 5xx failures, or other
backend error classes.

Compared with the prior Qwen 35B Tier 1 run, `ubatch=2048` did not produce a
meaningful throughput gain. It improved some boundary metrics on this run, but
the hard reliability gates still rejected it.

## Findings

### F1 - Do not promote `ubatch=2048` into production from this run

The raw prefill microbenchmark improved substantially, but the public
segmentation Tier 1 run still failed hard gates. Throughput was effectively
unchanged at the benchmark level, and one schema-invalid response plus three
unordered provenance events are enough to reject promotion under D042.

### F2 - More server slots did not help this segmentation workload

`parallel=2` and `parallel=4` were slower than single-slot serving on the
10-parent public smoke. Production segmentation also lacks safe concurrent
worker leasing and has process-global timeout behavior, so production
parallelization should not be attempted by launching multiple segmenters.

### F3 - The local llama-bench wrapper is incompatible with this ik_llama binary

The wrapper passes `-c` for context size, but the local `llama-bench` binary
rejects that argument. The benchmark was completed through direct raw
`llama-bench` calls. A follow-up harness repair should either omit context size
for this binary shape or detect supported flags before constructing the command.

### F4 - Deterministic decoding is not enough to make profile outputs identical

The 10-parent smoke outputs varied across server profiles despite
`temperature=0` and strict JSON schema. Treat small quality differences from
the smoke matrix as instability signals, not as model-selection evidence.

## Recommendation

Keep the current production segmentation server profile unchanged. If Phase 2
server tuning continues, the next useful work is a harness fix for
`llama-bench`, followed by repeatable Tier 1/Tier 2 runs for any candidate
profile. Do not pursue `--parallel` concurrency for production segmentation
until parent-level work leasing, timeout handling, and context-budget rules are
made concurrency-safe.

## Evidence Artifacts

Scratch artifacts retained locally:

- `.scratch/benchmarks/segmentation/ik-llama-config-20260507/llama-bench-raw/`
- `.scratch/benchmarks/segmentation/ik-llama-config-20260507/smoke-single/`
- `.scratch/benchmarks/segmentation/ik-llama-config-20260507/smoke-concurrent/`
- `.scratch/benchmarks/segmentation/ik-llama-config-20260507/early-signal/early_signal_par1_b2048_ub2048/20260508T002059Z.superdialseg.c4292092/run.json`
- `.scratch/benchmarks/segmentation/ik-llama-config-20260507/early-signal/early_signal_par1_b2048_ub2048/20260508T002059Z.superdialseg.c4292092/score.json`
- `.scratch/benchmarks/segmentation/ik-llama-config-20260507/early-signal/early_signal_par1_b2048_ub2048/20260508T002059Z.superdialseg.c4292092/report.md`
- `.scratch/benchmarks/segmentation/ik-llama-config-20260507/servers/`
