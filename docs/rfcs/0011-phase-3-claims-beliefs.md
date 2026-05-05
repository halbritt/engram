# RFC 0011: Phase 3 Claims and Bitemporal Beliefs

Status: proposal
Date: 2026-05-05
Context: BUILD_PHASES.md Phase 3 row; D002, D003, D004, D008, D009, D010,
D014, D017, D019, D020, D021, D028, D032, D034, D035, D040, D042; O001,
O007; PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04;
PHASE_2_QWEN27B_UMBRELLA_AB_2026_05_05

This RFC proposes the schema and contracts for Phase 3 — claim extraction
over the active Phase 2 segments, plus bitemporal belief consolidation
with audit and contradictions. It is a design proposal, not an
implementation handoff. Open questions at the bottom are explicitly
unresolved; promotion to a build prompt should follow review and any
DECISION_LOG entries that resolve them.

## Background

Phase 2 produced 11,169 active segments across 7,916 conversations under
`segmenter.v2.d034.enum-ids.tool-placeholders` on Qwen 35B A3B IQ4_XS.
Provenance integrity at the storage layer is clean: 0 cross-conversation,
0 missing-message, 0 unordered active rows. The substrate is ready for
Phase 3 in the structural sense.

Two known imprecisions shape the eval lens but do not block
implementation:

1. **Umbrella-overlap pattern.** ~45 ChatGPT conversations contain
   active "umbrella" segments where the model emitted endpoint-only
   `message_ids` and the expander swept a wide range, sometimes
   swallowing sibling sub-segments. 76 overlapping pairs across 0.57%
   of the corpus. The owner accepted weak claim grounding on these
   parents as a tolerable Phase 3 input rather than gating remediation.
2. **Under-fragmentation risk under alternate models.** The Qwen 27B
   AB confirmed the umbrella mechanism is model-side, not
   prompt-shape, but it also showed Qwen 27B over-merges entire
   conversations into single mega-segments. No production model swap
   is on the table for Phase 3; this is recorded so eval can watch
   for the same shape if Tier 2 model work later changes the
   substrate.

D040 narrows the Phase 3 substrate to the AI-conversation segments
only. Notes, captures, and Obsidian segments are not extracted in
this phase even though the schema reserves room for them.

## Problem

Phase 3 is the first synthesis stage. Once claims and beliefs exist,
ranking, retrieval, and `context_for` start to depend on them. Design
mistakes here propagate into beliefs that downstream work treats as
load-bearing. The architecture has many of the pieces specified at a
high level — V1_ARCHITECTURE_DRAFT lists the belief columns, and
DECISION_LOG entries D003 / D004 / D008 / D010 fix the load-bearing
invariants — but several decisions are not pinned:

- The exact `claims` schema, including how per-claim evidence is
  bound to the supporting messages.
- Whether `beliefs.evidence_ids` is non-empty at every status (this
  RFC proposes yes — strengthening D003).
- Whether `status='accepted'` is reachable in Phase 3 (this RFC
  proposes no — defer to the Phase 4 review queue, addressing O007's
  defensive direction).
- The grouping rule, value-equality rule, and contradiction detection
  algorithm for the consolidator.
- The predicate vocabulary and stability_class assignment rule the
  extractor commits to.
- Whether re-extraction also auto-rebuilds beliefs or whether
  consolidation is a separate operator step.

This RFC proposes a cohesive answer to all of the above and surfaces
the genuinely-open ones for review.

## Proposal

### Stage division

Phase 3 splits into two stages, both implemented in this phase:

- **Stage A — claim extraction.** For each active segment, call the
  local LLM with a deterministic structured prompt; persist 0..N
  `claims` rows with subject / predicate / object / stability_class /
  confidence / evidence_message_ids. Empty extraction is an explicit,
  recorded result (`claim_extractions.status='extracted'`,
  `claim_count=0`), not a failure.
- **Stage B — belief consolidation.** Group claims into bitemporal
  `beliefs` rows. New beliefs default to `candidate`. Contradictions
  close the prior belief's `valid_to` and insert a new row via
  `superseded_by`; `belief_audit` records every state transition;
  conflicts that cannot be auto-ordered land in `contradictions` for
  later review.

The consolidator is deterministic Python in V1 (no LLM call). Its
`prompt_version` / `model_version` columns record the consolidator's
version string so the schema column has consistent semantics with the
extractor.

### Schema

`consolidation_progress` extension: nothing new required — Phase 2's
`error_count` / `last_error` / `position` JSONB shape is reused with
new `stage` values (`extractor`, `consolidator`).

`claim_extractions` (analog of `segment_generations` for extraction):

