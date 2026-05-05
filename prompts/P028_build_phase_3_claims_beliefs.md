# P028: Build Phase 3 Claims and Beliefs

> Prompt ordinal: P028. Introduced: pending first commit. Source commit:
> pending.

## Role

Preferred model: Codex GPT-5.5.

You are the Phase 3 implementation agent. Your job is to implement the
accepted claims/beliefs spec in a fresh execution context, using the existing
Phase 1/2 code patterns and preserving Engram's local-only, raw-immutable,
non-destructive derivation rules.

## Guard

Do not execute this prompt until:

```text
docs/reviews/phase3/markers/07_BUILD_PROMPT_SYNTHESIS.ready.md
```

exists.

Before writing, run:

```bash
git status --short
```

The Phase 3 branch may already contain in-flight files from an earlier draft.
Do not overwrite unrelated work. If `src/engram/extractor.py`,
`src/engram/consolidator.py`, `migrations/006_claims_beliefs.sql`, or
`tests/test_phase3_claims_beliefs.py` already exist, treat them as scaffolding
that must be brought into alignment with the amended spec, not as authority.

## Read First

Read these before editing:

1. `docs/reviews/phase3/markers/07_BUILD_PROMPT_SYNTHESIS.ready.md`
2. `docs/reviews/phase3/PHASE_3_BUILD_PROMPT_SYNTHESIS_2026_05_05.md`
3. `docs/claims_beliefs.md`
4. `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md`
5. `DECISION_LOG.md`
6. `BUILD_PHASES.md`
7. `ROADMAP.md`
8. `SPEC.md`
9. `docs/schema/README.md`
10. `src/engram/segmenter.py`
11. `src/engram/embedder.py`
12. `src/engram/progress.py`
13. `src/engram/cli.py`
14. `migrations/004_segments_embeddings.sql`
15. `tests/`

Treat `docs/claims_beliefs.md` as the binding implementation contract. Where
`PHASE_3_BUILD_PROMPT_SYNTHESIS_2026_05_05.md` or this prompt explicitly
clarifies an ambiguous execution detail, follow the synthesis / prompt. Older
RFCs and earlier Phase 3 code are context only.

## Scope

Implement Phase 3 only:

- Stage A claim extraction over active Phase 2 AI-conversation segments.
- Stage B deterministic Python belief consolidation.
- Phase 3 schema and migration.
- CLI and Makefile operator entry points for extraction/consolidation.
- Resumability and failure diagnostics through `consolidation_progress`.
- Tests that pin the schema, extractor, consolidator, resumability, and CLI
  behavior in `docs/claims_beliefs.md`.
- Regenerated schema docs.

Source rows are exactly:

```sql
segments
WHERE is_active = true
  AND source_kind IN ('chatgpt', 'claude', 'gemini')
  AND conversation_id IS NOT NULL
```

joined to the active `segment_generations` row. Notes, captures, Obsidian, and
other source kinds stay out of Phase 3 extraction.

## Non-Goals

- Do not run the full Phase 3 corpus.
- Do not start the production Phase 3 pipeline. Implementation may run tests
  and synthetic/test-database checks only.
- Do not author the gold set.
- Do not implement Phase 4 entity canonicalization, `current_beliefs`, or HITL
  review queue.
- Do not implement Phase 5 belief embeddings, `context_for`, MCP serving,
  ranking, snapshots, or feedback.
- Do not add hosted services, cloud APIs, telemetry, external persistence, or
  any outbound network path from a corpus-reading process.
- Do not add LLM-mediated belief consolidation. Consolidation is deterministic
  Python in V1.
- Do not make new architecture decisions silently. If the spec is
  under-specified in a way that affects schema or derivation semantics, stop
  and report the gap.

## Likely Files

Expect to touch:

