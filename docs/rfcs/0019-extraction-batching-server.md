<a id="rfc-0019"></a>
# RFC 0019: Continuous-Batching Inference Server for Phase 3 Claim Extraction

| Field | Value |
|-------|-------|
| RFC | 0019 |
| Title | Continuous-Batching Inference Server for Phase 3 Claim Extraction |
| Status | proposal |
| Implementation | none |
| Date | 2026-05-07 |
| Context | Phase 3 claim extraction; RFC 0010; RFC 0011 § Stage A; RFC 0017; D020 (local-only inference); D034 (JSON-schema response format); `src/engram/extractor.py:33` (`EXTRACTION_PROMPT_VERSION`); `src/engram/segmenter.py:23` (`IK_LLAMA_BASE_URL`); `src/engram/segmenter.py:1918` (`ensure_local_base_url`) |

This is an idea-capture RFC, not an accepted architecture decision. It proposes
benchmarking a continuous-batching local inference server (vLLM or sglang) as
the back end for Phase 3 claim extraction, with the goal of converting a
multi-hour single-stream batch run into a same-day iteration loop. It does
**not** authorize switching production away from the current `ik-llama-server`
endpoint, and it does not weaken any Phase 2 / Phase 3 quality, provenance, or
local-only contract.

## Background

Phase 3 claim extraction (`src/engram/extractor.py`) and Phase 2 segmentation
(`src/engram/segmenter.py`) currently share a single local OpenAI-compatible
endpoint, `ik-llama-server` on `127.0.0.1:8081`, pinned via
`ENGRAM_IK_LLAMA_BASE_URL` and stamped onto each row as
`extraction_model_version` and `request_profile_version =
ik-llama-json-schema.d034.v2` (see `docs/claims_beliefs.md` § Provenance).

Operational observation: a full claim-extraction pass over the AI-conversation
corpus is single-stream throughput-bound. Empirically that is in the
~167 tok/s decode regime on Qwen3.5-35B-A3B (3B active params via MoE) on a
single RTX 3090. For a fixed corpus in the tens of thousands of segments,
this lands in the ~21-hour wall-clock range for one extractor version, which
puts re-extraction (RFC 0017 Part 2) on a once-a-month cadence rather than a
weekly one.

The technical claim being captured here is that this is an inference-serving
shape problem, not a hardware problem:

- Per request, `llama.cpp` does prefill (compute-bound, GPU briefly saturated)
  followed by decode (memory-bandwidth-bound).
- With ~3B active params, Qwen3.5-A3B's decode does not saturate a 3090's
  bandwidth; observed GPU utilization during decode is well below 100%.
- Continuous batching (vLLM, sglang) overlaps prefill of one request with
  decode of another, and packs many decode streams into one forward pass.
  PagedAttention sizes KV cache per active sequence rather than per slot, so
  long-input / short-output workloads (which is what extraction is) are
  exactly the shape continuous batching wins on.
- Realistic aggregate-throughput multiplier is in the 10–20× range on the
  same hardware. MoE routing fragments per-expert compute across the batch,
  so the high end of dense-model batching gains is not expected; the low end
  is still a meaningful win.

Concretely, this RFC tracks the proposal: serve the same extractor against
**vLLM** (or **sglang** as an alternative) running locally, fire concurrent
requests against its OpenAI-compatible endpoint, and use prefix caching for
the long extraction system prompt.

## Problem

The current single-stream serving shape:

- Couples extractor iteration speed to overnight runs. RFC 0017's
  re-extraction protocol becomes economically painful, so it is not exercised
  often, so prompt-version drift is hidden.
- Leaves 3090 capacity on the floor during decode, which is the dominant
  phase for extraction's input/output ratio.
- Fixes the inference back-end to `ik-llama` for both Phase 2 and Phase 3
  even though the two workloads have different shapes (Phase 2: structured
  output with per-window enums; Phase 3: many independent segment-level
  extractions over a long, mostly-static system prompt).

The risk in fixing this is: any change to the inference back-end is a change
to `extraction_model_version` and possibly `request_profile_version`, which
is a re-extraction trigger by design (RFC 0017 Part 1). A switch must produce
a measurable end-to-end win, not just a tok/s number, and it must preserve
schema-validity and provenance-validity contracts.