- `id UUID PK`
- `segment_id UUID NOT NULL REFERENCES segments(id)`
- `generation_id UUID NOT NULL REFERENCES segment_generations(id)`
- `extraction_prompt_version TEXT NOT NULL`
- `extraction_model_version TEXT NOT NULL`
- `request_profile_version TEXT NOT NULL`
- `status TEXT NOT NULL CHECK (status IN
  ('extracting','extracted','failed','superseded'))`
- `claim_count INT NOT NULL DEFAULT 0`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `completed_at TIMESTAMPTZ NULL`
- `raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb` — D035 failure
  diagnostics (`failure_kind`, `last_error`, attempt count, per-attempt
  `max_tokens`, decoded-token counts)
- Partial unique index for active extraction per `(segment_id,
  extraction_prompt_version, extraction_model_version)` WHERE
  `status IN ('extracting','extracted')`.

`claims`:

- `id UUID PK DEFAULT gen_random_uuid()`
- `segment_id UUID NOT NULL REFERENCES segments(id)`
- `generation_id UUID NOT NULL REFERENCES segment_generations(id)`
- `conversation_id UUID NULL REFERENCES conversations(id)` —
  denormalized for filtering; NULL for future note/capture extraction.
- `subject_text TEXT NOT NULL` — pre-canonicalization name. Phase 4
  will add an `entity_id` join column.
- `predicate TEXT NOT NULL` — drawn from a fixed enum the extractor
  prompt commits to (vocabulary TBD; see Open Questions).
- `object_text TEXT NULL`
- `object_json JSONB NULL`
- CHECK exactly one of `object_text` / `object_json` is non-null.
- `stability_class TEXT NOT NULL CHECK (stability_class IN
  ('identity','preference','project_status','goal','task','mood',
  'relationship'))` — D008.
- `confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1)`.
- `evidence_message_ids UUID[] NOT NULL` — subset of the parent
  segment's `message_ids`. INSERT trigger validates membership.
  Allowed to be the full set when the model cannot localize finer.
- `extraction_prompt_version TEXT NOT NULL`
- `extraction_model_version TEXT NOT NULL`
- `request_profile_version TEXT NOT NULL`
- `privacy_tier INT NOT NULL` — copied from parent segment (D019 /
  D032).
- `extracted_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `raw_payload JSONB NOT NULL` — model output incl. rationale.
- Insert-only trigger (block UPDATE and DELETE outright). Re-extraction
  inserts new rows; existing claims are never edited.
- Indexes: `(segment_id)`, `(conversation_id)`,
  `(extraction_prompt_version, extraction_model_version)`, GIN on
  `evidence_message_ids`.

`beliefs`:

- `id UUID PK DEFAULT gen_random_uuid()`
- `subject_text TEXT NOT NULL`
- `predicate TEXT NOT NULL`
- `object_text TEXT NULL`
- `object_json JSONB NULL`
- CHECK exactly one of `object_text` / `object_json` is non-null.
- `valid_from TIMESTAMPTZ NOT NULL`
- `valid_to TIMESTAMPTZ NULL` — NULL = currently valid.
- `observed_at TIMESTAMPTZ NOT NULL` — when supporting evidence was
  observed in the corpus.
- `recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `extracted_at TIMESTAMPTZ NOT NULL`
- `superseded_by UUID NULL REFERENCES beliefs(id)`
- `status TEXT NOT NULL CHECK (status IN
  ('candidate','provisional','accepted','superseded','rejected'))`
- `stability_class TEXT NOT NULL`
- `confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1)`
- `evidence_ids UUID[] NOT NULL` — raw `messages.id`s, non-empty for
  every status (proposed strengthening of D003 — see Proposed
  Decisions).
- `claim_ids UUID[] NOT NULL` — every contributing `claims.id`.
- `prompt_version TEXT NOT NULL` — consolidator version.
- `model_version TEXT NOT NULL` — consolidator version string in V1.
- `privacy_tier INT NOT NULL` — `max` over contributing claims.
- `raw_payload JSONB NOT NULL` — consolidator decision rationale.
- Mutation trigger: block DELETE outright. Allow UPDATE only on
  `valid_to`, `superseded_by`, `status` (with documented allowed
  transitions). Block UPDATE on every other column. Every UPDATE
  must have a corresponding `belief_audit` row in the same
  transaction.
- Indexes: `(subject_text, predicate)`,
  `(subject_text, predicate, valid_to)` partial WHERE
  `valid_to IS NULL` (the future `current_beliefs` view uses this),
  `(status, stability_class)`, GIN on `evidence_ids` and
  `claim_ids`.