- `migrations/006_claims_beliefs.sql`
- `src/engram/extractor.py`
- `src/engram/consolidator/__init__.py`
- `src/engram/consolidator/transitions.py`
- possibly additional `src/engram/consolidator/*.py` helpers
- `src/engram/cli.py`
- `src/engram/progress.py` only if the existing helper is insufficient
- `Makefile`
- `tests/conftest.py`
- `tests/test_phase3_claims_beliefs.py`
- related Phase 2 test helpers if they need small shared fixtures
- `docs/schema/README.md` via `make schema-docs` only

The spec names `engram.consolidator.transitions`. If the current tree has a
flat `src/engram/consolidator.py`, convert it to a package or otherwise make
that import path real while re-exporting the public API used by `cli.py` and
tests. Do not leave a fake transition API that tests only the happy path.

## Migration Naming

Use `migrations/006_claims_beliefs.sql` for Phase 3 in this worktree. The
current prior migration is `005_source_kind_gemini.sql`; `004` is
segmentation/embeddings.

If the branch changes and `006` is no longer the next available slot, stop and
report the conflict instead of renumbering unrelated migrations. Do not rewrite
generated schema docs by hand.

Phase 3 migration verification must run against a fresh Phase 2 database state.
The migration runner records applied migrations by filename only, so a default
local DB that already applied a draft `006_claims_beliefs.sql` is not valid for
verification or schema-doc generation. Before `make schema-docs`, check whether
`schema_migrations` already contains `006_claims_beliefs.sql`; if it does in
the default DB, use a scratch DB restored through migrations 001-005 or stop
and report the blocker. Do not edit `schema_migrations` in a live local corpus
DB as part of this prompt. Phase 3 migrations are forward-only; do not add
rollback / down-migration behavior.

## Schema Requirements

Implement the schema in `docs/claims_beliefs.md` exactly, including:

- `predicate_vocabulary` seeded from the V1 table in the spec. It must include
  stability class, cardinality class, object kind, group-object keys, required
  object keys, and descriptions. `experiencing` is not in V1. `lives_at` is
  JSON-only. `talked_about` is an event predicate.
- `claim_extractions` with statuses `extracting`, `extracted`, `failed`,
  `superseded`, active unique index on `(segment_id,
  extraction_prompt_version, extraction_model_version)` where status is
  `extracting` or `extracted`, completed `raw_payload.model_response` for
  success/empty/failure, and `raw_payload.dropped_claims` for salvage.
- `claims` insert-only, with `subject_normalized`, FK to
  `predicate_vocabulary`, evidence subset trigger against
  `segments.message_ids`, predicate/object/stability validation trigger,
  non-empty `subject_text`, non-empty `evidence_message_ids`, and exactly one
  of `object_text` or `object_json`. `raw_payload` records the per-claim
  `rationale` text from the extractor response.
- SQL function `engram_normalize_subject(text)` matching the spec's NFKC,
  lowercase, trim, whitespace-collapse, trailing-punctuation-strip behavior.
  Python normalization must match it; test parity.
- `beliefs` with `subject_normalized`, `cardinality_class`,
  `group_object_key`, `closed_at`, non-empty `evidence_ids` and `claim_ids`,
  non-empty `subject_text`, predicate-derived `stability_class`, mean
  confidence, and the UNIQUE partial active-belief index on
  `(subject_normalized, predicate, group_object_key)` where `valid_to IS NULL`
  and status is `candidate`, `provisional`, or `accepted`.
- A belief mutation trigger that rejects DELETE and rejects INSERT/UPDATE unless
  the transaction-scoped GUC `engram.transition_in_progress` is set. UPDATE may
  change only `valid_to`, `closed_at`, `superseded_by`, and/or `status`.
- `belief_audit` append-only, with `evidence_message_ids` (not
  `evidence_episode_ids`), `request_uuid`, and the full transition-kind CHECK:
  `insert`, `close`, `supersede`, `promote`, `demote`, `reject`,
  `reactivate`.
