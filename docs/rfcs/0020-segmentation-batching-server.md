<a id="rfc-0020"></a>
# RFC 0020: Continuous-Batching Inference Server for Phase 2 Segmentation

| Field | Value |
|-------|-------|
| RFC | 0020 |
| Title | Continuous-Batching Inference Server for Phase 2 Segmentation |
| Status | proposal |
| Implementation | none |
| Date | 2026-05-07 |
| Context | Phase 2 segmentation; RFC 0006; RFC 0008; RFC 0010; RFC 0019; D020 (local-only inference); D034 (JSON-schema response format); D036; D037; D042 (model-selection ladder); `src/engram/segmenter.py:23` (`IK_LLAMA_BASE_URL`); `src/engram/segmenter.py:28` (`SEGMENTER_REQUEST_PROFILE_VERSION`); `src/engram/segmenter.py:35` (`DEFAULT_WINDOW_CHAR_BUDGET`); `src/engram/segmenter.py:1542` (`build_windows`); `src/engram/segmenter.py:320` (`assert_context_budget`); `src/engram/segmenter.py:1918` (`ensure_local_base_url`) |

This is an idea-capture RFC, not an accepted architecture decision. It is the
Phase 2 segmentation companion to RFC 0019. It proposes benchmarking a
continuous-batching local inference back-end (vLLM or sglang) plus aggressive
prefix caching and a window-budget revisit as a path to compressing the
multi-day full-corpus segmentation pass into a same-day iteration loop. It
does **not** authorize switching the segmenter off `ik-llama-server`, does not
override RFC 0010's benchmark-first contract, and does not change Phase 2's
schema or provenance gates.

## Background

Phase 2 segmentation (`src/engram/segmenter.py`) already has more structure
than the RFC 0019 extraction story:

- It chunks each parent conversation into windows by character budget
  (`DEFAULT_WINDOW_CHAR_BUDGET = 60_000`, configurable via
  `ENGRAM_SEGMENTER_WINDOW_CHAR_BUDGET`), with an adaptive
  `context_safe_window_char_budget` shrink based on the probed context window
  (`src/engram/segmenter.py:348`).
- Each window is a single D034 JSON-schema completion request with per-window
  `message_ids.items.enum` constraints for provenance safety
  (`docs/segmentation.md` §§ Provenance, Context guards).
- Default `max_tokens=16384`, retry `max_tokens=32768`, with
  `assert_context_budget` enforcing
  `prompt_tokens + max_tokens + guard_margin <= context_window`
  (`src/engram/segmenter.py:320`).
- The current accepted server baseline (RFC 0010) is:
  `--ctx-size 49152 --parallel 1 --batch-size 2048 --ubatch-size 256
  --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --jinja`
  via `ik-llama-server`.
- `SEGMENTER_REQUEST_PROFILE_VERSION = "ik-llama-json-schema.d034.v2"` is the
  back-end-shape stamp recorded on every produced segment.

The technical claim being captured in this RFC is that segmentation has a
**different compute profile from claim extraction** and the throughput levers
shift accordingly:

| Phase | Input | Output | Bottleneck | Continuous-batching win | KV-cache pressure |
|---|---|---|---|---|---|
| Segmentation (Phase 2) | Long (window-sized, current default ≈15K tokens prompt) | Short structured (segment list) | Prefill (compute-bound) | Smaller (3–6× plausible) | High; KV size dominates batch limit |
| Extraction (Phase 3) | Short (one segment) | Long structured (claim rows) | Decode (bandwidth-bound) | Larger (10–20× plausible) | Lower; weights dominate |

Concretely, three levers with different cost-of-truth:

1. **Profile first.** A multi-day segmentation pass may not be 80% LLM time.
   It may be 50/50 LLM and surrounding code (JSON parsing, repair, embedding
   side calls, provenance validation, Postgres writes, supervisor I/O). No
   server change helps with the non-LLM share.
2. **Window-budget revisit and prefix caching.** Prefill is superlinear in
   context length on most attention impls. Cutting per-request prompt tokens
   and reusing prefix-cached tokens is the cheapest measurable win and does
   not change the inference back-end.
