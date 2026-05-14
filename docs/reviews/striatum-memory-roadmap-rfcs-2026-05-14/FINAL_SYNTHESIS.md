---
schema_version: "striatum.synthesis.v1"
artifact_kind: "synthesis"
---

# Striatum Memory Roadmap RFC Final Synthesis
author: operator [self-declared: roadmap-final-synthesis]

Status: synthesis
Date: 2026-05-14
Run ID: run_500d0f049ea04038b0e19d6045daf918

## Outcome

This synthesis accepts the Striatum memory roadmap/RFC package as proposal
evidence and review provenance only. It does not promote RFC 0045-RFC 0049,
authorize implementation, change canonical architecture, create migrations,
alter runtime behavior, or enable default-on Striatum memory. Future
implementation must target an accepted/promoted spec or recorded project
decision.

The original contract-coherence `needs_revision` blocker was repaired and
superseded. The bounded repair re-review found no remaining blockers, and the
operator accepted that late evidence path with follow-up. No original
contract-coherence finding remains blocking, and no human checkpoint remains
for this workflow. The operator may close the findings-ledger/final-synthesis
workflow; Striatum state transitions remain operator-owned and are not
performed by this artifact.

Routine default-on automatic Striatum memory remains blocked until accepted or
promoted RFC 0045-RFC 0048 successors exist and all applicable RFC 0049 gates
pass. Generated memory products remain blocked from Level 2 and Level 3
injection until a separate accepted privacy-inheritance, citation, and audit
contract exists.

## Finding Disposition

| Classification | Findings | Operator posture |
|---|---|---|
| Accepted | F001, F005, F006, F007, F020, F021 | Valid findings. Proposal text is repaired or adequate, but implementation/gate evidence is still required before affected runtime surfaces. |
| Accepted with modification or alignment follow-up | F002, F003, F004, F008, F009, F010, F011, F013, F014, F015, F016 | Carry as nonblocking current-workflow follow-up, but resolve or explicitly scope-limit before the named RFC promotion or any implementation that depends on the affected contract. |
| Accepted cleanup | F017, F018 | Clean up stale open-decision and roadmap text before a final promotion packet. |
| Deferred | F012, F019, F022 | Generated-product privacy contract, collapsed no-data status ergonomics, and session-disable persistence should remain explicit deferred/open work unless a promotion packet chooses to resolve them. |
| Rejected | none | No ledger finding is rejected by this synthesis. |

## Next Actions Before RFC Promotion

1. RFC 0047 retrieval-contract alignment: repair unauthorized/no-data/pair
   mismatch metadata redaction, privacy treatment for repository/instance
   labels, and SHA-shaped bundle identity examples. This covers F003, F004,
   and F013.
2. RFC 0046 projection/index alignment: add `workflow_job_id` and `job_id` to
   exact-reference vocabulary and define `striatum_embedding_skips`
   invalidation semantics. This covers F014 and F015, and should include the
   dirty-export projection mirror from F002.
3. RFC 0048 injection/audit policy alignment: add explicit manual paste-through
   policy, lower-tier audit redaction/privacy inheritance, `identity_leak` and
   `citation_leak` omission reasons, and stronger default-on/audit wording
   aligned to RFC 0049. This covers F008, F010, F011, F016, and F022.
4. RFC 0049 gate cleanup: clarify EG-020 as banning external or unpaired HTTP
   clients while allowing paired loopback/local runtimes with no-egress
   evidence; align exact-reference coverage with RFC 0046; remove stale
   redaction-state open-decision text. This covers F009, F014, and F017.
5. Roadmap/index cleanup: update stale `STRIATUM_MEMORY_ROADMAP.md` next-step
   text and, if promotion occurs, update `docs/rfcs/README.md` plus the
   canonical decision surface named by the operator. Binding architecture still
   belongs in `DECISION_LOG.md`; sequencing changes belong in `BUILD_PHASES.md`
   or `ROADMAP.md`.

## Next Actions Before Implementation

Implementation remains blocked on an accepted/promoted contract. When such a
contract exists, implementation must still prove the high-risk behaviors before
retrieval-visible rows, packet construction, or injection are enabled:

- path normalization, absolute-path/user-profile opt-in, and citation leak
  prevention;
