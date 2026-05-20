<a id="rfc-0049"></a>

# RFC 0049: Striatum Evaluation, No-Egress, And Retrieval-Quality Gates

| Field | Value |
|-------|-------|
| RFC | RFC-0049 |
| Title | Striatum Evaluation, No-Egress, And Retrieval-Quality Gates |
| Status | accepted_as_design_reference |
| Implementation | landed in part via `make eval-gates`; full gate matrix remains incremental |
| Created | 2026-05-14 |
| Source | `STRIATUM_MEMORY_ROADMAP.md` |
| Context | RFC 0044, RFC 0045, RFC 0046, RFC 0047, RFC 0048 |
| Review state | reviewable evaluation-gates handoff |

## Summary

This RFC is accepted as the design reference for the evidence gates required
before Engram-backed Striatum
memory can become routine operator infrastructure. The gates cover deterministic
fixture bundles, V2 validation, tenant/corpus isolation, personal-memory
negative tests, no-egress evidence, stale-index behavior, reference
authorization, malformed and uncited result handling, redaction, latency,
retrieval quality, prompt-injection containment, audit reconstruction, disable
controls, and Striatum compatibility when Engram is absent.

This began as an evaluation and promotion contract. D083 later accepted RFC
0046-RFC 0049 as design reference for the landed Striatum-memory e2e pipeline.
The full gate matrix remains incremental; implemented gates are described in
the RFC index and backlog.

The central promotion rule is:

```text
Manual/local operator search may ship earlier when it is explicit, local,
read-only, cited, scope-limited, and non-injecting.

Routine default-on automatic memory injection is blocked until the full
automatic gate set in this RFC passes and accepted/promoted successors exist
for RFC 0045, RFC 0046, RFC 0047, and RFC 0048.
```

## Roadmap Position

RFC 0049 is Phase 7 of the Striatum memory roadmap. It follows:

- RFC 0044, which accepted Engram-side Phase 1 Striatum raw retrieval with
  hardening findings;
- RFC 0045, which proposes the Striatum Corpus Contract V2 disk bundle;
- RFC 0046, which is accepted as design reference for landed rebuildable
  Striatum projections and indexes;
- RFC 0047, which is accepted as design reference for landed retrieval as
  optional local augmentation;
- RFC 0048, which is accepted as design reference for landed context-injection
  policy and budgets.

RFC 0049 is not a shortcut around those dependencies. If RFC 0045, RFC 0046,
RFC 0047, or RFC 0048 changes before acceptance, the gates here must be revised
where their fields, statuses, projection health checks, or packet policies no
longer match.

RFC 0045 remains proposal-only. RFC 0046-RFC 0048 are accepted as design
reference per D083, so gates depending on their landed projection, retrieval,
and packet contracts are no longer blocked solely by upstream status.

## Goals

1. Define fixture bundles and validator checks for Striatum Corpus Contract V2.
2. Define no-egress evidence for validator, ingest, projection, embedding,
   retrieval, MCP, and context-assembly paths that read Engram corpus data.
3. Define tenant/corpus isolation gates through actual service, MCP, and CLI
   paths.
4. Define personal-memory negative tests for Striatum default access.
5. Define `fetch_reference` reauthorization and MCP/reference error hardening
   gates.
6. Define stale-index, invalidated-active-row, redaction, and privacy
   reclassification behavior.
7. Define malformed, uncited, pair-mismatched, redacted, stale, and
   low-confidence result fixtures.
8. Define retrieval-quality golden queries with expected and forbidden
   references.
9. Define prompt-injection containment gates for retrieved memory text.
10. Define latency budgets and non-blocking fallback behavior.
11. Define audit-trail reconstruction gates for automatic packet augmentation.
12. Define disable-control gates for run, session, packet, purpose, and manual
    modes.
13. Define promotion criteria for manual search, experimental automatic
    injection, and routine default-on automatic injection.

## Non-Goals

- No corpus contract design beyond naming RFC 0045 dependencies.
- No projection or index schema design beyond naming RFC 0046 dependencies.
- No retrieval API or packet policy design beyond naming RFC 0047/RFC 0048
  dependencies.
- No exporter, ingester, migration, generated schema-doc, test, or code
  implementation.
- No quality evaluation of personal-memory content. Personal memory appears
  here only as negative authorization and non-injection coverage.
- No hosted benchmark service, hosted search, hosted embedding, hosted
  reranking, telemetry, cloud API, remote persistence, or network-accessible
  Engram service.
- No live LLM reranking in the serving path.
- No decision to make Engram authoritative Striatum state.

## Dependencies And Open Upstream Decisions

RFC 0049 depends on proposal surfaces that are not yet accepted. Reviewers must
keep those dependencies visible.

### RFC 0044 Hardening Dependencies

RFC 0044 Phase 1 is accepted with findings. The gates here assume the accepted
repair state for primary-pair semantics and add evidence requirements for the
remaining hardening queue:

- `memory.read_cross_corpus` is required for visible non-primary corpora inside
  the same tenant;
- `memory.read_cross_tenant` is required for visible non-primary tenants;
- the default Striatum operator token cannot read personal memory;
- `engram.fetch_reference` reauthorizes the stored row and does not trust opaque
  reference ids as grants;
- unauthorized and not-found failures collapse at the MCP boundary;
- decoded reference UUIDs are validated before database lookup;
- MCP frame parsing has content-length caps and JSON-RPC parse-error behavior;
- `describe-corpus` preserves the two-key tenant/corpus model, with shorthand
  only for the sanctioned `striatum -> striatum/striatum` case;
- unknown `memory.*` capability strings are rejected or warned on;
- `tenant_id='striatum'` rows are structurally tied to `source_kind='striatum'`
  where Striatum evidence is being served;
- real or committed fixture bundle smoke evidence exists;
- no-egress evidence is scoped honestly until an OS-level sandbox probe exists;
- Striatum-side reciprocal evidence proves no Engram runtime dependency.

### RFC 0045 Dependencies

RFC 0049 expects V2 fixture bundles to expose stable fields from RFC 0045:

- `manifest.json`, JSONL item streams, row counts, byte counts, and hashes;
- `tenant_id`, `corpus_id`, `source_kind`, and `sub_kind`;
- `item_id`, `logical_id`, `version_id`, `content_sha256`, and `record_sha256`;
- `observed_at`, `recorded_at`, and `emitted_at`;
- provenance pointers such as path, logical path, line range, commit, run id,
  process id, artifact id, issue id, or blocker id;
- privacy tier, redaction state, visibility, stability class, authority class,
  and confidence;
- links among RFCs, reviews, syntheses, runs, agents, artifacts, commits,
  issues, blockers, and handoffs.

Open RFC 0045 decisions that can change this RFC:

1. exact per-instance `corpus_id` grammar;
2. source of `instance_id` and `repository_id`;
3. zero-row required files versus manifest-declared omissions;
4. full diff and stdout/stderr export depth;
5. exact privacy-tier assignment policy Striatum can guarantee before export;
6. one-file-per-kind versus sharded layout;
7. V1 compatibility adapter ownership;
8. fixture bundle selection.

### RFC 0046 Dependencies

RFC 0049 expects RFC 0046 or its accepted successor to provide:

- projection generation ids and active/superseded state;
- `source_capture_id`, `source_item_id`, `source_logical_id`,
  `source_version_id`, hashes, and generation metadata;
