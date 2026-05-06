# Claims and Bitemporal Beliefs

Status: spec build-ready after P024 synthesis (2026-05-05). Promoted from
RFC 0011 + D043–D047, amended per
[PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md](reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md)
which folded in D048–D058.

This document is the implementation contract for Phase 3. It pins the schema,
the extractor and consolidator request shapes, the predicate vocabulary, the
deterministic decision rules, and the failure / resumability semantics that the
build prompt (P025) will hand to the implementer. It does not implement code.

Canonical references:

- [RFC 0011](rfcs/0011-phase-3-claims-beliefs.md)
- [DECISION_LOG.md](../DECISION_LOG.md) — D002, D003, D004, D008, D010, D019,
  D020, D021, D028, D032, D034, D035, D040, D043, D044, D045, D046, D047,
  D048, D049, D050, D051, D052, D053, D054, D055, D056, D057, D058, D064
- [BUILD_PHASES.md](../BUILD_PHASES.md) Phase 3 row
- [docs/segmentation.md](segmentation.md) — Phase 2 contract Phase 3 inherits
- [docs/reviews/v1/PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04.md](reviews/v1/PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04.md)
- [docs/reviews/v1/PHASE_2_QWEN27B_UMBRELLA_AB_2026_05_05.md](reviews/v1/PHASE_2_QWEN27B_UMBRELLA_AB_2026_05_05.md)

## Scope

Phase 3 is the first synthesis stage. It consumes the active Phase 2
AI-conversation segment generations and produces:

1. `claims` — one row per atomic LLM-extracted assertion bound to one segment,
   with raw-message-level evidence and a stability class. Insert-only.
2. `beliefs` — bitemporal, status-tracked rows consolidated from claims by a
   deterministic Python consolidator. Allow only the named state-transition
   updates; never overwrite value, evidence, or audit columns.
3. `belief_audit` — append-only log of every belief state transition.
4. `contradictions` — open / auto-resolved / human-resolved / irreconcilable
   conflicts surfaced by the consolidator.
5. `claim_extractions` — per-segment extraction-state row analogous to
   `segment_generations`, with D035 failure diagnostics.

### Non-goals (explicitly deferred)

- Entity canonicalization, `entities`, `entity_edges`, `entity_id` joins on
  claims/beliefs (Phase 4).
- `current_beliefs` materialized view (Phase 4).
- Belief review queue, accept / promote-to-pinned UX, correction-as-capture
  flow at the surface level (Phase 4 / D006 / D017).
- Auto-promotion of beliefs to `status='accepted'` (D044 — Phase 4 HITL only).
- Belief text embedding into the vector index (Phase 5 / D009).
- `context_for`, ranking, MCP, `context_feedback` (Phase 5).
- LLM-mediated belief consolidation. V1 consolidator is deterministic Python.
- Adversarial / falsification sweeps (F004 deferred).
- Hypotheses, failure-pattern detection, causal-link mining, goal-progress
  inference (D014 / F009 deferred).
- Note / capture / Obsidian extraction (D040 / D047 — future phase prompt).

## Inputs

- Source rows: `segments` WHERE `is_active = true` AND
  `source_kind IN ('chatgpt','claude','gemini')` AND `conversation_id IS NOT
  NULL`, joined to their `segment_generations` row (also active). Notes,
  captures, and Obsidian segments are excluded from this phase even though the
  schema reserves room for them.
- Per-segment payload: `content_text`, `summary_text`, ordered `message_ids`,
  `privacy_tier`, parent `conversation_id`, `segmenter_prompt_version`,
  `segmenter_model_version`.
- Per-message context for the prompt: each message's `role`, `content_text`,
  and a pre-assigned slot UUID drawn from `messages.id`. Tool-role messages
  inside a segment span are passed as compact placeholders (see *Extractor
  prompt construction* below); raw bodies stay on disk per D038.

The Phase 2 audit (PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04) certifies
provenance integrity for these segments: 0 cross-conversation, 0 missing,
0 unordered active rows. The known imprecision is the umbrella-overlap pattern
on ~45 ChatGPT parents (76 overlapping pairs across 0.57% of the corpus). This
spec does not gate on a targeted re-segmentation of those parents; the owner
accepted weak per-claim grounding on those segments as a tolerable Phase 3
input. Phase 3 evaluation will quantify any cost.

## Stage A — Claim extraction

### Per-segment lifecycle

1. The supervisor picks an active segment with no active `claim_extractions`
   row at the current `(extraction_prompt_version, extraction_model_version)`.
2. INSERT a `claim_extractions` row at `status='extracting'`. If a prior row
   exists at a different `(extraction_prompt_version,
   extraction_model_version)` for the same segment, transition that prior
   row to `status='superseded'` in the same transaction (D049).
3. Build the prompt; call the local LLM with the deterministic D034 request
   profile.
4. Parse only `choices[0].message.content`. Validate it against the response
   JSON schema (predicate enum, message-id enum, stability_class enum,
   confidence range, exactly-one-of object).