`belief_audit`:

- `id UUID PK`
- `belief_id UUID NOT NULL REFERENCES beliefs(id)`
- `transition_kind TEXT NOT NULL CHECK (transition_kind IN
  ('insert','close','supersede','promote','demote','reject',
  'reactivate'))`
- `previous_status TEXT NULL`
- `new_status TEXT NOT NULL`
- `previous_valid_to TIMESTAMPTZ NULL`
- `new_valid_to TIMESTAMPTZ NULL`
- `prompt_version TEXT NOT NULL`
- `model_version TEXT NOT NULL`
- `input_claim_ids UUID[] NULL`
- `evidence_episode_ids UUID[] NOT NULL DEFAULT '{}'`
- `score_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Append-only — no UPDATE, no DELETE.

`contradictions`:

- `id UUID PK`
- `belief_a_id UUID NOT NULL REFERENCES beliefs(id)`
- `belief_b_id UUID NOT NULL REFERENCES beliefs(id)`
- CHECK `belief_a_id <> belief_b_id`.
- `detected_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `detection_kind TEXT NOT NULL` — e.g., `same_subject_predicate`,
  `temporal_overlap_disagreement`.
- `resolution_status TEXT NOT NULL DEFAULT 'open' CHECK
  (resolution_status IN ('open','auto_resolved','human_resolved',
  'irreconcilable'))`
- `resolution_kind TEXT NULL`
- `resolved_at TIMESTAMPTZ NULL`
- `privacy_tier INT NOT NULL`
- `raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb`
- Allow UPDATE only on `resolution_status` / `resolution_kind` /
  `resolved_at`; block DELETE.

### Extractor contract

- D034 deterministic structured request: `stream=false`,
  `temperature=0`, `top_p=1`, `chat_template_kwargs.enable_thinking=false`,
  `response_format={"type":"json_schema",...}`. Parse only
  `choices[0].message.content`. Reject `reasoning_content`-only,
  Markdown-fenced, or schema-invalid responses.
