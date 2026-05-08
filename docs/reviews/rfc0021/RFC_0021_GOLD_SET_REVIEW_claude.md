# RFC 0021 Gold-Set Interview Curation Review — claude
author: reviewer-claude-opus-001

Status: review
Date: 2026-05-08
RFC refs: RFC-0021
Decision refs: D016, D040, D043, D044, D052, D056, D069, D074, D077, F010, O008
Phase refs: PHASE-0003, PHASE-0004

## Findings

### F001 — `008_gold_labels.sql` filename collides with migrations already in tree
Severity: blocking
Source: docs/rfcs/0021-gold-set-interview-curation.md:113; docs/rfcs/0021-gold-set-interview-curation.md:351; migrations/008_claim_extractions_request_profile_unique.sql; migrations/009_phase4_entities_review.sql
Rationale: The RFC names the new migration `008_gold_labels.sql` in both the schema section (line 113) and the promotion path (line 351). On disk, `migrations/008_claim_extractions_request_profile_unique.sql` is already in tree and `migrations/009_phase4_entities_review.sql` ships Phase 4 Tier 0 (D077). The next available slot is **`010_gold_labels.sql`**. Forward-only migrations cannot reuse a number; landing this RFC as written would silently shadow the request-profile uniqueness migration in any environment that has not yet applied 008/009. Fix the literal filename in the RFC before promoting, and add a one-line "next-available" rule so future RFCs do not repeat the mistake.

### F002 — `target_version_stamp JSONB` weakens the join contract against `claims`/`beliefs`/`belief_audit`
Severity: major
Source: docs/rfcs/0021-gold-set-interview-curation.md:120-124; migrations/006_claims_beliefs.sql:155-157,218-219,256-258; migrations/007_claim_audits.sql:46-47
Rationale: The RFC stores the version stamp as a free-shape JSONB blob, but the existing schema commits to typed columns: `claims.extraction_prompt_version / extraction_model_version / request_profile_version` (006_claims_beliefs.sql:155-157), `beliefs.prompt_version / model_version` (lines 218-219), `belief_audit.{prompt,model}_version` (lines 256-258), and the audit-cascade pattern uses `auditor_prompt_version` / `auditor_model_version` columns (007_claim_audits.sql:46-47). JSONB defeats CHECK constraints, FK-style validation, and indexed equality on the version triple — the exact join key Step 9 re-extraction cycles (D016) need. Beliefs lack a `request_profile_version` of their own (it lives only on `belief_audit`), so the JSONB cannot uniformly represent both target kinds without ambiguity. Replace with five typed columns (or two pairs + one stamp-kind discriminator), mirroring the audit cascade's column shape.

### F003 — Append-only is asserted but not enforced; the RFC has no trigger spec analogous to `claim_audits`/`belief_audit`
Severity: major
Source: docs/rfcs/0021-gold-set-interview-curation.md:139-141,274-275; migrations/006_claims_beliefs.sql:472-486,595-609; migrations/007_claim_audits.sql:104-118
Rationale: The RFC says "Append-only. No `UPDATE`/`DELETE` enforcement matches the raw-evidence discipline" (line 139) but does not specify the enforcement mechanism. `claims` (006:472-486), `belief_audit` (006:595-609), and `claim_audits` (007:104-118) all carry explicit `BEFORE UPDATE OR DELETE` triggers that raise. Without an equivalent trigger on `gold_labels`, the only enforcement is the prose; a downstream `UPDATE gold_labels SET verdict='true' WHERE rationale LIKE '%mistake%'` would succeed silently. Given the privacy-tier-carrying nature of these rows, the enforcement must be schema-level. Specify `fn_gold_labels_append_only()` in the RFC text so the migration author lands it on first pass.

