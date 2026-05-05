# Phase 3 Claims and Beliefs Spec Synthesis

Date: 2026-05-05
Synthesizer: claude_opus_4_7
Prompt: P024 — Synthesize Phase 3 Spec Findings
Target artifact: `docs/claims_beliefs.md`

This document accepts, modifies, defers, or rejects each finding in
[PHASE_3_CLAIMS_BELIEFS_SPEC_FINDINGS_LEDGER_2026_05_05.md](PHASE_3_CLAIMS_BELIEFS_SPEC_FINDINGS_LEDGER_2026_05_05.md)
and records the resulting deltas applied to canonical artifacts.

After this synthesis, `docs/claims_beliefs.md` is **build-ready**: the build
prompt (P025) may treat the amended spec as authoritative.

## Inputs read

- The findings ledger and the three independent reviews (Gemini Pro 3.1,
  Codex GPT-5.5, Claude Opus 4.7 fresh context).
- `docs/claims_beliefs.md` (P021 draft).
- `docs/rfcs/0011-phase-3-claims-beliefs.md`.
- `DECISION_LOG.md` (through D047 and the in-flight worktree state).
- `BUILD_PHASES.md`, `ROADMAP.md`, `SPEC.md`.
- `docs/process/multi-agent-review-loop.md`,
  `docs/process/phase-3-agent-runbook.md`.

## Verdict per finding

Severity is preserved from the ledger; this column shows the synthesis
disposition only.

| ID | Severity | Disposition | One-line note |
| --- | --- | --- | --- |
| S-F001 | P0 | accepted_with_modification | `valid_to` is fact-validity only; lifecycle uses `status` + `closed_at` + `superseded_by`; contradictions close prior at `MIN(new_evidence.created_at)`. |
| S-F002 | P0 | accepted | Active claim set = active segment generation × latest `claim_extractions` row per segment; older rows transition to `superseded`; orphan beliefs are rejected by Decision Rule 0. |
| S-F003 | P0 | accepted | Predicates carry a `cardinality_class` (`single_current`/`single_current_per_object`/`multi_current`/`event`); group key extends with `group_object_key` for scoped-current, multi-current, and event predicates. |
| S-F004 | P1 | deferred (with documentation) | V1 `valid_from` / `valid_to` are discovery time; biographic-time lift from `object_json` is deferred. Documented as a known V1 limitation against HUMAN_REQUIREMENTS. |
| S-F005 | P1 | accepted | Belief state changes only flow through a Python transition API (`engram.consolidator.transitions`). Direct SQL UPDATE on `beliefs` is rejected by trigger except via the API's session GUC marker. |
| S-F006 | P1 | accepted | Partial active-belief index becomes UNIQUE on `(subject_normalized, predicate, group_object_key)` while `valid_to IS NULL`. Loser of any race retries through the transition API. |
| S-F007 | P1 | accepted | `subject_normalized` set by trigger via SQL function `engram_normalize_subject(text)`; the same function is the canonical normalizer Python calls. Mirrored onto `claims`. |
| S-F008 | P1 | accepted | Privacy reclassification recompute uses Claude's three-branch decision tree (empty → reject; same value → supersede; different value → close+insert+open contradiction). |
| S-F009 | P1 | accepted_with_modification | `consolidate --rebuild` produces a structurally equivalent active set; test #23 is rewritten to assert structural equivalence rather than ID-stable no-op. |
| S-F010 | P2 | accepted_with_modification | Confidence aggregator becomes mean of contributing claim confidences; MAX is preserved on `belief_audit.score_breakdown` for forensics. |
| S-F011 | P2 | accepted_with_modification | Add a `predicate_vocabulary` lookup table holding the canonical mapping (predicate → stability class, cardinality class, object kind, group-object key list, optional JSON-schema fragment). `claims.predicate` references it via FK. Full JSON-schema enforcement of `object_json` shape stays prompt-side in V1; a per-predicate trigger validates required keys only. |
| S-F012 | P2 | accepted | `claim_extractions.raw_payload` stores raw model output for all completed extractions, including empty ones. |
| S-F013 | P2 | accepted | Add an extractor preflight against the largest 1% of segments by `message_ids` cardinality. If grammar fails, fall back to a relaxed schema that drops the per-segment enum and relies on the trigger backstop, scoped to segments above the cap. |
| S-F014 | P2 | accepted_with_modification | Pre-validate model output in Python (option B). Drop invalid claims with structured diagnostics in `claim_extractions.raw_payload.dropped_claims`. Extraction is `extracted` if at least one valid claim survived; `failed` only on zero successful claims with errors. |
| S-F015 | P2 | accepted | Drop `temporal_overlap_disagreement` example from the spec (no rule emits it). Document the two lineage traversal paths (`superseded_by` for same-value chains; `contradictions.belief_{a,b}_id` for contradiction lineage) plus a test covering both. |
| S-F016 | P3 | accepted | Rename `belief_audit.evidence_episode_ids` to `evidence_message_ids` (no rows exist). Extraction-transition rationale is recovered through the captures + `consolidation_progress` join (option a) and documented. |
| S-F017 | P3 | accepted (documentation only) | Tool-message placeholder limitation is named explicitly as a known recall blind spot for `uses_tool`, `working_on`, `project_status_is`. Artifact extraction stays a future stage. |
| S-F018 | P3 | accepted | `stability_class` is looked up from the predicate vocabulary table per-claim/per-belief; the MODE aggregator is removed. |

