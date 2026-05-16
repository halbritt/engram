# Architecture Recommendation Execution Plan

Date: 2026-05-16
Source assessment: `ARCHITECTURE_ASSESSMENT_2026-05-16.md`
Purpose: turn the architecture recommendations into an ordered, testable work
plan.

## Execution Principle

Do not expand the source surface again until Engram has a thin, cited,
no-egress `context_for` path and at least one useful eval loop. The current
architecture already has enough substrate to test the product promise. The next
work should make usefulness measurable.

## Success Definition

This plan is complete when:

1. The repo's docs, schema docs, dependencies, and RFC status agree with the
   current code.
2. Retrieval returns one uniform hit shape across Striatum, git, build-artifact,
   and Markdown sources.
3. Packet building and reference fetching work for all supported exact-reference
   sources.
4. A normal operator command can run corpus-reading work inside an OS-level
   no-egress boundary or report that the boundary is unavailable.
5. `context_for(conversation)` exists as a minimal personal context compiler.
6. The first gold-set eval runner can score `context_for` output against
   human-authored expected facts, stale suppressions, and required gaps.
7. Future work is guided by eval failures rather than by source-adapter
   availability alone.

## Guardrails

- Keep raw evidence immutable.
- Keep corpus-reading processes no-egress.
- Do not introduce hosted APIs, telemetry, hosted vector stores, remote
  embedding, or remote reranking.
- Do not add generated memory products until the generated-product contract is
  accepted.
- Treat Striatum/project memory as an application over Engram, not the shape of
  the personal-memory core.
- Prefer small landed increments with tests over large architecture rewrites.

## Phase 0: Freeze And Baseline

Goal: establish a known starting point and prevent scope from drifting while the
serving/eval loop is built.

### Steps

1. Record this plan as the active architecture-followup plan.
2. Add a short note to `OPERATOR_REPORT.md` pointing to this plan.
3. Decide that Stage 3+ source families from RFC 0050 remain deferred until
   Phase 5 of this plan is complete.
4. Run the current verification baseline:
   - `git status --short`
   - `git diff --check`
   - `make test`
   - `make eval-gates`
   - `make eval-source-ingestion-gates`
   - `make e2e-striatum`
5. Save the command results in an operational report if any baseline is
   red/yellow.

### Acceptance Criteria

- The operator can identify the baseline commit and test status.
- Any pre-existing failures are recorded and separated from new work.
- New source-family work is explicitly out of scope until `context_for` and the
  first eval loop exist.

### Human Checkpoint

Confirm whether this plan should become the active roadmap supplement. If yes,
update `ROADMAP.md` or `OPERATOR_REPORT.md` with a one-line pointer rather than
copying the whole plan.

## Phase 1: Repair Operational Drift

Goal: make repo authority match the code before building more.

### Steps

1. Add `PyYAML` as a direct runtime dependency in `pyproject.toml`.
   - Rationale: `source_contract.py` and `markdown_import.py` import `yaml`.
   - Test: fresh install or import smoke for both modules.

2. Regenerate schema docs.
   - Run `make schema-docs`.
   - Verify `docs/schema/README.md` includes migrations 017-020 tables:
     `git_commits`, `git_commit_paths`, `build_artifacts`,
     `build_artifact_findings`, `markdown_files`, `markdown_file_chunks`,
     `markdown_file_links`, and `source_audits`.

3. Align RFC status metadata.
   - Update RFC 0050 header status from `proposal` to
     `accepted_as_design_reference`, matching `docs/rfcs/README.md` and D084.
   - Check RFC 0046-0049 headers for the same index/header drift.

4. Reconcile stale backlog/report text.
   - Mark landed portions of `SOURCE_INGESTION_BACKLOG.md` as completed or
     superseded by D084.
   - Mark landed portions of `STRIATUM_MEMORY_E2E_BACKLOG.md` as completed or
     split out remaining gate/runbook work.
   - Keep historical OPERATOR_REPORT sections intact, but make the current
     summary unambiguous.

5. Add a lightweight authority-lint script or checklist.
   - Minimum first version can check:
     - generated schema docs mention all current migration tables;
     - RFC index status and RFC header status match for accepted references;
     - runtime imports are declared in `pyproject.toml`.

### Acceptance Criteria

