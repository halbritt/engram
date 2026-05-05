# Phase 3 Claims and Beliefs Spec Synthesis Review - Codex GPT-5.5

Date: 2026-05-05
Reviewer: codex_gpt5_5
Prompt: P024B - Review Phase 3 Spec Synthesis After Codex Rejection

Summary verdict: `reject_for_revision`

This is a same-model re-review of the P022 Codex `reject_for_revision`
verdict. Scope is limited to whether P024 synthesis and the patched
canonical spec materially resolved the original rejection findings.

## Resolution Map

| Original Codex finding / ledger ID | Status | Notes |
| --- | --- | --- |
| S-F003 - multi-valued/event predicates become false contradictions | `partially_resolved` | The new cardinality classes and `group_object_key` resolve ordinary `works_with` / `uses_tool` style cases, but `relationship_with` remains internally inconsistent and can still create false contradictions across different people. See B-F001. |
| S-F001 - `valid_to` mixes fact validity with row lifecycle | `resolved` | `valid_to` is now fact-validity only; lifecycle uses `closed_at`, `status`, `superseded_by`, transition API, and audit. Same-value supersession preserves prior `valid_to`; contradiction close uses new evidence time. |
| S-F002 - active claim set undefined across re-extraction and vanished claims | `resolved` | Active claim set is now active segment generation plus latest extracted `claim_extractions` row per segment. Older extraction rows supersede, and Decision Rule 0 rejects orphan beliefs. Tests #27 and #28 pin the behavior. |
| S-F005 - audit-on-update invariant lacks implementable mechanism | `resolved` | The spec now routes belief state changes through `engram.consolidator.transitions`, gates `beliefs` UPDATEs on `engram.transition_in_progress`, records `request_uuid`, and tests direct SQL rejection plus API success. |
| S-F004 - validity timestamps ignore explicit temporal assertions | `partially_resolved` | P024 explicitly chose D051: V1 validity columns are discovery-time only. That does not implement the Codex preferred biographic-time fields, but it is now an acknowledged V1 limitation rather than an unresolved architecture gap. |
| S-F011 - predicate vocabulary DB enforcement below the LLM boundary | `resolved` | `predicate_vocabulary` now backs `claims.predicate` with FK validation and carries stability class, cardinality class, object kind, group-object keys, and required keys. |
| S-F011 - `object_json` schema/testability below the LLM boundary | `partially_resolved` | Required-key validation is DB-backed and tested; full typed JSON Schema, enum validation, and `additionalProperties` enforcement remain prompt-side by D057. This is acceptable as a V1 tradeoff, but P025 must not infer stronger DB enforcement than the spec states. |

## Remaining Blocking Findings

### B-F001 - `relationship_with` still reintroduces S-F003 false contradictions

Severity: P0

Affected sections:

- `docs/claims_beliefs.md:228` says group-object key lists are for
  `multi_current` / `event` predicates and empty for `single_current`.
- `docs/claims_beliefs.md:236` lists `relationship_with` as
  `single_current` "per `(subject, name)`".
- `docs/claims_beliefs.md:277` seeds `relationship_with` as
  `single_current` with group-object key `name`.
- `docs/claims_beliefs.md:485` defines every `single_current`
  `group_object_key` as `''`, so only one current value exists per
  `(subject, predicate)`.
- `docs/claims_beliefs.md:497` says `relationship_with` is keyed on
  `name`, which contradicts the computation rule.
- `docs/claims_beliefs.md:716` says `group_object_keys` is empty for
  `single_current`; `docs/claims_beliefs.md:829` repeats that
  `group_object_key` is empty for `single_current`.
- Test #29 covers same-person different-status contradiction, but does not
  cover different-person non-conflict.

Issue:

The synthesis intended `relationship_with` to mean one current relationship
status per named person. The executable grouping rule does not encode that.
Under the written rules, these two ordinary claims share the same group key
`(subject_normalized, 'relationship_with', '')`:

```text
relationship_with {"name": "Alice", "status": "close"}
relationship_with {"name": "Bob", "status": "professional"}
```

Because both are `single_current` and their JSON values differ, Rule 3 makes
them contradictions. This is the same false-conflict class that caused the
original Codex rejection, just narrowed to one high-value relationship
predicate.

Required fix before P025:

Choose one consistent object-scoped single-current model and apply it through
the vocabulary, grouping rule, value-equality rule, unique index semantics,
schema notes, and tests. For example, introduce a class such as
`single_current_per_object`, or revise `single_current` so non-empty
`group_object_keys` are honored. The fixed spec must make different names
produce distinct active chains, while different `status` values for the same
`name` still contradict. Add an acceptance test for
`relationship_with(Alice)` plus `relationship_with(Bob)` producing two
beliefs and zero contradictions.

## Non-Blocking Follow-Up Findings

### N-F001 - S-F011 object-json enforcement remains deliberately partial

The patched spec is clear that the database only enforces object kind,
required keys, predicate-stability pairing, and FK vocabulary membership.
Typed JSON value validation, enum validation inside structured payloads, and
`additionalProperties` behavior remain prompt-side in V1. This is not a
blocker after D057, but the P025 build prompt should make the extractor JSON
schemas explicit enough that implementers do not invent incompatible shapes.

### N-F002 - S-F004 is an accepted V1 limitation, not a Phase 3 build target

The biographic-time concern is not implemented; it is documented under D051.
P025 should preserve the discovery-time contract and avoid adding
biographic-validity requirements unless the owner changes the accepted
decision.

## P025 Handoff Statement

`docs/claims_beliefs.md` is **not safe** to hand to P025 yet. The remaining
`relationship_with` grouping inconsistency must be resolved before a build
prompt is allowed to proceed.
