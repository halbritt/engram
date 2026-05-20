# Public Schemas

This directory contains public schemas for private local datasets and payloads
that live outside the codebase.

## Claim Grounding Boundary

RFC 0053 defines the constrained claim-grounding boundary:

- `claim_grounding_request.v1.schema.json` describes the request a no-egress
  claim extractor may send to a grounding broker. It can record network intent
  and grant metadata, but it is not the outbound network payload and carries no
  raw corpus text.
- `claim_grounding_network_dispatch.v1.schema.json` describes the minimized
  broker-to-network-adapter payload for a future internet-search-capable mode.
  It carries only request/corpus ids, `surface_form`, and the explicit
  `network_grant` with bounded `search_query`. That query may itself be private
  entity-name text, so it carries `query_privacy_tier`.
- `claim_grounding_response.v1.schema.json` describes the cited response shape
  a broker returns to extraction. Network-capable results must still cite local
  immutable grounding evidence.
- `src/engram/claim_grounding.py` provides the Python validator and local
  lookup adapter. It also builds the minimized network-dispatch payload for
  tests; internet-search runtime remains broker-side only and disabled by
  default.
- `src/engram/claim_grounding_broker.py` provides the local broker scaffold.
  It defaults to local lookup and can use an injected fake/adapter protocol;
  there is no ambient network access.
- `src/engram/claim_grounding_runtime.py` records the append-only runtime
  sidecars from `migrations/024_claim_grounding_runtime.sql`: requests, grants,
  grant lifecycle rows, grant uses, network dispatch attempts, responses, and
  links.
- `src/engram/claim_grounding_network.py` provides disabled configured
  generic HTTP and Tavily adapter scaffolds for broker-owned internet search.
  Generic HTTP uses fixed GET dispatch. Tavily uses fixed POST dispatch to
  Tavily's HTTPS Search API with the API key read from
  `ENGRAM_CLAIM_GROUNDING_TAVILY_API_KEY`. Both paths require minimized network
  dispatch payloads and bounded/sanitized result handling, and neither is
  enabled by default.
- `src/engram/claim_grounding_integration.py` provides disabled
  extraction-adjacent request sidecar emission for accepted claim drafts.
- `engram claim-grounding grants list|draft|approve|deny|revoke` provides the
  current CLI-first operator grant lifecycle surface. It appends audit rows and
  performs no network IO.
- The Python validator is currently normative for cross-field invariants that
  the public JSON schemas do not fully express yet, including exact
  surface-query matching, query privacy ceilings, local-context capsule rules,
  and response status/candidate cardinality. Schema/validator parity is a
  pre-integration blocker before independent producers rely on the schemas
  alone.

## Context Eval Dataset

The real owner-authored context eval dataset is intentionally not committed to
this repository. The repo carries a public synthetic starter fixture, the public
item schema, and Python validation:

- `context_eval_item.v1.schema.json` describes one JSON object in the JSONL
  gold-set file.
- `src/engram/context_eval.py` validates the JSONL file through
  `ContextEvalItem.from_json()` / `load_eval_items()`.
- `tests/fixtures/context_eval/gold.jsonl` is a two-item synthetic starter for
  smoke testing the eval loop. It is not a substitute for the private
  owner-authored dataset.
- `tests/test_context_eval.py` seeds a matching synthetic corpus and runs the
  real `engram eval context` CLI/compiler path against that fixture.
- `tests/fixtures/context_eval/synthetic_e2e/` is the preferred synthetic e2e
  harness. It includes a fixture corpus with beliefs, captures, and local
  public-entity grounding evidence for proper-noun disambiguation.
  `make e2e-context-synthetic` runs the real CLI/compiler path plus local
  `engram.ground_entity` lookup against it.

Dataset discovery:

- `engram eval context --dataset-path PATH` accepts either a JSONL file or a
  directory containing `context_eval.gold.jsonl`.
- `ENGRAM_EVAL_DATASET_PATH` provides the same path when the CLI flag is not
  set.
- The legacy `--gold-set PATH` direct JSONL flag remains supported for fixture
  and compatibility use.
