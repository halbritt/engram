# Phase 3 Build Prompt Review: Codex GPT-5.5

Date: 2026-05-05
Reviewer: codex_gpt5_5
Prompt reviewed: `prompts/P028_build_phase_3_claims_beliefs.md`
Verdict: revise before implementation

## Summary

The build prompt is broadly aligned with the amended Phase 3 spec and does a
good job pinning scope, local-only execution, Phase 3 non-goals, exact version
strings, and the final predicate vocabulary traps. I found no hosted-service,
telemetry, or external-persistence drift.

I would not hand this prompt to a fresh implementation context yet. There are
two correctness blockers and several run-risk ambiguities that are easy to
miss because the prompt says `docs/claims_beliefs.md` is binding while also
overriding a few details implicitly.

## Findings

### P0: Belief supersession order conflicts with the active-belief unique index

References:
- `prompts/P028_build_phase_3_claims_beliefs.md`, Consolidator Requirements
- `docs/claims_beliefs.md`, Decision rules and `beliefs` unique partial index

The spec's same-value Rule 2 says to insert the replacement belief, then set
the prior row to `status='superseded'` with `closed_at` and `superseded_by`.
The build prompt repeats the close-and-insert behavior but does not tell the
implementer how to order the SQL under the required UNIQUE partial index:

```text
(subject_normalized, predicate, group_object_key)
WHERE valid_to IS NULL AND status IN ('candidate','provisional','accepted')
```

A PostgreSQL partial unique index is not deferrable. If the prior active row is
still `candidate` with `valid_to IS NULL`, inserting the replacement active
row first will fail. This affects same-value supersession and any rebuild path
that closes and reinserts the same active group. Contradiction replacement has
the same ordering issue if the prior is not closed before the new candidate
insert.

Proposed prompt fix:

- Add an explicit transaction ordering note for the transition API.
- For same-value supersession: set the GUC, update the prior out of the active
  partial-index set first (`status='superseded'`, `closed_at=now()`, leave
  `valid_to` unchanged), insert the replacement, then set `superseded_by` on
  the prior once the new id exists. One audit transition may describe the
  logical supersession, but the prompt should say how this satisfies the
  "every UPDATE pairs with audit" rule.
- For contradiction replacement: close the prior first with the D048
  `valid_to` value, insert the new candidate, insert the contradiction edge,
  and do not set `superseded_by`.
- Add a test that same-value supersession succeeds with the UNIQUE partial
  index present.

### P0: Extraction supersession timing is contradictory and can erase the active claim set on failure

References:
- `docs/claims_beliefs.md`, Stage A lifecycle step 2
- `prompts/P028_build_phase_3_claims_beliefs.md`, active claim set from D049

`docs/claims_beliefs.md` says that when a new `claim_extractions` row is
inserted at `status='extracting'`, a prior row at a different extractor version
is transitioned to `status='superseded'` in the same transaction. The build
prompt later says older rows supersede when a newer extraction "completes".

The "supersede on extracting insert" version is unsafe. If the replacement LLM
call fails, the prior extracted claims are already out of the active claim set.
The next consolidator pass can then run Decision Rule 0 and reject beliefs even
though no successful replacement exists. This violates the non-destructive
re-extraction intent.

Proposed prompt/spec fix:

- Make the build prompt explicitly say old extracted rows remain active while
  a replacement row is `extracting`.
- Supersede the old extracted row only in the same transaction that commits a
  successful replacement at `status='extracted'`, including successful empty
  extraction with `claim_count=0`.
- Do not supersede the old row when the new row becomes `failed` because of
  service, parse, schema, context-guard, or zero-valid-claims salvage failure.
- Because the spec is currently contradictory, the synthesis should either
  patch `docs/claims_beliefs.md` or make the build prompt's override explicit
  enough that a fresh context will not follow lifecycle step 2 literally.

### P1: Existing `engram pipeline` scaffolding already starts Phase 3

References:
- `prompts/P028_build_phase_3_claims_beliefs.md`, CLI and Operator Commands
- current `src/engram/cli.py`
- current `Makefile`

The prompt says not to make `make pipeline` or `engram pipeline`
unexpectedly start a full Phase 3 production run, and says `pipeline-3` should
be the explicit Phase 3 operator entry. That is the right rule, but the current
worktree already has in-flight scaffolding where `engram pipeline` runs
segment, embed, extract, and consolidate, and `make pipeline` invokes that
command.

A builder following "bring scaffolding into alignment" might preserve this
behavior unless the prompt explicitly calls it out. That is a full-corpus run
risk because an existing Phase 2 operator command would silently expand into
Phase 3 extraction/consolidation.

Proposed prompt fix:

- Add an explicit task: audit and correct existing `pipeline` scaffolding so
  `engram pipeline` / `make pipeline` remain Phase 1/2 behavior unless the
  synthesis deliberately changes that contract.
- Put all Phase 3 extraction/consolidation behind `engram pipeline-3` and
  `make pipeline-3`.
- Add a CLI regression test that `pipeline` does not invoke extractor or
  consolidator, and `pipeline-3` does.

### P1: Phase 3 privacy reclassification invalidation lacks an implementation hook

References:
- `docs/claims_beliefs.md`, Privacy-tier propagation and D054 recompute tree
- `prompts/P028_build_phase_3_claims_beliefs.md`, Consolidator Requirements