All accepted-by-default mechanical fixes (M-F001 through M-F006) are folded in
as part of the deltas above.

## Architecture decisions resolved

These are recorded in `DECISION_LOG.md` as new accepted decisions D048
through D057. Each decision is binding for the build prompt; revisit triggers
are inline in the log.

| Decision | Topic | Source |
| --- | --- | --- |
| D048 | Bitemporal columns are fact-validity only; row lifecycle uses `status` + `closed_at` + `superseded_by`. | A-F001 / S-F001 |
| D049 | Active claim set is the active segment generation joined with the latest active `claim_extractions` row per segment; older rows are superseded. | A-F002 / S-F002 |
| D050 | Predicates carry a cardinality class; scoped-current, multi-current, and event predicates extend the group key with a normalized object discriminator. | A-F003 / S-F003 |
| D051 | V1 belief validity columns represent discovery time; biographic-time lift from `object_json` is deferred to a later phase. | A-F004 / S-F004 |
| D052 | Belief state changes flow through a Python transition API plus a session-GUC-gated trigger. Direct UPDATEs are rejected. | A-F005 / S-F005 |
| D053 | Cross-conversation belief group key is enforced by a UNIQUE partial index on `(subject_normalized, predicate, group_object_key) WHERE valid_to IS NULL`. Concurrent consolidator passes retry on conflict. | A-F006 / S-F006 |
| D054 | Privacy reclassification recompute follows the three-branch decision tree (empty / same-value / different-value). | A-F007 / S-F008 |
| D055 | `consolidate --rebuild` produces a structurally equivalent active belief set; idempotency is asserted at the structural level, not the row-id level. | A-F008 / S-F009 |
| D056 | Belief confidence aggregates as mean over contributing claims; MAX is preserved on the audit breakdown. | A-F009 / S-F010 |
| D057 | Predicate vocabulary is enforced by a `predicate_vocabulary` lookup table referenced from `claims` (and indirectly `beliefs`); LLM-side JSON schema remains primary; required-keys validation backstops per-predicate in the DB. | A-F010 / S-F011 |
| D058 | Extractor response salvage is per-claim: invalid claims are dropped with diagnostics, valid claims commit. | A-F011 / S-F014 |

## Owner checkpoints — resolutions for the spec defaults

The synthesis ships a default for each open checkpoint so the build prompt has
a coherent target. The owner can amend before P025 lands; otherwise these are
treated as accepted.

