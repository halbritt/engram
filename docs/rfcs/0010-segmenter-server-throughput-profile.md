# RFC 0010: Segmenter Server Throughput Profile

Status: proposal
Date: 2026-05-04
Context: Phase 2 segmentation; RFC 0006; RFC 0008; D034, D035, D036, D037, D040, D042

This RFC rewrites the proposed async topic-segmentation server configuration
as a benchmark-first throughput experiment. It is not an accepted production
configuration and does not authorize changing the current Phase 2 segmenter
model, request profile, or server service.

## Background

The original proposal argued for maximizing segmentation throughput on an RTX
3090 by moving toward a sparse MoE model, q8 KV cache, continuous batching,
larger physical micro-batches, and prompt-cache reuse. That instinct is
directionally useful: Phase 2 segmentation is local-model expensive, and prompt
processing dominates many successful calls.

However, Engram's segmenter is not a generic "large prompt, tiny output"
workload. The current production contract uses deterministic structured
generation:

- D034 JSON-schema response format;
- thinking disabled;
- `choices[0].message.content` only;
- bounded output tokens;
- per-window `message_ids.items.enum` constraints for provenance safety;
- client-side context guards before grammar-constrained requests reach context
  shift.

Those constraints make throughput tuning subordinate to schema validity,
provenance validity, and backend reliability.

## Problem

The proposed server command optimized raw prompt throughput while bypassing the
accepted Phase 2 quality and safety gates.

In particular:

- `-c 32768 -np 8` gives roughly 4K context per slot, which is smaller than
  Engram's normal structured request budget. Current defaults are
  `max_tokens=16384` and retry `max_tokens=32768`, before prompt and guard
  margin are counted.
- Large per-window enum schemas improve provenance safety but can reduce
  prefix-cache reuse because the schema changes between windows.
- Qwen 35B MoE is operationally fast, but the latest Tier 1 benchmark rejected
  its current output shape for provenance failures. D042 requires a Tier 2
  decision run before production model/profile changes.
- Throughput alone is not a valid objective for Engram. A faster profile that
  increases unordered spans, context-shift errors, truncation runaways, or
  fragmentation is worse than the slower baseline.

## Goals

- Evaluate model-server flags with local, reproducible evidence.
- Preserve D034/D036/D037 structured-output and provenance guarantees.
- Keep all testing local-only and outside the production corpus unless the
  normal Phase 2 operator explicitly runs the production pipeline.
- Measure throughput, VRAM behavior, context-shift failures, timeout/runaway
  classes, schema validity, provenance validity, and fragmentation together.
- Change one server variable at a time where possible.
- Produce a clear recommendation: reject, keep benchmarking, or promote into a
  later Phase 2 operations update.

## Non-goals

- Do not change `src/engram/segmenter.py`'s request profile.
- Do not change `SEGMENTER_PROMPT_VERSION` or derivation versioning.
- Do not switch production away from the current segmenter model/profile.
- Do not weaken JSON-schema, enum-constrained message ids, or context guards to
  gain speed.
- Do not add hosted services, external telemetry, cloud APIs, or remote model
  calls.
- Do not write benchmark outputs into retrieval-visible production rows.

## Current Baseline

The current comparable server baseline from recent benchmark runs is:

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

This profile has already been used with D034-style local-model benchmark
requests. It should remain the control unless a newer accepted operations
document supersedes it.

## Candidate Ideas To Test

### q8 KV Cache

q8 KV cache is already part of the current baseline. Keep it in the control and
record it explicitly in all benchmark artifacts.

### Prompt Cache

Prompt-cache reuse is worth testing, but it must be measured under the real
enum-constrained schema. Static system instructions may cache well; per-window
message-id enums may break reuse. A prompt-cache flag is useful only if it
improves parent/s without changing correctness metrics or increasing backend
instability.

### Micro-batch Ladder

Test `--ubatch-size` as a ladder under `--parallel 1` before combining it with
parallel slots:

```text
256 -> 512 -> 1024 -> 2048
```

Stop the ladder if VRAM approaches the configured stop threshold, completion
smoke fails, or context-shift / timeout failures increase.