- Single universal prompt for V1 (per O001's "one universal" option).
  Do not split per-stability-class until evidence justifies it.
- Schema constrains:
  - `evidence_message_ids.items` to an enum over the segment's
    actual `message_ids` (D036 echo — prevents hallucinated message
    ids before they reach the validator).
  - `predicate` to an enum over the documented vocabulary.
  - `stability_class` to its enum.
  - `confidence` to `[0, 1]`.
- D035 health smoke before any long extraction run; D035 failure
  diagnostics on every failed `claim_extractions` row.
- Per-segment privacy tier copied to each emitted claim.
- Adaptive shrink is not required: the audit found segment p99
  stored=62 messages, well within the bounded `max_tokens` budget.
  If a segment exceeds budget, fail-closed with a context-budget
  error rather than invent a per-claim chunking strategy.

### Consolidator contract

- Grouping key: `(normalize(subject_text), normalize(predicate))`.
  `normalize` lowercases, trims, collapses whitespace, and strips
  punctuation (exact rule documented). Phase 4's entity
  canonicalization will replace `subject_text` with `entity_id`;
  the consolidator must not pre-canonicalize beyond the documented
  rule so Phase 4 can re-derive cleanly.
- Decision rules:
  - **No existing belief for the group key** → insert a new belief at
    `status='candidate'` with `valid_from = min(observed_at across
    supporting claims)`, `valid_to = NULL`, `evidence_ids = union of
    evidence_message_ids across supporting claims`, `claim_ids =
    supporting claim ids`, `confidence = max claim confidence`
    (alternative aggregators recorded in `prompt_version`).
  - **Existing belief, same value** (`object_text` / `object_json`
    byte-equal under normalization) → close-and-insert: insert a fresh
    row with merged provenance, set the prior row's `superseded_by`
    to the new id, write `belief_audit` with
    `transition_kind='supersede'`. No in-place evidence growth.
  - **Existing belief, different value** → contradiction. Close the
    prior belief, insert a new belief at `status='candidate'`, insert
    a `contradictions` row at `resolution_status='open'`. Auto-resolve
    by temporal ordering when both rows have non-overlapping
    `observed_at`; record as `auto_resolved` with `resolution_kind`.
    Pure disagreements stay `open` for the Phase 4 review queue.
- Every state transition writes a `belief_audit` row in the same
  transaction (D010).

### Cross-cutting properties (inherited from Phase 1 / 2)

- Local-only execution; ik-llama on `127.0.0.1` (D020).
- Raw immutability preserved; `claims` insert-only; `beliefs` allow
  only the named state-transition UPDATEs; `belief_audit` and the
  active columns of `contradictions` append-only.
- Re-derivation is non-destructive (P4): new rows + supersession,
  never in-place UPDATE of evidence or value.
- Privacy carry: segment → claim → belief uses `max` over
  contributors (D019 / D032). Reclassification captures invalidate
  scoped to the affected parent conversation (D028 / D032).
- Versioning on every derived row (D021):
  `extraction_prompt_version` / `extraction_model_version` /
  `request_profile_version` for claims; `prompt_version` /
  `model_version` for beliefs; consolidator version on
  `belief_audit` rows.
- D034 deterministic structured local-LLM calls; D035 health smoke
  and per-attempt failure diagnostics.
- `consolidation_progress` checkpoints make extraction and
  consolidation resumable; reuses Phase 2's row shape.

## Proposed Decisions (require DECISION_LOG entries before build)

The following are not currently in DECISION_LOG and propagate into
load-bearing schema. They should be promoted into accepted decisions
before a build prompt is written.

1. **Strengthen D003 to require non-empty `evidence_ids` at every
   status.** D003 currently requires it on `accepted` beliefs. The
   three-tier separation (D002) forbids belief-without-evidence in
   principle; a `candidate` belief without raw evidence has nothing
   to be a candidate of. Strengthening to "every belief row carries
   at least one raw `messages.id`" makes the constraint enforceable
   at the schema level (CHECK on `cardinality(evidence_ids) > 0`)
   and removes a class of corner cases from Phase 4's review queue.

2. **No auto-promotion to `status='accepted'` in Phase 3.** New
   beliefs land at `candidate`. Promotion to `accepted` requires the
   Phase 4 HITL review queue. Rationale: HUMAN_REQUIREMENTS' refusal
   of false precision says confidence cannot be flattened to "looks
   confident enough"; D006 keeps wiki / public-facing surfaces gated
   on review; O007 asks which belief types must never auto-promote
   and answers "all of them, in V1" cleanly. Phase 4 may revisit per
   stability_class.

3. **Re-extraction does not auto-rebuild beliefs.** Bumping
   `extraction_prompt_version` inserts new claims; the consolidator's
   next run picks them up alongside existing claims. Re-consolidation
   under a new consolidator version is a separate operator step. This
   keeps the two stages independently re-runnable and makes blast
   radius of a prompt bump bounded.

4. **Predicate vocabulary is a fixed enum committed in the extractor
   schema.** The exact vocabulary is the largest unresolved design
   question (see Open Questions). The principle is that extraction
   schema constrains it before generation — the gold set is meaningful
   only against a stable predicate vocabulary.

5. **Phase 3 substrate is AI-conversation segments only.** Inherits
   D040. Note / capture / Obsidian extraction is a follow-up phase
   prompt; nothing in Phase 3 populates `claims.conversation_id IS
   NULL`.

## Open Questions

These need answers before the build prompt lands. Some require a
review pass; some need the owner's call.

1. **Predicate vocabulary.** What is the V1 enum? Candidate
   directions: (a) a small flat list (~30 predicates) covering identity,
   preference, project_status, goal, task, mood, relationship without
   per-class breakdown; (b) a per-stability-class vocabulary; (c) start
   with the predicates implied by `HUMAN_REQUIREMENTS.md`'s domain
   coverage and let the gold set drive growth. Affects extraction
   prompt design and gold-set authoring (Step 5).

2. **Object representation.** When does the extractor emit
   `object_text` vs `object_json`? Proposed rule: `object_text` for
   simple value-of-a-field facts (e.g., "user lives at X"),
   `object_json` for structured facts with sub-attributes (e.g., dose
   + frequency + side-effects on a medication). Needs a worked example
   set.

3. **Normalization rule for grouping.** Is "Lowercase + trim +
   collapse whitespace + strip punctuation" enough? It misses
   pluralization, possessives, alias resolution, and case inflection.
   Phase 4 brings entity canonicalization that subsumes most of this;
   the V1 normalization should be just enough to not produce duplicate
   chains for trivial spelling variation, and explicitly *not* good
   enough to look like canonicalization.

4. **Value-equality across object_text / object_json.** When the same
   real fact arrives once as text and once as JSON, are they equal?
   Proposed answer: never auto-merge across the column boundary in
   V1; document as a known duplication that Phase 4 can clean. But
   this needs validation against the corpus.

5. **Auto-resolution heuristics for contradictions.** Pure temporal
   ordering (no overlap → newer supersedes) is the safe default. What
   else? Confidence-weighted? Stability_class-conditional (identity
   beliefs auto-resolve more conservatively than mood beliefs)?
   Proposed: temporal-only in V1; everything else stays
   `resolution_status='open'`.

6. **Aggregator for `confidence` on a merged belief.** Max across
   supporting claims is simple and defensible. Mean weighted by
   recency, or per-stability-class weighting, are alternatives.
   Should be reviewable before lock-in.

7. **`observed_at` derivation.** Defined as "when supporting evidence
   was observed in the corpus." Operationally: max
   `messages.created_at` among `evidence_ids`? Median? The first
   message's timestamp? Affects bitemporal correctness on the close-
   and-insert sequence.

8. **Consolidator parallelism.** Stage B is deterministic Python; can
   it run in parallel with Stage A on a per-conversation basis, or
   does it need to wait for the full extractor pass before
   consolidating? Proposed: per-conversation pipeline so retrieval-
   visible beliefs grow incrementally. Alternative: hold consolidation
   until the extractor finishes corpus-wide so cross-conversation
   beliefs see all evidence at once.

9. **Belief embedding into the vector index.** D009 says "topic
   segments + accepted beliefs" both embed. Phase 3 produces no
   accepted beliefs, so no embedding work is in scope. But: does the
   schema reserve embedding columns now (analogous to the Phase 2
   `notes`/`capture` columns) or wait for Phase 4 / 5? Proposed:
   wait — the embedder already supports SHA256-keyed content; adding
   beliefs is a small follow-up.

10. **Pre-Phase-3 adversarial review.** D026 ran a pre-Phase-2
    adversarial round that produced D027–D033. Phase 3 is the first
    synthesis stage and arguably the higher-stakes one for the
    "model survives the corpus" property. Should the same gate apply?
    If yes, this RFC moves from `proposal` → `under_review` until the
    round runs.

## Risks

- **Umbrella substrate.** Claims grounded in umbrella segments will
  cite evidence that spans multiple semantic topics. This degrades
  per-claim grounding precision but does not break the schema; gold-
  set evaluation will quantify the cost.
- **Predicate-enum churn.** The first version of the predicate
  vocabulary will be wrong. Re-extraction is non-destructive, so
  cost is bounded, but every churn forces re-extraction over the
  full corpus. Consider letting the prompt emit `predicate` freely
  in a first probe pass, then deriving the enum from observed
  outputs before locking the schema.
- **Consolidator complexity creep.** The decision rules above are
  small. Adding heuristics (currentness scoring, stability_class
  weighting, cross-conversation entity guess) will pull in Phase 4
  / 5 work prematurely. Resist.
- **Auto-promotion drift.** A future "let's auto-accept high-
  confidence identity beliefs" proposal undermines the HITL property.
  Should be an explicit DECISION_LOG entry, not a prompt-level
  decision.
- **Belief audit volume.** Every state transition writes a row.
  Storage is cheap, but indexes and join cost grow. Document this as
  expected; revisit only if Phase 4 / 5 retrieval EXPLAINs show it
  matters.

## Promotion Path

If accepted:

1. Open DECISION_LOG entries for the five Proposed Decisions above
   (D043 strengthen D003, D044 no auto-promotion in Phase 3, D045
   re-extraction non-rebuilding, D046 fixed predicate enum in
   extractor schema, D047 Phase 3 substrate scope reaffirms D040).
   Numbering is illustrative; assign at acceptance time.
2. Write Open Questions answers into the same DECISION_LOG entries
   or follow-up RFCs as appropriate.
3. Update BUILD_PHASES.md Phase 3 row with any spec deltas (the
   current row is consistent with this proposal).
4. Optionally schedule a pre-Phase-3 adversarial round (the D026
   analog) before implementation. If skipped, record the decision.
5. Write the build prompt — `prompts/phase_3_claims_beliefs.md` —
   that references this RFC, the new DECISION_LOG entries, and any
   adversarial-round synthesis.

## Non-goals

This RFC does not address:

- Entity canonicalization, `entities` / `entity_edges`, `entity_id`
  on claims/beliefs (Phase 4).
- `current_beliefs` materialized view (Phase 4).
- Belief review queue, auto-promotion ergonomics, correction-as-
  capture UX (Phase 4 / D017).
- Belief text embedding and vector-index addition (Phase 5).
- `context_for`, ranking, MCP, `context_feedback` (Phase 5).
- Adversarial sweeps, falsification probes (F004 — deferred).
- Hypotheses, failure-pattern detection, causal-link mining,
  goal-progress inference (D014 — cut from V1).
- Note / capture / Obsidian extraction (D040; future phase prompt).
- LLM-mediated belief consolidation. V1 consolidator is deterministic
  Python; LLM tiebreak is later work.
- Cross-encoder LLM reranker (F003 — deferred).
