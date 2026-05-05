# Phase 3 Claims and Beliefs Spec — Review (Claude Opus 4.7, fresh context)

Date: 2026-05-05
Reviewer: claude_opus_4_7
Lens: architecture coherence, temporal semantics, evidence and audit model,
false-precision risks, human-review boundaries.
Target artifact: `docs/claims_beliefs.md` (P021 spec draft).
Upstream consulted: RFC 0011, DECISION_LOG (through D047), HUMAN_REQUIREMENTS,
BUILD_PHASES, ROADMAP, SPEC, docs/schema/README, docs/segmentation,
docs/process/multi-agent-review-loop, marker
`01_SPEC_DRAFT.ready.md`.

I did not read peer reviewers' files. I did not edit `docs/claims_beliefs.md`.

## Summary verdict

`accept_with_findings`.

The spec is internally coherent on most surfaces (schema, extraction lifecycle,
audit invariants, privacy carry, resumability), and the predicate vocabulary
plus deterministic-Python consolidator are a defensible V1 floor. Two
findings are P0: (a) `valid_to = now()` on the close paired with
`valid_from = MIN(messages.created_at)` on the new row breaks bitemporal
correctness for both biographic queries and the auto-resolution rule the spec
itself defines, and (b) re-extraction does not bound blast radius in the
specified consolidator algorithm — old and new extraction-version claims for
the same segment co-feed the consolidator and produce spurious
contradictions. Both must be amended in P024 before the build prompt lands.
The remaining findings are P1–P3 and reasonable to absorb as part of the
synthesis pass.

## Findings ordered by severity

### P0-1. `valid_to = now()` on close + `valid_from = MIN(...)` on contradiction insert breaks bitemporal correctness and makes auto-resolution unreachable

**Affected:** *Time semantics* table (lines 274–282), *Decision rules* §3
contradiction (lines 376–385), *Stage B — Belief consolidation* `valid_from`
spec (line 279), acceptance test #22 (lines 749–751), RFC 0011 OQ5.

**Issue.** The contradiction-supersession rule sets the prior belief's
`valid_to = now()`. The new belief opens with
`valid_from = MIN(messages.created_at)` over the new evidence subset — i.e.,
some moment in the past. Therefore the prior's interval is
`[valid_from_prior, now()]` and the new's interval is
`[past_time, NULL]`. They overlap on `[past_time, now()]` for every
contradiction landed against historical corpus evidence. The non-overlap
clause (line 379–382) — "Auto-resolve only when the two beliefs' validity
intervals (`valid_from` / `valid_to`) are non-overlapping" — therefore never
fires for the historical corpus. Acceptance test #22, which asserts
auto-resolution to `temporal_ordering`, is unreachable under the rule the
spec ships.

The same defect is worse for biography queries. Per HUMAN_REQUIREMENTS, the
distinguishing property of engram is "every fact carries a validity interval
… not just a created-at timestamp." A 2026 consolidator pass over 2018
evidence that supersedes a 2020 belief would close the 2020 belief at
`valid_to = 2026-XX`, falsely asserting that the old fact remained valid
until 2026. The biography-at-an-arbitrary-instant query
("what did I believe on 2020-06-15?") returns the wrong belief, by years.

**Consequence.** Two simultaneous failures: (1) the auto-resolution rule the
spec defines is dead code on real data, and (2) the central biographic
correctness property the architecture is built around is broken at the
write path. Test #22 cannot pass as written.

**Proposed fix.** On contradiction supersession, set the prior's
`valid_to = MIN(messages.created_at)` over the new evidence subset (the
moment the contradicting evidence first appears). This makes the two
intervals abut and the non-overlap auto-resolution fire correctly. The same
rule should apply to the same-value supersession close — the prior fact
became "the moment we learned about it" (`MIN`) for the new evidence
window, not "now". Document `now()` only on the `recorded_at` column, where
it belongs.

If the owner wants to keep `valid_to = now()` for some narrow case (e.g.,
the operator explicitly closes a belief by hand), that should be a separate
transition kind (`manual_close` or similar) on `belief_audit`, not the
default for consolidator-driven supersession.

### P0-2. Re-extraction blast radius (D045) is violated — old and new extraction-version claims co-feed the consolidator

**Affected:** *Re-derivation behavior (D045)* (lines 412–418), *Decision
rules* (lines 354–390), *Stage B — Belief consolidation* (lines 322–440),
RFC 0011 §1 (re-extraction non-rebuilding).

**Issue.** Line 415 says re-extraction inserts new `claims` rows; existing
claims remain insert-only. Line 418 says the consolidator "picks up new
claims alongside existing ones on its next pass." Line 309 says the
consolidator "excludes them [invalidated claims] from active belief
consolidation by joining on the active segment generation."

