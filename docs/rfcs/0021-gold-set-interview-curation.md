<a id="rfc-0021"></a>
# RFC 0021: Gold-Set Interview Curation

| Field | Value |
|-------|-------|
| RFC | 0021 |
| Title | Gold-Set Interview Curation |
| Status | accepted |
| Implementation | partial |
| Date | 2026-05-07 |
| Context | ROADMAP Step 5 (gold-set authoring); HUMAN_REQUIREMENTS § "the eval gold set is the actual specification"; BUILD_PHASES Phase 3 follow-on row; D016, D040, D044, D052, D057, D069, D073, D077, D078, D079, F010, O008; RFC 0011 §§ Stage A / Stage B; RFC 0017 prompt-template versioning; RFC 0018 § Promotion Path step 4 (cascade reviewer scheduled post-Step-5); RFC 0025 phase-scoped command surface; RFC 0027 web UI handoff; `migrations/006_claims_beliefs.sql:131` (`claims`); `migrations/006_claims_beliefs.sql:178` (`beliefs`) |
| Synthesis | docs/reviews/rfc0021/RFC_0021_GOLD_SET_SYNTHESIS.md |

Decision refs:
  - D016
  - D040
  - D044
  - D052
  - D057
  - D069
  - D073
  - D077
  - D078
  - D079
  - F010
  - O008

Review refs:
  - docs/reviews/rfc0021-rerun-2026-05-13/RFC_0021_GOLD_SET_REVIEW_codex.md
  - docs/reviews/rfc0021-rerun-2026-05-13/RFC_0021_GOLD_SET_REVIEW_claude.md
  - docs/reviews/rfc0021-rerun-2026-05-13/RFC_0021_GOLD_SET_REVIEW_gemini.md

Phase refs:
  - PHASE-0003-FOLLOWON

This accepted RFC defines an **agent-driven interview loop** that samples claims and
beliefs from the local corpus, asks the user one structured question at a time,
and stores the user's verdicts in an append-only local table. The accumulated
verdicts function as a continuously-curated gold set that never leaves the
machine. D079 is the binding project decision; this document is the
implementation contract and provenance for that decision.

The current implementation is partial but real: migrations 010, 011, and 013
create the local storage used by the CLI and the RFC 0027 web UI, and
`engram phase3 interview` exposes the v1 operator surface. This RFC still does
not promote gold labels into a hard gate, does not change the existing claim or
belief schemas, and does not authorize any remote model or pipeline dependency.
It overlaps with open question O008 ("eval gold-set authorship model") and does
not replace the `GOLD_SET_TEMPLATE` Step 5 deliverable; it complements that
template as a continuous extension surface.

## Background

`HUMAN_REQUIREMENTS.md` § "the eval gold set is the actual specification"
makes the gold set load-bearing: principles describe what the system should
do, but only the gold set defines what good looks like. D016 commits Engram
to running the gold set against the consolidated V1 corpus and treating
prompt/model re-extraction cycles as the convergence loop. D040 defers
authoring until claims and beliefs exist; that gate is now satisfied —
migrations 006 and 007 are in place, claims and beliefs land routinely under
Phase 3.

`HUMAN_REQUIREMENTS.md` § "gold-set authoring is the single most irreplaceable
human contribution" makes the user the only valid source for `expected_facts`.
A naive interpretation — "sit down once and write 25–50 entries" — has two
problems for a long-running personal-memory system:

1. **Coverage is bounded by what the user remembers to ask about** at the
   moment of authoring. Real evaluative power comes from questions the user
   does not pre-stage but recognizes as right-or-wrong when shown a candidate.
2. **The corpus drifts.** New beliefs land continuously; stability classes
   shift; superseding edges form. A static gold set written in May 2026
   degrades in coverage relative to a corpus that keeps growing.

The gold set itself **must not** live in the repo. It cites real
people, places, projects, and timestamps from the user's life. Storing
verdicts locally — alongside the claims and beliefs they describe — keeps the
substrate symmetric: raw evidence, derived claims, derived beliefs, and
derived gold-set labels all live in the same Postgres instance, all carry
provenance, none cross the machine boundary.

