# Striatum Memory Roadmap RFCs - Privacy Boundary Review
author: operator [self-declared: roadmap-review-privacy-boundary]

Status: review
Date: 2026-05-14
Run ID: run_500d0f049ea04038b0e19d6045daf918
Workflow job ID: review_privacy_boundary
Job ID: job_run_500d0f049ea04038b0e19d6045daf918_review_privacy_boundary
Session ID: sess_04c1cd744a4d4f40a10cadf7dbe5fb6d
Lease ID: lease_88433a17b1ca44c3b2725b38de3c1039

Scope: Privacy boundary review of the Striatum memory roadmap RFC package
(RFC 0045 corpus contract V2, RFC 0046 projection/index schema, RFC 0047
retrieval augmentation boundary, RFC 0048 context-injection policy, RFC 0049
evaluation gates) and the accompanying `STRIATUM_MEMORY_ROADMAP.md`. The
review evaluates local-only/no-egress posture, tenant/corpus isolation,
personal-memory default denial, capability boundaries, redaction/privacy
metadata, and Striatum-not-dependent-on-Engram.

Verdict: accept_with_findings

## Top-Line Summary

The five RFCs, read together, articulate the privacy boundary that
`HUMAN_REQUIREMENTS.md` and the RFC 0044 final synthesis require:

- corpus-reading processes are local-only and no-egress;
- `tenant_id='striatum'` is the local application-memory boundary and
  `corpus_id` is the inner workload boundary, with shorthand limited to the
  sanctioned `striatum -> striatum/striatum` convenience case;
- default Striatum operator tokens cannot read personal memory, and personal
  memory cannot enter Striatum automatic injection;
- visible-pair grants are not read-grants; cross-corpus and cross-tenant reads
  require explicit Engram-local capabilities;
- retrieved memory is evidence/context only, never instructions or
  authoritative Striatum state;
- Striatum must continue to function with Engram absent, disabled, unhealthy,
  unauthorized, stale, malformed, slow, or timed out;
- RFC 0049 names the evidence gates that block routine default-on automatic
  injection until they pass.

The package is internally consistent with RFC 0044 acceptance findings and
preserves the load-bearing local-first constraint. The findings below are
hardening and clarification, not architectural reversals. Accepting the package
with these findings does not relax the boundary; it tightens specific gaps that
could let private data leak through manifest metadata, projection columns,
retrieval responses, or implicit fallbacks.

## Findings (ordered by severity)

### PB-001 - Item-level absolute-path leakage is not closed by RFC 0045 validation
Severity: major
Affects:
- `docs/rfcs/0045-striatum-corpus-contract-v2.md` § Validation Rules
- `docs/rfcs/0045-striatum-corpus-contract-v2.md` § Item Record Shape
- `docs/rfcs/0046-striatum-projection-index-schema.md` § striatum_items, § striatum_chunks

Rationale: RFC 0045's validator rule "absolute-path leakage in fields
designated as display hints unless the manifest declares explicit operator
opt-in" only binds the manifest's `repository_root_hint` field. Item-level
`provenance.path`, `provenance.logical_path`, and chunk `path` fields can still
carry absolute or operator-private paths because the RFC requires only that
provenance be "retraceable". RFC 0046 then stores these directly in
`striatum_items.source_path`, `striatum_items.logical_path`,
`striatum_chunks.path`, and `striatum_references.ref_value`. Projection rows
become a durable copy of any operator-private directory layout exported by
Striatum. The RFC 0046 git projection has explicit `author_email_hash`
handling for similar reasons, but path fields have no parallel rule.

Proposed fix: add a V2 validation rule that item-level path-shaped fields
(`provenance.path`, `provenance.logical_path`, chunk path, and any
`striatum_references` `ref_kind in {path, logical_path}` value) must be
repository-relative unless the manifest explicitly opts into absolute-path
export, and must omit operator home directory prefixes (`/home/<user>`,
`/Users/<user>`, `/root`, Windows user profile equivalents) by default. RFC
0046 should mirror that rule at projection time so a misbehaving exporter is
caught before retrieval can serve operator-private paths.

