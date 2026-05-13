<a id="rfc-0021"></a>
# RFC 0021: Gold-Set Interview Curation

| Field | Value |
|-------|-------|
| RFC | 0021 |
| Title | Gold-Set Interview Curation |
| Status | accepted |
| Implementation | scaffolded |
| Date | 2026-05-07 |
| Context | ROADMAP Step 5 (gold-set authoring); HUMAN_REQUIREMENTS § "the eval gold set is the actual specification"; BUILD_PHASES Phase 3 acceptance row; D016, D040, D044, D052, D057, D069, D073, D077, D078, F010, O008; RFC 0011 §§ Stage A / Stage B; RFC 0017 prompt-template versioning; RFC 0018 § Promotion Path step 4 (cascade reviewer scheduled post-Step-5); RFC 0025 phase-scoped command surface; `migrations/006_claims_beliefs.sql:131` (`claims`); `migrations/006_claims_beliefs.sql:178` (`beliefs`) |
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
  - F010
  - O008

Review refs:
  - none

Phase refs:
  - PHASE-0003

This RFC proposes an **agent-driven interview loop** that samples claims and
beliefs from the local corpus, asks the user one structured question at a time,
and stores the user's verdicts in an append-only local table. The accumulated
verdicts function as a continuously-curated gold set that never leaves the
machine. A CLI surface is in scope as v1 for smoke-testing the backend; a web
UI is the intended long-term surface but is out of scope here.

This is an idea-capture RFC, not an accepted architecture decision. It does
not promote the gold set into a hard gate, does not change the existing claim
or belief schemas, and does not authorize any model or pipeline change. It
overlaps with — and may eventually subsume parts of — open question O008
("eval gold-set authorship model"). It does not replace the
`GOLD_SET_TEMPLATE` Step 5 deliverable; it complements it as a continuous
extension surface.

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

Each interview turn is a single `(claim_id | belief_id, typed version triple,
prompt, verdict, rationale, asked_at, answered_at)` tuple committed to a new
append-only local table. The agent never modifies the underlying claim or
belief; verdicts are derived data that joins onto existing IDs.

### Storage

A new migration `010_gold_labels.sql` adds the parent session table, the
labels table, the strata and verdict vocabularies, and four schema-level
triggers. Both the session and label tables land in a single transaction so
the NOT NULL FK on `gold_labels.session_id` is well-defined from the start
(matches the `006_claims_beliefs.sql` precedent).

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
resume` and the worked example below are unimplementable, and the candidate
pool snapshot id (see § Sampler) has nowhere to anchor.

```
gold_labels
  id                              UUID PRIMARY KEY
  session_id                      UUID NOT NULL REFERENCES gold_label_sessions(session_id)
  target_kind                     TEXT NOT NULL CHECK (target_kind IN ('claim','belief'))
  target_id                       UUID NOT NULL

  -- Typed version triple. Exactly one of the two triples is populated,
  -- selected by target_kind, mirroring the columns on `claims` (RFC 0011)
  -- and `belief_audit` (RFC 0011 Stage B / RFC 0018) so equality joins
  -- against the canonical version stamps stay indexed.
  extraction_prompt_version       TEXT NULL
  extraction_model_version        TEXT NULL
  consolidation_prompt_version    TEXT NULL
  consolidation_model_version     TEXT NULL
  request_profile_version         TEXT NOT NULL

  prompt_text                     TEXT NOT NULL
  prompt_template_version         TEXT NOT NULL  -- {area}.v{N}.{date_or_decision}.{descriptor} (RFC 0017)
  prompt_template_path            TEXT NOT NULL  -- prompts/interview/<id>_v{N}.md
  evidence_excerpt                TEXT NULL      -- redacted at export when privacy_tier > ceiling

  verdict                         TEXT NOT NULL REFERENCES gold_label_verdict_vocabulary(verdict)
  rationale                       TEXT NULL      -- capped at 2000 chars at the application layer

  -- Typed strata (replaces sampler_strata_key JSONB; mirrors predicate_vocabulary, D057).
  stability_class                 TEXT NOT NULL
  conf_band                       TEXT NOT NULL
  recency_band                    TEXT NOT NULL
  belief_status                   TEXT NULL
  strata_extra                    JSONB NOT NULL DEFAULT '{}'::jsonb

  -- Reproducibility / replay stamps.
  candidate_pool_snapshot_id      UUID NOT NULL
  active_learning_signal_version  TEXT NULL      -- NULL when bias is off (F018)

  sampler_id                      TEXT NOT NULL
  sampler_version                 TEXT NOT NULL
  asked_at                        TIMESTAMPTZ NOT NULL
  answered_at                     TIMESTAMPTZ NOT NULL
  privacy_tier                    INT NOT NULL   -- carried from target row by trigger
