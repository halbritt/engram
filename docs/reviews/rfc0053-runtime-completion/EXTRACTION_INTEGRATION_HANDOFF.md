# RFC 0053 Extraction Integration Handoff

## Summary

Added `src/engram/claim_grounding_integration.py`, a disabled extraction-adjacent
sidecar emitter. It builds RFC 0053 local-lookup requests from already accepted
claim drafts, persists request rows, and links them to the extraction with
`claim_grounding_links`.

Default extraction behavior is unchanged. `extract_claims_from_segment()` only
emits sidecars when `emit_claim_grounding_sidecars=True` or
`ENGRAM_CLAIM_GROUNDING_EMIT_SIDECARES` is enabled. The emitted payloads carry
entity surfaces and opaque message refs, not raw segment/message context.

## Verification

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -q tests/test_claim_grounding_integration.py`
- `.venv/bin/python -m ruff check src/engram/claim_grounding_integration.py tests/test_claim_grounding_integration.py`