### PB-002 - Manifest `git_dirty=true` exports may leak unmerged local state
Severity: major
Affects:
- `docs/rfcs/0045-striatum-corpus-contract-v2.md` § Manifest Shape
- `docs/rfcs/0045-striatum-corpus-contract-v2.md` § Identity Rules
- `docs/rfcs/0046-striatum-projection-index-schema.md` § striatum_git_refs

Rationale: RFC 0045's manifest carries `git_head` and `git_dirty`, but does not
specify behavior when `git_dirty=true`. A dirty working tree can include
unmerged branches, abandoned experiments, personal notes pasted into a
scratchpad file, or in-progress credentials in `.env`-shaped untracked files.
If Striatum's exporter walks the working tree, the bundle can pull content
the operator never intended to land in committed history. RFC 0046's
`striatum_git_refs` stores `changed_paths` and `diff_summary` that would
persist that leak in projections.

Proposed fix: require the V2 exporter to either refuse `git_dirty=true`
exports by default, or label every dirty-export item with a
`provenance.dirty_working_tree=true` flag and require an explicit operator
opt-in in the manifest. RFC 0046 should refuse to project dirty-export items
into retrieval-visible chunks/references unless the activation step records
the operator opt-in source.

### PB-003 - Retrieval response leaks corpus inventory through `corpus.bundle_ids`/time bounds
Severity: major
Affects:
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md` § Response Contract
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md` § Failure Behavior
- `docs/rfcs/0048-striatum-context-injection-policy.md` § Section Labels And Packet Shape

Rationale: Every retrieval response carries `corpus.bundle_ids`,
`corpus.source_time_min`, `corpus.source_time_max`, and `staleness_seconds`.
RFC 0047 carefully forbids `engram.describe_corpus` and `engram.health` from
revealing hidden personal corpus names, counts, or freshness metadata to a
default Striatum token, but the retrieval response shape is exempt from that
rule. A repeated probe through `engram.search` against a non-default
`(tenant_id, corpus_id)` pair could distinguish "unauthorized" from
"unauthorized but exists" by observing whether `corpus.bundle_ids` or time
bounds are populated even when `results=[]`. The injection policy will pass
the same `corpus.*` block into the audit trail (RFC 0048 § Audit Trail).

Proposed fix: state in RFC 0047 that `corpus.bundle_ids`, `source_time_min`,
`source_time_max`, and `staleness_seconds` are populated only for pairs the
caller is authorized to read, and that all four collapse to `null` or are
omitted on `unauthorized`, `no_data`, or pair-mismatch responses. RFC 0048
should add a packet-shape rule that audit/header fields never display
`corpus.*` metadata for pairs the caller cannot read.

