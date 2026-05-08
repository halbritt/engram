# RFC 0021 Gold-Set Findings Ledger
author: ledger-codex-gpt-5.5-001

Status: ledger
Date: 2026-05-08
Sources:
  - RFC_0021_GOLD_SET_REVIEW_claude.md
  - RFC_0021_GOLD_SET_REVIEW_codex.md
  - RFC_0021_GOLD_SET_REVIEW_gemini.md

## Findings

### F001 — Migration filename `008_gold_labels.sql` collides with shipped 008/009
Severity: blocking
Sources: [claude, codex]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:113, :351; migrations/008_claim_extractions_request_profile_unique.sql; migrations/009_phase4_entities_review.sql
Rationale: 008 and 009 numeric prefixes are already taken by the request-profile uniqueness migration and the Phase 4 entities/review migration; the next available slot is `010_gold_labels.sql`, and the wrong filename appears at both the schema citation and the Promotion Path step 3.
merged_from:
  - claude § F001
  - codex § F001

### F002 — `target_version_stamp JSONB` weakens the typed join contract against `claims`/`beliefs`/`belief_audit`
Severity: major
Sources: [claude, codex]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:120-124; migrations/006_claims_beliefs.sql:155-157, :169-172, :218-219, :257-258
Rationale: The existing schema uses typed `TEXT` columns and a btree index on the claim version pair; a JSONB stamp on `gold_labels` defeats indexed equality joins on the `(extraction_prompt_version, extraction_model_version, request_profile_version)` triple and the equivalent belief/belief_audit columns, and the RFC's belief-side citation of `request_profile_version` does not exist on `belief_audit`.
merged_from:
  - claude § F002
  - codex § F003

### F003 — Append-only is asserted but no Postgres-level trigger enforcement is specified
Severity: major
Sources: [claude, codex]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:139-141, :274-275; migrations/006_claims_beliefs.sql:472-486, :595-609; migrations/007_claim_audits.sql:104-118
Rationale: Every other append-only table in tree (`claims`, `belief_audit`, `claim_audits`) carries a `BEFORE UPDATE OR DELETE` trigger raising `P0001`; the RFC's prose ("no UPDATE/DELETE enforcement matches the raw-evidence discipline") is ambiguous and does not commit to writing `fn_gold_labels_append_only`, so an implementer could ship a table with no schema-level guard.
merged_from:
  - claude § F003
  - codex § F004

### F004 — `privacy_tier` carry rule is unenforced and ambiguous about multi-source max
Severity: major
Sources: [claude, codex]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:136, :265-268; migrations/006_claims_beliefs.sql:181, :220; HUMAN_REQUIREMENTS.md:607-616
Rationale: "Carried from target row" is enforced nowhere — no `BEFORE INSERT` trigger copies or asserts equality against the parent claim/belief tier — and the RFC does not specify a `max(tiers across all surfaced inputs)` rule, so a multi-source rendering or a buggy interview agent can silently land a Tier-1 row at a lower tier.
merged_from:
  - claude § F004
  - codex § F010 (insert-trigger half)

### F005 — `engram interview export --privacy-tier-max` default ceiling is undefined and risks fail-open Tier-1 leakage
Severity: blocking
Sources: [claude, codex, gemini]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:200-203; HUMAN_REQUIREMENTS.md:607-616
Rationale: The RFC says the default ceiling "matches the user's working tier," but no such concept exists anywhere in Engram (no env var, settings row, or CLI), so the export command's first invocation can silently emit Tier 1 rows; the fail-closed posture (Tier 1 ceiling default with explicit higher-tier opt-in) is not specified.
merged_from:
  - claude § F005
  - codex § F010 (export-ceiling half)
  - gemini § F001

### F006 — Sampler determinism is under-specified once active-learning bias reads time-varying state
Severity: major
Sources: [claude, codex]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:152-171
Rationale: Reproducibility from `(seed, sampler_version, strata_weights)` requires snapshotting both the candidate pool and any active-learning input (e.g., RFC 0018 reviewer scores or "no prior gold_labels row"); the RFC stamps neither a corpus snapshot nor a bias-input snapshot, so replays under the same seed will diverge silently when bias is enabled.
merged_from:
  - claude § F006
  - codex § F005

### F007 — `gold_labels` lacks a session/run identity column required by `engram interview resume` and the worked example
Severity: major
Sources: [claude, codex, gemini]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:115-137, :194-198, :221
Rationale: The CLI exposes `--session-id`, the worked example prints `session: gl-sess-2026-05-07-00`, and the resume contract depends on a stable seed-per-session, but the schema has no `session_id`/`run_id`/`seed` column and no parent `gold_label_session` table; resume cannot be implemented and per-session queries are unanswerable.
merged_from:
  - claude § F007
  - codex § F009
  - gemini § F008