- exact-reference lane that mirrors RFC 0045's closed `ref_kind` vocabulary,
  including `workflow_job_id` and `job_id`, plus structured, lexical, and
  optional local pgvector lanes;
- `authority_class`, `stability_class`, `confidence`, `privacy_tier`,
  `redaction_state`, chunk ids, and chunk boundaries;
- health checks for latest validated bundle, active generation, invalidated
  active rows, chunk counts, embedding counts, and V1 raw-only bundles.

Open RFC 0046 decisions that can change this RFC:

1. generic versus Striatum-specific projection generation table;
2. composite FK versus trigger/service guards for tenant/corpus raw evidence;
3. PostgreSQL lexical index strategy;
4. exact-reference vocabulary parity with RFC 0045's closed `ref_kind` set;
5. per-corpus pgvector partial index feasibility;
6. git identity and local-path privacy handling;
7. projection audit table shape;
8. semantic or inferred link ownership.

### RFC 0047 And RFC 0048 Dependencies

RFC 0049 consumes RFC 0047 statuses and timeouts:

```text
ok
no_data
disabled
unavailable
unauthorized
timeout
stale
malformed
error
```

RFC 0049 also consumes RFC 0048's policy that retrieved memory is evidence only,
never instructions, never an authorization grant, and never authoritative
Striatum state.

Open RFC 0047/RFC 0048 decisions that can change this RFC:

1. exact context-injection packet format and sidecar format;
2. exact disable-control CLI/UI names;
3. whether stale memory is automatically included for any purpose;
4. which downstream generated-product implementation spec from RFC 0051 must be
   accepted before generated memory products can be injected;
5. whether automatic injection becomes default-on for all five non-search
   purposes or only a subset after gate evidence.

## Promotion Levels

This RFC separates manual search from automatic injection.

### Level 0: Review And Developer Smoke

At Level 0, RFC 0049 is only a proposal. Implementers may build local fixtures,
test harnesses, and smoke commands, but Striatum memory is not a supported
operator workflow.

### Level 1: Manual/Local Operator Search

Manual search may be promoted before full automatic injection only when all of
these are true:

- the operator explicitly invokes search or fetch;
- the path is local-only, read-only, no hosted service, no telemetry, and no
  hidden persistence;
- no result is inserted into agent context unless the operator or packet builder
  explicitly selects or summarizes it into a cited memory section;
- default scope is `tenant_id='striatum'`, `corpus_id='striatum'`, and
  `source_kind='striatum'`;
- tenant/corpus authorization, personal-memory denial, `fetch_reference`
  reauthorization, and citation checks pass through the actual service/MCP path;
- the exact process used for manual search has at least code/dependency
  no-egress evidence and is labeled experimental until OS-level no-egress
  evidence exists;
- failures are visible and non-fatal.

Level 1 may use RFC 0044 raw retrieval while RFC 0045/RFC 0046 remain
unaccepted, but it must label that path as raw-only and must not claim V2
projection freshness, V2 retrieval quality, or automatic-injection readiness.

### Level 2: Experimental Automatic Injection

Experimental automatic injection may be opt-in only. It requires all Level 1
gates plus:

- deterministic V2 or reviewed-compatibility fixtures;
- prompt-injection containment;
- packet audit reconstruction;
- run/session/packet/purpose disable controls;
- latency timeouts and non-blocking fallback;
- stale-index and redaction gates for every retrieval-visible derived row used
  by the injection path.

The operator must opt in per run, session, or packet. Failure remains non-fatal.
Every Level 2 report must record the gate outcome and failure action for each
gate in the matrix below. Level 2 never authorizes default-on behavior; it only
authorizes the named opt-in automatic surface that the evidence packet covers.

### Level 3: Routine Default-On Automatic Injection

Routine default-on automatic injection is blocked until every automatic-required
gate in this RFC passes and RFC 0045, RFC 0046, RFC 0047, and RFC 0048, or
their accepted successors, are promoted. If any dependent upstream contract is
still proposal-only, dependent gates report `blocked_upstream` and Level 3
remains unavailable even when local test fixtures otherwise pass.

The only default-on purposes eligible after gate acceptance are:

```text
operator_startup
workflow_scaffold
packet_prepare
review_prepare
blocker_recovery
```

`ui_search` and `manual_search` remain manual-only. Personal memory remains
out of default Striatum injection.

## Gate Matrix

Gate outcomes use this vocabulary:

```text
pass
fail
blocked_upstream
not_run
accepted_with_scope_limit
```

`fail` means the gate observed unsafe behavior or missing evidence for the
covered surface. It blocks every promotion level where the matrix says the gate
is required.

`blocked_upstream` means the gate cannot honestly pass because it depends on an
unaccepted upstream contract, unresolved RFC 0044 hardening evidence, or a
missing accepted successor. It blocks dependent promotion levels until the
upstream contract is accepted/promoted and the gate is rerun.

`accepted_with_scope_limit` is allowed only when the report states exactly which
surface is covered and which promotion level is still blocked.