3. **Continuous batching.** vLLM / sglang with PagedAttention can interleave
   prefill of one request with decode of another, but on a 3090 with
   Qwen3.5-35B-A3B loaded the achievable concurrent request count for
   ≈15K-token windows is small (KV cache dominates remaining VRAM). The
   batch multiplier for segmentation is real but smaller than the extraction
   case.

## Problem

The segmenter is currently single-stream against `ik-llama-server`. Three
problems compound:

- **Iteration speed.** A full re-segmentation of the AI-conversation corpus
  is too slow to run on a prompt-tuning loop.
- **Optimization order is unclear.** The recommendation under review proposes
  "switch to vLLM" as the headline change, but the largest plausible win for
  this workload may be elsewhere (chunking, prefix caching, or pipeline
  parallelism) and the RFC needs to enforce that ordering.
- **Profile-version coupling.** Switching back-ends is a
  `SEGMENTER_REQUEST_PROFILE_VERSION` change. Like RFC 0019, that means a
  back-end switch is not free; it is a re-segmentation event whose output
  must be validated against the existing schema/provenance/fragmentation
  gates from RFC 0008 and RFC 0010, not just a tok/s improvement.

The risk in moving fast on this:

- A faster back-end with a higher `unknown_message_id` rate or higher
  unordered-span rate is worse than the slower baseline. RFC 0010 already
  makes this point; it carries forward unchanged.
- AWQ-INT4 weights of the candidate model are not output-equivalent to the
  in-use IQ4_XS GGUF without measurement. Phase 2 is more sensitive to
  output drift than Phase 3 because segmentation outputs gate every
  downstream stage.
- The model-selection ladder (RFC 0006 / RFC 0008 / D042) governs model
  choice. A back-end switch is not a vehicle for a quiet model swap. If the
  vLLM candidate runs the same base model, the comparison is back-end only;
  if the candidate also changes model identity or quantization family
  enough to count as a model change, it is gated by D042 and re-enters the
  Tier 0/1/2 ladder.

## Goals

- Order the levers by cost-of-truth: profile, window-budget, prefix caching,
  continuous batching, chunking-strategy revisits.
- Treat the throughput claim as a hypothesis to be tested locally with the
  real Phase 2 segmenter and a representative public-slice plus operator
  preflight, per RFC 0010.
- Preserve D034 / D036 / D037 schema, provenance, and fragmentation
  contracts. RFC 0010's promotion criteria carry forward.
- Keep the inference endpoint on `127.0.0.1` (D020). vLLM / sglang must be
  bound to localhost; `ensure_local_base_url`
  (`src/engram/segmenter.py:1918`) continues to apply.
- Decide between three outcomes: reject, keep benchmarking, or promote
  through `DECISION_LOG.md` with a `SEGMENTER_REQUEST_PROFILE_VERSION` bump.

## Non-goals

- Do not change `SEGMENTER_PROMPT_VERSION` or derivation versioning to chase
  a back-end change. A back-end switch is a `request_profile_version` event,
  not a prompt event.
- Do not switch production segmentation away from `ik-llama-server` until
  benchmark evidence justifies it.
- Do not weaken the per-window `message_ids.items.enum`,
  `assert_context_budget` guard, or D034 JSON-schema contract to gain speed.
- Do not change the Phase 2 model under cover of a back-end RFC. Model
  changes go through D042 (Tier 2 decision run).
- Do not introduce hosted services, external telemetry, cloud APIs, or
  remote model calls. vLLM / sglang must be self-hosted, on-machine, bound
  to localhost.
- Do not write benchmark outputs into retrieval-visible production rows.

## Proposal

### Part 1: Profile the existing pipeline before changing back-ends

This is the cheapest step and orders everything that follows. Pick a
representative slice (say, 50 parents) and instrument the segmentation pass
end-to-end to attribute wall-clock to:

- HTTP request to `ik-llama-server` (prefill + decode).
- JSON parsing and schema validation.
- Provenance validation (per-window enum check, span ordering).
- Repair / retry paths.
- Embedding side calls or any other LLM round-trip.
- Postgres reads and writes (`upsert_progress`, segment inserts, evidence
  links).
