<a id="rfc-0047"></a>

# RFC 0047: Striatum Retrieval Augmentation Boundary

| Field | Value |
|-------|-------|
| RFC | RFC-0047 |
| Title | Striatum Retrieval Augmentation Boundary |
| Status | proposal |
| Implementation | none |
| Created | 2026-05-14 |
| Source | `STRIATUM_MEMORY_ROADMAP.md` |
| Context | RFC 0044, RFC 0045, RFC 0046, `STRIATUM_MEMORY_ROADMAP.md` |
| Review state | reviewable boundary handoff |

## Summary

This RFC defines the Striatum/Engram retrieval augmentation boundary.
Striatum may use Engram as an optional local read-only augmentation source for
operator and workflow context, but Engram must not become Striatum runtime
infrastructure.

Memory availability must not be authoritative Striatum state. Striatum must
continue to prepare, start, run, review, and recover workflows when Engram is
absent, disabled, unhealthy, unauthorized, stale, malformed, or slow. Absence
or failure degrades gracefully to the existing repository, work-packet, and
operator-context path.

RFC 0045 is the upstream corpus contract for this RFC. RFC 0047 does not
redefine the export format, make bundle identity an authorization grant,
implement projections, expand Engram write surfaces, or decide prompt-injection
budgets. It specifies how retrieval may be requested, how responses must be
cited, what failures mean, and where the boundary must remain uncoupled.

## Roadmap Position

RFC 0047 follows:

- RFC 0044, which established the first local Striatum application-memory
  boundary in Engram;
- RFC 0045, which defines the Striatum Corpus Contract V2 disk bundle;
- RFC 0046, which is expected to define rebuildable Striatum projections and
  indexes over raw evidence.

RFC 0047 feeds:

- RFC 0048, which decides how much retrieved memory may enter operator and
  workflow-agent context;
- RFC 0049, which defines evaluation, no-egress, tenant/corpus isolation,
  stale-index, latency, and retrieval-quality gates.

This document is a review target, not an implementation prompt.

## Boundary Statement

The boundary is:

```text
Striatum authoritative state and current repository context
  -> optional local retrieval request, if configured and enabled
  -> Engram read-only local corpus query
  -> cited augmentation results or a non-fatal status
  -> Striatum operator/agent context as labeled memory, never as authority
```

The inverse boundary is forbidden:

```text
Striatum workflow state
  -> Engram dependency, Engram daemon requirement, memory gate,
     hosted lookup, hidden state transition, or unbounded prompt dump
```

Striatum authoritative state remains in Striatum-owned and repository-owned
surfaces: `.striatum/state.sqlite3`, daemon state, workflow JSON, run records,
RFCs, decision logs, operator reports, changelogs, git history, generated
artifacts, and explicit operator packets. Engram may summarize or cite that
history after export and ingest. It does not replace it.

## Goals

1. Define the augmentation-not-dependency contract for Striatum.
2. Define the allowed local invocation surfaces for Engram retrieval.
3. Define query and response contracts for retrieval augmentation.
4. Define graceful degradation for absent, unhealthy, unauthorized, stale,
   malformed, slow, or disabled Engram retrieval.
5. Define no-egress, no-cloud, no-telemetry, and no-hosted-persistence
   boundaries.
6. Define citation, provenance, confidence, stability, and freshness
   requirements for retrieved memory.
7. Define tenant/corpus isolation rules inherited from RFC 0044 and RFC 0045.
8. Define cache, rebuild, and invalidation rules for retrieval-derived state.
9. Define operator UX boundaries before RFC 0048 chooses injection policy.
10. Preserve compatibility with Striatum running without Engram.

## Non-Goals

- No Striatum daemon dependency on Engram.
- No Striatum state transition, lease, blocker, verdict, artifact publication,
  recovery action, or workflow readiness check that requires Engram.
- No Striatum `memory.*` daemon capability vocabulary.
- No Striatum import of an Engram client library.
- No Engram import of Striatum code at retrieval time.
- No write-side memory mutation from Striatum into Engram.
- No Engram write tools through this boundary.
- No personal-memory access by default.
- No cross-tenant or cross-corpus retrieval by default.
- No hosted MCP server, remote Engram service, cloud API, telemetry, SaaS
  persistence, hosted model call, or network egress from any corpus-reading
  process.
- No broad transcript, raw log, raw model-output, or whole-corpus dumping into
  agent prompts.
- No RFC 0048 context-injection budget decision.
- No RFC 0049 evaluation gate implementation.

## Dependencies

- RFC 0044 Engram-side Phase 1 acceptance with findings.
- RFC 0044 hardening follow-ups for uniform MCP/reference failures,
  tenant/source-kind consistency, validated capability names, real or fixture
  bundle smoke evidence, and schema-version reporting.