5. **Pre-validate in Python (D058).** Walk the parsed claim list; check each
   claim against the trigger-equivalent rules (predicate is in
   `predicate_vocabulary`, predicate ↔ stability class match,
   evidence_message_ids ⊆ segment.message_ids, object_json required keys per
   the predicate's vocabulary entry). Drop invalid claims with structured
   diagnostics into `raw_payload.dropped_claims[]`. Surviving claims proceed
   to insert.
6. Insert 0..N `claims` rows in one transaction with the
   `claim_extractions.status='extracted'` UPDATE; copy `privacy_tier` from the
   parent segment to each claim. `claim_count` records the number of
   inserted (post-salvage) claims, not the model's pre-validation count.
7. On any failure (HTTP, parse, schema, validation, context guard, retry
   budget exhausted) where **zero** claims survived salvage, set
   `claim_extractions.status='failed'` and persist D035 diagnostics in
   `raw_payload`, except for D064's accounted-zero terminal state: fully
   parsed, schema-valid outputs that remain all-invalid after validation
   repair are `status='extracted'`, `claim_count=0`, and
   `raw_payload.extraction_result_kind='accounted_zero'` only when every prior
   and final drop is locally diagnosed, redacted, and counted. If at least one
   claim survived, the extraction is `status='extracted'` even when one or
   more claims were dropped; the diagnostics for the dropped claims live
   alongside the success record in `raw_payload.dropped_claims`.

Empty extraction is an explicit, recorded result: `status='extracted'` with
`claim_count = 0`. Clean empty extraction has
`raw_payload.extraction_result_kind='clean_zero'`; accounted empty extraction
has `raw_payload.extraction_result_kind='accounted_zero'`. Empty extraction is
**not** a failure; clean zero means the segment held no assertions the prompt
was willing to commit to, while accounted zero means invalid drafts were
redacted and counted under D064. Per S-F012 / M-F001, the raw model output is
preserved on
`claim_extractions.raw_payload.model_response` for **every** completed
extraction (success, empty, or failed) so recall debugging can inspect what
the model produced.

### Extractor prompt construction

- Single universal prompt for V1 (per O001's "one universal" choice). A
  per-stability-class split is not made until evidence justifies it.
- The prompt receives:
  - The segment `summary_text` (when present) and the ordered list of
    constituent messages, each shown as `{role, message_id, content_text}`.
  - Tool-role messages and null-content messages are rendered as compact
    placeholders (e.g., `[tool message <uuid> omitted]`) — the same shape
    Phase 2 used (D038). Their `message_id` remains an enum value the model
    may cite as evidence.
- The prompt commits the model to:
  - emit a list of zero or more atomic assertions about the subject (the
    user / "I") or about entities the user is describing,
  - choose `predicate` from the enum below,
  - choose `stability_class` from the seven D008 values,
  - cite at least one `evidence_message_ids` drawn from the segment's
    `message_ids`,
  - emit either `object_text` or `object_json` per the rules below.

### Extractor request profile

Inherits Phase 2 D034:

```json
{
  "stream": false,
  "temperature": 0,
  "top_p": 1,
  "max_tokens": 8192,
  "chat_template_kwargs": {"enable_thinking": false},
  "response_format": {"type": "json_schema"}
}
```

Runtime version defaults (illustrative; the build prompt locks the exact
strings):

- `extraction_prompt_version = extractor.v1.d046.universal-vocab`
- `extraction_model_version` = the pinned ik-llama model id of the running
  segmenter / extractor (Phase 3 reuses Phase 2's model).
- `request_profile_version = ik-llama-json-schema.d034.v2` (same as Phase 2
  unless the extractor's `max_tokens` or other knobs diverge, in which case
  the version string changes).

Adaptive shrink is not required: the Phase 2 audit found stored `message_ids`
p99 = 62 messages, well within the bounded `max_tokens` budget. If a segment
exceeds budget, the extractor fails closed with a context-budget error rather
than inventing per-segment chunking. Per-segment chunking is a follow-up if
evidence requires it.

The D037 grammar / context-shift guard from segmentation applies: estimated
prompt tokens + `max_tokens` + safety margin must not reach context shift.

### Extractor structured-output schema

The schema is the contract the local LLM is bound to. It must constrain:

- `predicate` to the V1 enum (see *Predicate vocabulary*),
- `stability_class` to the seven D008 values,
- `evidence_message_ids.items` to an enum over the actual segment
  `message_ids` (D036 echo — prevents hallucinated UUIDs before they reach
  the trigger),
- `confidence` to `[0, 1]`,
- exactly one of `object_text` (string) or `object_json` (object) is present
  per claim,
- `subject_text` to a non-empty string (no enum — Phase 4 entity
  canonicalization handles canonicalization later),
- `object_text` (when present) to a non-empty string,
- `object_json` (when present) to an object whose keys are enumerated by
  the predicate (see *object_text vs object_json* below).

Top-level shape:

```json
{
  "claims": [
    {
      "subject_text": "string",
      "predicate": "lives_at",
      "object_text": "string OR null",
      "object_json": {"...": "..."},
      "stability_class": "preference",
      "confidence": 0.92,
      "evidence_message_ids": ["<uuid>"],
      "rationale": "string"
    }
  ]
}
```

`rationale` is captured in `raw_payload` for audit; it is not stored as a
separate column.

### Predicate vocabulary (V1, D046 + D050 + D057)

Flat enum option (RFC 0011 Open Question 1 option `a`). The build prompt
freezes this list in the response schema **and** in the `predicate_vocabulary`
lookup table (see *Schema → predicate_vocabulary*). Re-extraction is the
path for any later vocabulary change (D045).

Each predicate carries:

- a **stability class** (one of the seven D008 values),
- a **cardinality class** (`single_current` /
  `single_current_per_object` / `multi_current` / `event`) per D050,
- an **object kind** (`text` / `json`),
- a **group-object key list** (for `single_current_per_object`,
  `multi_current`, and `event` predicates: the ordered list of
  `object_json` keys whose normalized values form the belief group's
  object discriminator; empty for plain `single_current`),
- optional **required-keys** for `object_json` shapes (DB trigger backstop;
  the JSON-schema enum stays the primary line of defense).

#### Cardinality classes (D050)

- `single_current` — at any moment in time the user has exactly one current
  value per `(subject, predicate)`. A different value supersedes the
  prior. Examples: `has_name`, `has_pronouns`, `lives_at`, `drives`,
  `eats_diet`.
- `single_current_per_object` — at any moment in time the user has exactly
  one current value per `(subject, predicate, object discriminator)`. A
  different value for the same discriminator supersedes the prior, but
  different discriminators create independent belief chains. Examples:
  `relationship_with` per `name`; `project_status_is` per `project`.
- `multi_current` — multiple values may be true concurrently; group key
  uses the object discriminator so each (subject, predicate, object) gets
  its own belief chain. Examples: `has_pet`, `is_related_to`,
  `is_friends_with`, `works_with`, `uses_tool`, `owns_repo`, `prefers`,
  `dislikes`, `believes`, `studied`.
- `event` — a discrete event with no expected supersession; group key uses
  the event-defining object keys (often `name` + `when`). Examples:
  `met_with`, `traveled_to`, `talked_about`, `committed_to`, `must_do`.

#### Vocabulary table (V1)

| Predicate | Stability class | Cardinality | Object kind | Group-object keys | Required object_json keys | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `has_name` | identity | single_current | text | (n/a) | (n/a) | legal / preferred name |
| `has_pronouns` | identity | single_current | text | (n/a) | (n/a) | e.g., "she/her" |
| `born_on` | identity | single_current | text | (n/a) | (n/a) | ISO date string |
| `lives_at` | identity | single_current | json | (n/a) | `address_line1` | JSON-only per S-F009; short forms emit `{address_line1: "..."}` |
| `holds_role_at` | identity | single_current | json | (n/a) | `role`, `employer` | optional `since`, `until` |
| `has_pet` | identity | multi_current | json | `name`, `species` | `species` | optional `name`, `since` |
| `is_related_to` | relationship | multi_current | json | `name` | `name`, `kind` | optional `since` |
| `is_friends_with` | relationship | multi_current | text | text | (n/a) | name or alias |
| `works_with` | relationship | multi_current | text | text | (n/a) | name |
| `prefers` | preference | multi_current | text | text | (n/a) | open string |
| `dislikes` | preference | multi_current | text | text | (n/a) | open string |
| `believes` | preference | multi_current | text | text | (n/a) | open opinion |
| `uses_tool` | preference | multi_current | text | text | (n/a) | named software / hardware |
| `drives` | preference | single_current | text | (n/a) | (n/a) | vehicle make/model |
| `eats_diet` | preference | single_current | text | (n/a) | (n/a) | e.g., "vegetarian" |
| `working_on` | project_status | multi_current | text | text | (n/a) | project name |
| `project_status_is` | project_status | single_current_per_object | json | `project` | `project`, `status` | `status ∈ ('exploring','in_progress','blocked','paused','shipped','abandoned')` |
| `owns_repo` | project_status | multi_current | text | text | (n/a) | repo path / url |
| `wants_to` | goal | multi_current | text | text | (n/a) | aspirational verb phrase |
| `plans_to` | goal | multi_current | json | `action` | `action` | optional `by_when` |
| `intends_to` | goal | multi_current | text | text | (n/a) | open string |
| `must_do` | task | event | text | text | (n/a) | open action item |
| `committed_to` | task | event | json | `action`, `with_party` | `action` | optional `with_party`, `by_when` |
| `feels` | mood | multi_current | text | text | (n/a) | open emotion / disposition. `experiencing` was dropped from V1 (S-F010); the prompt routes "experiencing" lexicalizations to `feels`. |
| `relationship_with` | relationship | single_current_per_object | json | `name` | `name`, `status` | `status ∈ ('close','distant','strained','estranged','professional')` |
| `met_with` | relationship | event | json | `name`, `when` | `name` | optional `when` |
| `talked_about` | preference | event | text | text | (n/a) | topic name; classified `event` per S-F010 |
| `studied` | identity | multi_current | text | text | (n/a) | school / program / subject |
| `traveled_to` | identity | event | json | `place`, `when` | `place` | optional `when`, `with` |

`experiencing` is removed from the V1 enum. Both stability classes and
cardinality classes are looked up from `predicate_vocabulary` rather than
aggregated by the consolidator (D050 / D057, S-F018).

#### Predicate emission guide (V1)

The extractor prompt embeds these rules to reduce duplicate-chain noise
(S-F010):

- Use `met_with` only when the assertion describes a discrete event (with
  or without an explicit `when`); use `is_friends_with` for the durable
  relation; use `relationship_with` only when the assertion includes one of
  the closed `status` values.
- Lexicalizations of "experiencing X" emit `feels: "X"`. The prompt does
  not allow `experiencing` as a predicate.
- `talked_about` is event-class. Multiple `talked_about` claims with
  different topics are **not** contradictions; they are independent
  events.
- `wants_to` / `plans_to` / `intends_to` precedence: emit `plans_to` when
  the assertion has an `action` and (optionally) a `by_when`; emit
  `wants_to` for aspirational verb phrases without commitment language;
  emit `intends_to` only when the assertion is explicitly an intention
  short of a plan. Each predicate has its own group-object key, so
  emission noise still produces distinct (non-contradicting) chains.
- `lives_at` is JSON-only. Short address forms emit
  `{address_line1: "<text>"}` (S-F009).

### Object representation (D046 + D057 + RFC 0011 OQ2)

- `object_text` is used when the fact is a single value with no useful
  sub-structure. Examples: `prefers → "iced coffee"`,
  `dislikes → "open offices"`, `wants_to → "learn German"`.
- `object_json` is used when the fact has named sub-attributes the consumer
  would query individually. Examples:
  `holds_role_at → {role: "Senior Engineer", employer: "Acme",
  since: "2024-03"}`, `committed_to → {action: "review the migration",
  with_party: "Sam", by_when: "2026-05-09"}`.
- The object kind for each predicate is fixed by `predicate_vocabulary`. The
  schema requires exactly one of `object_text` / `object_json` per claim,
  and which one must match the predicate's pinned object kind. (D057
  enforces this through a CHECK on the predicate's `object_kind`.)
- Required-keys validation for `object_json` shapes uses a per-predicate
  trigger that consults the `predicate_vocabulary.required_object_keys`
  array. Full JSON Schema enforcement of structured shapes (typed values,
  `additionalProperties`) stays prompt-side in V1; the trigger is a
  defense-in-depth backstop only (S-F011).
- Cross-shape duplication (`object_text` and `object_json` chains for the
  same predicate) is structurally impossible in V1 because every predicate
  has exactly one allowed object kind. RFC 0011 OQ4 resolves this way.
  S-F009: `lives_at` is now JSON-only; the prior dual-shape exception is
  removed.

### Evidence rules

- `claims.evidence_message_ids UUID[] NOT NULL`,
  `cardinality(evidence_message_ids) > 0` enforced by CHECK.
- The extractor JSON schema constrains `items` to the segment's actual
  `message_ids`. A `BEFORE INSERT` trigger validates membership against the
  parent segment's `message_ids` and raises on mismatch. Phase 2's
  cross-conversation / unordered checks already gate the segment-level
  inputs (D030); this trigger gates the per-claim subset.
- The extractor is allowed to cite the entire `message_ids` set when it
  cannot localize finer; this is treated as weak grounding by later eval but
  is not a schema violation.
- `beliefs.evidence_ids UUID[] NOT NULL`,
  `cardinality(evidence_ids) > 0` enforced by CHECK at every status (D043
  strengthens D003). Empty evidence is never permitted on a belief row.
- `beliefs.claim_ids UUID[] NOT NULL`,
  `cardinality(claim_ids) > 0`. The consolidator records every contributing
  claim id; this is the path back to extraction provenance independent of
  the raw-message chain.

### Time semantics (D048)

`valid_from` and `valid_to` represent **fact validity only** — the interval
the belief asserts the fact is true. Row-lifecycle events
(close-and-insert under same value, supersede under contradiction, reject
under reclassification, close under `--rebuild`) use `status`,
`superseded_by`, and a new `closed_at` timestamp; they do **not** mutate
`valid_to` outside the cases where the evidence asserts that the fact ended
or changed.

| Column | Meaning | Source |
| --- | --- | --- |
| `claims.extracted_at` | When the extractor wrote the row | `now()` at insert |
| `beliefs.observed_at` | When the supporting evidence was observed in the corpus | `MAX(messages.created_at)` over the union of `evidence_ids`, falling back to `messages.imported_at` when `created_at` is null |
| `beliefs.valid_from` | Start of the bitemporal interval the belief asserts as true | initial insert: `MIN(messages.created_at)` over `evidence_ids` (same null fallback); contradiction supersession: `MIN(messages.created_at)` over the new evidence subset (the moment the contradicting evidence first appears) |
| `beliefs.valid_to` | End of the interval; NULL = currently valid. Only set when (a) an explicit temporal qualifier in the claim ends the fact (deferred, see *Discovery vs biographic time*), or (b) a contradiction supersedes the belief and the new evidence's `MIN(messages.created_at)` becomes the prior fact's end. Never set to `now()` for lifecycle events (D048). |
| `beliefs.closed_at` | When the row left the active set for any lifecycle reason (same-value supersession, contradiction close, reject, rebuild close). NULL while the row is active. | UPDATE-only column gated by the transition API (D052). |
| `beliefs.recorded_at` | When the consolidator wrote the row | `now()` at insert |
| `beliefs.extracted_at` | When the contributing claims were extracted | `MIN(claims.extracted_at)` over `claim_ids` |

`observed_at = MAX(messages.created_at)` is "the most recent moment the
evidence shows we saw it" — used by the contradiction auto-resolution rule
to order two beliefs that disagree on otherwise-non-overlapping intervals.

`valid_from = MIN(...)` because the evidence span witnesses the fact
starting at its earliest message.

#### Discovery time vs biographic time (D051 / S-F004)

V1 `beliefs.valid_from` and `beliefs.valid_to` are **discovery time** —
the interval the corpus first/last witnessed evidence of the assertion.
Several predicates carry biographic time inside `object_json`
(`holds_role_at.since` / `until`, `traveled_to.when`, `committed_to.by_when`,
`lives_at.since`, `born_on` itself). V1 does not lift those biographic
qualifiers into the validity columns. A 2026 conversation that says "I
lived in Boston from 2014 to 2018" is recorded as a 2026 belief whose
biographic interval lives only in the object payload.

Consequences:

- "What did I believe on 2020-06-15?" cannot be answered from
  `valid_from` / `valid_to` alone in V1.
- HUMAN_REQUIREMENTS' biographic-interval contract is partially honored:
  on the discovery-time axis it is enforced; on the biographic axis it
  is acknowledged as a known V1 limitation.
- Phase 4+ may add `biographic_valid_from` / `biographic_valid_to`
  columns or a view that joins them out of `object_json`. The schema
  does not reserve those columns now.
- Contradiction auto-resolution (`temporal_ordering`) operates on
  discovery-time intervals. With the close rule fixed by D048
  (contradiction close uses `MIN(new_evidence.created_at)`), historical
  evidence intervals abut rather than overlap and the rule fires
  correctly.

### Privacy-tier propagation (D019 / D032 + D054)

- `claims.privacy_tier` = parent `segments.privacy_tier`.
- `beliefs.privacy_tier` = `MAX(claims.privacy_tier)` across `claim_ids`
  (D019 / D032 carry rule).
- Reclassification captures continue the parent-scoped invalidation rule
  (D028 / D032). When a `captures` row of `capture_type='reclassification'`
  targets a raw row whose tier rises, the affected segments get invalidated
  per Phase 2 rules; downstream this invalidates active extractions and
  beliefs that depend on those segments. The Phase 3 invalidation rule:
  - All `claim_extractions` rows for invalidated segments transition to
    `status='superseded'` and a fresh extraction is queued under the same
    `extraction_prompt_version` once the segment is re-segmented and active.
  - All `claims` rows for invalidated segments stay in place (insert-only),
    but the consolidator excludes them from the active claim set by joining
    on the active segment generation × latest active `claim_extractions`
    row per segment (D049). The "invalidated" set is the symmetric
    difference: claims previously contributing to a belief that no longer
    appear in the active claim set after reclassification.

#### Recompute decision tree (D054, S-F008)

For each belief whose contributing `claim_ids` overlap an invalidated
claim set, compute the surviving claim set (claims still attached to
currently-active segment generations under the latest active extraction).
Then:

1. **Empty surviving set.** Reject the belief: `closed_at = now()`,
   `status = 'rejected'`. `belief_audit` writes
   `transition_kind = 'reject'` with the reclassification capture id in
   `score_breakdown.cause_capture_id`.
2. **Non-empty surviving set, same value.** Close-and-insert under the
   same value via the same-value supersession path (`transition_kind =
   'supersede'`). The new row's `claim_ids` is the surviving set; the
   prior row's `valid_to` is **unchanged** (D048).
3. **Non-empty surviving set, different value.** Close the prior, insert
   a new candidate at the surviving-set value, and INSERT a
   `contradictions` row at
   `detection_kind = 'reclassification_recompute'`,
   `resolution_status = 'open'`. Auto-resolution does **not** fire on this
   detection kind — privacy events are not temporal events.

This rule preserves the principle that tier changes are evidence
(captures), never UPDATE on raw, and that retrieval-visible derived rows
must reflect current effective tier (D023 / D028).

## Stage B — Belief consolidation (deterministic Python)

The consolidator is deterministic Python in V1 with no LLM call. Its
`prompt_version` and `model_version` columns record the consolidator
version string (e.g., `consolidator.v1.d044.no-auto-accept`) so the schema
column has consistent semantics with the extractor.

### Grouping key (D050)

```text
group_key = (normalize(subject_text), predicate, group_object_key)
```

`normalize` (canonical SQL function `engram_normalize_subject(text)
RETURNS text` + Python helper that calls it):

1. Unicode NFKC normalization.
2. Lowercase.
3. Trim leading and trailing whitespace.
4. Collapse internal whitespace runs to a single ASCII space.
5. Strip a fixed set of trailing punctuation: `. , ; : ! ?`.

This is **not** entity canonicalization. It is just enough to prevent
duplicate chains for trivial spelling variation (`"My dog Pip "` →
`"my dog pip"`). Pluralization, possessives, alias resolution, and case
inflection are intentionally unaddressed so Phase 4 can re-derive cleanly.

`group_object_key` (D050, S-F003) is computed from the predicate's
`predicate_vocabulary.cardinality_class`:

- **single_current** → `''` (empty string). Only one current value per
  `(subject, predicate)`; a different value triggers contradiction.
- **single_current_per_object** / **multi_current** / **event** → for
  object_text predicates, `normalize(object_text)`. For object_json
  predicates, the canonicalized values of the predicate's
  `group_object_keys` joined with `''` (unit separator). Missing keys
  serialize as the empty string. The resulting string is normalized (NFKC
  + lowercase + whitespace collapse + trim, no trailing-punctuation strip
  — JSON values may legitimately end with punctuation).

This means two `works_with` claims for "Alice" and "Bob" produce two
distinct group keys and never trigger a contradiction. Two
`relationship_with({name: "Alice", status: ...})` claims with different
statuses do contradict because `relationship_with` is
`single_current_per_object` keyed on `name`; the same predicate for
`{name: "Bob", status: ...}` is a separate chain. Likewise,
`project_status_is({project: "Engram", status: "blocked"})` can contradict
another status for Engram without colliding with
`project_status_is({project: "BenchKit", status: "shipped"})`.

### Value equality

Within a single group key, two values are equal when, after `normalize` on
string forms and exact JSONB equality on object forms, they match within
the same column. Cross-shape equality cannot occur: every predicate has
exactly one allowed object kind (D057). For `multi_current` / `event`
predicates, value equality is reduced to "same group_object_key under the
same predicate" — the discriminator is already part of the key.
`single_current_per_object` keeps full value equality within the scoped
group object, so different statuses for the same relationship or project
are treated as contradictions instead of same-value reinforcement.

### Decision rules

The consolidator iterates over (a) the active claim set for the
conversation it is consolidating and (b) the active beliefs whose
`claim_ids` may have left the active claim set since the last pass.

**Decision Rule 0 — Orphan rejection (D049, S-F002 / Gemini P0-2).**
For every active belief whose `claim_ids` are no longer fully present in
the active claim set (because the contributing claims attach to a now-
inactive `claim_extractions` vintage, or because the segment generation
was deactivated, or because a re-extraction emitted fewer claims),
reject the belief: `closed_at = now()`, `status = 'rejected'`,
`belief_audit.transition_kind = 'reject'`,
`score_breakdown.cause = 'orphan_after_reclassification' |
'orphan_after_reextraction' | 'orphan_after_segment_deactivation'`.
This rule runs first so subsequent rules see a clean slate.

For each `(group_key)` in the active claims after Decision Rule 0:

1. **No existing belief.** INSERT a new `beliefs` row at
   `status='candidate'`, `valid_from = MIN(messages.created_at)` over the
   union of contributing `evidence_message_ids`,
   `valid_to = NULL`, `closed_at = NULL`,
   `evidence_ids = union(claims.evidence_message_ids)`,
   `claim_ids = supporting claim ids`,
   `confidence = MEAN(claims.confidence)` (D056),
   `stability_class = predicate_vocabulary[predicate].stability_class`
   (D057, S-F018),
   `privacy_tier = MAX(claims.privacy_tier)`,
   `observed_at = MAX(messages.created_at)` over `evidence_ids`,
   `extracted_at = MIN(claims.extracted_at)`. Write a `belief_audit` row
   with `transition_kind = 'insert'` and a `score_breakdown` block
   recording mean / max / min / count / stddev of contributing
   confidences (D056).
2. **Existing belief, same value (single_current /
   single_current_per_object) or same group_object_key (multi_current /
   event).** Close-and-insert with merged provenance.
   Insert a fresh row whose `evidence_ids = union(prior + new)`,
   `claim_ids = union(prior + new)`, `valid_from` carried from the prior
   row (the fact's start has not changed), `valid_to` carried from the
   prior row (NULL or whatever explicit end it already had — D048
   forbids same-value lifecycle from mutating fact validity),
   `confidence = MEAN` over the merged claim set,
   `observed_at = MAX(messages.created_at)` over the merged evidence,
   `extracted_at = MIN(claims.extracted_at)` over the merged claim set.
   Then on the prior row, set `superseded_by = <new id>`,
   `closed_at = now()`, `status = 'superseded'`. Do **not** mutate the
   prior row's `valid_to` (D048, S-F001 / Gemini P1). Write a
   `belief_audit` row with `transition_kind = 'supersede'`.
3. **Existing belief, different value (single_current /
   single_current_per_object only).**
   Contradiction. Close the prior belief: `valid_to =
   MIN(messages.created_at)` over the new evidence subset (the moment the
   contradicting evidence first appears), `closed_at = now()`,
   `status = 'superseded'`. Insert a new belief at `status='candidate'`
   with `valid_from = MIN(messages.created_at)` over the new evidence.
   INSERT a `contradictions` row at `resolution_status='open'`,
   `detection_kind='same_subject_predicate'`. Auto-resolve when the two
   beliefs' fact-validity intervals (`valid_from` / `valid_to`) are
   non-overlapping; record as `auto_resolved` with
   `resolution_kind='temporal_ordering'` and set `resolved_at = now()`.
   Pure value disagreements with overlapping intervals stay `open` for
   the Phase 4 review queue. Write `belief_audit` rows for the close
   (`transition_kind='close'`) and the insert
   (`transition_kind='insert'`).

For `multi_current` and `event` predicates, Rule 3 does **not** fire — a
different group_object_key falls under Rule 1 (a new chain), and the
same group_object_key with a different stored value matches Rule 2
because group_object_key is the equality key. For
`single_current_per_object`, different group_object_keys also fall under
Rule 1, but different values inside the same group_object_key fall under
Rule 3.

Auto-resolution heuristics other than temporal ordering are out of scope
for V1 (RFC 0011 OQ5). Confidence-weighted and stability-class-
conditional auto-resolution are deferred.

### Confidence aggregator (D056)

`confidence = MEAN(claims.confidence)` for the contributing set.
`belief_audit.score_breakdown` preserves `{mean, max, min, count, stddev}`
on every transition for forensic use, so retrieval consumers and
HITL reviewers can see the underlying spread (HUMAN_REQUIREMENTS' refusal
of false precision contract).

### Belief transition API (D052, S-F005)

All belief state changes flow through a single Python module
`engram.consolidator.transitions` exposing:

- `insert_belief(...)`,
- `supersede_belief(prior_id, new_belief_payload)`,
- `close_belief(prior_id, reason)` (rebuild),
- `reject_belief(prior_id, cause)` (orphan / reclassification).

Each function opens a transaction, sets a session GUC
`engram.transition_in_progress = '<request_uuid>'`, runs the belief
INSERT/UPDATE plus the matching `belief_audit` INSERT, and commits.

The `beliefs` mutation trigger requires the GUC to be set on every
UPDATE; direct SQL UPDATE without the GUC is rejected. The `belief_audit`
INSERT records the same `<request_uuid>` so an operator can reconstruct
the transition pair from log inspection. This is the spec's concrete
answer to S-F005's "audit-on-update invariant lacks an implementable
mechanism" — the trigger does not have to prove a future audit row will
arrive; the API guarantees it before lifting the GUC.

Test #11 / #12 exercise both the rejection path (direct UPDATE without
GUC) and the success path (transition API call writes both rows and
clears the GUC).

### Status transitions allowed in Phase 3

| From | To | Trigger | Audit `transition_kind` |
| --- | --- | --- | --- |
| (insert) | `candidate` | new group key | `insert` |
| `candidate` | `superseded` | close-and-insert under same value (Rule 2) | `supersede` |
| `candidate` | `superseded` | contradiction supersedes (Rule 3, single_current / single_current_per_object only) | `supersede` |
| `candidate` | `rejected` | reclassification recompute, empty surviving set (D054 case 1) | `reject` |
| `candidate` | `rejected` | orphan after re-extraction or segment deactivation (Decision Rule 0) | `reject` |
| `candidate` | `superseded` | rebuild close (D055) | `close` then `insert` |

`provisional`, `accepted`, `reactivate`, `promote`, `demote` exist in the
schema for Phase 4 and are not written by the Phase 3 consolidator (D044).
The CHECK constraint on `belief_audit.transition_kind` keeps them
representable.

### Re-derivation behavior (D045 + D049 + D055)

- **Active claim set.** A claim is active for consolidation iff:
  - its `segment_id` is the current active generation, and
  - its `extraction_id` is the latest `claim_extractions` row at
    `status='extracted'` for that segment.

  When a new `claim_extractions` row at a different
  `(extraction_prompt_version, extraction_model_version)` lands at
  `status='extracted'`, the prior row for the same segment transitions to
  `status='superseded'` in the same transaction (D049). Older claims
  remain in place per the insert-only constraint, but the consolidator
  no longer treats them as active.

- **Re-extraction.** Bumping `extraction_prompt_version` or
  `extraction_model_version` inserts new `claims` rows under a new
  `claim_extractions` row; the prior row supersedes; older claims drop
  out of the active set. The consolidator picks up the new claim set
  on its next pass and applies Decision Rule 0 to reject any beliefs
  whose `claim_ids` are no longer fully present (S-F002 / Gemini P0-2).

- **Consolidator-only change.** Re-consolidation under a new consolidator
  `prompt_version` is a separate operator action. The supervisor offers
  an explicit `engram consolidate --rebuild` mode (see *CLI / operator
  expectations*) that closes the existing active belief set and reruns
  the decision rules over the full active claim set. Closures go through
  the transition API as `transition_kind='close'` with
  `previous_status='candidate'` and `new_status='superseded'`; new rows
  insert as `candidate`.

- **Rebuild idempotency (D055, S-F009).** A second `--rebuild` against an
  unchanged active claim set produces an active belief set that is
  **structurally equivalent** to the first rebuild's output: same
  `(group_key, value, evidence_ids, claim_ids, stability_class,
  confidence, valid_from, valid_to, status='candidate')` per row, but
  with new row IDs, new `recorded_at` timestamps, and additional
  `belief_audit` rows. The acceptance criterion is structural
  equivalence (test #23), not ID-stable no-op. Repeated rebuilds bloat
  the audit chain by design — operators are expected to run rebuild
  rarely and intentionally.

This keeps blast radius bounded: an extractor prompt bump invalidates only
extraction state for re-extracted segments. A consolidator change is
explicit operator work.

### Consolidator parallelism (D053)

V1 default: per-conversation pipeline. The consolidator runs after Stage A
finishes a conversation and consumes the new claims for that conversation.
This makes belief growth incremental and observable during a long extraction
run without holding up consolidation behind a corpus-wide barrier. Resolves
RFC 0011 OQ8.

Cross-conversation belief group keys are global: two conversations may
both produce a new claim for the same `(subject_normalized, predicate,
group_object_key)`. Concurrency safety is enforced by a UNIQUE partial
index on `beliefs (subject_normalized, predicate, group_object_key)
WHERE valid_to IS NULL AND status IN ('candidate', 'provisional',
'accepted')` (D053, S-F006). When two consolidator passes both attempt
to INSERT a candidate for the same group key, one wins and one fails on
the unique constraint. The transition API catches the conflict, re-reads
the now-existing active belief, and retries the decision rules — which
will dispatch to Rule 2 (same value) or Rule 3 (different value) as
appropriate.

Per-conversation parallelism therefore preserves correctness without
serializing all consolidation behind a single mutex.

## Schema

All Phase 3 tables live in a new migration `migrations/00X_claims_beliefs.sql`
(number assigned by the build prompt to match the next slot at build time).
The Phase 1.5 `consolidation_progress` table is reused unchanged with new
`stage` values (`extractor`, `consolidator`).

### `predicate_vocabulary` (D057)

| Column | Type | Notes |
| --- | --- | --- |
| `predicate` | `TEXT PK` | matches `claims.predicate` and the LLM JSON-schema enum |
| `stability_class` | `TEXT NOT NULL` | CHECK in the seven D008 values |
| `cardinality_class` | `TEXT NOT NULL` | CHECK in `('single_current','single_current_per_object','multi_current','event')` |
| `object_kind` | `TEXT NOT NULL` | CHECK in `('text','json')` |
| `group_object_keys` | `TEXT[] NOT NULL DEFAULT '{}'` | empty for plain `single_current`; ordered key list for the rest |
| `required_object_keys` | `TEXT[] NOT NULL DEFAULT '{}'` | required keys for `object_json` shapes (trigger backstop) |
| `description` | `TEXT NOT NULL` | one-line human-readable definition matching the *Predicate emission guide* |

Seed data is the V1 vocabulary table above. `claims.predicate` references
this table via FK. UPDATE / DELETE on `predicate_vocabulary` is allowed
(operator only) but bumps the consolidator `prompt_version` so re-runs
re-derive consistently.

### `claim_extractions`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID PK` | `gen_random_uuid()` |
| `segment_id` | `UUID NOT NULL` | FK `segments(id)` |
| `generation_id` | `UUID NOT NULL` | FK `segment_generations(id)` |
| `extraction_prompt_version` | `TEXT NOT NULL` | |
| `extraction_model_version` | `TEXT NOT NULL` | |
| `request_profile_version` | `TEXT NOT NULL` | |
| `status` | `TEXT NOT NULL` | CHECK in `('extracting','extracted','failed','superseded')` |
| `claim_count` | `INT NOT NULL DEFAULT 0` | |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `completed_at` | `TIMESTAMPTZ NULL` | |
| `raw_payload` | `JSONB NOT NULL DEFAULT '{}'` | Always populated for completed extractions: D035 diagnostics on failure, raw model output and salvage diagnostics on success/empty (M-F001 / D058) |

Partial unique index for active extraction:

```sql
CREATE UNIQUE INDEX claim_extractions_active_unique_idx
ON claim_extractions (segment_id, extraction_prompt_version,
                      extraction_model_version)
WHERE status IN ('extracting','extracted');
```

UPDATEs are restricted to `status`, `claim_count`, `completed_at`,
`raw_payload`. DELETE is blocked. Per D049, transitions from
`extracted` to `superseded` (when a newer extraction replaces a prior
extractor version) are explicitly allowed by the mutation guard.

`raw_payload` shape for completed extractions:

```json
{
  "model_response": "...",
  "parse_metadata": {"prompt_tokens": 0, "completion_tokens": 0, ...},
  "extraction_result_kind": "populated | clean_zero | accounted_zero",
  "dropped_claims": [
    {"reason": "trigger_violation", "claim": {...}, "error": "..."}
  ],
  "failure_kind": null
}
```

`extraction_result_kind` is required for `status='extracted'` rows:

- `populated` when `claim_count > 0`, including mixed valid+invalid
  extractions;
- `clean_zero` when `claim_count = 0` and no prior/final drops are counted;
- `accounted_zero` when `claim_count = 0` and validation-repair prior or final
  drops were diagnosed, redacted, and counted.

For failed extractions, `failure_kind` and the D035 attempt diagnostics
are populated; `dropped_claims` may also be populated when partial
salvage was attempted.

D064 accounted-zero eligibility is intentionally narrow. Parse errors, schema
rejections, repair parse/schema/service failures, missing drop arrays/counts,
count mismatches, unknown drop reasons, unknown or unbounded local validation
error classes, and unredacted diagnostics remain failed. The post-repair
all-invalid hard-failure kind is `local_validation_failed_post_repair`, with a
closed `accounting_failure_kind` such as `missing_diagnostics`,
`count_mismatch`, `unknown_drop_reason`, `unknown_error_class`, or
`unredacted_diagnostics`. `trigger_violation` remains the per-drop reason and
database-backstop failure kind, not the post-repair all-invalid failure kind.

Dropped-claim gate accounting uses the current-version latest extraction row
per selected active segment:

```text
inserted_claims = claim_extractions.claim_count
final_drops = validation_repair.final_dropped_count when present,
              else len(raw_payload.dropped_claims)
prior_drops = validation_repair.prior_dropped_count when present, else 0
expanded_drops = prior_drops + final_drops
expanded_dropped_claim_rate =
  sum(expanded_drops) / (sum(inserted_claims) + sum(expanded_drops))
```

When the denominator is zero, the rate is defined as 0. The same-bound Phase 3
gate remains 10%; accounted-zero rows can complete extraction/consolidation and
still cause the same-bound run to block if the expanded rate exceeds that gate.

### `claims`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID PK` | `gen_random_uuid()` |
| `segment_id` | `UUID NOT NULL` | FK `segments(id)` |
| `generation_id` | `UUID NOT NULL` | FK `segment_generations(id)` |
| `conversation_id` | `UUID NULL` | FK `conversations(id)`; NULL reserved for future note/capture extraction (D047 keeps it NULL in V1) |
| `extraction_id` | `UUID NOT NULL` | FK `claim_extractions(id)` |
| `subject_text` | `TEXT NOT NULL` | pre-canonicalization |
| `subject_normalized` | `TEXT NOT NULL` | trigger-set via `engram_normalize_subject(subject_text)` (D052 / S-F007); index target for join-friendly queries against beliefs |
| `predicate` | `TEXT NOT NULL` | FK `predicate_vocabulary(predicate)` (D057) |
| `object_text` | `TEXT NULL` | |
| `object_json` | `JSONB NULL` | |
| `stability_class` | `TEXT NOT NULL` | CHECK in the seven D008 values |
| `confidence` | `FLOAT NOT NULL` | CHECK `[0,1]` |
| `evidence_message_ids` | `UUID[] NOT NULL` | CHECK `cardinality > 0` |
| `extraction_prompt_version` | `TEXT NOT NULL` | |
| `extraction_model_version` | `TEXT NOT NULL` | |
| `request_profile_version` | `TEXT NOT NULL` | |
| `privacy_tier` | `INT NOT NULL` | from parent segment |
| `extracted_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `raw_payload` | `JSONB NOT NULL` | including `rationale` |

Constraints / triggers:

- `CHECK ((object_text IS NOT NULL AND object_json IS NULL) OR (object_text
  IS NULL AND object_json IS NOT NULL))`.
- `CHECK (cardinality(evidence_message_ids) > 0)`.
- `BEFORE INSERT` trigger `validate_claim_evidence_message_ids` verifies
  every UUID in `evidence_message_ids` is a member of the parent segment's
  `message_ids`.
- `BEFORE INSERT` trigger `set_claim_subject_normalized` calls
  `engram_normalize_subject(subject_text)` and assigns the result to
  `subject_normalized` (S-F007).
- `BEFORE INSERT` trigger `validate_claim_predicate_object` consults
  `predicate_vocabulary` to enforce: object_kind matches the populated
  `object_text` / `object_json` column; required_object_keys are present
  on `object_json`; predicate ↔ stability_class match (D057).
- INSERT-only trigger blocks UPDATE and DELETE outright.

Indexes: `(segment_id)`, `(conversation_id)`,
`(extraction_prompt_version, extraction_model_version)`,
`(predicate)`, `(stability_class)`, `(subject_normalized, predicate)`,
GIN on `evidence_message_ids`.

### `beliefs`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID PK` | `gen_random_uuid()` |
| `subject_text` | `TEXT NOT NULL` | |
| `subject_normalized` | `TEXT NOT NULL` | trigger-set via `engram_normalize_subject(subject_text)` (S-F007); index target |
| `predicate` | `TEXT NOT NULL` | FK `predicate_vocabulary(predicate)` (D057) |
| `cardinality_class` | `TEXT NOT NULL` | trigger-set from `predicate_vocabulary[predicate].cardinality_class` (D050) |
| `object_text` | `TEXT NULL` | |
| `object_json` | `JSONB NULL` | |
| `group_object_key` | `TEXT NOT NULL DEFAULT ''` | trigger-computed per *Grouping key* (D050); empty only for plain `single_current` |
| `valid_from` | `TIMESTAMPTZ NOT NULL` | fact-validity start (D048) |
| `valid_to` | `TIMESTAMPTZ NULL` | fact-validity end; NULL = currently valid; mutated only on contradiction supersession or explicit temporal end (D048) |
| `closed_at` | `TIMESTAMPTZ NULL` | row-lifecycle close timestamp; NULL while active (D048) |
| `observed_at` | `TIMESTAMPTZ NOT NULL` | `MAX(messages.created_at)` over evidence |
| `recorded_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `extracted_at` | `TIMESTAMPTZ NOT NULL` | |
| `superseded_by` | `UUID NULL` | FK `beliefs(id)` |
| `status` | `TEXT NOT NULL` | CHECK in `('candidate','provisional','accepted','superseded','rejected')` |
| `stability_class` | `TEXT NOT NULL` | trigger-set from `predicate_vocabulary[predicate].stability_class` (D057, S-F018) |
| `confidence` | `FLOAT NOT NULL` | mean over contributing claims (D056); CHECK `[0,1]` |
| `evidence_ids` | `UUID[] NOT NULL` | CHECK `cardinality > 0` (D043) |
| `claim_ids` | `UUID[] NOT NULL` | CHECK `cardinality > 0` |
| `prompt_version` | `TEXT NOT NULL` | consolidator version |
| `model_version` | `TEXT NOT NULL` | consolidator version |
| `privacy_tier` | `INT NOT NULL` | MAX over `claim_ids` |
| `raw_payload` | `JSONB NOT NULL` | consolidator decision rationale |

Constraints / triggers:

- `CHECK ((object_text IS NOT NULL AND object_json IS NULL) OR (object_text
  IS NULL AND object_json IS NOT NULL))`.
- `CHECK (cardinality(evidence_ids) > 0)` and
  `CHECK (cardinality(claim_ids) > 0)`.
- `BEFORE INSERT` trigger sets `subject_normalized`,
  `cardinality_class`, `stability_class`, and `group_object_key` from
  `predicate_vocabulary` and the input row; rejects predicate not in
  the vocabulary.
- Mutation trigger blocks DELETE outright. Allows UPDATE only on
  `valid_to`, `closed_at`, `superseded_by`, `status` — and only when
  the session GUC `engram.transition_in_progress` is set (D052). Every
  UPDATE is paired with a `belief_audit` INSERT carrying the same
  request UUID; the transition API guarantees the pair commits
  atomically.

Indexes:

- `(subject_normalized, predicate, group_object_key)` — base join key,
- **UNIQUE** partial index on `(subject_normalized, predicate,
  group_object_key) WHERE valid_to IS NULL AND status IN ('candidate',
  'provisional', 'accepted')` (D053, S-F006),
- `(status, stability_class)`,
- GIN on `evidence_ids` and `claim_ids`,
- `(superseded_by)` for traversal.

### `belief_audit` (append-only)

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID PK` | |
| `belief_id` | `UUID NOT NULL` | FK `beliefs(id)` |
| `transition_kind` | `TEXT NOT NULL` | CHECK in `('insert','close','supersede','promote','demote','reject','reactivate')` |
| `previous_status` | `TEXT NULL` | |
| `new_status` | `TEXT NOT NULL` | |
| `previous_valid_to` | `TIMESTAMPTZ NULL` | |
| `new_valid_to` | `TIMESTAMPTZ NULL` | |
| `prompt_version` | `TEXT NOT NULL` | |
| `model_version` | `TEXT NOT NULL` | |
| `input_claim_ids` | `UUID[] NULL` | |
| `evidence_message_ids` | `UUID[] NOT NULL DEFAULT '{}'` | raw `messages.id` set; renamed from `evidence_episode_ids` for parity with `claims.evidence_message_ids` (M-F002 / S-F016) |
| `score_breakdown` | `JSONB NOT NULL DEFAULT '{}'` | aggregator outputs `{mean, max, min, count, stddev}` plus `cause`/`request_uuid` |
| `request_uuid` | `UUID NOT NULL` | session-GUC marker matching the paired belief UPDATE / INSERT (D052) |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |

UPDATE and DELETE are blocked outright by trigger.

#### Lineage traversal (S-F015)

Both the same-value supersession chain and the contradiction lineage
must be traversable to reconstruct a belief's full history. The two
paths are:

- **Same-value chain.** Walk `superseded_by` recursively. Rule 2 sets
  this pointer; rebuild close also sets it.
- **Contradiction lineage.** Join `contradictions` on `belief_a_id` /
  `belief_b_id`. Rule 3 records the contradiction edge but does **not**
  set `superseded_by` on the prior belief — contradictions open new
  chains, not refresh existing ones.

A complete "what came before this belief" query unions both paths.
Test coverage: see acceptance test #28 below.

### `contradictions`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `UUID PK` | |
| `belief_a_id` | `UUID NOT NULL` | FK `beliefs(id)` |
| `belief_b_id` | `UUID NOT NULL` | FK `beliefs(id)` |
| `detected_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `detection_kind` | `TEXT NOT NULL` | one of `same_subject_predicate` (Rule 3) or `reclassification_recompute` (D054 case 3). Older `temporal_overlap_disagreement` example removed (S-F015 / M-F004). |
| `resolution_status` | `TEXT NOT NULL DEFAULT 'open'` | CHECK in `('open','auto_resolved','human_resolved','irreconcilable')` |
| `resolution_kind` | `TEXT NULL` | e.g., `temporal_ordering` |
| `resolved_at` | `TIMESTAMPTZ NULL` | |
| `privacy_tier` | `INT NOT NULL` | MAX over the two beliefs |
| `raw_payload` | `JSONB NOT NULL DEFAULT '{}'` | |
| | | `CHECK (belief_a_id <> belief_b_id)` |

Mutation trigger allows UPDATE only on `resolution_status`,
`resolution_kind`, `resolved_at`. DELETE blocked.

### `consolidation_progress` reuse

Phase 3 writes:

- `stage='extractor'`, `scope='conversation:<uuid>'`, `position` =
  `{conversation_id, segment_id, segment_index_within_conversation}`.
- `stage='consolidator'`, `scope='conversation:<uuid>'`, `position` =
  `{conversation_id, last_claim_extracted_at}`.

Failure semantics inherit from Phase 2: `error_count` increments on
service-unavailable / parse failures; `ENGRAM_EXTRACTOR_MAX_ERROR_COUNT`
(default 3) freezes a parent until manually requeued.

### Failure diagnostics on `claim_extractions.raw_payload`

D035 mirror of Phase 2 segmenter:

```json
{
  "failure_kind": "parse_error | schema_invalid | service_unavailable | context_guard | retry_exhausted | trigger_violation",
  "last_error": "string",
  "attempts": 3,
  "attempt_max_tokens": [4096, 8192, 8192],
  "decode_counts": [123, 234, 234],
  "attempt_errors": ["..."]
}
```

`trigger_violation` covers the case where the extractor schema accepted a
UUID that the `validate_claim_evidence_message_ids` trigger rejected at
insert (defense in depth in case the schema enum is bypassed).

## Local LLM request profile and structured output

- D034 deterministic structured request: `stream=false`, `temperature=0`,
  `top_p=1`, `chat_template_kwargs.enable_thinking=false`,
  `response_format={"type":"json_schema",...}`. Parse only
  `choices[0].message.content`. Reject `reasoning_content`-only,
  Markdown-fenced, or schema-invalid responses.
- D035 health smoke before any long extraction run: same shape as Phase 2.
  A tiny D034-profile completion that returns a schema-valid object must
  pass before and after any preflight slice.
- D037 / D038 inheritance: tool-message bodies remain compact placeholders
  in the prompt; the context guard refuses to send any request whose
  `prompt_tokens + max_tokens + safety_margin` would reach context shift.
- The extractor reuses the same ik-llama endpoint and pinned model id as
  Phase 2 (`ENGRAM_SEGMENTER_MODEL` is the de facto shared model env in
  V1). The build prompt may rename to `ENGRAM_EXTRACTOR_MODEL` for
  clarity; either way the corpus-reading process binds to 127.0.0.1 only
  (D020).

## Resumability and supervisor behavior

- Per-segment idempotence: the partial unique index on `claim_extractions`
  prevents duplicate active extractions per
  `(segment_id, extraction_prompt_version, extraction_model_version)`.
- Per-conversation idempotence: the supervisor queries
  `consolidation_progress` for `(stage='extractor', scope='conversation:<uuid>')`
  to find the next segment to extract.
- Crash recovery: any `claim_extractions` row left at `status='extracting'`
  longer than a configurable threshold is reaped on supervisor restart and
  re-queued. The build prompt locks the threshold; default proposal:
  `ENGRAM_EXTRACTOR_INFLIGHT_TIMEOUT_SECONDS=900`.
- Service-unavailable failures are parent-scoped and retryable, mirroring
  segmentation.
- The consolidator stage runs after a conversation's extractor stage
  finishes. A failed extraction on a single segment does **not** block
  consolidation of the rest of the conversation; the consolidator simply
  proceeds with whatever claims were extracted.

## CLI / operator expectations

These names are illustrative; the build prompt locks the spelling.

```bash
engram extract --batch-size 10 --limit 100        # Stage A only
engram consolidate --batch-size 10                # Stage B only
engram pipeline-3 --extract-batch-size 10 --consolidate-batch-size 10
                                                  # full Phase 3 pipeline,
                                                  # per-conversation
engram extract --segment-id UUID                  # single-segment retarget
engram consolidate --rebuild                      # close active beliefs,
                                                  # rerun consolidator over
                                                  # current active claims
engram extract --requeue --conversation-id UUID   # reset error_count and
                                                  # retry the parent
```

`make pipeline-3` is the operator entry for an unattended local run.
Progress is printed per-parent with elapsed seconds; throttled progress is
written to stdout the same way Phase 2 emits it. Long runs expect the same
`ENGRAM_EXTRACTOR_TIMEOUT_SECONDS` shape as `ENGRAM_SEGMENTER_TIMEOUT_SECONDS`.

The CLI documents that `engram pipeline-3` is **non-destructive** by default
and emits warnings if active beliefs already exist for a different
consolidator `prompt_version`.

## Tests and acceptance criteria

Schema-level (must pass before any LLM call lands rows):

1. Migration applies cleanly from a Phase 2 active corpus state.
2. `claims` insert blocks DELETE and UPDATE.
3. `claims` insert blocks evidence ids that are not members of the parent
   segment's `message_ids`.
4. `claims` insert blocks empty `evidence_message_ids`.
5. `claims` insert blocks rows with both / neither of `object_text` and
   `object_json`.
6. `beliefs` UPDATE on any column other than `valid_to`, `closed_at`,
   `superseded_by`, `status` is rejected.
7. `beliefs` UPDATE without the session GUC `engram.transition_in_progress`
   set is rejected (D052). UPDATE through the transition API succeeds and
   writes a paired `belief_audit` row carrying the same `request_uuid`.
8. `beliefs` insert blocks empty `evidence_ids` (D043) and empty
   `claim_ids`.
9. `beliefs` insert blocks rows with both / neither of `object_text` and
   `object_json`.
10. `belief_audit` blocks UPDATE and DELETE.
11. `contradictions` UPDATE on any column other than `resolution_status`,
    `resolution_kind`, `resolved_at` is rejected.
12. `contradictions` blocks DELETE.

Extractor-level:

13. D035 health smoke before and after a 10-segment preflight returns
    schema-valid JSON.
14. Empty extraction produces a `claim_extractions` row at
    `status='extracted'`, `claim_count=0`,
    `raw_payload.extraction_result_kind='clean_zero'`, and zero `claims` rows.
    No failure diagnostics are written.
15. Extractor on a synthetic segment with one identity and one preference
    claim produces exactly two `claims` rows with the expected predicates,
    stability classes, evidence subsets, and version columns.
16. Extractor on a segment whose request would exceed the context guard
    fails closed with `failure_kind='context_guard'`.
17. Extractor parse failures retry up to the configured budget and persist
    full D035 diagnostics on exhaustion.
18. Extractor JSON schema rejects a hallucinated `evidence_message_ids`
    entry; the trigger backstop also rejects it if the schema is bypassed.
19. Fully diagnosed, redacted, all-invalid validation-repair `still_invalid`
    rows produce `status='extracted'`, `claim_count=0`,
    `failure_kind=null`, and
    `raw_payload.extraction_result_kind='accounted_zero'`.
20. Ineligible all-invalid validation-repair rows remain failed with
    `failure_kind='local_validation_failed_post_repair'` and a closed
    `accounting_failure_kind`; unknown reasons, unknown/unbounded error
    classes, count mismatches, missing diagnostics, and unredacted diagnostics
    are ineligible.
21. Mixed valid+invalid extractions with inserted claims are
    `extraction_result_kind='populated'`.
22. Expanded dropped-claim gate accounting includes validation-repair prior
    drops and final drops exactly once per model attempt phase.

Consolidator-level:

1. First pass on a conversation with one new claim group key inserts one
    `belief` at `status='candidate'` and one `belief_audit` row at
    `transition_kind='insert'`. `score_breakdown` records mean / max /
    min / count / stddev for the contributing confidences (D056).
2. Second pass introducing a same-value claim under the same group key
    closes the prior belief (`closed_at`, `status='superseded'`,
    `superseded_by`) and inserts a fresh row whose `valid_from` /
    `valid_to` are inherited from the prior fact-validity interval
    (D048 — the prior row's `valid_to` is **not** mutated by same-value
    supersession).
3. Third pass introducing a different-value claim under the same
    `single_current` or `single_current_per_object` group key closes the
    prior with
    `valid_to = MIN(messages.created_at)` over the new evidence
    (not `now()`), inserts a new candidate at
    `valid_from = MIN(messages.created_at)` over the new evidence, and
    inserts one `contradictions` row at `resolution_status='open'`,
    `detection_kind='same_subject_predicate'` (D048).
4. When the two contradicting beliefs have non-overlapping
    `valid_from` / `valid_to` intervals (which the D048 close rule
    naturally produces from historical evidence), the contradiction
    auto-resolves to `resolution_status='auto_resolved'`,
    `resolution_kind='temporal_ordering'`.
5. `engram consolidate --rebuild` closes the existing active beliefs and
    rebuilds a structurally equivalent active set (D055); running it
    twice in a row produces an active set with the same
    `(group_key, value, evidence_ids, claim_ids, valid_from, valid_to,
    status='candidate')` per row, but new IDs and `recorded_at` and
    additional audit rows. Test asserts structural equivalence, not
    ID-stable no-op.
6. Privacy reclassification on a parent conversation invalidates affected
    segments; the next consolidator pass applies D054's three-branch
    decision tree:
    - empty surviving set → `status='rejected'`,
      `transition_kind='reject'`;
    - same-value surviving set → close-and-insert via Rule 2,
      `transition_kind='supersede'`;
    - different-value surviving set → close-and-insert plus a
      `contradictions` row at
      `detection_kind='reclassification_recompute'`,
      `resolution_status='open'`.
    All three sub-cases must be exercised.
7. Targeted consolidation over a conversation with clean-zero or
   accounted-zero extraction rows completes normally; those rows contribute
   zero claims and create no synthetic beliefs.

Re-extraction and concurrency:

1. **Re-extraction blast radius (D049).** A segment with v1 and v2
    `claim_extractions` rows at `status='extracted'` (after the
    automated v1→`superseded` transition) feeds only the v2 claim set
    into consolidation. v1 claims are present in `claims` but excluded
    from the active set.
2. **Orphan rejection (Decision Rule 0).** A belief whose `claim_ids`
    leave the active claim set (segment deactivation, re-extraction
    drop, reclassification empty surviving set) is closed via
    `transition_kind='reject'` on the next consolidator pass.
3. **Scoped-current and multi-current non-conflict (D050).** Two
    `works_with` claims for different objects under the same subject
    create two distinct beliefs and zero `contradictions` rows. Two
    `relationship_with` claims with different `name` values do the same.
    Two `relationship_with` claims under the same `(subject, name)` with
    different `status` values do contradict. Two `project_status_is`
    claims for different `project` values do not collide; two statuses
    for the same project do contradict.
4. **Concurrent consolidator pass (D053).** Two consolidator
    invocations on different conversations, both producing a candidate
    for the same `(subject_normalized, predicate, group_object_key)`,
    converge to one active belief. The losing INSERT either retries
    cleanly into Rule 2 / Rule 3 or surfaces a recoverable conflict
    diagnostic.
5. **Subject normalization parity (S-F007).** SQL
    `engram_normalize_subject(text)` output matches Python
    `engram.consolidator.normalize_subject(text)` over a fixture set
    covering whitespace, punctuation, NFKC, and case variation.
6. **Predicate vocabulary FK (D057).** Inserting a claim with a
    predicate not in `predicate_vocabulary` is rejected. Inserting an
    `object_json` claim missing a `required_object_keys` value is
    rejected. Predicate-stability mismatch is rejected.
7. **Lineage traversal (S-F015).** Both `superseded_by` and
    `contradictions.belief_{a,b}_id` paths reach the prior of any
    closed-then-replaced belief.
8. **Tail-segment grammar preflight (S-F013).** The largest 1% of
    active segments by `message_ids` cardinality complete extraction or
    fall back to a relaxed schema (predicate enum + UUID-pattern
    evidence ids + trigger backstop) without grammar-state errors.
9. **Per-claim salvage (D058 / D064).** An extraction response with one
    invalid claim and four valid claims commits four claims with
    `claim_extractions.status='extracted'`,
    `claim_count=4`, `raw_payload.extraction_result_kind='populated'`, and
    the dropped claim recorded in `raw_payload.dropped_claims`. Zero valid
    claims with errors yields `accounted_zero` only when D064 eligibility is
    satisfied; otherwise it remains `status='failed'`.
10. **Empty extraction raw payload (M-F001).**
    `claim_extractions.raw_payload.model_response` is populated for an
    empty extraction.
11. **Claim-count parity (M-F005).**
    `claim_extractions.claim_count` equals
    `(SELECT count(*) FROM claims WHERE extraction_id = ...)`.

End-to-end pilot (gate before full-corpus run):

1. A 50-conversation slice end-to-end produces non-zero claims and
    beliefs, no schema violations, no orphaned `extracting` rows after
    supervisor restart, and `consolidation_progress` reflecting completed
    state.
2. Re-running the pilot is idempotent: no duplicate `claims` or `beliefs`
    rows under unchanged extractor and consolidator versions.

The full-corpus Phase 3 run is gated on the owner per the runbook's Human
Checkpoints; this spec does not authorize starting it.

## Acknowledged limitations

The P024 synthesis closed all binding owner checkpoints (see
`docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md`).
The remaining items are accepted V1 limitations, not open decisions:

1. **Discovery time vs biographic time** (D051). V1 `valid_from` /
   `valid_to` represent discovery time only. Biographic-time qualifiers in
   `object_json` (`since`, `until`, `when`, `by_when`, `born_on`) are not
   lifted into the validity columns. Phase 4+ may add
   `biographic_valid_from` / `biographic_valid_to` columns or a view.
2. **Tool-message recall blind spot** (S-F017 / D038). Tool-role messages
   appear as compact placeholders, so artifact-only facts can be invisible
   to extraction. Predicates most affected: `uses_tool`, `working_on`,
   `project_status_is`. Artifact extraction is a future stage.
3. **Umbrella-overlap parents** (Phase 2 audit). 45 ChatGPT parents (76
   overlapping pairs across 0.57% of the corpus) carry weak per-claim
   grounding. Phase 3 evaluation will flag claims grounded in these
   parents as a known-imprecise category.
4. **Belief embedding into the vector index** (RFC 0011 OQ9). Deferred to
   Phase 5; the SHA256-keyed embedding cache keeps a later add cheap.

These are documented here so future agents do not mistake them for
unresolved P024 questions.

## Cross-cutting properties (inherited)

- Local-only execution; ik-llama on `127.0.0.1` (D020). The
  corpus-reading process has no network egress.
- Raw immutability preserved: `claims` insert-only; `beliefs` allow only
  the named state-transition UPDATEs; `belief_audit` and the active
  columns of `contradictions` append-only.
- Re-derivation is non-destructive (P4): new rows + supersession, never
  in-place UPDATE of evidence or value.
- Privacy carry: segment → claim → belief uses MAX over contributors
  (D019 / D032). Reclassification captures invalidate scope-bound to the
  affected parent conversation (D028 / D032), and the Phase 3 invalidation
  rule above closes affected beliefs.
- Versioning on every derived row (D021):
  `claims.extraction_prompt_version` / `extraction_model_version` /
  `request_profile_version`; `beliefs.prompt_version` / `model_version`
  (consolidator); audit captures both.
- D034 deterministic structured local-LLM calls; D035 health smoke and
  per-attempt failure diagnostics inherited from Phase 2.
- `consolidation_progress` checkpoints make extraction and consolidation
  resumable; the row shape is unchanged from Phase 2.
- `belief_audit` rationale for `claim_extractions` transitions
  (`extracted` → `superseded`) is recovered through a join on
  `captures` (for reclassification) or `consolidation_progress` (for
  re-extraction supervisor events) rather than an inline column on
  `claim_extractions` (S-F016 option a).