## Goals

- Treat the throughput claim as a hypothesis to be tested locally with the
  real Phase 3 extractor and a representative segment slice.
- Preserve D034 JSON-schema output, the structured-extraction contract in
  `src/engram/extractor.py`, and the `extraction_prompt_version` /
  `extraction_model_version` provenance stamps.
- Keep the inference endpoint on `127.0.0.1` (D020). vLLM and sglang both
  bind to a host/port and must be served bound to localhost; the existing
  `ensure_local_base_url` guard at `src/engram/segmenter.py:1918` continues
  to apply.
- Measure batch-level throughput, per-request latency, schema-valid rate,
  provenance-valid rate, VRAM behaviour, and end-to-end wall-clock for a
  fixed segment slice.
- Decide between three outcomes: reject, keep benchmarking, or promote
  through `DECISION_LOG.md` with a `request_profile_version` bump.

## Non-goals

- Do not switch production extraction away from `ik-llama-server` until
  benchmark evidence justifies it.
- Do not change `EXTRACTION_PROMPT_VERSION` to chase a back-end change. A
  back-end switch is itself a `request_profile_version` event; the prompt
  string stays stable across the comparison.
- Do not introduce hosted inference, cloud APIs, remote model calls, or any
  egress. vLLM / sglang must be self-hosted, on-machine, bound to localhost.
- Do not skip the Phase 2 segmenter throughput discussion in RFC 0010.
  Phase 2's structured shape (per-window enums, schema variance) does not
  obviously benefit from continuous batching; this RFC is scoped to Phase 3.
- Do not use the Tier 0/1 segmentation benchmark harness as the gate for
  this experiment. Extraction needs its own measurement plan.
- Do not assume AWQ/GPTQ INT4 weights are quality-equivalent to IQ4_XS for
  extraction without measuring it.

## Proposal

### Part 1: Inference back-end candidate

Treat **vLLM** as the primary candidate and **sglang** as the alternative
to revisit if vLLM falls short on this workload:

- vLLM: production-grade continuous batching, mature OpenAI-compatible API,
  PagedAttention, prefix caching. Does not consume `ik-llama`/`llama.cpp`
  GGUF (`IQ4_XS`) quants directly; requires AWQ-INT4 or GPTQ-INT4 weights
  for the same Qwen3.5-35B-A3B base model.
- sglang: comparable on many MoE workloads, sometimes faster, with strong
  prefix caching and native grammar-constrained decoding. Slightly less
  mature operationally; revisit if vLLM's grammar story is the bottleneck.

The rest of this RFC describes vLLM as the named candidate. Substituting
sglang is a benchmark variation, not a new RFC.

### Part 2: Local-only serving constraint

The vLLM / sglang server must be launched bound to `127.0.0.1` (or a Unix
socket if the framework supports one). The base URL the extractor talks to
is still validated by `ensure_local_base_url`; that guard already accepts
`127.0.0.1`, `localhost`, and `::1`. No new permissive entry is added.

A new env var, e.g. `ENGRAM_INFERENCE_BASE_URL`, can be introduced as a
back-end-agnostic alias if and only if the experiment is promoted; until
then the variable lives in benchmark scaffolding only and is not committed
to `src/engram`.

### Part 3: Quantization

The candidate weights are an **AWQ-INT4** quant of Qwen3.5-35B-A3B (or the
exact base model in production use; the version pinned at promotion time
is what matters, not the example here). Quality drift versus the in-use
`UD-IQ4_XS` GGUF must be measured against the actual extraction outputs,
not just perplexity:

- Field-presence rate per claim row (predicate, stability_class,
  confidence, evidence span ids).
- Predicate vocabulary distribution drift versus the IQ4_XS baseline.
- Stability-class assignment drift.
- Provenance-validity rate (no `unknown_message_id`, no spans outside the
  source segment).
- Schema-validity rate (`json.loads` round-trip, required fields, type
  coverage).

If AWQ-INT4 measurably degrades any of those rates beyond a tolerance set
in the benchmark plan, the answer is "stay on `ik-llama` and revisit when
better quants are available," not "ship anyway because it's faster."

### Part 4: Concurrency on the client side