- RFC 0045 Striatum Corpus Contract V2. Where older Striatum request text
  conflicts with RFC 0045, the versioned corpus contract wins.
- RFC 0046 projection and index design, once accepted, for structured and
  layered retrieval. Until then, RFC 0044 raw retrieval remains the baseline.
- A reciprocal Striatum-side boundary artifact proving that Striatum does not
  import Engram, does not add daemon RPC dependence on Engram, and degrades
  gracefully when Engram is unavailable.

## Terms

| Term | Meaning |
|------|---------|
| Augmentation | Optional memory retrieved from local Engram and labeled as memory in Striatum context. |
| Authoritative Striatum state | Striatum-owned state and repository artifacts that define workflow truth. Engram availability and memory results are not part of this state. |
| Memory status | A diagnostic such as `available`, `disabled`, `unavailable`, `unauthorized`, `timeout`, `stale`, `malformed`, or `no_data`. It is visible but non-fatal. |
| Citation | A retraceable pointer to RFC 0045 item identity and source provenance, sufficient for an operator or reviewer to find the underlying evidence. |
| Primary pair | The Engram-local default `tenant_id`/`corpus_id` pair in the caller token. Secondary pairs are visible only with explicit Engram-local grants. |

## Allowed Invocation Surfaces

The default review target is a local, operator-configured Engram MCP stdio
server exposing the RFC 0044 read-only tools:

```text
engram.search
engram.fetch_reference
engram.describe_corpus
engram.health
```

An implementation may also provide a thin one-shot Engram CLI wrapper for
health checks or explicit operator search, but it must be outside Striatum
daemon RPC and outside workflow-critical transitions. Any future sidecar must
preserve the same contract: local-only, read-only, no egress, optional, and
non-authoritative.

Forbidden invocation surfaces:

- Striatum daemon RPC methods that call Engram;
- Striatum workflow state fields that make Engram readiness a dependency;
- imports such as `import engram` or `from engram` in Striatum runtime modules;
- hosted or remote Engram endpoints;
- background sync jobs that silently push Striatum state into Engram;
- retry loops that block workflow progress waiting for memory.

## Control Flow

Permitted control flow:

1. Striatum constructs the normal operator or agent packet from authoritative
   local inputs.
2. If retrieval is enabled and configured, the operator/session layer issues
   one or more bounded local retrieval requests to Engram.
3. Engram authorizes the requested tenant/corpus pair using Engram-local
   capabilities, queries local raw evidence or rebuildable projections, and
   returns cited results or a non-fatal status.
4. Striatum labels any accepted results as memory augmentation and keeps them
   distinguishable from current repository state and explicit work-packet
   instructions.
5. If Engram fails or returns no usable results, Striatum continues with the
   baseline packet and may include a concise diagnostic status.

Forbidden control flow:

1. Striatum must not ask Engram whether a workflow may start, continue,
   complete, publish, or recover.
2. Striatum must not use Engram freshness, availability, or retrieval score as
   a required dependency edge.
3. Striatum must not write Engram availability into authoritative daemon state.
4. Striatum must not use Engram results to silently rewrite repository files,
   decision logs, workflow JSON, operator reports, changelogs, or `.striatum/`
   state.
5. Striatum must not retry with broader memory capabilities after an
   unauthorized response.

## Request Contract

RFC 0047 defines a logical request envelope. Implementations may map it to MCP
tool arguments, a CLI JSON argument, or a local library boundary inside Engram,
but the semantics must remain stable.

```json
{
  "schema_version": "striatum.retrieval_request.v1",
  "request_id": "uuid-or-stable-local-id",
  "purpose": "packet_prepare",
  "query_text": "Prior work on RFC 0044 capability boundary repairs",
  "tenant_id": "striatum",
  "corpus_id": "striatum",
  "filters": {
    "sub_kinds": ["rfc", "review", "synthesis", "handoff"],
    "exact_refs": [
      {"ref_kind": "rfc_id", "ref_value": "0044"}
    ],
    "logical_ids": [],
    "paths": [],
    "run_ids": [],
    "workflow_job_ids": [],
    "job_ids": [],
    "artifact_ids": [],
    "rfc_ids": ["0044"],
    "decision_ids": [],
    "commit_shas": [],
    "observed_at_min": null,
    "observed_at_max": null,
    "authority_classes": ["canonical_doc", "accepted_synthesis"]
  },
  "limits": {
    "top_k": 8,
    "max_results": 12,
    "max_excerpt_chars_per_result": 1200,
    "max_total_excerpt_chars": 6000,
    "min_score": null
  },
  "freshness": {
    "max_staleness_seconds": null,
    "accept_stale_with_warning": true
  },
  "timeout_ms": 2000,
  "citation_required": true,
  "include_content": "excerpt",
  "caller_context": {
    "striatum_run_id": null,
    "workflow_job_id": null,
    "job_id": null,
    "session_id": null
  }
}
```