### Parallel Slots

The original `--parallel 8 --ctx-size 32768` profile should be treated as a
candidate to disprove, not as a reference implementation. With Engram's current
request budgets, that shape is expected to be unsafe for ordinary production
segmentation.

Parallelism may be tested only after single-slot profiles are stable, and only
with enough per-slot context to satisfy:

```text
estimated_prompt_tokens + max_tokens + guard_margin < per_slot_context
```

If the candidate profile cannot satisfy that inequality for normal D034
requests, it is not a production Phase 2 profile.

### Model Choice

Model choice belongs to RFC 0006 / RFC 0008 / D042, not this RFC. Server flags
may be benchmarked against multiple local models, but no throughput result
overrides the model-selection ladder. A model/profile still needs schema
validity, provenance validity, fragmentation controls, and a Tier 2 decision
run before production promotion.

## Benchmark Shape

Each candidate server profile should run the same sequence:

1. Start the local `llama-server` on `127.0.0.1:8081`.
2. Record exact binary path, model path, model file size, `/v1/models`,
   `/props`, server args, and relevant environment variables.
3. Run a tiny D034 JSON-schema completion smoke.
4. Run a bounded public benchmark slice through the RFC 0008 harness.
5. If the profile passes the public slice, run a small local Phase 2 preflight
   with production code and `--limit 10`.
6. Run the same tiny D034 completion smoke after the benchmark/preflight.
7. Stop the server cleanly and archive logs.

The benchmark may add a longer operational soak only after the profile passes
the shorter gates.

## Metrics

Every run should report:

- parents/s and median/p90/p99 parent latency;
- prompt processing time when exposed by server logs;
- decoded token counts and max-token saturation rate;
- schema-valid rate;
- provenance-valid rate;
- `unknown_message_id`, unordered span, and empty-content failures;
- `runaway_unterminated` and `http_500_ctx_shift` classes;
- request timeout and service-unavailable counts;
- pre-run and post-run D034 smoke result;
- VRAM start/end/max and drift;
- server crash, CUDA, cuBLAS, or illegal-memory log signatures;
- segment count, predicted/expected segment ratio, sub-100-token fragments,
  adjacent tiny fragments, and no-boundary false splits where the harness can
  score them.

## Promotion Criteria

A server profile may be proposed for production only if all of the following
hold:

- pre-run and post-run D034 smokes pass;
- schema validity is 1.000 on the benchmark slice;
- provenance validity is 1.000 on the benchmark slice;
- no new unclassified failure class appears;
- context-shift, timeout, and service-unavailable rates do not worsen compared
  with baseline;
- VRAM remains below the stop threshold with acceptable drift;
- fragmentation metrics do not regress beyond the RFC 0008 thresholds;
- throughput improves enough to matter for the active Phase 2 run;
- the result is recorded in `docs/reviews/` or a follow-up synthesis document;
- any accepted production change updates the relevant operations document and,
  if it changes architecture or model/profile selection, `DECISION_LOG.md`.

## Rejected Shape From The Original Draft

Do not promote this command directly:

```text
llama-server
  -m Qwen3.6-35B-A3B-UD-IQ4_XS.gguf
  -c 32768
  -np 8
  -ub 2048
  -ctk q8_0
  -ctv q8_0
  --prompt-cache-all
  -fa 1
  -ngl 99
```

It may be included as an experimental profile only if the benchmark records
that its effective per-slot context is incompatible with normal Engram
structured requests, or if the request budgets are explicitly narrowed for a
separate non-production experiment.

## Open Questions

- Does `--prompt-cache-all` improve real D034 enum-constrained requests enough
  to matter, or does per-window schema variance erase the benefit?
- What `--ubatch-size` maximizes prompt processing without increasing tail
  failures on the 3090?
- Is there any safe parallel-slot profile for Engram's current 16K/32K output
  budget, or is single-slot serving the correct Phase 2 shape?
- Should retry max tokens be lowered before future server-profile benchmarks so
  retry attempts cannot exceed a 49K context window on enum-heavy prompts?
- Which measurements belong in `docs/segmentation.md` once a profile is
  accepted?