### PB-004 - `repository_label` and `instance_label` lack a privacy-tier rule
Severity: major
Affects:
- `docs/rfcs/0045-striatum-corpus-contract-v2.md` § Manifest Shape
- `docs/rfcs/0045-striatum-corpus-contract-v2.md` § Identity Rules
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md` § Tenant And Corpus Isolation

Rationale: V2 manifest fields `identity.instance_label` and
`identity.repository_label` are operator-visible labels with no constraints on
content. An operator who labels a repository `client-x-secret-project` or an
instance `personal-research-machine` will have those labels echoed through
RFC 0046 projection metadata (`raw_payload`), and downstream UI/search
diagnostics. The RFCs say labels are not authorization grants but do not say
labels must respect the highest privacy tier of the items they describe, nor
that labels should never appear in agent-visible diagnostics when the token
cannot read the underlying corpus.

Proposed fix: add a V2 rule that labels inherit the maximum privacy tier of
items they identify, and that labels must not appear in agent-visible
diagnostics for pairs the caller is not authorized to read. RFC 0047 should
explicitly add `instance_label` and `repository_label` to the list of fields
that are not access grants and must not be leaked into unauthorized-response
diagnostics.

### PB-005 - Embedding boundary does not explicitly forbid embedding withheld content bodies
Severity: major
Affects:
- `docs/rfcs/0046-striatum-projection-index-schema.md` § striatum_chunks
- `docs/rfcs/0046-striatum-projection-index-schema.md` § striatum_chunk_embeddings
- `docs/rfcs/0046-striatum-projection-index-schema.md` § Embedding boundaries

Rationale: The chunk vocabulary includes `redaction_notice` for withheld
items, and `striatum_chunk_embeddings` carries `privacy_tier`. But the RFC
does not state that fully withheld bodies must not produce embeddings of the
withheld text. A naive implementation could call the local embedder on the
withheld content before substituting the redaction notice, leaving an
embedding row that allows nearest-neighbor recovery of withheld content even
though `chunk_text` was sanitized.

Proposed fix: state in RFC 0046 that embeddings are computed only over the
content that appears in `chunk_text`. If `chunk_text` is a deterministic
redaction notice, the embedding is over the notice, not the original
withheld content. Add a fixture in RFC 0049 EG-060 that fails if a vector
nearest-neighbor query against a known withheld phrase returns its chunk.

### PB-006 - Personal-memory and Striatum reference-ID collisions are not tested
Severity: major
Affects:
- `docs/rfcs/0049-striatum-evaluation-gates.md` § EG-030 Tenant, Corpus, And Personal-Memory Isolation Gate
- `docs/rfcs/0049-striatum-evaluation-gates.md` § EG-040 fetch_reference And MCP/Reference Hardening Gate
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md` § Tenant And Corpus Isolation

Rationale: RFC 0047 and the RFC 0044 final synthesis require
`engram.fetch_reference` to reauthorize the stored row's tenant/corpus pair.
RFC 0049 EG-040 covers that requirement at the boundary level. Neither RFC
specifies a test where a `reference_id` issued under a Striatum token is then
replayed against a personal-memory row (or vice versa) by crafting a
collision-shaped payload. RFC 0044 finding F009 already showed that decoded
reference payloads can carry unvalidated values. The proposed gate set should
test that case explicitly rather than infer it from primary-pair regressions.

Proposed fix: extend EG-030 (or EG-040) with a fixture/test that constructs a
`reference_id` whose decoded row pointer targets a personal-memory row, then
verifies that a default Striatum token cannot fetch it and that the error
shape is the uniform unauthorized/not-found collapse. Add a symmetric
fixture in the reverse direction once a `memory.read_personal` token exists.

### PB-007 - RFC 0044 hardening dependency tracking
Severity: minor
Affects:
- `docs/rfcs/0045-striatum-corpus-contract-v2.md` § Dependencies
- `docs/rfcs/0046-striatum-projection-index-schema.md` § Upstream Contract Assumptions
- `docs/rfcs/0049-striatum-evaluation-gates.md` § EG-000 RFC 0044 Hardening Baseline
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/FINDINGS_LEDGER.md` F004, F009

Rationale: Several findings in the RFC 0044 ledger (F004 structural
tenant/source-kind consistency, F009 malformed decoded UUID handling) are
upstream of the privacy properties asserted in RFCs 0045-0049. The package
correctly names "RFC 0044 hardening cleanup" as a dependency, but only RFC
0049 EG-000 enumerates the specific items. RFC 0045 § Dependencies and RFC
0046 § Upstream Contract Assumptions should reference the ledger findings by
ID so a reviewer can trace which hardening items must land before each
downstream RFC is implementable.

Proposed fix: add an inline `RFC 0044 ledger preconditions` list to RFC 0045
and RFC 0046 naming F004 and F009 explicitly, so the privacy boundary cannot
be silently weakened by skipping a referenced cleanup item during
implementation planning.

### PB-008 - Manual search privacy boundary is implicit, not stated
Severity: minor
Affects:
- `docs/rfcs/0048-striatum-context-injection-policy.md` § Manual Versus Automatic Augmentation
- `docs/rfcs/0049-striatum-evaluation-gates.md` § Level 1 Manual/Local Operator Search

Rationale: Manual search is allowed earlier than automatic injection and
"still obeys tenant/corpus, privacy, redaction, no-egress, and citation
rules". The RFC does not explicitly forbid an operator who issues a manual
personal-memory search from copying that result back into a Striatum
operator/agent packet as plain text. The audit trail provisions in
RFC 0048 cover automatic injection but not manual paste-through.

Proposed fix: state in RFC 0048 that manual search results from a personal
or non-primary corpus must not be copied into Striatum operator or agent
context without an explicit per-packet operator opt-in and an audit-trail
entry recording the cross-boundary action. RFC 0049 EG-030 personal-memory
negative cases should add one fixture that exercises this manual-paste
boundary.

### PB-009 - No-egress evidence does not distinguish loopback Postgres from network
Severity: minor
Affects:
- `docs/rfcs/0049-striatum-evaluation-gates.md` § EG-020 No-Egress Gate
- `docs/rfcs/0046-striatum-projection-index-schema.md` § Design Principles
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md` § No-Egress And Local-Only Boundary

