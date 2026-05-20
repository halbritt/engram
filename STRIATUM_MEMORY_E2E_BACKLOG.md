# Striatum Memory E2E Pipeline — Backlog Execution Plan

Date: 2026-05-15
Posture: this document supersedes the paper-promotion sequencing in
[`STRIATUM_MEMORY_ROADMAP.md`](STRIATUM_MEMORY_ROADMAP.md) for execution
order. The 2026-05-15 pivot is to build the working pipeline layer by
layer, treating RFC 0045-RFC 0049 as design *reference*, not as a
contract gate. The acceptance decisions (AL-D002, AL-D003, AL-D004) are
recorded as humans review working code, not as conditions on shipping
more paper.

Current status as of 2026-05-17: Layers 1-5 landed on master and D083
accepted RFC 0046-RFC 0049 as design reference for the implemented e2e
pipeline. D085 records default-on Striatum operator-token authorization inside
the Striatum tenant/corpus boundary. The architecture follow-up A0-A9 slice
extended the serving path with a unified `MemoryHit` contract, non-capture
`fetch_reference`, executable no-egress probe/run wrapper, minimal
`context_for`, MCP `engram.context_for`, context snapshots/feedback, and
central `engram.policy` checks for packet/context serving plus shared
review/export tier guards, generic exact-reference indexing, and local-only
entity grounding lookup. D086 and D089 defer generated products until a
downstream generated-product spec is accepted; default-on or extraction-affecting
remote grounding fetches and full review UI remain separately gated. The
remaining work in this backlog is
incremental: keep the real-bundle runbook current, use
Layer 4 items as regression-hardening backlog where still valuable, and do not
expand RFC 0050 Stage 3+ source families until real `context_for` eval failures
justify the next family.

## Snapshot Of What Is Already Done

- Phase 1 raw evidence layer: ChatGPT, Claude, Gemini, Striatum bundle
  ingest. Migration 014 carries `source_kind='striatum'`, tenant/corpus
  columns, bundle id.
- Phase 2 segmentation + embedding: complete across the
  AI-conversation corpus (7916 conversations, 11266 active embedded
  segments). Not in scope for Striatum memory but available for shared
  retrieval surfaces later.
- Phase 3 claim extraction + belief consolidation, primary run: 43812
  claims, 42558 beliefs. Residual: 149 unextracted active segments,
  22 failed extractions (parallel-track cleanup).
- RFC 0044 Phase 1 read-only API: `MemoryService.search`,
  `MemoryService.fetch_reference`, `MemoryService.describe_corpus`,
  `MemoryService.health`; MCP stdio tools surface; `--allow-pair`
  visible-pairs-not-grants discipline; closed memory capability
  vocabulary.
- AL-D001 / EG-000 hardening baseline closed. Evidence:
  [`docs/reviews/eg-000-evidence-2026-05-15/EG_000_EVIDENCE.md`](docs/reviews/eg-000-evidence-2026-05-15/EG_000_EVIDENCE.md).
  Committed non-private fixture at
  [`tests/fixtures/striatum_eg000/`](tests/fixtures/striatum_eg000/).
  EG-000-era verification: 579 engram tests passed; the Striatum-side
  zero-coupling test passed
  at Striatum HEAD `a50f495`.
- Layers 1-5 are implemented: migration 015 projection tables, exact-reference
  retrieval, packet builder and audits, EG-010 fixture scaffolding, and
  `make e2e-striatum`. Historical test counts above are retained as execution
  provenance, not as the current suite size. Current evidence from 2026-05-17:
  `make test` passed 798 tests in 704.41s; the context/packet focused suite
  passed 35 tests in 42.05s; `make eval-gates` passed 16 tests in 21.88s;
  `make eval-source-ingestion-gates` passed 16 tests in 38.38s; and
  `make e2e-striatum` passed 1 test in 1.94s.

## Layer-By-Layer Execution Plan

The plan is ordered. Each layer should ship as one or more landed
commits with tests on master before the next layer starts. RFC 0046-
RFC 0049 are referenced; their proposal text is guidance, not contract.

