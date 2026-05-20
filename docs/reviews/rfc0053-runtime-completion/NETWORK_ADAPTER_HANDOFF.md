# RFC 0053 Network Adapter Handoff

## Summary

Added `src/engram/claim_grounding_network.py`, a disabled-by-default search
adapter scaffold for broker-owned internet grounding. It supports:

- `generic_http`, configured only by
  `ENGRAM_CLAIM_GROUNDING_SEARCH_ENDPOINT`, using fixed GET dispatch with
  `q=<search_query>`.
- `tavily`, selected by `ENGRAM_CLAIM_GROUNDING_SEARCH_PROVIDER=tavily` and
  authenticated by `ENGRAM_CLAIM_GROUNDING_TAVILY_API_KEY`, using fixed POST
  dispatch to Tavily's HTTPS Search API.

Both paths enforce timeout/byte/result limits, reject private/local result URLs,
reject extra private context fields in dispatch payloads, and sanitize provider
JSON into response-shaped candidates. Tavily sends only the exact grant-bound
entity surface query and keeps the API key out of the URL/body/response payload.

The adapter remains explicit/injected. It does not grant network access to the
extractor and is not enabled by default. Live adapter invocation through the
broker now requires persisted sidecars plus a latest-approved persisted grant.

## Verification

- `.venv/bin/pytest tests/test_claim_grounding_network.py`
- `.venv/bin/pytest tests/test_claim_grounding.py tests/test_claim_grounding_broker.py tests/test_claim_grounding_network.py`
- `.venv/bin/python -m ruff check src/engram/claim_grounding_network.py tests/test_claim_grounding_network.py`