```

Constraints worth naming explicitly:

- `chk_gold_labels_version_triple` — `target_kind = 'claim'` requires the
  extraction triple populated and the consolidation columns NULL;
  `target_kind = 'belief'` requires the consolidation triple populated and
  the extraction columns NULL. `request_profile_version` is required in
  both shapes.
- `chk_gold_labels_template_path_matches_version` — best-effort CHECK that
  the version embedded in `prompt_template_path` matches
  `prompt_template_version`; kept lightweight (substring match) so the
  cost is negligible.
- `idx_gold_labels_claim_triple` — btree on `(target_id, extraction_prompt_version,
  extraction_model_version, request_profile_version)` `WHERE target_kind = 'claim'`.
- `idx_gold_labels_belief_triple` — btree on `(target_id, consolidation_prompt_version,
  consolidation_model_version, request_profile_version)` `WHERE target_kind = 'belief'`.

Triggers (named explicitly, parallel to `claims` / `belief_audit` /
`claim_audits`):

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
- `fn_gold_labels_block_synthetic_audit_input` — CHECK or trigger ensuring
  no `belief_audit.input_claim_ids` row references a claim derived from a
  gold-label promotion path. Keeps D044's "no auto-promotion of beliefs
  from gold labels" intact: see also § Relationship to other artifacts.

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

  Cross-walk to `audit_reason_vocabulary` is deferred to v1.5 (synthesis-
  carried risk: Step 9 consumers may need a mechanical mapping between
  `false` and the cascade reviewer's "fact-correction" reason; gloss-now,
  mapping-later is the trade we accept).

- `gold_label_strata_vocabulary (key_name TEXT, key_value TEXT, gloss TEXT,
  PRIMARY KEY (key_name, key_value))` — seeded with v1 strata keys for
  `stability_class`, `conf_band`, `recency_band`, `belief_status`. Pattern
  matches `predicate_vocabulary` (D057). `strata_extra JSONB` on the label
  row holds non-canonical extension keys that have not yet been promoted
  into the vocabulary.

The table is not a `gold_entries` table — it does not author the
`expected_facts` shape consumed by Step 9 evals. Promotion of label clusters
into formal gold-set entries is a downstream step (see § Open questions).

### Sampler

Random sampling burns interviews on easy cases and clusters them by whatever
the corpus happens to over-produce. The proposal is **stratified sampling
with opt-in active-learning bias**, version-stamped:

- **Source view.** The sampler reads `current_beliefs` (D077) by default
  so status filtering excludes `superseded` and `rejected` rows. Operator
  override is `engram phase3 interview start --include-superseded` for
  adversarial sweeps.
- **Strata.** Cross product of `stability_class` × confidence band ×
  recency band, reweighted to over-sample under-labeled strata. For
  beliefs, also stratify on `belief_status` and on whether a
  `belief_audit` or `claim_audits` row already exists. Strata are stored
  as the typed columns described in § Storage and validated against
  `gold_label_strata_vocabulary` (D057 pattern).
- **Active-learning bias (opt-in).** Within a stratum, prefer (a) targets
  near the decision boundary of any existing local reviewer (RFC 0018)
  and (b) targets with no prior `gold_labels` row at the current version
  triple. The bias is **off by default** and must not run silently. The
  operator-visible "at scale" trigger is "RFC 0018 reviewer has produced
  ≥ 500 audit rows" — that 500 is empirically-tunable and expected to be
  revisited once any usage data exists. Operators enable the bias with
  `engram phase3 interview enable-active-learning --signal-version <v>`;
  the active value is stamped onto every emitted row as
  `active_learning_signal_version`. Enabling the bias is a project-level
  decision (see Open Questions); the flag is the mechanism, the
  activation is the decision.
- **Cooldowns.** A target answered in the last N days is suppressed for
  that window. Defaults per `(target, any verdict)` are tunable via
  `ENGRAM_GOLD_COOLDOWN_<STABILITY_CLASS>_DAYS` env vars (per the Python
  coding standard, RFC 0012):

  | Stability class | `(target, any verdict)` | `(target, verdict)` |
  |---|---|---|
  | `mood` | 3d | 1.5d |
  | `task` | 7d | 3.5d |
  | `goal` | 14d | 7d |
  | `preference` | 30d | 15d |
  | `project_status` | 30d | 15d |
  | `relationship` | 60d | 30d |
  | `identity` | 90d | 45d |

  Per `(target, verdict)` cooldown defaults to half the `(target, any
  verdict)` value. `skip` is **cooldown-free** (see § Skip semantics);
  the cooldown rule applies only to `true | false | stale | unsupported |
  unsure`. Empirical tuning is expected post-v1.
- **Determinism / reproducibility.** Each emitted question is stamped
  with `(seed, sampler_id, sampler_version, strata_weights)` plus a
  `candidate_pool_snapshot_id` (UUID identifying the pool the question
  was drawn from) and `active_learning_signal_version` (NULL when bias
  is off). The full set is what makes a session re-derivable; without
  the snapshot id, replay drifts as the corpus grows.

V1 sampler is the simplest version that respects strata + cooldowns + the
opt-in bias gate; deeper introspection (`inspect-strata-balance`,
`dry-run`) is deferred to a v1.1 CLI expansion if Phase 3 follow-on
operators hit a debugging wall.

#### Skip semantics

`skip` advances the cursor and inserts a row with `verdict = 'skip'`. The
prompt labels it `[skip - ask later]` to make the contract explicit: the
target re-surfaces on the next session because skip rows do not gate the
cooldown calculation. A separate `never_ask` blocklist surface is deferred
to v1.5; for v1, repeated skip simply re-surfaces.

### Interview agent

A locally-run agent (small local model is sufficient — this is reading
structured rows, not generating freeform claims) renders each sampled target
into a question using a versioned prompt template:

- For a claim: "Is this an accurate paraphrase of your situation at the
  time of the cited evidence?" + the canonical paraphrase. If a 1-line
  evidence excerpt is rendered, it is stored on the row in
  `evidence_excerpt` (a separate column from `prompt_text`) so the
  export path can redact it cleanly when the row's `privacy_tier`
  exceeds the requested ceiling.
- For a belief: "Is this currently true?" / "Was this true between
  `valid_from` and `valid_to`?" + the canonical paraphrase + an evidence
  count and date span (no raw quotes by default).
- For a contradiction (RFC 0011 § contradictions): "Which of these is
  closer to the truth, or are both wrong?" Pilot deferred to v1.5
  (Open Question 3); the polymorphic `(target_kind, target_id)` shape
  with the parent-validation trigger accommodates it without further
  schema change.

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
- `rationale` is capped at 2000 chars at the application layer with an
  80%-warning prompt as the user types past 1600 chars. The prompt
  shows `[Enter to skip rationale]` so the empty-rationale path is
  obvious. Richer mid-session break / resume UX is deferred to web v2;
  CLI v1 leans on `save-and-quit` (which is sufficient).

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
tiers require an explicit `--privacy-tier-max <N>` opt-in. Combined with
the separate `evidence_excerpt` column, the export path redacts the
excerpt whenever the row's `privacy_tier` exceeds the requested ceiling.

`--ignore-cooldown` relaxes the cooldown filter only; **no flag
combination relaxes the privacy tier ceiling below the default**, and
`--ignore-cooldown` does not relax strata-weight floors either. The
ceiling is the only one-way ratchet in the CLI surface.

CLI v1 is a thin loop over the sampler + storage. Its job is to prove the
schema, the sampler, the version stamping, and the idempotent commit
behavior. `list-sessions` and `coverage` exist specifically to debug
append-only failures and discover session ids; richer dashboards belong
to the v2 web surface.

### Web UI (v2 — out of scope here)

Captured here only to clarify v1 boundaries. The web surface is the only
plausible interview UX for a non-developer user; CLI v1 exists to keep the
backend contract honest before that work starts. Web surface design is a
separate RFC.

## Worked example

Single CLI session; numbers are illustrative.

```
$ engram phase3 interview start --n 5 --seed 4
session: gl-sess-2026-05-07-00 (gold_label_sessions row, started_at=2026-05-07T10:14Z)
sampler: stratified.v1, seed=4, strata={stability x conf-band x recency}
candidate_pool_snapshot: cps-2026-05-07-00     active_learning: off

