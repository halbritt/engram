# RFC 0023: Concurrent Extraction Pipeline via Python concurrent.futures
Status: draft
Date: 2026-05-07
Author: halbritt
Related artifacts:
- RFC 0017: Extraction prompt versioning
- RFC 0019: Continuous-Batching Inference Server for Phase 3 Claim Extraction (closed, not promoted)
- REVIEW-0031: Phase 3 Extraction Backend Benchmark (2026-05-07)
- D020: local-only inference
- D034: JSON-schema local model response profile
- D068: review artifact IDs
## Summary
Reduce Phase 3 claim-extraction wall-clock by introducing concurrent dispatch
at the Python orchestration layer, using `concurrent.futures` to overlap
multiple in-flight extraction units against one or more `ik_llama` HTTP
endpoints. Preserves the production extraction contract validated by
`ik_llama` v10. Does not change the inference backend, prompt, schema, or
model.
## Background
REVIEW-0031 confirmed that `ik_llama` is the production extraction backend
on the current single RTX 3090 and Qwen3.6-35B-A3B-IQ4_XS configuration.
Aggregate throughput is 0.0894 segments/sec, full-corpus wall-clock
~21 hours per run.
The same review's decision section names multi-instance sharding as the
priority axis for wall-clock improvement: *"those options keep the known-good
`ik_llama` quality profile while attacking wall-clock through parallelism."*
A second extraction node (proximal-v2) is in build, and the v3-pair NVLinked
node is also in build. When either is online, the corpus can be sharded across
two `ik_llama` endpoints. The dispatch mechanism is the gap this RFC
addresses.
A second, adjacent question is whether the existing single-endpoint pipeline
has untapped concurrency on the Python side — whether DB writes, schema
validation, embedding generation, or other surrounding work can overlap with
in-flight LLM calls. This RFC includes that case as Phase 1 because it is
testable today on proximal alone, before any second endpoint is available.
## Goals
1. Reduce extraction wall-clock by at least 1.5x on a single `ik_llama`
   endpoint without regressing extraction quality (claim count,
   schema-validity, segment completion).
2. Scale near-linearly to N endpoints once additional nodes are online.
3. Maintain the v10 quality contract: 100% segment completion, claim-count
   distribution within 5% of v10 baseline on a same-slice comparison, no
   schema-invalid regression.
4. Preserve idempotency of segment processing: retries do not duplicate
   claims.
5. Add observability sufficient to diagnose worker stalls, endpoint imbalance,
   and quality regressions.
## Non-Goals
1. Changing the inference backend. RFC 0019 closed; vLLM and sglang remain
   experimental harnesses.
2. Changing the extraction prompt, schema, or model.
3. Implementing tensor-parallel or pipeline-parallel inference within a
   single endpoint.
4. Cross-machine distributed orchestration. The network plane between
   proximal, proximal-v2, and v3-pair is local Tailscale only;
   low-coordination dispatch is sufficient.
## Design
### Architecture Overview
Three phases, each independently shippable and gated behind feature flags:
**Phase 1 — single endpoint, concurrent client.** Replace the serial
extraction loop with a `ThreadPoolExecutor` of N workers issuing concurrent
HTTP requests to the existing `ik_llama` endpoint. Each worker handles one
segment end-to-end (request → response → validate → DB write). Determines
whether `ik_llama` benefits from request-level concurrency, and overlaps
Python-side I/O and DB work with GPU compute.
**Phase 2 — multi-endpoint dispatch.** Generalize dispatch across M endpoints,
each with its own per-endpoint worker pool of N workers. Total concurrent
in-flight = M × N. Endpoints registered in config; segments dispatched via a
shared work queue.
**Phase 3 — decoupled stages.** Separate "request LLM" from "validate +
write" into distinct executor stages connected by a bounded queue. Allows the
LLM stage to remain saturated while validation and DB operations run in
parallel.
### Phase 1: Single-Endpoint Concurrent Dispatch
Replace the serial extraction driver with:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
def run_concurrent_extraction(segments, endpoint, max_workers, request_profile):
    with ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix="extract",
    ) as ex:
        futures = {
            ex.submit(extract_one_segment, seg, endpoint, request_profile): seg.id
            for seg in segments
        }
        for fut in as_completed(futures):
            seg_id = futures[fut]
            try:
                result = fut.result()
                handle_extraction_result(seg_id, result)
            except Exception as exc:
                handle_extraction_failure(seg_id, exc)
