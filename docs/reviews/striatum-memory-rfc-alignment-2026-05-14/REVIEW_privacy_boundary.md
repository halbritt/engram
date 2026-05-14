author: operator [self-declared: alignment-review-privacy]

# Striatum Memory RFC Alignment - Privacy Boundary Review

Status: review
Date: 2026-05-14
Run ID: run_169531d5568248ff8f0dfc803d955311
Workflow job ID: review_privacy_boundary
Job ID: job_run_169531d5568248ff8f0dfc803d955311_review_privacy_boundary
Session ID: sess_13a908ffc1e84eaab0020f4091046783
Lease ID: lease_cdae56e2eed64da0a9a3732538818cda

verdict: accept_with_findings

## Scope

This review evaluates the privacy and local-first boundary of the Striatum
memory RFC alignment workflow. Inputs are the proposal-text alignments to RFC
0046, RFC 0047, RFC 0048, and RFC 0049, plus the roadmap/index cleanup, against
the upstream Striatum memory roadmap RFC review package and the prior privacy
boundary review (`accept_with_findings`, 2026-05-14). Reviewer is reviewer-only;
no source artifact is modified by this pass.

Privacy axes evaluated:

- no cloud dependency, no telemetry, no user data leaving the machine without
  explicit operator approval;
- corpus identity, tenant/app/workspace labels, and audit surfaces must not
  leak unauthorized metadata;
- pairing/no-data/authorization failures must omit or redact corpus inventory
  and exact-reference details correctly;
- generated memory products must remain outside automatic retrieval/injection
  until a separate accepted privacy/audit gate exists;
- personal-memory functionality remains deferred in favor of Striatum-local
  workflow memory;
- the contract leaves room for future application memory systems to coexist
  under the same root authority while retaining app/workspace/corpus
  boundaries.

## Evidence Reviewed

Alignment handoffs (this workflow):

- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0046.md`
- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0047.md`
- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0048.md`
- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0049.md`
- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ROADMAP_INDEX_CLEANUP.md`

Source RFCs and canonical surfaces (current branch state):

- `docs/rfcs/0046-striatum-projection-index-schema.md`
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md`
- `docs/rfcs/0048-striatum-context-injection-policy.md`
- `docs/rfcs/0049-striatum-evaluation-gates.md`
- `STRIATUM_MEMORY_ROADMAP.md`
- `docs/rfcs/README.md`

Upstream review provenance:

- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_privacy_boundary.md`
  (PB-001..PB-012)
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINDINGS_LEDGER.md`
  (F001..F022)
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINAL_SYNTHESIS.md`
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_contract_coherence_repair.md`

Workflow context:

- `striatum/striatum-memory-rfc-alignment-2026-05-14/workflow.json`
- `striatum/striatum-memory-rfc-alignment-2026-05-14/RUNBOOK.md`

Independent read-only sub-agent lanes were used for cross-RFC consistency
checks: (a) unauthorized/no-data/pair-mismatch metadata redaction across RFC
0047/0048/0049, (b) path and dirty-working-tree privacy mirror across RFC
0045/0046/0047/0049, and (c) personal-memory and generated-product blockade
across RFC 0046/0047/0048/0049 plus the roadmap and index. All three sub-agents
returned successfully and edited no files.

## Top-Line Posture

The alignment workflow closed every blocking and every major privacy finding
that the prior privacy boundary review (PB-001..PB-006) and the contract
coherence repair (F001..F015) had carried into this run, at proposal-text
level:

- absolute-path/operator-private-path leakage is now blocked by RFC 0045
  validation and mirrored at projection time in RFC 0046
  (`docs/rfcs/0046-striatum-projection-index-schema.md:388-405, 1003-1005,
  1048-1049`);
- dirty-working-tree exports require manifest opt-in plus row-level
  `provenance.dirty_working_tree=true` and projected dirty rows carry
  `source_dirty_working_tree=true` distinguishable from clean committed
  evidence (`docs/rfcs/0046-striatum-projection-index-schema.md:163, 539-552,
  1009-1011, 1050-1052`);
