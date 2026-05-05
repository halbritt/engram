# Phase 3 Claims and Beliefs Spec Findings Ledger

Date: 2026-05-05
Recorder: codex_gpt5_5
Prompt: P023 - Record Phase 3 Spec Findings
Target artifact: `docs/claims_beliefs.md`

This ledger normalizes independent P022 reviews into stable finding IDs. It
does not accept, reject, or patch the spec. P024 owns synthesis and any source
artifact changes.

## Review Set

The configured review markers were present:

- `docs/reviews/phase3/markers/02_SPEC_REVIEW_gemini_pro_3_1.ready.md`
- `docs/reviews/phase3/markers/02_SPEC_REVIEW_codex_gpt5_5.ready.md`
- `docs/reviews/phase3/markers/02_SPEC_REVIEW_claude_opus_4_7.ready.md`

Also present: `02_SPEC_REVIEW_codex_gpt_5_5.ready.md`. The canonical
`codex_gpt5_5` marker records this as an alias for the same Codex review file.
No alternate reviewer set was needed.

Inputs read:

- `docs/claims_beliefs.md`
- `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_REVIEW_gemini_pro_3_1_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_REVIEW_codex_gpt_5_5_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_REVIEW_claude_opus_4_7_2026_05_05.md`
- `docs/process/multi-agent-review-loop.md`
- `docs/process/phase-3-agent-runbook.md`

## Severity Key

Severity is preserved from the highest severity assigned by any reviewer unless
there was a clear inflation. No severity was downgraded in this ledger.

- P0: must resolve before build prompt or implementation.
- P1: should resolve in synthesis before implementation unless explicitly
  deferred.
- P2: important spec, test, or operator-risk cleanup.
- P3: documentation or low-risk cleanup.

## Ledger Summary

| ID | Severity | Finding | Reviewers | Resolution class |
| --- | --- | --- | --- | --- |
| S-F001 | P0 | `valid_to` mixes fact validity with row lifecycle | Gemini, Codex, Claude | Architecture decision |
| S-F002 | P0 | Active claim set is undefined across re-extraction and vanished claims | Gemini, Codex, Claude | Architecture decision |
| S-F003 | P0 | Multi-valued/event predicates become false contradictions | Codex | Architecture decision |
| S-F004 | P1 | Explicit temporal assertions are not lifted into belief validity | Gemini, Codex, Claude | Owner checkpoint |
| S-F005 | P1 | Audit-on-update invariant lacks an implementable mechanism | Codex | Architecture / implementation decision |
| S-F006 | P1 | Concurrent consolidators can create duplicate active beliefs | Gemini, Claude | Architecture / implementation decision |
| S-F007 | P1 | Subject normalization storage and query contract are underspecified | Claude | Mechanical with implementation choice |
| S-F008 | P1 | Partial reclassification recompute is underspecified | Claude | Architecture / flow decision |
| S-F009 | P1 | `consolidate --rebuild` cannot be both close-and-reinsert and no-op | Claude | Owner checkpoint |
| S-F010 | P2 | `confidence = MAX(...)` may violate false-precision contract | Claude | Owner checkpoint |
| S-F011 | P2 | Predicate vocabulary contract is under-specified below the LLM boundary | Codex, Claude | Architecture / schema decision |
| S-F012 | P2 | Successful empty extractions do not preserve model output | Gemini | Accepted-by-default mechanical fix |
| S-F013 | P2 | Extractor schema enum size needs tail-risk preflight | Claude | Test / operational guard |
| S-F014 | P2 | One invalid claim can sink a whole extraction transaction | Claude | Implementation decision |
| S-F015 | P2 | Contradiction schema and lineage semantics need cleanup | Claude | Mechanical plus documentation |
| S-F016 | P3 | Audit naming and extraction-transition rationale are operator-confusing | Claude | Accepted-by-default mechanical fix |
| S-F017 | P3 | Tool-message placeholders create a known extraction recall blind spot | Gemini | Documentation / deferred architecture |
| S-F018 | P3 | Stability-class aggregation is dead code under fixed predicate mapping | Claude | Accepted-by-default mechanical fix |