| Gate | Purpose | Blocks Level 1 Manual Search | Blocks Level 2 Experimental Automatic Injection | Blocks Level 3 Default-On Injection | Failure Action |
|------|---------|-------------------------------|---------------------------------------------------|--------------------------------------|----------------|
| EG-000 RFC 0044 hardening baseline | Preserve accepted Phase 1 safety and reciprocal Striatum independence. | yes for service/MCP safety items | yes | yes | `fail` blocks affected service/MCP paths; `blocked_upstream` while RFC 0044 hardening evidence is unresolved; `accepted_with_scope_limit` may cover raw-only helper smoke only. |
| EG-010 V2 fixture and validator | Provide deterministic inputs and fail-closed validation. | no for RFC 0044 raw-only manual search; yes for V2 manual claims | yes unless using a reviewed compatibility fixture | yes | `fail` is fail-closed; `blocked_upstream` until RFC 0045 or accepted successor is promoted; `accepted_with_scope_limit` may cover raw-only or reviewed compatibility input only. |
| EG-020 no-egress | Prove corpus-reading paths and transitive local runtimes cannot call out. | yes, scoped to the manual path | yes | yes, OS-level evidence required | `fail` blocks the covered corpus-reading path, including any external, non-loopback, or unpaired HTTP/network dependency; `not_run` applies when sandbox evidence has not been attempted; `blocked_upstream` applies only when an unaccepted upstream contract prevents knowing which local runtimes must be covered; `accepted_with_scope_limit` may cover Level 1 code/dependency inspection only. |
| EG-030 tenant/corpus/personal isolation | Prevent cross-boundary reads and metadata leaks. | yes | yes | yes | `fail` blocks all levels for the affected surface; `blocked_upstream` if token/pair semantics depend on an unaccepted upstream contract; scope limits must name the exact authorized pair and surface. |
| EG-040 reference and MCP hardening | Reauthorize fetches and collapse probing surfaces. | yes for fetch-backed manual search | yes | yes | `fail` blocks fetch-backed use; `blocked_upstream` if reference format is not accepted; scope limits may cover search-only surfaces that do not fetch references. |
| EG-050 stale-index and freshness | Detect stale projections, invalidated rows, and current-authority conflicts. | no for raw-only manual search; yes for projection-backed search | yes for projection-backed injection | yes | `fail` blocks projection-backed paths; `blocked_upstream` until RFC 0046/RFC 0047 freshness contracts are accepted; scope limits may cover raw-only manual search. |
| EG-060 privacy/redaction | Prevent stale lower-tier, withheld-content, identity, or citation leakage. | yes when redacted rows can be returned | yes | yes | `fail` blocks covered paths; `blocked_upstream` if privacy/redaction vocabulary is not accepted; scope limits must exclude affected tiers, labels, paths, or redaction states. |
| EG-070 retrieval quality | Prove useful, cited recall through a manifest-backed query set. | minimal cited exact/search coverage required | yes for enabled opt-in purposes | yes, full golden-query manifest required | `fail` blocks the covered quality claim; `blocked_upstream` until RFC 0045 sub-kinds, RFC 0046 lanes, and RFC 0047 statuses are accepted; scope limits must name query families, lanes, and purposes covered. |
| EG-080 malformed/uncited result handling | Discard unusable, mismatched, or leak-shaped results. | yes | yes | yes | `fail` blocks injection and affected manual packet insertion; `blocked_upstream` if result status/error shape is not accepted; scope limits must name excluded malformed families. |
| EG-090 prompt-injection containment | Treat memory text as untrusted evidence. | yes only when manual results enter a packet | yes | yes | `fail` blocks any packet insertion; `blocked_upstream` if RFC 0048 packet policy is not accepted; scope limits may cover manual search that displays results outside packets. |
| EG-100 latency and non-blocking behavior | Bound operator and packet delay, including cold-start behavior. | yes for supported manual UX | yes | yes | `fail` blocks supported UX claims and automatic injection for slow surfaces; `accepted_with_scope_limit` may permit explicit slow manual search; `blocked_upstream` if timeout/status semantics are unaccepted. |
| EG-110 audit reconstruction | Reconstruct what memory was shown or omitted without leaking hidden state. | no unless manual insertion produces packet sections | yes | yes | `fail` leaves the purpose ineligible; `blocked_upstream` until packet/audit fields are accepted; scope limits must name the exact reconstructed purposes and redacted fields. |
| EG-120 disable controls | Allow memory to be disabled visibly. | manual mode must remain possible | yes | yes | `fail` blocks automatic injection; `accepted_with_scope_limit` may permit manual-only operation; `blocked_upstream` if disable-control names are unaccepted. |
| EG-130 Striatum without Engram | Prove augmentation is not dependency. | yes | yes | yes | `fail` blocks supported memory claims that make Engram required; scope limits must keep Striatum baseline workflows independent. |
| EG-140 generated memory product privacy/audit placeholder | Prevent derived memory products from entering injection before privacy inheritance and audit gates exist. | no for retrieval of cited source evidence | yes for any generated-product injection | yes | Generated products remain retrieval-invisible and injection-ineligible until a downstream generated-product implementation spec from RFC 0051 is accepted per D089, covering privacy inheritance, provenance/citation, audit, rebuildability, and eval gates; `accepted_with_scope_limit` means generated products are omitted. |

## EG-000: RFC 0044 Hardening Baseline

The baseline gate verifies that RFC 0044's accepted Phase 1 boundary remains
true before broader Striatum memory work builds on it.

Pass criteria:

- `MemoryService.search()` enforces primary-pair semantics.
- `MemoryService.fetch_reference()` enforces primary-pair semantics and
  reauthorizes the stored row.
- At least one MCP `tools/call` path exercises the CLI-style `--allow-pair`
  token shape and proves visible pairs are not read grants.
- `engram.describe_corpus` shorthand is restricted to the sanctioned
  `striatum` convenience or requires explicit `--tenant`.
- `engram-mcp-stdio --capability` rejects or warns on unknown `memory.*`
  capability names.
- `engram.health` reports schema version by numeric migration prefix or applied
  ordering, not fragile lexicographic maximum.
- A committed or non-private fixture Striatum export smoke proves the ingest and
  read-only retrieval path against non-synthetic bundle shape.
- A Striatum-side artifact proves no Engram client import, no Engram daemon RPC
  dependency, and graceful fallback when Engram is unavailable.

## EG-010: V2 Fixture Bundle And Validator Gate

The V2 gate provides deterministic local inputs for every downstream test.

Required fixture bundles:

1. Minimal V2 bundle with every required stream represented, including zero-row
   streams if RFC 0045 keeps that rule.
2. Multi-corpus isolation bundle with `corpus_id='striatum'` and a second
   `corpus_id='striatum:<fixture>'`.
3. Linked document bundle with RFC, review, synthesis, handoff, changelog, and
   decision rows.
4. Run bundle with run, workflow job, agent process, artifact, stdout/stderr
   summary, issue, and blocker links.
5. Git/path bundle with commit SHA, path references, branch or tag references,
   and bounded diff summaries.
6. Redaction bundle with `redaction_state='withheld'` items represented only by
   deterministic withheld/redaction notices, plus separate allowed `redacted`
   or `synthetic_summary` rows where RFC 0045 permits them.
7. Tombstone or incremental bundle that invalidates a prior logical item.
8. Negative V1 raw-only bundle proving V1 input does not become projection-ready
   without a reviewed adapter.
9. Negative tenant/corpus/source-kind mismatch bundle.
10. Personal-memory sentinel fixture outside the Striatum tenant for default
    denial tests.
11. Malformed result fixture with missing citations, bad reference ids,
    pair-mismatched rows, stale rows, low-confidence rows, and redacted rows.
12. Prompt-injection fixture containing instruction-shaped historical text.
13. Local mocked or precomputed embedding fixture. No hosted embedding call is
    allowed.

Validator pass criteria:

- fails closed on missing manifest, invalid JSON, non-object JSONL rows,
  non-UTF-8 files, unknown major schema version, malformed timestamps, and
  malformed `sha256:<hex>` fields;
- verifies bundle hash, file hash, byte count, row count, content hash, record
  hash, and duplicate `item_id` rules;
- rejects rows whose `source_kind`, `sub_kind`, `tenant_id`, or `corpus_id`
  conflicts with the manifest or accepted adapter;
- rejects missing required fields, missing provenance, missing privacy tier,
  missing redaction metadata, and missing visibility metadata;
- rejects or explicitly scopes absolute-path leakage in display-hint fields;
- runs without network access, live model calls, Striatum daemon RPC, Engram MCP,
  hosted services, telemetry, or remote persistence;
- writes validation evidence with fixture path, manifest hash, row counts, and
  validator version.

## EG-020: No-Egress Gate

No corpus-reading process may have outbound network egress. The gate covers:

- V2 validator;
- Striatum bundle ingest;
- projection worker;
- deterministic chunker;
- local embedding path;
- retrieval service;
- MCP stdio server;
- context-assembly path when it reads Engram results or references;
- any future local reviewer or evaluator that reads Engram corpus content.

For this gate, corpus-reading scope is transitive. Any process, subprocess, or
loopback service that receives raw corpus text, chunks, excerpts, embedding
input text, generated corpus-derived text, or corpus-bearing prompts is also a
corpus-reading process. This includes local model runtimes, local embedding
servers, Ollama, ik-llama, reviewer/evaluator runtimes, and any helper service
called over loopback. The caller process cannot satisfy this gate on behalf of
the runtime that actually receives corpus text.

External or non-loopback HTTP clients are not permitted on corpus-reading
paths. Loopback HTTP or local-runtime clients are permitted only when the
receiving endpoint is named, the endpoint receives corpus content only inside
the local no-egress boundary, and the receiving runtime has paired no-egress
evidence or is proven to share the caller's sandbox boundary.

Pass criteria:

