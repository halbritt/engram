# EG-000 RFC 0044 Hardening Baseline Evidence

Status: evidence
Date: 2026-05-15
Run: ad-hoc baseline (no Striatum runner involved)
Scope: AL-D001 deferred prerequisite — produce RFC 0044 Phase 0 hardening
       / EG-000-equivalent evidence before projection, retrieval, or
       operator-context implementation depends on the current Striatum
       substrate (see
       `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/FINDINGS_LEDGER.md`).

This evidence artifact covers all eight EG-000 pass criteria defined in
`docs/rfcs/0049-striatum-evaluation-gates.md` § "EG-000: RFC 0044 Hardening
Baseline" against Engram master at this commit. Every criterion is
exercised by a deterministic local test or a directly verifiable code
path; no synthetic/mock-only paths are used to satisfy the gate.

## Criterion Coverage

| # | Pass criterion | Evidence | Result |
|---|----------------|----------|--------|
| 1 | `MemoryService.search()` enforces primary-pair semantics. | `tests/test_striatum_ingest.py::test_service_search_and_fetch_require_cross_corpus_for_secondary_striatum_corpus` + `::test_service_search_and_fetch_require_cross_tenant_for_personal_pair`. Code path: `src/engram/memory.py:162-207` calls `self.token.authorize_read(pair)` and applies `WHERE tenant_id = %s AND corpus_id = %s AND source_kind::text = 'striatum'`. | pass |
| 2 | `MemoryService.fetch_reference()` enforces primary-pair semantics and reauthorizes the stored row. | Same tests as (1) plus `::test_default_striatum_token_cannot_read_personal_or_fetch_personal_reference`. Code path: `src/engram/memory.py:209-252` loads the row by `id` alone, then reconstructs `TenantCorpus(row[1], row[2])` and calls `self.token.authorize_read(pair)` against the *stored* pair. | pass |
| 3 | At least one MCP `tools/call` path exercises the CLI-style `--allow-pair` token shape and proves visible pairs are not read grants. | `tests/test_mcp_stdio.py::test_mcp_allow_pair_does_not_bypass_cross_corpus_for_search_or_fetch`. Both `engram.search` and `engram.fetch_reference` return `isError: True` with `memory.read_cross_corpus` in the error message when the token's `--allow-pair striatum/secondary` lists the pair but no `--capability memory.read_cross_corpus` is present. | pass |
| 4 | `engram.describe_corpus` shorthand is restricted to the sanctioned `striatum` convenience or requires explicit `--tenant`. | New CLI guard at `src/engram/cli.py` (describe-corpus branch): non-`striatum` positional requires `--tenant`. Tests: `tests/test_cli.py::test_describe_corpus_rejects_non_striatum_shorthand_without_tenant` and `::test_describe_corpus_accepts_non_striatum_corpus_with_explicit_tenant`. Original `tests/test_cli.py::test_describe_corpus_dispatches_to_memory_service` still covers the sanctioned shorthand. | pass |
| 5 | `engram-mcp-stdio --capability` rejects or warns on unknown `memory.*` capability names. | New validator in `src/engram/mcp_stdio.py::build_token` checks against `KNOWN_MEMORY_CAPABILITIES` (defined in `src/engram/memory.py`). Tests: `tests/test_mcp_stdio.py::test_build_token_rejects_unknown_memory_capability` (asserts `ValueError` naming the unknown value and listing the closed vocabulary) and `::test_build_token_accepts_known_memory_capability`. | pass |
| 6 | `engram.health` reports schema version by numeric migration prefix or applied ordering, not fragile lexicographic maximum. | `src/engram/memory.py::MemoryService.health` now selects `filename` from `schema_migrations` ordered by `applied_at DESC, filename DESC`, not `max(filename)`. Test: `tests/test_striatum_ingest.py::test_health_schema_version_uses_applied_ordering_not_lex_max` inserts a synthetic `0_synthetic_lex_loser.sql` row with `applied_at = NOW()` and asserts `health()['schema_version'] == '0_synthetic_lex_loser.sql'`. A `max(filename)` query would return `014_striatum_tenant_corpus.sql` and fail the assertion. | pass |
| 7 | A committed or non-private fixture Striatum export smoke proves the ingest and read-only retrieval path against non-synthetic bundle shape. | Committed fixture under `tests/fixtures/striatum_eg000/` built by `build_fixture.py` from Engram's own public RFC/decision-log/operator-report/changelog prose (so the bundle is non-private and content is real, not synthetic). Manifest is at `tests/fixtures/striatum_eg000/manifest.json` with `schema_version = "striatum.corpus_export.v1"` and `bundle_sha256` over canonicalized manifest content. Test: `tests/test_striatum_ingest.py::test_eg000_committed_fixture_round_trip_ingest_and_read` runs `ingest_striatum_bundle` against the committed bundle, then exercises `MemoryService.search`, `MemoryService.fetch_reference`, and `MemoryService.describe_corpus`. | pass |
| 8 | A Striatum-side artifact proves no Engram client import, no Engram daemon RPC dependency, and graceful fallback when Engram is unavailable. | Striatum repo at `/home/halbritt/git/striatum` (HEAD `a50f495`) carries `tests/test_cli_corpus_export.py::test_no_engram_imports_or_memory_capabilities_in_striatum`. The test asserts `import engram`, `from engram`, the `memory.` namespace, and `engram` (case-insensitive) all do *not* appear in the Striatum corpus, CLI, daemon_rpc, daemon_pg, MCP, service modules, or `pyproject.toml`. Run output: `1 passed in 0.03s`. Graceful fallback is implicit — Striatum has no Engram coupling at all, so there is nothing to fall back *from*. | pass |

