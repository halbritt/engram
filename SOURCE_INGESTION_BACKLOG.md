# Source-Ingestion Expansion — Backlog Execution Plan

Date: 2026-05-15
Posture: This document operationalizes RFC 0050
([docs/rfcs/0050-source-ingestion-expansion.md](docs/rfcs/0050-source-ingestion-expansion.md))
as a sequenced execution plan, analogous to
[`STRIATUM_MEMORY_E2E_BACKLOG.md`](STRIATUM_MEMORY_E2E_BACKLOG.md). RFC 0050 is
proposal-status; this backlog treats it as design reference. Each layer ships
as one or more landed commits with tests on master before the next layer
starts.

## Snapshot Of What Already Exists

- AI-conversation importers (`chatgpt_export.py`, `claude_export.py`,
  `gemini_export.py`) and the Striatum bundle importer
  (`striatum_ingest.py`) cover the current `source_kind` values.
- The Striatum-memory e2e pipeline (Layers 1-5 of
  `STRIATUM_MEMORY_E2E_BACKLOG.md`) is on master with projection,
  retrieval, packet, gates, and MCP smoke.
- The RFC 0050 source-contract proposal landed in
  `docs/rfcs/0050-source-ingestion-expansion.md` with cross-references
  to RFC 0033-0036 and RFC 0044-0049. The proposal carries 12 open
  questions (`OQ-SI-001..OQ-SI-012`) that humans resolve in
  `DECISION_LOG.md` separately from any code work.

## Sequencing Recommendation

Execute strictly in this order; later layers assume earlier ones held.

1. Layer 1: source contract template + git metadata/diff-stat importer.
2. Layer 2: build/test/lint/coverage/benchmark artifact importer.
3. Layer 3: Markdown/project-doc importer.
4. Layer 4: `EG-SI-NNN` evaluation-gate harness for layers 1-3.
5. Layer 5: exact-reference retrieval extension for project-execution
   sources via the existing `MemoryService.search` filter path.
6. Layer 6: operational families (`coverage_gap`, `source_audit`) and
   the no-derived-product-leak invariant tests.
7. Optional Stage 3+ work (human communication, observation/life,
   live capture) lands only after operator decides per RFC 0050.

## Layer 1 — Source Contract Template + Git Importer (RFC 0050 Stage 0 + Stage 1.1)

Goal: deliver the reusable source-contract template, document its required
fields, and ship the first contract-conformant importer for local git
commit metadata and diff stats.

### Deliverables

- A documented source-contract template at
  `docs/source-contracts/README.md` mirroring the YAML shape from
  RFC 0050 § Source Contract. The template lists mandatory fields, the
  four required questions, the closed projection-family vocabulary, the
  closed operational-family vocabulary (`coverage_gap`,
  `source_audit`), and the contract-validator test set.
- Example contracts at `docs/source-contracts/git.yaml` and
  `docs/source-contracts/build_artifact.yaml` even though only `git` is
  implemented in this layer (the second example is a forward-pointer
  for Layer 2).
- A contract validator under
  `src/engram/source_contract.py` exposing
  `validate_contract(path) -> ContractValidationResult` with a closed
  error vocabulary.
- A migration that adds `source_kind='git'` to the enum.
- A git importer under `src/engram/git_import.py` that:
  - takes a local repo path;
  - reads `git log --format=...` to fetch commit metadata, parent
    links, refs (branch and tag heads), and changed paths/diff stats
    (`git log --numstat`);
  - lands rows in `sources`, `git_commits`, and `git_commit_paths`
    (new tables) under `source_kind='git'`;
  - is idempotent on re-import (no duplicate rows for the same
    `repository_id`/`commit_sha`);
  - records repository identity (root content identity + remote URL
    plus first-commit SHA) so a re-clone of the same project does not
    create a duplicate `sources` row;
  - emits `coverage_gap` rows for any commits whose body or numstat
    could not be parsed.
- Two new tables for the projection: `git_commits` and
  `git_commit_paths`. Indexes on `(repository_id, commit_sha)` and
  `(commit_sha)`.