- `contradictions` with only `same_subject_predicate` and
  `reclassification_recompute` detection kinds in V1, and UPDATE limited to
  resolution fields. Enforce `belief_a_id <> belief_b_id`.

For `single_current` predicates, `group_object_key` is always the empty string
`''`. For object-text predicates whose vocabulary row uses `text` as the
group-object key, compute `group_object_key` from normalized `object_text`. For
JSON predicates, join the configured key values with the unit separator
described in the spec, with missing keys serialized as empty strings.

## Extractor Requirements

Build Stage A around the existing Phase 2 local structured-call style:

- endpoint defaults to `ENGRAM_IK_LLAMA_BASE_URL=http://127.0.0.1:8081`;
- enforce local-only URLs using the existing `ensure_local_base_url` pattern;
- model id defaults to `ENGRAM_EXTRACTOR_MODEL`, then
  `ENGRAM_SEGMENTER_MODEL`, then the existing ik-llama model probe;
- exact prompt version:
  `extractor.v1.d046.universal-vocab`;
- exact request profile version:
  `ik-llama-json-schema.d034.v2.extractor-8192`;
- `stream=false`, `temperature=0`, `top_p=1`, `max_tokens=8192`,
  `chat_template_kwargs.enable_thinking=false`,
  `response_format={"type":"json_schema", ...}`;
- parse only `choices[0].message.content`;
- reject reasoning-only, empty, Markdown-fenced, non-JSON, and
  schema-invalid responses;
- apply the D037 context guard before sending requests;
- render tool-role/null-content messages as compact placeholders while
  preserving their `message_id` as citeable evidence.

The extractor prompt/schema must use the final V1 predicate vocabulary from
`docs/claims_beliefs.md`, not the earlier draft list (`lives_in`, `works_at`,
`knows`, etc.).

The request-profile version string above is the extractor profile identity:
it covers `max_tokens=8192`, D034 deterministic settings, strict per-segment
structured output, and the relaxed evidence-UUID fallback policy. Future
changes to any of those semantics must bump the string.

Implement per-claim salvage:

- validate every parsed claim in Python against trigger-equivalent checks;
- drop invalid claims into `claim_extractions.raw_payload.dropped_claims`;
- commit surviving claims;
- set `status='extracted'` if at least one valid claim survives, even if some
  claims were dropped;
- set `status='failed'` only when zero claims survive and errors occurred;
- represent empty extraction as `status='extracted'`, `claim_count=0`, zero
  `claims`, and populated `raw_payload.model_response`.

Old extracted rows remain active while a replacement row is `extracting`.
Supersede the old extracted row only in the same transaction that commits a
successful replacement at `status='extracted'`, including a successful empty
extraction with `claim_count=0`. Do not supersede the old row when the new row
becomes `failed`.

Implement the S-F013 relaxed-schema fallback, but keep build-time execution
bounded. The production path should retry a segment with the relaxed schema
only after the strict per-segment enum schema fails with a grammar-state /
schema-construction error for that segment. `engram extract --segment-id UUID`
must not scan the corpus tail first. Unit tests use fake clients and synthetic
tail fixtures; this prompt does not authorize a real tail-corpus preflight.

## Consolidator Requirements

Build Stage B as deterministic Python. Use exact version strings:

```text
CONSOLIDATOR_PROMPT_VERSION = consolidator.v1.d048-d058.transition-api
CONSOLIDATOR_MODEL_VERSION = consolidator.v1.d048-d058.transition-api
```

Implement the active claim set from D049:

- claim segment is the current active generation;
- claim extraction is the latest `claim_extractions` row at
  `status='extracted'` for that segment;
- older `claim_extractions` rows transition to `superseded` only when a newer
  prompt/model extraction successfully commits at `status='extracted'` for the
  same segment;
- older `claims` remain insert-only but do not feed consolidation.

Implement Decision Rule 0 before other rules: reject active beliefs whose
`claim_ids` are no longer fully present in the active claim set because of
re-extraction, segment deactivation, or reclassification.