- static dependency/import inspection finds no external or non-loopback HTTP
  client, no unpaired loopback HTTP client, no web-search client, hosted SDK,
  telemetry, crash-reporting client, remote vector store, remote cache, cloud
  DLP/classification service, hosted reranker, or other hosted-network
  dependency on the corpus-reading path;
- any loopback HTTP client, model client, embedding client, or local service
  dependency that receives corpus text is paired with no-egress evidence for
  the receiving runtime;
- runtime sandbox probe runs each corpus-reading command with outbound network
  denied and records successful completion or expected local-only failure;
- runtime sandbox probe covers both the caller and every transitive local
  runtime that receives corpus content, or proves they run inside the same
  no-egress boundary;
- sandbox allows only required local resources. Loopback access to local
  Postgres, Ollama, or local model runtimes must be explicitly named when used;
- the Engram PostgreSQL instance that hosts raw evidence, projections, and
  packet audit evidence is proven to bind only to `127.0.0.1`, `::1`, or a
  local Unix socket, and the probe verifies the corpus-reading command cannot
  reach a non-loopback PostgreSQL address;
- DNS resolution and non-loopback socket attempts fail inside the probe;
- MCP remains stdio or loopback-only if a future reviewed HTTP API exists;
- no test uses a hosted model or hosted benchmark service;
- the evidence report states the operating system mechanism used, command
  lines, process/runtime inventory, allowed local endpoints, blocked-network
  result, loopback Postgres proof, and residual limits.

For Level 1 manual search, code/dependency inspection plus local stdio execution
can be accepted with a scope limit. Level 3 default-on automatic injection
requires the sandbox probe.

## EG-030: Tenant, Corpus, And Personal-Memory Isolation Gate

The isolation gate must exercise actual service and MCP paths, not only helper
methods.

Required cases:

- default Striatum token can read only its primary pair;
- visible secondary Striatum corpus is denied without
  `memory.read_cross_corpus`;
- visible secondary Striatum corpus is allowed only when explicitly requested
  and granted;
- non-primary tenant is denied without `memory.read_cross_tenant`;
- personal memory is denied by default even when a reference id or corpus label
  is known;
- personal memory requires `memory.read_personal` plus an explicit operator
  request and remains ineligible for default Striatum automatic injection;
- bundle identity, repository identity, labels, paths, discovery metadata, and
  opaque `reference_id` values are not authorization grants;
- `engram.describe_corpus` and `engram.health` do not reveal hidden personal
  corpus names, counts, freshness metadata, paths, or stack traces to a default
  Striatum token;
- `tenant_id='striatum'` rows have `source_kind='striatum'` before content is
  returned, and inconsistent rows are rejected or omitted;
- all returned results echo the authorized `(tenant_id, corpus_id)` pair.

Pass criteria:

- unauthorized reads return no content;
- unauthorized, `no_data`, and pair-mismatch responses omit or null corpus
  inventory metadata such as bundle ids, source-time bounds, freshness windows,
  staleness seconds, hidden corpus labels, and row counts;
- negative tests include both search and fetch;
- reference-replay tests include a crafted reference whose decoded row pointer
  targets personal memory under a default Striatum token, plus the symmetric
  case once a `memory.read_personal` token exists;
- at least one framed MCP or handler-level test covers the token shape used by
  the CLI;
- errors do not invite capability escalation inside agent-visible text.

## EG-040: `fetch_reference` And MCP/Reference Hardening Gate

Reference fetching is a separate authorization event.

Pass criteria:

- `engram.fetch_reference` decodes opaque references, validates the decoded row
  id as a UUID or accepted typed reference, then reauthorizes the stored
  tenant/corpus/source-kind row before returning content;
- a reference created under one capability scope cannot be replayed under a
  weaker scope;
- unauthorized, not-visible, and not-found references collapse to a uniform
  external MCP error shape;
- malformed base64, malformed JSON, syntactically invalid UUIDs, unknown table
  tags, and stale projection references return controlled reference errors;
- MCP frame reader enforces a maximum `Content-Length`;
- malformed headers and invalid JSON produce JSON-RPC parse-error responses
  where possible instead of crashing the operator session;
- no reference error leaks hidden tenant names, personal corpus counts, raw SQL
  errors, stack traces, private absolute paths, sensitive excerpts, corpus
  bundle ids, source-time bounds, or freshness metadata for unauthorized pairs.

## EG-050: Stale-Index And Freshness Gate

Staleness is correctness, not only quality.

Pass criteria:

- health checks compare latest validated raw bundle, active projection
  generation, manifest hash, item count, active chunk count, embedding count,
  embedding skip count by model/dimension/skip reason, copied-field mismatch
  counts between active embeddings, chunks, and items, invalidated-active-row
  count, and V1 raw-only bundle presence;
- invalidated-active-row count is zero for every retrieval-visible table;
- a new full bundle supersedes old active projection rows transactionally or
  marks the index stale until activation completes;
- incremental tombstone/redaction fixtures invalidate old chunks, references,
  embeddings, and retrieval caches before lower-tier reads can serve them;
- stale memory is returned only with `status='stale'` or a stale label when the
  request policy accepts stale results;
- stale memory is omitted or treated as `no_data` when the request rejects
  stale results;
- current repository files, current work packets, and accepted decisions outrank
  stale memory;
- stale/conflict omissions record the omitted memory item's `logical_id` or
  reference and the current authority item's `logical_id`, accepted decision id,
  packet id, or repository path that caused the omission;
- Engram never calls Striatum to auto-export fresh data. If freshness is needed,
  it emits a gap, stale status, or operator action hint without corpus egress.

Dirty-working-tree retrieval rendering cases (proposal-text coverage; the
cases below describe inputs and expected behavior. Harness wiring, fixture
names, and runnable command names remain deferred with EG-050's broader
implementation surface and do not assert that any gate currently passes):

- case `dirty_retrieval_surface_flag_present`: input is an RFC 0046
  projection row with `source_dirty_working_tree=true` returned through an
  authorized RFC 0047 retrieval; expected behavior is that the result row
  surfaces `dirty_working_tree=true` (RFC 0047 § Response Requirements) and
  the recommended citation rendering carries the `dirty_working_tree=true`
  marker adjacent to the citation. Covers: dirty rows must not be returned
  with `dirty_working_tree=false`, defaulted to `false`, or rendered
  without the marker.

- case `dirty_retrieval_no_clean_relabel`: input is a dirty RFC 0046
  projection row whose row-level provenance carries
  `provenance.dirty_working_tree=true`; expected behavior is that no RFC
  0047 result row, RFC 0048 memory item, or recommended citation rendering
  presents the result as a clean committed-state citation (no
  `dirty_working_tree=false`, no missing marker, no commit-only rendering
  that hides the dirty provenance). Covers: dirty evidence must remain
  distinguishable from evidence tied only to committed Git objects (RFC
  0046 § Dirty working tree projection rules).

- case `dirty_packet_freshness_label`: input is a dirty result row that is
  selected for an RFC 0048 packet; expected behavior is that the packet
  builder renders the item with the RFC 0048 memory item shape's
  `freshness=dirty_working_tree` label and `dirty_working_tree=true`, never
  relabels the item as `freshness=fresh`, and never collapses dirty status
  into the generic `stale` label. Covers: dirty status is a distinct
  freshness concern from staleness; a dirty row that is also stale carries
  both concerns without overwriting the dirty label.