Rationale: EG-020 requires the sandbox to allow only "required local
resources" and explicitly names loopback Postgres, Ollama, and local model
runtimes. It does not require evidence that the loopback policy is enforced
at the OS layer rather than only by the Postgres bind address. A misconfigured
local Postgres listening on `0.0.0.0` plus a permissive firewall can let
corpus content reach a non-loopback interface even without the corpus-reading
process making an outbound connection.

Proposed fix: add an EG-020 sub-criterion requiring evidence that the
PostgreSQL instance hosting Engram raw evidence and projections is bound to
`127.0.0.1` (or equivalent local-only socket), and that the sandbox probe
verifies the corpus-reading command cannot reach a non-loopback IP even when
network policy allows loopback Postgres.

### PB-010 - Audit-trail field set may itself leak across boundary
Severity: minor
Affects:
- `docs/rfcs/0048-striatum-context-injection-policy.md` § Reviewability And Audit Trail
- `docs/rfcs/0049-striatum-evaluation-gates.md` § EG-110 Audit-Trail Reconstruction Gate

Rationale: The audit trail captures `request_id`, `query_text`, `filters`,
`tenant/corpus pair`, `selected reference_id/item_id/logical_id/version_id`,
`omitted reference reason codes`, and `privacy/redaction labels`. If audit
records are stored in a generic shared log or surfaced into operator
diagnostics without a privacy-tier filter, those fields can encode the
existence of higher-tier or personal-memory items the caller was not allowed
to read. RFC 0048 names the fields but does not pin their storage tier or
visibility.

Proposed fix: add an explicit rule to RFC 0048 § Reviewability And Audit
Trail that audit records inherit the maximum privacy tier of the items they
reference, that omitted-reason audit entries for higher-tier items use
opaque references rather than `item_id`/`logical_id`, and that audit storage
itself is bound by the same no-egress and local-only constraints as
projections. RFC 0049 EG-110 should add an explicit assertion that audit
reconstruction does not require reading rows the caller is not authorized
to read.

### PB-011 - Memory section omitted-reason codes do not include path/label leak detection
Severity: nit
Affects:
- `docs/rfcs/0048-striatum-context-injection-policy.md` § Context Eligibility Rules

Rationale: The omission reason code vocabulary covers `privacy_tier_exceeded`,
`redaction_withheld`, and `current_state_conflict`, but does not include a
reason for "result rendered would leak operator-private path or label" or
"result inherits a higher-tier identity field". Without a named reason code,
an implementation can silently emit a result whose excerpt is acceptable but
whose citation echoes an absolute path or a higher-tier label.

Proposed fix: add omission reason codes such as `identity_leak` or
`citation_leak`, with explicit semantics: emitted when the result's body is
eligible but the citation/identity payload contains operator-private paths,
absolute paths, or labels above the caller's allowed privacy tier.

### PB-012 - "Generated memory products" privacy gate is deferred but not named in gate matrix
Severity: nit
Affects:
- `STRIATUM_MEMORY_ROADMAP.md` § Phase 6 Produce Derived Memory Products
- `docs/rfcs/0048-striatum-context-injection-policy.md` § Deferred Questions item 6
- `docs/rfcs/0049-striatum-evaluation-gates.md` § Deferred Questions item 9