### Request Requirements

- `schema_version` must identify the logical request version.
- `request_id` must be stable enough to correlate logs and diagnostics without
  becoming Striatum state authority.
- `purpose` must be one of the reviewed use cases:
  `operator_startup`, `workflow_scaffold`, `packet_prepare`,
  `review_prepare`, `blocker_recovery`, `ui_search`, or `manual_search`.
- `tenant_id` defaults to `striatum`.
- `corpus_id` defaults to the configured primary Striatum corpus, currently
  `striatum`, with future per-instance values shaped by RFC 0045.
- Cross-corpus or cross-tenant requests must name every requested pair
  explicitly and require matching Engram-local capabilities.
- `query_text` should be a task-focused retrieval query, not an entire packet,
  transcript, raw model output, or private unrelated context.
- `filters` should prefer stable RFC 0045 identifiers: `logical_id`,
  `item_id`, `sub_kind`, path, commit, run id, process id, artifact id, issue
  id, blocker id, and source time bounds.
- `filters.exact_refs` is the generic exact-reference filter shape. Each entry
  is an object `{"ref_kind": "<kind>", "ref_value": "<value>"}` whose
  `ref_kind` must come from the closed exact-reference vocabulary defined in
  RFC 0045 and projected by RFC 0046 (`item_id`, `logical_id`, `version_id`,
  `path`, `logical_path`, `rfc_id`, `decision_id`, `review_id`, `run_id`,
  `workflow_id`, `workflow_job_id`, `job_id`, `agent_process_id`,
  `artifact_id`, `issue_id`, `blocker_id`, `commit_sha`, `branch`, `tag`,
  `source_hash`, `bundle_id`). RFC 0045 and RFC 0046 remain the authoritative
  vocabulary owners; if those proposals close additional kinds before
  promotion, the accepted successor wins. Implementations must reject
  `exact_refs` entries whose `ref_kind` is outside the accepted vocabulary,
  rather than silently widening to a substring or vector fallback.
- The singular convenience fields such as `logical_ids`, `paths`, `run_ids`,
  `workflow_job_ids`, `job_ids`, `artifact_ids`, `rfc_ids`, `decision_ids`,
  and `commit_shas` are equivalent shorthands for `{ref_kind, ref_value}`
  entries with the matching kind. When a caller supplies both an `exact_refs`
  entry and an equivalent shorthand, the union is queried; no implicit
  precedence rule is defined here. Filters that cannot be expressed by the
  closed vocabulary (such as `sub_kinds`, `authority_classes`, and source
  time bounds) remain explicit fields on `filters`.
- Exact-reference filtering inherits the RFC 0045/RFC 0046 scoping rule that
  every lookup is bounded by the authorized `(tenant_id, corpus_id)` pair.
  Reference values are not globally authoritative and are never authorization
  grants on their own.
- `limits` must be bounded. A retrieval request may not ask for unbounded
  result sets or full corpus dumps.
- `timeout_ms` must be honored by the caller. Late responses are ignored.
- `citation_required=true` is the default for any result that may enter an
  operator packet, agent packet, review artifact, or handoff.

## Response Contract

Engram responses must distinguish successful retrieval from non-fatal memory
status. A caller may synthesize the same status shape when Engram cannot be
invoked at all.

