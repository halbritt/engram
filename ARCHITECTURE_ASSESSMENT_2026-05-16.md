# Engram Architecture Assessment

Date: 2026-05-16
Reviewer stance: systems architecture review, not an implementation handoff.

## Scope

I reviewed the project from the repo rather than from a live private corpus. I
read the canonical goal and principle docs (`README.md`, `SPEC.md`,
`HUMAN_REQUIREMENTS.md`, `BUILD_PHASES.md`, `ROADMAP.md`,
`STRIATUM_MEMORY_ROADMAP.md`, `STRIATUM_MEMORY_E2E_BACKLOG.md`,
`SOURCE_INGESTION_BACKLOG.md`, `DECISION_LOG.md`, `docs/UBIQUITOUS_LANGUAGE.md`,
and the active RFC index), then inspected the schema migrations, generated
schema docs, source contracts, major Python modules, CLI/Make targets, MCP
surface, and tests.

I did not run the full test suite. This report is a doc-only architecture
artifact.

## Executive Summary

Engram's best architectural choice is also its most unusual one: it treats
personal memory as evidence first and model output second. The raw evidence ->
claims -> beliefs split is the correct foundation for a local-first personal
memory system. The bitemporal belief model, append-only posture, model/prompt
versioning, privacy-tier defaults, and explicit no-egress principle all align
with the stated ambition: a time-indexed biography of one human life that
survives model churn and remains owned by the subject.

If I were inheriting this system, I would keep those principles. I would also
keep PostgreSQL/pgvector as the first storage and retrieval substrate, at least
until measurements force a split. The project is still comfortably inside the
range where boring local infrastructure is an advantage.

The main architectural risk is that the implementation is becoming an
ingestion and review platform before the primary product surface exists.
`context_for(conversation)` is still the promised product boundary, but recent
work has expanded source ingestion, Striatum memory, packet building, review
surfaces, and operational gates faster than it has closed the context-serving
loop. That is understandable given the repo's working style, but the next
architectural forcing function should be end-to-end context usefulness, not
another source family.

The second risk is shape drift. The architecture describes a clean layer model,
but the implementation is starting to encode source-specific retrieval and
projection behavior directly in large modules. `src/engram/cli.py` is about
2600 lines, `extractor.py` about 3150, `segmenter.py` about 1923, and
`memory.py` about 1398. That is not automatically bad, but it is evidence that
the codebase now has real bounded contexts that should be reflected in package
structure and contracts.

My greenfield architecture would still be local-first and Postgres-centered,
but it would start with a more explicit evidence catalog, projection registry,
derivation job system, policy engine, and memory-hit contract. I would make
Striatum/project memory an application of Engram rather than a peer concern
inside the core retrieval service. I would also make OS-level no-egress
execution a first-class runtime wrapper rather than mostly a documented
principle plus tests.

## What Engram Is Optimizing For

The project is not merely optimizing for chat continuity. The load-bearing
goals I infer are:

1. A local, queryable, time-indexed biography of one person.
2. Raw evidence that outlives every model, prompt, and derivation strategy.
3. Context packages that improve downstream AI interactions without becoming
   an opaque remote memory service.
4. Honest uncertainty: confidence, provenance, gaps, contradictions, and stale
   facts must surface, not disappear.
5. Strict separation between corpus access and network egress.
6. A local application-memory boundary for Striatum/project artifacts without
   allowing that boundary to read personal memory by default.

The current system honors these goals better than most personal-memory designs
would. The design does not confuse a model's summary with ground truth. It is
also unusually explicit about the user's threat model, which matters because a
complete personal biography is qualitatively more sensitive than a notes app.

## Current Architecture As I Understand It

The core pipeline is:

```text
local source artifacts
  -> immutable raw evidence
  -> topic segments and embeddings
  -> LLM-extracted claims
  -> deterministic bitemporal beliefs
  -> entity/review/current-belief projections
  -> context packages, packets, snapshots, feedback
```

Implemented or partially implemented areas:

- Raw ingestion for ChatGPT, Claude, Gemini, Striatum bundles, git metadata,
  build artifacts, and Markdown trees.
- Segmentation and embedding over the AI-conversation corpus.
- Claim extraction and deterministic belief consolidation.
- Gold-label interview CLI/web surfaces.
- Phase 4 current-belief/entity/review scaffolding.
- Striatum read-only memory search, exact-reference projection, packet
  building, MCP stdio tools, and packet audits.