Rationale: The roadmap names derived memory products (known-friction ledger,
prior-decisions index, RFC lineage map, etc.) as a future phase, and RFC 0048
correctly defers whether those products may be automatically injected. RFC
0049 names this as a deferred question. There is no explicit gate that says
generated memory products must inherit the maximum privacy tier of their
sources before they may enter even manual augmentation.

Proposed fix: when the deferred decision is taken, add a dedicated gate
(e.g. `EG-140 generated-product privacy inheritance`) that requires every
derived memory product to carry the maximum privacy tier of every cited raw
item plus a separate audit step. Until then, state in RFC 0048 that derived
products are not eligible for any injection path until that gate exists.

## Explicit Posture Notes

The findings above are tightening, not reversals. The RFC package's posture
on the load-bearing properties is sound:

- **Local-only/no-egress**: RFC 0045 validation, RFC 0046 projection workers,
  RFC 0047 invocation surfaces, RFC 0048 injection policy, and RFC 0049
  EG-020 all converge on "no HTTP/DNS/socket/hosted SDK/telemetry from any
  corpus-reading process". RFC 0049 separates code-inspection evidence from
  sandbox-probe evidence and gates routine default-on injection on the
  stronger evidence. Finding PB-009 is a refinement, not a contradiction.
- **Tenant/corpus isolation**: RFC 0045 fixes
  `memory_target.tenant_id='striatum'` and forbids `corpus_id='personal'`.
  RFC 0046 makes `tenant_id`/`corpus_id` mandatory on every projection row
  and partial-index predicate. RFC 0047 fixes `engram.fetch_reference`
  reauthorization. RFC 0048 forbids cross-boundary shorthand outside the
  sanctioned `striatum/striatum` default. RFC 0049 EG-030/EG-040 require
  service+MCP+CLI coverage. The remaining gaps are reference-collision
  testing (PB-006) and label-tier rules (PB-004).
- **Personal-memory default denial**: every RFC restates that personal memory
  requires `memory.read_personal` and is never auto-injected into Striatum
  packets. RFC 0049 EG-030 makes this a gate. Findings PB-006 and PB-008
  add coverage to manual and reference-replay surfaces.
- **Capability boundaries**: RFC 0047 § Tenant And Corpus Isolation and RFC
  0048 § Tenant, Corpus, Privacy, And Redaction Filters spell out
  `memory.read_striatum`, `memory.read_cross_corpus`, `memory.read_cross_tenant`,
  `memory.read_personal`, and `memory.describe`. Bundle identity, instance
  identity, repository identity, labels, paths, discovery metadata, and
  opaque `reference_id` values are explicitly not authorization grants.
  RFC 0049 EG-040 enforces the rule that a reference issued under one scope
  cannot be replayed under a weaker scope.
- **Redaction/privacy metadata**: RFC 0045 mandates `privacy.privacy_tier`,
  `privacy.redaction_state`, `privacy.redaction_profile`,
  `privacy.withheld_fields`, `visibility.default_visible_to`, and
  `visibility.requires_capabilities` on every item. RFC 0046 copies tier and
  redaction state onto every retrieval-visible row, mandates invalidation
  before lower-tier reads, and includes a `redaction_notice` chunk kind.
  RFC 0048 omission reason codes preserve the explicit-omission discipline.
  Findings PB-005 (embedding boundary) and PB-001 (path-shaped leak) close
  the remaining specific holes.
- **Striatum-not-dependent-on-Engram**: RFC 0047 § Compatibility With
  Striatum Without Engram and RFC 0049 EG-130 require Striatum to install,
  test, prepare packets, run, review, recover, and produce artifacts without
  Engram on `PATH`. RFC 0048 keeps every memory failure mode non-fatal and
  the timeout budgets in RFC 0047 are bounded. The reciprocal Striatum-side
  artifact is correctly tracked as an open dependency (F007 in the RFC 0044
  ledger). The privacy posture itself does not depend on the reciprocal
  artifact landing, but routine operator workflows do.

## Residual Risks (under accept_with_findings)