### Layer 1 — Projection Surface (RFC 0046 reference) — completed

Goal: materialize queryable projection rows from raw Striatum captures
so retrieval no longer has to scan and score the `raw_payload` JSON
column. Project only what retrieval actually needs; defer the rest.

Deliverables:

- New migration adding a `striatum_references` projection table with
  columns `(id, capture_id, tenant_id, corpus_id, ref_kind, ref_value,
  ref_value_normalized, content_hash, generation_id, is_active,
  observed_at, raw_payload)`. `ref_kind` vocabulary is closed and
  derives from `sub_kind` plus structured fields in `raw_payload`
  (`path`, `commit`, `rfc_id`, `decision_id`, etc.). Composite indexes
  on `(tenant_id, corpus_id, ref_kind, ref_value_normalized)` and
  `(tenant_id, corpus_id, generation_id, is_active)`.
- `striatum_projection_generations` table with the activation manifest
  payload from RFC 0046 § Embedding Activation Invariant (proposal
  text). One active generation per
  `(tenant_id, corpus_id, parent_kind, parent_id)`; older generations
  superseded.
- Projection worker that consumes `captures` rows where
  `source_kind='striatum'` and emits `striatum_references` rows under
  the current generation, with idempotent `(capture_id, generation_id)`
  uniqueness.
- `engram phase-projection run --tenant striatum --corpus striatum`
  CLI verb (and a `make project` target) that fast-forwards projections
  for the active generation; resumable, deterministic ordering.
- Tests: idempotent re-projection produces zero new rows; activation
  swap supersedes the prior generation atomically; reference rows
  carry `tenant_id`/`corpus_id`/`privacy_tier` from the parent capture.

Acceptance criteria:

- Every active capture has exactly one active reference row per
  derivation type emitted under the active generation.
- `make test` passes including new projection unit tests.
- `engram describe-corpus --tenant striatum` reports the same
  `record_count` as before AND a new `projection_active_count` field
  that matches it.

Scope kept out of Layer 1:

- Embeddings. The first retrieval layer is exact/lexical only.
- Cross-corpus / cross-tenant projection paths.
- Generated/derived memory products (deferred to AL-D004 contract).

### Layer 2 — Retrieval Surface (RFC 0047 reference) — completed

Goal: serve exact-reference and lexical queries from the projection
table rather than from `captures.raw_payload`. Stay read-only, no
egress, single primary pair by default.

Deliverables:

- `MemoryService.search()` gets a `filters` argument with
  `exact_refs: list[{ref_kind, ref_value}]`. When present, the SQL
  filters on `striatum_references` by ref_kind/ref_value_normalized,
  then joins back to `captures` only for the content payload (or
  serves `raw_payload` slice straight from the projection row). When
  absent, falls back to the existing lexical path against `captures`.
- Response shape adds `dirty_working_tree` boolean and `freshness`
  string (`fresh|stale|dirty_working_tree|unknown`) per
  RFC 0047/RFC 0048 alignment.
- `engram.search` MCP tool argument schema extended with
  `filters.exact_refs`, default `null`.
- Tests: `exact_refs` filter returns only matching rows; mismatched
  `ref_kind` returns empty; lexical fallback still returns the same
  hits as the existing tests.

Acceptance criteria:

- Retrieval latency on the committed EG-000 fixture stays under one
  second for exact-reference queries on a cold DB.
- The 4 existing RFC 0044 read tests in `tests/test_striatum_ingest.py`
  still pass unchanged (the lexical path is additive, not replacement).
- New tests cover the `exact_refs` path under
  primary-pair + visible-pair-not-grant discipline.

Scope kept out of Layer 2:

- Vector search. Lexical / exact-ref is enough for the first end-to-
  end path; vector slots in behind the same API later.
- Pagination, ranking quality. Deterministic small-N is fine.

### Layer 3 — Injection / Packet Builder (RFC 0048 reference) — completed

