# Implement RFC 0021 Gold-Set Interview Surface

Implement the accepted RFC 0021 (Gold-Set Interview Curation) per the
revised RFC text and D079. Read the work packet, `AGENTS.md`,
`docs/rfcs/0021-gold-set-interview-curation.md`, `DECISION_LOG.md` (D044,
D052, D057, D069, D073, D077, D078, D079), `src/engram/cli.py`,
`Makefile`, `tests/test_cli.py`, and the schema baselines in
`migrations/006_claims_beliefs.sql`, `migrations/007_claim_audits.sql`,
and `migrations/009_phase4_entities_review.sql` before editing.

## Required behavior

### 1. Migration `migrations/010_gold_labels.sql`

Add a single migration with:

- `gold_label_sessions` parent table:
  - `session_id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `seed BIGINT NOT NULL`
  - `sampler_id TEXT NOT NULL`
  - `sampler_version TEXT NOT NULL`
  - `strata_weights JSONB NOT NULL`
  - `started_at TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `completed_at TIMESTAMPTZ NULL`
  - `operator_note TEXT NULL`
- `gold_label_strata_vocabulary` lookup table seeded with the v1 strata
  keys (e.g., stability_class values, conf_band buckets `0.0-0.2`,
  `0.2-0.4`, …, `0.8-1.0`, recency_band buckets `<7d`, `<30d`, `<90d`,
  `<365d`, `>=365d`, belief_status `candidate|provisional|accepted`).
- `gold_label_verdict_vocabulary` lookup table seeded with the six
  verdicts (`true`, `false`, `stale`, `unsupported`, `unsure`, `skip`)
  plus a one-line `gloss TEXT`.
- `gold_labels` table:
  - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `session_id UUID NOT NULL REFERENCES gold_label_sessions(session_id)`
  - `target_kind TEXT NOT NULL CHECK (target_kind IN ('claim','belief'))`
  - `target_id UUID NOT NULL`
  - `extraction_prompt_version TEXT NULL`
  - `extraction_model_version TEXT NULL`
  - `consolidation_prompt_version TEXT NULL`
  - `consolidation_model_version TEXT NULL`
  - `request_profile_version TEXT NOT NULL`
  - CHECK enforcing the right triple is populated based on `target_kind`.
  - `prompt_template_version TEXT NOT NULL`
  - `prompt_template_path TEXT NOT NULL`
  - `prompt_text TEXT NOT NULL`
  - `evidence_excerpt TEXT NULL`
  - `verdict TEXT NOT NULL REFERENCES gold_label_verdict_vocabulary(verdict)`
  - `rationale TEXT NULL CHECK (rationale IS NULL OR length(rationale) <= 2000)`
  - `sampler_id TEXT NOT NULL`
  - `sampler_version TEXT NOT NULL`
  - `candidate_pool_snapshot_id UUID NOT NULL`
  - `active_learning_signal_version TEXT NULL`
  - `stability_class TEXT NOT NULL`
  - `conf_band TEXT NOT NULL`
  - `recency_band TEXT NOT NULL`
  - `belief_status TEXT NULL`
  - `strata_extra JSONB NOT NULL DEFAULT '{}'::jsonb`
  - `asked_at TIMESTAMPTZ NOT NULL`
  - `answered_at TIMESTAMPTZ NOT NULL`
  - `privacy_tier INT NOT NULL`
- Triggers (named per RFC 0021 § Storage):
  - `fn_gold_labels_append_only` `BEFORE UPDATE OR DELETE` raising
    `P0001`.
  - `fn_gold_labels_validate_target` `BEFORE INSERT` resolving
    `target_id` against `claims` or `beliefs` per `target_kind`,
    refusing dangling references.
  - `fn_gold_labels_carry_privacy_tier` `BEFORE INSERT` copying
    `privacy_tier` from the parent target; reject any operator-supplied
    tier that disagrees.
- Indexes:
  - btree on `(target_kind, target_id, extraction_prompt_version,
    extraction_model_version, request_profile_version)` for claim
    targets.
  - btree on `(target_kind, target_id, consolidation_prompt_version,
    consolidation_model_version, request_profile_version)` for belief
    targets.
  - btree on `(session_id)` and `(asked_at)`.
- View `current_gold_label`: latest `answered_at` per `(target_kind,
  target_id, version_triple)` with verdict-rank tiebreak (`true|false|
  stale|unsupported` outrank `unsure|skip`).

### 2. Python module `src/engram/interview/`

- `__init__.py` re-exports the public API.
- `storage.py`: append-only INSERT helpers for `gold_label_sessions`
  and `gold_labels`; raises `GoldLabelStorageError` on append-only or
  parent-validation trigger failure.