[1/5] belief b-7f3a... "user works at Acme Corp"  status=accepted, conf=0.87
      stability=project_status, ev=3 msgs over 9mo (2024-11 .. 2025-08)
      version: consolidation_prompt=cons.v3.2026-04.tighten,
               consolidation_model=qwen2.5-7b.20260315,
               request_profile=interview.v1.2026-05.smoke
      Q: Is this currently true?
      [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]
      > t
      rationale [Enter to skip rationale]: still here, role unchanged

[2/5] claim c-91d2... predicate=has_pet, object={"name":"Mochi","species":"cat"}
      stability=identity, conf=0.62
      version: extraction_prompt=extract.v5.2026-03.predicates,
               extraction_model=qwen2.5-7b.20260301,
               request_profile=interview.v1.2026-05.smoke
      Q: Is this an accurate paraphrase at the time of the cited evidence?
      [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]
      > t
      rationale [Enter to skip rationale]:

[3/5] belief b-c4e1... "user prefers vim"  status=accepted, conf=0.71
      stability=preference, ev=4 msgs over 18mo
      version: consolidation_prompt=cons.v3.2026-04.tighten,
               consolidation_model=qwen2.5-7b.20260315,
               request_profile=interview.v1.2026-05.smoke
      Q: Is this currently true?
      [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]
      > stale
      rationale [Enter to skip rationale]: switched to helix Apr 2026