- `make test` passes or any failures are unrelated and recorded.
- `git diff --check` passes.
- `docs/schema/README.md` reflects current schema.
- RFC 0050 and index status no longer contradict each other.
- PyYAML is no longer an undeclared runtime dependency.

## Phase 2: Unify The Retrieval Result Contract

Goal: make every retrieval lane return a single typed hit shape that packet
building, citations, audits, and reference fetching can rely on.

### Steps

1. Define a single retrieval hit model.
   - Proposed name: `MemoryHit` or `ReferenceHit`.
   - Required fields:
     - `reference_id`
     - `tenant_id`
     - `corpus_id`
     - `source_kind`
     - `sub_kind`
     - `external_id`
     - `content`
     - `score`
     - `privacy_tier`
     - `sensitivity_class`
     - `provenance`
     - `freshness`
     - `dirty_working_tree`
     - `observed_at`
     - `imported_at`
     - `target_table`
     - `target_id`

2. Replace ad hoc dict returns in project-execution exact-reference lookups.
   - `_lookup_git_commits`
   - `_lookup_build_artifacts_by_hash`
   - `_lookup_build_artifacts_by_run`
   - `_lookup_markdown_files_by_path`

3. Extend reference id encoding.
   - Current `fetch_reference()` only supports `captures`.
   - Add support for:
     - `git_commits`
     - `build_artifacts`
     - `markdown_files`
   - Ensure every encoded reference re-authorizes tenant/corpus before reading.

4. Normalize citation construction.
   - `build_packet_citation()` should work for all hit kinds.
   - Citations should include stable source fields such as path, commit SHA,
     run id, artifact hash, or markdown root/path when available.

5. Add packet-builder tests for project-execution sources.
   - Build packet by commit SHA.
   - Build packet by build-artifact hash.
   - Build packet by run id.
   - Build packet by markdown path.
   - Verify packet audit rows do not contain raw body content.
   - Verify `fetch_reference()` returns the same reference after
     re-authorization.

6. Split retrieval code if touched heavily.
   - Create `src/engram/retrieve/` only if it reduces local complexity during
     this phase.
   - Do not perform a cosmetic full-module move.

### Acceptance Criteria

- `MemoryService.search(... exact_refs=...)` returns one shape for Striatum,
  git, build artifacts, and Markdown.
- `MemoryService.build_packet()` works for every exact-reference source.
- `fetch_reference()` supports every reference id emitted by search.
- Cross-tenant and cross-corpus checks still fail closed.
- `make test`, `make eval-gates`, and `make eval-source-ingestion-gates` pass.

## Phase 3: Make No-Egress Executable

Goal: move D020 from principle/test convention toward an operator-visible
runtime boundary.

### Steps

1. Add a no-egress module.
   - Proposed package: `src/engram/no_egress.py`.
   - Responsibilities:
     - detect platform support;
     - run a probe;
     - run a subprocess under the best available no-egress mechanism;
     - produce a machine-readable result.

2. Add CLI commands.
   - `engram no-egress probe`
   - `engram no-egress run -- <command>`

3. Implement Linux first.
   - Preferred mechanisms, in order of practicality:
     - `unshare` network namespace where available;
     - `bwrap`/bubblewrap if installed;
     - deny-by-default firewall wrapper if available;
     - clear `unsupported` result when none is available.
   - The command must not pretend to enforce no-egress if enforcement is not
     active.

4. Add tests.
   - Unit test command construction.
   - Probe test that non-loopback connection attempt fails in enforced mode.
   - Fallback test returns `unsupported` without failing on platforms that lack
     the mechanism.

5. Wire one smoke target.
   - Add `make no-egress-smoke`.
   - First smoke can run a small Python socket attempt under the wrapper.
   - Later smokes can run an importer or context compiler under the wrapper.

6. Surface status in local UIs and health output.
   - Distinguish:
     - `egress_enforced`
     - `local_only_convention`
     - `unsupported`
     - `unknown`

### Acceptance Criteria

- `engram no-egress probe` returns JSON with enforcement status.
- Enforced mode blocks a non-loopback socket attempt.
- Unsupported mode is explicit and non-misleading.
- No existing loopback-only local model/Postgres flows are broken.
- At least one corpus-reading smoke runs under the wrapper or reports why it
  cannot.

