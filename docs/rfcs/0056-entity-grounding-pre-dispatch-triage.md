<a id="rfc-0056"></a>
# RFC 0056: Entity Grounding Pre-Dispatch Triage

| Field | Value |
|-------|-------|
| RFC | 0056 |
| Title | Entity Grounding Pre-Dispatch Triage |
| Status | proposal (revised after design review 2026-05-20) |
| Implementation | none |
| Date | 2026-05-20 |
| Context | RFC 0052; RFC 0053; RFC 0054; RFC 0055; `src/engram/entity_grounding_workflow.py`; `src/engram/extractor.py` (`IkLlamaExtractorClient`); HUMAN_REQUIREMENTS local-first principle |
| Review | `docs/reviews/rfc0056-pre-dispatch-triage-design-review/SYNTHESIS.md` (Codex GPT-5.5 + Gemini + local ik-llama, 2026-05-20). All accepted deltas folded into this document. |

Decision refs:
  - [D020](../../DECISION_LOG.md#d020)
  - [D094](../../DECISION_LOG.md#d094)
  - [D095](../../DECISION_LOG.md#d095)

## Summary

A bounded pass of the RFC 0054 batch workflow on the personal corpus (5 grants,
2026-05-20) produced a 0% resolution rate: every grant came back `ambiguous`.
Inspecting the surfaces shows three failure modes the batch worker cannot
detect from the entity row alone:

- **Ungroundable surfaces.** Personal artifacts (e.g. shopping lists,
  rough-draft titles) for which no public entity will ever match. Drafting
  and dispatching wastes operator review effort and provider quota.
- **Noise surfaces.** Segmentation/extraction debris that is meaningless
  without surrounding context.
- **Duplicate surfaces.** Phase 4 can produce multiple `unknown` entity rows
  for the same canonical text; today, each one drafts an independent grant.

This RFC proposes a two-tier pre-dispatch triage step that runs between
Phase 4 entity build and the RFC 0054 draft step. Tier 1 is a deterministic
rule-based pre-filter that catches structural cases without invoking the
LLM. Tier 2 is a local LLM classifier for cases the rules could not decide.
Only entities classified `groundable` reach the existing draft worker.

The triage step is local-only. It must not see the broker DSN, must not call
any network adapter, must not modify Phase 4 entities, and must not modify
RFC 0053 grant state. Its sole outputs are append-only
`entity_grounding_triage_actions` audit rows.

## Goals

- Cut the rate of ungroundable, noise, and duplicate surfaces reaching the
  draft queue without suppressing real groundable entities.
- Use only local claim/belief/evidence context as input.
- Reuse the pinned local LLM serving infrastructure already used by the
  extractor, on a **separate** backend port/model id so triage never
  contends with claim extraction.
- Produce deterministic, replayable triage actions with full version stamps.
- Carry privacy tier correctly from source claims through capsule, action,
  and any operator-facing rationale.
- Survive operator override across capsule churn.

## Non-Goals

- No network search.
- No grant approval.
- No query refinement (the RFC 0053 byte-exact `search_query == surface_form`
  invariant is unchanged).
- No Phase 4 entity mutation.
- No multi-step agentic loop.
- **No free-text rationale in LLM output.** The LLM returns a fixed
  `reason_code` enum only; rationale text, if ever surfaced, is built from
  the structured decision by the review layer.
- No alternative-model recommendations in this RFC. The default and only
  supported model is the pinned ik-llama backend specified below. Any other
  model is the subject of a separate compatibility spec.

## Boundary

The triage step runs entirely on the corpus-reading side of RFC 0053:

- Connects with the operator DSN (`ENGRAM_DATABASE_URL`).
- **Refuses to start if `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` is set
  in env.** The refusal must fire before DB connection and before any LLM
  client construction.
- Must not import `claim_grounding_network`, `claim_grounding_broker`, or
  any module under the network-adapter surface. A
  `tests/test_no_egress.py` import-graph assertion enforces this.
- The local LLM client must be constructed via the existing
  `ensure_local_base_url` guard; non-loopback hosts fail closed.
- **Loopback-only socket policy.** Tests must monkeypatch `socket.socket`
  and `socket.getaddrinfo` to refuse non-loopback addresses for the duration
  of the triage run.
- **Proxy env handling.** `http_proxy`, `https_proxy`, `all_proxy`, and
  their uppercase variants are unset before the LLM client is constructed.
  An explicit log line records the strip.
- **Broker DSN refusal precedence.** The env check happens first in the
  CLI entrypoint, before logging, before DB connection, before model client
  creation. A unit test asserts this ordering by mocking each downstream
  constructor to fail loudly.

The `no_egress` test surface for this RFC is a real binding gate, not a
smoke. See Acceptance Criteria for the exact test list.

## Local Model Backend

Default to the existing ik-llama serving pattern used by the extractor, on a
dedicated triage instance so the two workloads do not contend:

- OpenAI-compatible `/v1/chat/completions` with `response_format.type =
  "json_schema"` and `strict = True`.
- Default model id: the same model file used for extraction at the time of
  writing (`~/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf`). Model **digest**
  (SHA-256 of the GGUF file) is captured in every action row for replay.
- Configuration env vars:
  - `ENGRAM_TRIAGE_BASE_URL` — required; **must differ from
    `ENGRAM_IK_LLAMA_BASE_URL`** unless an explicit
    `ENGRAM_TRIAGE_ALLOW_SHARED_BACKEND=1` opt-in is set. The CLI refuses to
    start when the two URLs match without the opt-in.
  - `ENGRAM_TRIAGE_MODEL` — required; defaults to the pinned extractor
    model id.
  - `ENGRAM_TRIAGE_MAX_TOKENS` — defaults to 256 (the structured output is
    small enough to fit comfortably under that bound).
  - `ENGRAM_TRIAGE_TEMPERATURE` — defaults to 0.
  - `ENGRAM_TRIAGE_REQUEST_TIMEOUT_SECONDS` — defaults to 30.
  - `ENGRAM_TRIAGE_MAX_RETRIES` — defaults to 1.
  - `ENGRAM_TRIAGE_MAX_CONCURRENCY` — defaults to 1 (no concurrent LLM
    calls in the default profile).

Non-default models are explicitly out of scope. Any additional model must
pass a separate compatibility spec proving strict JSON Schema adherence,
refusal handling, and operator-labeled calibration before promotion.

## Workflow Integration and Rollout Stages

The triage step inserts cleanly between Phase 4 entity build and RFC 0054
draft:

```text
phase4 build-entities
    → entity-grounding triage   (this RFC)
        Stage 1: rule-based pre-filter (no LLM)
        Stage 2: LLM classifier (only for unresolved cases)
    → entity-grounding draft     (RFC 0054, gated on triage decision)
    → claim-grounding grants approve
    → entity-grounding broker-daemon
```

### Stage 1: Rule-Based Pre-Filter (no LLM call)

For each candidate entity, evaluate these checks in order. The first match
short-circuits, writes the action, and **does not invoke the LLM**:

1. **Already grounded.** Active `entity_identity_review_actions` row links
   the entity to local grounding evidence → `decision='groundable'`,
   `reason_code='already_grounded'`. (Idempotent skip downstream.)
2. **Already drafted or approved.** Active RFC 0053 grant exists for the
   entity surface in the same tenant/corpus →
   `decision='groundable'`, `reason_code='existing_grant'`.
3. **Canonical-key duplicate.** Another active entity exists with the same
   `(tenant_id, corpus_id, entity_kind, canonical_key)` → `decision='dedupe_of'`,
   `reason_code='canonical_key_duplicate'`, target = oldest active sibling.
4. **Length thresholds.** `len(canonical_text) < 3` or `> 200` →
   `decision='not_groundable'`, `reason_code='surface_length_out_of_range'`.
5. **Stop-list match.** Surface matches the operator-managed stop list
   (`src/engram/entity_grounding_triage_stoplist.txt`) → `decision='not_groundable'`,
   `reason_code='stoplist_match'`.
6. **Structural noise.** Surface is single-token-non-proper-noun (all
   lowercase, all digits, common stop-word) → `decision='not_groundable'`,
   `reason_code='segmentation_noise'`.

Entities that survive Stage 1 fall through to Stage 2.

### Stage 2: LLM Classifier (only for unresolved cases)

Build the local context capsule (next section), call the LLM, record the
action.

### Rollout Stages

Rollout is gated on operator-labeled eval results:

1. **Stage A (rules-only).** Default. Stage 1 enabled, Stage 2 disabled.
   `entity-grounding draft` consults rule actions and respects them.
2. **Stage B (LLM shadow).** Stage 2 enabled, but `entity-grounding draft`
   **ignores** Stage 2 actions for gating purposes. Stage 2 writes actions
   that operators inspect via the review UI but never block real drafts.
3. **Stage C (enforce).** `ENGRAM_TRIAGE_REQUIRED=1` flips, draft respects
   Stage 2 actions. Only allowed after eval thresholds are met (see
   Evaluation).

The default-on promotion to Stage C is the artifact this RFC's eval gate
guards.

## Local Context Capsule

For each candidate entity that reaches Stage 2, the triage worker assembles
a bounded local context capsule and submits it to the model. The capsule
must not include raw segment/message bodies.

Capsule components, each a deterministic ordered list:

- **Entity row fields:** `id`, `canonical_text`, `entity_kind`,
  `confidence`, `privacy_tier`, `created_at`.
- **Source claim summaries:** at most 6, **ordered by `claim_id` ascending**.
  Each item: `{predicate, subject_role, object_role, claim_id,
  claim_privacy_tier}`. Object text is omitted.
- **Sibling entity surfaces:** at most 6 other active entities sharing any
  source claim id, **ordered by entity `id` ascending**.
- **Existing local grounding evidence variants:** at most 6 rows for the
  same surface form, **ordered by evidence `id` ascending**. Only
  `canonical_label` and `source_label` columns are included; excerpts and
  source URLs are omitted.

Privacy-tier filtering rule:

> **The capsule must exclude any data derived from source claims whose
> `privacy_tier` exceeds the entity's `privacy_tier`.** This filter is
> applied before any tier-aware short-string allowance. Short
> public-tier object text is **not** included by default; if a future
> revision allows it, it must be denylist-checked against phone, address,
> credential, and personal-identifier patterns.

Effective capsule privacy tier:

> `capsule_privacy_tier = max(entity.privacy_tier,
> max(source_claim.privacy_tier for included claims),
> max(sibling_entity.privacy_tier for included siblings),
> max(evidence.privacy_tier for included evidence))`

This value is persisted on the action row.

Bounds:

- At most 6 source claim summaries, 6 sibling surfaces, 6 prior evidence
  rows.
- Total capsule size capped at 4 KiB after canonical JSON serialization
  (sorted keys, `separators=(",", ":")`).
- Tie-breaking for selection when a list exceeds 6 items: highest
  privacy-tier first, then most-recent `created_at`, then lowest UUID lex.

Capsule hash:

```
capsule_hash = sha256(canonical_json(capsule_contents)).hexdigest()
```

If the capsule cannot be assembled, the agent writes `decision='skip'`,
`reason_code='capsule_assembly_failed'`, and never calls the model.

## Decision Schema

The LLM is constrained by strict JSON schema. The schema is part of this
RFC, not deferred to implementation:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["schema_version", "decision", "reason_code", "confidence"],
  "properties": {
    "schema_version": { "const": "entity_grounding_triage.decision.v1" },
    "decision": {
      "type": "string",
      "enum": ["groundable", "not_groundable", "dedupe_of", "needs_review"]
    },
    "reason_code": {
      "type": "string",
      "enum": [
        "groundable_public_entity",
        "personal_artifact",
        "segmentation_noise",
        "too_broad_or_generic",
        "duplicate_surface",
        "model_insufficient_context",
        "model_refusal"
      ]
    },
    "dedupe_target_entity_id": {
      "oneOf": [{ "type": "string", "format": "uuid" }, { "type": "null" }]
    },
    "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
  },
  "allOf": [
    {
      "if": { "properties": { "decision": { "const": "dedupe_of" } } },
      "then": { "required": ["dedupe_target_entity_id"],
                "properties": { "dedupe_target_entity_id":
                  { "type": "string", "format": "uuid" } } }
    }
  ]
}
```

System-side decision precedence (evaluated before any LLM call;
short-circuit on first match):

1. `already_grounded` (Stage 1.1) → `groundable`
2. `existing_grant` (Stage 1.2) → `groundable`
3. `canonical_key_duplicate` (Stage 1.3) → `dedupe_of`
4. structural rejection (Stage 1.4–1.6) → `not_groundable`
5. LLM decision (Stage 2) — one of the four enum values
6. `agent_quoted_private_text` downgrade → `needs_review`
7. `agent_hallucinated_uuid` downgrade → `needs_review`

Hallucinated-UUID downgrade rule: if the model emits a
`dedupe_target_entity_id` that is **not** a member of the capsule's
sibling-entity id list, the application layer overrides the LLM decision to
`needs_review` with `reason_code='model_refusal'` (the precedence-7
downgrade is implementation-internal; the persisted reason_code stays in
the enum).

Dedupe target validity checks (applied at action insert and at draft
attribution):

- Same `(tenant_id, corpus_id)` as the candidate entity.
- Target status = `active`, `superseded_at IS NULL`.
- `dedupe_target_entity_id != candidate_entity_id` (no self-pointer).
- No cycle: walking the dedupe chain must not return to the candidate.
- **Latest non-superseded triage action on the target must have
  `decision = 'groundable'`.** Otherwise the candidate is downgraded to
  `needs_review` with `reason_code='duplicate_target_not_groundable'` (a
  follow-up enum extension if not already present).

## Schema (SQL)

```sql
CREATE TABLE entity_grounding_triage_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL DEFAULT 'personal',
    corpus_id TEXT NOT NULL DEFAULT 'personal',
    entity_id UUID NOT NULL REFERENCES entities(id),
    decision TEXT NOT NULL CHECK (decision IN
        ('groundable','not_groundable','dedupe_of','needs_review','skip')),
    reason_code TEXT NOT NULL,
    dedupe_target_entity_id UUID REFERENCES entities(id),
    confidence DOUBLE PRECISION NOT NULL
        CHECK (confidence >= 0 AND confidence <= 1),
    capsule_privacy_tier INTEGER NOT NULL,
    agent_version TEXT NOT NULL,
    model_id TEXT NOT NULL,
    model_digest TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    context_builder_version TEXT NOT NULL,
    generation_params JSONB NOT NULL,
    capsule_hash TEXT NOT NULL,
    actor TEXT,
    operator_rationale TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_at TIMESTAMPTZ,
    CHECK (
        decision <> 'dedupe_of'
        OR (dedupe_target_entity_id IS NOT NULL
            AND dedupe_target_entity_id <> entity_id)
    ),
    CHECK (
        agent_version <> 'operator'
        OR actor IS NOT NULL
    )
);

CREATE INDEX entity_grounding_triage_active_idx
    ON entity_grounding_triage_actions
    (tenant_id, corpus_id, entity_id, created_at DESC)
    WHERE superseded_at IS NULL;

CREATE UNIQUE INDEX entity_grounding_triage_active_unique_idx
    ON entity_grounding_triage_actions
    (tenant_id, corpus_id, entity_id, capsule_hash,
     model_id, prompt_version, schema_version)
    WHERE superseded_at IS NULL;
```

The table is mutation-guarded the same way `claim_audits` and
`entity_identity_review_actions` are: inserts only, plus a single
`superseded_at` stamp. A migration `025_entity_grounding_triage_actions.sql`
applies the table, indexes, and append-only trigger.

`operator_rationale` is tier-gated at read time by the review UI; it is
never round-tripped through an LLM and is only populated by operator
override (`--reason`/`--actor` path).

## Idempotency

Idempotency components:

```
key = (tenant_id, corpus_id, entity_id,
       capsule_hash, model_id, prompt_version, schema_version)
```

The partial unique index above enforces one active action per key. Two
concurrent triage runs hitting the same key produce a unique-violation on
the loser; the loser surfaces the existing action and does not call the
LLM.

The LLM is called only when:

1. No prior non-superseded action exists for the entity, AND
2. The candidate is not protected by an operator override (next subsection).

A rerun that produces the same key reuses the existing action without
calling the LLM.

### Invalidation Events

A new LLM call is required when any of these change:

- `model_id`
- `model_digest` (e.g. operator swapped the GGUF file but kept the path)
- `prompt_version`
- `schema_version`
- `context_builder_version`
- Source-claim membership for the entity
- Sibling-entity membership for the entity
- Evidence membership for the entity surface
- Privacy-tier promotion on any included row

Each invalidation event writes a new action row; the prior row's
`superseded_at` is stamped in the same transaction.

### Operator Override Survival

If the latest non-superseded action for an entity has
`agent_version = 'operator'`, the agent **skips** the LLM call and preserves
the operator's decision, regardless of `capsule_hash` drift. The only ways
to re-engage the agent for that entity are:

- `engram entity-grounding triage --entity-id UUID --ignore-overrides
  --decision ...` (records an operator-driven re-engagement, preserving
  audit trail of who reverted the override).
- A migration that drops `agent_version='operator'` rows (out of scope for
  routine runs; requires explicit operator review).

The agent never overrides an `agent_version='operator'` row by side effect.

## CLI

```text
engram entity-grounding triage --tenant personal --corpus personal --limit 50
engram entity-grounding triage --entity-id UUID
engram entity-grounding triage --dry-run
engram entity-grounding triage --dry-run --format jsonl
engram entity-grounding triage \
    --supersede --entity-id UUID \
    --decision {groundable,not_groundable,dedupe_of,needs_review} \
    --reason CODE \
    --actor halbritt@gmail.com \
    [--dedupe-target-entity-id UUID] \
    [--ignore-overrides]
engram entity-grounding triage --force-rerun --entity-id UUID
engram entity-grounding triage --batch-needs-review \
    --tenant personal --corpus personal \
    --decision {groundable,not_groundable} \
    --reason CODE --actor halbritt@gmail.com
```

Required flags for `--supersede`: `--decision`, `--reason`, `--actor`.
`--dedupe-target-entity-id` is required only when `--decision=dedupe_of`.

Output:

- Default mode prints sanitized aggregate JSON:
  `{actions_created, actions_reused, actions_superseded, decisions: {...},
   stage_1_short_circuit_count, stage_2_llm_call_count, workflow_version}`.
- `--dry-run --format jsonl` emits one record per entity:
  `{entity_id, decision, reason_code, confidence, capsule_hash, reused,
    elapsed_ms, capsule_privacy_tier}`. Never includes capsule contents.
  Never includes operator_rationale.

Concurrency:

- The CLI takes a per-`(tenant_id, corpus_id)` PostgreSQL advisory lock
  for the duration of the run (same pattern as the broker daemon).
- Operator `--supersede` inserts take a row-level lock on the candidate
  entity's active action; if a concurrent agent run lands first, the
  operator insert wins and the agent's row is stamped `superseded_at` in
  the same transaction.

## Evaluation

Pre-promotion eval gate (must pass before flipping
`ENGRAM_TRIAGE_REQUIRED=1`):

- **Labeled set:** 200–300 operator-labeled entities spanning every decision
  and reason_code value. Held out from any training/prompt-tuning data.
- **Per-class metrics:**
  - `recall(groundable) >= 0.95` — **false-suppression ceiling**, the
    primary gate.
  - `precision(not_groundable) >= 0.90` — confidence that suppressions
    are correct.
  - `precision(dedupe_of) >= 0.95` — duplicate target correctness.
  - `recall(needs_review) >= 0.80` — model self-doubt is calibrated.
- **Adversarial privacy cases:** at least 20 cases where source claims
  contain personally identifying text adjacent to public surfaces; verify
  the capsule filter and the rationale-paraphrase scanner.
- **Duplicate-target correctness:** for every `dedupe_of` decision in the
  labeled set, the dedupe target must itself be `groundable` (i.e. the
  dedupe chain terminates at a valid entity).
- **Confidence calibration:** decisions with `confidence >= 0.9` must
  agree with the operator label at least 95% of the time.
- **Runtime at scale:** measure wall-clock time at 300 and 1000 candidates
  on the local backend. Total time / candidate must remain under
  `ENGRAM_TRIAGE_REQUEST_TIMEOUT_SECONDS`.
- **No-egress test gate:** the full `tests/test_no_egress.py` suite must
  pass with triage invoked end-to-end. This is a gate, not a smoke check.

The eval set lives under `evals/entity_grounding_triage/` with a baseline
report committed before any promotion.

## Observability and Review UI

Operator surface for `needs_review` and override:

- **List view** filtered by `decision='needs_review'`. Columns: entity
  surface, privacy tier, source-claim count, sibling count, prior triage
  history, existing grants/evidence summary.
- **Per-entity detail panel:** source-claim ref list (no raw object text
  unless tier-gated and operator opted in), sibling entities with their
  surfaces and triage decisions, existing grants and evidence (read-only
  references), structured reason_code, operator_rationale if any, action
  history with timestamps.
- **Batch controls:** force-ground, force-not-ground, mark-dedupe-of
  (requires operator to pick the target entity from a candidate list).
  Each batch action records `actor` and a single `reason_code`.

CLI parity for the same actions is required (the `--batch-needs-review`
flag above). The review UI is operator-side, the same surface where Phase 4
review actions live.

Telemetry:

- Per-iteration counts and timings exposed via the JSONL dry-run output.
- No candidate text in any log line. No model output text in any log line.
- Errors include reason_code and entity_id, never capsule contents.

## Open Questions

1. **Pre-existing approved grants.** If triage decides `not_groundable` for
   an entity that already has an approved grant, the action records the
   contradiction and surfaces it in the review queue. The agent does **not**
   revoke the grant. Operator decides.
2. **Dedupe scope.** Restricted to the same `(tenant_id, corpus_id)`.
   Cross-corpus dedupe is explicitly out of scope.
3. **Two-phase dedupe consistency.** Stage 2 currently classifies entities
   independently; cross-batch dedupe chains (A → B → C) can record
   technically-invalid pointers. The Accept-#2 constraint (target must be
   `groundable`) prevents these from materializing into bad drafts, but the
   action rows can be inconsistent. A two-phase triage (classify, then
   resolve dedupe pointers with knowledge of all Phase 1 decisions) is
   deferred. If the first eval shows pointer invalidity above 5%, that
   triggers a follow-up RFC.
4. **Model re-triage on backend upgrade.** When the ik-llama model file
   changes (new digest), no automatic corpus-wide re-triage. Operators can
   `--force-rerun --entity-id` selectively, or the eval gate triggers a
   wider rerun when a promotion is being considered.

## Acceptance Criteria

This RFC is implemented when all of the following are true:

- Migration `025_entity_grounding_triage_actions.sql` applies the table,
  the active-row partial unique index, and the append-only trigger.
- `src/engram/entity_grounding_triage.py` exists with Stage 1 rule-based
  pre-filter and Stage 2 LLM classifier separable for independent test.
- The triage entrypoint refuses to start when
  `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` is set, **before** any DB
  or LLM client construction.
- `ENGRAM_TRIAGE_BASE_URL` enforcement: refuses to share with
  `ENGRAM_IK_LLAMA_BASE_URL` unless `ENGRAM_TRIAGE_ALLOW_SHARED_BACKEND=1`.
- `engram entity-grounding triage` CLI surface complete: `--dry-run`,
  `--dry-run --format jsonl`, `--limit`, `--entity-id`, `--supersede` with
  `--decision`/`--reason`/`--actor`/`--dedupe-target-entity-id`/
  `--ignore-overrides`, `--force-rerun`, `--batch-needs-review`.
- `engram entity-grounding draft` consults the latest non-superseded
  triage action and gates accordingly. Stage A (rules-only), Stage B
  (LLM shadow, draft ignores Stage 2), and Stage C (enforce) are each
  selectable by env var.
- `tests/test_entity_grounding_triage.py` covers:
  - Stage 1 rule short-circuits for every reason_code in Stage 1.
  - Stage 2 paths for each LLM decision and each downgrade.
  - Capsule determinism (same entity twice → same `capsule_hash`).
  - Privacy-tier filtering (high-tier source claim excluded from capsule).
  - Capsule max-tier inheritance on the action row.
  - Hallucinated-UUID downgrade.
  - Idempotency by partial unique index (concurrent insert produces one
    surviving active row).
  - Operator-override survival across capsule churn.
  - Dedupe target validity (active, same scope, non-self, no cycle,
    target-itself-groundable).
- `tests/test_no_egress.py` adds triage-entrypoint coverage:
  - Loopback-only socket policy enforced.
  - Import-graph assertion that `entity_grounding_triage` does not import
    `claim_grounding_network`, `claim_grounding_broker`, or any
    network-adapter module.
  - Broker DSN refusal fires before DB and LLM client construction
    (ordering test).
  - Proxy env vars stripped before client construction.
- A real JSON Schema fixture lives at
  `tests/fixtures/entity_grounding_triage_decision_v1.json` and is the
  source of truth for both the LLM request and the action insert
  validator. Tests assert: extra fields rejected; invalid enum rejected;
  bad UUID format rejected; overlong values rejected; `dedupe_of` without
  `dedupe_target_entity_id` rejected.
- CLI acceptance tests for manual override decision, reason, actor,
  dedupe target, `--force-rerun`, and redacted per-entity dry-run output.
- Review UI acceptance criteria for `needs_review` list, per-entity
  detail panel, batch controls, tier-aware rationale visibility.
- Eval suite under `evals/entity_grounding_triage/` with baseline report
  covering: per-class precision and recall thresholds, adversarial
  privacy cases, duplicate-target correctness, confidence calibration,
  runtime at 300/1000 candidates, no-egress gate.
- Stage A → B → C rollout is operator-controlled by env var; promotion
  to Stage C is gated on eval thresholds documented in this RFC.