### F008 — Verdict vocabulary collapses `false` vs `unsupported` and is not differentiated at the prompt
Severity: major
Sources: [claude, codex, gemini]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:128-130, :219-253; migrations/007_claim_audits.sql:10-35, :41-44; docs/rfcs/0018-evidence-to-claim-audit-cascade.md:170-201
Rationale: The verdict enum mixes "claim is wrong about the world" with "evidence does not establish the claim," the worked example's prompt only renders five of the six options (omitting `unsupported`), and the RFC does not gloss each verdict against RFC 0018 audit reasons or provide a verdict-vocabulary table parallel to `audit_reason_vocabulary`; downstream Step 9 consumers cannot distinguish fact-correction from trace-broken signal.
merged_from:
  - claude § F008
  - codex § F011
  - gemini § F002

### F009 — Prompt template versioning diverges from RFC 0017's single composite version string
Severity: major
Sources: [claude, codex]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:126-127, :188-190; docs/rfcs/0017-extraction-prompt-versioning.md:64-75
Rationale: RFC 0017 commits to one composite `{area}.v{N}.{date_or_decision}.{descriptor}` version string and a single artifact path `prompts/<area>/<id>_v{N}.md`, but RFC 0021 splits this into `prompt_template_id TEXT` + `prompt_template_version TEXT` with no path convention or CHECK linking the two; the join from a label row to its rendering prompt is unverifiable.
merged_from:
  - claude § F009
  - codex § F008

### F010 — D044 prohibition leaves a foothold for a future belief auto-demote from a `false` verdict
Severity: major
Sources: [claude]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:289-293, :305-309; DECISION_LOG.md (D044, D069); migrations/006_claims_beliefs.sql:472-486, :595-609
Rationale: The RFC prohibits auto-promotion/demotion in prose but does not commit that the gold-label loader must not call `engram.consolidator.transitions`, nor request a CHECK/trigger preventing `belief_audit.input_claim_ids` from referencing gold-label-derived synthetic claims; a Phase 4 review queue could re-introduce an auto-demote path that violates D044.
merged_from:
  - claude § F010

### F011 — CLI surface lacks session-listing/coverage commands needed to debug append-only failures
Severity: minor
Sources: [claude]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:194-202; src/engram/cli.py
Rationale: `start | resume | history | export` cannot enumerate active or recent sessions (so `--session-id` has nothing to discover), inspect coverage gaps, or verify under-labeled strata before a `start --strata <expr>`; the worked example shows a session id no command can list.
merged_from:
  - claude § F011

### F012 — Re-asks under the same `target_version_stamp` are uncapped and the `current_gold_label` tiebreaker is unspecified
Severity: minor
Sources: [claude, codex]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:139-142, :160-164
Rationale: Later verdicts on the same target produce new rows and the cooldown only suppresses display, but the RFC does not define the `current_gold_label` view's tiebreaker (latest, majority, confidence-weighted) and the sampler's "no prior label at current version stamp" check has to read the view rather than raw `gold_labels`; the wrong tiebreaker silently changes which signals reach Step 9.
merged_from:
  - claude § F012
  - codex § F015

### F013 — `prompt_text` storage of rendered evidence excerpts can persist Tier-1 raw text and leak via export
Severity: major
Sources: [claude, gemini]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:125, :180-184, :265-268
Rationale: The claim-question rendering rule explicitly includes "a 1-line evidence excerpt (privacy-tier-respecting)" in `prompt_text`, contradicting the privacy section's "no raw evidence text is required in the label row"; combined with the undefined export ceiling (F005), one `engram interview export` invocation can leak Tier 1 raw fragments. The RFC needs to either store evidence excerpts in a separate column, omit them for Tier 1 targets, or redact `prompt_text` above the requested ceiling.
merged_from:
  - claude § F013
  - gemini § F009

### F014 — Interaction with `current_beliefs` (Phase 4 Tier 0) is unspecified
Severity: minor
Sources: [claude]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:256-258; migrations/009_phase4_entities_review.sql:143-181
Rationale: D077's `current_beliefs` materialized view ships status filtering (excludes `superseded`/`rejected`), and the RFC's `current_gold_label` sits adjacent to it; the RFC does not state whether the sampler reads `beliefs` directly or through `current_beliefs`, which changes which beliefs ever get an interview question.
merged_from:
  - claude § F014

### F015 — Polymorphic `(target_kind, target_id)` has no real FK and no parent-validation trigger
Severity: blocking
Sources: [codex]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:117-119; migrations/006_claims_beliefs.sql:131-176, :178-237, :330-470
Rationale: A `(target_kind, target_id)` polymorphic reference cannot be enforced with a Postgres `REFERENCES` clause, and the RFC declares neither a `BEFORE INSERT` trigger that resolves `target_id` against the right parent table nor a contradictions-style mutation guard; the table will accept dangling labels — the failure mode the rest of Phase 3 protects against.
merged_from:
  - codex § F002

