# Phase 3 Build Prompt Review — Claude Opus 4.7

Date: 2026-05-05
Reviewer model: claude_opus_4_7 (fresh context for this review pass)
Prompt under review: `prompts/P028_build_phase_3_claims_beliefs.md`
Spec under reference: `docs/claims_beliefs.md` (build-ready after P024 synthesis)

## Verdict

`accept_with_findings`. The build prompt is faithful to the amended spec on
the load-bearing pieces (transition API + GUC, predicate vocabulary table,
cardinality classes / group key, Decision Rule 0, D048 close math, D058
salvage, structural-equivalence rebuild, partial unique active-belief index,
local-only LLM, no full-corpus run). It is detailed enough that a fresh
implementer should not silently pick a different architecture on the
contested decisions. The findings below are gaps and ambiguities, not
architectural rewrites.

Recommend P027 build-prompt-synthesis fold in F1, F2, F4, F5, F8, F9, F10,
F12, F14, and F16 before promoting to `07_BUILD_PROMPT_SYNTHESIS.ready.md`.
The rest can ride as documentation deltas or be left to the implementer.

## Findings

### F1 (P0) — Build prompt sets `request_profile_version` but the spec keeps it open

The build prompt locks the exact string

```text
ik-llama-json-schema.d034.v2.extractor-8192
```

(P028 *Extractor Requirements*).

The spec says (`docs/claims_beliefs.md` §"Extractor request profile"):

> `request_profile_version = ik-llama-json-schema.d034.v2` (same as Phase 2
> unless the extractor's `max_tokens` or other knobs diverge, in which case
> the version string changes).

`max_tokens` does diverge from Phase 2 (Phase 2 used a smaller cap; the
extractor pins 8192 explicitly), so the spec's conditional fires and a new
suffix is required. **But the suffix `.extractor-8192` is a build-prompt
choice, not a spec choice.** It is also slightly misleading: 8192 is the
extractor's `max_tokens` value, but the request profile encodes more than
just that — it implicitly includes the per-segment-enum schema and the
relaxed-fallback variant from S-F013.

Why it matters: this version string lands in `claims`, `claim_extractions`,
and `belief_audit`. It is forensically load-bearing. A future re-extraction
needs to be able to distinguish "I changed the schema fallback rule" from
"I changed max_tokens" by reading this string.

Recommended fix in P027:

- accept the build prompt's choice but document that the suffix is the
  extractor profile identity (max_tokens + structured-output fallback
  policy), not just `max_tokens`; or
- pick a more durable suffix like `extractor.v1` so a future schema-only
  bump can change `extractor.v1` → `extractor.v2` without lying about
  `max_tokens`.

Either is fine. The build prompt as written commits to a string the spec
did not commit to.

### F2 (P0) — GUC scoping is permissive

The build prompt says (P028 *Consolidator Requirements*):

> Each transition opens a transaction, sets
> `engram.transition_in_progress=<request_uuid>`, performs the belief
> INSERT/UPDATE plus the matching `belief_audit` INSERT, and commits
> atomically. Clear or scope the GUC so it cannot leak outside the
> transition. Direct SQL UPDATE on `beliefs` without the GUC must fail.

"Clear or scope" is too permissive. `SET engram.transition_in_progress
= '...'` is session-scoped: it survives commit and rollback and outlives
the transition. The trigger then accepts any subsequent UPDATE on that
session, including one from completely unrelated code paths or a manual
psql session that forgot to `RESET`. That defeats D052.

The spec (`docs/claims_beliefs.md` §"Belief transition API") says:

> Each function opens a transaction, sets a session GUC
> `engram.transition_in_progress = '<request_uuid>'`, runs the belief
> INSERT/UPDATE plus the matching `belief_audit` INSERT, and commits.

Spec is also imprecise here, but the obviously safe-by-construction form
is `SET LOCAL engram.transition_in_progress = '...'`, which dies on
COMMIT/ROLLBACK without operator action. The build prompt should require
`SET LOCAL` (or an equivalent transaction-scoped wrapper) and require a
test that demonstrates the GUC is **gone** after the transition function
returns.