- case `dirty_unauthorized_no_metadata_leak`: input is a dirty projection
  row that the caller is not authorized to read, requested through an
  unauthorized, `no_data`, or pair-mismatch path; expected behavior is that
  the response carries no result row for that candidate, leaks no
  `dirty_working_tree` flag, hidden path, or dirty-specific metadata, and
  records the omission only through the privacy-safe audit shape defined
  in RFC 0048 § Omission Audit Event Shape. Covers: dirty state must not
  become a side channel for unauthorized-corpus inventory.

## EG-060: Privacy, Redaction, And Withheld-Content Gate

Pass criteria:

- default Striatum retrieval omits rows above the token's allowed privacy tier;
- withheld content returns no hidden content and no inferred summary of hidden
  content;
- deterministic redaction notices may appear only when the notice itself is
  allowed by policy;
- redaction state stays attached to every returned result and injected item;
- privacy reclassification invalidates old lower-tier chunks and embeddings
  before lower-tier reads can serve them;
- result fixtures include redacted, withheld, low-confidence, stale,
  identity-leak-shaped, and citation-leak-shaped rows;
- `identity_leak` and `citation_leak` are RFC 0049 gate-local omission reason
  codes until RFC 0048 or an accepted successor reconciles them with packet
  omission vocabulary;
- automatic injection preserves redaction labels or omits the item with a
  reason code such as `redaction_withheld`, `privacy_tier_exceeded`,
  `identity_leak`, or `citation_leak`;
- `identity_leak` is used when a result body is otherwise eligible but an
  identity field, label, instance name, repository label, or path-shaped field
  would reveal data above the caller's allowed tier;
- `citation_leak` is used when a citation, reference payload, path, line hint,
  or display identifier would reveal an absolute path, operator-private label,
  hidden corpus identity, or higher-tier source identity.

EG-060 `raw_payload` privacy inheritance fixture (proposed; not implemented
and not yet passing):

- the fixture proposes that every projection `raw_payload` value inherits
  the parent item's `privacy.privacy_tier`, `privacy.redaction_state`,
  `privacy.withheld_fields`, and `visibility`
  (`visibility.default_visible_to` and `visibility.requires_capabilities`)
  as exported by RFC 0045 and projected by RFC 0046, and that retrieval and
  injection must forbid `raw_payload`-derived fields above the caller's
  authorized tier, redaction state, or visibility;
- fixture proposal: a multi-tier V2 bundle yields projection rows across
  every family proposed by RFC 0046 (`striatum_items`, `striatum_references`,
  `striatum_documents`, `striatum_runs`, `striatum_agents`,
  `striatum_artifacts`, `striatum_git_refs`, `striatum_issues`,
  `striatum_links`, `striatum_chunks`, `striatum_chunk_embeddings`, and
  `striatum_embedding_skips`) with `raw_payload` values whose constituent
  fields each carry a known parent `privacy.privacy_tier`,
  `privacy.redaction_state`, and `visibility`;
- pass criteria proposal: for a caller authorized at a given tier and
  capability set, the RFC 0047 response, the RFC 0048 injected packet, and
  any `omitted[]` audit entry must not expose any `raw_payload`-derived
  field whose inherited tier, redaction state, or visibility exceeds
  caller authorization, and the matching projection row must be omitted
  with a closed RFC 0048 reason code such as `privacy_tier_exceeded`,
  `redaction_withheld`, `identity_leak`, or `citation_leak`;
- negative-case proposal: a candidate row whose `raw_payload` carries
  hidden body text, withheld field values, pre-redaction content,
  operator-private absolute paths, or identity/label fields that would
  exceed visibility must fail closed before retrieval, injection, or audit
  entry exposure, regardless of whether the row's top-level columns alone
  would otherwise be eligible;
- audit-reconstruction proposal: EG-110 audit reconstruction must show
  that every omission caused by a `raw_payload`-derived violation is
  recorded with an opaque request-local `candidate_id`, lineage to the
  projection family, generation, and retrieval lane, and a closed RFC
  0048 reason code, without copying the hidden `raw_payload`-derived
  content into the audit record itself;
- status: this fixture is proposal text only. EG-060 carries the fixture
  description as a proposal; the fixture is not implemented and has not
  been exercised against runtime evidence. Until accepted/promoted RFC
  0045-RFC 0048 successors and the implementation exist, this fixture's
  state is `not_run`, and the gate continues to use `blocked_upstream`
  when upstream privacy/redaction vocabulary is not accepted.

## EG-070: Retrieval-Quality And Golden-Query Gate

Retrieval quality is measured by cited references, not impressions.

Golden queries must be declared in a machine-readable manifest, committed with
the gate evidence packet or otherwise content-addressed in the review packet.
The manifest must include:

- manifest schema version and manifest hash;
- fixture bundle ids, paths, `bundle_sha256` values, manifest hashes, and
  fixture record hashes used by the query set;
- minimum required query counts by RFC 0045 `sub_kind`, RFC 0046 projection
  family, retrieval lane, and RFC 0048 purpose;
- one record per query with deterministic id, purpose, requested pair, filters,
  retrieval lane, projection family, expected references, forbidden references,
  freshness policy, and threshold tier;
- explicit coverage for negative, isolation, redaction, stale/conflict, and
  malformed-result families.

Golden query records should have this shape inside the manifest:

```json
{
  "id": "golden.rfc0044.capability_boundary",
  "fixture_bundle_ids": ["bundle.striatum.v2.minimal"],
  "fixture_manifest_sha256": "sha256:<hex>",
  "fixture_record_hashes": ["sha256:<hex>"],
  "purpose": "review_prepare",
  "retrieval_lane": "structured",
  "projection_family": "striatum_items",
  "query_text": "Prior findings about RFC 0044 capability boundary repairs",
  "tenant_id": "striatum",
  "corpus_id": "striatum",
  "filters": {
    "rfc_ids": ["0044"],
    "sub_kinds": ["rfc", "review", "synthesis", "handoff"]
  },
  "expected_references": ["logical_id:rfc:0044", "logical_id:review:rfc0044-final-synthesis"],
  "forbidden_references": ["tenant:personal"],
  "expected_status": "ok",
  "freshness_policy": "accept_stale_with_warning",
  "quality_threshold_tier": "P1",
  "notes": "Exact RFC and accepted synthesis should outrank raw logs."
}
```

Required golden-query families:

- exact identifier lookup by RFC id, decision id, review id, run id, workflow
  job id, job id, process id, artifact id, issue id, blocker id, commit SHA,
  path, source hash, and bundle id where fixtures provide them;
- structured filter queries by corpus, sub-kind, authority class, status,
  privacy tier, source time, run/job, agent role, artifact kind, path, and
  commit;
- linked-object traversal such as reviews for an RFC, runs that produced a
  handoff, artifacts produced by a job, or blockers associated with a failed
  run;
- lexical queries over canonical docs, reviews, reports, artifacts, git
  summaries, and chunks;
- semantic queries over task descriptions, prior failures, review concerns,
  and operator workflow phrases when local embeddings are enabled;
- authority and recency ranking queries where current canonical docs and
  accepted syntheses outrank old brainstorms, unsynthesized reviews, raw logs,
  and stale packets;
- negative queries that should return `no_data` or omit forbidden references;
- multi-corpus queries proving no cross-corpus result appears without explicit
  grant;
- redaction queries proving withheld content is not leaked;
- stale/conflict queries proving stale memory is labeled or omitted, with the
  current authority item recorded when a memory result is omitted for conflict.

Minimum manifest coverage:

- at least one query for every RFC 0045 `sub_kind` represented in the fixture
  bundle, or an explicit manifest omission explaining why that sub-kind is not
  retrieval-visible;