- Supervisor / orchestration overhead (queue claim, lease, release).

The output is a written share-of-time table archived under
`docs/reviews/phase2/PHASE_2_SEGMENTATION_PROFILE_<date>.md`.

Decision branch on the share:

- **≥80% LLM time.** Continue with Parts 2–4. Inference-side levers are the
  right place to spend.
- **50–80% LLM time.** Continue with Parts 2–4 but expect smaller wall-clock
  gains, and open a parallel question about the Python / Postgres half. A
  separate RFC may be warranted for pipeline-level concurrency.
- **<50% LLM time.** Stop. The segmenter is not LLM-bound, the inference
  back-end is the wrong lever, and any vLLM benchmark is pre-mature
  optimization. Open a separate RFC for the dominant cost.

### Part 2: Window-budget revisit (no back-end change)

The current default `ENGRAM_SEGMENTER_WINDOW_CHAR_BUDGET=60000` (~15K
tokens) was chosen for parent coverage, not for prefill cost. Two
sub-experiments are cheap because they require no inference change:

- **Smaller windows.** Try 8K-token and 12K-token effective windows on a
  small public-slice and on a tiny operator preflight. Measure parents/s,
  schema validity, provenance validity, fragmentation metrics from RFC 0008,
  and the rate of windows that previously triggered the retry path.
  Hypothesis: smaller windows reduce per-request prefill superlinearly,
  improve prefix-cache hit rate, and lower KV-cache pressure once batching
  is on, while costing some boundary-recall at window edges.
- **Window overlap.** `WINDOW_OVERLAP_MESSAGES` already exists
  (default `0`); a small overlap (1–2 messages) may compensate for any
  boundary-recall loss from smaller windows.

If smaller windows degrade fragmentation or boundary metrics beyond the
RFC 0008 thresholds, the answer is "keep the 60K budget." This is a
measurement, not an assumption.

### Part 3: Prefix caching (back-end change)

The segmenter prompt has a long, stable static block (system instructions
+ schema definition + examples) followed by a per-window dynamic block
(message-id enum + windowed messages). For prefix caching to bite, the
static block must precede the dynamic block in the assembled prompt and
must be byte-identical across windows in a single corpus pass.

Two server frameworks support this:

- **vLLM** with `--enable-prefix-caching`. The OpenAI-compatible chat
  endpoint matches the segmenter's existing client.
- **sglang** with native prefix caching, sometimes more aggressive than
  vLLM and with native grammar-constrained decoding for free.

The benchmark in Part 5 measures cache hit rate against the real
per-window prompts. If the per-window enum is currently inserted before
the static block, this RFC may add a follow-up note recommending a prompt
re-assembly. **That re-assembly is a `SEGMENTER_PROMPT_VERSION` bump and
goes through its own review.** It is not silent.

### Part 4: Continuous batching with KV-cache budgeting

This is the headline change in the recommendation under review and it is
deliberately Part 4, not Part 1.

- **Server.** vLLM (primary) or sglang (alternative), bound to
  `127.0.0.1`, on a non-collision port from `ik-llama-server`.
- **Quantization.** AWQ-INT4 of the segmenter's pinned base model
  (currently the Qwen3.5-35B-A3B family per `docs/segmentation.md`).
  AWQ-INT4 is *not* output-equivalent to UD-IQ4_XS without measurement.
  Promotion requires schema-validity, provenance-validity, and
  fragmentation parity on the RFC 0008 public slice (see Part 5).
- **Batch sizing.** Long-context prefill makes KV cache the dominant
  VRAM consumer per concurrent request. For an effective ≈15K-token
  window on a 3090 with the model loaded, expect a small concurrency
  ceiling (`--max-num-seqs` in the 2–6 range, not 16–32). The benchmark
  reports the actual ceiling.
- **Client.** Wrap the existing segmenter request path in a bounded
  concurrency primitive (`asyncio.Semaphore` or `ThreadPoolExecutor`)
  with `N` aligned to `--max-num-seqs` and to VRAM headroom. The
  per-request structured-output contract does not change.
- **Speculative decoding: skip.** Segmentation outputs are short, so
  spec-decode's payoff is small; meanwhile it adds a second model and
  more failure surface. Out of scope for this RFC.