- Source-contract discipline and source-ingestion gates for git/build/Markdown.

Not yet implemented as the primary product loop:

- Personal `context_for(conversation)`.
- `memory_events`, `context_snapshots`, and `context_feedback` migrations.
- Belief embeddings and multi-lane context ranking/packing.
- The user-authored gold set as the binding quality oracle.
- OS-enforced no-egress runtime as a normal operator command.

## What I Would Keep

**The raw/claim/belief separation.** This is the most important design choice.
It prevents the common failure mode where summaries become evidence and then
future summaries cite those summaries as fact.

**Bitemporal belief modeling.** `valid_from` / `valid_to` plus
`observed_at` / `recorded_at` is exactly the right shape for biography. The
system should know when something was true, when it learned it, and when it
stopped believing it.

**Non-destructive derivation.** Segment generations, extraction versions,
embedding versions, audit rows, and supersession are worth the operational
complexity. This is how the corpus survives model upgrades.

**Postgres-first local infrastructure.** Postgres, plain SQL migrations,
pgvector, local model runtimes, and pytest are appropriate for this phase.
A graph database, distributed cache, hosted search service, or remote reranker
would be premature.

**No LLM reranker in the live path for V1.** The weighted scorer is the right
default until evals prove otherwise. Inspectability matters more than theoretical
ranking elegance at this stage.

**Source contracts.** RFC 0050's "declare the raw boundary and projection
families before writing an adapter" is a good governance pattern. This should
become more formal, not less.

**Tenant/corpus boundaries.** The current local `tenant_id` / `corpus_id`
model is not hosted multi-tenancy, but it is useful local capability scoping.
The Striatum boundary should stay explicit.

## Architectural Concerns

### 1. The Primary Product Surface Is Still Missing

The docs correctly say `context_for(conversation)` is the product. The code has
good pieces for it, but the actual personal context compiler is not there yet.
That means the project is still validating substrates rather than validating
memory usefulness.

This matters because the only external truth test is whether the next assistant
gets better. More source adapters can increase possible recall, but they also
increase policy, provenance, privacy, and ranking complexity before the system
has a live feedback loop.

What I would do:

- Freeze new source-family expansion until a thin `context_for` vertical slice
  exists.
- Implement a minimal read-only context compiler over `current_beliefs`, pinned
  beliefs, exact-reference/project packets, and explicit gaps.
- Use that slice to drive the first useful evals before broadening ingestion.

### 2. The Core Package Has Outgrown Its Physical Shape

The code has real contexts now, but they are still mostly flat under
`src/engram`. The strongest signs are module size and mixed responsibilities:

- `cli.py` owns parser construction, command routing, phase orchestration, and
  presentation.
- `memory.py` owns token authorization, lexical retrieval, exact-reference
  joins, packet building, citations, packet audits, freshness logic, and
  reference encoding.
- `segmenter.py` and `extractor.py` each combine prompt construction, model
  clients, retries, parsing, persistence, diagnostics, and worker loops.

The architecture docs already describe bounded contexts. I would make those
boundaries visible in code:

```text
engram.ingest.*
engram.derive.segment.*
engram.derive.extract.*
engram.belief.*
engram.entity.*
engram.retrieve.*
engram.serve.*
engram.eval.*
engram.policy.*
engram.adapters.*
```

This is not a call for a broad refactor tomorrow. It is a direction: new code
should stop adding responsibilities to the existing large modules unless the
change is local and temporary.

### 3. Source-Specific Tables Are Becoming A Second Raw Model

The canonical raw evidence layer is described as `sources`, `conversations`,
`messages`, `notes`, and `captures`. Newer source-ingestion work adds
family-specific tables such as `git_commits`, `build_artifacts`, and
`markdown_files`. Those tables are append-only or mostly append-only, which is
good, but they do not all fit cleanly into the original raw-evidence vocabulary.

This is the early sign of a broader issue: a complete biography will produce
many source-specific tables unless there is a generic evidence catalog.

I would introduce a common envelope before adding many more source families:

```text
source_runs
evidence_items
evidence_blobs
evidence_refs
projection_generations
projection_items
reference_index
source_audits
```

