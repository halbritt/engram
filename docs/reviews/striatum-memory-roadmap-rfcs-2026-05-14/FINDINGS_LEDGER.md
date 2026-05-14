# Striatum Memory Roadmap RFC Findings Ledger
author: operator [self-declared: roadmap-findings-ledger]

Status: ledger
Date: 2026-05-14
Run ID: run_500d0f049ea04038b0e19d6045daf918
Scope: Normalizes the review findings for the Striatum memory roadmap RFC
package. This ledger records review disposition and follow-up posture only.
It does not authorize RFC promotion, implementation, Striatum state
transitions, publication, completion, verdict changes, commits, migrations,
tests, schema-doc generation, or any runtime behavior.

Sources:
  - `striatum/striatum-memory-roadmap-rfcs-2026-05-14/prompts/findings_ledger.md`
  - `docs/process/multi-agent-review-loop.md`
  - `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_privacy_boundary.md`
  - `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_contract_coherence.md`
  - `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_contract_coherence_repair.md`
  - `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_operator_ergonomics.md`
  - `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/OPERATOR_DECISION_CONTRACT_REPAIR.md`
  - `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/OPERATOR_DECISION_ACCEPT_CONTRACT_REPAIR_REVIEW.md`
  - `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REPAIR_RFC0045_CONTRACT.md`
  - `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REPAIR_RFC0046_PROJECTIONS.md`
  - `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REPAIR_RFC0049_GATES.md`

## Posture Summary

- `REVIEW_privacy_boundary.md` verdict: `accept_with_findings`.
- `REVIEW_operator_ergonomics.md` verdict: `accept_with_findings`.
- `REVIEW_contract_coherence.md` verdict: `needs_revision`, superseded for
  blocking posture by the bounded repair cycle, the fresh
  `REVIEW_contract_coherence_repair.md` verdict `accept_with_findings`, and
  `OPERATOR_DECISION_ACCEPT_CONTRACT_REPAIR_REVIEW.md`.
- No original contract-coherence finding remains blocking in this ledger.
  Remaining contract-coherence repair findings are carried as nonblocking
  follow-up before RFC promotion or implementation.
- Routine default-on automatic Striatum memory remains blocked by the RFC 0049
  gate posture until accepted/promoted RFC 0045-RFC 0048 successors exist and
  all applicable gates pass.
- Generated memory products remain blocked from Level 2 and Level 3 injection
  until a separate accepted privacy-inheritance, citation, and audit contract
  exists.

## Original Contract-Coherence Supersession

The first contract-coherence review found five blocking issues and five major
issues. The operator routed those findings to repair instead of overriding the
review. The repair re-review found no remaining blockers and the operator
accepted that late evidence path. The dispositions below are retained as
provenance, but the original `needs_revision` verdict no longer blocks the
run's findings-ledger posture.

| ID | Original severity | Ledger disposition |
|----|-------------------|--------------------|
| CC-001 | blocking | Resolved. RFC 0045 now requires row-level `tenant_id`, `corpus_id`, and `bundle_id` and validates row identity against `manifest.memory_target`. |
| CC-002 | blocking | Partially resolved, nonblocking follow-up. Bundle identity and lifecycle record shapes were added; RFC 0047 bundle identity examples still drift. See F013. |
| CC-003 | blocking | Resolved. RFC 0046 now uses generation-scoped idempotency and full-snapshot active generation activation with carry-forward rows. |
| CC-004 | blocking | Partially resolved, nonblocking follow-up. Embedding serving fields and skip table were added; skip invalidation semantics still need alignment. See F015. |
| CC-005 | blocking | Resolved. RFC 0049 now blocks Level 3 until accepted/promoted RFC 0045-RFC 0048 successors and passing gates exist. |
| CC-006 | major | Resolved. RFC 0046 now blocks migration/projection implementation on RFC 0044 Phase 0 hardening or EG-000-equivalent evidence. |
| CC-007 | major | Partially resolved, nonblocking follow-up. RFC 0045 vocabularies were closed; RFC 0046 still needs exact-reference vocabulary alignment. See F014. |
| CC-008 | major | Resolved. RFC 0049 now defines Level 2, Level 1-3 matrix columns, and per-gate failure actions. |
| CC-009 | major | Resolved. RFC 0049 now treats no-egress evidence as transitive across local runtimes receiving corpus text. |
| CC-010 | major | Partially resolved, nonblocking follow-up. Golden-query and packet-audit coverage were added; reference coverage and RFC 0048 audit wording still need alignment. See F014 and F016. |