Without this lock, the trigger can be bypassed accidentally without any
test detecting it.

### F3 (P0) — Direct SQL INSERT on `beliefs` is not gated by the GUC

The build prompt says the trigger blocks DELETE and rejects UPDATE without
the GUC, allowing UPDATE only on the four lifecycle columns (P028 *Schema
Requirements*).

It is silent on INSERT. Re-reading the spec (`docs/claims_beliefs.md`
§"`beliefs`" → Mutation trigger):

> Mutation trigger blocks DELETE outright. Allows UPDATE only on
> `valid_to`, `closed_at`, `superseded_by`, `status` — and only when
> the session GUC `engram.transition_in_progress` is set (D052). Every
> UPDATE is paired with a `belief_audit` INSERT carrying the same
> request UUID; the transition API guarantees the pair commits
> atomically.

So a direct SQL INSERT into `beliefs` (bypassing the API) is permitted by
the trigger and writes no `belief_audit` row. The audit-on-write
invariant therefore depends on code discipline at the API layer, not on
the trigger. The build prompt inherits this without flagging it.

Possible mitigations:

- gate INSERT with the same GUC requirement (and add the corresponding
  `belief_audit` INSERT inside the transition API), or
- accept the gap as documented and add a single explicit test asserting
  that INSERT-without-API + INSERT-without-GUC succeeds at the trigger
  level, so future maintainers see the boundary.

Either way, the build prompt should make the choice explicit. As written,
the implementer might either over-tighten (gate INSERT with GUC and break
tests) or under-tighten (no enforcement, no test, audit pairing silently
lossy through an SQL hole).

### F4 (P1) — Hidden architecture decision: `pipeline-3 --limit`

Build prompt locks (P028 *CLI and Operator Commands*):

```bash
engram pipeline-3 --extract-batch-size 10 --consolidate-batch-size 10 --limit 50
```

Spec (`docs/claims_beliefs.md` §"CLI / operator expectations") shows:

```bash
engram pipeline-3 --extract-batch-size 10 --consolidate-batch-size 10
                                                  # full Phase 3 pipeline,
                                                  # per-conversation
```

The `--limit 50` flag is a build-prompt-introduced argument that the spec
neither requires nor describes. Whether `--limit` counts conversations,
segments, or claims is unspecified. Pilots and operator dry-runs will
need this, but the semantics matter — `--limit 50 --extract-batch-size
10` could mean "50 segments split into 5 batches" or "50 conversations".

Recommend: P027 either drops the `--limit 50` example (lock only the
spec-locked subset and note `--limit` is an implementation choice the
implementer must define and test), or pins its semantics: "`--limit`
caps conversations processed end-to-end".

### F5 (P1) — Missing: `engram pipeline-3` non-destructiveness warning

Spec (`docs/claims_beliefs.md` §"CLI / operator expectations"):

> The CLI documents that `engram pipeline-3` is **non-destructive** by
> default and emits warnings if active beliefs already exist for a
> different consolidator `prompt_version`.

The build prompt does not include this requirement. Implementer reading
P028 in a fresh context will not invent the warning unprompted.

This is the closest thing in V1 to a "you might be about to mix beliefs
across consolidator versions" guard, and it is the visible operator
signal that re-derivation is happening. Worth adding to P027.

### F6 (P1) — `engram extract --requeue --conversation-id UUID` semantics underspecified

Spec says it "reset error_count and retry the parent." Build prompt
locks the command name but does not specify:

- whether stale `claim_extractions.status='extracting'` rows for that
  parent are first transitioned to `failed` (a write) or just reaped;
- whether `failed` extractions are re-queued, or only `extracting`
  extractions older than `ENGRAM_EXTRACTOR_INFLIGHT_TIMEOUT_SECONDS`;
- whether the requeue increments `consolidation_progress.error_count` or
  resets it;