## Findings

### S-F001 - `valid_to` mixes fact validity with row lifecycle

Severity: P0

Merged from:

- Gemini P0 finding 1 and P1 finding 3.
- Codex P1 finding "`valid_to` conflates truth validity with derivation
  lifecycle."
- Claude P0-1.

Issue:

The spec defines `valid_from` / `valid_to` as the interval a belief asserts as
true, but the decision rules also set `valid_to = now()` for same-value
supersession, contradiction close, privacy rejection, and rebuild close. This
turns row lifecycle events into asserted biographic truth. The contradiction
rule then opens the replacement at a past evidence timestamp, causing intervals
to overlap and making temporal auto-resolution unreachable on historical
corpus evidence.

Consequences recorded by reviewers:

- Historical queries can report that a superseded fact remained valid until the
  consolidation run date.
- Same-value provenance refreshes fragment a still-current fact into artificial
  validity intervals.
- Acceptance test #22 cannot pass under the written interval math.

Preserved dissent / unresolved choice:

- Reviewers agree that `valid_to = now()` is wrong for default consolidator
  close operations.
- Gemini and Codex lean toward keeping same-value fact intervals unchanged and
  tracking lifecycle with `status`, `superseded_by`, audit, and possibly
  `superseded_at` / `closed_at`.
- Claude proposes setting the prior `valid_to` to the new evidence timestamp
  for contradiction, and also suggests applying a timestamp-based close to
  same-value supersession. That same-value part differs from Gemini/Codex.
- Synthesis must decide whether `valid_to` is strictly fact-validity only, and
  what lifecycle timestamp, if any, is added.

Implied tests:

- Contradiction close uses the chosen fact-validity rule, not `now()`.
- Same-value supersession does not imply the fact stopped being true.
- Auto-resolution is reachable when intervals are genuinely non-overlapping.

### S-F002 - Active claim set is undefined across re-extraction and vanished claims

Severity: P0

Merged from:

- Gemini P0 finding 2.
- Codex P1 finding "Active claims are undefined across extraction-version
  changes."
- Claude P0-2.

Issue:

Claims are insert-only, and multiple `claim_extractions` versions can exist for
the same segment. The spec says the consolidator joins through active segment
generations and "picks up new claims alongside existing ones", but does not
define which extraction version is active. It also lacks a rule for active
beliefs whose supporting claims disappear because a newer extraction emits
fewer or zero claims.

Consequences recorded by reviewers:

- Prompt/model re-extraction can mix stale and fresh claims in one belief set.
- Different outputs from old and new extractor versions can become spurious
  contradictions.
- Beliefs supported only by no-longer-active claims can remain active
  indefinitely.
- D045's bounded-blast-radius property is not satisfied as written.

Preserved dissent / unresolved choice:

- Claude proposes "latest extracted claim_extraction per segment" based on
  version/created order.
- Codex suggests an explicit operator-pinned
  `(extraction_prompt_version, extraction_model_version,
  request_profile_version)` filter, or marking prior extraction rows
  `superseded`.
- Gemini frames the missing rule as an orphan-belief lifecycle pass before
  processing active claims.

Implied tests:

- A segment with v1 and v2 extracted claims contributes only the selected
  current claim vintage by default.
- A new empty extraction causes prior claims from that segment to stop feeding
  active beliefs.
- Orphaned beliefs are superseded, rejected, or otherwise closed by an
  explicit audited transition.

### S-F003 - Multi-valued/event predicates become false contradictions

Severity: P0

Merged from:

- Codex P0 finding "Consolidation treats multi-valued predicates as
  contradictions."

Issue:

The grouping key is only `(normalize(subject_text), predicate)`, and any
different object value under that key is a contradiction. Many listed
predicates are naturally multi-valued or event-like: examples include
`has_pet`, `is_related_to`, `is_friends_with`, `works_with`, `uses_tool`,
`owns_repo`, `studied`, `traveled_to`, `met_with`, and often `prefers`.