Goal: produce a memory packet for a workflow query — a small typed
shape with selected items, omitted-with-reason entries, and citations.
This is the consumer-facing artifact; downstream agents consume the
packet, not raw search results.

Deliverables:

- `MemoryService.build_packet(query, *, budget, tenant_id, corpus_id)`
  method returning the packet shape (see RFC 0048 § "Memory Item Shape"
  and § "Omission Audit Event Shape" for the canonical fields).
- Closed omission reason vocabulary on the packet:
  `disabled|unavailable|unauthorized|privacy_tier_exceeded|
  redaction_withheld|stale_rejected|over_budget|duplicate|
  generated_product_blocked|low_score|pair_mismatch`. Wired up so the
  packet builder emits a reason whenever a candidate is excluded.
- `engram.build_packet` MCP tool with input schema mirroring the
  method signature.
- Audit record persisted to a new `striatum_packet_audits` table:
  `(packet_id, generation_id, query, budget, selected[], omitted[])`
  with no `raw_payload` content beyond the candidate reference ids.
- Tests: a packet over the EG-000 fixture returns at least one item
  for an exact-reference query; the audit row records the omitted
  candidates and reasons; cross-tenant calls without
  `memory.read_cross_tenant` fail before the audit row is inserted.

Acceptance criteria:

- Packet renders for the EG-000 fixture and at least one real captured
  Striatum bundle (the user provides or we capture-as-fixture).
- Audit-reconstruction smoke can replay the omission list from the
  audit row.
- No `raw_payload` field exceeds the caller's authorized privacy tier
  in any packet item (validates the EG-060 fixture proposal text).

Scope kept out of Layer 3:

- Multi-tier privacy hierarchies beyond the current `privacy_tier`
  integer. Deferred to Layer 5 / future RFC alignment.
- Personal-memory paste-through (AL-N015 / AL-D004 territory).

### Layer 4 — Evaluation Gates (RFC 0049 reference) — current gate passing; broader hardening deferred

Goal: deterministic gates that prove each prior layer stays correct
under regression. EG-000 already exists; this layer extends to the
gates that matter for the e2e path. Pick the minimum that exercises
real behavior, not the full RFC 0049 matrix.

Landed portions: EG-010 fixture library/scenarios and the current
`make eval-gates` target. As of 2026-05-17 the target passes 16 tests covering
fixture validation, exact-reference retrieval, packet building, policy
omissions, dirty packet labels, audit reconstruction, and cross-tenant audit
behavior. Remaining gate ideas below are regression-hardening backlog, not
blockers for the current exact-reference Striatum serving path.

Hardening backlog:

- **EG-010 V2 fixture and validator.** Generalize the EG-000 fixture
  builder into a fixture *library* under
  `tests/fixtures/striatum_v2/<scenario>/` with the eleven scenarios
  enumerated in RFC 0049 § EG-010. Most scenarios are small — start
  with `minimal`, `multi_corpus_isolation`, `redaction`, and
  `tombstone`. A single `validate_fixture()` helper proves each
  bundle parses and verifies its manifest hash before ingest. Initial scenarios
  are covered by the current `make eval-gates` target.
- **EG-050 stale/dirty gate.** Test cases for retrieval rendering of
  dirty rows and packet freshness labels per AL-N005. Cover the four
  retrieval cases from the RFC 0049 alignment edits. Initial packet-label
  coverage landed in
  `tests/test_memory_packet.py::test_build_packet_preserves_dirty_working_tree_label_in_packet_and_audit`;
  the remaining work is the broader retrieval rendering matrix.
- **EG-060 raw_payload privacy inheritance gate.** Promote the
  proposed fixture in
  `docs/rfcs/0049-striatum-evaluation-gates.md` from `not_run` to
  `passing` with the test exercising the four projection families
  Layer 1 emits.
- **EG-080 omitted-event coverage.** Test that every closed omission
  reason from Layer 3 has at least one fixture exercising it.