1. **Predicate vocabulary lock-in.** Default: keep the 30-predicate flat list,
   adjust `talked_about` to a topic-event class, drop `experiencing` in favor
   of `feels` (predicate-emission rule disambiguates), and make `lives_at`
   JSON-only. The list also gains a cardinality class column. Per-stability-
   class enums (RFC 0011 OQ1 option `b`) and probe-then-lock (option `c`) are
   not adopted in V1.
2. **Discovery vs biographic time.** Default: V1 is discovery time. The spec
   adds an explicit *Discovery time vs biographic time* section; future
   phases may add `biographic_valid_from` / `biographic_valid_to` or a view.
3. **Active extraction-version policy.** Default: latest `claim_extractions`
   row per segment (joined through active segment generation). When a new
   extraction at a different `(extraction_prompt_version,
   extraction_model_version)` lands, the prior row transitions to
   `status='superseded'`.
4. **Confidence aggregation.** Default: mean over contributing claims; the
   audit row preserves MAX, MIN, count, and stddev for forensics.
5. **`consolidate --rebuild` semantics.** Default: structural equivalence;
   test #23 is rewritten accordingly.
6. **Pre-Phase-3 adversarial round.** Default: skip; the P022 fan-out review
   round (Gemini Pro 3.1, Codex GPT-5.5, Claude Opus 4.7 fresh context) was
   substantially adversarial.
7. **Targeted re-segmentation of 45 umbrella-overlap parents.** Default:
   `proceed_with_caveats`. Phase 3 evaluation will flag claims grounded in
   those 45 parents as a known-imprecise category.
8. **Belief embedding into the vector index.** Default: deferred to Phase 5.
   The schema does not reserve embedding columns now; SHA256-keyed cache
   makes a later add cheap.
9. **Per-claim salvage on invalid extraction response.** Default: drop bad
   claims with structured diagnostics; salvage the rest (option B).

## Files patched

The build prompt should treat these as authoritative.

- `docs/claims_beliefs.md` — section-level edits for time semantics,
  predicate vocabulary, grouping key, decision rules, transition API,
  rebuild semantics, schema (beliefs, claims, claim_extractions,
  belief_audit, predicate_vocabulary), and tests.
- `DECISION_LOG.md` — D048 through D058 added as accepted decisions.
- `BUILD_PHASES.md` — Phase 3 acceptance criteria block updated to refer to
  the amended spec rules; no structural change.
- `ROADMAP.md` — unchanged. The Step 4C handoff still applies.
- `SPEC.md` — unchanged. The high-level diagram and "what's not in V1"
  blocks are still accurate after these amendments.

In-flight worktree files (`migrations/006_claims_beliefs.sql`,
`src/engram/consolidator.py`, `src/engram/extractor.py`,
`tests/test_phase3_claims_beliefs.py`) are **not** modified by this
synthesis. They were authored against an earlier draft and are diverged from
the amended spec on schema columns (notably `closed_at`, `cardinality_class`,
`group_object_key`, `subject_normalized` mirroring on `claims`,
`predicate_vocabulary`, the renamed audit column, and the active-belief
unique constraint) plus the transition-API code path. The build prompt (P025)
will direct the implementer to bring those files into alignment with the
amended spec rather than the other way around.

## Tests now expected (delta beyond the existing 26)

The amended spec carries the following additional or rewritten acceptance
tests. They are cross-referenced from the implied-tests blocks in the
ledger.

- **Bitemporal close math** (S-F001 / S-F002): same-value supersession
  preserves the prior `valid_to`; contradiction close uses
  `MIN(new_evidence.created_at)`; auto-resolution is reachable on
  non-overlapping intervals.
- **Re-extraction blast radius** (S-F002): a segment with v1 + v2
  `claim_extractions` rows feeds only v2 claims into consolidation; the v1
  row is `status='superseded'`.
