# RFC 0006: Synthetic Segmentation Model Benchmark

Status: proposal
Date: 2026-05-03
Context: Phase 2 model/profile selection; D005, D034, D037, D039

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

## Scope

This benchmark is a development tool, not a production pipeline path. It should
not mutate active `segment_generations`, activate retrieval-visible rows, or
change `migrations/004_segments_embeddings.sql`.

The harness may use scratch tables, temporary databases, JSON fixtures, or
in-memory repositories. If it writes to the normal schema, it must mark outputs
inactive and isolate them by benchmark run id.

## Synthetic Fixture Set

Create a small set of synthetic parent conversations with deterministic,
human-authored expected outputs. The target size is 30-50 parents, enough to
cover edge cases without making every benchmark run expensive.

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
- expected-span precision and recall,
- boundary over-split count,
- boundary under-split count,
- topic re-entry handling on fixtures that return to an earlier topic.

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

## Decision Rules

Do not choose a model by throughput alone.

A candidate model/profile can replace the current one only if:

- it preserves provenance-valid output,
- it has no worse runaway or backend-wedge behavior on the synthetic set,
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

## Harness Shape

Recommended repo layout:

```text
benchmarks/
  segmentation/
    fixtures/
      synthetic_parents.jsonl
      expected_claims.jsonl
    run_benchmark.py
    strategies.py
    scoring.py
    README.md
```

The harness should:

1. Load fixtures without requiring the production database.
2. Run each configured strategy against the exact same parent set.
3. Validate output against the same segment parser/provenance rules used by
   Phase 2 where practical.
4. Run the fixed claim extraction prompt over resulting segments.
5. Emit one machine-readable result file and one human-readable Markdown
   report.

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

This gives Engram a falsifiable way to compare new local models before spending
multi-day corpus passes. It also creates a stable target for future segmenter
refactors: if the synthetic benchmark and later gold set stay green, internal
structure can change without guessing about semantic regressions.
