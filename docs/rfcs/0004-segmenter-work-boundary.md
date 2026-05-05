# RFC 0004: Segmenter Worker Boundary (Augments RFC 0003)

Status: proposal
**Date:** 2026-05-02
**Augments:** RFC 0003 (Decoupling Micro-Architecture in the Segmentation Pipeline)
**Relates to:** RFC 0001 (Supervisor Controller Loop)

## 1. Context

RFC 0003 correctly identifies that `src/engram/segmenter.py` conflates four
operational domains and proposes decomposition along data access, pure domain
logic, transport, and orchestration lines. RFC 0001 establishes that Engram’s
durable execution model is a deterministic supervisor controller invoking
bounded stage workers, with telemetry, retries, backpressure, and scheduling
owned by the supervisor — not by the workers themselves.

These two RFCs are compatible but RFC 0003 was drafted without the supervisor
pattern in view. As a result, several of its proposed seams are placed at the
wrong layer, and one critical concern — versioned LLM request provenance — is
not addressed at all.

This RFC refines RFC 0003 so that the resulting segmenter shape is directly
consumable by the RFC 0001 supervisor.

## 2. Problem Statement

Three concrete deltas against RFC 0003:

- **Telemetry placement.** RFC 0003 §3.1 folds progress/telemetry writes
  (`upsert_progress`, `consolidation_progress`) into the segmenter’s
  repository. Under RFC 0001, progress accounting is a supervisor concern
  (`supervisor_runs`, `stage_attempts`, `memory_events`). Keeping it inside
  the segmenter re-couples the worker to a lifecycle it should not own and
  blocks the supervisor from being the single source of truth for “what work
  has been attempted and with what outcome.”
- **Orchestration terminology.** RFC 0003 §3.3 introduces an “Orchestrator”
  inside the segmenter that pulls from the repository, drives the LLM client,
  and writes back results. RFC 0001 reserves “controller” / “supervisor” /
  “orchestrator” for the deterministic reconcile loop. A second orchestrator
  inside a worker is a category error: the worker should not loop, schedule,
  or decide what to process next. It should accept one bounded unit of work
  and return one bounded result.
- **Versioned request provenance.** RFC 0001 requires that every LLM-mediated
  action be tied to a `prompt/model/request-profile` version and recorded as a
  structured event (D034). RFC 0003 names a transport client that “executes the
  payload, handles timeouts, parses the JSON schema” but does not say where
  the request profile is assembled, validated, or stamped onto the persisted
  segment row. This metadata is load-bearing for replayability and the
  supervisor’s audit story.

## 3. Proposed Refinements

### 3.1 Remove Progress/Telemetry from the Segmenter

The `segmenter_repo.py` boundary proposed in RFC 0003 §3.1 should cover
**segment persistence only**:

- reading eligible `Conversation` / `MessageWindow` inputs,
- writing `SegmentationResult` rows (segments, generation metadata, request
  profile stamps).

It should **not** include:

- `upsert_progress` or any `consolidation_progress` writes,
- `supervisor_runs` / `stage_attempts` writes,
- lease acquisition, retry counters, or backoff state.

These are supervisor-owned. The worker entry point returns a structured
result; the supervisor is responsible for recording the attempt.

### 3.2 Rename “Orchestrator” to “Worker Entry Point”

Replace RFC 0003 §3.3’s “Orchestrator” with a single typed worker entry point.
Proposed signature:

```python
def run_segmenter(
    work: SegmenterWorkItem,
    repo: SegmenterRepository,
    client: LlmTransportClient,
    profile: RequestProfile,
) -> SegmenterAttemptResult:
    ...
```

Where:

- `SegmenterWorkItem` is a bounded input (e.g., a single conversation id plus
  window parameters), supplied by the supervisor.
- `RequestProfile` is the explicit, versioned `(prompt_version, model_version, request_profile_version)` triple.
- `SegmenterAttemptResult` is a sum type covering `Success(segments, stamp)`,
  `RetryableFailure(reason, diagnostic)`, and `TerminalFailure(reason, diagnostic)`. The supervisor decides what to do with each variant.

The worker entry point performs no looping, no requeuing, no scheduling, no
multi-conversation iteration. It is a single bounded transformation.

### 3.3 Introduce an Explicit Prompt Builder Module

Prompt assembly is naturally a pure function and should be its own module
(`segmenter_prompt.py`), not buried inside the transport client:

```python
def build_segmentation_prompt(
    window: MessageWindow,
    profile: RequestProfile,
) -> SegmentationRequest:
    ...
```

Inputs are primitives and the request profile; output is a fully-formed,
schema-validated request payload. This module:

- contains zero IO,
- is the single place `prompt_version` is materialized,
- is exhaustively unit-testable against frozen prompt fixtures,
- makes prompt-version diffs reviewable in isolation.

### 3.4 Reduce the Transport Client to Pure Transport

The `IkLlamaSegmenterClient` (or its successor) accepts a fully-formed
`SegmentationRequest`, executes it, enforces timeouts, validates the JSON
schema of the response, and returns a `SegmentationResponse` or a typed
transport failure. It does not build prompts, does not consult the repository,
and does not know about `RequestProfile` semantics beyond passing the model
identifier through.

### 3.5 Stamp the Request Profile on Persisted Rows

`SegmenterRepository.write_result()` must accept and persist the
`RequestProfile` triple alongside each emitted segment row. This is the
mechanism that satisfies RFC 0001’s audit requirement: every persisted
derivation can be replayed from its stored inputs, prompt version, model
version, and request-profile version.

This requires either:

- a column-level addition to `segment_generations` (preferred), or
- a foreign-key reference to a `desired_versions` row (acceptable if the
  versions table from RFC 0001 lands first).

The choice is deferred to whichever supervisor schema work lands first;
RFC 0004 commits only that the worker emits the triple as part of its result.

## 4. Resulting Layering

```
supervisor (RFC 0001)
  -> selects SegmenterWorkItem
  -> opens lease, records stage_attempt start
  -> calls run_segmenter(work, repo, client, profile)
       -> repo.load_window(work) -> MessageWindow
       -> build_segmentation_prompt(window, profile) -> SegmentationRequest
       -> client.execute(request) -> SegmentationResponse | TransportFailure
       -> pure: validate, compute boundaries, assemble SegmentationResult
       -> repo.write_result(result, profile) -> persisted rows
       -> return SegmenterAttemptResult
  -> records stage_attempt outcome, progress, events
  -> decides retry / requeue / escalate
```

No loop inside the worker. No telemetry inside the worker. No prompt
construction inside the transport client. No request-profile guessing
anywhere.

## 5. Migration Order

This RFC does not change RFC 0003’s overall decomposition; it refines the
seams. Suggested staging:

1. Extract pure domain logic (RFC 0003 §3.2) — lowest risk, immediate test
   coverage win.
1. Extract `segmenter_prompt.py` and freeze current prompt as a versioned
   fixture.
1. Reduce transport client to pure transport; thread `RequestProfile`
   through the call sites unchanged.
1. Extract `segmenter_repo.py` for **segment persistence only**; leave
   existing progress writes in place at their current call sites
   temporarily.
1. Introduce `run_segmenter()` worker entry point. Existing CLI batchers
   call it directly, supplying a stub `RequestProfile` from config.
1. Move progress/telemetry writes out of the segmenter and into the CLI
   batcher (as the current stand-in for the supervisor). When the
   RFC 0001 supervisor lands, this seam moves with it cleanly.

Each step is independently shippable and independently revertable.

## 6. Consequences

- **Worker-supervisor contract is explicit.** The segmenter becomes the
  reference implementation for the RFC 0001 stage worker shape. Other
  workers (embedder, claim extractor, belief consolidator) can follow the
  same `(WorkItem, Repository, TransportClient, RequestProfile) -> AttemptResult` template.
- **Audit and replay are first-class.** Any persisted segment can be
  reproduced from its stored work item, prompt version, model version, and
  request-profile version.
- **Prompt evolution is reviewable.** Prompt changes become diffs to a
  single pure module with frozen fixtures, instead of textual edits buried
  in transport code.
- **Telemetry surface shrinks.** The segmenter no longer needs to know
  about `consolidation_progress` at all. Schema changes there stop touching
  segmenter code.
- **Reversibility.** High. No database schema changes are mandatory in this
  RFC; the request-profile stamp can land as a JSON column on existing
  tables and migrate to a normalized form when the supervisor schema work
  arrives.

## 7. Non-Goals

- This RFC does not propose the supervisor itself; that is RFC 0001.
- This RFC does not propose a new request-profile registry; it only requires
  that the worker emit the triple it was invoked with.
- This RFC does not change the LLM request contract defined in D034.
- This RFC does not change bitemporal invariants or privacy tier handling.

## 8. Open Questions

- Should `RequestProfile` be a value object constructed by the caller, or
  resolved by name from a (future) `desired_versions` table?
- Should `SegmenterAttemptResult.RetryableFailure` carry a suggested backoff
  hint, or is backoff strictly the supervisor’s concern?
- Where do partial successes live — does a window that produced some valid
  segments and one schema violation return `Success` with a warning, or
  `TerminalFailure`?
