# Phase 3 Claims And Beliefs Spec Review - Codex GPT-5.5

Summary verdict: `reject_for_revision`

The spec is close to buildable in schema shape, but several rules would corrupt
the first belief layer if handed directly to implementation. The blockers are
mostly around consolidation semantics: predicate cardinality, temporal validity
vs row lifecycle, extraction-version selection, and audit enforcement.

## Findings

### P0 - Consolidation treats multi-valued predicates as contradictions

- Affected file / section: `docs/claims_beliefs.md` Predicate vocabulary,
  Grouping key, Decision rules (`docs/claims_beliefs.md:199`,
  `docs/claims_beliefs.md:329`, `docs/claims_beliefs.md:354`)
- Issue: The consolidator groups only by `(normalize(subject_text), predicate)`
  and treats a different object value under that key as a contradiction. Many
  predicates in the fixed vocabulary are naturally multi-valued or event-like:
  `has_pet`, `is_related_to`, `is_friends_with`, `works_with`, `uses_tool`,
  `owns_repo`, `studied`, `traveled_to`, `met_with`, and often `prefers`.
- Consequence: Normal facts such as "the user works with Alice" and "the user
  works with Bob" become contradictory beliefs. A full Phase 3 run would flood
  `contradictions`, close valid beliefs, and push ordinary multi-entity memory
  into the Phase 4 review queue as false conflicts.
- Proposed fix: Add predicate cardinality / conflict semantics before the build
  prompt. At minimum, classify each predicate as `single_current`,
  `multi_current`, or `event`. For `multi_current` and `event` predicates, the
  group key must include a normalized object discriminator or selected object
  fields, and contradiction detection should only run within the same object
  identity. Keep subject+predicate-only contradiction for genuinely
  single-valued current facts such as `lives_at` or `eats_diet`.

### P1 - `valid_to` conflates truth validity with derivation lifecycle

- Affected file / section: `docs/claims_beliefs.md` Time semantics, Decision
  rules, Re-derivation behavior, `beliefs` schema (`docs/claims_beliefs.md:273`,
  `docs/claims_beliefs.md:367`, `docs/claims_beliefs.md:411`,
  `docs/claims_beliefs.md:514`)
- Issue: The spec uses `valid_to` both as the asserted end of a belief's truth
  interval and as a lifecycle close marker for same-value supersession,
  reclassification rejection, and `--rebuild`. A same-value claim closes the
  prior belief with `valid_to = now()`, even though the fact did not stop being
  true.
- Consequence: The bitemporal layer will lie about history. A belief can appear
  to have ended because a new extractor version, privacy reclassification, or
  provenance merge touched it. That breaks the time-indexed biography contract
  and makes `current_beliefs` semantics fragile.
- Proposed fix: Separate truth validity from row lifecycle. Use `valid_from` /
  `valid_to` only for the interval the fact is asserted true. For same-value
  supersession, rebuild, or invalidation, keep the validity interval unchanged
  and use `status`, `superseded_by`, audit rows, and preferably a lifecycle
  timestamp such as `superseded_at` / `closed_at`. Only set `valid_to` when the
  evidence asserts the fact ended or changed.

### P1 - Active claims are undefined across extraction-version changes

- Affected file / section: `docs/claims_beliefs.md` Re-derivation behavior,
  `claim_extractions`, `claims`, Resumability (`docs/claims_beliefs.md:411`,
  `docs/claims_beliefs.md:449`, `docs/claims_beliefs.md:477`,
  `docs/claims_beliefs.md:650`)
- Issue: Claims are insert-only and multiple `claim_extractions` rows can exist
  for the same segment under different extractor prompt/model versions. The
  spec defines active claims mainly by joining through active segments, but that
  does not exclude stale extraction versions. It also says the consolidator
  picks up new claims alongside existing ones after a prompt bump.
- Consequence: Re-extraction can mix old and new prompt outputs in one belief
  set, inflate confidence, create duplicate provenance, and make `--rebuild`
  dependent on historical extractor versions rather than the selected current
  version. This undercuts D045's bounded-blast-radius intent.
- Proposed fix: Define the active claim set explicitly. Options: mark prior
  `claim_extractions` rows `superseded` when a new extractor version becomes
  current, or require `engram consolidate` / `--rebuild` to take an exact
  `(extraction_prompt_version, extraction_model_version, request_profile_version)`
  and filter to that version. Tests should prove old extraction versions do not
  influence new beliefs unless the operator deliberately includes them.

### P1 - The audit-on-update invariant is not implementable as written

- Affected file / section: `docs/claims_beliefs.md` `beliefs` mutation trigger,
  tests (`docs/claims_beliefs.md:546`, `docs/claims_beliefs.md:707`)
- Issue: "Every UPDATE must have a corresponding `belief_audit` row in the same
  transaction" is stated as a trigger invariant, but no correlation mechanism
  is specified. A normal row trigger cannot reliably know whether a matching
  audit row will be inserted later in the transaction, and a loose existence
  check can be satisfied by an unrelated audit row.
- Consequence: The implementer will either weaken the invariant, write brittle
  triggers that reject valid transitions depending on statement order, or leave
  a false sense of audit coverage.
- Proposed fix: Make all belief state changes go through database functions or
  a Python transition API that updates the belief and inserts audit in one
  operation, while revoking direct UPDATE from normal code. If direct UPDATE is
  still allowed, add a concrete deferred-constraint design with a transition id
  / audit id that proves the audit row matches the changed belief, columns,
  previous state, and new state.

### P1 - Validity timestamps ignore explicit temporal assertions

- Affected file / section: `docs/claims_beliefs.md` Time semantics, Predicate
  vocabulary, Decision rules (`docs/claims_beliefs.md:273`,
  `docs/claims_beliefs.md:199`, `docs/claims_beliefs.md:354`)