The extractor currently issues sequential requests. To exercise continuous
batching the client must fire multiple requests in flight at once. Two
acceptable shapes:

1. `asyncio` + an async HTTP client, with a bounded semaphore of N
   concurrent requests.
2. `concurrent.futures.ThreadPoolExecutor` with N workers wrapping the
   existing synchronous request path.

The bound `N` is tuned against the server's `--max-num-seqs` and against
VRAM headroom, not picked once and forgotten. The benchmark records the
chosen `N`.

This change is a wrapper around the existing extractor entry point; it
does not require changing the per-request structured-output contract.

### Part 5: Prefix caching for the system prompt

The extraction system prompt is long and stable across a single
`EXTRACTION_PROMPT_VERSION`. vLLM's `--enable-prefix-caching` (and sglang's
prefix cache) can amortize prefill across all segments in the run.

The benchmark records:

- Prefill time with prefix caching enabled vs. disabled.
- KV-cache hit rate as exposed by the server's metrics endpoint.
- Whether the segment-level user prompt invalidates the prefix prematurely
  (e.g., if any per-segment templating is currently inserted before the
  invariant block).

If the prefix cache is invalidated by current prompt construction, this
RFC may add a follow-up note recommending that `extractor.py` reorder its
prompt assembly so the static block precedes the per-segment block. That
reorder is a `EXTRACTION_PROMPT_VERSION` bump and would happen under
RFC 0017's contract, not silently.

### Part 6: Grammar-constrained decoding (optional)

If the benchmark surfaces malformed-JSON retries as a non-trivial cost,
grammar-constrained decoding (sglang native grammar, or
`outlines` / `lm-format-enforcer` on vLLM) can be added. This is an
optimization slot, not a requirement. Adding a constrained decoder is a
`request_profile_version` change.

### Part 7: Multi-GPU / multi-host shape (deferred)

Once a second 3090 is available the proposal is one of:

- One vLLM instance with tensor parallelism across both cards. Larger
  batch sizes; same client.
- Two independent vLLM instances, one per card, with the segment list
  sharded between them. Embarrassingly parallel; no NCCL; no networking
  between them beyond the shared filesystem the extractor already uses.

The choice depends on the benchmark in Part 8. Do not commit to either
shape in this RFC. Both stay local.

### Part 8: Benchmark plan

The benchmark must run against a **fixed segment slice** drawn from the
existing AI-conversation corpus, not the full corpus. A 1000-segment slice
covering the existing register distribution is a starting size; the exact
slice and seed are recorded in the benchmark artifact.

For each candidate configuration (control = current `ik-llama-server`;
candidates = vLLM AWQ-INT4 with various `--max-num-seqs` and prefix cache
settings):

1. Spin up the candidate server bound to `127.0.0.1` on a non-collision
   port. Record exact binary, model path, model file size, server flags,
   and `/v1/models` / metrics endpoints.
2. Run a tiny D034-shaped extraction smoke against one segment to confirm
   the OpenAI-compatible surface area matches the extractor's
   expectations.
3. Run the 1000-segment slice with the experimental client wrapper at the
   chosen concurrency bound `N`.
4. Stop the server cleanly. Archive logs.
5. Diff the produced claim rows against the `ik-llama` control on the
   same slice: field-presence, predicate distribution, stability-class
   distribution, provenance validity, schema validity.
6. Record wall-clock time, peak VRAM, GPU utilization profile,
   prefix-cache hit rate, malformed-JSON retry rate, and any server-side
   error class counts.

The slice runs are written to a benchmark artifact directory **outside**
production claim rows. Nothing the benchmark produces lands in
retrieval-visible Postgres tables until the configuration is promoted.

### Part 9: Promotion criteria

A back-end switch may be proposed for production only if all of the
following hold against the same fixed segment slice:

- Pre-run and post-run D034 smokes pass.
- Schema-valid rate is at least the `ik-llama` baseline.
- Provenance-valid rate is at least the `ik-llama` baseline.
- Predicate vocabulary and stability-class distribution drift fall within
  a tolerance recorded in the benchmark plan, or the drift is judged
  acceptable in a recorded review.
- Wall-clock time on the 1000-segment slice improves by enough to matter
  for re-extraction iteration speed (target: ≥5×; floor: ≥2×, below
  which the operational complexity is not earned).