Then source-specific tables become optimized projections, not the only way to
address evidence. This would also make retrieval and packet code stop caring
whether a result came from Striatum, git, Markdown, a calendar, or a future
health import.

### 4. The Memory Hit Contract Is Not Uniform

`SearchHit.to_json()` returns a packet-ready shape with `reference_id`,
`sub_kind`, `privacy_tier`, `provenance`, `freshness`, and
`dirty_working_tree`. The packet builder assumes that shape. But the
project-execution exact-reference path returns dictionaries from git,
build-artifact, and Markdown lookups that do not include the same fields.

Evidence:

- `MemoryService.build_packet()` reads `hit["reference_id"]`,
  `hit["privacy_tier"]`, and related fields in `src/engram/memory.py`.
- `_search_exact_refs()` combines Striatum hits and project-execution hits.
- `_lookup_git_commits()`, `_lookup_build_artifacts_by_hash()`,
  `_lookup_build_artifacts_by_run()`, and `_lookup_markdown_files_by_path()`
  return a different shape.

This is more than a bug. It is an architectural contract leak. Search results,
packets, citations, audits, and fetch-by-reference need one typed result model
for every retrieval lane.

What I would do:

- Define a single `MemoryHit` / `ReferenceHit` dataclass.
- Make every retrieval lane return that shape.
- Encode project references with `reference_id`s, not only raw table ids.
- Add packet-builder tests for git, build-artifact, and Markdown exact refs.

### 5. No-Egress Is A Principle More Than A Runtime Product

The docs correctly treat no-egress as structural. The code has useful checks:
loopback model endpoint validation, loopback UI binds, local assets, and
socket-monkeypatch tests for importers. That is not the same as OS-level
enforcement.

For this project, "no outbound calls in this code path" is not enough. A future
LLM worker, parser dependency, subprocess, or local tool integration can drift.
The no-egress runtime should be an executable product surface.

What I would add:

```text
engram no-egress run -- <command>
engram no-egress probe
make no-egress-smoke
```

On Linux, that should use a network namespace/firewall/seccomp/Landlock-style
strategy. The exact mechanism can be modest at first, but it should produce a
machine-readable attestation used by pipeline gates and visible in operator
surfaces.

### 6. Documentation Authority Is Drifting

Several docs are intentionally canonical, but status has moved fast:

- `docs/schema/README.md` is generated and does not include newer migrations
  017-020. `OPERATOR_REPORT.md` explicitly notes that `make schema-docs` was
  not run after those migrations.
- `docs/rfcs/README.md` marks RFC 0050 as `accepted_as_design_reference`, while
  the RFC 0050 header still says `Status | proposal`.
- Some roadmap/backlog text still describes already-landed layers as future or
  partially stale.

This is expected in a fast-moving repo, but it directly affects architecture
review because the repo relies on docs as governance. I would make "authority
lint" a first-class gate:

- generated schema docs match current migrations;
- RFC header status matches RFC index status;
- accepted decisions referenced by source contracts exist;
- OPERATOR_REPORT current summary does not contradict ROADMAP current step.

### 7. Dependency Declaration Is Incomplete

`src/engram/source_contract.py` and `src/engram/markdown_import.py` import
`yaml`, but `pyproject.toml` only declares `psycopg` as a runtime dependency
and does not declare PyYAML in the dev extras either. PyYAML happens to exist
in the current `.venv`, but `pip show PyYAML` reports no packages requiring it.

That is a reproducibility hole. It is small, but it cuts against the project's
"boring local infrastructure" discipline.

### 8. Source Audit Does Not Yet Audit Failed Invocations

`source_audits` has an `outcome` vocabulary that includes `failed`, but the
three importers I inspected call `record_source_audit()` inside the successful
import transaction after doing the main work. If an importer fails before that
point, the invocation leaves no durable audit row.

That may be acceptable for Layer 6, but the table name and enum imply stronger
coverage. A production-grade audit trail should distinguish:

- invocation started;
- source read failed;
- parse failed;
- transaction aborted;
- import completed with rows inserted/skipped/tombstoned.

Append-only audit can support this by inserting a "started" row outside the
main transaction and appending a completion row, or by writing a separate
failure row after rollback.

### 9. Entity Resolution Is Too Late For The Long Arc