- **EG-110 audit reconstruction.** Replay a packet audit row and
  prove the selected + omitted lists can be reconstructed without
  loading `raw_payload` content above caller authorization. Initial
  reconstruction coverage landed through `reconstruct_packet_audit()` and
  `tests/test_memory_packet.py::test_reconstruct_packet_audit_replays_selected_and_omitted_without_payload`;
  promotion-level paste-through fixtures remain optional.
- **EG-120 disable-control transient-unless-promoted.** The four
  gate cases authored under AL-N009. Wire them to the disable-control
  surface added in Layer 3.

Acceptance criteria:

- Each gate above has a named pytest function in `tests/`.
- `make eval-gates` (new target) prints a per-gate pass/fail summary.
- Failing any gate is a CI-style regression, not a soft warning.

Scope kept out of Layer 4:

- EG-020 paired-loopback gate (no-egress already enforced at the
  service layer; the test would be redundant).
- EG-090..EG-100 advanced quality gates (defer until vector search
  lands in Layer 2's vector extension).

### Layer 5 — End-To-End MCP Wiring And Serving Smoke — completed

Goal: a single end-to-end smoke from raw bundle on disk → ingest →
projection → packet over MCP → consumer sees the citation. Proves the
pipeline holds together; not a load test.

Deliverables:

- A `tests/test_pipeline_smoke_striatum.py` that:
  1. Ingests `tests/fixtures/striatum_eg000/`.
  2. Runs Layer 1 projection.
  3. Starts an `engram-mcp-stdio` subprocess with the default token.
  4. Sends `tools/call` for `engram.search` with `filters.exact_refs`
     and asserts the citation is present.
  5. Sends `tools/call` for `engram.build_packet` and asserts the
     packet shape, omitted reason vocabulary, and audit row.
- `make e2e-striatum` Makefile target that runs the smoke against the
  current test DB.
- A real-bundle serving runbook at
  `docs/runbooks/striatum-memory-e2e-2026-05-15.md` describing how to
  ingest a real Striatum bundle, run projections, and verify a packet
  end-to-end on a developer machine.

Acceptance criteria:

- `make e2e-striatum` exits 0 against the EG-000 fixture.
- The runbook is reproducible on a fresh checkout with `make install`,
  `make migrate`, and a local Striatum export bundle.

## Cross-Cutting Items

These are not single layers but they have to land alongside.

### Decisions That Need The Human

- **AL-D002** — record an acceptance entry in `DECISION_LOG.md` that
  the RFC 0046-RFC 0049 proposals are the design reference for the
  e2e pipeline. Completed by D083.
- **AL-D003** — Level 3 / default-on automatic memory authorization.
  Completed by D085 for the default Striatum operator token inside
  `tenant_id='striatum', corpus_id='striatum'`.
- **AL-D004** — generated-product contract (privacy inheritance,
  citation, audit, gate). Deferred by D086 and D089 until a downstream
  generated-product specification is accepted; RFC 0051/D094 covers only the
  narrow generic evidence/reference substrate.

### Nonblocking RFC Polish (Defer Until Promotion Packet)

Carried from
[`docs/reviews/striatum-memory-rfc-alignment-2026-05-14/FINDINGS_LEDGER.md`](docs/reviews/striatum-memory-rfc-alignment-2026-05-14/FINDINGS_LEDGER.md):

- `AL-N007`, `AL-N008`: stale open-decision wording cleanup.
- `AL-N010`: response-status to packet-label mapping (`ok` →
  `memory: available`).
- `AL-N011`: workflow/job identifiers in citation rendering.
- `AL-N012`: roadmap/index promotion packet posture.
- `AL-N013`: Level 1 manual/raw-only quality checklist.
- `AL-N014`: RFC 0047 authority wording cleanup.
- `AL-N015`: EG-030/EG-110 manual paste-through fixture.

These are paper edits, not code work. They land if and when the human
chooses to publish a promotion packet.

### Operator UX Items From Memory

- `subject_kind_hint` (migration 012 payload) is not yet surfaced to
  the extractor prompt or interview UI; queued for cleanup. Reference:
  `feedback`/`project` memory note
  `project_interview_predicate_intent_polish`.
- RFC 0027 web UI polish ("yeesh" on first real use); reference:
  `project_rfc0027_ui_polish_deferred`.

### Upstream Striatum Bugs To Track

- [striatum#18](https://github.com/halbritt/striatum/issues/18):
  supervisor never closes the lane stdin write end, blocking
  `codex exec ... -` and any other `cmd -` lane on EOF. Until this
  lands, do not start daemon-mode supervised runs.
- [striatum#20](https://github.com/halbritt/striatum/issues/20):
  the runner should detect heartbeat stalls / lease expiration and
  raise blockers; operators should not have to roll their own
  watchdog.

The scaffolded promotion workflow at
`striatum/striatum-memory-rfc-promotion-2026-05-14/` stays
deferred-canceled until #18 lands or its lane command is moved off
stdin.

## Parallel Engram Pipeline Residuals (Not Striatum-Memory)

Surfaced so they do not fall off. Touch when convenient; they do not
block any Striatum-memory layer.

- 149 active segments without an extraction (Phase 3 gap).
- 22 failed claim extractions to revisit.
- Step 5A/5B from [`ROADMAP.md`](ROADMAP.md): synthetic context-eval e2e
  harness first, owner gold-set authoring second. Owner chat history has too
  much entity ambiguity for the first eval substrate. The public harness at
  `tests/fixtures/context_eval/synthetic_e2e/` seeds beliefs, captures, and
  local public-entity grounding evidence; it does not replace the later
  owner-authored private dataset.
- RFC 0053 claim-grounding synthetic e2e is separate from this Striatum-memory
  backlog and from context serving. Its starter target is
  `make e2e-claim-grounding-synthetic`; the sidecar/runtime scaffold target is
  `make e2e-claim-grounding-runtime`. The current scaffold includes persisted
  grant lifecycle rows, CLI grant approval/denial/revocation, disabled
  extraction request sidecars, disabled configured generic HTTP and Tavily
  search adapters, and broker credential-separation tests; default extraction
  remains no-egress and network-free.
- Steps 6-9 from `ROADMAP.md`: adversarial round → synthesize →
  full V1 corpus stabilization → gold set against consolidated V1
  corpus.
- Phase 4 entity canonicalization + belief review queue.
- Phase 5 residuals after the 2026-05-16 architecture slice: broad
  context-snapshot invalidation policy, source/projection/entity event
  coverage, feedback review/reporting surfaces, and real owner-authored
  context evals. Minimal `context_for`, context snapshots, MCP serving, and
  context feedback insertion now exist.

## Remaining Sequencing Recommendation

Layers 1-5 and AL-D002/AL-D003 have landed. A0-A9 also landed the narrow
serving/context/policy/generic-index/local-grounding follow-up slice. Remaining
Striatum-memory work is limited to incremental hardening and operator
documentation:

1. Keep the real-bundle Striatum e2e runbook current.
2. Complete remaining named Layer 4 hardening gates where still valuable:
   EG-050 retrieval rendering, EG-060, EG-080, EG-120, and any promotion-level
   EG-110 fixtures beyond the current audit reconstruction smoke.
3. Keep optional vector retrieval deferred until exact-reference packet
   behavior is stable under the unified hit contract.
4. Keep generated products deferred until a downstream generated-product
   specification is accepted (D089).
5. Keep RFC 0050 Stage 3+ source-family expansion deferred until real
   `context_for` eval failures identify the next source family.

## What This Plan Is Not

- A promotion path for RFC 0045 as binding spec. RFC 0045 remains
  proposal-only; RFC 0046-RFC 0049 are accepted design references, not frozen
  binding specs.
- A commitment to ship every gate in RFC 0049. Only the gates listed
  in Layer 4 are in scope.
- A schedule. Sequencing is fixed; cadence is not. Each layer ships
  when its tests are green and the working code is on master.