- Peak VRAM stays below the 3090's stop threshold.
- No new failure class (CUDA OOM, scheduler hang, KV-cache eviction
  thrash) appears.
- A review document under `docs/reviews/` records the comparison.
- A `DECISION_LOG.md` entry is added covering the inference-server
  change, the new `request_profile_version`, and the new
  `extraction_model_version` value the production extractor will stamp.
- RFC 0017's re-extraction protocol is invoked (or scheduled) to
  re-extract the corpus under the new `request_profile_version` /
  `extraction_model_version`. Pre-existing claim rows under the old
  version stay in place per the raw-is-sacred / append-only contract.

## Risks and adversarial concerns

- **MoE batching is not dense-model batching.** Expert routing is
  per-token-per-request; large batches fragment compute across experts
  unevenly. The 10–20× number is best-case; the workload may underperform
  it. The benchmark in Part 8 must produce the actual number on this
  workload before any throughput claim is repeated.
- **AWQ-INT4 ≠ IQ4_XS.** They are different quantization families with
  different rounding characteristics. "Noise-level for structured
  extraction" is a hypothesis until measured against the extractor's
  own outputs, not an assumption.
- **Prefix-cache fragility.** If the extractor's prompt construction
  varies subtly per segment in a way that defeats prefix caching, the
  claimed prefill savings disappear. The benchmark must measure hit
  rate; do not assume it.
- **Grammar-constrained decoding can change outputs.** A constrained
  decoder is not a no-op; it can hide malformed-JSON cases that
  previously surfaced as retries, masking upstream prompt regressions.
  Treat it as a separate experiment.
- **Operational surface area.** vLLM is heavier than `llama.cpp` /
  `ik-llama-server`. It introduces a Python runtime in the serving
  path, a different model-loading workflow, a different metrics
  surface, and a different update cadence. The benchmark should
  include a "what does this look like as a `systemd` unit" answer
  before promotion.
- **Two back-ends in parallel.** During the experiment, both
  `ik-llama-server` and a candidate server may be running. Port
  collisions and accidental cross-talk to the wrong endpoint must be
  guarded by `ENGRAM_IK_LLAMA_BASE_URL` discipline and by the local-only
  URL guard.

## Open questions

1. Is there a smaller, cheaper version of this experiment that bypasses
   weight conversion? For example, running vLLM with the existing model
   in FP16 on a 1000-segment slice (ignoring quantization) to isolate
   the batching gain from the quant question.
2. Does the extractor's current prompt assembly preserve the static
   prefix needed for prefix-cache reuse, or does it need a re-ordering
   pass first? If the latter, that re-ordering is itself an
   `EXTRACTION_PROMPT_VERSION` bump (RFC 0017 Part 1).
3. Does `DECISION_LOG.md` need a new decision row for the abstraction
   "inference back-end is a `request_profile_version` axis", or is the
   existing per-row stamp sufficient?
4. What happens to the Phase 2 segmenter when the Phase 3 extractor
   migrates? Phase 2 stays on `ik-llama-server` (its enum-heavy schema
   makes batching less obviously profitable). The two back-ends co-exist
   on different ports, both local. This RFC scopes only Phase 3; revisit
   Phase 2 separately if at all.
5. Should the future shared base-URL env var be `ENGRAM_INFERENCE_BASE_URL`,
   or should the existing `ENGRAM_IK_LLAMA_BASE_URL` be repurposed and
   eventually renamed when ik-llama is no longer the default? Naming
   decision deferred until the experiment outcome is known.

## Acceptance criteria for promotion

Promotion paths are split:

- **Idea capture (this RFC):** lands as `proposal` in
  `docs/rfcs/README.md`. No code change is required to accept it.
- **Benchmark execution:** producing the comparison artifact under
  `docs/reviews/phase3/PHASE_3_EXTRACTION_BACKEND_BENCHMARK_<date>.md`
  is the next concrete step. It does not require a `BUILD_PHASES.md`
  promotion; it is operator work.
- **Production back-end switch:** requires a `DECISION_LOG.md` entry,
  a new `extraction_model_version`, a new `request_profile_version`,
  and an RFC 0017 re-extraction plan. None of those are authorized by
  this RFC.