Implement Rule 1/2/3 exactly:

- New group key inserts a `candidate` belief.
- Same-value reinforcement closes and inserts a fresh belief with merged
  provenance; the prior `valid_to` is not changed; lifecycle uses
  `closed_at`, `status='superseded'`, and `superseded_by`.
- Different value for `single_current` or same scoped object under
  `single_current_per_object` closes the prior with `valid_to =
  MIN(messages.created_at)` over the new evidence subset, inserts a new
  candidate, and inserts a contradiction. Contradiction lineage is through
  `contradictions.belief_a_id` / `belief_b_id`; do not set
  `superseded_by` for contradiction replacement unless the spec synthesis has
  explicitly changed that rule.
- `multi_current` and `event` predicates do not contradict across different
  `group_object_key` values.
- Auto-resolve only temporal-ordering contradictions with non-overlapping
  fact-validity intervals. Reclassification recompute contradictions stay
  open.

Implement the D054 privacy-reclassification recompute hook, not only its tests.
Add or extend a named invalidation helper so segment invalidation removes old
claims from the active claim set without mutating `claims` rows. The helper
must transition `claim_extractions` for invalidated segments to `superseded`,
queue fresh extraction after a new active segment generation exists, and run
before `engram extract`, before `engram consolidate`, and inside
`engram pipeline-3`. The consolidator then applies:

- empty surviving set -> reject with
  `score_breakdown.cause='orphan_after_reclassification'`;
- same-value surviving set -> same-value supersession;
- different-value surviving set -> close-and-insert plus a contradiction at
  `detection_kind='reclassification_recompute'` that stays open.

When reclassification is driven by a capture row, record the capture id in
`score_breakdown.cause_capture_id`.

All belief state changes must go through `engram.consolidator.transitions`:

- `insert_belief(...)`
- `supersede_belief(prior_id, new_belief_payload)`
- `close_belief(prior_id, reason)`
- `reject_belief(prior_id, cause)`

Each transition opens a transaction, sets
`SET LOCAL engram.transition_in_progress=<request_uuid>`, performs the belief
INSERT/UPDATE plus the matching `belief_audit` INSERT, and commits atomically.
The GUC must be transaction-scoped and gone after commit/rollback. Direct SQL
INSERT/UPDATE on `beliefs` without the GUC must fail.

Because the active-belief UNIQUE partial index is not deferrable, physical SQL
ordering matters:

- same-value supersession first updates the prior row out of the active
  partial-index set (`status='superseded'`, `closed_at=now()`, `valid_to`
  unchanged), then inserts the replacement candidate, then sets
  `superseded_by` on the prior row to the replacement id under the same
  request UUID;
- contradiction replacement first closes the prior row with the D048
  `valid_to` value and `status='superseded'`, then inserts the new candidate,
  then inserts the contradiction edge; do not set `superseded_by` for
  contradiction replacement;
- rebuild close first closes the active row with `transition_kind='close'`,
  `previous_status='candidate'`, and `new_status='superseded'`, then the
  rebuild inserts fresh candidate rows.

The audit row may describe one logical transition even when the transition API
uses more than one physical UPDATE under the same request UUID to satisfy the
unique index.

`consolidate --rebuild` closes the current active belief set through the
transition API and reruns consolidation over the full active claim set. Its
idempotency contract is structural equivalence of the active set, not stable
row ids.

## Resumability and Failure Behavior

Reuse `consolidation_progress`; do not add a parallel progress table.

Extractor:

- per-conversation scope:
  `stage='extractor'`, `scope='conversation:<uuid>'`;
- position includes `conversation_id`, `segment_id`, and segment index within
  the conversation;
- stale `claim_extractions.status='extracting'` rows older than
  `ENGRAM_EXTRACTOR_INFLIGHT_TIMEOUT_SECONDS` default `900` are reaped by
  UPDATE, never DELETE: set `status='failed'`, `completed_at=now()`, and
  `raw_payload.failure_kind='inflight_timeout'`, preserving D035 diagnostics.
  Reaping does not increment `consolidation_progress.error_count`; the next
  failed retry attempt does;
