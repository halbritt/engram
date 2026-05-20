# RFC 0053 Product Surface Handoff

## Summary

Added a CLI-first operator grant lifecycle surface:

- `engram claim-grounding grants list`
- `engram claim-grounding grants draft --request-json PATH`
- `engram claim-grounding grants approve --request-id ID --grant-id ID --granted-by ACTOR`
- `engram claim-grounding grants deny --request-id ID --grant-id ID --denied-by ACTOR --reason TEXT`
- `engram claim-grounding grants revoke --request-id ID --grant-id ID --revoked-by ACTOR --reason TEXT`

The list/output payloads display the exact `surface_form`, `search_query`,
`query_text_class`, `query_privacy_tier`, allowed targets, tenant/corpus,
extraction run, and opaque source refs. These commands append lifecycle rows
and perform no network IO.

## Verification

- `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -q tests/test_cli.py -k claim_grounding`
- `.venv/bin/python -m ruff check src/engram/cli.py tests/test_cli.py`