Consequence:

Ordinary facts such as "works with Alice" and "works with Bob" would close each
other and flood `contradictions` with false conflicts.

Unresolved choice:

The spec needs predicate-level conflict semantics before implementation. The
review proposes at least `single_current`, `multi_current`, and `event`
classes, with object discriminators included in the group key where needed.
The owner may instead cut the V1 predicate list down to single-current facts,
but that would materially change Phase 3 scope.

Implied tests:

- Two `uses_tool` or `works_with` claims for different objects do not create a
  contradiction.
- A genuinely single-current predicate still detects incompatible values.

### S-F004 - Explicit temporal assertions are not lifted into belief validity

Severity: P1

Merged from:

- Codex P1 finding "Validity timestamps ignore explicit temporal assertions."
- Claude P1-7.
- Gemini open question on `valid_from` derivation.

Issue:

The spec derives `valid_from`, `valid_to`, and `observed_at` from message
timestamps, while several predicates carry real-world temporal qualifiers in
`object_json` or `object_text`: `since`, `until`, `when`, `by_when`, and
date-bearing predicates such as `born_on`. A 2026 message saying "I lived in
Boston from 2014 to 2018" would be represented as discovered in 2026 unless
the object payload is interpreted elsewhere.

Consequences recorded by reviewers:

- V1 bitemporal columns may represent discovery time, not biographic time.
- Historical "what was true on date X" queries can be wrong or empty.
- Temporal auto-resolution based on conversation timestamps can order facts by
  when they were discussed rather than when they were true.

Preserved dissent / unresolved choice:

- Codex proposes claim-level temporal fields such as `asserted_valid_from`,
  `asserted_valid_to`, `temporal_basis`, and disabling auto-resolution when
  explicit intervals are absent.
- Claude proposes at minimum documenting V1 as discovery-time-only and
  deferring biographic-time lift to later columns or a view.
- Gemini asks the owner to confirm whether the `observed_at` / `valid_from`
  distinction is sufficient for historical queries.

### S-F005 - Audit-on-update invariant lacks an implementable mechanism

Severity: P1

Merged from:

- Codex P1 finding "The audit-on-update invariant is not implementable as
  written."

Issue:

The spec says every allowed `beliefs` UPDATE must have a corresponding
`belief_audit` row in the same transaction. It does not define how a trigger
can prove the audit row matches the changed belief, columns, previous state,
and new state, especially when the audit row may be inserted after the UPDATE
statement.

Consequence:

The build prompt would force the implementer to either weaken audit coverage,
write brittle statement-order-dependent triggers, or rely on an invariant that
is not actually enforced.

Unresolved choice:

Options raised by review:

- Route all belief state transitions through database functions or a Python
  transition API that writes belief and audit rows together.
- Add a concrete deferred-constraint design with a transition ID / audit ID.
- Revoke direct UPDATE from normal code and test direct SQL rejection.

### S-F006 - Concurrent consolidators can create duplicate active beliefs

Severity: P1

Merged from:

- Claude P1-4.
- Gemini's RFC 0011 contradiction note about per-conversation consolidator
  races.

Issue:

The spec allows per-conversation consolidation while the belief group key is
global. The partial active-belief index on `(subject_normalized, predicate)` is
not unique. Two consolidator passes can both observe no existing active belief
for the same global key and both insert candidate beliefs.

Consequence:

The active belief set is not deterministic and `current_beliefs` can later
return multiple active rows for the same single-current fact.

Unresolved choice:

The spec needs one of:

- Unique active-belief index / constraint plus retry on conflict.
- Advisory lock or serialized transaction per group key.
- Explicitly serial consolidation.

This finding interacts with S-F003: any uniqueness or lock scope must honor
multi-valued/event predicate semantics.

### S-F007 - Subject normalization storage and query contract are underspecified

Severity: P1

Merged from:

- Claude P1-3 and P3-18.

Issue:

`beliefs.subject_normalized` is required and described as computed at insert,
but the spec does not choose SQL generated column, trigger, SQL function, or
application-side computation. `claims` has no `subject_normalized`, so operator
queries must reimplement normalization to compare claims to beliefs.

Consequence:

Different code paths can normalize differently, causing duplicate group keys
or misleading audit queries.

Resolution class:

Mechanical with an implementation choice. P024 should pin the canonical
normalization storage strategy and decide whether mirroring
`subject_normalized` onto `claims` is in scope.

Implied tests:

- SQL-inserted subject text normalizes identically to the Python consolidator
  helper.

### S-F008 - Partial reclassification recompute is underspecified

Severity: P1

Merged from:

- Claude P1-5.

Issue:

The privacy reclassification section specifies full invalidation and a
same-value surviving-set recompute, but not the cases where the surviving
claims yield a different value or no surviving claim set remains under the
active segment generation.

Consequence:

The build prompt must invent status/audit/contradiction behavior for partial
privacy invalidation, and may treat privacy events as temporal contradictions.

Reviewer's proposed decision tree:

1. Compute surviving claims attached to currently active segment generations.
2. If empty, reject with `transition_kind='reject'`.
3. If non-empty and same value, close-and-insert with `transition_kind=
   'supersede'`.
4. If non-empty and different value, close-and-insert with a contradiction at
   `detection_kind='reclassification_recompute'`, left open for review.

This remains a synthesis decision, not a ledger decision.

### S-F009 - `consolidate --rebuild` cannot be both close-and-reinsert and no-op

Severity: P1

Merged from:

- Claude P1-6.

Issue:

The spec says `engram consolidate --rebuild` closes active beliefs and reruns
the decision rules, then acceptance test #23 says running it twice against an
unchanged claim corpus is a no-op. Under close-and-reinsert, the second run
creates new IDs, new `recorded_at` values, and extra audit rows.

Consequence:

The acceptance criterion cannot pass as worded, and repeated rebuilds bloat
the audit chain unless a no-op short-circuit exists.

Unresolved choice:

- Redefine "no-op" as structurally equivalent active belief set.
- Add a pre-diff short-circuit and skip close/reinsert when output is
  equivalent.
- Narrow rebuild to changed claim sets only, which requires extra state.

### S-F010 - `confidence = MAX(...)` may violate false-precision contract

Severity: P2

Merged from:

- Claude P2-8.

Issue:

The consolidator stores the maximum contributing claim confidence. A single
high-confidence claim can hide a broad spread of lower confidence claims, and
Phase 5 inline confidence tags would present the maximum as the belief's
confidence.

Consequence:

The serving layer can overstate certainty, conflicting with the
HUMAN_REQUIREMENTS false-precision contract.

Unresolved choice:

Owner/synthesis should choose MAX, mean, weighted mean, or another aggregator,
and record why. If MAX remains, the spec should explicitly acknowledge the
false-precision tradeoff and preserve supporting spread in audit fields.

### S-F011 - Predicate vocabulary contract is under-specified below the LLM boundary

Severity: P2

Merged from:

- Codex P2 findings on DB enforcement and object JSON schemas.
- Claude P2-9, P2-10, and P3-15.

Issue:

D046 says the predicate vocabulary is fixed and schema-constrained, but the
spec leaves several parts prompt-side or prose-only:

- `claims.predicate` is `TEXT`; DB enum/CHECK/vocabulary-table enforcement is
  not pinned.
- Predicate-to-stability-class mapping is prompt-side, not DB-enforced.
- Structured `object_json` shapes do not define required keys, optional keys,
  value types, enum values, or `additionalProperties`.
- Predicate emission semantics overlap (`met_with` vs `relationship_with`,
  `feels` vs `experiencing`, `wants_to` vs `plans_to` vs `intends_to`).
- `lives_at` allows both text and JSON, guaranteeing cross-shape duplicate
  chains under the stated no-cross-column-merge rule.
- `stability_class = MODE(...)` is dead code if every predicate has exactly one
  pinned stability class.

Consequence:

Different implementers can follow the spec and still build incompatible JSON
schemas or consolidation behavior. Future SQL/manual paths can bypass the LLM
schema and insert invalid predicate/class/object combinations.

Unresolved choice:

The reviews imply a stronger machine-readable vocabulary contract, likely a DB
enum or lookup table carrying allowed stability class, object kind, cardinality
/ conflict scope, JSON schema metadata, and emission guidance. Synthesis must
choose the level of enforcement.

### S-F012 - Successful empty extractions do not preserve model output

Severity: P2

Merged from:

- Gemini P2 finding 4.

Issue:

Empty extraction is recorded as `status='extracted'` with `claim_count=0`, and
the tests say no failure diagnostics are written. The spec does not require
storing the raw successful LLM output.

Consequence:

If the model returns an empty claim list because of prompt misalignment,
refusal, or other behavior that is syntactically valid, recall debugging loses
the evidence.

Accepted-by-default mechanical fix:

Store raw response content and relevant parse metadata in
`claim_extractions.raw_payload` for all successful and empty extractions, not
only failures. This does not decide architecture.

### S-F013 - Extractor schema enum size needs tail-risk preflight

Severity: P2

Merged from:

- Claude P2-11.

Issue:

The extractor JSON schema constrains `evidence_message_ids.items.enum` to the
segment's actual message UUID set. Phase 2 p99 was 62 messages, with a larger
tail. The spec has a context-token guard but no explicit preflight for grammar
schema size under the largest message-ID enum cases.

Consequence:

The longest segments may fail consistently under grammar-constrained
generation, creating avoidable extraction holes.

Proposed guard:

Add a preflight over the largest 1 percent of active segments by
`message_ids` cardinality. If it fails, synthesis should define a fallback
such as relaxing the enum above a cap and relying on Python/trigger
validation.

### S-F014 - One invalid claim can sink a whole extraction transaction

Severity: P2

Merged from:

- Claude P2-13.

Issue:

The lifecycle inserts all claims and updates extraction status in one
transaction. If one claim violates the evidence trigger, all otherwise valid
claims for that segment are discarded and the extraction is marked failed.

Consequence:

Failure rate and lost recall can be higher than necessary, especially when a
single bad evidence UUID appears in an otherwise useful response.

Unresolved choice:

- Pre-validate the full model response in Python and drop/reject bad claims
  before SQL insert.
- Use per-claim subtransactions and record dropped-claim diagnostics.
- Keep all-or-nothing intentionally and document the recall tradeoff.

### S-F015 - Contradiction schema and lineage semantics need cleanup

Severity: P2

Merged from:

- Claude P2-12 and P3-17.

Issue:

The `contradictions.detection_kind` examples include
`temporal_overlap_disagreement`, but no decision rule emits it. Separately,
same-value supersession uses `superseded_by`, while contradiction replacement
does not; lineage traversal therefore requires both `superseded_by` and
`contradictions`.

Consequence:

Operators and Phase 4/5 readers can misread the contradiction vocabulary or
miss part of a belief's replacement history.

Resolution class:

Mostly mechanical/documentation. Either define or remove the unused
`detection_kind` example, and document the two lineage traversal paths. A
small test should cover both traversal paths.

### S-F016 - Audit naming and extraction-transition rationale are operator-confusing

Severity: P3

Merged from:

- Claude P3-14 and P3-16.

Issue:

`belief_audit.evidence_episode_ids` stores raw `messages.id` values, but
Engram has no `episodes` table. `claim_extractions` can transition to
`superseded`, but the spec does not specify where the reason or linked
reclassification capture is recorded.

Accepted-by-default mechanical fix:

- Rename `evidence_episode_ids` to `evidence_message_ids` before any rows
  exist, unless D010 compatibility is intentionally preserved.
- Either document that extraction-transition rationale is recovered through
  captures/progress joins, or add inline fields such as `superseded_reason`
  and `superseded_by_capture_id`.

### S-F017 - Tool-message placeholders create a known extraction recall blind spot

Severity: P3

Merged from:

- Gemini P3 finding 5.

Issue:

The extractor inherits D038 and sees compact placeholders instead of tool or
artifact bodies. This protects raw artifact handling and prompt budgets, but it
means artifact-only facts can be invisible to extraction.

Consequence:

Predicates such as `uses_tool`, `working_on`, or `project_status_is` may lose
recall when the supporting evidence lives only in omitted tool output.

Resolution class:

Document the limitation explicitly and keep artifact extraction as a future
stage unless synthesis chooses to amend D038 for Phase 3.

### S-F018 - Stability-class aggregation is dead code under fixed predicate mapping

Severity: P3

Merged from:

- Claude P3-15.

Issue:

The spec says each predicate has one allowed stability class, then the
consolidator computes `stability_class = MODE(...)` across contributing
claims. Under a fixed predicate-to-class map, the mode and tie-breaker are
unreachable.

Accepted-by-default mechanical fix:

Replace the rule with "look up the predicate's pinned stability class" or note
that MODE is intentionally degenerate in V1.

## Accepted-by-Default Mechanical Fixes

These items appear safe to apply during P024 synthesis if no reviewer/owner
objection is raised. They do not decide final architecture.

- M-F001: Store raw successful LLM output and parse metadata in
  `claim_extractions.raw_payload` for all extractions, including empty
  extractions. Source: S-F012.
- M-F002: Rename `belief_audit.evidence_episode_ids` to
  `evidence_message_ids` before rows exist, or explicitly preserve the old name
  for D010 compatibility. Source: S-F016.
- M-F003: Replace `stability_class = MODE(...)` with the predicate's pinned
  stability-class lookup, or document the degenerate behavior. Source: S-F018.
- M-F004: Remove or define `temporal_overlap_disagreement` in
  `contradictions.detection_kind` examples. Source: S-F015.
- M-F005: Add an acceptance test that `claim_extractions.claim_count` equals
  inserted `claims` rows for the extraction. Source: Codex test gaps.
- M-F006: Document the D038 tool-placeholder recall limitation and future
  artifact-extraction path. Source: S-F017.

## Architecture Decisions Needed

These should not be silently patched as mechanical edits.

- A-F001: Define whether `beliefs.valid_to` is fact-validity only, and choose
  the separate row-lifecycle mechanism if needed. Source: S-F001.
- A-F002: Define the active claim set across extractor prompt/model versions
  and vanished claims. Source: S-F002.
- A-F003: Add predicate cardinality/conflict semantics or reduce the predicate
  vocabulary to single-current facts. Source: S-F003.
- A-F004: Decide whether Phase 3 lifts explicit temporal assertions into
  claim/belief validity columns or documents V1 as discovery-time-only. Source:
  S-F004.
- A-F005: Choose the enforceable belief transition/audit mechanism. Source:
  S-F005.
- A-F006: Choose concurrency control for global belief group keys. Source:
  S-F006.
- A-F007: Define privacy reclassification recompute behavior for empty,
  same-value, and different-value surviving claim sets. Source: S-F008.
- A-F008: Define rebuild semantics and update test #23 accordingly. Source:
  S-F009.
- A-F009: Choose the belief confidence aggregation rule. Source: S-F010.
- A-F010: Choose predicate vocabulary enforcement shape below the LLM boundary:
  DB enum, CHECKs, or vocabulary metadata table. Source: S-F011.
- A-F011: Choose all-or-nothing versus partial salvage for invalid claims in an
  otherwise valid extraction response. Source: S-F014.

## Owner Checkpoints

From the spec's own open checkpoints plus review findings, the owner should
explicitly weigh in on:

1. Predicate vocabulary lock-in, especially cardinality/conflict classes and
   overlapping predicate semantics (`talked_about`, `experiencing`,
   `lives_at`, goal predicates).
2. Whether `valid_from` / `valid_to` must carry biographic time in Phase 3 or
   whether discovery-time-only is acceptable as an acknowledged V1 limitation.
3. The active extraction-version policy: latest per segment, operator-pinned
   version tuple, or explicit superseding of older `claim_extractions`.
