# 04_SPEC_SYNTHESIS.ready

Prompt: P024 — Synthesize Phase 3 Spec Findings
Model / agent: claude_opus_4_7 (Synthesis owner)
Started:   2026-05-05T20:30Z
Completed: 2026-05-05T21:10Z

## Files written or modified

- `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md`
  — new synthesis document. Per-finding dispositions for S-F001 through
  S-F018, owner-checkpoint resolutions, summary of patches applied, and
  an explicit build-readiness statement.
- `docs/claims_beliefs.md` — amended in place. Section-level edits to
  Stage A lifecycle (per-claim salvage, raw payload preservation),
  Predicate vocabulary (cardinality classes, emission guide,
  `experiencing` removed, `lives_at` JSON-only), Object representation,
  Time semantics (fact-validity vs lifecycle, new `closed_at`,
  Discovery vs biographic time subsection), Privacy reclassification
  recompute decision tree, Stage B Grouping key (object discriminator),
  Decision rules (Rule 0 orphan rejection, amended Rule 2 / Rule 3,
  cardinality-class-aware contradiction firing), Confidence aggregator
  (mean), Belief transition API, Re-derivation behavior (active claim
  set, structural-equivalence rebuild), Consolidator parallelism
  (UNIQUE partial index), Status transitions, Schema (new
  `predicate_vocabulary` table; `closed_at`, `cardinality_class`,
  `group_object_key`, mirrored `subject_normalized` on `claims`,
  renamed `belief_audit.evidence_message_ids`, `request_uuid`,
  UNIQUE partial belief index, contradiction `detection_kind` cleanup),
  Acceptance tests (revised #6/#7/#19–#24, new #27–#37), Acknowledged
  limitations (replaces Open owner checkpoints).
- `DECISION_LOG.md` — added D048–D058 (eleven new accepted decisions
  covering fact-validity-only `valid_to`, active claim set, predicate
  cardinality classes, discovery-time V1, transition API, UNIQUE
  active-belief index, reclassification recompute tree, rebuild
  structural equivalence, mean confidence, predicate vocabulary table,
  per-claim salvage).
- `BUILD_PHASES.md` — Phase 3 *Key tables / migrations* and *Acceptance
  criteria* blocks rewritten to reference the amended spec. No phase
  reordering.
- `docs/reviews/phase3/markers/04_SPEC_SYNTHESIS.ready.md` — this
  marker.

## Files explicitly NOT modified

- `docs/rfcs/0011-phase-3-claims-beliefs.md` — kept as historical
  proposal context per task constraints.
- `migrations/006_claims_beliefs.sql`, `src/engram/extractor.py`,
  `src/engram/consolidator.py`, `tests/test_phase3_claims_beliefs.py` —
  in-flight worktree files authored against an earlier draft. They
  diverge from the amended spec on schema columns and the transition
  API. The build prompt (P025) will direct the implementer to bring
  these into alignment.
- `ROADMAP.md` and `SPEC.md` — unchanged. The Step 4C handoff and the
  high-level architecture diagram are still accurate after these
  amendments.

## Per-finding disposition

| ID | Disposition |
| --- | --- |
| S-F001 | accepted_with_modification (D048) |
| S-F002 | accepted (D049 + Decision Rule 0) |
| S-F003 | accepted (D050) |
| S-F004 | deferred with explicit V1 documentation (D051) |
| S-F005 | accepted (D052 transition API) |
| S-F006 | accepted (D053 UNIQUE partial index) |
| S-F007 | accepted (`engram_normalize_subject` SQL function + Python parity) |
| S-F008 | accepted (D054 three-branch decision tree) |
| S-F009 | accepted_with_modification (D055 structural equivalence) |
| S-F010 | accepted_with_modification (D056 mean) |
| S-F011 | accepted_with_modification (D057 vocabulary table) |
| S-F012 | accepted (raw payload always stored) |
| S-F013 | accepted (preflight + relaxed-schema fallback) |
| S-F014 | accepted_with_modification (D058 per-claim salvage option B) |
| S-F015 | accepted (drop unused detection_kind, document two traversal paths) |
| S-F016 | accepted (rename to evidence_message_ids; option a rationale recovery) |
| S-F017 | accepted as documentation only |
| S-F018 | accepted (predicate-pinned lookup, MODE removed) |

All accepted-by-default mechanical fixes (M-F001 through M-F006) are
folded into the section edits above.

## Verification performed

- Read the findings ledger and all three reviews end-to-end.
- Read the existing spec, RFC 0011, the working DECISION_LOG (with the
  uncommitted D043–D047 rows), BUILD_PHASES, ROADMAP, SPEC, and the
  process docs.
- Ran `git status --short` before and during edits to confirm I am only
  touching files this prompt owns. Pre-existing modifications to
  `DECISION_LOG.md`, `docs/README.md`, `scripts/phase3_tmux_agents.sh`,
  `src/engram/cli.py`, `tests/conftest.py`, and the migration rename
  remain untouched.
- Decision IDs D048–D058 do not collide with any existing IDs in the
  log.
- Marker filename matches the runbook's expected step-4 marker.

## Build readiness

`docs/claims_beliefs.md` is build-ready after this synthesis. There are
no remaining P0 architecture conflicts; all P1 findings are resolved or
explicitly deferred with documentation; P2/P3 findings are folded in.
The remaining limitations (discovery-time-only validity, tool-message
recall blind spot, 45 umbrella-overlap parents) are acknowledged in the
spec, not open decisions.

## Next expected marker

`05_BUILD_PROMPT_DRAFT.ready.md` — the build prompt P025 against the
amended spec. Per `docs/process/multi-agent-review-loop.md`, the build
prompt should run in a fresh context window so the synthesis debate
does not pollute the implementer's attention.