## Findings

### F001 - Path-shaped fields can leak operator-private paths
Severity: major
Classification: accepted repair, with projection/implementation follow-up
Sources: `PB-001`, `REPAIR_RFC0045_CONTRACT.md`,
`REPAIR_RFC0046_PROJECTIONS.md`
Affects:
  - RFC 0045 item shape and validation rules
  - RFC 0046 `striatum_items`, `striatum_chunks`, `striatum_references`
Disposition: RFC 0045 incorporated repository-relative path defaults,
absolute-path/user-profile opt-in, and validation. RFC 0046 partially
incorporated projection-time path rules.
Blocking posture:
  - RFC promotion: no current package blocker after repair; confirm projection
    text alignment before promotion.
  - implementation: yes, path normalization and rejection/sanitization must be
    enforced before retrieval-visible rows exist.
  - routine Striatum operator use: blocked by gates where path/citation leaks
    are possible.
  - later personal-memory work: yes, the same citation/path leak rule must
    carry to personal-memory corpora.

### F002 - Dirty working tree exports can persist local unmerged state
Severity: major
Classification: accepted repair, with projection mirror follow-up
Sources: `PB-002`, `REPAIR_RFC0045_CONTRACT.md`
Affects:
  - RFC 0045 manifest and identity rules
  - RFC 0046 git-reference projection behavior
Disposition: RFC 0045 now makes dirty exports invalid by default unless the
manifest records explicit operator opt-in and rows carry
`provenance.dirty_working_tree=true`. The ledger did not find an explicit
RFC 0046 dirty-projection mirror in the repair evidence.
Blocking posture:
  - RFC promotion: follow-up before promoting the exporter/projection contract.
  - implementation: yes for exporter and projection paths that can see dirty
    working trees.
  - routine Striatum operator use: dirty exports must remain refused or
    explicitly opted in.
  - later personal-memory work: no direct blocker, but the pattern should be
    reused for any local working-copy source.

### F003 - Retrieval responses can leak unauthorized corpus inventory metadata
Severity: major
Classification: follow-up alignment before RFC 0047 promotion/implementation
Sources: `PB-003`, `REVIEW_contract_coherence_repair.md`,
`REPAIR_RFC0049_GATES.md`
Affects:
  - RFC 0047 response contract and failure behavior
  - RFC 0048 packet/audit shape
  - RFC 0049 EG-030, EG-040, EG-110
Disposition: RFC 0049 now gates unauthorized metadata redaction, but RFC 0047
still exposes `corpus.bundle_ids`, source time bounds, and staleness fields
without fully matching the gate's redaction posture.
Blocking posture:
  - RFC promotion: yes for RFC 0047 unless explicitly scope-limited or aligned.
  - implementation: yes for retrieval failure and pair-mismatch behavior.
  - routine Striatum operator use: Level 3 remains blocked until the gates pass.
  - later personal-memory work: yes, personal-memory metadata probing must
    collapse unauthorized and not-found shapes.

### F004 - Repository and instance labels need privacy-tier treatment
Severity: major
Classification: partially repaired, follow-up for RFC 0047 alignment
Sources: `PB-004`, `REPAIR_RFC0045_CONTRACT.md`, `REPAIR_RFC0049_GATES.md`
Affects:
  - RFC 0045 manifest identity labels
  - RFC 0047 tenant/corpus isolation and diagnostics
