# Phase 3 Build Review — claude_opus_4_7

Date: 2026-05-05
Reviewer model: Claude Opus 4.7 (`claude_opus_4_7`)
Subject: Phase 3 (claims/beliefs) implementation completed by Codex GPT-5.5
under prompt P028, marker `08_BUILD_COMPLETE.ready.md`.

Coordinator constraint honored:
- No fixes were written.
- No corpus pipeline started.
- No hosted-service or non-local LLM call was issued.

`git status --short` was inspected before writing this file. Only Phase 3
review files and this report's marker are added; no unrelated changes touched.

## Scope of review

I reviewed:

- `migrations/006_claims_beliefs.sql`
- `src/engram/extractor.py`
- `src/engram/consolidator/__init__.py`
- `src/engram/consolidator/transitions.py`
- `src/engram/cli.py` (Phase 3 paths)
- `src/engram/segmenter.py` (only the
  `apply_reclassification_invalidations` Phase 2 entry to confirm the
  Phase 3 hook can find the capture id)
- `tests/test_phase3_claims_beliefs.py`, `tests/conftest.py`
- `docs/claims_beliefs.md`, `prompts/P028_build_phase_3_claims_beliefs.md`,
  `DECISION_LOG.md` (D044–D058)
- regenerated `docs/schema/README.md`
- `docs/reviews/phase3/markers/08_BUILD_COMPLETE.ready.md`

I did not run tests or migrations; the marker reports `make test` passing
93/93. My findings below are static review only.

## Summary

The build hits the spec on the major surfaces: schema shape, predicate
vocabulary, transition API, GUC-gated belief mutation guard, per-claim
salvage, relaxed-schema fallback, decision rules 0/1/2/3 and the temporal
auto-resolve, the `pipeline-3` warn-on-different-prompt-version path, and
the Phase 1/2 isolation of `pipeline`. The structure of the consolidator
matches the build prompt (separate `transitions` module, transition kinds
limited per spec).

