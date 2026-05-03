# RFC 0006: Public-First Segmentation Model Benchmark

Status: proposal
Date: 2026-05-03
Context: Phase 2 model/profile selection; D005, D034, D037, D039, D041

This RFC proposes a local-only benchmark harness for comparing segmentation
models, request profiles, and cheap non-LLM baselines before changing the
production Phase 2 segmentation contract.

The immediate motivation is evaluating another Qwen candidate model against
the current Qwen 3.6 35B A3B setup and prior Gemma smoke tests. The broader
goal is to stop judging segmenter candidates only by throughput and backend
stability. Segment quality must be measurable before it becomes the input to
claims, beliefs, and `context_for`.

## Problem

Phase 2 has enough operational telemetry to compare model stability:

- parents/min,
- timeout and runaway rate,
- JSON/schema failure rate,
- VRAM behavior,
- backend crash or wedge signatures.

That is necessary but not sufficient. A faster model can still over-fragment
topics, omit quiet but important facts, merge unrelated claims, or produce
segments that are poor extraction units. Once claims and beliefs exist, those
mistakes propagate downstream.

The benchmark should answer two questions independently:

1. Can a model/profile produce valid, provenance-safe segments reliably?
2. Are those segments useful for claim extraction compared with cheap
   deterministic baselines?

D041 changes the benchmark substrate order: start with public datasets for
portability. The private Engram corpus is not a benchmark dependency, and
synthetic fixtures are an edge-case/regression layer rather than the first
quality substrate.

## Scope

This benchmark is a development tool, not a production pipeline path. It should
not mutate active `segment_generations`, activate retrieval-visible rows, or
change `migrations/004_segments_embeddings.sql`.

The harness may use local public-dataset snapshots, scratch tables, temporary
databases, JSON fixtures, or in-memory repositories. If it writes to the normal
schema, it must mark outputs inactive and isolate them by benchmark run id.

Public dataset snapshots are stored outside this repository and outside the
production database. Download and license acceptance are explicit operator
actions outside any no-egress Engram corpus-reading runtime.

## Dataset Order

1. **SuperDialseg first for quality.** It has supervised dialogue segmentation
   labels and supports strict boundary, window-tolerant F1, P_k, and
   WindowDiff scoring without private data.
2. **LMSYS-Chat-1M second for operational stress.** It is closer to real
   human-LLM conversation shape, but it has no segmentation labels. Use it for
   throughput, runaway, schema-validity, VRAM, and backend-stability metrics,
   not for boundary or claim-recall scores unless labels are separately
   authored.
3. **Synthetic fixtures third for traps and regressions.** They remain small,
   versioned, and hand-authored to cover edge cases public datasets do not
   isolate well.

The private Engram corpus is intentionally absent from this order. It can be
used later for private local smoke only, but it must not be required for model
or strategy comparisons.

## Public Dataset Use

Public datasets are the primary starting point, not optional follow-up work.