- `ENGRAM_EXTRACTOR_MAX_ERROR_COUNT` default `3` freezes a parent until
  manually requeued;
- service-unavailable, parse, schema, context-guard, retry-exhausted, and
  trigger-violation diagnostics follow D035 in `raw_payload`.

Consolidator:

- per-conversation default; run after a conversation's extractor stage
  finishes;
- a failed extraction on one segment does not block consolidation of the rest
  of that conversation;
- progress scope:
  `stage='consolidator'`, `scope='conversation:<uuid>'`;
- position includes `conversation_id` and `last_claim_extracted_at`;
- unique active-belief conflicts are caught, the active belief is re-read, and
  the decision rules retry.

## CLI and Operator Commands

Lock these command names:

```bash
engram extract --batch-size 10 --limit 100
engram extract --segment-id UUID
engram extract --requeue --conversation-id UUID
engram consolidate --batch-size 10
engram consolidate --conversation-id UUID
engram consolidate --rebuild
engram pipeline-3 --extract-batch-size 10 --consolidate-batch-size 10 --limit 50
```

Add Makefile targets:

```bash
make extract
make extract-docker
make consolidate
make consolidate-docker
make pipeline-3
make pipeline-3-docker
```

Keep existing Phase 1/2 targets working. Do not make `make pipeline` or
`engram pipeline` unexpectedly start a full Phase 3 production run unless the
build-prompt synthesis explicitly instructs that behavior. `pipeline-3` is the
explicit Phase 3 operator entry.

Progress output should mirror Phase 2: terse per-parent/per-segment lines with
elapsed seconds and final counts. Commands must support bounded `--limit` runs
for operator pilots, but this prompt does not authorize running a real corpus
pilot.

`engram extract --limit N` caps selected segments. `engram pipeline-3 --limit N`
caps conversations processed end-to-end. `engram extract --requeue
--conversation-id UUID` mirrors Phase 2's requeue style for Phase 3 state:
transition any in-flight extraction rows for that conversation to
`status='failed'` with `raw_payload.failure_kind='manual_requeue'`, reset the
extractor progress row's `error_count` and `last_error`, then retry that
conversation through the normal bounded extraction path. Failed extraction rows
are not deleted.

Audit the current scaffolding explicitly: `engram pipeline` and `make pipeline`
must remain Phase 1/2 behavior and must not invoke the extractor or
consolidator. All Phase 3 production behavior belongs behind `pipeline-3`.
`engram pipeline-3` must warn when active beliefs already exist for a different
consolidator `prompt_version`.

## Schema Docs Rule

After the migration is implemented and applied locally, regenerate schema docs
with:

```bash
make schema-docs
```

Never edit `docs/schema/README.md` by hand. If no fresh Phase 2 database is
available to run migration verification and schema-doc generation, report that
explicitly in the completion marker and final response. The completion marker
must say which database state produced schema docs.

## Test Plan

Use fake extractor clients and synthetic DB fixtures for LLM behavior. Do not
call a real local LLM from unit tests.

Implement or update tests to cover every Phase 3 implementation acceptance item
in `docs/claims_beliefs.md`, with special attention to:

- migration applies from the Phase 2 schema;
- migration verification uses a fresh Phase 2 DB and does not rely on a default
  DB that already recorded draft `006_claims_beliefs.sql`;
- insert-only `claims`;
- `claim_extractions` mutation restrictions and supersession behavior;
- claim evidence subset trigger and empty-evidence rejection;
- object shape, non-empty subject, and predicate-vocabulary validation;
- exact predicate-vocabulary seed parity with the V1 table in
  `docs/claims_beliefs.md`, including exclusion of old draft predicates, and
  extractor JSON-schema predicate enum parity with that same source;