These rules together mean: for an active segment with two extraction
generations (`extractor.v1.*` and `extractor.v2.*`), the consolidator sees
both vintages of claims for the same `(subject, predicate)` group key.
If `v2` produced a different value than `v1` on the same segment, the
consolidator emits a contradiction — even though the right semantics is
"v2 supersedes v1 for this segment." D045's stated property — "blast radius
of a prompt bump bounded" — does not hold under the specified algorithm.

**Consequence.** Every operator-driven prompt bump produces spurious
contradictions on every segment whose new extraction differs from its old
one. The contradictions table fills with noise that cannot be auto-resolved
(per P0-1 that path is broken anyway, but also: the two vintages have
identical `evidence_message_ids` so any timestamp-based rule will see
overlap or coincidence, not ordering). HITL review queue gets flooded with
artifacts of the prompt bump rather than real conflicts in the corpus.

**Proposed fix.** Add an explicit consolidator filter rule:

> For each segment, only the latest extraction-version's `claims` rows
> contribute to consolidation. Latest is defined as the active
> `claim_extractions` row at `status='extracted'` with the most recent
> `(extraction_prompt_version, extraction_model_version)` order — or
> equivalently, join through `claim_extractions WHERE status='extracted'`
> and dedupe on `segment_id` keeping the highest `created_at`.