- retrieval responses, failure diagnostics, and freshness rules now omit or
  null `corpus.bundle_ids`, `bundle_sha256s`, source-time bounds, staleness,
  hidden labels, row counts, and hidden paths on `unauthorized`, `no_data`,
  and pair-mismatch responses
  (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:351-358,
  390-404, 530-538, 706-708`);
- `identity.instance_label`, `identity.repository_label`, and
  `identity.repository_root_hint` are display-only, privacy-inherited, and
  must not appear in unauthorized/not-visible diagnostics
  (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:470-476,
  658-661, 710-711`);
- bundle-id examples are opaque (`striatum.bundle:<stable-local-id>`) with
  `bundle_sha256` represented separately as an integrity hash
  (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:293-294,
  334-335, 513-514, 569-570`);
- embeddings are computed only from persisted `chunk_text`, never from a
  pre-redaction or fully withheld body, with a deterministic fixture in RFC
  0046 (`docs/rfcs/0046-striatum-projection-index-schema.md:673-678, 792-794,
  1001-1002`);
- reference-collision/replay coverage is required at gate level for both
  Striatum-to-personal and the symmetric direction once
  `memory.read_personal` exists
  (`docs/rfcs/0046-striatum-projection-index-schema.md:1006-1008`,
  `docs/rfcs/0049-striatum-evaluation-gates.md:497-499`);
- audit records inherit the maximum privacy tier and use opaque request-local
  candidate ids for omitted higher-tier candidates
  (`docs/rfcs/0048-striatum-context-injection-policy.md:644-651`,
  `docs/rfcs/0049-striatum-evaluation-gates.md:831-836`);
- `identity_leak`, `citation_leak`, and `generated_product_blocked` omission
  reason codes exist as packet vocabulary and as gate-evidence vocabulary
  (`docs/rfcs/0048-striatum-context-injection-policy.md:266-293`,
  `docs/rfcs/0049-striatum-evaluation-gates.md:567-579, 723-729`);
- routine default-on automatic injection remains blocked until accepted or
  promoted RFC 0045-RFC 0048 successors exist and applicable RFC 0049 gates
  pass; generated memory products are explicitly blocked from Level 2 and
  Level 3 injection until a separate privacy-inheritance, citation, audit,
  and gate contract is accepted
  (`docs/rfcs/0048-striatum-context-injection-policy.md:230-236, 415-419,
  734-736`, `docs/rfcs/0049-striatum-evaluation-gates.md:270-289, 890-919`);
- personal memory requires `memory.read_personal` plus an explicit operator
  request and is never auto-injected by default; manual paste-through into a
  Striatum operator/agent packet requires explicit per-packet selection,
  current authorization, citation eligibility, privacy/redaction checks, and
  audit metadata (`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:478-481`,
  `docs/rfcs/0048-striatum-context-injection-policy.md:445-446, 581-587`,
  `docs/rfcs/0049-striatum-evaluation-gates.md:479-480, 984`);
- the roadmap and RFC index correctly state that RFC 0045-RFC 0049 do not
  authorize implementation, migrations, runtime behavior, or default-on
  Striatum memory without a separate recorded project decision or accepted
  spec handoff (`STRIATUM_MEMORY_ROADMAP.md:74-77, 254-260`,
  `docs/rfcs/README.md:65-69`);
- the projection schema leaves the door open for future local application
  memories under the same `tenant_id`/`corpus_id` discipline rather than
  locking the schema to Striatum only
  (`docs/rfcs/0046-striatum-projection-index-schema.md:181-183, 301-302,
  1122-1123`).

The findings below are non-blocking. They tighten residual surfaces that the
proposal-text alignment did not close, and they should be addressed before any
of the affected RFCs is promoted or implementation begins on the affected
surface.

## Blockers

None. The alignment workflow closed every blocking privacy finding that the
upstream privacy review and the contract-coherence repair carried.

## Nonblocking Findings

### AP-001 - General `raw_payload` privacy bound is missing across projection families
Severity: major (nonblocking before promotion; load-bearing before
implementation)
Affects:
- `docs/rfcs/0046-striatum-projection-index-schema.md` § Common Projection
  Columns; § striatum_chunk_embeddings; § striatum_embedding_skips
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md` § Response
  Contract; § Citation And Provenance
- `docs/rfcs/0048-striatum-context-injection-policy.md` § Context Eligibility
  Rules; § Tenant, Corpus, Privacy, And Redaction Filters
- `docs/rfcs/0049-striatum-evaluation-gates.md` § EG-060

Rationale: RFC 0046 places `raw_payload JSONB NOT NULL` on every projection
family (`docs/rfcs/0046-striatum-projection-index-schema.md:179, 257, 350,
593, 705, 748`) but states a privacy bound for `raw_payload` content only in
two narrow places: the dirty-working-tree audit hint
(`docs/rfcs/0046-striatum-projection-index-schema.md:547-548`) and embedding
skip rows (`docs/rfcs/0046-striatum-projection-index-schema.md:768-770`). RFC
0047's response contract does not name `raw_payload` at all, and RFC 0048's
eligibility rules speak of body excerpt/summary, not arbitrary
source-specific JSONB. RFC 0049 EG-060 enumerates `redaction_withheld`,
`privacy_tier_exceeded`, `identity_leak`, and `citation_leak` reason codes
but does not require fixtures proving `raw_payload` inherits the parent
item's `privacy_tier`, `redaction_state`, and `visibility`. An implementation
that follows the proposal text literally could persist or even surface
operator-private fields in `raw_payload` for non-dirty, non-skip projections
without tripping any current rule.

Proposed fix: add a Common Projection Columns sub-rule in RFC 0046 stating
that every `raw_payload` value inherits the parent item's `privacy_tier`,
`redaction_state`, and `visibility`, and that no field whose presence would
exceed those constraints may live in `raw_payload`. RFC 0047 should add a
sentence to the Response Contract noting that `raw_payload`-derived fields
are not part of the response unless the upstream contract whitelists them.
RFC 0049 EG-060 should add a fixture asserting that no retrieval-visible
`raw_payload` field surfaces content above the caller's tier.

### AP-002 - Dirty-working-tree state is not surfaced or gated at the retrieval boundary
Severity: minor (nonblocking before promotion; load-bearing before
implementation)
Affects:
- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md` § Response
  Contract; § Citation And Provenance; § Freshness And Truthfulness
- `docs/rfcs/0048-striatum-context-injection-policy.md` § Memory Item Shape;
  § Freshness And Stale-Memory Handling
- `docs/rfcs/0049-striatum-evaluation-gates.md` § EG-050; § EG-070

Rationale: RFC 0046 makes `source_dirty_working_tree=true` mandatory on every
projected dirty row and states that "Dirty evidence must not be presented as
clean committed state. Exact lookups, citations, health checks, and future
packet builders must be able to distinguish dirty working-tree evidence from
evidence tied only to committed Git objects"
(`docs/rfcs/0046-striatum-projection-index-schema.md:549-552`). RFC 0047's
response example and recommended citation rendering
(`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:299-345,
508-515`) carry no dirty flag and the failure/freshness tables
(`docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md:385-405,
522-542`) treat dirty as a stale concern only. RFC 0048's memory item shape
(`docs/rfcs/0048-striatum-context-injection-policy.md:329-336`) and freshness
labels (`docs/rfcs/0048-striatum-context-injection-policy.md:537-544`) do not
expose dirty state. RFC 0049 has no dedicated dirty-working-tree retrieval or
audit gate. A faithful packet-builder implementation could therefore present
a dirty-tree excerpt with a clean-looking citation despite the projection
carrying the flag. ALIGN_RFC0046 explicitly defers this to RFC 0047/0048
follow-up; this review records it so it is not lost.

Proposed fix: add a `dirty_working_tree=true|false` field to the RFC 0047
result row and the recommended citation rendering. Add a freshness label
`freshness=dirty_working_tree` (or equivalent) to RFC 0048 memory item shape
and audit fields. Add a Dirty-Working-Tree gate or sub-criterion to RFC 0049
covering both retrieval surface and audit reconstruction.

### AP-003 - RFC 0048 audit clause does not restate local-only/no-egress storage
Severity: minor (nonblocking before promotion; load-bearing before
implementation)
Affects:
- `docs/rfcs/0048-striatum-context-injection-policy.md` § Reviewability And
  Audit Trail
- `docs/rfcs/0049-striatum-evaluation-gates.md` § EG-110

Rationale: RFC 0049 EG-110 explicitly requires "audit records inherit the
maximum privacy tier of the selected or omitted items they identify, and
audit storage remains local-only and no-egress"
(`docs/rfcs/0049-striatum-evaluation-gates.md:835-841`). RFC 0048's
Reviewability And Audit Trail section
(`docs/rfcs/0048-striatum-context-injection-policy.md:619-655`) requires
privacy-tier inheritance and opaque request-local candidate ids but does not
restate the local-only/no-egress storage constraint at the policy level. RFC
0048 is the document an implementer is most likely to read when wiring audit
storage; the no-egress audit-storage rule should not depend on a reviewer
also reading the gate text.

Proposed fix: add one sentence to RFC 0048 § Reviewability And Audit Trail
stating that audit records and any audit storage are subject to the same
local-only/no-egress and tenant/corpus-isolation rules as retrieval
projections, and that audit-storage backends must not introduce a hosted or
network dependency.

### AP-004 - F017 cleanup is incomplete in RFC 0046 and RFC 0048 open-decision lists
Severity: nit
Affects:
- `docs/rfcs/0046-striatum-projection-index-schema.md` § Upstream Contract
  Assumptions item 5
- `docs/rfcs/0048-striatum-context-injection-policy.md` § RFC 0045
  Dependencies item 5

Rationale: ALIGN_RFC0049 cleaned up RFC 0049's open-decision text so that
"final redaction-state vocabulary" is no longer carried as an open RFC 0045
question. RFC 0046 still lists "5. final redaction-state vocabulary"
(`docs/rfcs/0046-striatum-projection-index-schema.md:86`) and RFC 0048 still
lists "5. final redaction-state vocabulary"
(`docs/rfcs/0048-striatum-context-injection-policy.md:144`) under their RFC
0045-dependent open decisions. The upstream finding ledger F017 explicitly
calls these stale (`docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINDINGS_LEDGER.md:372-385`).
Privacy implication is low (the actual redaction vocabulary is closed
upstream), but the stale text invites future drift where reviewers treat
redaction vocabulary as still negotiable.

Proposed fix: remove or restate item 5 in both lists so they match the RFC
0049 cleanup (e.g., "exact privacy-tier assignment policy Striatum can
guarantee before export").

### AP-005 - RFC 0049 EG-060 gate-local note about identity_leak/citation_leak is now stale
Severity: nit
Affects:
- `docs/rfcs/0049-striatum-evaluation-gates.md` § EG-060

Rationale: RFC 0049 EG-060 states that "`identity_leak` and `citation_leak`
are RFC 0049 gate-local omission reason codes until RFC 0048 or an accepted
successor reconciles them with packet omission vocabulary"
(`docs/rfcs/0049-striatum-evaluation-gates.md:567-571`). ALIGN_RFC0048
already added both codes to the RFC 0048 omission reason list
(`docs/rfcs/0048-striatum-context-injection-policy.md:266-293`). The
gate-local clause is therefore stale and could be read as authority that the
codes are not yet packet vocabulary.

Proposed fix: remove the "until RFC 0048 or an accepted successor
reconciles" qualifier or replace it with a pointer to the RFC 0048 omission
reason list.

### AP-006 - No RFC 0049 fixture exercises manual paste-through cross-boundary policy
Severity: nit
Affects:
- `docs/rfcs/0049-striatum-evaluation-gates.md` § EG-030; § EG-110

Rationale: ALIGN_RFC0048 added the explicit manual paste-through policy to
RFC 0048 (`docs/rfcs/0048-striatum-context-injection-policy.md:581-587`),
covering personal/non-primary results being copied into Striatum
operator/agent packets. The upstream privacy review PB-008 originally
proposed an EG-030 fixture exercising this manual-paste boundary. RFC 0049
does not currently include such a fixture; the closest coverage is EG-110
audit reconstruction (which assumes automatic packet) and EG-030 reference
replay (which targets default-token reads). For evidence completeness before
Level 1 manual search promotion, a manual-paste fixture should exist.

Proposed fix: add an EG-030 (or EG-110) sub-criterion that a packet
constructed from manual paste-through of a personal-memory or non-primary
result without per-packet operator opt-in fails the gate, and that an audit
record exists for any approved manual paste-through.

## Deferred Items

These items are nonblocking and should remain explicit deferrals until later
workflows. They were correctly handled by the alignment workflow as deferred
or out of write scope:

- F012 / EG-140: generated memory products remain blocked from Level 2 and
  Level 3 injection until a separate accepted privacy-inheritance, citation,
  audit, and gate contract exists. The placeholder gate is in place
  (`docs/rfcs/0049-striatum-evaluation-gates.md:890-919`,
  `docs/rfcs/0048-striatum-context-injection-policy.md:415-419, 734-736`).
  Personal memory remains outside default Striatum injection.
- F019: collapsed `no_data` packet-status ergonomics (low privacy impact;
  ergonomics-only).
- F020: RFC 0048 still lacks an explicit conflict-warning rule requiring both
  the omitted memory item and the current authority item; RFC 0049 carries it
  at gate level (`docs/rfcs/0049-striatum-evaluation-gates.md:549-550,
  754-757, 829-830`). Privacy impact is indirect.
- F022: session-scope disable persistence is now stated as transient unless
  explicitly promoted (`docs/rfcs/0048-striatum-context-injection-policy.md:612-617`).
  Operator-surprise risk after daemon restart is acknowledged.
- Reciprocal Striatum-side artifact proving Striatum has no Engram runtime
  dependency remains a separate dependency tracked under EG-130 and the RFC
  0044 ledger F007. The privacy posture of this RFC package does not depend
  on it landing, but routine operator workflows do.

## Workflow Friction

The following workflow friction was observed during this review and during
the upstream alignment lanes. None of it changes the privacy verdict; each
item is recorded so the operator can address recurrence.

- The Striatum doctor verification was reported as `doctor ok=false` in the
  run summary (`striatum/striatum-memory-rfc-alignment-2026-05-14/RUNBOOK.md:6`).
  No specific failure detail is in the summary; the operator should confirm
  that doctor failure does not mask a workflow-state inconsistency before
  publishing verdicts.
- The alignment author lanes consistently reported a sub-agent spawn
  rejection when combining `agent_type` with a full-history fork
  (ALIGN_RFC0046, ALIGN_RFC0047, ALIGN_RFC0048, ALIGN_RFC0049 friction
  sections). The retries succeeded as read-only explorers without the fork
  combination. This review encountered no such rejection because it issued
  read-only Explore agents directly, but the recurring author-lane failure
  suggests the documented spawn pattern in the workflow prompts may be
  inconsistent with the current runner restrictions.
- The workflow-prompt-named input directory
  `striatum/striatum-memory-rfc-alignment-2026-05-14/` did not contain the
  upstream synthesis, ledger, or contract-coherence repair artifacts. Every
  alignment lane and this review fell back to the corresponding files under
  `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/` (the actual
  committed location). The workflow prompt should be updated so future
  authors do not need to discover the redirection independently.
- The shared worktree carried out-of-scope edits to `CHANGELOG.md`,
  `OPERATOR_REPORT.md`, and other paths during the alignment lanes. Each
  alignment lane noted those entries and did not edit them. This review also
  did not edit them. The operator should reconcile the worktree before
  publishing.
- The alignment review directory itself
  (`docs/reviews/striatum-memory-rfc-alignment-2026-05-14/`) had to be
  created by the first alignment author because it did not exist when the
  workflow prompts were issued. Subsequent lanes (including this review)
  reused that directory.
- Sub-agent independence: this review used three parallel read-only Explore
  agents for cross-RFC consistency checks (unauthorized metadata, path/dirty
  privacy mirror, generated-product/personal-memory blockade). All three
  returned successfully. Their findings were folded into the AP-001..AP-006
  block above; no agent edited files.

## Validation

- Whitespace check (this artifact only):
  `git diff --no-index --check /dev/null docs/reviews/striatum-memory-rfc-alignment-2026-05-14/REVIEW_privacy_boundary.md`
- This review is reviewer-only. No source RFC, source roadmap, source RFC
  index, alignment handoff, code, migration, generated schema doc, test,
  CHANGELOG, DECISION_LOG, OPERATOR_REPORT, or `.striatum/` file was modified
  by this pass. No Striatum publish/complete/verdict command was run.