- whether the requeue runs synchronously or just clears state.

The Phase 2 segmenter has analogous semantics. The build prompt should
either pin this explicitly or instruct the implementer to mirror Phase
2's `--requeue` behavior column-for-column.

### F7 (P1) — "Tail-segment grammar preflight" wording is muddled

The build prompt says (P028 *Extractor Requirements*):

> Add the top-1-percent tail-segment grammar preflight from the spec.
> If the strict per-segment enum schema fails on the largest segments by
> `message_ids` cardinality, fall back only for those over-cap segments
> to a relaxed schema that keeps the predicate enum and relies on UUID
> pattern plus the DB trigger backstop for evidence ids.

"Preflight" implies pre-check; "if … fails" implies reactive fallback.
The spec test #34 says:

> The largest 1% of active segments by `message_ids` cardinality
> complete extraction or fall back to a relaxed schema (predicate enum
> + UUID-pattern evidence ids + trigger backstop) without grammar-state
> errors.

That is also reactive. There is no spec language that defines a
percentile threshold computed up front. Recommend the build prompt drop
the word "preflight" and say "reactive fallback to a relaxed schema for
segments where the strict per-segment enum fails with a grammar-state
error", and pin which `failure_kind` the relaxed-schema retry attempts
recover from. Otherwise an implementer will spend time computing the
top-1% cardinality cohort before any LLM call.

### F8 (P1) — Subject-text non-empty CHECK is not pinned in the schema requirements list

Build prompt's *Schema Requirements* section enumerates several CHECKs
(predicate FK, evidence subset trigger, exactly-one-of object, non-empty
`evidence_message_ids`) but does not call out that `claims.subject_text`
must be non-empty.

Spec (`docs/claims_beliefs.md` §"Extractor structured-output schema"):

> `subject_text` to a non-empty string

The spec does not require a CHECK constraint, only a JSON-schema
constraint, but the spec table for `claims` defines `subject_text TEXT
NOT NULL`. An empty string still satisfies that. The implementer may or
may not add a `CHECK (length(trim(subject_text)) > 0)`. If `claims` accept
empty subjects, the consolidator's normalization will produce an empty
`subject_normalized`, which then cannot be distinguished from missing
data downstream.

Recommend P027 explicitly pin: `CHECK (length(trim(subject_text)) > 0)`
on `claims` (and the same on `beliefs`), with a unit test.

### F9 (P1) — `score_breakdown.cause_capture_id` and `cause` strings are not pinned