- **Scoped-current and multi-current predicate non-conflict** (S-F003):
  two `works_with` claims under the same subject with different objects do
  not produce a contradiction; neither do two `relationship_with` or
  `project_status_is` claims with different scoped objects. Conflicting
  statuses for the same relationship name or project do contradict.
- **Empty re-extraction orphan rejection** (S-F002 / Decision Rule 0): a
  belief whose `claim_ids` no longer match the active claim set is
  closed via `transition_kind='reject'`.
- **Audit enforcement via transition API** (S-F005): direct SQL UPDATE on
  `beliefs` is rejected; transition API succeeds and writes both rows.
- **Concurrent consolidator pass** (S-F006): two parallel consolidator
  invocations on different conversations targeting the same global group
  key produce one active belief; the loser retries cleanly.
- **Subject normalization parity** (S-F007): SQL `engram_normalize_subject`
  output matches Python `engram.consolidator.normalize_subject` over a
  shared fixture set.
- **Partial reclassification recompute** (S-F008): empty surviving set →
  reject; same-value surviving set → supersede; different-value
  surviving set → supersede + open contradiction at
  `detection_kind='reclassification_recompute'`.
- **Rebuild structural equivalence** (S-F009): rebuild #2 produces a
  structurally equivalent active set even with new IDs / `recorded_at`.
- **Claim-count parity** (M-F005): `claim_extractions.claim_count` equals
  the number of inserted `claims` rows.
- **Predicate vocabulary FK** (D057): inserting a claim with a predicate
  not in `predicate_vocabulary` fails.
- **Object-json required keys** (D057): inserting an `object_json` claim
  missing a predicate-required key fails.
- **Tail-segment grammar preflight** (S-F013): top-1% segments by
  `message_ids` cardinality pass extraction or fall back to relaxed
  schema cleanly.
- **Lineage traversal** (S-F015): both `superseded_by` chain and
  `contradictions` lineage are reachable for any closed-then-replaced
  belief.

## Owner-visible deltas to the spec

The following sections of `docs/claims_beliefs.md` were rewritten or
extended during this synthesis. The full edited file is the binding
artifact; this list is for review:

- *Stage A — Claim extraction* — per-segment lifecycle (salvage), empty
  extraction `raw_payload`, response-validation step, predicate
  vocabulary table format extended with cardinality class, predicate
  emission guide.
- *Stage B — Belief consolidation* — grouping key with object
  discriminator, value equality, decision rules including new Decision
  Rule 0 (orphan rejection) and amended same-value / contradiction rules,
  confidence aggregator, transition API, concurrency policy, rebuild
  semantics.
- *Time semantics* — new subsection separating discovery vs biographic
  time; `valid_to` semantics tightened; new `closed_at` column.
- *Schema* — added `predicate_vocabulary` table; added `closed_at`,
  `cardinality_class`, `group_object_key` (computed) on `beliefs`;
  added `subject_normalized` on `claims`; renamed
  `belief_audit.evidence_episode_ids` to `evidence_message_ids`; UNIQUE
  partial index on the active belief group key; tightened transition API.
- *Tests and acceptance criteria* — replacement and additions per the
  list above.
- *Open owner checkpoints* — closed out; remaining items move to
  *Acknowledged limitations* (discovery time, tool-placeholder blind
  spot, umbrella-overlap parents).

## Build readiness

After applying these deltas, `docs/claims_beliefs.md` is build-ready. The
amended spec:

- has no remaining P0 architecture conflicts;
- defines the active claim set, the active belief uniqueness invariant,
  and the close-and-insert math without ambiguity;
- specifies a concrete audit-on-update mechanism (transition API +
  session-GUC marker);
- pins the predicate vocabulary including cardinality classes;
- hands the build prompt a single closed list of acceptance tests.

The remaining V1 limitations (discovery-time-only validity, tool-message
recall blind spot, 45 umbrella-overlap parents grounded weakly) are
**known and documented**, not architectural blockers.

## Next expected marker

`05_BUILD_PROMPT_DRAFT.ready.md` — the build prompt P025 against the
amended spec.