- A CLI verb `engram import git <repo-path>` that calls the importer
  with `--dry-run`, `--allow-dirty`, and `--full-patch=false` defaults.
- Tests:
  - `test_source_contract_validator.py` — contract template, example
    contracts, error vocabulary.
  - `test_git_importer.py` — idempotent re-import on a fixture repo;
    conflict on a force-pushed branch; tombstone for a removed branch;
    no outbound network during ingest.
  - `test_git_importer_no_egress.py` — runs the importer under a
    socket-monkeypatch to assert no outbound calls.
- A small fixture git repo under
  `tests/fixtures/source_contract_git/` with two commits, one branch,
  one tag, one file rename.

### Acceptance Criteria

- `make test` passes including the four new test modules.
- `engram describe-corpus --tenant personal --corpus personal --json`
  reports `git` source kind when at least one git repo has been
  imported.
- The source contract validator rejects a contract missing any
  mandatory field with a closed error code.
- Re-importing the fixture git repo produces zero new rows.
- A fresh `engram migrate` succeeds against
  `postgresql:///engram_test`.

### Scope Kept Out Of Layer 1

- Patch bodies. Defer to a later opt-in slice per RFC 0050
  `OQ-SI-001`.
- Cross-repo deduplication. One repo at a time; the `repository_id`
  identity strategy is the work.
- Vector search or any retrieval surface (Layer 5).
- Operational families' query layer (Layer 6 makes them queryable);
  Layer 1 only writes `coverage_gap` rows when parse fails.

## Layer 2 — Build Artifact Importer (RFC 0050 Stage 1.2)

Goal: ship a contract-conformant importer for local build/test/lint
artifact directories.

### Deliverables

- Source contract at `docs/source-contracts/build_artifact.yaml`
  (started in Layer 1, finalized here).
- Importer under `src/engram/build_artifact_import.py` that walks a
  named directory and ingests:
  - JUnit XML test reports;
  - coverage JSON or XML;
  - benchmark JSON;
  - linter output (ruff JSON, eslint JSON, pyright JSON);
  - plain log files (head/tail snippets, full body opt-in only).
- Tables `build_artifacts` and `build_artifact_findings`.
- `engram import build-artifacts <dir>` CLI verb.
- Identity: artifact content hash + path + run id when present + commit
  SHA when present.
- Tests covering each artifact family + a "no JUnit, no log, just
  metadata" minimal case + a "log contains apparent secret" redaction
  case.

### Acceptance Criteria

- `make test` passes including the new test module.
- Importer never reads patch bodies from logs above a configurable
  byte limit by default.
- Re-import of the same artifact directory is idempotent.

## Layer 3 — Markdown / Project-Doc Importer (RFC 0050 Stage 2)

Goal: ship a contract-conformant importer for local Markdown trees.

### Deliverables

- Source contract at `docs/source-contracts/markdown_tree.yaml`.
- Importer under `src/engram/markdown_import.py` that walks a
  directory and ingests Markdown files with:
  - identity: `(root_id, normalized_relative_path, content_hash)`;
  - rebuildable projection of headings, frontmatter, links, tags, and
    chunk anchors;
  - file-move detection without rewriting raw rows.
- New tables `markdown_files`, `markdown_file_chunks`, and
  `markdown_file_links`.
- `engram import markdown <root>` CLI verb.
- Tests for idempotent re-import, content drift detection, file
  rename, broken link reporting.

### Acceptance Criteria

- Re-importing an unchanged directory produces zero new rows.
- File rename creates a new identity row and a tombstone for the old
  path without rewriting the old raw row.
- Heading/frontmatter/link projection rebuilds from raw evidence.

## Layer 4 — Evaluation Gates `EG-SI-NNN`

Goal: deterministic gates per RFC 0050 § Evaluation Gates that prove
each Layer 1-3 contract holds under regression.

### Deliverables