Spec (`docs/claims_beliefs.md` §"Privacy reclassification" and §"Decision
rules"):

> `belief_audit` writes `transition_kind = 'reject'` with the
> reclassification capture id in `score_breakdown.cause_capture_id`.

> `score_breakdown.cause = 'orphan_after_reclassification' |
> 'orphan_after_reextraction' | 'orphan_after_segment_deactivation'`.

Build prompt mentions Decision Rule 0 and the three-branch reclassification
recompute, but does not pin the `cause` enum values or the
`cause_capture_id` field name. A fresh implementer is likely to invent
slightly different keys (`cause_kind`, `reclassification_capture`, etc.),
which will silently break any later forensic query that joins on these
fields. Pin them in P027.

### F10 (P1) — `belief_audit.transition_kind` enum is not pinned in build prompt tests

Spec (`docs/claims_beliefs.md` §"`belief_audit`"):

> `transition_kind` … CHECK in `('insert','close','supersede','promote',
> 'demote','reject','reactivate')`

Phase 3 only writes `insert`, `close`, `supersede`, `reject`. The other
three are reserved for Phase 4. The build prompt does not require the
constraint to include the Phase 4 values, even though the spec does. An
implementer who reads only the build prompt may add a tighter CHECK that
lists only the four Phase 3 values; that will then break Phase 4
silently.

Recommend P027 pin the full 7-value CHECK constraint and add a test that
inserts each of the four allowed Phase 3 transitions but also asserts the
constraint accepts `promote` / `demote` / `reactivate` (or at least does
not reject them at the constraint level — there will be other guards in
Phase 4).

### F11 (P1) — Concurrency test (#30) is high flake risk without a recipe

Build prompt asks for "concurrent consolidator conflict retry" coverage
(P028 *Test Plan*). Spec test #30:

> Two consolidator invocations on different conversations, both producing
> a candidate for the same `(subject_normalized, predicate,
> group_object_key)`, converge to one active belief. The losing INSERT
> either retries cleanly into Rule 2 / Rule 3 or surfaces a recoverable
> conflict diagnostic.

Implementing this with real concurrency (threads / asyncio / two
connections) is doable but flaky in CI. The spec does not pin a
preferred recipe. The cheapest deterministic approach is:

1. open two psycopg connections,
2. start a transaction on conn A, INSERT the candidate, do **not** commit,
3. on conn B, set the GUC and INSERT the same candidate — expect the
   unique constraint violation,
4. commit conn A,
5. assert conn B's transition API caught the violation, re-read, and
   dispatched to Rule 2 / Rule 3.

The build prompt should either pin a recipe like the above or call out
that the test must be deterministic (no `time.sleep`, no thread joins).
Otherwise the implementer will write a flaky test, hit it once in CI, and
disable it.

### F12 (P1) — `--rebuild` does not pin `previous_status`/`new_status` semantics on the close

Spec (`docs/claims_beliefs.md` §"Re-derivation behavior"):

> Re-consolidation under a new consolidator `prompt_version` is a
> separate operator action. … Closures go through the transition API as
> `transition_kind='close'` with `previous_status='candidate'` and
> `new_status='superseded'`; new rows insert as `candidate`.

Build prompt says (P028 *Consolidator Requirements*):

> `consolidate --rebuild` closes the current active belief set through
> the transition API and reruns consolidation over the full active claim
> set. Its idempotency contract is structural equivalence of the active
> set, not stable row ids.

The build prompt does not pin that the `belief_audit` row for the close
must record `transition_kind='close'`, `previous_status='candidate'`,
`new_status='superseded'`. Test #23 in the spec also does not assert
this. Implementer may write `transition_kind='supersede'` or
`new_status='rejected'`. P027 should pin both fields, and the test should
assert them.

### F13 (P2) — `predicate_vocabulary` seed verification test missing

The spec V1 vocabulary table has 30 rows with specific stability classes,
cardinality classes, object kinds, and group-object keys. Build prompt
says (P028 *Schema Requirements*):

> `predicate_vocabulary` seeded from the V1 table in the spec. It must
> include stability class, cardinality class, object kind, group-object
> keys, required object keys, and descriptions. `experiencing` is not
> in V1. `lives_at` is JSON-only. `talked_about` is an event predicate.

That is correct but does not require a test that checks the seed against
the spec table row-for-row. Drift between the seed migration and the
spec is the most likely place a downstream behavior bug starts. Add a
test:

> `tests/test_phase3_claims_beliefs.py::test_predicate_vocabulary_seed_matches_spec`
> reads the 30-row table from the spec markdown (or a Python-side
> constant generated from it) and asserts each `(predicate,
> stability_class, cardinality_class, object_kind, group_object_keys,
> required_object_keys)` matches the seeded row.

### F14 (P2) — `(extraction_prompt_version, extraction_model_version, request_profile_version)` triple lock not asserted

Build prompt and spec both say `claims` and `claim_extractions` carry the
three derivation columns. Test plan covers extractor request shape and
schema parity, but does not assert that **every inserted `claims` row
must have the same three values as its parent `claim_extractions` row**.
A common implementation slip is taking `extraction_prompt_version` from
the runtime constant rather than the just-inserted parent row, which is
fine on the happy path but breaks on retries / requeues that raced
against a config change.

Recommend an explicit test: "claim's three derivation version columns
exactly match its parent extraction row" using a synthetic mismatch
fixture.

### F15 (P2) — Tests #25 / #26 (50-conversation pilot, idempotency) are out of scope but not flagged

Spec lists these as "End-to-end pilot (gate before full-corpus run)".
Build prompt's *Test Plan* does not enumerate them, and the *Non-Goals*
section says "Do not run the full Phase 3 corpus" and "Implementation
may run tests and synthetic/test-database checks only." Good — but the
build prompt's *Acceptance Criteria* says

> `docs/claims_beliefs.md` acceptance tests are represented in the test
> suite

which, read literally, includes #25 and #26. An anxious implementer may
spin up the pilot to satisfy this clause and accidentally start a 50-conv
extraction run.

Recommend P027 explicitly carve #25 and #26 out: "Tests #25 and #26 are
operator gates, not unit tests; this build prompt does not authorize
running them."

### F16 (P2) — Stale `extracting` row reaping behavior on `error_count`

Build prompt says (P028 *Resumability and Failure Behavior*):

> stale `claim_extractions.status='extracting'` rows older than
> `ENGRAM_EXTRACTOR_INFLIGHT_TIMEOUT_SECONDS` default `900` are reaped
> and re-queued on supervisor restart;
> `ENGRAM_EXTRACTOR_MAX_ERROR_COUNT` default `3` freezes a parent until
> manually requeued;

The relationship is undefined: does reaping a stale `extracting` row
count as one error and increment `consolidation_progress.error_count`?
Or does reaping silently re-queue?

If reaping increments, a wedged ik-llama (which the Phase 2 D035 soak
showed is a real shape) will burn through `MAX_ERROR_COUNT=3` quickly
and freeze parents the operator does not actually want frozen. If
reaping does not increment, a real ik-llama unhealth shape is invisible
in `consolidation_progress`.

Spec is silent. Build prompt should either pin the choice (probably:
reaping does **not** increment error_count, but the next failed attempt
on the requeued segment does), or instruct the implementer to mirror
Phase 2's segmenter behavior column-for-column and call out the spec
silence.

### F17 (P2) — `claims.raw_payload` NOT NULL but no default is locked

Spec (§"`claims`"): `raw_payload JSONB NOT NULL`, including `rationale`.
Build prompt does not pin this. If the implementer mirrors Phase 2's
`raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb`, every claim row will
need an explicit assignment that includes `rationale` (extractor-provided)
plus possibly the per-claim model rationale block. Spec tests #15 do
not assert `rationale` is preserved.

Lower priority but worth pinning in P027: "`claims.raw_payload` records
the per-claim `rationale` text from the extractor response (test
#15a)".

### F18 (P3) — `(belief_a_id <> belief_b_id)` self-reference CHECK on contradictions not pinned

Spec has it as an inline CHECK. Build prompt's schema requirements say:

> `contradictions` with only `same_subject_predicate` and
> `reclassification_recompute` detection kinds in V1, and UPDATE limited
> to resolution fields.

It does not pin the self-reference CHECK. Lower priority since the
consolidator will not generate a self-contradiction in any happy path,
but a fixture or a poorly-written test might. Add to P027.

### F19 (P3) — Migration reversibility not addressed

Phase 1/2 migrations are forward-only. Build prompt does not state the
migration must also be forward-only. Spec is silent. An implementer who
adds DOWN/rollback statements and then runs them locally during dev
could discard real schema. Lower priority; covered by raw immutability
being a Phase 1 invariant in practice.

### F20 (P3) — No defense against accidentally running corpus extraction during dev

Build prompt prohibits a corpus run, but the implemented CLI commands
(`engram extract --batch-size 10 --limit 100` etc.) are real and will
operate against whatever DB the implementer's environment points to. If
that DB is the production Phase 2-active corpus, a stray
`engram extract --limit 1` is the start of a Phase 3 pilot.

Defense-in-depth suggestion (not blocking): require an explicit env var
like `ENGRAM_PHASE3_CORPUS_RUN=1` for any non-test corpus operation,
defaulting to off. Implementation tests can set it; the implementer is
much less likely to set it accidentally. Spec does not require this; it
is purely a guard.

## What the build prompt got right

- D052 transition API and GUC are explicit, including the rejection-path
  test and the success-path test (#11/#12).
- D048 close math (`MIN(messages.created_at)` over new evidence; prior
  `valid_to` untouched on same-value supersession) is pinned in plain
  language.
- D049 active claim set selection rule is named, with the older row
  transitioning to `superseded` in the same transaction.
- Decision Rule 0 (orphan rejection) is called out separately from the
  three-branch reclassification recompute. Both surfaces are tested.
- D050 cardinality classes and group-object key construction are pinned,
  including the `lives_at`-JSON-only and `talked_about`-event amendments.
- D055 structural-equivalence rebuild contract is named explicitly.
- D053 partial UNIQUE active-belief index and the conflict-retry
  contract are present.
- D058 per-claim salvage is fully specified including the
  `claim_count`-counts-survivors rule and the `extracted` vs `failed`
  split.
- D057 predicate vocabulary table is required as the structural backstop
  with FK from `claims.predicate`.
- Local-only constraints, ik-llama-only request profile, no hosted
  services, `127.0.0.1` binding.
- Migration numbering pinned at `006_claims_beliefs.sql` with a stop-and-
  report rule if the slot conflicts.
- Existing in-flight scaffolding is correctly framed as "bring into
  alignment with the amended spec, not as authority."

## Privacy / local-first / full-corpus risk summary

- **Privacy:** clean. Build prompt repeats local-only requirements,
  inherits D020, requires `ensure_local_base_url`, prohibits new
  outbound paths.
- **Full-corpus risk:** moderate. Build prompt prohibits the run but
  ships fully-functional CLI commands an implementer could trigger.
  See F20.
- **Privacy reclassification recompute:** specified correctly across
  all three branches; the `cause` strings are not pinned (F9).
- **Tool-message placeholder rule (D038):** correctly inherited.
- **Raw immutability:** preserved; `claims` insert-only and `belief_audit`
  append-only are pinned.

## Missing implementation tasks (summary list)

- Pin GUC scoping as `SET LOCAL` and add a test that the GUC is gone
  after the transition (F2).
- Decide and document INSERT-on-`beliefs` policy (F3).
- Pin `pipeline-3 --limit` semantics or drop it (F4).
- Add the non-destructiveness warning in `pipeline-3` (F5).
- Pin `--requeue` semantics across stale and failed extractions (F6).
- Drop "preflight" wording from S-F013 fallback description (F7).
- Pin `subject_text` non-empty CHECK (F8).
- Pin `cause` enum + `cause_capture_id` field name (F9).
- Pin full 7-value `transition_kind` enum (F10).
- Pin a deterministic recipe for the concurrent consolidator test (F11).
- Pin `transition_kind='close'` audit fields on rebuild close (F12).
- Add a test that `predicate_vocabulary` seed matches the spec table
  (F13).
- Add a test that `claims` derivation version columns equal their
  parent extraction row's columns (F14).
- Carve out tests #25 / #26 as operator gates (F15).
- Pin reaping-vs-error-count interaction (F16).
- Pin `claims.raw_payload.rationale` preservation (F17).
- Pin `belief_a_id <> belief_b_id` CHECK (F18).
- Decide migration reversibility (F19).

## Suggested next-step marker

This review is the second of three. After Codex GPT-5.5 and Gemini Pro
3.1 reviews land, the ledger / synthesis loop produces:

```text
docs/reviews/phase3/markers/06_BUILD_PROMPT_REVIEW_claude_opus_4_7.ready.md
```

(this review's marker), then the synthesis pass produces the
implementation-ready P028:

```text
docs/reviews/phase3/markers/07_BUILD_PROMPT_SYNTHESIS.ready.md
```

The implementer of P028 should read this review along with the other
two reviews before opening any file.