- dirty working tree refusal or explicit opt-in carried through exporter and
  projection behavior;
- unauthorized/not-found and pair-mismatch metadata collapse;
- repository/instance label privacy inheritance;
- withheld-body embedding prevention, including redaction-only vector inputs;
- reference replay/collision protection;
- RFC 0044 Phase 0 hardening or EG-000-equivalent evidence;
- OS-level no-egress evidence for the caller and every transitive local runtime
  that receives corpus text;
- audit privacy inheritance, opaque omitted-candidate records, and packet
  reconstruction without lower-tier leaks;
- conflict warning audit behavior and cold-start/warm-cache latency evidence.

## Next Actions Before Routine Striatum Operator Use

Default-on Level 3 automatic memory is not ready. Before routine use, the
operator needs accepted/promoted RFC 0045-RFC 0048 successors, passing RFC 0049
gates, RFC 0044 hardening evidence, and measured packet/startup behavior inside
the automatic budget.

Level 1 manual/local search may be considered earlier only under the RFC 0049
constraints: explicit local read-only use, cited and scope-limited output,
service/MCP authorization, no automatic injection, and raw-only labeling if it
uses RFC 0044 while RFC 0045/RFC 0046 remain unaccepted. This synthesis does not
enable that mode.

Generated memory products are out of scope for routine Level 2/Level 3
injection until a separate privacy-inheritance, citation, and audit contract is
accepted and gated.

## Deferred Personal-Memory Implications

Personal memory remains outside the default Striatum operator token and outside
default Striatum injection. Later personal-memory exposure needs separate
approval and gate evidence, including:

- `memory.read_personal` as an explicit capability, never an implication of
  Striatum corpus access;
- reference replay tests covering Striatum-to-personal and personal-to-Striatum
  collisions;
- unauthorized/not-found metadata collapse for personal corpus probing;
- explicit per-packet opt-in and audit for any manual paste-through from
  personal or non-primary memory;
- lower-tier audit views that do not leak personal-memory metadata;
- generated-product privacy inheritance before any derived personal-memory item
  can enter injection.

## Highest-Priority Follow-Up Workflows

1. Queue a non-implementation RFC alignment workflow for RFC 0047/RFC 0046/RFC
   0048/RFC 0049. This is the highest-priority promotion blocker because it
   resolves the nonblocking but important repair re-review findings now carried
   as follow-up.
2. Queue an RFC 0044 hardening/EG-000 evidence workflow before any projection,
   retrieval, or operator-context implementation depends on the current Phase 1
   Striatum memory substrate.
3. Queue a promotion packet only after the alignment workflow is complete. That
   packet should decide whether to promote accepted specs, record binding
   decisions, and update the RFC index/roadmap.
4. Keep generated memory products and personal-memory default injection
   deferred until a separate privacy-inheritance, citation, audit, and gate
   package exists.

## Final Recommendation

Close this Striatum review workflow as `accepted_with_follow_up`: the blocker is
superseded and no human checkpoint remains, but do not promote RFC 0045-RFC
0049 or start implementation from this package. The next operator move should
be a focused RFC alignment workflow, followed by RFC 0044 hardening evidence,
then a separate promotion decision.

## Validation

Read inputs:

- `AGENTS.md` and canonical project docs required by repo instructions.
- `striatum/striatum-memory-roadmap-rfcs-2026-05-14/prompts/synthesis.md`.
- `docs/process/multi-agent-review-loop.md`.
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINDINGS_LEDGER.md`.
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REVIEW_contract_coherence_repair.md`.
- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/OPERATOR_DECISION_ACCEPT_CONTRACT_REPAIR_REVIEW.md`.

Read-only sub-agent lanes were used for blocker posture, implementation
blockers, RFC-promotion follow-ups, and routine-use/personal-memory
implications. No source RFCs, `CHANGELOG.md`, `OPERATOR_REPORT.md`,
`DECISION_LOG.md`, code, tests, migrations, schema docs, or Striatum state were
modified by this worker.

Allowed write:

- `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINAL_SYNTHESIS.md`

Required validation command:

```sh
git diff --check -- docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/FINAL_SYNTHESIS.md
```

Result: passed with exit code 0 and no output.
