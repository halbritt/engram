# Segmentation Benchmark Specification

Status: skeleton/spec only

This benchmark turns RFC 0006 into an implementation plan. It is a local-only,
scratch-only tool for comparing segmentation strategies before changing
production Phase 2 behavior.

## Design Principles

- No cloud dependency and no user data leaving the machine.
- No writes to the production database.
- Benchmark outputs are inactive artifacts scoped by benchmark run id.
- Production Phase 2 schema remains authoritative; P-FRAG stays deferred per
  D039.
- Deterministic, structured request contracts from D034 are the default for LLM
  strategies.
- Context-boundary failures must fail closed per D037.

## Fixture Schema

Synthetic parent fixtures live in JSONL. The first line is a header object.

```json
{
  "record_type": "header",
  "fixture_version": "0.1.0",
  "schema_version": "segmentation-fixtures.v1",
  "description": "Synthetic fixtures only; no real user data."
}
```

Each later line is a parent fixture:

```json
{
  "record_type": "fixture",
  "fixture_id": "multi_topic_reentry_001",
  "source_kind": "chatgpt",
  "parent_id": "00000000-0000-4000-8000-000000000101",
  "title": "Synthetic multi-topic re-entry",
  "privacy_tier": 1,
  "messages": [
    {
      "id": "00000000-0000-4000-8000-000000001001",
      "sequence_index": 0,
      "role": "user",
      "content_text": "Synthetic text.",
      "privacy_tier": 1,
      "placeholders": []
    }
  ],
  "expected_segments": [
    {
      "segment_id": "s1",
      "message_ids": ["00000000-0000-4000-8000-000000001001"],
      "topic_label": "short label for humans",
      "summary": "Expected topic summary.",
      "expected_claim_ids": ["c1"]
    }
  ],
  "fixture_notes": [
    "What failure mode this fixture exercises."
  ]
}
```

Rules:

- `message_ids` in expected segments are ordered UUID strings from the same
  parent fixture.
- Expected segment spans are explicit, not vague topic judgments.
- Null, image-only, and tool/file artifact messages are represented as
  placeholder messages and may be included in expected spans for provenance.
- `privacy_tier` on an expected segment is computed as the max of parent and
  covered message tiers when scoring privacy leakage.
- Fixture version bumps minor for additive fixtures and major when expected
  output for an existing fixture changes.

## Expected-Claims Schema

Expected claims may be embedded in the fixture or stored as a companion JSONL
file keyed by `fixture_id`. The companion form is preferred once fixtures grow.
The first line is a header with the same `fixture_version`.

Each claim set record:

```json
{
  "record_type": "expected_claim_set",
  "fixture_id": "multi_topic_reentry_001",
  "claims": [
    {
      "claim_id": "c1",
      "claim_text": "The synthetic user prefers concise weekly planning notes.",
      "evidence_message_ids": ["00000000-0000-4000-8000-000000001001"],
      "expected_segment_ids": ["s1"],
      "privacy_tier": 1,
      "stability_class": "preference",
      "valid_from": null,
      "valid_to": null,
      "match_aliases": [
        "prefers short weekly planning notes"
      ]
    }
  ]
}
```

Claim utility scoring uses a fixed benchmark-only extractor prompt. It is a
within-run measuring stick, not Phase 3 quality evidence. Result files must
record the extractor prompt version verbatim.

## Result Schema

The future runner writes one JSON result object per strategy/run. JSONL is also
acceptable for streaming, as long as every result record is self-contained.

```json
{
  "schema_version": "segmentation-benchmark-result.v1",
  "run_id": "2026-05-03T00-00-00Z.current-qwen.synthetic-v0.1.0",
  "created_at": "2026-05-03T00:00:00Z",
  "fixture_version": "0.1.0",
  "dataset": {
    "kind": "synthetic",
    "snapshot": "fixtures/segmentation/0.1.0"
  },
  "strategy": {
    "name": "current_qwen_d034",
    "kind": "llm",
    "implementation_version": "segmentation-benchmark-strategy.v1",
    "config": {}
  },
  "reproducibility": {},
  "parents": [],
  "metrics": {}
}
```

Parent-level result records should include raw model output references, parsed
segments, validation failures, timings, token counts where available, VRAM
samples where available, and scoring details. Large raw outputs should be
written as separate scratch artifacts referenced by SHA256 and relative path.

## Strategy Interface

All strategies take an in-memory benchmark parent and return proposed segments.
They must not open production database connections.

```python
class SegmenterStrategy(Protocol):
    name: str
    kind: Literal["llm", "fixed_window", "message_group"]

    def segment(self, parent: BenchmarkParent, config: RunConfig) -> StrategyOutput:
        ...
```

Required initial strategies:

- `current_qwen_d034`: current Qwen model/profile using the D034 request shape.
- `qwen_candidate_d034`: another Qwen candidate, explicitly configured.
- `gemma_candidate_d034`: optional Gemma candidate if configured.
- `fixed_token_windows`: fixed N estimated-token windows with overlap.
- `message_groups`: contiguous role-turn groups capped by estimated tokens.

LLM strategy deviations from D034 must be versioned and surfaced in result
metadata. Deterministic baselines should use the same token-estimation policy
for comparable fragment-floor reporting.