## Phase 4: Build Minimal Personal `context_for`

Goal: ship the smallest useful context compiler over existing personal memory
substrates.

### Steps

1. Define the request and output contracts.
   - Proposed request:
     - `query_text`
     - optional `conversation_id`
     - optional `tenant_id='personal'`
     - optional `corpus_id='personal'`
     - token budget
     - privacy tier ceiling
   - Proposed output:
     - `context_id`
     - `compiler_version`
     - `status`
     - `sections`
     - `citations`
     - `omissions`
     - `source_belief_ids`
     - `source_segment_ids`
     - `source_reference_ids`

2. Implement lane interfaces.
   - Start with deterministic lanes:
     - pinned beliefs;
     - current beliefs lexical match;
     - recent captures/recent signals;
     - exact-reference hits when query contains obvious refs;
     - missing-data/gaps.
   - Defer:
     - LLM reranking;
     - graph expansion beyond simple entity lookup;
     - broad semantic belief search if belief embeddings are not ready.

3. Implement section packing.
   - Initial sections:
     - Standing Context
     - Relevant Beliefs
     - Recent Signals
     - Raw Evidence Snippets
     - Uncertain / Conflicting
     - Missing Data / Gaps
   - Enforce token or word-budget approximations.
   - Include `(conf=..., src=...)` style tags where applicable.

4. Add privacy policy checks.
   - Use current tier ceiling rules initially.
   - Emit `withheld_due_to_policy` rather than pretending no data exists.

5. Add CLI.
   - `engram context-for --query "..." --tenant personal --corpus personal`
   - `engram context-for --query-file path`
   - JSON and markdown output modes.

6. Add MCP tool only after CLI behavior is stable.
   - Proposed tool: `engram.context_for`.
   - Keep Striatum packet tools separate.

7. Add tests.
   - Current belief included with citation.
   - Pinned belief appears in Standing Context.
   - Stale/superseded belief is omitted or historically labeled.
   - No-data query emits explicit gap.
   - Policy-withheld material is not rendered as no-data.
   - Token budget truncates low-priority items first.

### Acceptance Criteria

- `engram context-for --query ...` returns a sectioned context package from a
  seeded test corpus.
- Every included memory item has provenance and confidence where available.
- Missing data and withheld data are distinguishable.
- No live LLM call is required.
- No network egress is required.
- `make test` passes.

## Phase 5: Build The First Gold-Set Eval Loop

Goal: make `context_for` measurable against human-authored expected behavior.

### Steps

1. Define the eval item schema.
   - Fields:
     - prompt/query;
     - required facts;
     - forbidden stale facts;
     - required gaps;
     - relevant entities;
     - allowed evidence references;
     - privacy ceiling;
     - notes from the human.

2. Convert or reuse existing gold-label material.
   - Do not auto-generate the gold set from extracted beliefs.
   - The human's real expected answer is the source of truth.

3. Implement eval runner.
   - Proposed command:
     - `engram eval context --gold-set path.jsonl --output report.json`
   - Runner compiles context for each prompt and scores:
     - required fact recall;
     - unsupported fact rate;
     - stale fact rate;
     - required gap emission;
     - citation coverage;
     - token waste approximation.

4. Add report renderer.
   - JSON for machines.
   - Markdown summary for review.
   - Store reports under `docs/reviews/context-eval/<date>/`.

5. Add first small fixture eval.
   - Use synthetic or non-private fixture rows.
   - Do not depend on private corpus content in tests.

6. Run first real eval manually.
   - Human-authored 25-entry set is enough for the first loop.
   - Record failures as backlog items grouped by root cause:
     - missing ingestion;
     - retrieval miss;
     - ranking/packing issue;
     - stale belief;
     - unsupported belief;
     - privacy withholding;
     - bad extraction/consolidation.

### Acceptance Criteria

- Eval runner produces stable metrics on fixture data.
- A real private eval can be run locally without committing private outputs.
- At least one eval report exists with actionable failure categories.
- Future architecture work can point to eval failure classes, not only intuition.

### Human Checkpoint

The human must author or approve the first real gold-set entries. This is not
delegable to the model.

## Phase 6: Add Events, Snapshots, And Feedback

Goal: make context serving refreshable and auditable rather than recomputed or
manually refreshed forever.

### Steps