The spec needs a single-sentence rule and a test (gap #4 below). The
existing partial unique index on `claim_extractions` already enforces "at
most one active extraction per (segment, version)"; what's missing is the
rule that consolidator picks the newest one per segment.

### P1-3. `subject_normalized` is required NOT NULL but its computation site is unspecified

**Affected:** `beliefs` schema (line 521).

**Issue.** Line 521: "`subject_normalized | TEXT NOT NULL | computed at
insert via the `normalize` rule; index target`." The `normalize` rule is
defined in Python (lines 335–346). The spec does not say whether the column
is a SQL `GENERATED ALWAYS AS (...) STORED` expression, computed by a
trigger, or set by the application code. Each path has different
correctness properties:

- A Python-side computation can drift from any other consumer that joins
  on the column (e.g., the partial index for current beliefs at line 553).
- A generated column requires the `normalize` rule to be expressible in
  SQL — possible (lower / regexp_replace / btrim) but the spec doesn't
  pin the SQL form, and trailing-punctuation strip is a fixed set
  requiring an explicit regex.
- A trigger is the most conservative option and aligns with how
  `claims.evidence_message_ids` is validated (line 504), but adds
  per-insert overhead.

**Consequence.** The build prompt is forced to make this call without spec
authority. If two implementers normalize differently (e.g., one strips
unicode combining marks, the other does not), the partial active-belief
index breaks and the consolidator can produce duplicate active beliefs for
what should be the same group key.

**Proposed fix.** Pin the storage strategy in the spec. My recommendation:
SQL `GENERATED ALWAYS AS` with the exact normalize expression spelled out.
Co-document the Python `normalize` function as the canonical reference and
call out that any change requires a generated-column expression update plus
a non-destructive backfill via close-and-insert. If the normalize rule is
too rich for SQL, fall back to a `BEFORE INSERT` trigger that calls a
SQL function `engram_normalize_subject(text) RETURNS text`, and require
both Python and SQL to use the same function.

### P1-4. No UNIQUE constraint on the active belief partial index — concurrent consolidator passes can produce duplicate active beliefs for the same group key

**Affected:** `beliefs` indexes (lines 552–558), *Consolidator parallelism*
(lines 432–440).

**Issue.** Line 553–554: "`(subject_normalized, predicate)` partial WHERE
`valid_to IS NULL` (the Phase 4 `current_beliefs` view will use this)" — an
*index*, not a *unique index*. The consolidator runs per-conversation (line
437). Per-conversation parallelism is permitted in the spec (line 433: "V1
default: per-conversation pipeline"). When two conversations both produce a
new claim for the same `(subject_normalized, predicate)` group key, the two
consolidator passes can both observe "no existing belief," both insert a
`candidate` row, and both succeed. Result: two active candidate beliefs for
the same group key, neither superseding the other.

The spec mentions this race is bounded by per-conversation grouping (line
437–440) but the bound only holds for claims a pass *introduces*; the
`(subject_normalized, predicate)` group key crosses conversation boundaries
by design.

**Consequence.** Active belief set is not a function of the active claim
set. `current_beliefs` retrieval returns N>1 rows for a single fact. Phase
4 review queue shape inflates.

**Proposed fix.** Either (a) make the partial index UNIQUE — preventing the
race at write time and forcing the loser to re-read and rerun the
decision rules — or (b) declare consolidator runs serial (no
per-conversation parallelism) and write that down explicitly. (a) is
strictly safer and pairs well with the existing close-and-insert idiom; it
adds one retry path on conflict but is otherwise transparent. The existing
partial unique index on `claim_extractions` is precedent for this idiom in
the same migration.

### P1-5. Partial-reclassification recompute path is silent on the "different surviving value" and "empty surviving set" cases

**Affected:** *Privacy-tier propagation* (lines 295–316).

**Issue.** Lines 313–316 specify two outcomes for a partial-reclassification
recompute: (a) surviving set yields the same value → fresh `candidate` row
supersedes prior, and (b) implicitly: surviving set yields a different
value or empty set → unspecified.

If the surviving set yields a different value, is that handled by the
contradiction supersession path? The text says "supersedes the prior via
the normal close-and-insert flow," which is the same-value path. Different
value would need to flow through `contradictions`. Whether it does, and
whether `belief_audit.transition_kind` is `supersede` or `reject`, is
undefined.

If the surviving set is empty (every contributing claim was on an
invalidated segment), the rule on line 311–313 — "Beliefs whose `claim_ids`
are *fully* drawn from invalidated claims are rejected" — would apply.
But "fully drawn from invalidated claims" is computed against `claim_ids`,
not against "claims still active under the active segment generation." Two
different definitions of "invalidated" are in play (claim row vs. active
segment join), and reviewers cannot tell which one the consolidator queries.

**Consequence.** Acceptance test #24 tests the fully-invalidated case but
not the partial cases. The build prompt has to make the same judgment
call and may pick differently than the spec author intended.

**Proposed fix.** Spell out the recompute decision tree:

1. Compute the surviving claim set (claims attached to currently-active
   segment generations).
2. If empty → reject (status='rejected', transition_kind='reject').
3. If non-empty and yields the same value as the prior belief → close-and-
   insert under the same value (transition_kind='supersede').
4. If non-empty and yields a different value → close-and-insert with the
   new value, write a `contradictions` row at `detection_kind=
   'reclassification_recompute'`, leave `resolution_status='open'` for the
   Phase 4 review queue. Auto-resolution should NOT fire on this kind —
   it's a privacy event, not a temporal event.

Add a corresponding acceptance test (gap #2 below).

### P1-6. `engram consolidate --rebuild` cannot be a "no-op against an unchanged claim corpus" under the close-and-reinsert rule the spec specifies

**Affected:** *Re-derivation behavior (D045)* (lines 411–429), CLI rebuild
mode (lines 681–684), acceptance test #23 (lines 752–754).

**Issue.** The rebuild flow on lines 421–429 is "closes the active belief
set and reruns the decision rules over the full active claim set." Then
test #23 asserts: "running it twice in a row is a no-op against an
unchanged claim corpus."

Walk the second invocation:
1. Start state: active belief B (post-rebuild #1), `valid_to=NULL`.
2. Rebuild #2: close B → `valid_to=now()`, `status='superseded'`. Audit row
   at `transition_kind='close'`.
3. Run decision rules: for the `(group_key)`, no active belief exists. Rule
   §1 fires → INSERT new candidate B'. Audit row at
   `transition_kind='insert'`.

The result is structurally similar to before (one active candidate per
group key with the same value) but with a different `id`, different
`recorded_at`, two extra `belief_audit` rows, and a closed predecessor B
in the chain. That is not a no-op by any reasonable definition of "no-op
against an unchanged claim corpus."

**Consequence.** Test #23 fails as worded. The rebuild semantics are
non-idempotent, which both bloats `belief_audit` and makes
`engram consolidate --rebuild` unsafe to run repeatedly. Operators
re-running rebuild after a transient failure get duplicate audit chains
each time.

**Proposed fix.** Choose one:

- **(A)** Re-define the test: rebuild #2 produces a structurally equivalent
  active belief set with possibly-different audit/id columns, and the
  invariant is "no new contradictions, no value changes, no ID-stable
  diff" rather than "no-op." Probably the right call.
- **(B)** Add a no-op short-circuit to rebuild: before close-and-reinsert,
  compute the proposed new belief set; if it matches the current active
  set under value-equality and provenance-equality, skip the close-and-
  insert. Idempotent at the cost of complexity.
- **(C)** Define `--rebuild` more narrowly: only rebuild beliefs whose
  contributing claim set has changed since the last consolidator pass.
  Requires tracking "consolidator's last seen claim set per group key"
  somewhere — the spec doesn't currently store that.

(A) is the smallest change. The spec should pick one and commit.

### P1-7. Discovery time vs. biographic time conflation

**Affected:** *Time semantics* (lines 274–292), *Predicate vocabulary*
JSON shapes (lines 199–230), HUMAN_REQUIREMENTS ("Temporal validity on
every fact" — lines 586–589), RFC 0011 OQ7.

**Issue.** Several predicates carry biographic time inside `object_json`:
`holds_role_at` has `since`, `until?`; `traveled_to` has `when?`;
`committed_to` has `by_when?`; `lives_at` has `since`; `born_on` is itself
the biographic date. None of these are lifted into `beliefs.valid_from` /
`valid_to`. The bitemporal interval is purely discovery time —
"when the corpus first/last saw evidence of the assertion" — not "when the
assertion was true of the world."

HUMAN_REQUIREMENTS uses the same column names (`valid_from` / `valid_to`)
to describe the biographic interval ("'User lives at 123 Main' is true
*from* 2018-04 *until* 2022-09"). The spec's V1 derivation makes
`valid_from = 2024-03-01` (the conversation date), not 2018-04, even
though the user explicitly told the model "2018-04."

**Consequence.** The biography-at-an-arbitrary-instant query — the
distinguishing property of engram — does not work in V1. A query
"what did the user believe on 2020-06-15?" returns nothing, because every
`valid_from` is 2024+ (the discovery date). Phase 4 / 5 will discover the
same gap and have to either rename columns or backfill with a
biographic-time lift from `object_json`.

**Consequence (secondary).** Without an explicit acknowledgement in the
spec, downstream prompts/code will treat `valid_from` as biographic and
build queries on it. By the time someone notices, it's a schema-rename
problem that touches every reader.

**Proposed fix.** Add a section to the spec, *Discovery time vs.
biographic time*, that:

1. States explicitly that V1 `beliefs.valid_from` and `valid_to` are
   discovery time, not biographic time.
2. Says the biographic time fields live in `object_json` (`since`,
   `until`, `when`, `by_when`) and are not currently lifted into the
   bitemporal columns.
3. Names this as a known V1 limitation against HUMAN_REQUIREMENTS'
   biography promise, with a deferred work item ("Phase 4+ may add
   `biographic_valid_from` / `biographic_valid_to` columns or a
   computed view that joins them out of `object_json`").

This is a documentation-only fix in the spec — it does not change schema
or rules — but it prevents a load-bearing principle from quietly drifting
through Phase 3 unchallenged.

### P2-8. Confidence aggregator `MAX` is the most aggressive choice and is in tension with the false-precision contract

**Affected:** *Confidence aggregator* (lines 391–395), HUMAN_REQUIREMENTS
"Why refusal of false precision is a contract" (lines 332–358), D022
inline confidence tags.

**Issue.** `confidence = MAX(claims.confidence)` over the contributing
claim set. If five extractions produced confidences `[0.2, 0.3, 0.3, 0.4,
0.95]` for the same group key, the belief surfaces at `0.95`. If only the
last extraction produced `0.95` (the others disagree on subjective grounds
like "did the user really commit to that?"), the MAX hides the underlying
spread. D022's inline `(conf=0.95)` then misrepresents the consensus to
the consuming model — exactly the failure mode HUMAN_REQUIREMENTS calls
"a context layer that confidently asserts unknowns is worse than no
context layer."

The consolidator's `raw_payload` preserves rationale, but `context_for`
(Phase 5) reads `beliefs.confidence` for the inline tag, not the audit log.

**Consequence.** Every Phase 5 retrieval result inherits an over-confident
confidence number. Downstream models that learn to trust the tag are
trained on a positively biased signal.

**Proposed fix.** Switch V1 default to **mean** of contributing claim
confidences, weighted optionally by the count of distinct evidence message
IDs (more evidence → higher weight, capped). MAX should be retained as a
field on `belief_audit.score_breakdown` for forensic use. The owner can
keep MAX if there's a specific argument I'm missing (e.g., "single high-
confidence extraction is enough"), but the spec should explicitly
acknowledge the false-precision tension; right now it cites RFC 0011 OQ6
as resolved and moves on.

### P2-9. Dual-shape predicates (`lives_at`) cause guaranteed duplication and the spec accepts it

**Affected:** *Predicate vocabulary* (line 204 `lives_at`), *Object
representation (D046)* (lines 237–251), *Value equality* (lines 349–352).

**Issue.** `lives_at` is the only predicate in the V1 enum that allows
both `object_text` and `object_json` shapes. The spec documents that
"Across the column boundary the consolidator does **not** auto-merge in
V1" (line 248–251), which is consistent — but `lives_at` is an
identity-class predicate where having two parallel chains for the same
fact is precisely the worst outcome. `holds_role_at` (similarly structured
in concept) is JSON-only; `has_pet` is JSON-only. Why is `lives_at` the
exception?

**Consequence.** Every conversation that mentions an address sometimes as
"123 Main" and sometimes as `{address_line1: "123 Main", city: "...", ...}`
produces two separate `(my, lives_at)` chains. Phase 4 entity
canonicalization will need to merge them, but it cannot do so without an
LLM tiebreak (or address parsing) — which is exactly what V1 is trying to
defer.

**Proposed fix.** Make `lives_at` JSON-only for V1, mirroring
`holds_role_at`. Update the prompt-side rule and the response schema so
the extractor cannot emit `object_text` for `lives_at`. Short-form text
addresses become `object_json: {address_line1: "<text>"}` with the other
keys absent. This costs nothing in expressive power and prevents a known
duplication.

### P2-10. Predicate semantics need a disambiguation guide; several predicates overlap

**Affected:** *Predicate vocabulary* (lines 199–230), RFC 0011 OQ1 (D046
locked the enum but not the semantics).

**Issue.** Several predicate pairs/triples have unclear extractor-side
distinctions:

- `met_with` vs. `is_friends_with` vs. `relationship_with` — when the user
  says "I had lunch with Sam," does the extractor emit `met_with({name:
  Sam})`, or `is_friends_with("Sam")`, or both, or neither? The prompt
  has no rule.
- `feels` vs. `experiencing` — `feels: "anxious"` vs. `experiencing:
  "anxiety"` are the same fact under different lexicalizations.
- `talked_about` is mapped to `preference` stability class (line 228),
  but "I talked about gardening" is neither a preference nor stable — it
  is a topic-of-conversation event. The classification looks accidental.
- `intends_to` vs. `plans_to` vs. `wants_to` — three goal-class predicates
  with overlapping semantics. `plans_to` is JSON-shaped, the other two are
  text. Without rules, the extractor's choice is non-deterministic across
  runs.

**Consequence.** Two extractor runs on the same segment under the same
prompt version may emit different `predicate` columns for the same
underlying assertion. Group-key collisions don't fire; duplicate chains
proliferate. This is a deterministic-enum lock without deterministic-
emission semantics — defeats the purpose of D046.

**Proposed fix.** Add a *Predicate emission guide* to the spec (or to the
prompt itself): a one-sentence rule per predicate stating when the
extractor must use it vs. an alternative. For overlapping pairs,
consolidate or define a clear precedence rule. Specifically: drop
`talked_about` (or move it to a different stability class with a clearer
definition); merge `experiencing` into `feels`; require `relationship_with`
when the assertion includes a `status` enum, otherwise `is_friends_with` /
`is_related_to`; require `met_with` only for events with a `when?` value.

### P2-11. Extractor schema enum size at the upper tail of `message_ids` may stress ik-llama grammar

**Affected:** *Extractor request profile* (lines 119–142), *Extractor
structured-output schema* (lines 154–169), D037, D036 echo (line 244 RFC
0011).

**Issue.** Phase 2 audit reported segment-level `message_ids` p99 = 62.
Phase 3 inherits Phase 2's segment substrate but does NOT window further;
the extractor processes one segment at a time. The JSON schema constrains
`evidence_message_ids.items.enum` to the segment's exact UUID set
(line 159–162). At p99=62 this is a 62-entry enum. Beyond p99, the tail
goes higher; the spec doesn't cite a cap.

D037 documented that ik-llama crashes at context shift under
grammar-constrained generation. The spec's context guard (line 151–152)
addresses prompt-token budget but not grammar-state size. There is no
benchmark in the spec confirming that large enum schemas combined with
the longest segments work reliably under D034 sampling.

**Consequence.** A small fraction of segments at the tail may consistently
fail with `failure_kind='trigger_violation'` or grammar-related errors,
contributing to the failure-pattern that Phase 3 evaluation will then
have to disentangle.

**Proposed fix.** Before the build prompt locks the schema, add an
acceptance pre-flight: run the extractor schema against the largest 1%
of active segments (by `message_ids` cardinality) and confirm zero
grammar errors. If the test fails, the spec gains a per-segment
enum-size cap and a fallback ("for segments with > N messages, the
schema relaxes the enum to a UUID pattern and relies on the trigger
backstop"). This is a P2 because it's a contingent risk; if the pre-
flight passes, no spec change is needed.

### P2-12. `contradictions.detection_kind` includes a value that no decision rule emits

**Affected:** `contradictions` schema (lines 580–598), *Decision rules*
(lines 354–390).

**Issue.** Line 588 documents `detection_kind` examples as
`same_subject_predicate` and `temporal_overlap_disagreement`. The
decision rules only specify the first one. `temporal_overlap_disagreement`
is undefined — no rule fires it. If the schema CHECK ever pins the enum
(it currently does not, since `detection_kind TEXT NOT NULL` is open),
this becomes a dead value.

**Consequence.** Operators reading `contradictions.detection_kind` see a
value the system never writes. Schema vocabulary inflates with no
semantics behind it.

**Proposed fix.** Either drop `temporal_overlap_disagreement` from the
spec text and leave the column open-ended for Phase 4 extension, or
specify the rule that fires it (e.g., "two same-value beliefs whose
intervals overlap by > X% are flagged at this kind for the review
queue"). The simpler fix is the drop.

### P2-13. Single-claim trigger rejection sinks the whole transaction

**Affected:** *Per-segment lifecycle* step 5 (lines 89–93), *Failure
diagnostics* (lines 612–629).

**Issue.** The lifecycle says "Insert 0..N `claims` rows in one
transaction with the `claim_extractions.status='extracted'` UPDATE." If
the trigger rejects 1 of N rows (e.g., one bad evidence_message_ids), the
entire transaction reverts. The extraction goes to `failed` with
`failure_kind='trigger_violation'` and ALL valid claims from that segment
are lost.

For a 60-message segment yielding 5 claims, one bad UUID in claim 4
discards the 4 good claims. The retry budget burns on the same prompt
that produced the bad UUID — the local LLM is unlikely to do better
without prompt help.

**Consequence.** Higher failure rate than necessary; lost good claims
that would otherwise contribute to beliefs.

**Proposed fix.** Two options for the build prompt:

- **(A)** Per-claim transactions inside one extraction: insert each claim
  in its own subtransaction; failed inserts go into
  `claim_extractions.raw_payload.attempt_errors` but successful claims
  commit. The extraction is `extracted` with `claim_count = success_count`
  and a non-empty `failure_diagnostics` block listing the dropped claims.
- **(B)** Pre-validate the model's response in Python (against the same
  rules the trigger enforces) and drop bad claims before the SQL insert.

(B) is simpler and aligns with the existing schema-level enum constraint
on `evidence_message_ids` (the trigger is defense-in-depth; the schema
already prevents most misses). The spec should pick one.

### P3-14. `belief_audit.evidence_episode_ids` retains the D010-era name and confuses the audit table

**Affected:** `belief_audit` schema (line 574), *Pre-existing Phase 3
worktree files* note in the marker (item 7).

**Issue.** The column is named `evidence_episode_ids` for historical
compatibility with D010 / Stash terminology, but stores raw `messages.id`
values (line 574 documents this). Engram's schema has no `episodes` table.
Operators reading the audit table without the spec at hand will not know
what `evidence_episode_ids` references; they'll likely assume it points
to a missing table.

The marker explicitly flags this for review (item 7) and notes the
rename is cheap before any rows exist.

**Consequence.** Long-term confusion. Forensic queries against the audit
table will use the wrong mental model.

**Proposed fix.** Rename to `evidence_message_ids` for parity with
`claims.evidence_message_ids`. Update the spec, migration filename, and
test #19/#20/#21 expectations. This is a one-line change in the spec.

### P3-15. `stability_class = MODE` aggregator is dead code

**Affected:** *Decision rules* §1 (lines 357–366), *Predicate vocabulary*
(line 232–235: each predicate is pinned to one `stability_class`).

**Issue.** Line 232–235: "The predicate-to-stability-class mapping is a
lint check the extractor schema enforces in V1 (each predicate has exactly
one allowed `stability_class`)." Therefore for any group key
`(subject_normalized, predicate)`, every contributing claim has the same
`stability_class`. MODE is a no-op; the tie-breaker on highest-confidence
is unreachable.

**Consequence.** Dead code in the consolidator, plus the impression that
the consolidator does sophisticated stability-class arbitration. It does
not.

**Proposed fix.** Replace MODE with "the predicate's pinned
stability_class (lookup, not aggregation)." If the spec author wants to
preserve the MODE-with-tie-breaker rule for future predicates that might
be polysemous, add a comment that V1's predicate→class mapping makes the
rule degenerate.

### P3-16. `claim_extractions` UPDATE has no audit chain

**Affected:** `claim_extractions` schema (lines 449–476), *Privacy-tier
propagation* (lines 296–316).

**Issue.** The reclassification flow flips `claim_extractions.status` from
`extracted` to `superseded` (line 304–305). `claim_extractions` UPDATEs are
permitted on a fixed column set (line 474–475). But beliefs require a
matching `belief_audit` row in the same transaction (line 549); claims
require nothing equivalent. There is no audit chain on
`claim_extractions` transitions.

**Consequence.** When an operator asks "why was this extraction marked
superseded?", the answer is in `consolidation_progress` or
`captures.capture_type='reclassification'` joined back through segments —
two hops away. Compare with the in-table audit on beliefs.

**Proposed fix.** Either (a) document this as deliberate ("rationale
lives in the captures+consolidation_progress chain, not in
claim_extractions"), or (b) add a `superseded_reason TEXT` and
`superseded_by_capture_id UUID NULL` to `claim_extractions` for
inline rationale. (a) is fine if it's documented; (b) is more
operator-friendly. The spec is silent on which.

### P3-17. `superseded_by` not set on contradiction supersession; chain traversal uses two paths

**Affected:** *Decision rules* §3 (lines 376–385), `beliefs.superseded_by`
column (line 529).

**Issue.** Same-value supersession (rule §2) sets `superseded_by` on the
prior row. Contradiction supersession (rule §3) does not — it inserts a
new candidate, closes the prior, and writes a `contradictions` row. The
prior's `superseded_by` is left NULL.

This is a defensible design choice (contradiction is a *new chain*, not
the same chain getting refreshed), but it means a reader traversing
`superseded_by` to answer "what came before this belief?" misses
contradictions. The full chain requires a UNION of `superseded_by` and
`contradictions.belief_a_id / belief_b_id`.

**Consequence.** Mostly fine for semantic reasoning, but Phase 4
`current_beliefs` view and Phase 5 retrieval need to traverse both. The
spec should be explicit.

**Proposed fix.** Document the two traversal paths (close-and-insert
chain via `superseded_by`; contradiction lineage via `contradictions`)
in the spec under *Belief consolidation* and add a test (gap #5 below)
for both paths.

### P3-18. `claims.subject_normalized` is absent — operators querying claims must re-implement the normalize rule in SQL

**Affected:** `claims` schema (lines 477–512), `beliefs.subject_normalized`
(line 521).

**Issue.** Beliefs carry `subject_normalized`; claims do not. To answer
"how many claims are in flight for the same subject as belief B?", an
operator must re-implement `normalize` in their query.

**Consequence.** Convenience drag, not a correctness issue. But because
the consolidator is the only enforcement point for normalize-rule
fidelity, claim-level audit queries can produce mismatches with
consolidator output.

**Proposed fix.** Mirror `subject_normalized TEXT NOT NULL GENERATED
ALWAYS AS (...)` (or trigger-computed) onto `claims`. Costs ~20 bytes per
row and gives operators the join-friendly column they'd otherwise have to
compute on read. Trivial schema addition.

## Open questions for the owner

1. **Bitemporal `valid_from` semantics.** Should V1 `beliefs.valid_from`
   carry biographic time (lifted from `object_json` `since`/`when` fields
   when present) or remain pure discovery time? If the latter, please
   acknowledge in the spec that V1 does not yet honor the
   HUMAN_REQUIREMENTS biographic-interval contract on `valid_from`.

2. **Confidence aggregator** (P2-8). MAX vs. MEAN vs. weighted MEAN. RFC
   0011 OQ6 was deferred-to-default; given the false-precision contract,
   is MAX really the V1 you want?

3. **`lives_at` shape lock-in** (P2-9). Make it JSON-only to remove the
   only dual-shape predicate, or keep it dual-shape and accept the
   guaranteed duplication?

4. **Per-claim vs. per-extraction transactions** (P2-13). Drop bad claims
   and keep good ones, or all-or-nothing?

5. **Predicate disambiguation guide** (P2-10). Drop overlapping predicates
   (`talked_about`, `experiencing`) and ship a per-predicate emission
   rule, or accept emission noise as a tolerable V1 cost?

6. **`engram consolidate --rebuild` semantics** (P1-6). Loosen test #23
   to "structurally equivalent active set" or implement a no-op
   short-circuit?

7. **Predicate-to-stability-class enforcement.** The spec says it's
   prompt-side, not DB CHECK. With D046 locking the enum, why not pin a
   small lookup table or a CHECK constraint with the 30-row mapping? The
   build prompt would have an easier integration test path.

## Test or acceptance-criteria gaps

The spec's 26 acceptance tests cover the schema-level invariants well.
The gaps below correspond to the findings above and should be added
before the build prompt accepts.

1. **Re-extraction blast radius** (P0-2). Add a test:
   - Given an active segment with two claim_extractions vintages
     (`v1` and `v2`) at `status='extracted'`, both with a same-key
     claim that disagrees on value, the consolidator's pass produces
     a single belief grounded in the v2 claim only and emits no
     `contradictions` row.

2. **Partial reclassification recompute** (P1-5). Three sub-tests:
   - Surviving set yields same value → close-and-insert (transition_kind
     = 'supersede').
   - Surviving set yields different value → close-and-insert plus
     `contradictions` row at `detection_kind=
     'reclassification_recompute'`.
   - Surviving set is empty → reject (transition_kind = 'reject').

3. **Concurrent consolidator passes** (P1-4). Test:
   - Two consolidator passes targeting different conversations but
     producing claims for the same `(subject_normalized, predicate)`
     race. Result: exactly one active belief; the loser's pass either
     supersedes or attaches to the existing belief.

4. **Contradiction interval math after supersession** (P0-1). Test:
   - Belief B1 (value X, valid_from=T1). New evidence at T2 > T1
     with value Y. After consolidator pass: B1.valid_to = T2 (NOT
     now()), B2.valid_from = T2, B2.valid_to = NULL. Auto-resolution
     rule fires (intervals are non-overlapping), `contradictions.
     resolution_status='auto_resolved'`,
     `resolution_kind='temporal_ordering'`.

5. **Both supersession traversal paths** (P3-17). Test:
   - `superseded_by` reaches the same-value chain.
   - `contradictions.belief_{a,b}_id` reaches the contradiction lineage.
   - The two together cover every closed-then-replaced belief.

6. **Subject_normalized correctness across SQL and Python** (P1-3). Test:
   - Insert a row via SQL with deliberate variation
     (`"My Dog Pip "`); the stored `subject_normalized` matches
     `engram.consolidator.normalize_subject("My Dog Pip ")` in
     Python.

7. **Rebuild idempotency** (P1-6). Test depends on the chosen
   resolution; whichever path the spec picks, add the corresponding
   acceptance test.

## Places where the spec contradicts RFC 0011 or should intentionally supersede it

- **RFC 0011 OQ5 (auto-resolution heuristics)** — RFC says "temporal-only
  in V1; everything else stays open." Spec ships the rule. But the
  close-rule (`valid_to = now()`) makes the auto-resolve branch dead in
  practice. Spec should either supersede RFC 0011 OQ5 with an explicit
  "auto-resolve is reachable iff the close rule uses
  `MIN(messages.created_at)` over the new evidence" or restate the rule
  to make it firable. (See P0-1.)

- **RFC 0011 OQ7 (`observed_at` derivation)** — RFC asked
  "max / median / first?". Spec picks max with rationale that auto-
  resolution needs ordering. The rationale only holds if auto-resolution
  is reachable, which P0-1 breaks. If the close rule is fixed to use
  `MIN(messages.created_at)`, the auto-resolution rule operates on
  `valid_from` / `valid_to`, not `observed_at`, and OQ7's choice
  becomes about historical-record fidelity rather than supersession
  correctness. Spec should re-justify the MAX choice once the close
  rule is fixed. RFC 0011's median option may then look more defensible.

- **RFC 0011 OQ8 (consolidator parallelism)** — RFC said "per-conversation
  pipeline so retrieval-visible beliefs grow incrementally." Spec
  implements but doesn't address concurrency safety on the
  cross-conversation `(subject_normalized, predicate)` group key. The
  unique-index fix in P1-4 lets the spec keep the RFC's per-conversation
  parallelism without losing correctness.

- **RFC 0011 #1 (Strengthen D003 to non-empty `evidence_ids` always)** —
  Spec implements correctly via `CHECK (cardinality(evidence_ids) > 0)`.
  No conflict.

- **RFC 0011 #4 (predicate vocabulary is fixed enum committed in
  extractor schema)** — Spec implements (line 232–235). Pure prompt-side
  enforcement is a defensible V1 trade-off but loses the DB safety net.
  Owner should weigh against RFC 0011's principle that the schema
  constrain output before generation; today the response schema does
  it (via JSON Schema enum) but the database does not.

## Closing note for synthesis (P024)

The spec is close enough to ship that the build prompt could land with
findings P0-1, P0-2, P1-3, and P1-4 amended and the rest folded into a
single follow-up clean-up pass. The two P0 issues are not edge cases —
they touch the central bitemporal write path and the central re-derivation
property. They should be the first two items the synthesis resolves.

Marker file: `docs/reviews/phase3/markers/02_SPEC_REVIEW_claude_opus_4_7.ready.md`.