`context_feedback` (HUMAN_REQUIREMENTS § "context_feedback is the eval set
extending itself in production") is the closest existing concept: every
in-product annotation becomes a candidate gold-set entry. This RFC proposes
the **dual** of that loop — an explicit, user-initiated interview pass that
samples from existing claims/beliefs rather than waiting for retrieval to
surface them.

## Problem

How do we let the user continuously author and re-author gold-set verdicts
against the live local corpus, without:

- requiring batch reauthoring sessions;
- letting raw user-life content escape the machine;
- re-introducing the "manually review every belief" failure mode that
  HUMAN_REQUIREMENTS § adversarial review explicitly rejects;
- conflating user verdicts with derived `claim_audits` / `belief_audit` /
  `contradictions` rows (each of which already has a defined producer).

## Proposal

### Shape

An **interview agent** running locally drives a CLI loop, surfaced under the
phase-scoped command namespace introduced in RFC 0025 (D078):

```
$ engram phase3 interview start --n 10
[1/10] Sampled belief b-7f3a... "user works at Acme Corp" (project_status, accepted, conf 0.87)
       Evidence: 3 messages, 2024-11-12 → 2025-08-04 (range 9 months).
       Q: Is this currently true?
       [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later] >
       Optional rationale [Enter to skip rationale]: _
```

Each interview turn is a single `(claim_id | belief_id, target-version stamp,
prompt, verdict, rationale, asked_at, answered_at)` tuple committed to a new
append-only local table. The agent never modifies the underlying claim or
belief; verdicts are derived data that joins onto existing IDs.

### Storage

Migration `010_gold_labels.sql` adds the parent session table, the labels
table, the strata and verdict vocabularies, and three `gold_labels` triggers:
append-only, parent-target validation, and privacy-tier carry. Migration
`011_gold_label_session_targets.sql` then materializes the selected target
order for resume/web rendering, and migration
`013_interview_active_learning_state.sql` adds local active-learning opt-in
events plus selected-target metadata. The session and label tables land in a
single transaction so the NOT NULL FK on `gold_labels.session_id` is
well-defined from the start (matches the `006_claims_beliefs.sql` precedent).

```
gold_label_sessions
  session_id           UUID PRIMARY KEY
  seed                 INT NOT NULL
  sampler_id           TEXT NOT NULL
  sampler_version      TEXT NOT NULL
  strata_weights       JSONB NOT NULL
  started_at           TIMESTAMPTZ NOT NULL
  completed_at         TIMESTAMPTZ NULL
  operator_note        TEXT NULL
```

The session table is load-bearing: without it, `engram phase3 interview
resume`, `list-sessions`, and the worked example below are unimplementable.
The selected target order is anchored by `gold_label_session_targets`; the
`candidate_pool_snapshot_id` is only an opaque session-instance tag in the
current schema, not a replayable candidate-pool snapshot.

```
gold_labels
  id                              UUID PRIMARY KEY
  session_id                      UUID NOT NULL REFERENCES gold_label_sessions(session_id)
  target_kind                     TEXT NOT NULL CHECK (target_kind IN ('claim','belief'))
  target_id                       UUID NOT NULL

  -- Typed target-version stamp. Exactly one prompt/model pair is populated,
  -- selected by target_kind. For claims, request_profile_version mirrors the
  -- claims column. For beliefs, request_profile_version is interview-side
  -- metadata because beliefs/belief_audit have no canonical request-profile
  -- column in the current schema.
  extraction_prompt_version       TEXT NULL
  extraction_model_version        TEXT NULL
  consolidation_prompt_version    TEXT NULL
  consolidation_model_version     TEXT NULL
  request_profile_version         TEXT NOT NULL

  prompt_text                     TEXT NOT NULL
  prompt_template_version         TEXT NOT NULL  -- {area}.v{N}.{date_or_decision}.{descriptor} (RFC 0017)
  prompt_template_path            TEXT NOT NULL  -- prompts/interview/<id>_v{N}.md
  evidence_excerpt                TEXT NULL      -- exported only for rows inside the privacy ceiling

  verdict                         TEXT NOT NULL REFERENCES gold_label_verdict_vocabulary(verdict)
  rationale                       TEXT NULL      -- capped at 2000 chars at the application layer

  -- Typed strata (replaces sampler_strata_key JSONB; vocabulary-backed by convention).
  stability_class                 TEXT NOT NULL
  conf_band                       TEXT NOT NULL
  recency_band                    TEXT NOT NULL
  belief_status                   TEXT NULL
  strata_extra                    JSONB NOT NULL DEFAULT '{}'::jsonb

  -- Session/sampler stamps. candidate_pool_snapshot_id is not a replayable pool.
  candidate_pool_snapshot_id      UUID NOT NULL
  active_learning_signal_version  TEXT NULL      -- NULL when no active signal is set

  sampler_id                      TEXT NOT NULL
  sampler_version                 TEXT NOT NULL
  asked_at                        TIMESTAMPTZ NOT NULL
  answered_at                     TIMESTAMPTZ NOT NULL
  privacy_tier                    INT NOT NULL   -- carried from target row by trigger
```

Constraints worth naming explicitly:

- `chk_gold_labels_version_triple` — `target_kind = 'claim'` requires the
  extraction prompt/model pair populated and the consolidation columns NULL;
  `target_kind = 'belief'` requires the consolidation prompt/model pair
  populated and the extraction columns NULL. `request_profile_version` is
  required in both shapes; for belief rows it versions the interview/sampler
  contract, not a belief-side request profile.
- `chk_gold_labels_template_path_matches_version` — best-effort CHECK that
  the version embedded in `prompt_template_path` matches
  `prompt_template_version`; kept lightweight (substring sanity check) so the
  cost is negligible. It is not a hash or a proof that the prompt file content
  matches the version.
- `idx_gold_labels_claim_triple` — btree on `(target_id, extraction_prompt_version,
  extraction_model_version, request_profile_version)` `WHERE target_kind = 'claim'`.
- `idx_gold_labels_belief_triple` — btree on `(target_id, consolidation_prompt_version,
  consolidation_model_version, request_profile_version)` `WHERE target_kind = 'belief'`.
  The third column groups label rows by the interview request profile; it does
  not join to a canonical `belief_audit.request_profile_version` column.

Migration 010 triggers:

- `fn_gold_labels_append_only` — `BEFORE UPDATE OR DELETE` raising `P0001`.
  Append-only is enforced at the schema layer, not by policy; later verdicts
  on the same target produce new rows. Re-derivation of "current verdict
  per target" is `current_gold_label` (a plain view; see § Promotion path).
- `fn_gold_labels_carry_privacy_tier` — `BEFORE INSERT` copies
  `privacy_tier` from the parent claim or belief at row creation time and
  refuses any operator-supplied tier that disagrees. For future
  multi-source rendering (e.g. contradiction-mode questions surfacing two
  beliefs at once), the carry rule is `privacy_tier = max(tiers across all
  surfaced inputs)`.
- `fn_gold_labels_validate_target` — `BEFORE INSERT` resolves `target_id`
  against the right parent table per `target_kind` (`claim` →
  `claims`, `belief` → `beliefs`), refusing dangling references. This
  mirrors the polymorphic mutation guard on `contradictions` and is what
  makes the `(target_kind, target_id)` shape safe.

There is intentionally no `fn_gold_labels_block_synthetic_audit_input` trigger
in the current schema. SQL cannot detect "gold-label-derived synthetic claim"
without a source/origin discriminator on `claims` or a separate synthetic-claim
table. D044 is therefore enforced in v1 by the gold-label code path: it records
labels only, does not synthesize claims, and must not call
`engram.consolidator.transitions`. If a future RFC adds label-derived claims,
it must first add a source/origin shape that a SQL guard can inspect.

Migration 011 adds the selected-order table used by CLI resume and RFC 0027
web rendering:

```
gold_label_session_targets
  session_id                      UUID NOT NULL REFERENCES gold_label_sessions(session_id)
  idx                             INT NOT NULL
  target_kind                     TEXT NOT NULL CHECK (target_kind IN ('claim','belief'))
  target_id                       UUID NOT NULL
  candidate_pool_snapshot_id      UUID NOT NULL
  extraction_prompt_version       TEXT NULL
  extraction_model_version        TEXT NULL
  consolidation_prompt_version    TEXT NULL
  consolidation_model_version     TEXT NULL
  request_profile_version         TEXT NOT NULL
  stability_class                 TEXT NOT NULL
  conf_band                       TEXT NOT NULL
  recency_band                    TEXT NOT NULL
  belief_status                   TEXT NULL
  inserted_at                     TIMESTAMPTZ NOT NULL
  active_learning_signal_version  TEXT NULL
  confidence                      FLOAT NULL
  observed_at                     TIMESTAMPTZ NULL
  PRIMARY KEY (session_id, idx)
```

This table materializes the sampled order only. It makes an opened session
resumable and renderable without re-sampling, but it does not record the full
candidate pool, the pre-shuffle ordinal, cooldown eligibility for rejected
members, or reviewer scores. Full pool replay would require a separate
candidate-pool snapshot table and a stable `ORDER BY` before seeded
randomization.

Lookup tables seeded by the migration:

- `gold_label_verdict_vocabulary (verdict TEXT PRIMARY KEY, gloss TEXT NOT NULL)` —
  parallel to RFC 0018's `audit_reason_vocabulary` (D073). v1 seeds:

  | Verdict | Gloss |
  |---|---|
  | `true` | claim/belief is correct about the world |
  | `false` | claim/belief is wrong about the world |
  | `stale` | was true at evidence time, no longer true |
  | `unsupported` | evidence does not establish claim, regardless of world truth |
  | `unsure` | user cannot rule |
  | `skip` | user advances without ruling (cooldown-free; see § Cooldowns) |

  These six states are the v1 vocabulary. There is no current eight-verdict
  contract; adding states requires a follow-up RFC and migration. `false` and
  `unsupported` are deliberately separate glosses even though world-truth and
  evidence-grounding can overlap in real life. In v1 the operator chooses the
  primary failure mode; a mechanical cross-walk to audit reasons remains
  deferred.

  Cross-walk to `audit_reason_vocabulary` is deferred to v1.5 (synthesis-
  carried risk: Step 9 consumers may need a mechanical mapping between
  `false` and the cascade reviewer's "fact-correction" reason; gloss-now,
  mapping-later is the trade we accept).

- `gold_label_strata_vocabulary (stratum_kind TEXT, key TEXT, display TEXT,
  PRIMARY KEY (stratum_kind, key))` — seeded with v1 strata keys for
  `stability_class`, `conf_band`, `recency_band`, `belief_status`. Pattern
  matches `predicate_vocabulary` (D057), but migration 010 does not attach
  FK constraints or a validation trigger from `gold_labels` to this vocabulary.
  Current enforcement is application-side and by operator convention. If Step 9
  needs hard schema validation, a follow-up migration should add
  `fn_gold_labels_validate_strata` or separate per-dimension vocabulary FKs.
  `strata_extra JSONB` on the label row holds non-canonical extension keys that
  have not yet been promoted into the vocabulary.

The table is not a `gold_entries` table — it does not author the
`expected_facts` shape consumed by Step 9 evals. Promotion of label clusters
into formal gold-set entries is a downstream step (see § Open questions).

### Sampler

Random sampling burns interviews on easy cases and clusters them by whatever
the corpus happens to over-produce. The implemented v1 sampler is
**strata-aware, cooldown-aware, and version-stamped**:

- **Source view.** The sampler reads `current_beliefs` (D077) by default
  so status filtering excludes `superseded` and `rejected` rows. Operator
  override is `engram phase3 interview start --include-superseded` for
  adversarial sweeps.
- **Strata.** Cross product of `stability_class` × confidence band ×
  recency band. For beliefs, also record `belief_status`. Strata are stored as
  the typed columns described in § Storage. The current v1 sampler supports
  operator filters over these fields and stamps them on labels/session targets;
  it does not yet reweight draws to over-sample under-labeled strata, and it
  does not schema-validate the label columns against
  `gold_label_strata_vocabulary`.
- **Active-learning signal (opt-in; selection bias deferred).** Operators can
  enable a local signal with
  `engram phase3 interview enable-active-learning --signal-version <v>`. The
  latest signal value is stamped onto later session targets and labels as
  `active_learning_signal_version`. The current v1 sampler does not yet use
  RFC 0018 reviewer scores or prior-label gaps to change sample ordering. Any
  future selection bias must remain off by default, version-stamped, and backed
  by an explicit project decision once reviewer/audit data exists at useful
  volume.
- **Cooldowns.** A target answered in the last N days is suppressed for
  that window. Defaults per `(target, any non-skip verdict)` are tunable via
  `ENGRAM_GOLD_COOLDOWN_<STABILITY_CLASS>_DAYS` env vars (per the Python
  coding standard, RFC 0012):

  | Stability class | V1 `(target, any non-skip verdict)` cooldown |
  |---|---|
  | `mood` | 3d |
  | `task` | 7d |
  | `goal` | 14d |
  | `preference` | 30d |
  | `project_status` | 30d |
  | `relationship` | 60d |
  | `identity` | 90d |

  `skip` is **cooldown-free** (see § Skip semantics); the cooldown rule applies
  only to `true | false | stale | unsupported | unsure`. The "half-window per
  `(target, verdict)`" policy from the earlier design is not implemented in v1;
  current code uses the latest non-skip label for `(target_kind, target_id)`.
  Empirical tuning is expected post-v1.
- **Determinism / reproducibility.** Each emitted question is stamped with
  `(seed, sampler_id, sampler_version, strata_weights)`, a
  `candidate_pool_snapshot_id`, and `active_learning_signal_version` when set.
  In the current implementation the snapshot id is a UUID generated per
  sampler call; it groups the rows emitted from that call but is not a
  content-addressed or replayable pool snapshot. Re-rendering/resume stability
  comes from `gold_label_session_targets`, which stores the selected target
  order at session creation. Reconstructing the full candidate pool later is
  not supported by the current schema.

V1 sampler is the simplest version that respects strata filters, target
cooldowns, re-ask caps, active-learning stamps, and selected-order
materialization. Deeper introspection (`inspect-strata-balance`, `dry-run`),
true under-labeled-stratum reweighting, and replayable candidate-pool capture
are deferred until operators have evidence that they are needed.

#### Skip semantics

`skip` advances the cursor and inserts a row with `verdict = 'skip'`. The
prompt labels it `[skip - ask later]` to make the contract explicit: the
target re-surfaces on the next session because skip rows do not gate the
cooldown calculation. A separate `never_ask` blocklist surface is deferred
to v1.5; for v1, repeated skip simply re-surfaces.

### Interview agent

A local renderer/agent reads structured rows and renders each sampled target
into a question using a versioned prompt template. It does not need a remote
service or a live LLM call:

- For a claim: "Is this an accurate paraphrase of your situation at the
  time of the cited evidence?" + the canonical paraphrase. If a 1-line
  evidence excerpt is rendered, it is stored on the row in
  `evidence_excerpt` (a separate column from `prompt_text`) so the v1 export
  can include it only for rows inside the requested privacy ceiling.
- For a belief: "Is this currently true?" / "Was this true between
  `valid_from` and `valid_to`?" + the canonical paraphrase + an evidence
  count and date span (no raw quotes by default).
- For a contradiction (RFC 0011 § contradictions): "Which of these is
  closer to the truth, or are both wrong?" Pilot deferred to v1.5
  (Open Question 3). The current `target_kind` CHECK accepts only `claim`
  and `belief`; contradiction-mode questions require a follow-up schema shape
  for paired targets rather than relying on the existing polymorphic target.

Templates live under `prompts/interview/<id>_v{N}.md`. Each row stores a
single composite `prompt_template_version` matching RFC 0017's
`{area}.v{N}.{date_or_decision}.{descriptor}` shape, alongside
`prompt_template_path` pointing at the on-disk file; these replace the
earlier split `prompt_template_id` / `prompt_template_version` columns.
The agent's job is rendering and capture, not judgment. It does not
auto-vote.

#### Mid-session semantics

- Ctrl-C / SIGINT commits no half-typed rationale: the row is only
  inserted on the `answered_at` write, so a torn turn produces no row.
- `q` and the `save-and-quit` command both mark the session
  `completed_at = NULL` — i.e. resumable. `engram phase3 interview
  list-sessions --state open` is the discovery surface for unfinished
  sessions.
- `skip` inserts a `skip` verdict row immediately and advances; see
  § Skip semantics above.
- `rationale` is capped at 2000 chars by the schema and storage path. The
  prompt shows `[Enter to skip rationale]` so the empty-rationale path is
  obvious. Richer mid-session break / resume UX is handled by the separate RFC
  0027 web surface; CLI v1 leans on `save-and-quit`.

### CLI v1 (smoke-test surface)

All interview commands live under the phase-scoped command surface
introduced in RFC 0025 (D078); the bare `engram interview` namespace is
incompatible with the just-landed command contract:

- `engram phase3 interview start [--n 10] [--strata <expr>] [--seed <int>]
  [--include-superseded] [--ignore-cooldown] [--ignore-reask-cap]`
- `engram phase3 interview resume [--session-id <id>]`
- `engram phase3 interview history [--target <id>] [--since <ts>]`
- `engram phase3 interview export --format jsonl [--privacy-tier-max <N>]`
- `engram phase3 interview list-sessions [--state open|completed|all]`
- `engram phase3 interview coverage --strata <expr>`
- `engram phase3 interview enable-active-learning --signal-version <v>`

Export is local-only for offline analysis. The default for
`--privacy-tier-max` is **`1`** (fail-closed Tier 1 ceiling): higher
tiers require an explicit `--privacy-tier-max <N>` opt-in. The current export
filters out rows whose `privacy_tier` exceeds that ceiling; it does not emit a
redacted placeholder row for higher-tier labels.

`--ignore-cooldown` relaxes the cooldown filter only; **no flag
combination relaxes the privacy tier ceiling below the default**, and
`--ignore-cooldown` does not relax the separate re-ask cap unless
`--ignore-reask-cap` is also set. The ceiling is the only one-way ratchet in
the CLI surface.

CLI v1 is a thin loop over the sampler + storage. Its job is to prove the
schema, the sampler, the version stamping, and the idempotent commit
behavior. `list-sessions` and `coverage` exist specifically to debug
append-only failures and discover session ids; `coverage` is currently a simple
count-by-`stability_class` view, not a full strata dashboard.

### Web UI (separate RFC 0027 surface)

Captured here only to clarify ownership. RFC 0027 / Spec 0027 defines the
local web UI and adds `engram phase3 interview serve`; RFC 0021 owns the
gold-label storage, sampler, verdict, and CLI contract that the web UI reuses.

## Worked example

Single CLI session; numbers are illustrative.

```
$ engram phase3 interview start --n 5 --seed 4
session: gl-sess-2026-05-07-00 (gold_label_sessions row, started_at=2026-05-07T10:14Z)
sampler: stratified.v1, seed=4, strata={stability x conf-band x recency}
candidate_pool_tag: 0f0c... (opaque UUID)     active_learning: off
selected_order: materialized in gold_label_session_targets

[1/5] belief b-7f3a... "user works at Acme Corp"  status=accepted, conf=0.87
      stability=project_status, ev=3 msgs over 9mo (2024-11 .. 2025-08)
      version: consolidation_prompt=cons.v3.2026-04.tighten,
               consolidation_model=qwen2.5-7b.20260315,
               interview_request_profile=interview.v1.d079.initial
      Q: Is this currently true?
      [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]
      > t
      rationale [Enter to skip rationale]: still here, role unchanged

[2/5] claim c-91d2... predicate=has_pet, object={"name":"Mochi","species":"cat"}
      stability=identity, conf=0.62
      version: extraction_prompt=extract.v5.2026-03.predicates,
               extraction_model=qwen2.5-7b.20260301,
               request_profile=extractor.v5.2026-03.local
      Q: Is this an accurate paraphrase at the time of the cited evidence?
      [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]
      > t
      rationale [Enter to skip rationale]:

[3/5] belief b-c4e1... "user prefers vim"  status=accepted, conf=0.71
      stability=preference, ev=4 msgs over 18mo
      version: consolidation_prompt=cons.v3.2026-04.tighten,
               consolidation_model=qwen2.5-7b.20260315,
               interview_request_profile=interview.v1.d079.initial
      Q: Is this currently true?
      [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]
      > stale
      rationale [Enter to skip rationale]: switched to helix Apr 2026

[4/5] claim c-2210... predicate=goal_to, object_text="learn rust"
      stability=goal, conf=0.55
      version: extraction_prompt=extract.v5.2026-03.predicates,
               extraction_model=qwen2.5-7b.20260301,
               request_profile=extractor.v5.2026-03.local
      Q: Is this an accurate paraphrase at the time of the cited evidence?
      [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]
      > unsure
      rationale [Enter to skip rationale]:

[5/5] belief b-aa90... "user is_related_to {name:'Sam',kind:'sibling'}"
      stability=relationship, ev=1 msg
      version: consolidation_prompt=cons.v3.2026-04.tighten,
               consolidation_model=qwen2.5-7b.20260315,
               interview_request_profile=interview.v1.d079.initial
      Q: Is this currently true?
      [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]
      > t
      rationale [Enter to skip rationale]:

5 verdicts committed to gold_labels (session_id=gl-sess-2026-05-07-00).
session summary: 3 true, 0 false, 1 stale, 0 unsupported, 1 unsure, 0 skip.
session marked completed_at=2026-05-07T10:23Z.
```

After session: a `current_gold_label` view returns the most recent verdict per
`(target_kind, target_id, populated prompt/model pair, request_profile_version)`.
For beliefs, that request profile is the interview contract stamp. The
tiebreaker is the latest `answered_at`, with a verdict-rank fallback (`true` /
`false` / `stale` / `unsupported` outrank `unsure` / `skip`). Re-asks under the
same stored version shape are capped by the sampler at 3 by default, with
operator override. The `belief_audit`, `claim_audits`, and `contradictions`
tables are unchanged.

## Privacy and provenance

- **No outbound network.** Sampler, agent, and storage all run against the
  local Postgres + local LLM endpoint. Same constraint as every other
  Engram pipeline (D020).
- **`privacy_tier` carry, schema-enforced.** The label row inherits the
  target's privacy tier via the `fn_gold_labels_carry_privacy_tier`
  `BEFORE INSERT` trigger; an operator-supplied tier that disagrees with
  the parent is rejected. For future multi-source rendering (e.g.
  contradiction-mode questions surfacing two beliefs at once) the rule
  is `privacy_tier = max(tiers across all surfaced inputs)`.
- **Fail-closed export.** `engram phase3 interview export` defaults
  `--privacy-tier-max` to `1`; higher-tier rows are filtered out unless
  the operator opts in explicitly with `--privacy-tier-max <N>`. No
  flag combination relaxes the ceiling below the default — there is no
  "user's working tier" concept in Engram, and the RFC does not
  introduce one.
- **Excerpt handling.** Where a 1-line evidence excerpt is rendered, it is
  stored in the dedicated `evidence_excerpt` column rather than embedded in
  `prompt_text`. The v1 export path filters out rows above the requested
  privacy ceiling, so there is no separate "keep row but strip excerpt" branch
  for high-tier rows. Future contradiction-mode or mixed-tier exports need
  their own redaction rule.
- **Provenance preserved.** Each label cites the target ID, the typed
  prompt/model stamp (claim columns or belief columns, not both), the
  `request_profile_version`, the sampler ID + version + seed + strata weights,
  the opaque candidate-pool tag, the active-learning signal version (if
  non-NULL), the session id, and the prompt template version + path. When
  `gold_label_session_targets` is present, the selected order is also preserved
  for resume/rendering. A future re-extraction that produces a new claim
  version does not invalidate prior labels; they remain attached to the version
  they were authored against (RFC 0017 versioning discipline). Belief labels
  are attached to the belief row and its prompt/model stamp; the request
  profile on those rows is interview-side metadata.
- **Append-only, schema-enforced.** `fn_gold_labels_append_only`
  (`BEFORE UPDATE OR DELETE`, raises `P0001`) matches the raw-evidence
  rule (D002 / P4). Re-asking produces a new row.

## Relationship to other artifacts

- **RFC 0011** — labels join onto `claims.id` and `beliefs.id`; no schema
  changes inside Phase 3 are required. The existing
  `(extraction_prompt_version, extraction_model_version,
  request_profile_version)` triple on `claims` is the claim-side version stamp.
  Beliefs expose `prompt_version` and `model_version`; neither `beliefs` nor
  `belief_audit` currently exposes a canonical request-profile column. RFC 0021
  therefore treats `gold_labels.request_profile_version` on belief labels as
  interview-side metadata, not as a belief derivation join key.
- **RFC 0017** — interview prompt templates follow the same
  `*_template_version` versioning as extraction prompts.
- **RFC 0018** — labels are an **input** to the audit cascade reviewer
  rather than a substitute for it. D069 keeps the cascade advisory; gold
  labels would do the same for V1. They are independent producers; both
  feed Step 9 evals.
- **D044** — no auto-promotion or auto-demotion of beliefs from gold
  labels. A `false` verdict does **not** flip belief status; it produces
  signal for Step 9 re-extraction cycles and for the post-Phase-3
  adversarial round (Step 6). To keep the rule from leaking through a
  side door: **the gold-label loader must not call
  `engram.consolidator.transitions` (D052)** and must not synthesize claims
  from labels. There is no current schema-level trigger that can detect
  "gold-label-derived synthetic claim" because `claims` has no origin
  discriminator. If future work adds label-derived claims, it must first add an
  inspectable origin/source shape and then define the SQL guard.
- **D057 / predicate_vocabulary** — `gold_label_strata_vocabulary`
  follows the same local-vocabulary pattern using `(stratum_kind, key,
  display)`. Migration 010 seeds canonical strata values but does not enforce
  them with FKs/triggers on `gold_labels`; `strata_extra JSONB` carries any
  non-canonical extension keys until they are promoted into the vocabulary.
- **D073 / audit_reason_vocabulary** — `gold_label_verdict_vocabulary`
  is parallel to it. v1 ships gloss-now; the cross-walk to
  `audit_reason_vocabulary` is deferred to v1.5 (synthesis-carried
  risk).
- **D077 / current_beliefs** — sampler reads `current_beliefs` by
  default so status filtering excludes superseded / rejected rows;
  `--include-superseded` opts back in for adversarial sweeps.
- **D078 / RFC 0025** — all CLI commands live under `engram phase3
  interview {start, resume, history, export, list-sessions, coverage,
  enable-active-learning}`. RFC 0027 adds `serve` under the same phase-scoped
  namespace for the local web UI.
- **F010** — gold authorship has been deferred to "after hand-written
  hits coverage limits." This RFC proposes a continuous authoring surface
  rather than a cross-model judge; the two are complementary, not
  competing.
- **O008** — partial proposed answer: "user manual" (this RFC) plus
  later "LLM judge over user-confirmed subsets" (out of scope here).
- **`context_feedback`** — same kind of signal, opposite direction. Where
  `context_feedback` annotates retrieval outputs at use-time, `gold_labels`
  samples claims/beliefs at curate-time. Both should be allowed to feed
  Step 9.

## What this RFC does **not** propose

- **Does not** make gold labels a gate on extraction, consolidation, or
  belief promotion. Advisory only, mirroring D069.
- **Does not** capture new claims the user volunteers during interview.
  That is a real product question — does the user dictate facts the
  agent records as new evidence? — but it is a separate RFC. v1
  intentionally only labels existing rows.
- **Does not** introduce a remote service, a hosted UI, or any
  third-party API. Local agent, local DB, local model.
- **Does not** provide full candidate-pool replay. Current storage preserves
  label provenance and selected-order resume, not all candidates considered by
  the sampler.
- **Does not** schema-validate strata values against
  `gold_label_strata_vocabulary` in migration 010. That remains a small SQL
  follow-up if Step 9 needs hard guarantees.
- **Does not** redefine `expected_facts` or the GOLD_SET_TEMPLATE Step 5
  deliverable. The template still owns the cross-system eval contract;
  this RFC produces label data the template can later draw from.
- **Does not** handle multi-user shape. Engram is single-user; that
  remains true.

## Open questions

1. **Promotion path from labels to gold-set entries.** *Partially answered.*
   Per-stability-class target cooldowns plus the sampler-side 3-reask cap under
   the same stored version shape define how labels accumulate per target; what
   set of label rows then constitutes evidence for a `GOLD_SET_TEMPLATE` entry
   remains to be specified. A "k labels agreeing across N days" rule is likely
   fine for v1.
2. **Web UI handoff.** *Answered separately by RFC 0027 / D080.* The CLI stays
   as the backend smoke/admin surface. The local web UI reuses the same storage
   and materialized session targets.
3. **Contradiction-mode questions.** Worth piloting? They produce richer
   signal than per-row verdicts but are harder to render. Defer to v1.5. The
   current schema only accepts `target_kind IN ('claim','belief')`, so
   contradiction mode needs a follow-up paired-target shape.
4. **Active-learning bias signal source.** *Mechanism implemented; selection
   bias deferred.* `engram phase3 interview enable-active-learning
   --signal-version <v>` persists a local signal and stamps it onto subsequent
   rows. The current sampler does not yet consume RFC 0018 reviewer scores or
   reorder candidates. Turning that stamp into an actual bias should be a
   separate decision once enough reviewer/audit data exists.
5. **New-claim capture during interview.** Out of scope here, but a real
   open product question. Likely its own RFC, since it touches raw
   immutability framing.
6. **Cooldown defaults.** *Answered for v1 target cooldowns.* v1 ships
   per-stability-class defaults (mood 3d, task 7d, goal 14d, preference 30d,
   project_status 30d, relationship 60d, identity 90d) per `(target, any
   non-skip verdict)`, tunable via `ENGRAM_GOLD_COOLDOWN_<STABILITY_CLASS>_DAYS`
   env vars. Per-verdict half-window cooldowns remain deferred.
7. **Export shape.** The current JSONL export is a local operator export with
   fail-closed row filtering. Step 9 likely needs version-rich JSONL with the
   target prompt/model stamp and request profile; that ingest/export contract is
   still a follow-up, not something the current CLI output fully satisfies.
8. **Replayable candidate pools.** Selected-order materialization is enough for
   resume and web rendering. Full candidate-pool replay requires a new snapshot
   table, member rows, and a stable pool ordering contract before seeded
   randomization.

## Promotion path

1. Reviewed and revised; see `docs/reviews/rfc0021/` and the fresh rerun under
   `docs/reviews/rfc0021-rerun-2026-05-13/`.
2. ~~If accepted, add a BUILD_PHASES entry under Phase 3 follow-on or
   Step 5 substrate work; mark this RFC `accepted`.~~ **Done.**
3. ~~Land migration `010_gold_labels.sql` (gold_label_sessions +
   gold_labels + the strata and verdict vocabularies + the three
   `gold_labels` triggers, single transaction) and the sampler/agent/CLI
   skeleton.~~ **Done.**
4. ~~Land selected-order materialization for resume/web rendering.~~ **Done via
   migration `011_gold_label_session_targets.sql` / RFC 0027.**
5. ~~Wire the export path with the fail-closed Tier 1 default.~~ **Done.** Step
   9 ingest still needs a version-rich export contract.
6. ~~Defer web UI to its own RFC.~~ **Done via RFC 0027 / Spec 0027.**
7. Remaining follow-ups: version-rich Step 9 export/ingest, replayable
   candidate-pool snapshots if replay becomes necessary, schema-level strata
   validation if Step 9 needs hard guarantees, and any future synthetic-claim
   origin shape before a D044 SQL trigger can exist.