1. Add migrations.
   - `memory_events`
   - `context_snapshots`
   - `context_feedback`

2. Emit events from mutation points.
   - belief accept/reject/correct/promote;
   - source import completed;
   - projection generation activated;
   - entity resolution changes;
   - gold/context feedback captured.

3. Add snapshot compiler.
   - Cold compile: `context_for` generates a package.
   - Warm read: return fresh snapshot for scope.
   - Refresh: event invalidates or refreshes affected scope.

4. Add feedback capture.
   - `useful`
   - `wrong`
   - `stale`
   - `irrelevant`
   - optional correction note.

5. Add tests.
   - Belief change emits event.
   - Snapshot invalidates or refreshes after event.
   - Feedback row links to source belief/segment/reference ids.
   - Warm read matches cold compile for unchanged input.

### Acceptance Criteria

- `context_for` has a cold path and a warm snapshot path.
- Feedback lands in append-only rows.
- Stale snapshots are not silently served after relevant events.
- Phase 5 eval runner can record compiler/snapshot version.

## Phase 7: Centralize Policy

Goal: stop privacy behavior from being scattered across routes, token checks,
and conventions.

### Steps

1. Add a policy module.
   - Proposed package: `src/engram/policy/`.
   - Inputs:
     - actor/token;
     - tenant/corpus;
     - purpose;
     - privacy tier;
     - sensitivity class;
     - source kind;
     - target surface.
   - Outputs:
     - allow;
     - redact;
     - withhold;
     - cite-only;
     - deny.

2. Replace direct route/service checks incrementally.
   - Interview evidence routes.
   - Bench-review excerpt routes.
   - Memory packet builder.
   - `context_for`.

3. Persist omission/withholding where useful.
   - Make "withheld due to policy" distinct from "no data".

4. Add privacy/sensitivity dashboard.
   - Minimum read-only CLI first:
     - `engram privacy report`
   - Later web surface can reuse the same service.

### Acceptance Criteria

- Same policy decision function is used by packet and context rendering.
- Tests prove Tier 2+ material is withheld from Tier 1 surfaces.
- Omitted/withheld reasons use a closed vocabulary.
- No route regresses to ad hoc tier comparison without a test.

## Phase 8: Generalize Evidence And Reference Indexing

Goal: prepare for future biography sources without adding a bespoke retrieval
path for each one.

### Steps

1. Design a generic evidence catalog.
   - Decide whether this is a new RFC, a spec, or a direct migration plan.
   - Proposed tables:
     - `evidence_items`
     - `evidence_blobs`
     - `reference_index`
     - `projection_items`
     - `projection_generations` or a generalized equivalent.

2. Backfill current specialized sources into the generic index.
   - Striatum captures.
   - git commits.
   - build artifacts.
   - Markdown files.

3. Make exact-reference search read the generic index first.
   - Keep specialized queries as fallback while migrating.

4. Add generation and stale-index gates.
   - Dropping/rebuilding generic projection rows should reproduce active
     reference coverage.

5. Only after this, approve the next source family.

### Acceptance Criteria

- New source families can add references without editing `MemoryService` source
  kind branches.
- Existing exact-reference tests pass through the generic reference index.
- Projection rebuild gates cover all active source families.

## Phase 9: Build Entity Identity Review

Goal: make identity resolution strong enough for broader personal biography
sources.

### Steps

1. Extend entity model if needed.
   - `entity_aliases`
   - `entity_observations`
   - `entity_external_ids`
   - `entity_merge_events`
   - `entity_split_events`

2. Add deterministic candidate generation.
   - Normalize names.
   - Use source-specific external ids where present.
   - Use evidence overlap and co-occurrence as weak signals.

3. Add review surface.
   - Merge aliases.
   - Split wrong merges.
   - Mark "not same entity".
   - Attach external ids.
   - Inspect evidence.

4. Wire reviewed entities into `context_for`.
   - Mention detection can be simple at first.
   - Entity neighborhood should cite evidence.

### Acceptance Criteria

- Human-reviewed merges/splits are append-only and evidence-backed.
- `context_for` can use reviewed entities without inventing identity links.
- Entity review decisions are auditable.

## Phase 10: Backup, Keys, And Tier 5 Destruction Design

Goal: address the long-term local-first operational requirement before high-risk
life data enters the system.