- at least one query for every RFC 0046 retrieval lane enabled in the evidence
  packet: exact-reference, structured, lexical, and local vector when vector is
  enabled;
- for the exact-reference lane, coverage includes every RFC 0045 exact-reference
  namespace represented in the fixtures, including RFC id, decision id, review
  id, run id, workflow id, workflow job id, job id, process id, artifact id,
  issue id, blocker id, commit SHA, path, logical path, source hash, and bundle
  id; lexical or vector fallback does not count as exact-reference success;
- at least one query for each Level 3 candidate purpose from RFC 0048:
  `operator_startup`, `workflow_scaffold`, `packet_prepare`, `review_prepare`,
  and `blocker_recovery`;
- at least one negative query each for unauthorized pair, personal-memory
  denial, redaction/withheld content, stale rejection, current-authority
  conflict, missing citation, identity leak, and citation leak.

Initial threshold proposal:

- P0 exact identifier queries: 100 percent return the expected primary
  reference at rank 1 through the exact-reference lane, with citation,
  successful `fetch_reference` reauthorization, and no forbidden reference.
- P1 structured and linked queries: at least 90 percent return all required
  references within the requested `top_k`, with no forbidden reference.
- P2 lexical and semantic queries: at least 80 percent return one expected
  high-authority reference in the top 5, with no forbidden reference.
- Negative and isolation queries: 100 percent return `no_data`, `unauthorized`,
  or an allowed redaction notice, with no forbidden content.
- Every returned result used for pass/fail has a citation sufficient for
  `fetch_reference`.
- Every result row used for pass/fail is traceable to the retrieval lane,
  projection family, projection row id, chunk id when applicable, chunk hash
  when applicable, generation id, score, rank, and ranking profile used for
  that query.

If hardware, corpus size, or upstream schema changes make these thresholds
unfair, reviewers may revise them before promotion. A failed golden query cannot
be waived by manual judgment without recording the query id, failure, and
reason.

## EG-080: Malformed, Uncited, And Pair-Mismatched Result Gate

Callers must treat retrieval output as untrusted.

Required malformed fixtures:

- missing `reference_id`;
- missing citation;
- missing `tenant_id` or `corpus_id`;
- response pair different from request pair;
- result row whose stored pair differs from response pair;
- unknown `source_kind`;
- malformed timestamps;
- invalid score or confidence type;
- stale result without freshness metadata;
- redacted result without redaction state;
- result whose body is eligible but whose identity fields, labels, paths, or
  citation payload would leak unauthorized or higher-tier data;
- low-confidence generated summary without confidence;
- oversized excerpt;
- duplicate references with conflicting hashes.

Pass criteria:

- uncited results are discarded and never injected;
- pair-mismatched results are discarded and logged as malformed or
  unauthorized;
- malformed partial results do not poison otherwise valid results unless the
  response-level contract is broken;