- `claims.raw_payload.rationale` preservation and claim derivation columns
  exactly matching the parent `claim_extractions`
  `(extraction_prompt_version, extraction_model_version,
  request_profile_version)`;
- `beliefs` mutation guard rejects direct INSERT/UPDATE without transaction
  GUC and allows the transition API path with matching `request_uuid`; assert
  the GUC does not leak after the transition returns;
- `belief_audit` append-only behavior, renamed `evidence_message_ids`, and the
  full seven-value `transition_kind` CHECK;
- contradiction update restrictions and self-reference CHECK;
- extractor D034 request shape and parse rejections;
- empty extraction, raw payload preservation, context guard, retry diagnostics,
  hallucinated evidence ids, relaxed-schema fallback with synthetic tail
  fixtures, per-claim salvage, and claim-count parity;
- old extracted rows remain active while replacement extraction is in-flight,
  and failed replacement extraction does not supersede them;
- first belief insert and audit score breakdown;
- same-value supersession preserving `valid_to` and succeeding with the UNIQUE
  partial active-belief index present;
- contradiction close math using `MIN(new_evidence.created_at)`;
- temporal auto-resolution;
- re-extraction active-claim-set blast radius;
- Decision Rule 0 orphan rejection with
  `score_breakdown.cause` equal to one of
  `orphan_after_reclassification`, `orphan_after_reextraction`, or
  `orphan_after_segment_deactivation`;
- scoped-current/multi-current/event non-conflict behavior;
- privacy reclassification invalidation hook plus recompute's three branches,
  including `score_breakdown.cause_capture_id` for capture-driven
  reclassification;
- concurrent consolidator conflict retry using a deterministic two-connection
  recipe; do not use sleep-based thread timing;
- SQL/Python subject normalization parity;
- lineage traversal through both `superseded_by` and `contradictions`;
- rebuild structural equivalence and rebuild close audit fields
  (`transition_kind='close'`, `previous_status='candidate'`,
  `new_status='superseded'`);
- stale `extracting` reaping updates to `failed/inflight_timeout`, performs no
  DELETE, does not increment `error_count`, and permits retry;
- CLI regression that `pipeline` does not invoke Phase 3, while `pipeline-3`
  does.

Spec tests #25 and #26 are operator pilot gates, not unit tests for this build
prompt. Represent their invariants with synthetic tests, but do not run the
50-conversation pilot here.

Run:

```bash
make test
```

If the local test database is unavailable, run:

```bash
make test-docker
```

If neither can run, report the blocker and do not mark the build complete as
fully verified.

## Acceptance Criteria

The build is complete when:

- `make test` or `make test-docker` passes.
- The Phase 3 migration applies cleanly from a Phase 2 database state.
- `make schema-docs` has regenerated `docs/schema/README.md`.
- Phase 3 implementation acceptance tests from `docs/claims_beliefs.md` are
  represented in the test suite; operator pilot gates #25/#26 are not run.
- Existing Phase 1/2 tests still pass.
- No Phase 3 full-corpus extraction/consolidation was started.
- No hosted service, external persistence, telemetry, or non-local LLM endpoint
  was introduced.
- Public operator commands exist and print useful progress.
- `git status --short` shows only intentional Phase 3 implementation,
  tests, generated schema docs, and marker changes.

## Required Completion Marker

After implementation and verification, write:

```text
docs/reviews/phase3/markers/08_BUILD_COMPLETE.ready.md
```

The marker must include:

- prompt ordinal and title;
- model / agent name;
- started and completed timestamp;
- files written or modified;
- tests and commands run;
- whether schema docs were regenerated;
- which database state was used for migration verification and schema-doc
  generation;
- explicit statement that the full corpus was not run;
- any residual blockers or skipped verification;
- next expected marker:
  `docs/reviews/phase3/markers/09_BUILD_REVIEW_<model_slug>.ready.md`.