Disposition: RFC 0045 now makes labels display-only, privacy-inherited, and
unavailable in unauthorized diagnostics. RFC 0049 adds gate coverage. RFC 0047
still needs explicit alignment beyond saying labels are not grants.
Blocking posture:
  - RFC promotion: follow-up before RFC 0047 promotion.
  - implementation: yes where labels can appear in diagnostics, citations, or
    audit records.
  - routine Striatum operator use: scope-limit or block surfaces that expose
    higher-tier labels.
  - later personal-memory work: yes, personal corpus labels are direct privacy
    metadata.

### F005 - Withheld bodies must never be embedded before redaction
Severity: major
Classification: accepted repair
Sources: `PB-005`, `REPAIR_RFC0045_CONTRACT.md`,
`REPAIR_RFC0046_PROJECTIONS.md`
Affects:
  - RFC 0046 chunks and embeddings
  - RFC 0049 redaction/vector fixtures
Disposition: RFC 0045 and RFC 0046 now state that embeddings may be computed
only over emitted `chunk_text`; a deterministic redaction notice is embedded
instead of the withheld body.
Blocking posture:
  - RFC promotion: no current text blocker after repair.
  - implementation: yes, vector serving must prove withheld text cannot be
    recovered through embeddings.
  - routine Striatum operator use: blocked until privacy/redaction gates pass.
  - later personal-memory work: yes, personal-memory vectors must inherit this
    rule.

### F006 - Reference replay/collision coverage must protect personal memory
Severity: major
Classification: accepted repair, gate evidence required later
Sources: `PB-006`, `REPAIR_RFC0046_PROJECTIONS.md`,
`REPAIR_RFC0049_GATES.md`
Affects:
  - RFC 0047 fetch-reference isolation
  - RFC 0049 EG-030 and EG-040
Disposition: RFC 0046 scopes reference rows by stored tenant/corpus pair and
RFC 0049 now requires crafted reference-replay coverage, including the
symmetric personal-memory case once `memory.read_personal` exists.
Blocking posture:
  - RFC promotion: no current text blocker after repair.
  - implementation: yes for fetch-reference and reference-id decoding paths.
  - routine Striatum operator use: blocked until tests/gates prove replay fails.
  - later personal-memory work: direct blocker before personal-memory fetch
    integration.

### F007 - RFC 0044 hardening preconditions must remain explicit
Severity: minor
Classification: accepted repair, implementation prerequisite
Sources: `PB-007`, `CC-006`, `REPAIR_RFC0045_CONTRACT.md`,
`REPAIR_RFC0046_PROJECTIONS.md`
Affects:
  - RFC 0045 dependencies
  - RFC 0046 implementation prerequisites
  - RFC 0049 EG-000
Disposition: RFC 0045 and RFC 0046 now name RFC 0044 hardening preconditions,
including F004 and F009 from the RFC 0044 ledger.
Blocking posture:
  - RFC promotion: no remaining text blocker.
  - implementation: yes, RFC 0044 Phase 0 hardening or EG-000-equivalent
    evidence is a prerequisite.
  - routine Striatum operator use: blocked by EG-000 if missing.
  - later personal-memory work: indirect; protects all capability and
    reference-boundary work.

### F008 - Manual search paste-through needs explicit cross-boundary policy
Severity: minor
Classification: partially repaired, RFC 0048 follow-up
Sources: `PB-008`, `REPAIR_RFC0049_GATES.md`
Affects:
  - RFC 0048 manual versus automatic augmentation
  - RFC 0049 Level 1 manual/local operator search
Disposition: RFC 0049 partially covers Level 1 and gate behavior. RFC 0048
still needs explicit wording for copying personal or non-primary manual search
results into Striatum operator/agent packets only with per-packet opt-in and
audit.
Blocking posture:
  - RFC promotion: follow-up before RFC 0048 promotion or explicit deferral.
  - implementation: yes for packet construction and audit behavior.
  - routine Striatum operator use: manual use must remain explicit, cited, and
    audited.
  - later personal-memory work: direct blocker for personal-memory manual
    paste-through.