- every omission records an entry that conforms to the canonical omission
  audit event shape defined in RFC 0048
  [Omission Audit Event Shape](0048-striatum-context-injection-policy.md#omission-audit-event-shape),
  with `selected=false`, a `reason` drawn from the closed RFC 0048
  vocabulary, request-local `candidate_id`, lineage (retrieval lane,
  projection family, projection generation, projection/chunk ids when
  visible to the reviewing tier), and ranking (rank, score);
- identity or citation leak omissions use `identity_leak` or `citation_leak`
  rather than silently dropping the result under a generic malformed reason;
- new omission reasons that do not fit the closed RFC 0048 vocabulary are
  not invented at the malformed-handling boundary; RFC 0048's extension
  rule applies and the closest defensible code plus `reason_detail`
  (subject to the lower-tier redaction rules) is used until an extension
  is accepted upstream;
- automatic packet assembly records omission entries using the canonical
  shape and produces status `malformed`, `no_data`, `stale`, or `ok` as
  appropriate, rather than citation-free prose.

## EG-090: Prompt-Injection Containment Gate

Retrieved memory is untrusted evidence. It may contain old prompts, commands,
review text, malicious strings, or tool output.

Required prompt-injection fixtures:

- memory text saying `ignore prior instructions`;
- memory text instructing an agent to run a command;
- memory text claiming to grant `memory.read_personal` or another capability;
- memory text asking for broader Engram access after `unauthorized`;
- memory text containing a URL or network exfiltration instruction;
- raw model-output-like text with system/developer/operator instruction shape;
- stale packet text that conflicts with the current packet.

Pass criteria:

- memory is rendered only in a labeled memory section, never system, developer,
  or operator instruction slots;
- memory text is not executed, followed, or converted into a capability grant;
- unauthorized results do not trigger a retry with broader capabilities;
- current operator instructions, current packets, current repo files, Striatum
  state, and accepted project decisions outrank memory;
- conflict warnings cite both the omitted memory item's `logical_id` or
  reference and the current authority item's `logical_id`, accepted decision
  id, packet id, or repository path;
- broad logs, raw transcripts, raw model output, and whole-corpus dumps are not
  automatically injected;
- tool output and network-derived content are never combined with direct Engram
  corpus access;
- the rendered packet preserves citations next to any memory-derived claim.

## EG-100: Latency And Non-Blocking Gate

Latency gates bound operator ergonomics. Timeouts are memory status, not
workflow blockers.

Default budgets:

| Surface | Target | Hard behavior |
|---------|--------|---------------|
| health check | p95 <= 500 ms | timeout becomes `unavailable` or `timeout` |
| search | p95 <= 2 seconds | late response ignored |
| fetch | p95 <= 5 seconds | late response ignored |
| operator startup automatic memory | p95 <= 3 seconds | total automatic budget <= 10 seconds |
| packet/review/blocker automatic memory | p95 <= 8 seconds | total automatic budget <= 10 seconds |
| manual search UI/CLI | p95 <= 2 seconds for listed results | slower paths remain explicit/manual |

Pass criteria:

- benchmarks record hardware, database size, fixture bundle hashes, index state,
  local model/embedding status, command line, repetitions, p50, p95, max, and
  timeout count;
- `operator_startup` benchmarks include separate cold-start and warm-cache
  measurements. Cold-start evidence records whether Postgres, projection
  indexes, local embedding/model runtimes, and retrieval workers were already
  resident;
- if cold-start `operator_startup` search cannot meet the default target, the
  report may propose asynchronous prefetch or a larger purpose-specific timeout
  up to 5 seconds, but Level 3 remains blocked unless the total automatic
  packet budget stays within 10 seconds and timeout behavior remains
  non-fatal;
- automatic retries default to zero, except one local transient process-start
  retry inside the same hard budget;
- when the budget expires, Striatum continues with baseline context and visible
  memory status;
- no workflow readiness, lease, blocker, artifact publication, or review
  verdict waits on Engram memory;
- slower-than-budget results block default-on injection until fixed, but may
  still permit explicit manual search if marked as manual and non-blocking.

## EG-110: Audit-Trail Reconstruction Gate

Automatic memory sections must be reconstructable after the fact without making
Engram authoritative Striatum state.

Pass criteria:

- for Level 2, at least one automatic packet for each enabled opt-in purpose
  covered by the report is reconstructed from audit evidence; for Level 3, at
  least one automatic packet for each default-on purpose is reconstructed, or
  the purpose remains ineligible for default-on use;
- the audit record includes policy version, purpose, timestamp, run id,
  workflow job id, job id, session id, lease id, enable/disable state, override
  source, request id, query text, filters, tenant/corpus pair, limits, freshness
  policy, timeout, citation requirement, response status, warnings, Engram
  schema/retrieval profile, bundle ids or projection generation ids, selected
  references, omitted candidate entries, the canonical-shape omission reason,
  token budget, estimated token use, truncation decisions, stale/conflict
  labels, privacy tier, and redaction labels;
- candidate-level audit evidence records every selected and omitted candidate
  using the canonical omission audit event shape defined in RFC 0048
  [Omission Audit Event Shape](0048-striatum-context-injection-policy.md#omission-audit-event-shape),
  including request-local `candidate_id`, `selected` flag, `reason` from the
  closed RFC 0048 vocabulary, lineage fields (retrieval lane, projection
  family, projection generation id, projection row id, item projection id,
  chunk id, chunk hash, chunk bounds, bundle id, `reference_id`, RFC 0045
  item identity) populated only when visible to the reviewing tier, ranking
  fields (rank, score, score breakdown, ranking profile), and labels
  (freshness, privacy tier, redaction state, authority class, stability
  class, confidence) populated subject to the same visibility rule;
- conflict omission records include the omitted memory `logical_id` or visible
  reference and the current authority `logical_id`, accepted decision id,
  packet id, or repository path that caused the omission, recorded in the
  RFC 0048 `conflict_with` block;
- omitted candidates that are unauthorized, pair-mismatched, above the caller's
  privacy tier, or hidden by redaction use opaque request-local candidate ids
  instead of leaking item ids, logical ids, paths, labels, bundle ids,
  source-time bounds, or corpus inventory into lower-tier audit views, per
  RFC 0048's privacy-safe local audit rules;
- audit records inherit the maximum privacy tier of the selected or omitted
  items they identify, and audit storage remains local-only and no-egress;
- the reason codes used in audit evidence are drawn from the closed RFC 0048
  vocabulary; any extension must follow RFC 0048's extension rule before it
  is accepted as evidence under this gate;
- reconstruction can explain why every selected result appeared and why every
  omitted candidate was omitted;
- reconstruction for an authorized caller does not require reading rows that
  caller is not authorized to read; lower-tier reconstruction receives the
  redacted/opaque omission evidence only;
- a per-run copy of the memory section is provenance only. It is not readiness
  state, cache authority, or a substitute for current repository reads.

Dirty-working-tree audit reconstruction cases (proposal-text coverage; these
cases describe inputs and expected behavior. Harness wiring, fixture names,
and runnable command names remain deferred with EG-110's broader
implementation surface and do not assert that any gate currently passes):

- case `dirty_audit_records_flag`: input is an automatic packet that
  selected at least one dirty result row (RFC 0046
  `source_dirty_working_tree=true`); expected behavior is that the audit
  record carries the `dirty_working_tree` boolean for that selected
  candidate, mirrored from the RFC 0047 result row and the RFC 0046
  projection row, alongside the existing freshness label, privacy tier,
  and redaction state. Covers: audit reconstruction must show which
  selected items derived from dirty working-tree evidence.

- case `dirty_audit_records_for_visible_omissions`: input is an automatic
  packet whose candidate list contained dirty rows that were omitted for
  reasons other than authorization or privacy tier (for example
  `freshness_rejected`, `budget`, or `pair_mismatch_safe_reason`); expected
  behavior is that the omitted candidate audit entry carries the
  `dirty_working_tree` boolean when the candidate is visible to the
  reviewing tier under the RFC 0048 § Omission Audit Event Shape rules.
  Covers: dirty state is recorded for visible omitted candidates so a
  later reviewer can reconstruct whether the omission applied to dirty or
  clean evidence.

- case `dirty_audit_lower_tier_opaque`: input is an audit reconstruction
  request from a reviewer whose tier is below the privacy tier of a dirty
  candidate; expected behavior is that the audit view uses the opaque
  request-local `candidate_id` for that candidate and does not surface the
  `dirty_working_tree` flag, source path, dirty-specific lineage, or any
  other field above the reviewer's tier. Covers: dirty state inherits
  parent-item privacy and may not become a side channel for higher-tier
  inventory in lower-tier audit views.

- case `dirty_audit_no_clean_relabel_in_reconstruction`: input is a
  reconstruction of an automatic packet that included a dirty result;
  expected behavior is that the reconstructed memory section preserves
  the `dirty_working_tree=true` marker and the
  `freshness=dirty_working_tree` label that RFC 0048 § Memory Item Shape
  requires, never reconstructs the item with `dirty_working_tree=false` or
  a `freshness=fresh` label, and never replaces the dirty evidence with a
  clean-looking citation. Covers: audit reconstruction faithfully
  preserves the rendering contract that RFC 0047 and RFC 0048 establish
  for dirty evidence.

## EG-120: Disable-Control Gate

Disable controls must be explicit and visible.

Required controls:

```text
run: disable all automatic memory for this Striatum run
session: disable automatic memory for an operator or agent session
packet: disable or override memory for one packet
purpose: disable memory for a purpose such as review_prepare
manual: allow manual search while automatic injection remains disabled
```

Pass criteria:

- run-scope disable prevents automatic Engram calls and records status
  `disabled`;
- session-scope disable prevents automatic calls for that session;
- packet-scope disable or override affects only that packet;
- purpose-scope disable affects only the named purpose;
- manual search can remain enabled while automatic injection is disabled;
- disable state is visible in packet metadata or memory status;
- silent disablement is a failure because it prevents later review;
- disabled automatic memory never degrades into hidden manual search, hidden
  retries, or broader capability requests.

Gate cases for the transient-unless-promoted rule (RFC 0048's session-disable
persistence rule, `docs/rfcs/0048-striatum-context-injection-policy.md`):
these cases are proposal-text coverage of the disable-control rule. They
describe inputs and expected behavior; harness wiring and runnable command
names remain deferred with EG-120's broader implementation surface.

- case `disable_session_transient_on_restart`: input is an operator or agent
  session that issued a session-scope disable, followed by a daemon restart
  with no recorded promotion to run scope or operator configuration; expected
  behavior is that the new session starts without inheriting the prior
  session-scope disable, the prior session's disable state does not silently
  carry over, and an automatic call in the new session is governed by the
  default enable/disable state rather than the lost session-scope disable.
  Covers: session-scope disablement is transient across daemon restart unless
  promotion is recorded.

- case `disable_session_promoted_persists`: input is a session-scope disable
  that an implementation explicitly promotes to run scope or operator
  configuration, with the promotion recorded in disable state; expected
  behavior is that after a daemon restart the promoted disable continues to
  prevent automatic Engram calls within its promoted scope, the promotion is
  reflected in packet metadata or memory status as a non-session scope, and
  the promotion record is reconstructable in EG-110 audit evidence. Covers:
  promotion to a non-session scope must persist and must remain visible.

- case `disable_session_unpromoted_no_silent_carry`: input is a session-scope
  disable that was never promoted, paired with a subsequent automatic packet
  attempt in a post-restart session that reuses the same operator identity or
  the same workflow continuation; expected behavior is that the post-restart
  attempt either proceeds under the default enable state or is disabled only
  by a fresh, explicit disable, never by a silently inherited prior
  session-scope disable. Covers: the rule that disablement may not be silent
  and may not survive restart without an explicit promotion record.

- case `disable_promotion_recorded_in_audit`: input is any promotion of a
  session-scope disable to run scope or operator configuration; expected
  behavior is that the promotion source, the prior and new scope, and the
  recording timestamp appear in the disable-control transcript referenced by
  EG-110's audit evidence, alongside the existing enable/disable state and
  override source fields. Covers: the promotion record requirement that
  closes the deferred F022 / AL-D011 disable-persistence concern at gate
  level.

## EG-130: Striatum-Without-Engram Compatibility Gate

Striatum must continue to function without Engram.

Pass criteria:

- Striatum package installation has no Engram dependency;
- Striatum runtime modules do not import Engram client code;
- Striatum daemon RPC capability registries do not include Engram `memory.*`
  capabilities;
- Striatum workflows prepare, start, run, review, recover, and produce required
  artifacts with Engram missing from `PATH`;
- Engram unavailable, unhealthy, unauthorized, stale, malformed, disabled, or
  timed out responses remain non-fatal;
- optional Engram tests are gated behind explicit local opt-in;
- operator docs may explain Engram configuration, but no hidden state turns
  Engram into a dependency.

## EG-140: Generated Memory Product Privacy And Audit Placeholder Gate

Generated memory products from the roadmap, such as known-friction ledgers,
prior-decision indexes, reusable implementation-pattern indexes, blocker
summaries, agent-performance notes, project-trajectory summaries, and RFC
lineage maps, are derived products. They are not raw evidence and they are not
eligible for Level 2 or Level 3 injection until a downstream generated-product
implementation spec from RFC 0051 is accepted per D089, covering privacy
inheritance, provenance/citation, audit, rebuildability, and eval gates.

Current gate action:

- any attempt to inject a generated memory product reports `blocked_upstream`
  until the downstream generated-product implementation spec is accepted;
- `accepted_with_scope_limit` may permit source-evidence retrieval while
  explicitly omitting generated products;
- Level 1 manual search of the cited source evidence remains governed by
  EG-010 through EG-130 and does not promote the derived product itself.

Future pass criteria must include:

- every generated product cites the raw and projection evidence it summarizes;
- the generated product inherits the maximum privacy tier, redaction state, and
  visibility constraints of every cited source item;
- the product has its own generation id, product hash, source item ids, source
  chunk ids/hashes, source projection generation ids, model/prompt/version
  metadata if any model produced it, and audit record;
- generated products with missing citations, unsupported source tiers, or stale
  source generations are omitted with explicit reason codes;
- generated products never replace current authority, raw evidence, or accepted
  decisions.

## Evidence Packet For Review

A reviewable RFC 0049 implementation packet should include:

- fixture manifest with paths, hashes, row counts, and privacy/redaction notes;
- V2 validator transcript and negative-validator transcript;
- no-egress evidence report with sandbox mechanism, command outputs,
  transitive local runtime inventory, allowed loopback endpoints, and loopback
  Postgres bind proof;
- isolation matrix covering service, MCP, and CLI paths;
- `fetch_reference` and MCP/reference hardening transcript;
- stale-index and redaction invalidation transcript;
- machine-readable golden-query manifest and retrieval-quality result table;
- malformed/uncited result handling transcript;
- prompt-injection containment packet examples;
- latency report with hardware, fixture metadata, warm-cache measurements, and
  cold-start `operator_startup` measurements;
- audit reconstruction sample for automatic packet memory with candidate-level
  row/chunk/lane/rank/score and omission evidence;
- disable-control transcript for run, session, packet, purpose, and manual
  modes;
- generated-memory-product omission evidence while EG-140 remains
  `blocked_upstream`;
- Striatum-without-Engram reciprocal artifact;
- reviewer recommendations and accepted/deferred findings under
  `docs/reviews/`.

## Review Requirements

Use the multi-agent review loop before promotion. Required review lanes:

- local-first and no-egress evidence review;
- transitive local model/embedding runtime no-egress review;
- tenant/corpus/personal-memory isolation review;
- RFC 0045 fixture and validator review;
- RFC 0046 stale-index and projection-health review;
- retrieval-quality and golden-query review;
- prompt-injection and instruction-safety review;
- operator-latency and ergonomics review;
- auditability and provenance review;
- generated memory product privacy/audit review before any derived product is
  eligible for injection;
- Striatum runtime-independence review;
- implementation-readiness review for both repositories.

Reviewers should treat as blockers any gap that allows personal memory by
default, cross-corpus leakage, cross-tenant leakage, uncited injection,
instruction-shaped memory becoming active instructions, stale lower-tier
retrieval, hidden hosted dependency, network egress from a corpus-reading
process, workflow dependence on Engram, or default-on automatic injection
without disable controls.

## Acceptance Criteria

- Fixture bundles and validator checks are deterministic, local, and
  fail-closed.
- V1 raw-only and V2 projection-ready paths are distinguished.
- No-egress evidence is structural for default-on automatic injection and covers
  transitive local model/embedding runtimes that receive corpus text.
- Tenant/corpus isolation is tested through service, MCP, and CLI surfaces.
- Unauthorized and pair-mismatch responses and audit views do not leak corpus
  inventory, bundle ids, source-time bounds, hidden labels, paths, or row ids.
- Personal memory is denied by default and never automatically injected into
  Striatum packets.
- `fetch_reference` reauthorizes stored rows and collapses probing distinctions
  externally.
- Stale projections, invalidated active rows, privacy reclassification, and
  redaction behavior are detectable and tested.
- Malformed, uncited, pair-mismatched, redacted, stale, and low-confidence
  result fixtures are handled without unsafe injection.
- Golden retrieval queries have a machine-readable manifest, expected
  references, forbidden references, lane/purpose/projection coverage, and
  pass/fail thresholds.
- Prompt-injection fixtures prove retrieved memory remains evidence only.
- Latency budgets are bounded and non-fatal on timeout.
- Audit evidence can reconstruct at least one automatic packet memory section
  before that surface becomes default-on, including row/chunk/lane/rank/score,
  generation, candidate selection, and omission reasons without leaking hidden
  state.
- Disable controls exist for run, session, packet, purpose, and manual modes.
- Generated memory products remain `blocked_upstream` for injection until a
  downstream generated-product implementation spec from RFC 0051 is accepted
  per D089.
- Striatum remains usable without Engram installed, configured, healthy, or
  reachable.
- Manual search and automatic injection promotion criteria are explicit.
- Upstream proposal dependencies and open decisions are named rather than
  silently frozen.
- Level 3 default-on automatic injection requires accepted/promoted successors
  for RFC 0045, RFC 0046, RFC 0047, and RFC 0048.

## Deferred Questions

1. Which exact V2 fixture bundle becomes the committed review seed after
   RFC 0045 acceptance?
2. Which `corpus_id` grammar and instance/repository identity rules are accepted
   upstream?
3. Which RFC 0046 projection generation and health-check schema is accepted?
4. Whether vector retrieval is required for Level 3 or can remain additive after
   exact, structured, and lexical gates pass.
5. Whether the initial quality thresholds need separate values for small fixture
   bundles and large real local corpora.
6. Which hardware profile becomes the reference latency profile.
7. Exact Striatum CLI/UI names for disable controls.
8. Whether stale memory is default-eligible for `operator_startup` or only for
   `review_prepare` and `blocker_recovery`.
9. Which downstream generated-product implementation spec from RFC 0051 will
   define generated memory product privacy inheritance, citation, audit,
   rebuildability, and eval evidence before those products can enter automatic
   injection.
10. Where long-lived gate reports should live after Striatum has a durable
    memory-evaluation artifact convention.