Deferring rich entity canonicalization until after claims/beliefs was the right
V1 sequencing choice. For the long-arc biography, entity identity becomes
central much earlier. Names, relationships, addresses, doctors, schools,
companies, places, and family members all change over time and collide across
source systems.

The current deterministic entity pass is a useful smoke layer, not a durable
identity system. Greenfield, I would model identity as its own ledger:

```text
entities
entity_aliases
entity_observations
entity_merge_events
entity_split_events
entity_external_ids
entity_review_tasks
```

Every alias and merge should cite evidence. Human review should be normal, not
exceptional, for high-impact people/places/organizations.

### 10. Privacy Needs Policy, Not Just Columns

`privacy_tier` is correctly pervasive. Newer source work also introduces
`sensitivity_class`. The next step is a policy engine that every retrieval,
packet, context compiler, export, and UI route calls before rendering content.

Right now, privacy enforcement is partly table constraints, partly route code,
partly token capability checks, and partly convention. That is reasonable for
V1, but broad biography sources will need centralized policy decisions:

```text
policy_input = actor + tenant/corpus + source_kind + sensitivity + tier + purpose
policy_output = allow | withhold | redact | cite_only | aggregate_only
```

The system should persist withheld/omitted decisions because missing material
is semantically meaningful. "No data" and "withheld due to policy" are not the
same answer.

### 11. Materialized Projections Need Event Discipline

`current_beliefs` is a materialized view and refresh is explicit. That is fine
for Phase 4 smoke. It will be brittle for serving unless refresh/invalidation
is driven by `memory_events` or an equivalent event ledger.

The architecture docs already call for `memory_events` and
`context_snapshots`. I would implement the event contract before adding
non-trivial `context_for` caching. Otherwise stale current-belief and packet
state will become hard to reason about.

### 12. Large Binary/Life Sources Need A Different Storage Boundary

Postgres is the right control plane. It should not become the raw byte store
for full photo libraries, audio, video, OCR-heavy documents, medical PDFs, or
large logs.

Greenfield, I would use:

- encrypted content-addressed blob storage on local disk;
- Postgres metadata, hashes, refs, policy labels, and derivation state;
- deterministic extraction/projection jobs over blobs;
- deletion/destruction semantics for Tier 5 material at the key layer.

This is not urgent for current sources. It is urgent before multimodal and
health/finance/media ingestion.

## Greenfield Architecture

If I were building Engram from scratch with the current requirements, I would
use this architecture:

```text
                 no-egress runtime boundary
                         |
local source adapters -> evidence vault -> evidence catalog
                         |                 |
                         |                 v
                         |          projection registry
                         |                 |
                         v                 v
                 derivation job system -> claims -> beliefs
                                           |        |
                                           v        v
                                      entities   policy engine
                                           |        |
                                           v        v
                                  retrieval index + reference index
                                           |
                                           v
                               context compiler / packet builder
                                           |
                                           v
                                  MCP/API/UI/eval feedback
```

### 1. Evidence Vault

The evidence vault stores immutable source artifacts and content blobs. It is
local, encrypted, content-addressed, and append-only.

Postgres stores metadata:

```text
evidence_items(
  id,
  tenant_id,
  corpus_id,
  source_kind,
  source_instance_id,
  item_identity,
  logical_identity,
  source_run_id,
  observed_at,
  recorded_at,
  valid_from,
  valid_to,
  privacy_tier,
  sensitivity_class,
  content_hash,
  blob_uri,
  text_excerpt,
  raw_payload,
  lifecycle_state
)
```

The vault stores bytes and text bodies when bodies are too large or sensitive
for convenient Postgres storage.

### 2. Source Registry And Contracts

I would keep YAML source contracts initially, but load them into a
`source_contracts` table at migration or validation time. The runtime does not
need every field on day one, but the database should know which source kinds
exist and which policies apply.

I would avoid a long-term Postgres enum for rapidly growing `source_kind`.
Enums are good for genuinely static vocabularies. Source kinds are a plugin
surface. A registry table plus check/foreign-key discipline scales better once
the project moves past a handful of adapters.

### 3. Projection Registry

Every derived table or index should have the same generation contract:

```text
projection_generations(
  id,
  projection_family,
  source_contract_version,
  code_version,
  input_signature,
  status,
  activated_at,
  superseded_at
)

projection_items(
  id,
  generation_id,
  evidence_item_id,
  projection_family,
  item_kind,
  item_key,
  content_hash,
  observed_at,
  privacy_tier,
  sensitivity_class,
  payload
)
```

High-volume families can still get specialized tables. The generic projection
item gives retrieval, audits, rebuilds, and coverage gates one common handle.

### 4. Reference Index

Exact-reference retrieval should not be Striatum-specific. It should be a
generic index:

```text
reference_index(
  tenant_id,
  corpus_id,
  ref_kind,
  ref_value_normalized,
  target_kind,
  target_id,
  generation_id,
  is_active,
  privacy_tier,
  sensitivity_class
)
```

Git commit SHAs, RFC ids, file paths, calendar event ids, claim ids, artifact
ids, lab result ids, and photo ids can all live behind the same lookup contract.

### 5. Derivation Job System

`consolidation_progress` is a good early checkpoint table. Greenfield, I would
separate it into jobs, attempts, leases, and outputs:

```text
derivation_jobs
derivation_attempts
derivation_outputs
derivation_failures
```

Every job would be `(input_id, derivation_kind, version) -> output_generation`,
with deterministic idempotence and bounded retries. This would make
segmentation, embedding, extraction, projection, entity resolution, and
context-snapshot refresh use the same operational semantics.

### 6. Belief Ledger

I would keep Engram's current belief design but make the status transitions
more explicitly event-sourced:

```text
beliefs              -- current row state for query efficiency
belief_events         -- append-only transition log
belief_evidence_links -- normalized evidence references
belief_claim_links    -- normalized claim references
belief_conflicts      -- contradictions/conflict sets
```

Arrays are acceptable in the current implementation. For greenfield long-term
queries, normalized link tables make cross-source provenance, evidence coverage,
and deletion/key-destruction policy easier.

### 7. Entity Identity Service

Entity resolution should be a service boundary, not only a table set. It should
own canonical ids, aliases, merges, splits, review tasks, and external ids.

No derived belief should be forced to wait for perfect entity resolution, but
retrieval and context packing should be able to ask the identity service:

```text
resolve_mentions(text) -> candidate entity ids with confidence
entity_neighborhood(entity_id, policy, max_depth) -> cited edges
```

### 8. Retrieval And Context Compiler

I would split retrieval into lanes but unify outputs:

```text
lane -> MemoryHit[]
MemoryHit -> policy decision -> context item candidate
context item candidate -> ranking -> section packing -> rendered context
```

Every `MemoryHit` needs:

- stable `reference_id`;
- evidence/projection target;
- content or cite-only marker;
- temporal labels;
- confidence;
- privacy/sensitivity labels;
- source authority;
- freshness;
- omission/withholding reason when excluded.

### 9. Policy Engine

The policy engine should be callable from every surface:

```text
authorize(actor, purpose, item_labels) -> allow/redact/withhold/cite_only
```

It should be boring code, not an LLM. It should also emit policy-decision audit
rows for withheld or redacted material where that does not leak the content
itself.

### 10. Applications

I would make these separate applications over the same core:

- Personal context compiler: `context_for(conversation)`.
- Striatum/project memory packet builder.
- Gold-set/eval workbench.
- Belief/entity review UI.
- Future daily biography compiler.

This keeps Striatum-specific concerns from creeping into the personal memory
core while still letting Striatum dogfood Engram heavily.

## Functionality I Would Add

### Minimal Personal `context_for`

Ship the smallest useful version:

- input: current conversation text or task summary;
- lanes: pinned beliefs, current beliefs lexical/semantic, recent signals,
  exact refs, gaps;
- output: sectioned markdown with confidence and citations;
- feedback: useful/wrong/stale/irrelevant on emitted items.

Do not wait for perfect entity resolution or graph expansion.

### Gold-Set Eval Runner

The interview UI helps author labels, but the system still needs the eval loop
that makes those labels operational:

- compile context for a gold prompt;
- compare expected facts, stale suppressions, and required gaps;
- record precision/recall/stale/unsupported/token-waste metrics;
- track result deltas by prompt/model/version.

This is the project's actual objective function.

### Unified Packet Builder For All Sources