### F004 — `privacy_tier INT` lacks `IS NOT NULL` carry rule and lacks any "max over inputs" semantics, leaving Tier 1 leakage on multi-source labels possible
Severity: major
Source: docs/rfcs/0021-gold-set-interview-curation.md:136,265-268; migrations/006_claims_beliefs.sql:181,220; HUMAN_REQUIREMENTS.md:607-616
Rationale: HUMAN_REQUIREMENTS.md:607-616 names Tier 1 "only me, only on this machine" and says health/finances/beliefs default Tier 1 with explicit promotion only. The RFC's `privacy_tier` column declares `NOT NULL` (line 136) and the prose says "carried from target row," but `claims.privacy_tier` is per-segment max (006:181) and `beliefs.privacy_tier` is max over contributing claims (006:220). The interview agent renders evidence excerpts (line 181) and date spans (line 184) into `prompt_text`, which is also stored in the row. If the prompt template ever expands to include rationale text quoted from a Tier-1 belief while the label row inherits the *belief's* tier (already Tier 1), that's fine — but if a reviewer ever introduces a belief→claim drill-down that joins more permissive claims, the carry rule must be `max(tier across all surfaced inputs)`, not "tier of the chosen target." Spec the rule explicitly: `privacy_tier = max(tiers of every row whose content reaches prompt_text)`.