## CLI Shape

The future CLI should be explicit about scratch-only operation:

```bash
python -m benchmarks.segmentation.run_benchmark validate-fixtures \
  --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl \
  --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl

python -m benchmarks.segmentation.run_benchmark list-strategies

python -m benchmarks.segmentation.run_benchmark run \
  --fixtures benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl \
  --expected-claims benchmarks/segmentation/fixtures/expected_claims.example.jsonl \
  --strategy current_qwen_d034 \
  --strategy fixed_token_windows \
  --output-dir .scratch/benchmarks/segmentation \
  --offline

python -m benchmarks.segmentation.run_benchmark score \
  --results .scratch/benchmarks/segmentation/run.jsonl
```

`--offline` is the default posture: no downloads, no service discovery, no model
calls unless a later implementation adds an explicit local strategy enable flag.

## Scoring Plan

Operational metrics:

- valid JSON rate
- schema-valid rate
- provenance-valid `message_ids` rate
- unknown message id count
- cross-parent message id count
- empty embeddable segment count
- sub-floor fragment counts at 50, 100, and 200 estimated tokens
- timeout/runaway count
- parent throughput
- token throughput when exposed by the backend
- peak and steady VRAM
- backend errors grouped by class

Segmentation metrics:

- median, p10, and p90 segment token length
- segment count per parent
- strict expected-boundary precision and recall
- window-tolerant F1 at +/-1 and +/-2 message positions
- P_k
- WindowDiff
- boundary over-split count
- boundary under-split count
- topic re-entry handling for fixtures flagged as re-entry traps

Boundary representation:

- Convert each segmentation to boundary positions between message sequence
  indexes.
- Strict precision/recall requires exact boundary matches.
- Window-tolerant F1 counts a predicted boundary as matching if it is within
  the configured tolerance of an unmatched expected boundary.
- P_k and WindowDiff operate over the boundary vector for each parent, then are
  macro-averaged across fixtures.

Claim utility metrics:

- claim precision against expected fixture claims
- claim recall against expected fixture claims
- unsupported claim count
- duplicate claim count
- privacy-tier leakage count

Claim matching starts with normalized exact text plus `match_aliases`; semantic
matching by a local judge is an open question and must not be introduced without
versioned scoring metadata.

## Failure-Mode Handling

Classify failures without hiding them behind aggregate scores:

- `invalid_json`: output cannot be parsed as JSON.
- `schema_invalid`: parsed JSON does not match the required segment schema.
- `provenance_unknown_id`: segment cites a message id absent from the fixture.
- `provenance_cross_parent_id`: segment cites a valid UUID from a different
  parent fixture.
- `provenance_unordered`: cited ids are not in parent message order.
- `empty_embeddable_text`: segment text is empty after benchmark
  canonicalization.
- `context_budget`: request would reach context shift or configured budget.
- `timeout`: request exceeds configured deadline.
- `runaway`: generation reaches runaway heuristics or retry max tokens.
- `backend_error`: local endpoint failure grouped by backend signature.
- `public_dataset_unavailable`: optional public dataset snapshot missing or not
  licensed locally.

Failed parent results are still result rows. They contribute to operational
failure metrics and are excluded only from metrics that require valid segment
boundaries, with denominator reporting.

## Reproducibility Metadata

Every result file must include:

- git commit
- model path/id and SHA256
- endpoint version/properties
- request profile and prompt versions
- context window, max tokens, retry max tokens, batch, and ubatch
- sampling params
- CUDA toolkit and driver versions
- fixture version
- public dataset snapshot/version if used
- relevant `ENGRAM_SEGMENTER_*` environment variables
- benchmark strategy implementation version
- scoring implementation version
- benchmark-only extractor prompt text/version

Single runs are point estimates. Decision-grade comparisons should report the
median across N reruns because local deterministic decoding can still vary
across server restarts and batch sizes.

## Public Dataset Handling

Public datasets are optional. The synthetic fixture set is sufficient for the
initial harness.

Rules:

- Download and license acceptance happen outside any Engram corpus-reading
  runtime.
- Store public datasets under an ignored local scratch path, not in this repo
  and not in the production database.
- Record dataset name, source, license state, snapshot/version, local path hash,
  and preprocessing script version.
- Never redistribute dataset rows or derived examples in committed fixtures.
- Never mix public dataset rows into Engram's production corpus.
- SuperDialseg may be used for labeled topic-boundary metrics.
- LMSYS-Chat-1M may be used only for operational stress metrics unless labels
  are separately authored.

## Open Questions For Review

- Should expected claims stay embedded in parent fixtures or remain in a
  companion JSONL once the fixture set grows?
- What exact text-normalization rules are acceptable before claim matching
  needs a local judge?
- What thresholds define "comparable or better" for claim precision/recall and
  provenance validity?
- Should fixed-window baselines use estimated tokens from the current segmenter
  heuristic or a tokenizer-specific estimate?
- Which public dataset, if any, is worth adding first after synthetic fixtures?
- Should benchmark artifacts ever use scratch tables, or should the first
  implementation stay purely file/in-memory?
- What minimum segment floor should trigger a follow-up P-FRAG schema proposal?