- Findings PB-001 through PB-006 are all "major" because they describe paths
  by which private operator data (paths, dirty trees, corpus inventory,
  labels, withheld embeddings, replayed references) could persist or surface
  without an explicit operator decision. None of them constitutes a current
  capability bypass; they are leak surfaces that the proposal language does
  not yet close. They should be resolved before implementation lands on the
  affected RFCs.
- Findings PB-007 through PB-010 are coherence/coverage gaps that, if left
  open, would let later implementation drift weaken the boundary without
  triggering a review. They should be folded into the relevant RFC text and
  the RFC 0049 gate matrix.
- Findings PB-011 and PB-012 are vocabulary/scope nits. They can land
  alongside the higher-severity fixes or in the first implementation pass
  for RFC 0048/RFC 0049.

## Suggested Follow-Up

1. Update RFC 0045 with: item-level path normalization rule (PB-001), dirty-tree
   export policy (PB-002), label privacy-tier rule (PB-004), and an explicit
   pointer to RFC 0044 ledger findings F004/F009 in § Dependencies (PB-007).
2. Update RFC 0046 with: embedding boundary clarification (PB-005), path-field
   handling that mirrors `author_email_hash` (PB-001), and the ledger
   precondition pointer (PB-007).
3. Update RFC 0047 with: response-metadata redaction for unauthorized pairs
   (PB-003) and an explicit label non-grant clause (PB-004).
4. Update RFC 0048 with: audit-record privacy-tier rule (PB-010), manual
   paste-through rule (PB-008), and additional omission reason codes
   (PB-011).
5. Update RFC 0049 with: reference-collision negative cases (PB-006),
   loopback-Postgres binding evidence (PB-009), audit-trail
   authorization-coverage assertion (PB-010), and a placeholder gate for
   generated memory products (PB-012).
6. Re-run a multi-agent review loop after the originating authors synthesize
   these findings; the cross-RFC nature of PB-001, PB-003, and PB-004 means
   single-RFC review will miss the gap.

## Validation Evidence

This review artifact is a single new file under
`docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/`. Whitespace validation:

```sh
git diff --check -- docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_privacy_boundary.md
```

Result: passed with no output (the path is untracked, so the check returns
clean).

A secondary no-index whitespace probe:

```sh
git diff --check --no-index /dev/null docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_privacy_boundary.md
```

Exits non-zero because the file differs from `/dev/null`, which is expected
behavior and not a whitespace finding.

No code, migration, generated schema doc, test, source-of-truth document,
CHANGELOG, DECISION_LOG, OPERATOR_REPORT, RFC, or `.striatum/` file was
modified by this review. Inputs read before writing:

- `AGENTS.md`, `README.md`, `HUMAN_REQUIREMENTS.md`, `DECISION_LOG.md` (review
  pass), `BUILD_PHASES.md`, `ROADMAP.md` (referenced via package), `SPEC.md`,
  `STRIATUM_MEMORY_ROADMAP.md`, `docs/schema/README.md` (referenced via
  package);
- `docs/rfcs/0045-striatum-corpus-contract-v2.md`,
  `docs/rfcs/0046-striatum-projection-index-schema.md`,
  `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md`,
  `docs/rfcs/0048-striatum-context-injection-policy.md`,
  `docs/rfcs/0049-striatum-evaluation-gates.md`;
- `docs/reviews/rfc0045-striatum-corpus-contract-v2/SPEC_HANDOFF.md`,
  `docs/reviews/rfc0046-striatum-projection-index-schema/SPEC_HANDOFF.md`,
  `docs/reviews/rfc0047-striatum-retrieval-augmentation-boundary/SPEC_HANDOFF.md`,
  `docs/reviews/rfc0048-striatum-context-injection-policy/SPEC_HANDOFF.md`,
  `docs/reviews/rfc0049-striatum-evaluation-gates/SPEC_HANDOFF.md`;
- `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/FINAL_SYNTHESIS.md`,
  `docs/reviews/rfc0044-engram-memory-phase1-tenant-isolation-2026-05-13/FINDINGS_LEDGER.md`.