```
`extract_one_segment` is the existing extraction unit (HTTP call + schema
validation + claim insertion), unchanged in behavior. The change is purely
orchestration: serial → concurrent dispatch.
**Why ThreadPoolExecutor and not ProcessPoolExecutor.** The LLM call is HTTP
I/O from Python's perspective. The GIL is released during socket reads.
ProcessPoolExecutor adds serialization overhead with no concurrency benefit
for I/O-bound workloads, and its process boundary breaks the existing DB
connection pool.
**Worker count tuning.** Sweep N ∈ {1, 2, 4, 8}. Three plausible outcomes:
- `ik_llama` serializes requests with no batching: throughput plateaus at N=1
  or shows mild gain from overlapping HTTP setup, JSON parsing, and DB writes.
- `ik_llama` has any continuous batching or request queueing: throughput
  scales sub-linearly with N up to an endpoint-specific limit.
- Above that limit: throughput plateaus or regresses, queue depths grow,
  per-request latencies increase.
The sweep is the experiment. The optimal N for production is the empirical
answer.
### Phase 2: Multi-Endpoint Dispatch
Configuration adds an endpoint registry:
```yaml
extraction:
  endpoints:
    - name: proximal
      url: http://proximal.local:8080
      workers: 4
      enabled: true
    - name: v3-pair
      url: http://v3.local:8080
      workers: 4
      enabled: true
```
Dispatch strategy: shared work queue, each per-endpoint worker pool pulls
from the queue. This naturally load-balances across endpoints with different
speeds (e.g., the NVLinked v3-pair may be faster than proximal-v2 single-card)
without requiring weight tuning.
Endpoint health checking: HTTP `GET /health` poll on a 30s interval.
Unhealthy endpoints are removed from dispatch; in-flight segments fail fast
and re-queue. No cross-endpoint coordination beyond the shared queue.
### Phase 3: Decoupled Stages
```
[segment iterator]
    → (request_queue, bounded)
    → [N LLM workers]
    → (response_queue, bounded)
    → [M validate+write workers]
    → done