4. Confidence aggregation: MAX, mean, weighted mean, or another rule.
5. `engram consolidate --rebuild` semantics: structural equivalence versus
   true no-op short-circuit.
6. Whether to run any additional pre-Phase-3 adversarial review beyond the
   completed Gemini/Codex/Opus P022 fan-out.
7. Whether to targeted-rerun the 45 Phase 2 umbrella-overlap parents before
   Phase 3, or proceed with caveats as the current spec default says.
8. Whether belief-text embeddings remain deferred to Phase 5, as the current
   spec says.
9. Whether an invalid claim in a multi-claim extraction should discard the
   whole segment's extraction or salvage valid claims with diagnostics.

No reviewer requested changing the local-first / no-egress posture, using a
hosted service, or starting a full-corpus Phase 3 run. The runbook checkpoints
for those remain unchanged.

## Proposed DECISION_LOG Entries Implied

The exact IDs belong to P024. These are proposed decision-log topics, not
accepted decisions.

| Proposed ID | Decision topic | Source findings |
| --- | --- | --- |
| DL-PROP-01 | Belief validity columns represent fact validity only; lifecycle close/supersession uses explicit status/audit/timestamp semantics chosen in synthesis. | S-F001 |
| DL-PROP-02 | Active claim set policy across extractor versions and empty/dropped re-extractions. | S-F002 |
| DL-PROP-03 | Predicate cardinality and conflict semantics, including group-key object discriminators for multi-valued/event predicates. | S-F003 |
| DL-PROP-04 | Treatment of explicit temporal qualifiers in claims and beliefs: lifted into validity columns now, or discovery-time V1 limitation. | S-F004 |
| DL-PROP-05 | Belief transition API / database function / deferred-constraint model for audit-coupled updates. | S-F005 |
| DL-PROP-06 | Consolidator concurrency policy for global belief group keys. | S-F006 |
| DL-PROP-07 | Privacy reclassification recompute decision tree and audit semantics. | S-F008 |
| DL-PROP-08 | Rebuild semantics and idempotency contract. | S-F009 |
| DL-PROP-09 | Confidence aggregation rule for beliefs. | S-F010 |
| DL-PROP-10 | Predicate vocabulary enforcement substrate: enum/CHECK/table plus object schema metadata. | S-F011 |
| DL-PROP-11 | Extraction response salvage policy when individual claims fail validation. | S-F014 |

## Consolidated Test Gaps

The review set implies adding or amending tests before Phase 3 implementation
is considered ready:

- Bitemporal close math: no default `valid_to = now()` lifecycle close; same
  value refresh does not end fact validity; contradiction auto-resolution is
  reachable when intervals do not overlap.
- Re-extraction blast radius: old extractor vintages do not feed active
  beliefs unless deliberately selected; new empty extraction deactivates prior
  claim support.
- Multi-valued predicates: multiple valid objects do not create
  contradictions.
- Explicit temporal assertions: evidence observed in 2026 can assert a
  2014-2018 validity interval, or the spec explicitly tests the documented V1
  limitation.
- Audit enforcement: state transitions go through the chosen transition API or
  constraint mechanism; direct unsupported SQL UPDATE is rejected.
- Concurrency: two per-conversation consolidator passes for the same group key
  produce one correct active belief.
- Subject normalization: SQL and Python normalization match.
- Partial reclassification recompute: same, different, and empty surviving
  claim sets are covered.
- Rebuild: test matches the chosen idempotency or structural-equivalence
  contract.
- Predicate vocabulary: invalid predicates, invalid predicate/stability pairs,
  invalid object JSON keys/types, and ambiguous emission cases are rejected or
  normalized by the chosen contract.
- Extraction diagnostics: empty extraction stores raw output; claim_count
  equals inserted rows; invalid evidence IDs are caught by both schema/Python
  and trigger paths as applicable.
- Extractor grammar tail: largest message-ID enum segments pass a preflight or
  use a documented fallback.
- Contradiction lineage: same-value supersession and contradiction lineage are
  both traversable.