### F005 — `--privacy-tier-max` ceiling defaults to "user's working tier" but no such concept exists in V1; export risks defaulting to tier=1 ceiling and leaking by default
Severity: major
Source: docs/rfcs/0021-gold-set-interview-curation.md:200-202; HUMAN_REQUIREMENTS.md:607-616
Rationale: Line 202 says "default tier ceiling matches the user's working tier." Engram has no "working tier" concept anywhere — `privacy_tier` is per-row, and there is no session/profile state recording a current ceiling. If an implementer reads "matches the user's working tier" as "the highest tier the user can see" they will default to Tier 1 (the lowest restriction), which means **every interview verdict touching Tier 1 content leaves the machine on `engram interview export`**. The RFC must either (a) define "working tier" with a concrete column or env var, or (b) hard-default `--privacy-tier-max=2` (or whatever Tier 2's "surfaceable to AI assistants" maps to) and require an explicit `--allow-tier 1` flag with a confirm prompt, mirroring D044's "no automatic anything" stance.

### F006 — Sampler determinism contract is contradicted by "active-learning bias" reading mutable downstream state
Severity: major
Source: docs/rfcs/0021-gold-set-interview-curation.md:152-171
Rationale: The RFC promises "the sampler is seeded; the sampler ID + version + seed + strata weights are stamped on each emitted question so an interview pass is reproducible" (lines 165-167). But the active-learning bias source is RFC 0018 reviewer scores ("targets near the decision boundary of any existing local reviewer"; line 159) and "no prior `gold_labels` row at the current `target_version_stamp`" (line 160). Both inputs are time-varying: re-running the same `(seed, strata weights, sampler version)` after one new `claim_audits` row insert produces a different question sequence. The RFC's defense — "active-learning bias is wired but defaulted off until RFC 0018 reviewer output exists at scale" (line 170) — is consistent with V1, but the RFC does not say a sampler **with the bias on** is no longer reproducible from `(seed, version)` alone. Either (a) capture the active-learning input snapshot in the stamped `sampler_strata_key` so replay is deterministic, or (b) explicitly document that determinism only holds with bias=off.

### F007 — Per-question session/run id is absent; `sampler_strata_key JSONB` is the only place a session can hide
Severity: major
Source: docs/rfcs/0021-gold-set-interview-curation.md:131-133,221-222
Rationale: The proposed schema has `sampler_id`, `sampler_version`, and `sampler_strata_key` (lines 131-133), but no session id column. The worked example (line 221) shows `session: gl-sess-2026-05-07-00`, which has nowhere to live — it would have to be smuggled inside `sampler_strata_key` JSONB (the same column the strata expression occupies). That blocks replay (no per-session reproducibility), `engram interview resume --session-id` (line 198 — the CLI command relies on a column that does not exist), and per-session audit. Add `session_id UUID NOT NULL` and either a `gold_label_session` parent table (preferred) or a documented convention that `session_id` is generated client-side at `start`.

### F008 — Verdict vocabulary conflates two different defects: `false` vs `unsupported`
Severity: minor
Source: docs/rfcs/0021-gold-set-interview-curation.md:128-129; docs/rfcs/0018-evidence-to-claim-audit-cascade.md:174-182,261-273
Rationale: RFC 0018's Stage 2 distinguishes `partial` (some weak axes but core fact grounded) from `invalidated` (trace broken or evidence contradicts). RFC 0021's verdict enum is `('true','false','stale','unsupported','unsure','skip')`. Without a definitions block, an interviewer cannot tell whether `false` means "the claim is wrong about the world" or "the claim is wrong about *this* evidence" — those map to different RFC 0018 reasons (`value_mismatch` vs `trace_broken`). Step 9 re-extraction loops will silently merge them, undermining the "is the prompt wrong vs is the world different" diagnosis the gold set is supposed to enable. Add a definitions table mapping each verdict to a primary RFC 0018 audit reason, and split `false` into `false_world` (contradicted by user's lived knowledge) vs `false_evidence` (claim does not follow from the cited messages) — or document a deliberate decision to collapse them.

### F009 — RFC 0017 versioning fit is asserted but the path convention is wrong
Severity: minor
Source: docs/rfcs/0021-gold-set-interview-curation.md:188-190; docs/rfcs/0017-extraction-prompt-versioning.md:64-75
Rationale: The RFC says interview templates "live under `prompts/interview/`" (line 188) and follow RFC 0017 versioning. RFC 0017 §"Storage" specifies `prompts/<area>/<id>_v{N}.md` immutable per version (lines 64-75). RFC 0021 should commit to `prompts/interview/<template_id>_v{N}.md` (e.g., `prompts/interview/belief_currentness_v1.md`) and to the `{area}.v{N}.{date_or_decision}.{descriptor}` version-string format the extractor already uses. Without that, `prompt_template_id` and `prompt_template_version` become unbounded free-text strings and the join from a label row to its rendering prompt is unverifiable.

### F010 — D044 wording leaves a foothold for a future implementer to flip belief status from a `false` verdict
Severity: major
Source: docs/rfcs/0021-gold-set-interview-curation.md:289-293,305-309; DECISION_LOG.md (D044, D069); migrations/006_claims_beliefs.sql:472-486,595-609
Rationale: The RFC says "no auto-promotion or auto-demotion of beliefs from gold labels. A `false` verdict does **not** flip belief status; it produces signal for Step 9 re-extraction cycles" (lines 290-293). Good — but the same paragraph leaves Stage 2 ambiguity: the audit cascade RFC 0018 reads gold labels as input (line 286) and a future Phase 4 review queue or auto-resolver could be tempted to interpret `(verdict=false, audit=invalidated)` as "demote." The schema enforces `engram.transition_in_progress` (006:499-504) for belief mutations, but it does not gate on caller identity. Strengthen the RFC's prohibition by (a) committing that the gold-label loader code MUST NOT call `engram.consolidator.transitions` at all, and (b) requesting a CHECK or trigger signal that a `belief_audit` row's `input_claim_ids` cannot reference a gold-label-derived synthetic claim. Otherwise this becomes a lurking D044 violation the moment someone wires "auto-demote" into a Phase 4 build prompt.

### F011 — `engram interview` CLI surface lacks status/run-listing commands required to debug append-only failures
Severity: minor
Source: docs/rfcs/0021-gold-set-interview-curation.md:194-202; src/engram/cli.py
Rationale: The four subcommands (`start | resume | history | export`) cover happy-path label production and replay, but offer no way to (a) list active or recent sessions (RFC's `--session-id <id>` arg has nothing to enumerate), (b) inspect coverage gaps the sampler is producing, (c) verify which strata are under-labeled before a `start --strata <expr>`. The RFC explicitly defers UX to the web surface (line 211), but the listed commands cannot smoke-test the sampler+storage contract on their own — the worked example shows a session id that no command can list. Add `engram interview list-sessions` and `engram interview coverage` (or document explicitly that those land in v1.5).

### F012 — Re-asks under the same `target_version_stamp` are uncapped and produce silent ballot-stuffing
Severity: minor
Source: docs/rfcs/0021-gold-set-interview-curation.md:139-141,162-164
Rationale: "Re-derivation of 'current verdict per target' is a view, not a table" (line 142) plus "later verdicts on the same target produce new rows" (line 140) plus the cooldown only suppressing display (line 163) means a user can answer the same `(target_id, target_version_stamp)` ten times in ten sessions and the view definition determines whose vote counts. The RFC does not specify the `current_gold_label` view's tiebreaker (latest by `answered_at`? majority by verdict? confidence-weighted?). For `false`/`stale` verdicts feeding Step 9, the wrong tiebreaker silently changes which signals reach re-extraction. Specify the view definition (`SELECT DISTINCT ON (target_kind, target_id, target_version_stamp) ... ORDER BY answered_at DESC` is the natural default), and either cap re-asks or surface verdict drift as an explicit signal.

### F013 — `prompt_text` storage of rendered evidence excerpt risks Tier-1 raw-text duplication into the gold-label row
Severity: minor
Source: docs/rfcs/0021-gold-set-interview-curation.md:125,180-184,265-268
Rationale: `prompt_text TEXT NOT NULL` (line 125) plus the rendering rules ("a 1-line evidence excerpt (privacy-tier-respecting)" for claims, line 181) means raw evidence text snippets land in `gold_labels.prompt_text`. The privacy-tier carry on the row covers the field, but the RFC's privacy section says "no raw evidence text is required in the label row" (line 267) — which is contradicted by line 181's rendering rule. Either (a) commit to "evidence count + date span only, never raw text" for the rendered prompt (matching the belief case), or (b) document that label rows can carry quoted Tier-1 raw text and adjust the export ceiling default accordingly. As written the two paragraphs disagree.

### F014 — RFC does not state how `gold_labels` interacts with `current_beliefs` (Phase 4 Tier 0, already shipped)
Severity: minor
Source: docs/rfcs/0021-gold-set-interview-curation.md:256-258; migrations/009_phase4_entities_review.sql:143-181
Rationale: D077 has already shipped `current_beliefs` as a status-aware materialized view (009:143-181). RFC 0021 was authored 2026-05-07; Phase 4 Tier 0 landed in the same window. The RFC's "after-session" view name `current_gold_label` (line 256) sits adjacent to `current_beliefs` and could plausibly want to join through it (e.g., "show me unlabeled accepted beliefs"). The RFC is silent on whether the sampler reads `beliefs` directly or through `current_beliefs`. Sampling through the view picks up status filtering (it excludes `superseded`/`rejected`); sampling through the base table does not. Pin this — the choice changes which beliefs ever get an interview question.

## Open questions

- Should the gold-label loader run in a Postgres role that lacks `UPDATE`/`DELETE` on `gold_labels`, in addition to the trigger? Defense in depth costs little and matches the F010 concern.
- Is the `current_gold_label` view a plain view, materialized view, or `LATERAL` join helper? Phase 4's `current_beliefs` chose materialized for read latency; gold labels may be small enough for a regular view, but the RFC should say which.
- Does `engram interview export` write to a path under `docs/operations/<area>/<loop>/reports/` (per D074's directory home) or to a free-form `--out` path? The RFC says "local-only export" but doesn't pick a home; downstream eval runners need to know.
- Does a verdict on a `claim` propagate any signal to the belief that consolidator built from it, or are the two completely orthogonal? RFC 0018 wires Stage 2 verdicts into `belief_audit.score_breakdown`; RFC 0021 should say whether gold labels do the same.
- What is the migration strategy if the predicate vocabulary expands under a new RFC and a previously-labeled claim's `target_version_stamp` becomes inadmissible — are old labels still queryable, do they need a `superseded_by` column, or do they remain valid forever as historical signal?
- How does this loop interact with `context_feedback` (HUMAN_REQUIREMENTS § "context_feedback is the eval set extending itself") at Step 9 — does the merge happen at export time, or do they remain separate signal streams the eval runner unions?

verdict: needs_revision