### F009 - No-egress evidence needs loopback and wording cleanup
Severity: minor
Classification: accepted repair with wording follow-up
Sources: `PB-009`, `CC-009`, `REVIEW_contract_coherence_repair.md`,
`REPAIR_RFC0049_GATES.md`
Affects:
  - RFC 0049 EG-020
Disposition: RFC 0049 now requires Postgres loopback/local-socket proof,
non-loopback failure probes, and transitive no-egress evidence for local
runtimes that receive corpus text. The repair re-review still found wording
conflict between rejecting any HTTP client and allowing paired loopback
HTTP/model/embedding clients.
Blocking posture:
  - RFC promotion: wording cleanup before promotion, but no restored blocker.
  - implementation: yes, OS-level evidence must cover caller and transitive
    local runtimes.
  - routine Striatum operator use: default-on remains blocked until evidence
    passes.
  - later personal-memory work: protects all local evidence, including
    personal memory.

### F010 - Audit records need privacy inheritance and lower-tier views
Severity: minor
Classification: partially repaired, RFC 0048 follow-up
Sources: `PB-010`, `REVIEW_contract_coherence_repair.md`,
`REPAIR_RFC0049_GATES.md`
Affects:
  - RFC 0048 reviewability and audit trail
  - RFC 0049 EG-110
Disposition: RFC 0049 now adds audit privacy inheritance, opaque omitted
candidate handling, and lower-tier audit redaction. RFC 0048's audit field
list remains weaker than the gate language.
Blocking posture:
  - RFC promotion: follow-up before RFC 0048 promotion or explicit
    scope-limited acceptance.
  - implementation: yes for audit storage, diagnostics, and packet
    reconstruction.
  - routine Striatum operator use: blocked by EG-110 until authorization-safe
    audit reconstruction passes.
  - later personal-memory work: direct blocker for personal-memory audit
    visibility.

### F011 - Omission reason vocabulary needs identity and citation leak codes
Severity: nit
Classification: partially repaired, RFC 0048 vocabulary follow-up
Sources: `PB-011`, `REVIEW_contract_coherence_repair.md`,
`REPAIR_RFC0049_GATES.md`
Affects:
  - RFC 0048 context eligibility and omission reasons
  - RFC 0049 EG-060 and EG-080
Disposition: RFC 0049 now requires `identity_leak` and `citation_leak`; RFC
0048's suggested omission reason list still lacks those reasons.
Blocking posture:
  - RFC promotion: low-severity follow-up before RFC 0048 promotion.
  - implementation: include the codes before any injection surface.
  - routine Striatum operator use: nonblocking if gate text remains stricter
    than RFC 0048, but alignment is required for clarity.
  - later personal-memory work: relevant to personal-memory labels/citations.

### F012 - Generated memory products remain blocked without a privacy contract
Severity: nit
Classification: accepted repair, deferred future contract
Sources: `PB-012`, `REPAIR_RFC0049_GATES.md`
Affects:
  - Striatum memory roadmap derived-product phase
  - RFC 0048 deferred automatic-injection question
  - RFC 0049 EG-140
Disposition: RFC 0049 now has a placeholder/blocking gate. A later accepted
privacy-inheritance, citation, and audit contract is still required.
Blocking posture:
  - RFC promotion: no blocker for source-evidence search RFCs.
  - implementation: generated products must not enter Level 2 or Level 3
    injection until the separate contract exists.
  - routine Striatum operator use: raw/source-evidence search is not blocked;
    generated-product injection is blocked.
  - later personal-memory work: direct blocker for derived personal-memory
    products.

### F013 - RFC 0047 bundle identity examples still use SHA-shaped IDs
Severity: major
Classification: nonblocking repair re-review follow-up
Sources: `CC-002`, `REVIEW_contract_coherence_repair.md`
Affects:
  - RFC 0047 retrieval response and citation examples
  - RFC 0045 bundle identity semantics
