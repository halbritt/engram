# Architecture Execution Plan

Date: 2026-05-16
Source assessment: `ARCHITECTURE_ASSESSMENT_2026-05-16.md`

## Phase 0: Freeze And Baseline
**Goal:** Establish a known starting point and prevent scope from drifting while the serving/eval loop is built.
1. Record this plan as the active architecture-followup plan.
2. Add a short note to `OPERATOR_REPORT.md` pointing to this plan.
3. Defer Stage 3+ source families from RFC 0050 until Phase 5 is complete.
4. Run the current verification baseline (`git status`, `git diff --check`, `make test`, `make eval-gates`, `make eval-source-ingestion-gates`, `make e2e-striatum`).
5. Save the command results in an operational report if any baseline is red/yellow.

## Phase 1: Repair Operational Drift
**Goal:** Make repo authority match the code before building more.
1. Add `PyYAML` as a direct runtime dependency in `pyproject.toml`.
2. Regenerate schema docs (`make schema-docs`).
3. Align RFC status metadata (RFC 0050, 0046-0049).
4. Reconcile stale backlog/report text in `SOURCE_INGESTION_BACKLOG.md` and `STRIATUM_MEMORY_E2E_BACKLOG.md`.
5. Add a lightweight authority-lint script or checklist.

## Phase 2: Unify The Retrieval Result Contract
**Goal:** Make every retrieval lane return a single typed hit shape that packet building, citations, audits, and reference fetching can rely on.
1. Define a single retrieval hit model (e.g., `MemoryHit` or `ReferenceHit`).
2. Replace ad hoc dict returns in project-execution exact-reference lookups.
3. Extend reference id encoding to support `git_commits`, `build_artifacts`, `markdown_files`.
4. Normalize citation construction for all hit kinds.
5. Add packet-builder tests for project-execution sources.
6. Split retrieval code into `src/engram/retrieve/` if it reduces local complexity.

## Phase 3: Make No-Egress Executable
**Goal:** Move D020 from principle/test convention toward an operator-visible runtime boundary.
1. Add a no-egress module (`src/engram/no_egress.py`).
2. Add CLI commands: `engram no-egress probe` and `engram no-egress run -- <command>`.
3. Implement Linux first (`unshare`, `bwrap`, firewall wrapper).
4. Add tests for command construction, probe test, fallback test.
5. Wire one smoke target (`make no-egress-smoke`).
6. Surface status in local UIs and health output.

## Phase 4: Build Minimal Personal `context_for`
**Goal:** Ship the smallest useful context compiler over existing personal memory substrates.
1. Define the request and output contracts.
2. Implement lane interfaces (pinned beliefs, lexical match, recent captures, missing-data).
3. Implement section packing with token/word-budget approximations.
4. Add privacy policy checks and emit `withheld_due_to_policy`.
5. Add CLI: `engram context-for`.
6. Add MCP tool `engram.context_for` once CLI behavior is stable.
7. Add robust testing for citations, beliefs, missing data, and policy-withheld material.

## Phase 5: Build The First Gold-Set Eval Loop
**Goal:** Make `context_for` measurable against human-authored expected behavior.
1. Define the eval item schema.
2. Convert or reuse existing gold-label material (human-authored expected answers).
3. Implement eval runner (`engram eval context --gold-set path.jsonl --output report.json`).
4. Add report renderer for JSON and Markdown.
5. Add first small fixture eval.
6. Run first real eval manually using human-authored entries.

## Phase 6: Add Events, Snapshots, And Feedback
**Goal:** Make context serving refreshable and auditable rather than recomputed or manually refreshed forever.
1. Add migrations: `memory_events`, `context_snapshots`, `context_feedback`.
2. Emit events from mutation points (belief changes, source imports, projection generation, feedback).
3. Add snapshot compiler with cold compile, warm read, and refresh capabilities.
4. Add feedback capture (`useful`, `wrong`, `stale`, `irrelevant`).
5. Add tests validating event emissions and snapshot refreshing.

## Phase 7: Centralize Policy
**Goal:** Stop privacy behavior from being scattered across routes, token checks, and conventions.
1. Add a policy module (`src/engram/policy.py`).
2. Incrementally replace direct route/service checks.
3. Persist omission/withholding where useful.
4. Add privacy/sensitivity dashboard CLI (`engram privacy report`).

## Phase 8: Generalize Evidence And Reference Indexing
**Goal:** Prepare for future biography sources without adding a bespoke retrieval path for each one.
1. Design a generic evidence catalog (RFC required per D088).
2. Backfill current specialized sources into the generic index.
3. Make exact-reference search read the generic index first.
4. Add generation and stale-index gates.
5. Wait for the next source family based on `context_for` eval failures.

## Phase 9: Build Entity Identity Review
**Goal:** Make identity resolution strong enough for broader personal biography sources.
1. Extend entity model with aliases, observations, external IDs, and merge/split events.
2. Add deterministic candidate generation.
3. Add review surface to handle aliases and identity verification.
4. Wire reviewed entities into `context_for`.
5. Define MCP-facing grounding via an RFC before implementation.

## Phase 10: Backup, Keys, And Tier 5 Destruction Design
**Goal:** Address the long-term local-first operational requirement before durable high-risk life-data expansion.
1. Write a backup/key-management design.
2. Build restore smoke testing before backup automation.
3. Keep cloud sync out of scope, relying entirely on local mechanisms.

## Phase 11: Blob Vault For Large And Sensitive Bodies
**Goal:** Avoid turning Postgres into the raw byte store for media, audio, video, large PDFs, and high-volume document bodies.
1. Design encrypted local blob storage (hash-addressed, key-tier separated).
2. Add `evidence_blobs` metadata directly in Postgres.
3. Migrate future large-source contracts to reference blobs.

## Phase 12: Refactor Along Active Boundaries
**Goal:** Reduce coupling without stopping product progress for a cosmetic rewrite.
1. Ensure new retrieval work is placed in `src/engram/retrieve/`.
2. Place new policy work in `src/engram/policy/`.
3. Separate compiler work in `src/engram/context/` and runtime logic in `src/engram/runtime/` or `src/engram/no_egress.py`.
4. Intelligently split `cli.py` and `segmenter.py` where active behavior dictates separation.

---
**Prepared By:** Gemini CLI