## Test run

The following Engram tests cover criteria 1-7 and pass against the
working tree at commit-to-be:

```
ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test" \
  .venv/bin/python -m pytest \
  tests/test_striatum_ingest.py tests/test_mcp_stdio.py tests/test_cli.py -q
...
46 passed in 22.55s
```

The Striatum-side test for criterion 8:

```
(in /home/halbritt/git/striatum)
pytest tests/test_cli_corpus_export.py::test_no_engram_imports_or_memory_capabilities_in_striatum -q
...
1 passed in 0.03s
```

## Code changes that landed for EG-000

- `src/engram/memory.py` — added `KNOWN_MEMORY_CAPABILITIES` constant;
  replaced `SELECT max(filename) FROM schema_migrations` in `health()`
  with `ORDER BY applied_at DESC, filename DESC LIMIT 1`.
- `src/engram/mcp_stdio.py::build_token` — validates each `--capability`
  value against `KNOWN_MEMORY_CAPABILITIES` and raises `ValueError`
  naming the offending value if it is unknown.
- `src/engram/cli.py` describe-corpus branch — positional shorthand only
  collapses to `tenant_id == 'striatum'` when the positional equals
  `striatum`; every other corpus requires explicit `--tenant` and exits
  with code 2 otherwise.
- `tests/test_striatum_ingest.py` — added the EG-000 fixture smoke test
  and the schema-version applied-ordering test.
- `tests/test_mcp_stdio.py` — added the unknown-capability rejection
  test and the known-capability acceptance test.
- `tests/test_cli.py` — added the describe-corpus shorthand restriction
  tests.
- `tests/fixtures/striatum_eg000/` — committed fixture bundle and the
  deterministic `build_fixture.py` that regenerates it.

## Scope and limits

This artifact closes `AL-D001` for the eight pass criteria specified by
EG-000. It does not by itself authorize implementation of RFC 0046
projections, RFC 0047 retrieval, RFC 0048 injection, or RFC 0049 broader
gates; those still depend on the AL-D002 acceptance decision and the
remaining nonblocking promotion items listed in
`docs/reviews/striatum-memory-rfc-alignment-2026-05-14/FINDINGS_LEDGER.md`.

The Striatum-side independence test asserts the *current* boundary; it
does not prevent a future Striatum change from adding an Engram
dependency. If that ever lands, the test in
`~/git/striatum/tests/test_cli_corpus_export.py` would have to be
weakened or removed first, which is the documented break point.