### Steps

1. Write a backup/key-management design.
   - Local encrypted backup format.
   - Restore procedure.
   - Key hierarchy.
   - Recovery key handling.
   - Dead-man's-switch policy.
   - Tier 5 destruction mechanism.

2. Build restore smoke before backup automation.
   - A backup that cannot be restored is not a backup.

3. Keep cloud sync out of scope.
   - Explicit export is allowed.
   - Background third-party sync remains disallowed.

### Acceptance Criteria

- Backup design is accepted before health/finance/media bulk ingestion.
- Restore smoke exists against a non-private fixture DB/blob set.
- Tier 5 material has a credible key-destruction path.

## Phase 11: Blob Vault For Large And Sensitive Bodies

Goal: avoid turning Postgres into the raw byte store for media, audio, video,
large PDFs, and high-volume document bodies.

### Steps

1. Design encrypted local blob storage.
   - Content-addressed.
   - Local-only.
   - Hash-addressed from Postgres.
   - Supports key-tier separation.

2. Add `evidence_blobs` metadata.
   - content hash;
   - byte size;
   - media type;
   - encryption key id;
   - retention policy;
   - privacy/sensitivity labels.

3. Migrate future large-source contracts to reference blobs.
   - Do not retroactively move small existing text unless needed.

### Acceptance Criteria

- Large body ingestion can store metadata in Postgres and bytes in encrypted
  local blob storage.
- Retrieval can cite blobs without rendering unauthorized bytes.
- Tier 5 destruction can operate at key/blob level.

## Phase 12: Refactor Along Active Boundaries

Goal: reduce coupling without stopping product progress for a cosmetic rewrite.

### Steps

1. New retrieval work goes under `src/engram/retrieve/`.
2. New policy work goes under `src/engram/policy/`.
3. New context compiler work goes under `src/engram/context/`.
4. New no-egress work goes under `src/engram/no_egress.py` or
   `src/engram/runtime/`.
5. Split `cli.py` only when modifying a command group.
   - Example:
     - `engram.cli.phase1`
     - `engram.cli.phase2`
     - `engram.cli.phase3`
     - `engram.cli.memory`
     - `engram.cli.context`
6. Split `segmenter.py` / `extractor.py` only when touching active behavior.
   - Separate pure prompt/schema/parsing helpers from persistence and model
     clients over time.

### Acceptance Criteria

- No broad move-only refactor lands without behavior work.
- New packages own new boundaries.
- Tests continue to pin CLI compatibility.

## Decision Checkpoints

These require explicit operator decision before implementation proceeds:

1. Make this plan the active architecture-followup plan.
2. Accept the exact shape of `context_for` V1 output.
3. Accept the first real gold-set eval format.
4. Decide whether generic evidence/reference indexing needs an RFC or can ship
   as an implementation spec.
5. Accept backup/key-management design before high-sensitivity source families.
6. Accept generated-product contract before generated summaries, biographies,
   OCR text, captions, or daily compiler outputs become retrieval-visible.

## Suggested Work Packets

The plan can be cut into these implementation packets:

1. `P-ARCH-001`: dependency/schema/RFC/backlog drift repair.
2. `P-ARCH-002`: unified `MemoryHit` contract and project-source packet tests.
3. `P-ARCH-003`: generic `fetch_reference` for non-capture references.
4. `P-ARCH-004`: no-egress probe and wrapper.
5. `P-ARCH-005`: minimal `context_for` contract and CLI.
6. `P-ARCH-006`: context section packing and policy/gap rendering.
7. `P-ARCH-007`: gold-set eval runner.
8. `P-ARCH-008`: `memory_events`, `context_snapshots`, `context_feedback`.
9. `P-ARCH-009`: centralized policy module.
10. `P-ARCH-010`: generic reference index design and migration.

## Recommended First Three Commits

1. Drift repair:
   - PyYAML dependency;
   - schema docs;
   - RFC status alignment;
   - stale current-summary cleanup.

2. Retrieval contract:
   - `MemoryHit` dataclass;
   - all exact-reference lanes return it;
   - packet builder covers project-execution hits.

3. No-egress:
   - `engram no-egress probe`;
   - `engram no-egress run`;
   - `make no-egress-smoke`;
   - honest unsupported fallback.

After those three commits, start `context_for`.