**SuperDialseg** (Jiang et al., EMNLP 2023): 9,478 dialogues with supervised
topic-segmentation boundaries derived from document-grounded dialogue corpora,
plus human verification on the test set. Public sources currently expose it as
[`Coldog2333/super_dialseg`](https://huggingface.co/datasets/Coldog2333/super_dialseg)
on Hugging Face and the
[`Coldog2333/SuperDialseg`](https://github.com/Coldog2333/SuperDialseg)
project repository. Use cases:

- Score segmenters against labeled dialogue boundaries at a scale synthetic
  fixtures cannot reach.
- Compare against dialogue-segmentation literature when assessing whether a
  candidate model/profile is competitive for the task category, not just for
  Engram-shaped private data.
- Exercise deterministic baselines and P-FRAG candidates without any private
  corpus dependency.

**LMSYS-Chat-1M**: 1M real human-LLM multi-turn conversations across 25 LLMs,
available through
[`lmsys/lmsys-chat-1m`](https://huggingface.co/datasets/lmsys/lmsys-chat-1m).
No segmentation labels. Use cases:

- Operational stress on a distribution closer to Engram's actual ChatGPT /
  Claude / Gemini corpus.
- Throughput, runaway rate, schema-valid rate, VRAM behavior, and backend error
  taxonomy on realistic prompt distributions.
- Distribution-shape checks for the prompt builder and structured-output
  parser, without authoring more synthetic fixtures.

Quality metrics that depend on labels (boundary precision/recall, W-F1, P_k,
WindowDiff, claim precision/recall) cannot use LMSYS-Chat-1M unless a separate
labeling layer exists.

LMSYS-Chat-1M is gated on Hugging Face and carries restrictive terms, including
non-identification, prohibited transfer, and deletion-on-request obligations.
Its license permits compliant research and commercial development use, but the
dataset must be isolated to local benchmark runs, not redistributed, and never
mixed into Engram's production corpus. Download and license acceptance happen
outside any no-egress Engram corpus-reading runtime.

## Synthetic Fixture Set

Create a small set of synthetic parent conversations with deterministic,
human-authored expected outputs after the public-dataset adapters exist. Start
at 12-15 parents covering the listed fixture families, and grow only when a
real failure mode escapes the public bench. Hand-grading 50 fixtures up front
is expensive and the marginal coverage past ~15 well-chosen fixtures is small.

The fixture set is versioned. `synthetic_parents.jsonl` carries a leading
header object with `fixture_version` (semver-style: bump minor on additions,
major when expected outputs for an existing fixture change). Each result file
records the `fixture_version` it was scored against, so green runs across
fixture edits are not falsely comparable.

Each fixture should include:

- source kind,
- parent id,
- ordered messages with stable UUIDs,
- role,
- content text,
- optional null/tool/image placeholders,
- privacy tier,
- expected segment spans,
- expected atomic claims,
- notes explaining the trap the fixture is meant to exercise.

Recommended fixture families:

- short clean Q&A,
- long coding/debugging thread,
- multi-topic drift with return to an earlier topic,
- repeated or near-duplicate facts,
- quiet preference embedded in a noisy exchange,
- temporal statement with relative dates,
- contradiction inside one parent,
- tool/file artifact placeholders,
- null/image/tool-only messages,
- privacy-tier mixed messages,
- parent near the context guard boundary,
- JSON-looking content inside a message,
- messages whose UUID-like text is not a real message id,
- contiguous role-turn groups that are a plausible cheap fallback,
- a conversation that should become exactly one segment.

The expected output should be verifiable by code. Avoid vague judgments such as
"good topic split." Prefer explicit spans and explicit claims.

## Candidate Strategies

The first benchmark round should compare:

- current Qwen model/profile,
- the new Qwen candidate model/profile,
- any Gemma profile still under consideration,
- fixed N-token windows with overlap,
- message-group segmentation: one segment per contiguous role-turn group up to
  N estimated tokens.

The LLM strategies should use the deterministic D034 request profile unless a
candidate requires an explicit, versioned deviation. Any deviation must be
reported as part of the benchmark output.

The deterministic baselines are cheap insurance. Even when LLM topic
segmentation wins, their gap matters for model portability and fallback
planning when the segmenter model is unavailable.

## Metrics

Report operational metrics per model/profile/strategy:

- valid JSON rate,
- schema-valid rate,
- provenance-valid `message_ids` rate,
- unknown-message-id count,
- cross-parent-message-id count,
- empty embeddable segment count,
- sub-floor fragment counts at 50, 100, and 200 estimated tokens,
- timeout/runaway count,
- parent throughput,
- token throughput when exposed by the backend,
- peak and steady VRAM,
- backend errors grouped by class.

Report segmentation metrics:

- median, p10, and p90 segment token length,
- segment count per parent,
- expected-span precision and recall (strict boundary match),
- window-tolerant F1 (W-F1) at boundary tolerance values that match the
  segmenter's expected granularity (recommend reporting at ±1 and ±2 message
  positions),
- P_k (Beeferman et al., 1999) for probability-of-disagreement-at-distance-k,
- WindowDiff (Pevzner & Hearst, 2002) for boundary-count-aware penalty,
- boundary over-split count,
- boundary under-split count,
- topic re-entry handling on fixtures that return to an earlier topic.

Strict F1 alone is brittle for fuzzy boundaries: a one-message offset on a
correct topic shift counts as both a false positive and a false negative.
Window-tolerant F1, P_k, and WindowDiff are the dialogue-segmentation
literature standards and should be reported alongside strict F1 so a candidate
that is "close enough" is not penalized identically to one that is structurally
wrong. Strict F1 stays useful as a hard ceiling on perfectly-aligned output.

Report claim utility metrics by running the same local extraction prompt over
each strategy's segments:

- claim precision against expected fixture claims,
- claim recall against expected fixture claims,
- unsupported claim count,
- duplicate claim count,
- privacy-tier leakage count.

Claim extraction does not need to be production Phase 3. A benchmark-only
extractor prompt is acceptable if it is fixed across all strategies and its
version is recorded in the output.

The benchmark-only extractor is a within-run measuring stick, not a Phase 3
quality predictor. It exists to compare strategies under identical extraction
conditions in a single benchmark run. Claim precision/recall numbers do not
project onto the eventual Phase 3 extractor's output, and should not be cited
as a Phase 3 readiness signal. Each result file should reproduce the
benchmark-extractor prompt version verbatim so cross-run claim-utility
comparisons are unambiguous.

## Decision Rules

Do not choose a model by throughput alone.

A candidate model/profile can replace the current one only if:

- it preserves provenance-valid output,
- it has no worse runaway or backend-wedge behavior on the public benchmark
  slice,
- it has comparable or better claim precision,
- it has comparable or better claim recall,
- and its throughput improvement is large enough to matter operationally.

For D039 / P-FRAG, preserve the deferred decision rule:

If D034-profile LLM topic segmentation fails to beat fixed N-token windows on
claim precision and produces more sub-floor fragments, falsify D005 as the
unquestioned embedding/extraction unit and revisit before changing the
deployed segmentation contract.

If topic segmentation wins, pin the minimum segment floor where it stops
over-fragmenting and only then consider a follow-up migration for
`min_token_count`, `merge_rule`, or expanded `window_strategy` values.

## Reproducibility

Each result file must record enough metadata to reproduce the run on the same
hardware:

- git commit (already in the existing per-result list),
- model file path **and** SHA256,
- ik-llama or Ollama endpoint version, build commit, and `/props` snapshot
  where applicable,
- request profile name + version,
- segmenter prompt version,
- benchmark-extractor prompt version,
- context window, max tokens, retry max tokens, batch and ubatch sizes,
- sampling parameters (`temperature=0`, `top_p`, seed if applicable),
- CUDA toolkit and driver versions,
- fixture version,
- public-dataset version/snapshot identifier when used,
- environment variables that influence behavior (e.g. `ENGRAM_SEGMENTER_*`).

Determinism caveats: ik-llama output can vary slightly across batch sizes and
across server restarts even at `temperature=0`. The harness should treat
single-run scores as point estimates, not exact reproductions, and should
report median across N reruns when a metric is being used to make a
decision-grade comparison between candidates.

## Harness Shape

Recommended repo layout:

```text
benchmarks/
  segmentation/
    datasets.py
    fixtures/
      synthetic_parents.jsonl
      expected_claims.jsonl
    run_benchmark.py
    strategies.py
    scoring.py
    README.md
```

The harness should:

1. Load public dataset snapshots and fixtures without requiring the production
   database.
2. Run each configured strategy against the exact same parent set.
3. Validate output against the same segment parser/provenance rules used by
   Phase 2 where practical.
4. Run the fixed claim extraction prompt over resulting segments.
5. Emit one machine-readable result file and one human-readable Markdown
   report.

Failure modes the harness must handle without corrupting partial results:

- backend unreachable on startup → abort cleanly before running any strategy,
  emit a result file with `aborted: true` and the failed precondition;
- backend becomes unreachable mid-run → record per-strategy partial counts,
  mark the run incomplete, do not rerun automatically;
- a strategy times out on a single fixture → record the timeout against that
  fixture and continue with the next fixture; report aggregate timeout count
  per strategy;
- a strategy returns malformed output → score as a provenance-validation
  failure for that fixture, do not exclude from aggregates;
- fixture file fails to parse → abort the run before any strategy starts so
  partial results cannot be misattributed to the wrong fixture set.

Suggested output path:

```text
benchmarks/segmentation/results/YYYYMMDDTHHMMSSZ/
```

Each result should record:

- git commit,
- model path/id,
- ik-llama or Ollama endpoint version/properties where applicable,
- request profile,
- context window,
- max tokens,
- timeout,
- fixture version,
- extraction prompt version,
- all aggregate metrics,
- per-fixture failures.

## Non-Goals

- No full-corpus benchmarking.
- No production activation of benchmark generations.
- No automatic model selection.
- No schema migration as part of the first benchmark.
- No claim/belief production pipeline dependency.

## Consequences

This gives Engram a falsifiable and portable way to compare new local models
before spending multi-day private corpus passes. It also creates a stable target
for future segmenter refactors: if the public benchmark, synthetic regression
fixtures, and later gold set stay green, internal structure can change without
guessing about semantic regressions.