- **Grammar-constrained decoding: optional.** sglang's native grammar
  support may eliminate retries from malformed outputs. Same caveat as
  RFC 0019 Part 6: a constrained decoder can mask upstream prompt
  regressions and is itself a `request_profile_version` event.

The MoE batching penalty is worse on prefill-heavy workloads than on
decode-heavy ones, because long-context prefill processes many tokens at
once and they hit many different experts unevenly. Realistic continuous-
batching gain on this workload is **3–6× over single-stream**, not the
10–20× plausible for extraction. The benchmark must produce the actual
number; the high end of the range is not a planning assumption.

### Part 5: Benchmark plan (extends RFC 0010)

The benchmark reuses the RFC 0010 shape but adds candidate configurations
that include vLLM / sglang back-ends and Part 2's window-budget
variations.

For each candidate configuration (control = current `ik-llama-server`
RFC 0010 baseline; candidates = vLLM AWQ-INT4 with assorted
`--max-num-seqs`, prefix-cache, and window-budget settings):

1. Spin up the candidate server bound to `127.0.0.1` on a non-collision
   port. Record exact binary, model path, model file size, server flags,
   and `/v1/models` / metrics endpoints.
2. Run a tiny D034 JSON-schema completion smoke (RFC 0010 step 3).
3. Run a bounded RFC 0008 public benchmark slice through the harness.
4. If the public slice passes, run a small operator preflight with
   production code and `--limit 10` (RFC 0010 step 5). Operator
   preflight does **not** write into retrieval-visible production
   tables.
5. Run the post-run D034 smoke (RFC 0010 step 6).
6. Stop the server cleanly and archive logs.
7. Diff the produced segments against the `ik-llama` control on the
   same slice: schema validity, provenance validity, fragmentation,
   `unknown_message_id` rate, unordered-span rate,
   `runaway_unterminated`, `http_500_ctx_shift`, sub-100-token
   fragments, adjacent tiny fragments, no-boundary false-split rate.

The slice runs are written to a benchmark artifact directory **outside**
production segments. Nothing the benchmark produces lands in
retrieval-visible Postgres tables until the configuration is promoted.

### Part 6: Multi-GPU / multi-host shape (deferred)

Once a second 3090 is available the proposal is one of:

- One vLLM instance with tensor parallelism across both cards. Larger
  per-instance batch sizes; same client. Helpful for KV-cache headroom
  on long windows.
- Two independent vLLM instances, one per card, with the parent list
  sharded between them. Embarrassingly parallel; no NCCL; no
  networking between them beyond the shared filesystem the segmenter
  already uses.

The choice depends on the benchmark in Part 5. Do not commit to either
shape in this RFC. Both stay local.

### Part 7: Promotion criteria (extends RFC 0010)

A back-end switch may be proposed for production only if **all** of the
following hold against the same RFC 0008 public slice and operator
preflight:

- Pre-run and post-run D034 smokes pass.
- Schema-valid rate is at least the `ik-llama` baseline.
- Provenance-valid rate is at least the `ik-llama` baseline.
- Context-shift, timeout, and service-unavailable rates do not worsen.
- VRAM remains below the stop threshold with acceptable drift.
- Fragmentation metrics do not regress beyond the RFC 0008 thresholds.
- No new unclassified failure class appears.
- Wall-clock time on the slice improves by enough to matter for full-
  corpus iteration speed (target: ≥5×; floor: ≥2×, below which the
  operational complexity is not earned).
- A review document under `docs/reviews/phase2/` records the
  comparison.
- A `DECISION_LOG.md` entry is added covering the inference-server
  change, the new `SEGMENTER_REQUEST_PROFILE_VERSION`, and any change
  to model identity or quantization family.
- A re-segmentation plan is recorded. Like RFC 0019's re-extraction
  plan, this is the operator step that re-runs Phase 2 under the new
  `request_profile_version`. Pre-existing segments under the old
  profile stay in place per the raw-is-sacred / append-only contract;
  re-segmentation produces new derivation rows, not in-place rewrites.

## Risks and adversarial concerns