```
Bounded queues prevent runaway memory if one stage stalls. Number of LLM
workers tuned for endpoint capacity (Phase 2). Number of validate+write
workers tuned to keep up with peak claim insertion rate; likely M=2-4 even at
high LLM throughput because DB writes are fast and embeddings are batched.
Phase 3 is incremental over Phase 2; ship only if Phase 2 profiling shows the
validation/write stage is on the critical path.
## Idempotency
Every segment must be safely re-runnable. Existing extraction already writes
per-segment results; the new requirement is that concurrent retries do not
produce duplicate claim rows.
Two enforcement mechanisms, both required:
1. **Pre-flight check.** Before dispatching a segment, query its existing
   extraction state. If marked completed for the current
   `EXTRACTION_PROMPT_VERSION` and request profile, skip.
2. **Insert-time guard.** Segment-id + prompt-version + request-profile is a
   uniqueness key on the claim provenance side. Concurrent inserts of the
   same key collapse to one (conflict-do-nothing) or surface as a clear
   error.
The pre-flight check makes interrupted runs cheap to resume. The insert-time
guard makes correctness independent of orchestration bugs.
## Failure Handling
Failure classes, taken from REVIEW-0031:
- `context-budget`: input too large for endpoint config
- `schema-invalid`: model output failed JSON-schema validation
- `local-validation`: Pydantic or custom validation rejected output
- `network`: connection reset, timeout, etc.
Per-class retry policy:
| Failure class | Retries | Backoff | Re-dispatch eligible? |
| --- | --- | --- | --- |
| `network` | 3 | exponential (1s, 4s, 16s) | yes — may land on different endpoint |
| `schema-invalid` | 1 | none | no — same endpoint |
| `local-validation` | 1 | none | no — same endpoint |
| `context-budget` | 0 | n/a | no — deterministic failure |
Retries on the same endpoint stay pinned to that endpoint to avoid masking
endpoint-specific issues. Network-class retries are eligible to re-dispatch
across endpoints because the original endpoint may be unhealthy.
## Observability
Per-segment trace events: `segment_id`, `endpoint`, `worker_id`,
`request_start`, `request_end`, `response_size`, `claim_count`,
`failure_class` if any.
Per-endpoint aggregate metrics on a rolling 5-minute window:
`segments_completed`, `segments_failed`, `latency_p50`, `latency_p95`,
`in_flight_count`, `queue_depth`.
Workers log to the existing engram event sink. Aggregate metrics exposed via
the Prometheus scrape already present on each node.
## Privacy And Scope
This RFC follows engram's privacy redaction conventions. Segment text, prompt
payloads, and model completions remain on local endpoints and are not
transmitted to remote logging or metrics systems. Aggregate counts, latencies,
endpoint identifiers, and failure classes are the only items emitted to logs
and metrics.
All endpoints bind to private network addresses (Tailscale 100.x.x.x or local
127.0.0.1) per D020 local-only inference. The shared work queue is
in-process; no network coordination plane is added.
## Success Criteria
A Phase 1 production rollout requires, evaluated on the 100-segment same-slice
benchmark from REVIEW-0031:
1. 100% segment completion (no regression vs v10's 100% on the slice).
2. Claim count within 5% of v10's 506 claims for the slice.
3. Schema-validity within 1% of v10 (no observable regression).
4. Wall-clock improvement of at least 1.5x vs the serial single-endpoint
   baseline.
Phase 2 production rollout adds:
5. Linear scaling within 80% of theoretical max — two endpoints should yield
   ≥1.6x of single-endpoint Phase 1 throughput.
6. Endpoint imbalance bounded — no endpoint sits idle while another has
   queued work.
Phase 3 rollout adds:
7. Validation/write stage measurably on the critical path before Phase 3 is
   built. If it is not, Phase 3 is not justified.
8. End-to-end wall-clock improvement at least 20% beyond Phase 2.
## Risks And Mitigations
**Risk: `ik_llama` serializes requests with no batching, Phase 1 yields no
throughput gain.**
Mitigation: this is an expected possible outcome and the worker-count sweep
surfaces it cheaply. If N=1 is optimal, Phase 1 still adds the dispatcher
infrastructure that Phase 2 (multi-endpoint) requires, where wins are
guaranteed.
**Risk: concurrent requests cause GPU memory pressure or quality regressions
in `ik_llama`.**
Mitigation: same-slice quality benchmark gates each phase. If quality
regresses, reduce N or fail back to serial behind the feature flag.
**Risk: idempotency bug duplicates claims on retry.**
Mitigation: insert-time uniqueness guard at the DB layer, not just pre-flight
check. Failure mode is loud (constraint violation surfaced as a logged error)
rather than silent (duplicate row).
**Risk: shared work queue contention across endpoints.**
Mitigation: queue is in-process Python; lock contention is microseconds vs
LLM call seconds. Not a real concern at the throughput levels involved.
**Risk: per-endpoint imbalance if endpoints have very different speeds.**
Mitigation: shared queue handles this naturally — fast endpoints pull more
work. Per-endpoint worker count is a first-order tuning knob if needed.
**Risk: thermal or sustained-load issues on proximal under N>1.**
Mitigation: Phase 1C is an explicit sustained-run validation step before
production rollout, not just a single benchmark.
## Open Questions
1. Does `ik_llama` benefit from request-level concurrency? **Empirical
   question, settled by the Phase 1A worker-count sweep.**
2. What is the cost of the pre-flight idempotency check at scale? Likely
   negligible (single indexed lookup per segment), but should be measured on
   the full corpus before Phase 1B production rollout.
3. Should the dispatcher implement priority queues for re-runs vs first-time
   runs? Probably not for v1, but worth flagging if the workflow evolves.
4. Does Phase 3 actually help, or is the validate/write stage already off the
   critical path? Determined by Phase 2 profiling. Default assumption is that
   Phase 3 is not needed.
## Implementation Phases
**Phase 1A** (~1-2 days): Add a `concurrent_extraction` driver alongside the
existing serial one. Add a benchmark mode that runs the same 100-segment
slice from REVIEW-0031 with N ∈ {1, 2, 4, 8}. Capture throughput, latency
distribution, claim count, schema-validity for each. Output a comparable
findings document.
**Phase 1B** (~1 day, conditional): If Phase 1A shows throughput improvement
at N>1 with no quality regression, add the production code path with the
optimal N. Gate behind a feature flag.
**Phase 1C** (~1 day): Sustained-run validation on proximal at the production
worker count. Watch GPU temps, memory pressure, and stability over a 4-8
hour run. Confirm no thermal or queue-depth pathologies.
**Phase 2A** (~2-3 days, after the first additional endpoint is online):
Multi-endpoint dispatcher with shared work queue. Health checking. Re-run
the 100-segment benchmark across two endpoints to validate scaling.
**Phase 2B** (~1 day): Production rollout of multi-endpoint dispatch.
Same feature flag gating.
**Phase 3** (deferred, ~3-5 days when warranted): Decoupled stages. Build
only if Phase 2 profiling shows validation/write on the critical path.
## Decision
If accepted, Phase 1A starts immediately on proximal as a benchmark, with
no production code path changes. Production code paths in Phase 1B and
Phase 2B are gated behind feature flags for safe rollback. Phase 2 ships
when the second endpoint (proximal-v2 or v3-pair, whichever is first online)
is available.
This decision is independent of RFC 0019. It neither depends on nor blocks
any future inference-backend work.