```json
{
  "schema_version": "striatum.retrieval_response.v1",
  "request_id": "uuid-or-stable-local-id",
  "status": "ok",
  "tenant_id": "striatum",
  "corpus_id": "striatum",
  "generated_at": "2026-05-14T00:00:00Z",
  "engram": {
    "schema_version": "014_striatum_tenant_corpus.sql",
    "retrieval_profile_version": "striatum.retrieval.v1",
    "projection_generation_id": null
  },
  "corpus": {
    "bundle_ids": ["striatum.bundle:<stable-local-id>"],
    "bundle_sha256s": ["sha256:<hex>"],
    "source_time_min": "2026-05-01T00:00:00Z",
    "source_time_max": "2026-05-14T00:00:00Z",
    "staleness_seconds": 0
  },
  "results": [
    {
      "reference_id": "opaque-engram-reference",
      "item_id": "striatum.v2:repository:repo:rfc:0044@sha256:<hex>",
      "logical_id": "rfc:0044",
      "version_id": "sha256:<hex>",
      "tenant_id": "striatum",
      "corpus_id": "striatum",
      "source_kind": "striatum",
      "sub_kind": "rfc",
      "title": "RFC 0044: Engram Phase 1 Implementation Spec",
      "excerpt": "Bounded excerpt suitable for prompt injection.",
      "score": 0.91,
      "score_breakdown": {},
      "privacy_tier": 1,
      "dirty_working_tree": false,
      "classification": {
        "evidence_kind": "raw",
        "stability_class": "decision",
        "confidence": null,
        "authority_class": "canonical_doc"
      },
      "timestamps": {
        "observed_at": "2026-05-13T00:00:00Z",
        "recorded_at": "2026-05-13T00:00:00Z",
        "emitted_at": "2026-05-14T00:00:00Z"
      },
      "citation": {
        "path": "docs/rfcs/0044-engram-phase-1-implementation-spec.md",
        "logical_path": "docs/rfcs/0044-engram-phase-1-implementation-spec.md",
        "line_start": 1,
        "line_end": 40,
        "commit": "<commit-sha-or-null>",
        "blob_sha256": "sha256:<hex>",
        "content_sha256": "sha256:<hex>",
        "record_sha256": "sha256:<hex>",
        "bundle_id": "striatum.bundle:<stable-local-id>",
        "bundle_sha256": "sha256:<hex>",
        "run_id": null,
        "process_id": null,
        "artifact_id": null
      }
    }
  ],
  "warnings": [],
  "omitted": []
}
```

### Response Requirements

- `status` must be one of `ok`, `no_data`, `disabled`, `unavailable`,
  `unauthorized`, `timeout`, `stale`, `malformed`, or `error`.
- Corpus inventory metadata, including `corpus.bundle_ids`,
  `corpus.bundle_sha256s`, source time bounds, freshness windows,
  `staleness_seconds`, hidden labels, row counts, and hidden paths, may be
  populated only for authorized visible pairs and visible result sets. For
  `unauthorized`, `no_data`, and tenant/corpus pair-mismatch responses, those
  fields must be omitted or set to null.
- `tenant_id` and `corpus_id` must echo the authorized pair. Callers must
  discard results whose pair does not match the requested authorized pair.
- `no_data` must not distinguish absent, empty, filtered, above-tier,
  stale-rejected, not-found, or unauthorized-adjacent cases through corpus
  inventory metadata.
- Every result must include `reference_id`, `tenant_id`, `corpus_id`,
  `source_kind`, `sub_kind`, `privacy_tier`, score or ordering basis, and
  citation.
- Every result must surface a `dirty_working_tree` boolean that mirrors the
  underlying projection row's `source_dirty_working_tree` value (RFC 0046
  `docs/rfcs/0046-striatum-projection-index-schema.md` § Dirty working tree
  projection rules). The field must be present on every visible result row;
  it must not be omitted, defaulted to `false`, or inferred from absence.
  Dirty evidence must not be returned with `dirty_working_tree=false` and
  must not be presented as clean committed state. The field inherits the
  parent item's privacy tier and remains visibility-scoped: unauthorized,
  `no_data`, and pair-mismatch responses carry no result rows and therefore
  carry no `dirty_working_tree` flag.
- Every result that enters prompt or artifact context must include an RFC
  0045-compatible `item_id`, `logical_id`, `version_id`, and at least one
  retraceable provenance pointer.
- Generated summaries and derived memory products must cite their underlying
  raw item ids and carry confidence. Direct raw evidence may use
  `confidence=null` when no meaningful source confidence exists.
- `engram.fetch_reference` must re-authorize the stored row's tenant/corpus
  pair. Opaque `reference_id` values are not authorization.
- Pair-mismatched rows must be discarded before citation. Agent-visible
  diagnostics may name only the requested pair and a generic status; they must
  not reveal the mismatched pair or its inventory metadata.
- Results without citations are invalid for injection. They may be logged as
  malformed retrieval evidence, but they must not be presented as memory.
- Current repository state and explicit work packets outrank memory when they
  disagree. Retrieved memory may be stale.