[4/5] claim c-2210... predicate=goal_to, object_text="learn rust"
      stability=goal, conf=0.55
      version: extraction_prompt=extract.v5.2026-03.predicates,
               extraction_model=qwen2.5-7b.20260301,
               request_profile=interview.v1.2026-05.smoke
      Q: Is this an accurate paraphrase at the time of the cited evidence?
      [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]
      > unsure
      rationale [Enter to skip rationale]:

[5/5] belief b-aa90... "user is_related_to {name:'Sam',kind:'sibling'}"
      stability=relationship, ev=1 msg
      version: consolidation_prompt=cons.v3.2026-04.tighten,
               consolidation_model=qwen2.5-7b.20260315,
               request_profile=interview.v1.2026-05.smoke
      Q: Is this currently true?
      [t]rue / [f]alse / [s]tale / [u]nsupported / unsure / [skip - ask later]
      > t
      rationale [Enter to skip rationale]:

5 verdicts committed to gold_labels (session_id=gl-sess-2026-05-07-00).
session summary: 3 true, 0 false, 1 stale, 0 unsupported, 1 unsure, 0 skip.
session marked completed_at=2026-05-07T10:23Z.
```

After session: a `current_gold_label` view returns the most recent verdict
per `(target_kind, target_id, version_triple)` — tiebreaker is the latest
`answered_at`, with a verdict-rank fallback (`true` / `false` / `stale` /
`unsupported` outrank `unsure` / `skip`). Re-asks under the same version
triple are capped at 3 by default, with operator override. The
`belief_audit`, `claim_audits`, and `contradictions` tables are unchanged.

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
- **Excerpt redaction.** Where a 1-line evidence excerpt is rendered, it
  is stored in the dedicated `evidence_excerpt` column rather than
  embedded in `prompt_text`. The export path drops `evidence_excerpt`
  on any row whose `privacy_tier` exceeds the requested ceiling. The
  `prompt_text` column contains the rendered question, which the user
  has by definition seen.
- **Provenance preserved.** Each label cites the target ID, the typed
  version triple (claim columns or belief columns, not both), the
  sampler ID + version + seed + strata weights, the candidate-pool
  snapshot id, the active-learning signal version (if non-NULL), the
  session id, and the prompt template version + path. A future
  re-extraction that produces a new claim version does not invalidate
  prior labels; they remain attached to the version they were authored
  against (RFC 0017 versioning discipline).
- **Append-only, schema-enforced.** `fn_gold_labels_append_only`
  (`BEFORE UPDATE OR DELETE`, raises `P0001`) matches the raw-evidence
  rule (D002 / P4). Re-asking produces a new row.

## Relationship to other artifacts

- **RFC 0011** — labels join onto `claims.id` and `beliefs.id`; no schema
  changes inside Phase 3 are required. The existing
  `(extraction_prompt_version, extraction_model_version,
  request_profile_version)` triple on `claims` is the version stamp; for
  beliefs, the `belief_audit` version columns are the analogue.
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
  `engram.consolidator.transitions` (D052)**, and a CHECK / trigger
  prevents `belief_audit.input_claim_ids` from referencing any
  gold-label-derived synthetic claim. This is a code-review invariant
  on the loader plus a schema-level guard on the audit table; a
  stronger separate-DB-role enforcement is deliberately not chosen
  (would cross-cut D052 without need).
- **D057 / predicate_vocabulary** — `gold_label_strata_vocabulary`
  follows the same `(key_name, key_value, gloss)` pattern, with
  `strata_extra JSONB` carrying any non-canonical extension keys until
  they are promoted into the vocabulary.
- **D073 / audit_reason_vocabulary** — `gold_label_verdict_vocabulary`
  is parallel to it. v1 ships gloss-now; the cross-walk to
  `audit_reason_vocabulary` is deferred to v1.5 (synthesis-carried
  risk).
- **D077 / current_beliefs** — sampler reads `current_beliefs` by
  default so status filtering excludes superseded / rejected rows;
  `--include-superseded` opts back in for adversarial sweeps.
- **D078 / RFC 0025** — all CLI commands live under `engram phase3
  interview {start, resume, history, export, list-sessions, coverage,
  enable-active-learning}`.
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
- **Does not** redefine `expected_facts` or the GOLD_SET_TEMPLATE Step 5
  deliverable. The template still owns the cross-system eval contract;
  this RFC produces label data the template can later draw from.
- **Does not** handle multi-user shape. Engram is single-user; that
  remains true.

## Open questions

1. **Promotion path from labels to gold-set entries.** *Partially
   answered.* Per-stability-class cooldowns (F020) plus the 3-reask cap
   under the same version triple (F012) define how labels accumulate
   per target; what set of label rows then constitutes evidence for a
   `GOLD_SET_TEMPLATE` entry remains to be specified. A "k labels
   agreeing across N days" rule is likely fine for v1.
2. **Web UI handoff.** When the web surface arrives, does the CLI go away
   or stay as an admin/back-channel tool? Lean toward keep, since
   smoke-testing the backend remains useful indefinitely.
3. **Contradiction-mode questions.** Worth piloting? They produce richer
   signal than per-row verdicts but are harder to render. Defer to v1.5;
   the polymorphic shape (with the parent-validation trigger) already
   accommodates the schema.
4. **Active-learning bias signal source.** *Answered.* RFC 0018 reviewer
   scores are the feed; the operator-visible "at scale" trigger is "RFC
   0018 reviewer has produced ≥ 500 audit rows", with that 500
   empirically-tunable. Activation is gated behind `engram phase3
   interview enable-active-learning --signal-version <v>` and stamped
   onto every emitted row as `active_learning_signal_version`. Whether
   the activation itself warrants a DECISION_LOG entry is its own open
   project question.
5. **New-claim capture during interview.** Out of scope here, but a real
   open product question. Likely its own RFC, since it touches raw
   immutability framing.
6. **Cooldown defaults.** *Answered.* v1 ships per-stability-class
   defaults (mood 3d, task 7d, goal 14d, preference 30d, project_status
   30d, relationship 60d, identity 90d) per `(target, any verdict)` and
   half those values per `(target, verdict)`, tunable via
   `ENGRAM_GOLD_COOLDOWN_<STABILITY_CLASS>_DAYS` env vars. Empirical
   re-tuning is expected post-v1.
7. **Export shape.** JSONL with `(target, verdict, version_triple)` is
   the minimum; whether additional pivots are useful enough to bake in
   depends on Step 9 needs.

## Promotion path

1. Reviewed and revised; see `docs/reviews/rfc0021/`.
2. ~~If accepted, add a BUILD_PHASES entry under Phase 3 follow-on or
   Step 5 substrate work; mark this RFC `accepted`.~~ **Done.**
3. Land migration `010_gold_labels.sql` (gold_label_sessions +
   gold_labels + the strata and verdict vocabularies + the four named
   triggers, single transaction) and the sampler/agent/CLI skeleton on
   a separate branch.
4. Wire the export path with the fail-closed Tier 1 default and the
   excerpt-redaction rule; confirm Step 9 eval runners can ingest it.
5. Defer web UI to its own RFC after CLI v1 produces real label data.
