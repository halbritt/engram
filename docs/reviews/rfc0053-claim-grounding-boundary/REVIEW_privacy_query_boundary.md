# RFC 0053 Claim Grounding Boundary Review -- privacy_query_boundary

Status: review
Date: 2026-05-18
Lane: codex_privacy
Role: reviewer
RFC refs: RFC-0053
Decision refs: D020, D090, D094

## Findings

### F001 -- Non-surface query classes bypass the entity-name-only leak boundary
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:191; src/engram/claim_grounding.py:129; src/engram/claim_grounding.py:949; tests/test_claim_grounding.py:161
Rationale: RFC 0053 correctly states that `network_grant.search_query` is the only string the network-capable mode may use, that it may be private entity-name text, and that it must not become raw segment/message/claim/capture text. The scaffold only enforces exact equality between `search_query` and `surface_form` when `query_text_class == "entity_surface_form"`. The other accepted classes, `operator_entered` and `broker_minimized`, can carry any non-empty 240-character string with a grant-shaped payload. That leaves the core privacy exception too broad for extractor-originated requests: a confused or injected extractor can relabel `"Project Atlas private budget context"` as `operator_entered` or `broker_minimized` and pass validation even though the entity-name-only boundary is supposed to prevent that shape of leak.
Proposed fix: For any request emitted by the corpus-reading extractor, require `query_text_class == "entity_surface_form"` and normalized equality with `surface_form`, or add an explicit `query_origin`/request-type split that proves `operator_entered` queries came from a separate operator UI without corpus access. If `broker_minimized` remains, define the minimizer process and prove it has no access to raw segment/message/capture text. Add tests that the same drift string rejected for `entity_surface_form` is also rejected from extractor-originated `operator_entered` and `broker_minimized` grants.

### F002 -- Source references are not opaque enough to prove raw context cannot cross
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:184; src/engram/claim_grounding.py:176; src/engram/claim_grounding.py:205; tests/test_claim_grounding.py:183
Rationale: RFC 0053 relies on `source_refs` being opaque local references with optional span hashes and no message text. The Python validator rejects forbidden field names such as `message_text`, but it accepts arbitrary non-empty strings for `target_table` and `target_id`. Because the request payload itself is allowed to reach the broker, a raw sentence can be smuggled through an allowed field like `target_id` without tripping the private-payload-key guard. That weakens the claim that surrounding raw corpus context is prevented from reaching an internet-search-capable broker mode.
Proposed fix: Make `source_refs` actually opaque: restrict `target_table` to the intended local evidence tables and validate `target_id` as a UUID or other closed local-reference grammar. Add negative tests for raw-context strings placed in `target_id`, `target_table`, and other identifier fields, not only for rejected key names.

## Open Questions

- Should network-capable broker requests receive `source_refs` at all, or should they receive only `request_id`, `network_grant`, and the bounded `search_query` until after fetch output has landed as local append-only grounding evidence?
- Is the private entity-name exception limited to exact `surface_form` values from the extractor, with broader operator-entered searches handled by a separate product surface?

verdict: needs_revision