Disposition: RFC 0045 now separates opaque `bundle_id` from `bundle_sha256`,
but RFC 0047 still shows `bundle_ids` and citation `bundle_id` values shaped
as `sha256:<hex>`.
Blocking posture:
  - RFC promotion: fix or explicitly scope-limit before RFC 0047 promotion.
  - implementation: yes for response/citation schema compatibility.
  - routine Striatum operator use: nonblocking until retrieval responses are
    implemented, then contract drift would affect citations.
  - later personal-memory work: no direct blocker.

### F014 - Exact-reference vocabulary omits workflow and job identifiers
Severity: major
Classification: nonblocking repair re-review follow-up
Sources: `CC-007`, `CC-010`, `REVIEW_contract_coherence_repair.md`
Affects:
  - RFC 0046 `striatum_references`
  - RFC 0047 filters
  - RFC 0049 exact lookup coverage
Disposition: RFC 0045 defines `workflow_job_id` and `job_id` reference kinds
and RFC 0049 requires exact lookup coverage for them, but RFC 0046's reference
vocabulary still omits them.
Blocking posture:
  - RFC promotion: fix before RFC 0046/RFC 0049 promotion.
  - implementation: yes for exact-reference lookup and gate fixtures.
  - routine Striatum operator use: nonblocking until exact lookup surfaces are
    implemented.
  - later personal-memory work: no direct blocker.

### F015 - Embedding skip rows need invalidation semantics
Severity: major
Classification: nonblocking repair re-review follow-up
Sources: `CC-004`, `REVIEW_contract_coherence_repair.md`,
`REPAIR_RFC0046_PROJECTIONS.md`
Affects:
  - RFC 0046 `striatum_embedding_skips`
Disposition: RFC 0046 added `striatum_embedding_skips`, but the re-review
found skip rows are not clearly invalidation-addressable. Either the table
needs active/invalidation fields, or the RFC needs an explicit same-generation
active chunk/item join rule for skip validity.
Blocking posture:
  - RFC promotion: fix before RFC 0046 promotion.
  - implementation: yes for privacy reclassification and completeness checks.
  - routine Striatum operator use: vector lanes remain gated until stale/skip
    handling is proven.
  - later personal-memory work: relevant to any personal-memory vector lane.

### F016 - RFC 0048 should align with RFC 0049 on audit and default-on wording
Severity: minor
Classification: nonblocking repair re-review follow-up
Sources: `REVIEW_contract_coherence_repair.md`, `PB-010`
Affects:
  - RFC 0048 automatic augmentation target and audit list
  - RFC 0049 Level 3 prerequisites and EG-110
Disposition: RFC 0049 now requires accepted/promoted upstream successors and
stronger audit rules. RFC 0048 still describes the post-RFC 0049 target and
audit fields more weakly.
Blocking posture:
  - RFC promotion: follow-up before RFC 0048 promotion.
  - implementation: yes where RFC 0048 is used as packet implementation
    guidance.
  - routine Striatum operator use: Level 3 remains blocked by RFC 0049
    regardless.
  - later personal-memory work: relevant where audit fields can expose
    personal-memory metadata.

### F017 - Redaction-state vocabulary open-decision lists are stale
Severity: nit
Classification: nonblocking cleanup
Sources: `REVIEW_contract_coherence_repair.md`
Affects:
  - RFC 0046, RFC 0048, and RFC 0049 downstream open-decision lists
  - RFC 0045 redaction-state vocabulary
Disposition: Downstream open-decision lists still treat final redaction-state
vocabulary as open even though RFC 0045 now defines it.
Blocking posture:
  - RFC promotion: cleanup before final promotion packet.
  - implementation: no, unless implementors rely on stale open-decision text.
  - routine Striatum operator use: no.
  - later personal-memory work: no direct blocker.

### F018 - Roadmap next-step text is stale after RFC 0045-RFC 0049 authoring
Severity: nit
Classification: nonblocking cleanup
Sources: `REVIEW_contract_coherence_repair.md`
Affects:
  - `STRIATUM_MEMORY_ROADMAP.md`
Disposition: The roadmap still says the immediate next step is scaffolding
RFC 0045, even though RFC 0045-RFC 0049 now exist and the operator routed the
package through repair plus fresh re-review.
Blocking posture:
  - RFC promotion: cleanup before final promotion packet.
  - implementation: no.
  - routine Striatum operator use: no.
  - later personal-memory work: no.