The spec requires invalidated segments to make dependent `claim_extractions`
inactive, leave old `claims` insert-only, and drive the D054 recompute tree
over affected beliefs. The build prompt includes Decision Rule 0 and asks for
tests of the three D054 branches, but it does not name the implementation task
that connects Phase 2 invalidation to Phase 3 state.

The current Phase 2 code has `apply_reclassification_invalidations()` that
deactivates `segments` and `segment_embeddings`. A fresh builder needs to know
whether to extend that function, add a Phase 3 companion, or call a new
invalidation step before `extract`, `consolidate`, and `pipeline-3`.

Proposed prompt fix:

- Add an implementation task that transitions `claim_extractions` for
  invalidated segments to `superseded`, queues fresh extraction after the new
  active segment generation exists, and ensures the consolidator sees the
  invalidated claim difference.
- State where this runs: before `engram extract`, before `engram consolidate`,
  and inside `engram pipeline-3`, or via a named helper.
- Extend tests beyond the D054 branch outcomes to assert that segment
  invalidation actually removes old claims from the active claim set without
  mutating the `claims` rows.

### P1: Migration verification is unsafe if the draft `006` was already applied locally

References:
- `prompts/P028_build_phase_3_claims_beliefs.md`, Migration Naming and Schema
  Docs Rule
- current `migrations/006_claims_beliefs.sql` scaffold
- migration runner behavior in `src/engram/migrations.py`

The prompt correctly says to use `migrations/006_claims_beliefs.sql` and treat
the existing file as scaffolding. The migration runner records applied
migrations by filename only. If a local database has already applied the draft
`006_claims_beliefs.sql`, rewriting the file and running `make migrate` will
skip it. Then `make schema-docs` can document stale draft schema without
applying the amended migration.

Proposed prompt fix:

- Require migration verification against a fresh Phase 2 database state, not
  the developer's possibly advanced default DB.
- Before schema-doc generation, require checking whether
  `schema_migrations` already contains `006_claims_beliefs.sql`; if it does
  in the default DB, use a scratch DB restored through Phase 2 migrations or
  stop and report the blocker. Do not edit `schema_migrations` in a live local
  corpus DB as part of this prompt.
- Add this to the completion marker so reviewers know which database state
  produced `docs/schema/README.md`.

### P2: Tail-segment and health preflights need explicit execution bounds

References:
- `prompts/P028_build_phase_3_claims_beliefs.md`, Extractor Requirements and
  Test Plan
- `docs/claims_beliefs.md`, tests #13, #25, #26, and #34

The prompt says not to run a real corpus pilot, but it also asks for the
top-1-percent tail-segment grammar preflight and D035 health smoke behavior.
A fresh implementation context could reasonably wire these as automatic
real-corpus LLM calls before `engram extract --limit N`, causing a bounded
operator pilot to touch more of the active corpus than requested.

Proposed prompt fix:

- Clarify that this build prompt implements and unit-tests the preflight logic
  using fake clients and synthetic fixtures only.
- Specify that production preflight execution must be explicit or must obey
  the operator's bound. `engram extract --segment-id UUID` should not scan the
  corpus tail first.
- Clarify that the 50-conversation end-to-end pilot in the spec is represented
  by synthetic tests during implementation and is not run until a later
  operator prompt authorizes it.

### P2: Stale `extracting` reaping is underspecified

References:
- `prompts/P028_build_phase_3_claims_beliefs.md`, Resumability and Failure
  Behavior

The prompt says stale `claim_extractions.status='extracting'` rows older than
`ENGRAM_EXTRACTOR_INFLIGHT_TIMEOUT_SECONDS` are "reaped and re-queued" on
restart. Because `claim_extractions` is delete-protected and active uniqueness
depends on status, the exact transition matters.

Proposed prompt fix:

- Define reaping as an UPDATE from `extracting` to `failed` with
  `failure_kind='inflight_timeout'`, D035 diagnostics in `raw_payload`, and
  `completed_at=now()`, leaving the row for audit.
- Then a retry can insert a fresh `extracting` row for the same segment and
  version because the partial unique index excludes `failed`.
- Add a restart/reap test that proves no DELETE occurs and the retry is
  allowed.

### P2: Predicate vocabulary parity should be tested directly

References:
- `prompts/P028_build_phase_3_claims_beliefs.md`, Schema Requirements and Test
  Plan

The prompt warns not to use the older draft predicate list. Given the current
worktree has draft scaffolding using `lives_in`, `works_at`, `knows`, etc.,
the test plan should directly pin the final vocabulary and the extractor JSON
schema/table parity.

Proposed prompt fix:

- Add a test that `predicate_vocabulary` contains exactly the V1 rows from
  `docs/claims_beliefs.md` and excludes old draft predicates.
- Add a test that the extractor JSON schema predicate enum is generated from
  the same source as the seeded table, or at least is byte-for-byte equivalent
  to the table's predicate set.

## Non-Findings

- The prompt preserves the local-first/no-egress constraint at the prompt
  level: local endpoint defaults, local URL enforcement, no hosted APIs, no
  telemetry, and fake clients in tests.
- The prompt correctly scopes Phase 3 to AI-conversation segments and excludes
  notes, captures, Obsidian, Phase 4 review/entity work, and Phase 5 serving.
- The prompt correctly names generated schema docs as generated output and
  forbids hand editing.

## Suggested Synthesis Priority

Address the P0 items before implementation starts. The P1/P2 items can be
folded into the build prompt as explicit implementation notes and tests; they
do not require new architecture decisions if the synthesis keeps the existing
spec intent.