### F016 — `sampler_strata_key JSONB` is unindexable and admits silent strata-key drift
Severity: major
Sources: [codex]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:131-133
Rationale: A free-form JSONB strata key cannot serve the sampler's "under-labeled strata" hot-loop weighting query and lets future code introduce new keys (`recency_band`, `belief_status`) without breaking historical rows; the codebase pattern (see `predicate_vocabulary`) is a typed lookup table or split typed columns with checks.
merged_from:
  - codex § F006

### F017 — `engram interview` does not slot into RFC 0025's phase-scoped CLI surface
Severity: major
Sources: [codex]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:194-201; src/engram/cli.py:64-70, :74-75, :281-419
Rationale: Master just landed RFC 0025's command surface where every new command is either phase-scoped or a bare deprecation alias; `engram interview` is neither, so the RFC must declare a phase placement (e.g., `engram phase3 interview {start,resume,history,export}`) or carve out a cross-phase substrate row in BUILD_PHASES before the build prompt can land.
merged_from:
  - codex § F007

### F018 — Active-learning bias has no schema affordance and no operator-visible "at scale" trigger
Severity: major
Sources: [codex, gemini]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:158-172, :332-334
Rationale: The RFC ships active-learning "wired but defaulted off" with no `active_learning_signal_version` column on `gold_labels`, no concrete threshold for when the bias should turn on, no operator-facing readiness signal, and no opt-in command; the feature ships dead and, when enabled, will silently break sampler replay because the bias input is not stamped.
merged_from:
  - codex § F012
  - gemini § F007

### F019 — Worked example does not exercise contradictions-mode pilot question
Severity: nit
Sources: [codex]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:247-250; migrations/006_claims_beliefs.sql:80
Rationale: The worked example only walks the trivial single-row interview path and never exercises a contradiction-mode question (RFC § Open Q 3), which would require two `target_id`s and reveal whether the polymorphic schema can express it; deferring to v1.5 still informs schema decisions today.
merged_from:
  - codex § F013

### F020 — Cooldown defaults are deferred and `current_gold_label` view is undefined
Severity: major
Sources: [codex, gemini]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:163-164, :256, :338-340
Rationale: V1 ships with no concrete cooldown numbers per stability_class, no commitment between per-`(target, verdict)` vs per-target-any-verdict shape, and no definition of the `current_gold_label` view the cooldown depends on; the empirical-tuning posture is a hidden gate (cooldowns cannot be tuned before any session runs) and an implementer building the sampler has no anchor.
merged_from:
  - codex § F014
  - gemini § F004

### F021 — No mid-session abort path; resume/skip/Ctrl-C semantics unspecified
Severity: major
Sources: [gemini]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:97-104, :194-202
Rationale: Neither the CLI subcommand list nor the prompt-level interaction specifies what happens at `[37/50]` on Ctrl-C, `q`, or save-and-quit: whether a half-typed rationale commits, whether `skip` advances or holds the cursor, whether SIGINT mid-rationale is durable, or how the operator finds an unfinished session without remembering the session id; sessions over 30 questions will produce torn state.
merged_from:
  - gemini § F003

### F022 — "Show me everything" cooldown override has no privacy floor
Severity: major
Sources: [gemini]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:163-164, :194-202
Rationale: The cooldown override is described in prose but not in the CLI surface, has no flag name (`--ignore-cooldown` vs `--all`), and naturally extends to relaxing strata weights and `privacy_tier` ceilings; the RFC must explicitly draw the line so a cooldown override never relaxes the sampler's privacy tier filter.
merged_from:
  - gemini § F005

### F023 — Worked example lacks fatigue mitigation; rationale field is uncapped free text
Severity: minor
Sources: [gemini]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:130, :219-253
Rationale: A 50-question session at the worked-example density produces ~200 lines of terminal output and 50 free-text rationale prompts, but the prompt does not show "[Enter to skip]," there is no mid-session break/save marker, and `rationale TEXT NULL` has no soft cap or 80% warning; UX gaps drop trust after the first long session.
merged_from:
  - gemini § F006

### F024 — `skip` is structurally ambiguous against cooldown semantics
Severity: minor
Sources: [gemini]
Affects: docs/rfcs/0021-gold-set-interview-curation.md:128-129, :163-164
Rationale: `skip` could mean "ask me later" or "stop showing it," and the cooldown text does not say whether `skip` triggers suppression; without a rule the cooldown will treat `skip` like any verdict and suppress the target for N days — the opposite of the user's mental model. The RFC should either keep `skip` cooldown-free with `[skip - ask later]` labeling, or introduce a separate `never_ask`/blocklist surface.
merged_from:
  - gemini § F010

## Counts

- Total findings: 24
- Severity breakdown: blocking=3, major=15, minor=5, nit=1
- Per-reviewer contributions: claude=14, codex=15, gemini=10
