# Phase 3 Claims and Beliefs Spec Synthesis Review - Codex GPT-5.5 Rerun

Date: 2026-05-05
Reviewer: codex_gpt5_5
Prompt: P024B - Review Phase 3 Spec Synthesis After Codex Rejection

Summary verdict: `accept_with_findings`

This is a same-model rerun of the P024B review after the prior
`reject_for_revision` result. Scope is limited to whether P024 synthesis and
the patched canonical spec materially resolve the original P022 Codex rejection
findings. This is not a second full architecture review.

## Resolution Map

| Original Codex finding / ledger ID | Status | Notes |
| --- | --- | --- |
| S-F001 - `valid_to` mixes fact validity with row lifecycle | `resolved` | `valid_to` is now fact-validity only. Same-value lifecycle transitions use `closed_at`, `status`, `superseded_by`, the transition API, and audit. Contradiction supersession closes fact validity at `MIN(new_evidence.created_at)`, not `now()`. |
| S-F002 - active claim set undefined across re-extraction and vanished claims | `resolved` | Active claims are now the active segment generation joined to the latest `status='extracted'` `claim_extractions` row per segment. Older rows are superseded, and Decision Rule 0 rejects beliefs whose `claim_ids` leave the active set. |
| S-F003 - multi-valued/event predicates become false contradictions | `resolved` | The spec now uses `single_current`, `single_current_per_object`, `multi_current`, and `event`. `group_object_key` extends the belief key for scoped-current, multi-current, and event predicates. The prior P024B blocker on `relationship_with` is resolved: it is now `single_current_per_object` keyed by `name`, and test #29 covers different-name non-conflict plus same-name status contradiction. |
| S-F005 - audit-on-update invariant lacks implementable mechanism | `resolved` | Belief state changes are routed through `engram.consolidator.transitions`; `beliefs` UPDATEs require `engram.transition_in_progress`, and `belief_audit.request_uuid` pairs the audit row with the transition. Tests require direct SQL rejection and API success. |
| S-F011 - predicate vocabulary DB enforcement below the LLM boundary | `resolved` | `predicate_vocabulary` is a DB lookup table. `claims.predicate` references it, and triggers enforce object kind, required JSON keys, and predicate/stability compatibility. |
| S-F011 - `object_json` schema/testability | `partially_resolved` | Required-key validation is DB-backed and tested; full typed JSON Schema, enum validation inside payloads, and `additionalProperties` remain prompt-side in V1 per D057. This is a documented tradeoff, not a blocker. |
| S-F004 - explicit temporal assertions are not lifted into belief validity | `partially_resolved` | P024 chose D051: V1 validity columns are discovery-time only. Biographic-time lift is not implemented, but the limitation is now explicit in the spec and decision log. |
| Codex test gap - `claim_extractions.claim_count` parity | `resolved` | Test #37 requires `claim_count` to equal inserted claim rows after per-claim salvage. |

## Remaining Blocking Findings

None.

## Non-Blocking Follow-Up Findings

### N-F001 - `object_json` enforcement remains intentionally partial

The amended spec is clear that the database enforces FK vocabulary membership,
object kind, required keys, and predicate/stability compatibility. It does not
DB-enforce JSON value types, inner enum values such as `relationship_with.status`,
or `additionalProperties`. P025 should preserve that boundary and make the
extractor JSON schemas explicit enough that implementation does not drift.

### N-F002 - Phase 4 `current_beliefs` wording should be status-aware

`BUILD_PHASES.md` still describes the future `current_beliefs` materialized view
as over `beliefs` with `valid_to IS NULL`. After D048, same-value superseded
rows can legitimately retain `valid_to IS NULL`, so Phase 4 should filter by
active statuses as well. This does not block P025 because the Phase 3 spec and
unique active-belief index already use `valid_to IS NULL AND status IN
('candidate','provisional','accepted')`.

### N-F003 - Test #27 wording is slightly ambiguous

Test #27 says "A segment with v1 and v2 `claim_extractions` rows at
`status='extracted'` (after the automated v1->`superseded` transition)". The
intended behavior is clear from the surrounding active-claim-set rules: v1 is
superseded and v2 is extracted. A later cleanup should tighten that sentence so
the test text does not imply two simultaneously extracted active rows.

## P025 Handoff Statement

`docs/claims_beliefs.md` is safe to hand to P025.

The original Codex rejection findings are materially resolved or explicitly
accepted as documented V1 limitations. There are no remaining P0/P1 blockers
that should stop the build prompt from being drafted against the amended spec.
