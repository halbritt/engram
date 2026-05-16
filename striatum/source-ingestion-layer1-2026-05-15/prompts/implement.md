# Layer 1 Implementation Prompt

Implement the Layer 1 deliverables from
[`SOURCE_INGESTION_BACKLOG.md`](../../SOURCE_INGESTION_BACKLOG.md):

1. Source contract template at `docs/source-contracts/README.md`.
2. Example contracts: `docs/source-contracts/git.yaml`,
   `docs/source-contracts/build_artifact.yaml` (Layer 2 forward-pointer).
3. Contract validator at `src/engram/source_contract.py` with
   `validate_contract(path) -> ContractValidationResult` and a closed
   error vocabulary.
4. Migration adding `source_kind='git'` and the new tables
   (`git_commits`, `git_commit_paths`).
5. Git importer at `src/engram/git_import.py` implementing the
   RFC 0050 contract for source_kind=git: commit metadata, parent
   links, refs, changed paths/numstat. Idempotent re-import. No
   outbound network. Coverage-gap emission on parse failure.
6. CLI verb `engram import git <repo-path>` with
   `--dry-run`, `--allow-dirty`, `--full-patch=false` defaults.
7. Tests:
   - `tests/test_source_contract_validator.py`
   - `tests/test_git_importer.py`
   - `tests/test_git_importer_no_egress.py`
8. Fixture repo at `tests/fixtures/source_contract_git/` —
   create the repo programmatically in a test setup helper rather
   than checking in a `.git` directory. Two commits, one branch,
   one tag, one file rename.

## Reference Material

Required reading (use file-read tools):

- [`docs/rfcs/0050-source-ingestion-expansion.md`](../../docs/rfcs/0050-source-ingestion-expansion.md)
  — the contract spec.
- [`SOURCE_INGESTION_BACKLOG.md`](../../SOURCE_INGESTION_BACKLOG.md) §
  Layer 1.
- [`docs/rfcs/0012-python-agentic-coding-standard.md`](../../docs/rfcs/0012-python-agentic-coding-standard.md)
  — coding standard.
- Existing importers as reference patterns:
  `src/engram/chatgpt_export.py`, `src/engram/claude_export.py`,
  `src/engram/striatum_ingest.py`.
- Existing migrations as reference: `migrations/014_*.sql`,
  `migrations/015_*.sql`.
- `tests/conftest.py` for the `conn` fixture and the
  `ENGRAM_TEST_DATABASE_URL` convention.

## Constraints

- No outbound network in any importer code path.
- `from __future__ import annotations` everywhere.
- Type hints on every signature.
- Per-stage exception family rooted in a domain class (see
  `SegmentationError` in `src/engram/segmenter.py` as the pattern).
- Tunables via `ENGRAM_`-prefixed env vars read at module top.
- Tests must be deterministic; no live LLM or network calls.
- The migration must reverse cleanly: include a down-migration if
  the project convention supports it, otherwise document
  irreversibility per the existing migration pattern.
- Use `subprocess.run(["git", ...], cwd=repo, check=True,
  capture_output=True, text=True)` for git invocations; no
  GitPython dependency.

## Deliverable Path

Write a short handoff at
`docs/reviews/source-ingestion-layer1-2026-05-15/IMPLEMENTATION_NOTES.md`
summarizing what landed, what is deferred to later layers, and any
open questions for the reviewer. The handoff is the workflow
artifact; the actual deliverable is the working code in the listed
paths.

Do not start the handoff with a markdown-byline-style `Author:` or
`author:` line; use `Lane:` and `Role:` instead.

Run `make test` before completing. Surface any failure in the
handoff rather than hiding it.