- `omitted[]` carries one entry per candidate that the retrieval/augmentation
  path considered and did not return as a selected result. Each entry uses
  the canonical omission audit event shape defined in RFC 0048
  [Omission Audit Event Shape](0048-striatum-context-injection-policy.md#omission-audit-event-shape),
  with `selected=false`, a `reason` drawn from the closed RFC 0048 vocabulary,
  and lineage and ranking fields covering candidate `candidate_id`, retrieval
  lane, projection family, projection generation, rank, score, freshness
  label, privacy tier, and redaction state. `warnings[]` may surface
  operator-facing summaries derived from omitted entries but must not leak
  fields the caller is not authorized to read.
- `omitted[]` is privacy-safe local audit material. Entries for candidates
  whose underlying row is above the caller's allowed privacy tier,
  unauthorized, pair-mismatched, or hidden by redaction must use opaque
  request-local `candidate_id` values and must omit or null `reference_id`,
  `item_id`, `logical_id`, `version_id`, projection row ids, chunk ids,
  chunk hashes, bundle ids, paths, labels, and source-time bounds, per RFC
  0048. The `omitted[]` array is for local audit reconstruction; it must
  not be exported off-host, sent to hosted services, or used as
  authorization evidence.
- The closed RFC 0048 omission reason vocabulary may not be extended on the
  retrieval wire without an accepted RFC 0048 change; see RFC 0048's
  extension rule.
- Every projection `raw_payload` value inherits the parent item's
  `privacy.privacy_tier`, `privacy.redaction_state`, `privacy.withheld_fields`,
  and `visibility` (`visibility.default_visible_to` and
  `visibility.requires_capabilities`) as exported by RFC 0045 and projected
  by RFC 0046. Response fields derived from `raw_payload` are not part of
  the response unless the upstream RFC 0045/RFC 0046 contract explicitly
  whitelists them, and any retrieval-visible `raw_payload`-derived field
  that would exceed the caller's authorized privacy tier, redaction state,
  or visibility is forbidden. `unauthorized`, `no_data`, and tenant/corpus
  pair-mismatch responses must omit or null `raw_payload`-derived fields on
  the same terms as other inventory metadata, and `omitted[]` entries must
  not carry `raw_payload`-derived content above the reviewing tier. RFC
  0049 EG-060 carries the matching gate fixture.

## Failure Behavior

All failure modes below are non-fatal for Striatum workflow execution.

| Condition | Required behavior |
|-----------|-------------------|
| Retrieval disabled | Do not call Engram. Continue baseline flow. Show `disabled` only where memory status is normally shown. |
| Engram command missing | Continue baseline flow. Status `unavailable`; do not install, fetch, or phone home. |
| Engram unhealthy or DB unreachable | Continue baseline flow. Status `unavailable`; no workflow retry loop. |
| Corpus absent or empty | Continue baseline flow. Status `no_data` with the requested pair; omit corpus inventory metadata. |
| Unauthorized | Continue baseline flow. Status `unauthorized`; do not retry with broader capabilities and do not expose corpus inventory metadata. |
| Timeout | Continue baseline flow. Status `timeout`; ignore late responses. |
| Stale corpus or index | Continue with warning only if request allows stale memory; otherwise treat as `no_data` without leaking rejected staleness metadata. |
| Malformed response | Discard the response. Status `malformed`; do not inject partial uncited content. |
| Citation missing | Discard the affected result. If all results are uncited, status `malformed` or `no_data`. |
| Tenant/corpus mismatch | Discard the mismatched results and record `malformed` or `unauthorized` per Engram's error shape; do not reveal the mismatched pair or its inventory metadata. |
| Low score or weak confidence | Return `no_data` or a clearly labeled low-confidence memory lane; do not inflate certainty. |
| Engram internal error | Continue baseline flow. Status `error`; include no stack trace in agent prompts. |

Engram failure diagnostics should be concise and operator-facing. They must
not include hidden corpus names, personal-memory counts, bundle ids,
bundle hashes, source time bounds, freshness windows, staleness seconds,
labels, row ids, raw SQL errors, secret paths, stack traces, or sensitive
excerpts.

## Timeout And Retry Policy

Default budgets:

- health check: 500 ms;
- search: 2 seconds;
- fetch: 5 seconds;
- total automatic augmentation budget per packet: 10 seconds.

The caller may issue several searches inside the total budget, but it must not
block workflow progress once the budget is exhausted. Automatic retries default
to zero. A single retry is allowed only for local transient process startup
failures and must stay inside the same total budget.

Timeouts are not Striatum blockers. A timed-out retrieval request becomes a
memory status and the packet proceeds without augmentation.

## No-Egress And Local-Only Boundary

Any process that reads Engram corpus content must be local-only and no-egress:

- no external or non-loopback HTTP client on corpus-serving paths, and no
  remote egress of corpus content under any circumstance;
- loopback HTTP or local-runtime clients (for example a local model runtime,
  local embedding server, Ollama, ik-llama, or another local helper service)
  are permitted only when the receiving endpoint is named, binds to
  `127.0.0.1`, `::1`, or a local Unix socket, receives corpus content only
  inside the local no-egress boundary, and has paired no-egress evidence for
  the receiving runtime or shares the caller's sandbox boundary, as required
  by RFC 0049 EG-020;
- no DNS lookup requirement for corpus-serving paths;
- no hosted model call;
- no cloud embedding or reranking API;
- no telemetry, crash reporting, analytics, or usage beacon;
- no hosted persistence or remote cache;
- no web search from Engram;
- no network-accessible Engram MCP server.

The loopback/local-runtime exception is strictly local-runtime: Engram is
no-cloud and no-egress, so loopback-to-local-runtime is allowed but no remote
egress of corpus content, embedding input, prompts, or audit data is ever
permitted. Any local runtime that receives corpus text inherits the
corpus-reading scope and must itself have paired no-egress evidence under
RFC 0049 EG-020.

MCP stdio is the default boundary. A future loopback HTTP API may be reviewed
only if it preserves the no-egress corpus-reading property, binds locally, and
does not become a hosted service. OS-level no-egress enforcement remains a
separate evidence gate; this RFC must not overclaim that enforcement until
RFC 0049 records a sandbox probe.

If a task needs fresh external data, Engram may emit an explicit gap or
"unknown" signal. A separate network-using process may perform the lookup
without direct Engram corpus access.

## Tenant And Corpus Isolation

Default Striatum retrieval uses:

```text
tenant_id = striatum
corpus_id = striatum
source_kind = striatum
```

RFC 0045 allows future per-instance corpora such as:

```text
tenant_id = striatum
corpus_id = striatum:<instance-or-repository-id>
```

Rules:

- `source_kind='striatum'` is the ingest/parser discriminator.
- `tenant_id='striatum'` is the local application-memory boundary.
- `corpus_id` is the workload or instance boundary inside the Striatum tenant.
- Bundle identity, instance identity, repository identity, labels, paths, and
  discovery fields are not authorization grants.
- RFC 0045 `identity.instance_label`, `identity.repository_label`, and
  `identity.repository_root_hint` are display-only, privacy-inherited
  metadata. They are not discovery keys, join keys, collision boundaries, or
  authorization inputs.
- Instance and repository labels may be shown only to callers authorized for
  the described corpus and privacy tier. Unauthorized, not-visible, `no_data`,
  pair-mismatch, health, and describe diagnostics must omit or redact them.
- Default Striatum operator access carries only `memory.read_striatum` for the
  configured primary pair plus `memory.describe`.
- Personal memory requires `memory.read_personal`.
- Secondary Striatum corpora require explicit visibility and
  `memory.read_cross_corpus` when a request crosses the primary pair.
- Any non-Striatum tenant requires `memory.read_cross_tenant` and an explicit
  tenant name.
- `engram.describe_corpus` and `engram.health` must not reveal hidden personal
  corpus names, counts, or freshness metadata to a default Striatum token.
- `engram.fetch_reference` must recheck the stored row's tenant/corpus pair
  and must collapse unauthorized/not-found distinctions at the external MCP
  boundary once the RFC 0044 hardening follow-up lands.

## Citation And Provenance Requirements

Retrieved memory is usable only when it is citeable.

Every injected result must carry:

- `tenant_id`, `corpus_id`, and `source_kind`;
- `sub_kind`, `item_id`, `logical_id`, and `version_id` from RFC 0045 or the
  compatibility adapter;
- source path or logical path when available;
- line range when the source is text and line mapping exists;
- commit, blob hash, content hash, record hash, bundle id, run id, process id,
  artifact id, issue id, blocker id, or bundle integrity hash where available;
- `privacy_tier`, redaction state where exposed, confidence, stability class,
  and authority class;
- `dirty_working_tree` boolean for the result row, so renderings can mark
  dirty working-tree evidence distinctly from evidence tied only to committed
  Git objects.

Prompt and artifact renderings must label memory separately from current
instructions. A recommended rendering shape is:

```text
Memory result: <short claim or excerpt>
Citation: tenant=striatum corpus=striatum sub_kind=rfc logical_id=rfc:0044
path=docs/rfcs/0044-engram-phase-1-implementation-spec.md lines=1-40
commit=<sha-or-null> bundle_id=striatum.bundle:<stable-local-id>
bundle_sha256=sha256:<hex> dirty_working_tree=<true|false>
```

When `dirty_working_tree=true`, the rendering must keep that marker adjacent
to the citation. Renderings must not drop the marker, present a dirty result
without it, or imply the citation refers to a clean committed state when the
result row carries dirty working-tree provenance.

Retrieved memory must not be rewritten into an uncited assertion. If the
operator or an agent acts on memory, the artifact should preserve the citation
next to the claim or explicitly state that no memory was available.

Citations and result fields must not draw content from a projection
`raw_payload` value above the caller's authorized privacy tier, redaction
state, or visibility. `raw_payload` inherits the parent item's
`privacy.privacy_tier`, `privacy.redaction_state`, `privacy.withheld_fields`,
and `visibility` as exported by RFC 0045 and projected by RFC 0046; see the
Response Contract clause above and RFC 0049 EG-060 for the matching gate
fixture.

## Freshness And Truthfulness

Engram's Striatum memory is a snapshot of exported and ingested evidence. It
may lag current repository state.

Rules:

- Current files, work packets, and operator instructions outrank memory.
- Responses must expose source time bounds or staleness when known.
- Source time bounds and staleness are visibility-scoped metadata for the
  authorized result set, not proof of full-corpus coverage or hidden corpus
  inventory.
- Stale memory can be shown only with a stale label unless the caller rejects
  stale results.
- If the caller rejects stale results, the response must use `no_data` or the
  agreed non-fatal status without leaking rejected `staleness_seconds`,
  source time bounds, bundle identities, labels, or row counts.
- `no_data` is a real result. It means Engram has no usable local evidence for
  the request under the requested tenant/corpus/capability boundary.
- Low-confidence or generated-summary results must keep confidence visible.
- A retrieved result must not imply full coverage of Striatum history unless
  the corpus contract and freshness metadata support that claim.
- Dirty working-tree evidence is a distinct freshness concern from staleness.
  Result rows projected from RFC 0046 dirty rows must surface
  `dirty_working_tree=true`, and the rendering must keep that marker adjacent
  to the citation. Dirty evidence is never reclassified as clean committed
  state, and a clean-looking citation may not accompany a dirty-tree excerpt.

## Cache, Rebuild, And Invalidation Rules

Engram may maintain local retrieval indexes, projections, and response caches
as derived data. They are rebuildable from RFC 0045 raw evidence plus accepted
projection contracts. They are not canonical evidence.

Striatum may keep a per-run copy of injected augmentation only as provenance
for what was shown to an agent or operator. That copy must not become a future
readiness condition, dependency edge, or replacement for querying current
repository state.

Retrieval cache keys must include at least:

- request schema version;
- retrieval profile version;
- tenant/corpus pair;
- visible-pair and capability fingerprint;
- query text and filters;
- limits affecting result selection;
- opaque corpus bundle ids or projection generation ids;
- bundle integrity hashes such as `bundle_sha256`, when they affect result
  selection or invalidation;
- redaction profile or privacy visibility version.

Bundle ids are opaque RFC 0045 identities. Cache keys and diagnostics must not
use `sha256:<hex>` values as bundle identity; hashes belong in explicit
integrity fields such as `bundle_sha256`.

Invalidate or bypass retrieval caches when:

- a new bundle is ingested;
- projection generation changes;
- redaction profile changes;
- privacy tier or visible-pair policy changes;
- capability scope changes;
- index health is stale or unknown;
- RFC 0045 compatibility adapter version changes.

Rebuilds must preserve raw evidence immutability. A changed item is represented
by a new RFC 0045 `item_id` and stable `logical_id`, not mutation of old raw
evidence. Reference IDs may be opaque and implementation-specific, but
responses must carry stable RFC 0045 identities so citations survive index
rebuilds.

## Operator UX Boundaries

Before RFC 0048 accepts injection policy, operator UX should stay conservative:

- memory is opt-in by configuration or explicit command;
- every automatic augmentation has a visible status;
- an operator can disable retrieval per run, per packet, or per session;
- unavailable memory is not noisy unless it would explain missing context;
- unauthorized memory does not invite broader access inside agent prompts;
- memory sections are labeled as memory, not instructions;
- citations stay attached to memory excerpts;
- result counts and excerpts are bounded;
- explicit `no_data` is preferred over silent uncertainty when the operator
  asked for memory;
- current repository state and packet instructions are visually and
  semantically separate from memory;
- manual search may surface richer diagnostics than automatic packet
  augmentation, but still obeys tenant/corpus and no-egress rules.

Recommended packet section label:

```text
Retrieved Local Memory (optional, cited, may be stale)
```

Recommended status labels:

```text
memory: available
memory: disabled
memory: unavailable
memory: unauthorized
memory: timeout
memory: stale
memory: no_data
```

## Compatibility With Striatum Without Engram

Striatum remains compatible with no Engram installation:

- package installation must not depend on Engram;
- normal Striatum tests and CI must not require Engram;
- Striatum workflows must create the same required artifacts with Engram
  missing from `PATH`;
- daemon RPC capability registries must not include `memory.*`;
- no Striatum runtime module may import an Engram client library;
- optional Engram fixtures must be gated by explicit local opt-in such as
  `ENGRAM_TEST=1`;
- operator docs may describe how to configure Engram, but configuration is not
  automatic hidden state;
- Engram health may be displayed, but it is not a precondition for workflow
  execution.

The acceptable fallback is the current behavior: read repository docs,
canonical RFCs, decision logs, review artifacts, work packets, and explicit
operator context directly.

## Security And Privacy Boundaries

Default Striatum augmentation must not expose personal memory.

Privacy requirements:

- preserve RFC 0045 privacy tiers, redaction state, and visibility metadata;
- never use bundle labels, repository labels, or paths as access grants;
- treat bundle ids, bundle hashes, source time bounds, freshness and staleness
  values, repository and instance labels, counts, row ids, and root hints as
  corpus inventory metadata subject to the same authorization and redaction
  rules as retrieved content;
- reject or omit results above the caller's allowed privacy tier;
- avoid leaking hidden corpus names through status, health, or describe tools;
- avoid leaking repository or instance labels through unauthorized, not-visible,
  `no_data`, pair-mismatch, health, describe, citation, or audit diagnostics;
- do not place raw SQL errors, file-system secrets, stack traces, or private
  absolute parent paths into agent-visible diagnostics;
- treat tool output and retrieved text as untrusted content, not instructions;
- keep capability vocabularies Engram-local and separate from Striatum daemon
  capabilities.

Any relaxation of local-first, no-egress, or default personal-memory isolation
requires explicit human approval and a new accepted decision.

## Review Requirements

Use the multi-agent review loop before promotion. The review packet should
include this RFC and the handoff artifact under
`docs/reviews/rfc0047-striatum-retrieval-augmentation-boundary/`.

Required review lanes:

- Striatum runtime independence review;
- Engram capability and tenant/corpus boundary review;
- no-egress and local-only review;
- operator UX and truthfulness review;
- recovery-path and failure-mode review;
- RFC 0045 dependency coherence review;
- implementation-readiness review for both repositories.

Reviewers should test the RFC against the RFC 0044 findings ledger, especially
single-pair authorization, `fetch_reference` reauthorization, `describe`
metadata leakage, malformed references, and no-egress evidence scope.

## Acceptance Criteria

- Striatum can prepare, start, run, review, recover, and produce required
  artifacts without Engram installed, configured, healthy, or reachable.
- Engram retrieval is optional, local, read-only, no-egress, and
  non-authoritative.
- Memory availability is explicitly not authoritative Striatum state.
- Query contract names purpose, tenant/corpus pair, filters, bounds,
  freshness, timeout, and citation requirements.
- Response contract names status, source identity, freshness, citations,
  confidence/stability/authority metadata, and warnings.
- Failure modes are visible but non-fatal.
- Default timeouts are bounded and cannot block workflow progress.
- Capability defaults cannot expose personal memory to Striatum.
- Cross-corpus and cross-tenant reads require explicit Engram-local grants.
- Unauthorized, `no_data`, and tenant/corpus pair-mismatch responses omit or
  null corpus inventory metadata, including bundle ids, bundle hashes, source
  time bounds, staleness, labels, counts, row ids, and hidden paths.
- Repository and instance labels are display-only, privacy-inherited metadata,
  not authorization, discovery, join, or collision keys.
- RFC 0045 bundle identity examples use opaque `bundle_id` values, with
  `bundle_sha256` represented separately as an integrity hash.
- `engram.fetch_reference` re-authorizes the stored row and does not trust
  opaque references as authorization.
- Retrieved memory is cited and distinguishable from current repo state.
- Results without citations are invalid for injection.
- Cache and rebuild rules keep Engram-derived retrieval state rebuildable from
  raw RFC 0045 evidence.
- Operator UX includes clear status and an explicit disable path.
- Cross-repo tests or review artifacts prove no runtime import/dependency
  regression.

## Deferred Questions

1. Exact per-instance `corpus_id` grammar and operator-visible label vocabulary
   belong to RFC 0045 acceptance or a follow-up decision. Label privacy
   inheritance and unauthorized metadata redaction are fixed requirements of
   this RFC, not deferred.
2. Exact projection generation identifiers depend on RFC 0046.
3. Exact context-injection budgets, section order, and prompt formatting belong
   to RFC 0048.
4. Exact no-egress sandbox probe, latency gate, fixture bundle, and golden
   retrieval query set belong to RFC 0049.
5. Whether a one-shot CLI wrapper is worth implementing in addition to MCP
   stdio should be decided during implementation planning.
6. Whether stale memory should be shown automatically or only on explicit
   operator request should be resolved with RFC 0048 ergonomics review.
7. Whether generated memory products from the roadmap can be queried by this
   contract before they have separate audit gates remains deferred.