Extend packet building beyond Striatum only after the hit contract is unified.
Packets should be able to include personal/project/git/build/Markdown evidence
with the same citation and omission semantics.

### OS-Level No-Egress Runner

Make no-egress an executable wrapper and gate:

- `engram no-egress probe`;
- `engram no-egress run -- engram phase3 extract --limit 1`;
- CI/local tests that prove non-loopback network attempts fail;
- UI/CLI health field that says whether the current process is sandboxed or
  only conventionally local.

### Entity Review Workbench

Before broad life ingestion, build a focused identity UI:

- merge/split aliases;
- mark "not same person";
- attach external ids;
- inspect all evidence for an entity;
- show confidence and source distribution;
- require evidence for entity merges.

### Privacy/Sensitivity Dashboard

Add an operator surface that answers:

- What Tier 2+ material is retrieval-visible?
- Which sources contain secret-shaped or high-sensitivity content?
- Which packets withheld material and why?
- Which source families are extraction-eligible?
- Which policies are default-on for each tenant/corpus?

### Backup And Key Management Design

The human requirements make encrypted backup and posthumous handoff
load-bearing. I would not postpone the design too far. At minimum, define:

- local encrypted backup format;
- key hierarchy;
- Tier 5 destruction mechanism;
- restore test;
- dead-man's-switch policy as a local/offline runbook.

### Data Quality And Coverage Dashboard

Add a read-only dashboard for:

- extraction failures;
- accounted-zero rates;
- stale projections;
- unrefreshed materialized views;
- source-audit failures/gaps;
- unembedded active segments;
- beliefs without entity links;
- contradictions by age and severity.

This is the operational counterpart to "refusal of false precision."

## Near-Term Execution Order I Recommend

1. Repair operational drift:
   - add direct PyYAML dependency;
   - regenerate schema docs;
   - align RFC 0050 header status with the index/decision log;
   - update stale backlog text now that Layers 1-6 landed.

2. Fix the retrieval result contract:
   - one hit shape across Striatum, git, build artifacts, and Markdown;
   - packet-builder tests for project-execution exact refs;
   - `fetch_reference()` support for non-capture references or a generic
     reference resolver.

3. Implement the no-egress runner/probe:
   - make D020 demonstrable at runtime;
   - use it in at least one importer/projection/serving smoke.

4. Ship a thin personal `context_for`:
   - no LLM reranker;
   - no graph backend;
   - current/pinned beliefs, exact refs, recent signals, gaps, citations.

5. Author and run the first gold-set eval:
   - even 25 entries is enough to start falsifying ranking and extraction.

6. Refactor only along active change lines:
   - create `engram.retrieve`, `engram.policy`, `engram.ingest`, and
     `engram.derive` packages as new work lands;
   - avoid a cosmetic file move that does not reduce coupling.

7. Build the event contract:
   - `memory_events`;
   - context snapshot invalidation;
   - materialized view refresh policy;
   - feedback events.

8. Revisit source expansion after eval data:
   - add the next source only when it answers a gold-set gap or a repeated real
     context failure.

## What I Would Do Differently From The Existing Architecture

I would still build Engram. I would not change the moral center of the system.
Local-first, raw evidence, provenance, bitemporal validity, and no-egress are
the right foundation.

I would change the sequencing and some physical boundaries:

- Build `context_for` earlier, even if primitive, because it is the only real
  product test.
- Establish a generic evidence item and reference index before source families
  multiply.
- Treat Striatum/project memory as an application over Engram, not a shape that
  the core memory service special-cases.
- Make policy and no-egress executable subsystems rather than mostly
  principles plus scattered checks.
- Move from large phase modules toward bounded packages as each area changes.
- Keep generated products forbidden until the generated-product contract exists.
- Introduce encrypted blob storage before media, health, finance, or large
  document bodies enter the system.

## Bottom Line

The architecture is directionally strong and unusually principled. Its largest
asset is the refusal to let model output become ungrounded memory. Its largest
liability is that implementation momentum is currently ahead of the primary
serving/eval loop.

The next best architecture move is not a bigger graph, a better model, or more
source adapters. It is a narrow, cited, no-egress `context_for` path that can be
judged against a human-authored gold set. Once that loop exists, the rest of the
architecture has a real objective function. Without it, the project can keep
getting more impressive while remaining hard to prove useful.
