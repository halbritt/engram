---
schema_version: "striatum.synthesis.v1"
artifact_kind: "synthesis"
---

# RFC 0044 Engram Phase 1 Final Synthesis
author: operator [self-declared: rfc0044-final-synthesis]

Status: synthesis
Date: 2026-05-14
External Striatum RFC: 0044
Decision refs: D001, D002, D020

## Verdict

RFC 0044 Engram-side Phase 1 is accepted with findings.

The implementation satisfies the intended local boundary: Striatum corpus
bundles are ingested from disk as immutable raw captures under
`tenant_id='striatum', corpus_id='striatum'`; Engram does not import or invoke
Striatum at runtime; the MCP stdio surface exposes only the four read-only
tools; and personal memory remains outside the default Striatum operator token.

The original correctness review found one blocking issue: single-pair serving
paths could read visible secondary corpora or tenants without the required
cross-boundary capability grants. That finding was valid. The focused repair
adds explicit `primary_pair` semantics, updates MCP token construction so
`--allow-pair` grants visibility rather than elevated read authority, and adds
service-path plus MCP-handler regressions for `MemoryService.search()`,
`MemoryService.fetch_reference()`, and MCP `tools/call`. The repair review
accepted the fix with no findings, and the workflow recovery artifacts attach
accepted verdicts for both the repaired correctness lane and the operator
review lane.

No remaining finding blocks Engram-side Phase 1 acceptance. The residuals are
hardening, evidence-scope, or reciprocal Striatum-repo follow-ups.

## Accepted Findings

- F001, single-pair serving reads bypass cross-boundary capability checks:
  accepted as blocking at original review time; resolved by the repair. The
  final state requires `memory.read_cross_corpus` for visible non-primary
  corpora inside the same tenant and `memory.read_cross_tenant` for visible
  non-primary tenants.
- F002 from the original correctness review, serving-path tests were missing:
  accepted and resolved. The repaired tests cover service reads and an MCP
  handler path matching the CLI `--allow-pair striatum/secondary` token shape.
- F002 from the ledger, `describe-corpus` shorthand collapses tenant and
  corpus: accepted as a minor follow-up. It is not a current authorization
  bypass, but it should be tightened to preserve the explicit two-key model.
- F003, weak MCP/reference existence and authorization distinctions: accepted
  as defense-in-depth. Collapse unauthorized and not-found failures at the MCP
  boundary.
- F004, Striatum tenant/source-kind consistency is not structurally enforced:
  accepted as hardening. Add database or service guardrails before future
  non-personal tenants broaden.
- F005, arbitrary `--capability` strings: accepted as a nit. Warn on or reject
  unknown capability names.
- F006, MCP frame reader lacks size cap and parse-error response: accepted as a
  robustness follow-up.
- F007, reciprocal Striatum-side augmentation checks are outside this Engram
  evidence set: accepted as a major cross-repo follow-up. This does not block
  Engram-side Phase 1, but it does block claiming the full RFC 0044
  augmentation contract is independently verified across both repositories.
- F008, `health()` schema version uses lexicographic migration order: accepted
  as a nit.
- F009, malformed decoded UUID references can bypass reference-error wrapping:
  accepted as a nit.
- F010, no OS-level no-egress sandbox was exercised: accepted as an
  evidence-scope limitation. The current evidence is code/test inspection of
  the RFC 0044 runtime surface, not structural D020 enforcement.
- F011, capability and manifest evidence used synthetic fixtures, not a real
  Striatum export smoke: accepted as a follow-up before routine operator use.

## Rejected Findings

- R001, captures trigger may not make tenant/corpus/bundle columns immutable:
  rejected. The existing raw-evidence trigger rejects any update/delete on
  captures, so later-added columns are covered.
- R002, operator review's "no critical issues" conclusion as a complete
  acceptance result: not carried. The operator review remains useful evidence
  for manifest/provenance and ergonomics, but the correctness blocker was
  real and required repair.
- R003, full MCP subprocess coverage is required for every Phase 1 capability
  test: rejected as a blanket rule. Service-level tests are sufficient for many
  checks, while the repaired blocker now has representative MCP handler
  coverage where it mattered.

## Follow-Up Queue

1. Add a Striatum-repo reciprocal augmentation-boundary artifact: no Striatum
   CLI or daemon import of Engram client code, no daemon RPC dependency on
   Engram, and graceful degradation when Engram is unavailable.
2. Run a local smoke against a real or committed fixture Striatum export bundle
   before relying on RFC 0044 for routine operator workflows.
3. Tighten `engram describe-corpus` so shorthand is only the sanctioned
   `striatum -> tenant_id='striatum', corpus_id='striatum'` convenience case,
   or require `--tenant` outside that case.
4. Harden MCP/reference error handling: uniform unauthorized/not-found messages,
   decoded UUID validation before database lookup, content-length cap, and
   JSON-RPC parse-error responses.
5. Add structural tenant/source-kind consistency checks for Striatum rows and a
   matching `fetch_reference()` guard.
6. Validate `--capability` values against the known Engram `memory.*`
   vocabulary.
7. Change `health()` schema-version selection to numeric migration prefix or
   applied timestamp ordering.
8. If future acceptance needs structural D020 evidence rather than code
   inspection, add a no-egress sandbox probe for the RFC 0044 runtime surface.

verdict: accept_with_findings