- `sampler.py`: stratified sampler with seeded RNG; reads
  `current_beliefs` (D077) by default; `--include-superseded` flag
  surfaces superseded/rejected. Active-learning bias defaulted off;
  opt-in only when `active_learning_signal_version` is provided.
  Cooldown defaults via `ENGRAM_GOLD_COOLDOWN_<STABILITY_CLASS>_DAYS`
  env vars (defaults: `goal=14`, `task=7`, `mood=3`, `preference=30`,
  `relationship=60`, `identity=90`, `project_status=30`); per-verdict
  cooldown defaults to half. `skip` is cooldown-free.
- `agent.py`: rendering surface. Reads a target row (claim or belief),
  selects the appropriate template at
  `prompts/interview/<id>_v{N}.md`, renders the question and (optional)
  evidence excerpt, captures the verdict + rationale. Does NOT generate
  freeform claims; does NOT call live LLMs.
- `errors.py`: `GoldLabelStorageError`, `GoldLabelSamplerError`,
  `GoldLabelVerdictError` subclasses of a domain root.

Constants live behind `ENGRAM_GOLD_*` env vars per the Python coding
standard (RFC 0012).

### 3. CLI: `engram phase3 interview {start, resume, history, export, list-sessions, coverage, enable-active-learning}`

Wire under `engram phase3 interview` per D078:

- `engram phase3 interview start [--n 10] [--strata <expr>] [--seed <int>]`
- `engram phase3 interview resume [--session-id <id>]`
- `engram phase3 interview history [--target <id>] [--since <ts>]`
- `engram phase3 interview export [--format jsonl] [--privacy-tier-max <N>] [--output <path>]`
  Default `--privacy-tier-max 1` (fail-closed Tier 1).
- `engram phase3 interview list-sessions [--state open|completed]`
- `engram phase3 interview coverage --strata <expr>`
- `engram phase3 interview enable-active-learning --signal-version <v>`

The `--ignore-cooldown` flag must NOT relax `--privacy-tier-max` or
strata-weight floors.

Do NOT register a bare `engram interview`; the only entry point is
`engram phase3 interview`.

### 4. Prompts: `prompts/interview/`

Add at minimum:

- `prompts/interview/claim_v1.md` — claim-mode question template.
- `prompts/interview/belief_v1.md` — belief-mode question template.

Each template's filename must match the `prompt_template_version` it
declares per RFC 0017 (`interview.claim.v1.d079.initial` →
`prompts/interview/claim_v1.md`).

### 5. Makefile targets

Add phase-scoped targets:

- `phase3-interview-start`
- `phase3-interview-resume`
- `phase3-interview-history`
- `phase3-interview-export`
- `phase3-interview-list-sessions`
- `phase3-interview-coverage`

Use the same docker/isolated suffix pattern as other phase3 targets when
reasonable (e.g., `phase3-interview-export-docker`).

### 6. Tests

Add deterministic tests under `tests/`:

- `tests/test_interview_cli.py`: argparse dispatch, fail-closed Tier 1
  default on export, no-bare-interview namespace, `--ignore-cooldown`
  scope.
- `tests/test_interview_sampler.py`: seeded determinism, strata
  selection, cooldown env var application, `skip` cooldown exemption.
- `tests/test_interview_storage.py`: append-only trigger raises (use
  the test database fixture pattern from `tests/test_db.py` if one
  exists), parent-validation trigger refuses dangling target_id,
  privacy-tier carry rejects mismatched operator tier.
- `tests/test_migrations.py` (or extend existing) to confirm migration
  010 applies cleanly.

Tests must NOT call live LLMs. Use deterministic fixtures.

### 7. Docs

- Update `README.md` with a short `engram phase3 interview` section in
  the operator command examples.
- Update `CHANGELOG.md` with the implementation note under
  `## [Unreleased]`.

## Out of scope

- No web UI.
- No new claim capture during interview (RFC 0021 § What this RFC does
  not propose).
- No belief status auto-flip from verdicts (D044).
- No call to `engram.consolidator.transitions` from the gold-label
  loader (D052 invariant).
- No contradiction-mode template (deferred to v1.5 per RFC § Open Q 3).

## Handoff artifact

When done, write
`docs/reviews/rfc0021-gold-set-implementation/IMPLEMENTATION_HANDOFF.md`
with the exact lowercase `author:` line from the work packet, a summary
of changed files, the verification commands already run, and any
residual risks.

Stay inside the declared write scope. Do not edit BUILD_PHASES.md,
DECISION_LOG.md, HUMAN_REQUIREMENTS.md, or any RFC.