Findings split between **Blockers** (must address before any operator pilot
or full-corpus run), **Hazards** (correctness or operator-safety risks the
operator should know about and that should land in a follow-up before #25),
and **Coverage gaps** (test debt that is consistent with the build
completing but should be filled before promoting Phase 3 past pilot).

I did not find a raw-immutability violation, an outbound-network egress, a
predicate-vocabulary drift between `extractor.PREDICATE_ENUM` and the seed
table, or a missing audit row on the happy paths I traced.

## Blockers

### B1. Different-value contradiction (Rule 3) is not transactionally atomic and is unsafe under concurrent consolidator passes

`process_claim_value_group` (`src/engram/consolidator/__init__.py:608`)
implements Rule 3 as three independent transactions:

```python
close_belief(conn, active.id, ..., transition_kind="close")  # txn 1
new_id = insert_belief(conn, payload)                        # txn 2
contradiction_id = insert_contradiction(conn, ...)           # txn 3 (implicit)
```

Each of `close_belief` / `insert_belief` opens its own
`with conn.transaction():` block and commits independently (or, under the
operator CLI where the connection is `autocommit=False`, releases its own
savepoint). The `except errors.UniqueViolation` retry then calls
`conn.rollback()` and re-loops.

The hazard:

- Step 1 closes the prior. Step 1 commits.
- Step 2's `INSERT INTO beliefs` collides with the active partial unique
  index because another consolidator inserted the same group key first.
- The retry runs again. The prior we closed in step 1 is **already
  superseded** in the database; `fetch_active_belief_for_group` now returns
  a different active row (the winner of the race). The loop closes that
  one too, then inserts.

The end state has two superseded rows (one of them closed for no reason,
its `belief_audit.transition_kind='close'` permanently logged), one
candidate, and a contradiction edge anchored on a `belief_a_id` that was
not the actual contradicting prior. `superseded_by` is not set for the
Rule 3 path (correct per spec), so the wrong-close row is still
traceable, but it is a real correctness defect: the audit trail will
attribute the close to "different value contradiction" even though the
row was closed during a stale retry.

This violates the build prompt's intent for D053 ("the transition API
catches the conflict, re-reads the now-existing active belief, and
retries the decision rules"). For Rule 3 to be safely retryable, the
close + new insert + contradiction must form a single atomic unit so a
losing retry leaves no side effects. Suggested approach (not patched
here): wrap Rule 3 in a single outer `conn.transaction()` and rely on
the partial-index conflict landing on the inner insert before any close
commits, OR re-fetch the active row inside the transaction with `FOR
UPDATE`, OR use `INSERT ... ON CONFLICT DO NOTHING` first to canary the
group key.

This hazard does not affect Rule 2 same-value supersession in the same
way: `supersede_belief` does close-then-insert-then-fix-superseded_by
under one `with conn.transaction()`, so all three statements share an
atomic boundary.

### B2. `process_claim_value_group` calls `conn.rollback()` after the inner transaction has already rolled back

In the cli code path (`autocommit=False`), the consolidator runs inside
a long-lived implicit outer transaction. `with conn.transaction()` inside
`supersede_belief` / `close_belief` / `insert_belief` becomes a savepoint.
When the inner statement raises `UniqueViolation`, the savepoint is rolled
back automatically by the context manager.

The `except errors.UniqueViolation: conn.rollback()` line at
`src/engram/consolidator/__init__.py:670` then rolls back the **outer
transaction**, discarding every prior mutation in this batch — including
unrelated belief inserts from earlier groups in the same conversation,
the `apply_phase3_reclassification_invalidations` UPDATE at the start of
`consolidate_beliefs`, and any `consolidation_progress` rows already
written. Tests do not catch this because the `conftest.py` fixture forces
`autocommit=True`, which makes inner transactions independent and turns
`conn.rollback()` into a near-noop.

Suggested fix direction (not applied): drop the `conn.rollback()` call —
the inner context manager has already rolled back to the failing
savepoint — and rely on the loop continuation. If a real explicit
rollback is needed, scope it via a savepoint, not the outer transaction.

### B3. `apply_reclassification_recompute` does close-then-insert-then-contradiction without the same retry guard

`apply_reclassification_recompute`
(`src/engram/consolidator/__init__.py:442`) handles D054 case 3
("non-empty surviving set, different value") with the same close → insert
→ contradiction shape as Rule 3, but **without** even the two-attempt
retry that `process_claim_value_group` has. Under any active-partial-index
conflict (concurrent consolidator, or a Rule 1/2/3 pass that interleaves),
the insert raises and the close is left committed. There is no reattempt.

The blast radius is smaller than B1 because reclassification recompute
runs inside Decision Rule 0 before the per-conversation rules, but the
correctness defect is the same: a closed belief on a partial failure with
no compensating action.

### B4. `apply_reclassification_recompute` decides "same value vs different value" using full JSONB equality, not the spec's per-cardinality value-equality rule

`apply_reclassification_recompute` calls `belief_value_equal` to choose
between D054 case 2 (same-value supersession) and case 3 (close-and-insert
plus contradiction). `belief_value_equal`
(`src/engram/consolidator/__init__.py:828`) compares full
`canonical_json(object_json)` for object_json beliefs and
`normalize_subject(object_text)` for object_text beliefs.

Per the spec:

> "For `multi_current` / `event` predicates, value equality is reduced to
> 'same group_object_key under the same predicate' — the discriminator is
> already part of the key."

For `multi_current` JSON predicates such as `has_pet` (group keys
`name,species`) or `is_related_to` (group key `name`), the surviving
claim set after a partial reclassification can legitimately produce a
different `object_json` (e.g., one of the contributing claims dropped a
`since` value) while keeping the same `group_object_key`. The spec calls
that "same value" — the implementation will see different `object_json`
and route it to case 3, opening a contradiction at
`detection_kind='reclassification_recompute'` that should not exist.

`process_claim_value_group` correctly special-cases this with
`first.cardinality_class in {"multi_current", "event"}`. The recompute
path is missing the same guard.

### B5. `claim_extractions` mutation guard rejects the `superseded_by_extraction_id` raw_payload merge UPDATE used by the extractor's success path

The trigger `fn_claim_extractions_mutation_guard` at
`migrations/006_claims_beliefs.sql:297` allows UPDATE only when
`id, segment_id, generation_id, extraction_prompt_version,
extraction_model_version, request_profile_version, created_at` are all
unchanged. That permits status / claim_count / completed_at / raw_payload
updates as required.

The extractor at `src/engram/extractor.py:540` issues:

```sql
UPDATE claim_extractions
SET status = 'superseded',
    completed_at = COALESCE(completed_at, now()),
    raw_payload = raw_payload || jsonb_build_object(
        'superseded_by_extraction_id',
        %s::text
    )
WHERE segment_id = %s
  AND id <> %s
  AND status = 'extracted'
```

That update changes only `status`, `completed_at`, and `raw_payload`, all
of which the trigger allows. **No defect here on the trigger** — I
verified it explicitly. Withdrawing this from the blockers list. *(See
note: I am leaving this paragraph in place for transparency about what I
checked; the actual blocker count is B1–B4.)*

## Hazards

### H1. Migration renumbering was performed despite the build prompt forbidding it

`git status` shows
`D migrations/004_source_kind_gemini.sql` and
`?? migrations/005_source_kind_gemini.sql`. The build prompt P028 says
"if `006` is no longer the next available slot, stop and report the
conflict instead of renumbering unrelated migrations." The completion
marker does not call this out. The rename appears to have happened in
the worktree before P028 ran — P028's own text already calls
`005_source_kind_gemini.sql` "the current prior migration" — but the
rename is still uncommitted, which means any operator who pulls this
branch and runs `make migrate` against a database that already recorded
`004_source_kind_gemini.sql` will see ledger drift (the renamed file's
SHA does not match any prior `schema_migrations` row by filename, and
the prior `004_source_kind_gemini.sql` row has no on-disk file).

Recommendation for the coordinator: confirm whether the renumber is
sanctioned (by an earlier prompt the build prompt is aware of) and, if
so, commit it explicitly so the build review trail is unambiguous;
otherwise the operator pilot must run only against a database whose
ledger never contained `004_source_kind_gemini.sql`.

### H2. `engram extract --segment-id UUID` calls `apply_phase3_reclassification_invalidations` per-segment

`extract_claims_from_segment`
(`src/engram/extractor.py:423`) invokes
`apply_phase3_reclassification_invalidations(conn)` and
`reap_stale_extractions(conn)` on every call. In a batch this runs N
times — once per segment. The reclassification UPDATE is global and
re-inspects every invalidated segment and every active extraction. On a
warm corpus this is wasteful; in a long batch it amplifies progress
churn (every segment that triggers the hook bumps two
`consolidation_progress` rows).

Functionally correct, but operator pilot timing will be misleading until
this hook is hoisted to the batch entry (`extract_pending_claims` and
`engram pipeline-3`). The build prompt phrased the hook as something
that runs "before `engram extract`, before `engram consolidate`, and
inside `engram pipeline-3`" — once per command, not once per segment.

### H3. `find_reclassification_capture_id` returns at most one capture id per orphan belief

`src/engram/consolidator/__init__.py:962` joins the orphan belief's
claim_ids → segments → `consolidation_progress` rows at
`stage='privacy_reclassification', status='completed'`, returning the
most recent one by `updated_at`. If the belief's claim set spans two
captures (e.g., two messages on the same conversation reclassified at
different times), only the latest is recorded in
`score_breakdown.cause_capture_id`. The spec text for D054 reads
"reclassification capture id" singular and `score_breakdown` is JSONB,
so this is not a strict contract violation, but operator post-hoc audits
that follow the capture id back to its capture row will lose the older
one.

Worth a one-line schema-doc note that `cause_capture_id` is "most recent
capture", or a follow-up to switch to `cause_capture_ids` array.

### H4. `apply_phase3_reclassification_invalidations` does not propagate the privacy-reclassification cause through to `claim_extractions.raw_payload.failure_kind`

The function writes `raw_payload || jsonb_build_object('failure_kind',
'privacy_reclassification', 'superseded_by_phase3_invalidation', true)`.
The build prompt's D035 failure kinds are
`parse_error | schema_invalid | service_unavailable | context_guard |
retry_exhausted | trigger_violation`. `privacy_reclassification` is a
new kind specific to Phase 3 — fine — but the docs/spec do not list it.
A new kind in the wild without a spec entry is the kind of drift D035
was designed to prevent.

Add `privacy_reclassification` to the documented `failure_kind` enum in
`docs/claims_beliefs.md` and `BUILD_PHASES.md` as a follow-up.

### H5. `is_friends_with` / `works_with` / `prefers` etc. carry `group_object_keys=ARRAY['text']` in the seed but the trigger never reads it

`migrations/006_claims_beliefs.sql:81` seeds text-typed
multi-current predicates with `group_object_keys=ARRAY['text']`. The
trigger `fn_beliefs_prepare_validate` only reads `group_object_keys` for
JSON predicates; for text predicates it always uses
`engram_normalize_subject(NEW.object_text)`. The literal `'text'` token
is therefore meta-marker noise in the table.

Not a correctness bug today; it is a footgun the next time someone
reads the table and tries to use it. Either remove the `'text'` token
from these rows (set `group_object_keys=ARRAY[]::text[]` for object_text
predicates) or document that `'text'` is reserved.

### H6. The transition GUC is set with `current_setting('engram.transition_in_progress', true)` but the trigger does not validate it equals the row's request UUID

The transition API in `transitions.py` sets the GUC then writes the
audit row with the same `request_uuid`. The trigger
`fn_beliefs_prepare_validate` checks the GUC is non-empty but does not
require its value to match anything. Direct SQL operators who happen to
have set the GUC by hand (e.g., for debugging) could mutate beliefs
without writing an audit row at all; the trigger is a defense in depth,
not an invariant.

D052 is explicit that this is the chosen design ("The trigger does not
have to prove a future audit row will arrive; the API guarantees it
before lifting the GUC"). Worth a short README in the transition module
warning operators not to set the GUC manually. Not a defect against the
spec.

### H7. The audit row for a same-value supersede points only to the prior; the new candidate has no `belief_audit` row

`supersede_belief` writes one audit row at
`belief_id=prior_id, transition_kind='supersede'`. The new candidate it
inserted has no audit row at all. The spec explicitly endorses one row
("Write a `belief_audit` row with `transition_kind='supersede'`"), but
operator queries that walk `belief_audit` to find a belief's lifecycle
will find an active candidate with no `transition_kind='insert'` row.

If this is intentional, document it in `docs/claims_beliefs.md` ("Rule 2
emits one audit row, anchored on the prior"); if not, emit both rows
under the same `request_uuid` (the build prompt's "audit row may
describe one logical transition even when the transition API uses more
than one physical UPDATE" wording suggests one is enough, but it is not
unambiguous).

### H8. `supersede_belief` audit logs `previous_status=prior["status"]` which may already be `superseded` after the first physical UPDATE

`supersede_belief` first UPDATEs the prior to `status='superseded'`,
then inserts the new row, then writes the audit. By the time
`_insert_audit` runs, `prior["status"]` was captured *before* the
UPDATE (via `_fetch_belief_for_update`), so `previous_status` is the
expected `candidate`. I traced this carefully — it is correct. Calling
out so the next reviewer doesn't have to retrace.

### H9. The relaxed-schema fallback allows the model to emit predicates outside the V1 enum

`extraction_json_schema(..., relaxed_schema=True)` removes both the
`predicate.enum` constraint and the `evidence_message_ids.items.enum`
constraint, leaving only a UUID regex on evidence ids and an open
string for predicate (`src/engram/extractor.py:266`). Pre-validation in
`validate_claim_draft` then rejects any predicate not in
`PREDICATE_BY_NAME`. So an out-of-vocab predicate from the model is
salvaged-out as `dropped_claims`, not committed. Functionally correct,
but the relaxed path has visibly weaker schema-level prevention than
the strict path. Worth a comment in `extraction_json_schema` documenting
that the trigger / `validate_claim_draft` are the load-bearing
defenses on the relaxed path.

### H10. `requeue_extraction_conversation` resets `error_count=0` on the extractor progress row, but does not reset the consolidator progress row

Per the build prompt: `engram extract --requeue --conversation-id UUID`
"resets the extractor progress row's `error_count` and `last_error`,
then retries that conversation through the normal bounded extraction
path." That's what the implementation does. It does **not** reset the
consolidator row, which is correct — the consolidator is downstream and
its error_count is independent — but the operator-facing CLI text
("extract requeue: N in-flight extraction(s) marked failed") doesn't
hint at this. Minor doc concern; flag to the runbook author.

## Coverage gaps

These are tests the build prompt asked for that I cannot find in
`tests/test_phase3_claims_beliefs.py`. The build can still claim
acceptance because most schema-level invariants are pinned; the gaps
matter before a 50-conversation pilot.

- **D054 three-branch test (acceptance #24).** Only the empty-surviving
  branch (`reject`) is exercised in
  `test_decision_rule_0_rejects_orphan_and_reclassification_hook`. The
  same-value-surviving branch (supersede) and the
  different-value-surviving branch (close + insert + contradiction at
  `detection_kind='reclassification_recompute'`) are not. D054's own
  decision-log row says "Acceptance test #24 covers all three branches";
  one out of three is in the suite.
- **Concurrent consolidator pass (acceptance #30).** Build prompt
  required a "deterministic two-connection recipe; do not use
  sleep-based thread timing". I see no such test. Combined with B1/B2,
  this is the gap most likely to bite under a real concurrent pilot.
- **Orphan rejection causes #28.** Only `orphan_after_reclassification`
  is asserted. `orphan_after_reextraction` and
  `orphan_after_segment_deactivation` paths in `orphan_cause_for_claims`
  have no test.
- **Re-extraction blast radius #27.** The closest test is
  `test_extractor_empty_failure_replacement_and_reaping`, which
  verifies the supersede transition on `claim_extractions` but does not
  assert that the consolidator only sees v2 claims (no v1 claim
  contributes to a belief).
- **Lineage traversal #33.**
  `test_rebuild_structural_equivalence_and_lineage` asserts the rebuild
  audit shape but does not walk the contradiction
  `belief_a_id`/`belief_b_id` path back from a closed belief.
- **Claim-count parity #37.** No explicit test asserts
  `claim_extractions.claim_count = (SELECT count(*) FROM claims WHERE
  extraction_id = ...)` after partial salvage. Implicitly held by
  `test_extractor_request_shape_parse_rejections_and_salvage` which
  asserts `claim_count == 1`, but a regression that off-by-ones the
  count would still pass.
- **`pipeline-3` warning DB-state test.**
  `test_cli_pipeline_is_phase2_only_and_pipeline3_warns` mocks
  `active_beliefs_with_other_consolidator_version` to return 1; the
  underlying SQL of `active_beliefs_with_other_consolidator_version`
  has no integration test. A typo in the partial WHERE clause would
  silently never warn in production.
- **`engram extract --requeue` flow.** The function
  `requeue_extraction_conversation` is exported and reachable from the
  CLI, but no test exercises it end-to-end (transition `extracting →
  failed/manual_requeue`, progress reset).
- **Subject normalization fixture coverage #31 is shallow.** Three
  fixtures (`" User!! "`, `"Ａlice\tSmith..."`, `"Project  Engram?"`)
  cover whitespace, NFKC fullwidth, ellipsis, mid-word tab, trailing
  punctuation, and case. They do not cover internal punctuation that
  must be **kept** (e.g., `"my friend O'Brien"`), Unicode combining
  marks that NFKC reorders, or empty/whitespace-only input. Parity
  testing on the strict spec rule needs a wider net before a pilot.

## Spec / schema deltas I checked and did not flag

- Predicate vocabulary parity between
  `extractor.PREDICATE_VOCABULARY` (Python) and the SQL seed: identical
  set, identical stability/cardinality/object_kind/required_object_keys
  on every row. Test `test_predicate_vocabulary_and_extractor_schema_parity`
  pins this.
- `experiencing` is excluded from both seed and enum. ✓
- `lives_at` is JSON-only with `address_line1` required. ✓
- `talked_about` is event-class. ✓
- `belief_audit.evidence_message_ids` is named per S-F016 (not
  `evidence_episode_ids`). ✓
- `claims` is insert-only via `fn_claims_insert_only`. ✓
- `beliefs` mutation trigger limits UPDATE to
  `valid_to, closed_at, superseded_by, status`. ✓
- `contradictions` UPDATE limited to
  `resolution_status, resolution_kind, resolved_at`; DELETE blocked. ✓
- `belief_audit` UPDATE/DELETE blocked. ✓
- D034 request shape: `stream=False, temperature=0, top_p=1,
  max_tokens=8192, chat_template_kwargs.enable_thinking=False,
  response_format.type=json_schema`. ✓
- Markdown-fenced / reasoning-only / non-JSON / empty-content responses
  rejected. ✓
- D037 context-guard via `assert_context_budget`. ✓
- D058 per-claim salvage: surviving claims commit, dropped land in
  `raw_payload.dropped_claims`, status escalates correctly. ✓
- Tool / null-content message placeholders preserved as cite-able
  `message_id` evidence in the prompt. ✓
- `pipeline` does not invoke Phase 3; `pipeline-3` warns on different
  consolidator `prompt_version`. ✓
- `subject_normalized` SQL parity with Python `normalize_subject`. ✓
  (within fixture coverage caveat above)
- D055 rebuild closes via `transition_kind='close'` then re-inserts
  candidates; structural equivalence asserted. ✓
- Stale `extracting` reaping uses UPDATE (not DELETE), records
  `failure_kind='inflight_timeout'`, does not increment `error_count`. ✓

## Operator hazards before pipeline start

1. Do not run `engram pipeline-3` against a corpus with concurrent
   extractors / consolidators until B1, B2, B3 are addressed. Single
   process operator usage is safe.
2. Confirm with the coordinator that the
   `004_source_kind_gemini.sql` → `005_source_kind_gemini.sql` rename
   (still uncommitted in the worktree) is sanctioned, and commit it
   before any non-scratch DB sees the new migration ledger.
3. Document `failure_kind='privacy_reclassification'` (H4) before
   operators encounter it in raw payloads.
4. Before the 50-conversation pilot (#25), stand up the missing tests in
   the Coverage gaps section, especially the D054 three-branch tests
   and the concurrent-consolidator recipe (#30), so the pilot's exit
   criteria can be unambiguously asserted.

## Verdict

The build is structurally complete and consistent with `docs/claims_beliefs.md`
on every schema and transition surface I checked. It is **not** safe for
concurrent Phase 3 operation today (B1, B2, B3); it **is** safe for a
single-operator extract / consolidate / pipeline-3 run on a Phase 2
corpus.

Recommend: address B1/B2/B3 in a focused follow-up (no schema migration
needed; all three live in `consolidator/__init__.py` and a small
adjustment to the retry boundary), B4 with a one-liner cardinality
guard, and the missing tests #24 / #28 / #30 / #33 / #37 before the
50-conversation pilot gate.
