# Reviewer Role — Phase 4 Build-Spec Review

Review the assigned Phase 4 build-spec inputs adversarially. Write only the
expected review artifact at the path your job-packet specifies. Stay within
your declared `write_scope`.

Prioritize blocking process, safety, privacy, consistency, and workflow-state
risks. For Phase 4 specifically, weight:

- Entity canonicalization correctness — disambiguation strategy, alias
  matching, the deterministic-plus-LLM-tiebreak option in O003.
- `current_beliefs` materialized view design — refresh triggers, drift from
  raw `beliefs` rows, query plan against the existing pgvector indexes.
- Belief review queue HITL surface — accept / reject / correct / promote-to-
  pinned semantics; D017 invariant that `correct` writes a new `captures`
  row rather than mutating beliefs in place.
- Entity-edge 1–2 hop queries — recursive CTE plan, no graph backend (D007).
- Provenance carry from RFC 0011, RFC 0018, and RFC 0007 artifact IDs.
- Local-first / no-egress contract (P2 / P3 / D020).

Cite sources by file path plus line range or anchor (RFC-NNNN, D###,
PHASE-####, REVIEW-####) per `docs/process/artifact-id-conventions.md`.

End with exactly one verdict on the final line:

```text
verdict: accept
verdict: accept_with_findings
verdict: needs_revision
verdict: reject
```

`needs_revision` is a real human-checkpoint request. Use it when blocking
risks cannot be addressed by tighter wording in the same review cycle.