- Test module `tests/test_source_ingestion_gates.py` with one test per
  gate in scope:
  - `EG-SI-000 No-Egress` — Level A (socket monkeypatch) for all three
    importers, then a sandboxed-process Level B test for git only.
  - `EG-SI-010 Source Contract Validator` — runs the validator across
    every contract under `docs/source-contracts/` and asserts mandatory
    fields and closed vocabulary.
  - `EG-SI-020 Raw Ingest Idempotency And Conflict` — re-import is
    no-op; manifest mismatch raises.
  - `EG-SI-040 Privacy/Sensitivity/Redaction` — log redaction case
    from Layer 2.
  - `EG-SI-050 Projection Rebuild And Activation` — drop projection
    rows, rebuild, verify counts match.
  - `EG-SI-060 Exact Reference And Citation` — exact lookup by
    `commit_sha`, file path, artifact hash returns the right rows.
  - `EG-SI-080 Coverage, Gaps, And Lifecycle` — disabled source emits
    `coverage_gap`; removed branch tombstoned.
  - `EG-SI-100 Source-Family Fixture Matrix` — every Layer 1-3 family
    has at least one positive, negative, and malformed fixture.
- `make eval-source-ingestion-gates` Makefile target.

### Acceptance Criteria

- `make eval-source-ingestion-gates` exits 0 on master.
- Each gate has a named pytest function.
- Failing any gate is a CI-style regression.

### Out Of Scope For Layer 4

- `EG-SI-030 Tenant/Corpus/Source Isolation` — covered by retrieval
  layer; defer to Layer 5.
- `EG-SI-070 Extraction Eligibility` — only applicable once Stage 3
  human-communication sources land; defer.
- `EG-SI-090 Audit Reconstruction` — defer to Layer 6.

## Layer 5 — Exact-Reference Retrieval Extension (RFC 0050 Stage 1 success criterion)

Goal: surface git/build-artifact projections behind the existing
`MemoryService.search` `filters.exact_refs` API the Striatum-memory
work already established (`STRIATUM_MEMORY_E2E_BACKLOG.md` Layer 2).

### Deliverables

- Extend the `ref_kind` vocabulary on the projection to include
  `commit_sha`, `repo_path`, `run_id`, `artifact_hash`, and
  `failure_signature`.
- Wire `MemoryService.search` so that an `exact_refs` filter with
  these kinds returns rows from the project-execution projections,
  not just Striatum captures.
- Add tests under `tests/test_memory_service_exact_refs_git.py` and
  `..._build_artifacts.py`.

### Acceptance Criteria

- Exact-reference search for a known `commit_sha` returns the right
  commit row.
- The existing Striatum exact-reference tests still pass.
- No vector search is introduced in Layer 5.

## Layer 6 — Operational Families + No-Derived-Product-Leak

Goal: make `coverage_gap` and `source_audit` queryable as operational
families per RFC 0050 § Operational Families, and prove the
no-derived-product-leak invariant in tests.

### Deliverables

- Migration adding `coverage_gap` and `source_audit` queryable views
  or projection tables.
- Tests that prove:
  - `source_audit` records every importer invocation with input hash,
    output counts, and outcome;
  - disabled or absent sources produce explicit `coverage_gap` rows;
  - packet rendering and `engram describe-corpus` never expose
    generated summaries or derived products as raw evidence.
- `EG-SI-090 Audit Reconstruction` test.

### Acceptance Criteria

- `make test` passes including new test modules.
- A reconstructed packet audit can reproduce the selected and
  omitted candidates for a packet built over a fixture corpus.

## Cross-Cutting Items

- Update `docs/ingestion.md` with the new contract template
  reference and the per-family CLI verbs as each importer lands.
- Update `CHANGELOG.md` Unreleased section once each layer lands.
- Update `BUILD_PHASES.md` once Layer 6 is on master and the source-
  contract discipline is the project default for new importers.
- Generated schema docs are refreshed via `make schema-docs` after each
  migration; do not hand-edit.

## What This Backlog Is Not

- A promotion path for RFC 0050. The RFC stays proposal-only until a
  recorded operator decision in `DECISION_LOG.md` accepts it.
- A commitment to Stages 3-5 (human communication, observation, live
  capture). Those depend on RFC 0050 open questions
  (`OQ-SI-005`, `OQ-SI-006`, `OQ-SI-011`) and on operator decision.
- A schedule. Sequencing is fixed; cadence is not. Each layer ships
  when its tests are green on master.