### F019 - No-data memory status can add packet noise
Severity: minor
Classification: deferred/open ergonomics follow-up
Sources: `ERGO-001`, `REVIEW_operator_ergonomics.md`
Affects:
  - RFC 0048 memory section status/header shape
Disposition: Not repaired in the reviewed repair handoffs. The suggested
follow-up is allowing a collapsed single-line status when no memory items are
selected.
Blocking posture:
  - RFC promotion: no, but accept or defer explicitly.
  - implementation: no hard blocker.
  - routine Striatum operator use: minor UX noise in high-frequency no-data
    turns.
  - later personal-memory work: no direct blocker.

### F020 - Conflict warnings should cite current authority
Severity: minor
Classification: accepted repair
Sources: `ERGO-002`, `REPAIR_RFC0049_GATES.md`
Affects:
  - RFC 0048 conflict warnings
  - RFC 0049 EG-050, EG-090, EG-110
Disposition: RFC 0049 now requires conflict warnings and conflict omissions to
cite both the omitted memory item and the current authority item.
Blocking posture:
  - RFC promotion: no current blocker after repair.
  - implementation: yes for automatic injection and audit behavior.
  - routine Striatum operator use: default-on remains gated if this evidence is
    missing.
  - later personal-memory work: relevant but not independently blocking.

### F021 - Operator startup timeout needs cold-start evidence
Severity: nit
Classification: accepted repair
Sources: `ERGO-003`, `REPAIR_RFC0049_GATES.md`
Affects:
  - RFC 0047 search timeout guidance
  - RFC 0049 EG-100
Disposition: RFC 0049 now requires cold-start and warm-cache
`operator_startup` latency measurements and keeps Level 3 blocked if the
startup behavior cannot stay within the total automatic packet budget.
Blocking posture:
  - RFC promotion: no current blocker after repair.
  - implementation: benchmark evidence required for the startup path.
  - routine Striatum operator use: Level 3 blocked if cold-start behavior fails
    EG-100.
  - later personal-memory work: no direct blocker.

### F022 - Session-scope disable persistence is undefined
Severity: nit
Classification: deferred/open ergonomics follow-up
Sources: `ERGO-004`, `REVIEW_operator_ergonomics.md`
Affects:
  - RFC 0048 disable controls
Disposition: Not repaired in the reviewed repair handoffs. The contract should
clarify whether session-scope disablement is transient across daemon restarts
or persists only when promoted to run/operator-config scope.
Blocking posture:
  - RFC promotion: low-severity follow-up or explicit deferral.
  - implementation: yes for state semantics.
  - routine Striatum operator use: operator surprise risk after restart.
  - later personal-memory work: privacy-relevant before personal memory can be
    exposed through disable controls.

## Not Carried As Blocking

- The original `REVIEW_contract_coherence.md` `needs_revision` verdict is not
  carried as a current blocker because the operator accepted the fresh repair
  re-review and instructed the prior verdict/blocker to be superseded.
- The repair handoffs are proposal-text repairs only. They did not implement
  code, tests, migrations, generated schema docs, runtime behavior, gate
  evidence, Striatum state transitions, or RFC promotion.
- This ledger does not mark any RFC accepted, promoted, implemented, complete,
  or ready for default-on operator use.

## Validation

Read-only extraction was split across privacy boundary, original
contract-coherence plus repair re-review, operator ergonomics, repair mapping,
and ledger/process constraints. Those sub-agents reported no file writes.

Allowed write performed by this worker:
  - `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINDINGS_LEDGER.md`

Forbidden writes not performed:
  - source RFCs
  - `CHANGELOG.md`
  - `OPERATOR_REPORT.md`
  - `DECISION_LOG.md`
  - code, tests, migrations, generated schema docs
  - Striatum state

Required validation command:

```sh
git diff --check -- docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINDINGS_LEDGER.md
```

Result: passed with exit code 0 and no output.