- Issue: `valid_from` and `observed_at` are derived from `messages.created_at`,
  but the vocabulary includes structured temporal fields such as `since`,
  `until`, `when`, and `by_when`. The claims schema has no claim-level
  `asserted_valid_from`, `asserted_valid_to`, or `observed_at`; the decision
  rule also refers to `observed_at_for_claim`, which is not a claim column.
- Consequence: "I lived in Boston from 2014 to 2018" said in a 2026 message
  becomes valid from 2026 unless the object payload is handled out of band.
  Temporal auto-resolution would then order contradictions by conversation time
  rather than the life interval being asserted.
- Proposed fix: Add explicit temporal fields to claims, even if nullable:
  `asserted_valid_from`, `asserted_valid_to`, `temporal_basis`, and optionally
  `temporal_confidence`. Derive belief validity from explicit temporal claims
  first, and use message time only as an `observed_at` / fallback proxy. If V1
  cannot extract temporal qualifiers yet, disable contradiction auto-resolution
  except where explicit non-overlapping validity intervals exist.

### P2 - Predicate vocabulary is not database-enforced enough for D046

- Affected file / section: `docs/claims_beliefs.md` Predicate vocabulary,
  `claims` schema (`docs/claims_beliefs.md:232`, `docs/claims_beliefs.md:477`);
  `DECISION_LOG.md` D046
- Issue: D046 says the DB enforces the fixed predicate vocabulary, but the spec
  mostly relies on the extractor schema and describes the predicate-to-stability
  mapping as prompt-side. The table lists `predicate TEXT NOT NULL` with "one
  of the V1 enum", but it does not choose a DB enum, CHECK, or vocabulary table.
- Consequence: Test fixtures, manual repairs, or future code paths can insert
  predicates or predicate/stability pairs the extractor would never emit,
  creating vocabulary drift below the LLM boundary.
- Proposed fix: Use a DB enum or a `claim_predicate_vocabulary` table with
  allowed stability class, object kind, cardinality/conflict scope, and JSON
  schema metadata. Add an INSERT trigger or FK-style validation so direct SQL
  cannot bypass D046.

### P2 - Object JSON schemas are underspecified for implementation

- Affected file / section: `docs/claims_beliefs.md` Structured-output schema,
  Predicate vocabulary, Object representation (`docs/claims_beliefs.md:153`,
  `docs/claims_beliefs.md:199`, `docs/claims_beliefs.md:237`)
- Issue: The spec says `object_json` keys are enumerated by predicate, but the
  table only gives prose examples. It does not define required keys, value
  types, allowed enum values for every structured predicate, or
  `additionalProperties` behavior.
- Consequence: Different implementers can produce incompatible extractor
  schemas while all believing they followed the spec. The local LLM may also
  emit malformed but superficially valid JSON that the consolidator cannot
  compare deterministically.
- Proposed fix: Add a small machine-like schema table per structured predicate:
  required keys, optional keys, primitive types, enum values, and whether extra
  keys are rejected. Include at least one migration/unit test that rejects an
  object_json shape outside the predicate contract.

## Open Questions For The Owner

1. Should Phase 3 support multi-valued and event predicates directly, or should
   the V1 predicate list be cut down to single-current facts until Phase 4?
2. Is `valid_to` intended to mean "the fact stopped being true" only, or also
   "this row left the active derivation set"? If it is both, the bitemporal
   contract should be renamed or split.
3. Should the current extraction version be an operator-pinned global setting
   for consolidation, or should older extraction versions remain eligible by
   default?
4. Are explicit temporal qualifiers in claims in scope for Phase 3 V1? If not,
   should temporal auto-resolution be disabled until they are?
5. Should predicate vocabulary live as a Postgres enum, a CHECK constraint, or
   a small vocabulary table that also stores cardinality and object schema?

## Test Or Acceptance-Criteria Gaps

- Add a consolidator test where one subject has two valid values for a
  multi-valued predicate, such as two `uses_tool` claims, and no contradiction
  is inserted.
- Add a same-value supersession test proving the old row is superseded without
  implying the fact's truth interval ended.
- Add a re-extraction-version test proving a new extractor prompt/model does
  not mix stale claims into the active claim set.
- Add an audit enforcement test through the intended transition API, plus a
  direct SQL UPDATE rejection test. The current "same transaction" criterion
  needs a concrete mechanism before it can be tested honestly.
- Add a temporal extraction/consolidation test where evidence is observed in
  2026 but explicitly asserts a 2014-2018 validity interval.
- Add DB-level tests for invalid predicates, invalid predicate/stability pairs,
  and invalid `object_json` keys/types.
- Add a test that `claim_extractions.claim_count` equals the number of inserted
  claims for the extraction id.

## RFC 0011 Contradictions Or Supersession Notes

- The spec intentionally promotes RFC 0011's proposed D043-D047 decisions; that
  is consistent with the current DECISION_LOG.
- The spec should intentionally supersede RFC 0011's subject+predicate-only
  grouping rule if the cardinality finding is accepted. The RFC carries the
  same flaw; leaving it inherited would make the build prompt wrong.
- RFC 0011 OQ7 is settled by the spec as `observed_at = MAX(messages.created_at)`,
  but the explicit-temporal-assertion gap should reopen that decision or narrow
  it to "fallback when no explicit validity interval exists."
- RFC 0011 OQ5's temporal auto-resolution should be narrowed: it is safe only
  for intervals derived from explicit temporal evidence, not for intervals
  inferred from conversation timestamps alone.
- The spec's additions of `claims.extraction_id` and
  `beliefs.subject_normalized` are useful implementation deltas beyond the RFC
  and should remain if the schema is revised.
