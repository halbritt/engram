<a id="rfc-0037"></a>
# RFC 0037: OutputGuard for Segmentation Structured Output

| Field | Value |
|-------|-------|
| RFC | 0037 |
| Title | OutputGuard for Segmentation Structured Output |
| Status | proposal |
| Implementation | none |
| Date | 2026-05-13 |
| Context | PHASE-0002 segmentation; RFC 0006 segmentation benchmark; RFC 0008 early-signal benchmark; RFC 0010 segmenter throughput profile; RFC 0020 segmentation batching server; D020 local-only execution; D021 derivation versioning; D034 deterministic structured request contract; D035 inference health diagnostics; D037 context-shift guard; `src/engram/segmenter.py:239` (`IkLlamaSegmenterClient.segment`); `src/engram/segmenter.py:369` (`parse_segmentation_response`); `docs/segmentation.md` |

Decision refs:
  - none yet (proposal)

Review refs:
  - none yet

Phase refs:
  - PHASE-0002

This RFC proposes introducing
[OutputGuard](https://github.com/ndcorder/outputguard) as a narrow Phase 2
structured-output validation and repair layer for segmentation responses.
Segmentation is the direct fit: Engram chunks local conversation text into
topic sections and requires the local model to return schema-constrained JSON
of the form `{"segments": [...]}`.

The model-portability claim is simple: Engram should not bake every local
runtime's JSON quirks into handwritten parsing branches. The segmenter should
own the semantic contract: segment order, message-id provenance,
non-empty content, privacy carry, and activation rules. A small local
structured-output adapter absorbs well-understood syntax-level variance across
models and runtimes.

This is **not** a serving proposal. It does not change `context_for`, Phase 5,
MCP, ranking, hot snapshots, or any assistant-facing output. It is a Phase 2
derivation-boundary proposal.

## External Dependency Snapshot

As of 2026-05-13, OutputGuard's README describes it as a Python library for
validating, repairing, and retrying LLM structured outputs. It supports JSON
Schema validation, batch validation, guarded generation wrappers, retry prompt
generation, and fifteen repair strategies for common JSON-family failures such
as code fences, trailing commas, comments, single quotes, unquoted keys,
truncated objects, ellipses, bad Unicode, and unclosed containers.

Its `pyproject.toml` reports:

- package name: `outputguard`
- version: `2.1.0`
- license: MIT
- Python: `>=3.10`
- runtime dependencies: `click`, `jsonschema`, `pyyaml`, `rich`, and `tomli`
  only on Python versions before 3.11

OutputGuard operates on strings and schemas. It has no LLM provider dependency
and does not require network access at runtime. This makes it compatible with
Engram's local-first constraint, subject to normal dependency review and
pinning.

## Motivation

Engram's current segmenter already does the hard architectural parts correctly:

1. It calls only the local OpenAI-compatible ik-llama endpoint.
2. It uses D034 deterministic settings: no streaming, temperature zero,
   bounded `max_tokens`, thinking disabled, and `response_format` set to
   `json_schema`.
3. It constrains `message_ids` to the active window's actual UUIDs.
4. It parses only `choices[0].message.content`.
5. It rejects empty content, `reasoning_content` payloads, Markdown-fenced
   JSON, invalid JSON, schema-invalid payloads, and provenance-invalid
   segments.
6. It records failed generations and retries through the existing Phase 2
   run machinery.

The brittle part is the generic structured-output shell around the domain
contract. `parse_segmentation_response()` currently contains local hand-rolled
checks for formatting failures before falling through to `json.loads()` and
then to Engram's own payload parser. That is fine for one model/runtime pair,
but it becomes model-portability friction as Engram rotates local models and
inference servers.

Different local models and grammar implementations fail differently:

- Some wrap otherwise-valid JSON in code fences.
- Some emit valid JSON plus commentary when constrained decoding weakens.
- Some produce trailing commas or single quotes.
- Some encode tokenization artifacts in the first few characters.
- Some fail near context pressure with unclosed strings or containers.

D034 intentionally pins a deterministic request contract, but it should not
require every future model migration to re-teach Engram the same JSON cleanup
routine. A dedicated structured-output adapter can make the portability layer
explicit, testable, and versioned.

## Proposal

Add a Phase 2 segmentation structured-output adapter, initially backed by
OutputGuard, between the raw model response string and
`parse_segmentation_payload()`.

Current path:

```text
HTTP response
  -> choices[0].message.content
  -> json.loads
  -> parse_segmentation_payload
  -> database provenance / activation guards
```

Proposed path:

```text
HTTP response
  -> choices[0].message.content
  -> segmentation structured-output adapter
       - validate against segmentation_json_schema(...)
       - optionally apply conservative syntax repair
       - report repair metadata
  -> parse_segmentation_payload
  -> database provenance / activation guards
```

The adapter must be local, deterministic, and narrow. It is not allowed to
reinterpret segment semantics. Engram's existing parser and database guards
remain authoritative for:

- exact top-level keys,
- required segment fields,
- non-empty segment text,
- `message_ids` shape,
- allowed-message membership,
- segment ordering and parent-scoped provenance,
- privacy-tier propagation,
- generation activation and invalidation behavior.

OutputGuard may only help the response become parseable and JSON
Schema-valid before the Engram-specific checks run.

## Conservative Strategy Profile

Production segmentation must start with an allowlist of syntax-level repair
strategies. The default profile should be intentionally smaller than
OutputGuard's full strategy set.

Allowed in the first production profile:

- `strip_fences`
- `fix_commas`
- `fix_encoding`
- `fix_newlines`

Allowed only after benchmark evidence:

- `fix_quotes`
- `fix_keys`
- `fix_booleans`
- `remove_comments`
- `extract_json`
- `fix_closers`

Disallowed for production segmentation unless a later decision accepts the
risk:

- `fix_truncated`
- `fix_ellipsis`
- `fix_values`
- `fix_unicode`
- `fix_inner_quotes`

The disallowed group can silently change information content or turn a
semantically incomplete segmentation into something schema-valid. Engram
already has a safer path for truncation-like failures: retry the same prompt
with a larger output budget, bounded by the context guard and retry cap.

## Model Portability Contract

The adapter exists to make model/runtime swaps less invasive, not to hide
quality regressions.

Every segmentation run that uses OutputGuard must record enough metadata to
make later re-derivation auditable:

- `structured_output_adapter`: e.g. `outputguard`
- `structured_output_adapter_version`: e.g. `outputguard==2.1.0`
- `structured_output_profile_version`: an Engram-owned profile string
- `strategies_allowed`
- `strategies_applied`
- `repaired`: boolean
- `repair_confidence` when available
- `schema_valid_before_repair`: boolean when measured
- `schema_valid_after_repair`: boolean

If production behavior changes, `SEGMENTER_REQUEST_PROFILE_VERSION` must bump.
That preserves D021's derivation-versioning invariant: a segment generation
produced under strict `json.loads()` is not the same derivation profile as one
produced under `outputguard` repair.

The model-portability win is that future model migrations can compare:

```text
same prompt/schema/window
  + model A / profile strict-json
  + model B / profile outputguard-conservative
```

without collapsing syntax repair, semantic segmentation quality, and model
choice into one undiagnosable failure bucket.

## Privacy And Local-First Constraints

OutputGuard itself is local string processing, but segmentation outputs may
contain private corpus text in `content_text`. Therefore:

1. No OutputGuard diagnostics containing raw model output, repaired text, or
   diffs may be committed to the repository.
2. Committed benchmark summaries must redact or aggregate repair examples.
3. `retry_prompt()` must not be used in production segmentation unless
   `include_message_history=False` is set or an Engram-owned prompt builder
   proves that private output is not copied into committed artifacts.
4. `guarded_generate()` must not replace Engram's segmenter orchestration in
   the first implementation; Engram keeps ownership of HTTP calls, retries,
   context guards, and run-state persistence.
5. Dependency installation must not add telemetry, hosted services, or runtime
   network calls.

This proposal does not relax D020. The corpus-reading process still has no
network egress.

## Adoption Plan

### Stage 0: Offline Audit

Add a scratch-only audit tool that reads failed segmentation model responses
from local untracked logs or an operator-provided JSONL file, runs the proposed
OutputGuard profile, and reports aggregate counts:

- total failures inspected,
- valid without repair,
- valid after allowed repair,
- invalid after allowed repair,
- strategy counts,
- rejected-by-profile strategy counts,
- downstream `parse_segmentation_payload()` pass/fail counts.

The tool must not write production tables and must not commit private outputs.
This stage can live under `benchmarks/segmentation/` or `scripts/` depending
on how reusable it becomes.

Promotion from Stage 0 requires evidence that repaired outputs pass Engram's
own parser and provenance checks without increasing fragmentation or
overlap-quality failures on a representative Phase 2 replay slice.

### Stage 1: Optional Production Adapter

Add an optional dependency extra, likely `engram[structured-output]`, and an
explicit environment flag:

```text
ENGRAM_SEGMENTER_STRUCTURED_OUTPUT_ADAPTER=outputguard
ENGRAM_SEGMENTER_STRUCTURED_OUTPUT_PROFILE=conservative-v1
```

Default remains the current strict parser until the RFC is accepted and
benchmark evidence justifies changing the default.

### Stage 2: Default For New Model Profiles

If Stage 1 reduces format-related failures without hiding semantic failures,
make the adapter part of the default request profile for new segmentation model
versions only. Existing segment generations remain reproducible under their
old profile strings.

## Implementation Sketch

Likely code shape:

- Add `src/engram/structured_output.py` or `src/engram/segment_output.py` with
  a small Engram-owned interface:

  ```python
  @dataclass(frozen=True)
  class StructuredOutputResult:
      payload: dict[str, object]
      repaired: bool
      strategies_applied: tuple[str, ...]
      metadata: dict[str, object]
  ```

- Keep `src/engram/segmenter.py::parse_segmentation_payload()` unchanged as
  the domain parser.
- Change `parse_segmentation_response()` to call the adapter only after the
  existing `choices[0].message.content` checks.
- Add tests around:
  - fenced JSON repairs,
  - trailing comma repairs,
  - disallowed truncated-output repair,
  - invalid message UUID still rejected after repair,
  - schema-valid but Engram-invalid payload still rejected,
  - metadata recorded on segment generation failures/successes.

The adapter should be optional at import time. If the environment selects
`outputguard` and the package is missing, the segmenter should fail closed with
a clear installation error before any long run begins.

## Non-Goals

- No change to segmentation prompt semantics.
- No change to the segment table schema in the first implementation.
- No change to embedding behavior.
- No claim extraction or belief-consolidation adoption in this RFC.
- No Phase 5 serving, MCP, `context_for`, or hot-state changes.
- No automatic acceptance of repaired outputs that fail Engram's existing
  parser or database guards.
- No use of hosted models, hosted validators, or remote schema services.

## Risks

### Repair Can Hide A Real Model Regression

If a model starts returning malformed or partial segmentations, repair may
turn a useful failure signal into a valid-looking payload. The mitigation is
the conservative profile, strategy metadata, benchmark gates, and disallowing
truncation/ellipsis repair by default.

### Dependency Footprint Grows

Engram's base dependency set is intentionally small. OutputGuard brings
`jsonschema`, `PyYAML`, `click`, and `rich`. The mitigation is an optional
extra until benchmark evidence supports making it core.

### Schema Validation May Duplicate Existing Checks

OutputGuard can validate JSON Schema, but Engram already validates the
payload. Duplication is acceptable only if it simplifies portability and
improves diagnostics. Engram-specific validation remains the source of truth.

### Private Text In Diagnostics

Repair reports and diffs can contain segment text. The mitigation is to keep
raw diagnostics untracked and to commit only redacted aggregate summaries.

## Acceptance Criteria

Before this RFC can become an accepted decision:

1. An offline audit over real failed segmentation outputs shows the conservative
   OutputGuard profile recovers a meaningful fraction of formatting failures.
2. A bounded Phase 2 replay compares strict parsing vs OutputGuard parsing on
   the same source slice and reports:
   - segment count distribution,
   - overlap/fragmentation metrics,
   - schema/provenance pass rate,
   - repair strategy counts,
   - failed parent/window count.
3. Every repaired output that reaches the database passes
   `parse_segmentation_payload()` and the existing message-id provenance
   guards.
4. `SEGMENTER_REQUEST_PROFILE_VERSION` is bumped for any production behavior
   change.
5. Committed reports contain no private segment text, raw model output, or
   repaired output.
6. The default production path remains strict until a recorded decision accepts
   the measured behavior change.

## Open Questions

1. Should OutputGuard be a dev/benchmark-only dependency first, or an optional
   runtime extra from the start?
2. Which exact repair strategies belong in `conservative-v1` after Stage 0
   tests against real Engram failures?
3. Should repair metadata live only in `segment_generations.raw_payload`, or
   should successful repaired segment rows also carry a compact marker in
   `segments.raw_payload`?
4. Is JSON Schema validation through OutputGuard measurably helpful when the
   ik-llama grammar already uses the same schema, or is OutputGuard valuable
   mainly for syntax cleanup and diagnostics?
5. Does adopting OutputGuard for segmentation make a later extraction adapter
   easier, or should extraction remain separate because D064 accounted-zero
   semantics are more delicate?