- **Profile-step skipped.** The biggest risk is jumping straight to a
  vLLM benchmark when the real cost is in Python or Postgres. The
  promotion gate forces Part 1 first; do not amend the gate.
- **MoE prefill batching is worse than dense prefill batching.** The
  3–6× number is best-case; this workload may underperform it.
- **Long-context KV pressure caps batch size.** A 3090 with the model
  loaded has only a few GB of headroom for KV; concurrency is in the
  small single digits at the current 60K-char window. Smaller windows
  raise the ceiling but only if Part 2 shows fragmentation parity.
- **AWQ-INT4 ≠ IQ4_XS for segmentation.** Phase 2 outputs gate every
  downstream stage; output drift is more expensive here than in
  extraction. "Probably noise-level" is not an answer; measurement is.
- **Model-selection ladder bypass.** A back-end change that quietly
  changes model identity or quantization family enough to count as a
  model change is governed by D042, not by this RFC. The benchmark
  must record the exact model file and quantization family of every
  candidate, and any change to model identity is escalated to
  RFC 0006 / RFC 0008.
- **Prefix-cache fragility.** If the per-window enum currently sits
  before the static prompt block, prefix caching gives nothing. The
  fix is a `SEGMENTER_PROMPT_VERSION` bump, which is its own review
  (see Part 3).
- **Two back-ends in parallel during the experiment.** Port collisions
  and accidental cross-talk to the wrong endpoint must be guarded by
  `ENGRAM_IK_LLAMA_BASE_URL` (or a future
  `ENGRAM_INFERENCE_BASE_URL`) discipline and by the local-only URL
  guard. Both servers stay on `127.0.0.1`.
- **Operational surface area.** vLLM is heavier than `ik-llama-server`.
  It introduces a Python runtime in the serving path, a different
  model-loading workflow, a different metrics surface, and a different
  update cadence. Promotion includes a `systemd` unit story.

## Open questions

1. What is the actual share-of-time breakdown of the current
   segmentation pass? Without Part 1, none of the other parts have a
   sound priority order.
2. Is there a smaller experiment that bypasses weight conversion? For
   example, running vLLM with the existing model in FP16 on a public
   slice (ignoring quantization) to isolate the batching gain from the
   quant question. Same question as RFC 0019 open question 1, asked
   for the segmenter prompt instead.
3. Does the current segmenter prompt assembly already place the static
   block before the per-window enum? If yes, prefix caching is
   immediately exercisable without a `SEGMENTER_PROMPT_VERSION` bump.
   If no, that bump is part of the cost.
4. Is the target Phase 2 model the same family the production segmenter
   uses today, or does this RFC implicitly want a model swap? The
   answer must stay "same family" to keep this RFC scoped to a back-end
   change. A model change re-enters D042.
5. Should the segmenter and extractor share a single inference back-end
   (one vLLM instance serving both) or run two instances on two ports?
   One instance saves VRAM by not double-loading the model, but
   constrains scheduling; two instances are simpler to reason about and
   simpler to scale per phase. Defer this to the post-promotion
   decision in `DECISION_LOG.md`.
6. Naming of the future shared base-URL env var. Same question as
   RFC 0019 open question 5; resolve once and apply to both phases.

## Acceptance criteria for promotion

Promotion paths are split:

- **Idea capture (this RFC):** lands as `proposal` in
  `docs/rfcs/README.md`. No code change is required to accept it.
- **Profile artifact:** producing
  `docs/reviews/phase2/PHASE_2_SEGMENTATION_PROFILE_<date>.md` is the
  next concrete step and is operator work; no `BUILD_PHASES.md`
  promotion is required to run it.
- **Window-budget benchmark:** a follow-up artifact alongside the
  profile result; runs through the existing RFC 0008 public slice. No
  back-end change required.
- **Back-end benchmark:** runs the RFC 0010 shape extended by Part 5.
  Operator work; no `BUILD_PHASES.md` promotion required to run it.
- **Production back-end switch:** requires a `DECISION_LOG.md` entry,
  a new `SEGMENTER_REQUEST_PROFILE_VERSION`, and a re-segmentation
  plan. None of those are authorized by this RFC.
