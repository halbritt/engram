# RFC 0044 Repair Synthesis And Operator Decision

author: operator [self-declared: rfc0044-repair-synthesis]

Status: accepted_with_follow_up
Date: 2026-05-14
Original run: `run_322110269dfb4ec98fc6f7ea818448c0`
Repair run: `run_1aadc5c6bc00434497bc6d9754358a62`
Original checkpoint: `blk_603d77b8a1364075994f2bf8565478b7`

## Decision

The original RFC 0044 correctness `needs_revision` checkpoint is resolved by
the focused capability-boundary repair. Continue the original RFC 0044 workflow
past the correctness checkpoint.

This decision does not waive the separate operator-contract / missing-verdict
blocker on the original Gemini review lane. That blocker remains a workflow
provenance issue to resolve independently.

## Original Blocking Findings

`REVIEW_correctness_codex.md` found:

- F001: single-pair `MemoryService.search()` and `fetch_reference()` reads
  could bypass cross-corpus / cross-tenant capability requirements because
  those serving paths used `MemoryToken.authorize_read()` rather than the
  stricter multi-pair helper.
- F002: existing tests covered helper behavior, not the actual service and MCP
  serving paths.

## Repair Evidence

The repair handoff and evidence show:

- `MemoryToken` now carries an explicit `primary_pair`.
- Single-pair authorization now requires `memory.read_cross_corpus` for
  visible non-primary corpora inside the same tenant.
- Single-pair authorization now requires `memory.read_cross_tenant` for visible
  non-primary tenants.
- `engram-mcp-stdio` derives the primary pair from primary `--tenant` /
  `--corpus`; extra `--allow-pair` values grant visibility only, not elevated
  cross-boundary read authority.
- Service-path tests now exercise both `MemoryService.search()` and
  `MemoryService.fetch_reference()`.
- MCP handler tests exercise the same `--allow-pair striatum/secondary` token
  shape that the CLI constructs.

`REPAIR_CAPABILITY_EVIDENCE.md` reports:

- `tests/test_striatum_ingest.py tests/test_mcp_stdio.py`: 11 passed.
- Adjacent RFC 0044 target tests: 6 passed.
- Local-only and read-only surface scans passed for the repaired runtime
  surface.

`REPAIR_CAPABILITY_HANDOFF.md` additionally reports the full suite passing:

- `make test`: 541 passed.

`REVIEW_capability_repair_codex.md` returned `accept` with no findings and
explicitly marks F001 and F002 resolved.

## Residual Follow-Up

The original RFC 0044 run still has a separate operator-contract / missing
verdict blocker from the Gemini review lane. Resolve that blocker through a
workflow/provenance decision or a replacement operator-contract review before
treating the original RFC 0044 run as fully synthesized.
