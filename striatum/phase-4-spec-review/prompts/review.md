# Phase 4 Build-Spec Review — Task

You are reviewing the Phase 4 build-spec inputs. There is no dedicated Phase
4 spec doc yet; the inputs you review define what such a spec would have to
account for. Your job is to surface the risks, gaps, and decisions a Phase
4 spec author needs to resolve before writing.

## Inputs (delivered with your packet)

- `BUILD_PHASES.md` § Phase 4 — the current acceptance criteria.
- `HUMAN_REQUIREMENTS.md` — load-bearing principles (refusal of false
  precision, local-first, no-egress).
- `DECISION_LOG.md` — accepted decisions; D006, D007, D017, D044, D052,
  D053, D055, D068, D074 are most relevant.
- Three RFCs as upstream context: 0007 (artifact IDs), 0011 (Phase 3
  schema), 0018 (audit cascade).

## What Phase 4 introduces

Per `BUILD_PHASES.md` PHASE-0004:

- entity canonicalization + `entities` and `entity_edges` tables;
- `current_beliefs` materialized view (over beliefs with `valid_to IS NULL`);
- belief review queue exposing `accept` / `reject` / `correct` / `promote-to-pinned`
  per D006; `correct` writes a new `captures` row per D017;
- 1–2 hop neighborhood queries via recursive CTE (no graph backend per D007);
- entity disambiguation tiebreak via local LLM if needed (per O003).

## Review checklist

1. **Schema coherence with Phase 3.** Are the proposed tables compatible
   with existing claims/beliefs/predicate_vocabulary shapes? Do any
   constraints conflict?
2. **Materialized view refresh policy.** When does `current_beliefs`
   refresh? Does it stay in sync with belief transitions through the
   D052 transition API? Is there a stale-window during refresh?
3. **HITL surface invariants.** Does the queue UX preserve the no-mutation-
   in-place rule (D017)? Are `accept` / `promote-to-pinned` distinct from
   schema-level `status` transitions? What happens when two reviewers act
   on the same belief?
4. **Entity-edge query plan.** Will the 1–2 hop recursive CTE scale to
   the V1-corpus belief count? Index strategy?
5. **Disambiguation tiebreak.** What's the contract for the local-LLM
   tiebreak in O003? Is it advisory or load-bearing? How are tiebreaker
   decisions audited?
6. **Provenance carry.** Do `entities` and `entity_edges` rows carry
   `extraction_*` versioning per D021? Do entity merges preserve audit
   trails analogous to `belief_audit`?
7. **Audit cascade integration.** RFC 0018's `claim_audits` and
   `projection_audits` are advisory in V1 (D069). Does Phase 4's review
   queue surface those audit signals to the reviewer?
8. **Local-first contract.** Does anything proposed for Phase 4 require
   network egress or cloud APIs? (It should not.)
9. **What's missing.** What should the Phase 4 spec cover that no current
   document mentions?

## Output

Write your review to the path in your job packet:
`docs/reviews/phase4/PHASE_4_SPEC_REVIEW_<lane>.md`.

Structure the review as:

```md
# Phase 4 Build-Spec Review — <lane>

Status: review
Date: <YYYY-MM-DD>
RFC refs: ...
Decision refs: ...
Phase refs: PHASE-0004

## Findings

### F001 — <one-line title>
Severity: <blocking | major | minor | nit>
Source: <path>:<line range or section anchor>
Rationale: <one paragraph>

[... more findings ...]

## Open questions

- <questions to resolve before a spec can be authored>

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Do not modify any file outside the path your packet specifies. Do not
edit `BUILD_PHASES.md`, any RFC, or `DECISION_LOG.md`.
