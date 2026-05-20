# RFC 0053 Claim Grounding Boundary Review -- eval_gate

Status: review
Date: 2026-05-18
Lane: codex_eval
Role: reviewer
RFC refs: RFC-0053
Decision refs: D020, D090, D094

## Findings

### F001 -- Synthetic e2e is not yet a claim-grounding gate
Severity: blocking
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:318; docs/rfcs/0053-claim-extraction-grounding-boundary.md:335; Makefile:275; tests/test_context_eval_synthetic_e2e.py:41
Rationale: RFC 0053 requires a synthetic e2e gate before grounding can affect extraction output, including an extractor or extractor-adjacent harness that emits grounding requests. The implemented `e2e-context-synthetic` target runs the context-eval CLI and local `engram.ground_entity` lookup, but it does not emit `claim_grounding.request.v1` from segment/message evidence, persist request/response sidecars, or prove any grounded extraction behavior. RFC 0053 acknowledges the current context fixture is seed coverage, not the full extraction-grounding gate.
Proposed fix: Add a dedicated claim-grounding synthetic e2e target and fixture, or explicitly wire one into the eval gate target, that starts from synthetic raw private evidence, emits validated `ClaimGroundingRequest` payloads, records `ClaimGroundingResponse` artifacts, and proves claim output/provenance behavior remains versioned and auditable.

### F002 -- Ambiguity is shape-tested, not extraction-tested
Severity: major
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:307; tests/test_claim_grounding.py:216; tests/test_context_eval_synthetic_e2e.py:89; src/engram/claim_grounding.py:763
Rationale: The scaffold can parse an ambiguous response with two candidates, and the context e2e lookup returns both `Project Atlas` and `Atlas Station` for an `Atlas` query. That proves local lookup can expose ambiguity, but not that extraction preserves ambiguity instead of choosing the first candidate or silently resolving the claim. The RFC's failure semantics require extraction to preserve the surface form and ambiguity set.
Proposed fix: Add a synthetic extraction case with an ambiguous proper noun and assert that the extractor-adjacent harness records `status=ambiguous`, keeps both cited candidates, and does not attach resolved external entity provenance or mutate claim text based on candidate order.

### F003 -- Denied and granted network requests are not proven by the gate
Severity: blocking
Source: docs/rfcs/0053-claim-extraction-grounding-boundary.md:331; tests/test_claim_grounding.py:105; tests/test_claim_grounding.py:122; tests/test_claim_grounding.py:197; tests/test_claim_grounding.py:380; tests/test_context_eval_synthetic_e2e.py:118; src/engram/mcp_stdio.py:358
Rationale: Unit tests accept an explicit `network_grant`, reject network mode without one, parse a synthetic `performed_by_grounding_broker` response, and defer a granted miss because fetch is unsupported. The MCP surface rejects `allow_network=True` before lookup. None of this is an e2e denied/granted network-request proof: there is no denied response artifact, no simulated granted broker run, no append-only evidence write before response, and no assertion that the network-capable broker receives only `network_grant.search_query`.
Proposed fix: Add two synthetic broker paths: one denied grant that yields `status=denied` and `network_fetch=denied`, and one granted fetch fixture where the fake network broker receives only the granted search query, writes local grounding evidence, and returns a cited `performed_by_grounding_broker` response.

### F004 -- Poisoned public evidence handling is absent
Severity: major
Source: docs/reviews/rfc0053-claim-grounding-boundary/ADVERSARIAL_SECURITY_REVIEW.md:140; tests/fixtures/context_eval/synthetic_e2e/corpus.json:39; src/engram/entity_grounding.py:143
Rationale: The adversarial review requires a poisoned public evidence sample, but the current synthetic fixture contains only benign grounding rows. The local grounding scorer searches `content_excerpt` and `raw_payload`, so instruction-shaped public text can become matching evidence, yet no test proves it is treated only as cited evidence rather than authority or prompt instructions before extraction consumes grounding.
Proposed fix: Add a poisoned public grounding row with prompt-injection-shaped content and assert the broker/extractor path preserves bounded citation metadata, does not execute or forward the instruction text as control content, and either omits, lowers confidence, or preserves ambiguity according to the accepted policy.

### F005 -- No-egress is not exercised on the extractor grounding path
Severity: major
Source: HUMAN_REQUIREMENTS.md:155; docs/rfcs/0053-claim-extraction-grounding-boundary.md:51; docs/rfcs/0053-claim-extraction-grounding-boundary.md:327; tests/test_no_egress.py:70; Makefile:275
Rationale: The repository has a generic no-egress wrapper/probe and the MCP grounding tool refuses network fetch, but the synthetic context e2e target is not run under the no-egress wrapper and does not invoke a claim extractor path that emits grounding requests. That leaves the key D020 claim unproven for this boundary: the corpus-reading extractor can participate in grounding without opening sockets or delegating network fetch through MCP.
Proposed fix: Run the claim-grounding synthetic e2e extractor harness under `engram no-egress run` where supported, and add a socket-monkeypatch fallback that fails on outbound sockets while request emission, local lookup, denied network handling, and response consumption execute.

## Open Questions

- Should the claim-grounding e2e gate be a new `make e2e-claim-grounding-synthetic` target or part of `make eval-gates`?
- What minimal extraction artifact should the gate assert before full extractor integration exists: sidecar-only provenance, claim raw payload reference, or both?
- What policy outcome should poisoned public evidence produce in v1: omission, explicit ambiguous candidate, or cited low-confidence candidate?

verdict: needs_revision
