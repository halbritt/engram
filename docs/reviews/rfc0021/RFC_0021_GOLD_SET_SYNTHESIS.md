# RFC 0021 Gold-Set Interview Curation Synthesis
author: synthesizer-claude-opus-001

Status: synthesis
Date: 2026-05-08
RFC refs: RFC-0021
Decision refs: D016, D040, D044, D052, D057, D069, D073, D077, D078, F010, O008
Phase refs: PHASE-0003 (follow-on), Step 5 (gold-set authoring substrate)

## Findings outcome

| ID  | Outcome  | Reason |
|-----|----------|--------|
| F001 | accepted | Migration `008_gold_labels.sql` collides with shipped 008/009; rename to `010_gold_labels.sql` and update both schema citation and Promotion Path step 3. |
| F002 | accepted | Replace `target_version_stamp JSONB` with the typed triple `(extraction_prompt_version, extraction_model_version, request_profile_version)` for claim targets and the matching belief/belief_audit columns; add a btree index on the active triple to preserve indexed equality joins (mirrors migration 006). |
| F003 | accepted | Commit explicitly to a `fn_gold_labels_append_only` `BEFORE UPDATE OR DELETE` trigger raising `P0001`, parallel to claims/belief_audit/claim_audits. RFC prose must name the function and assert schema-level enforcement, not just policy. |
| F004 | accepted | Specify a `BEFORE INSERT` trigger that copies `privacy_tier` from the parent claim/belief at row creation time and refuses any operator-supplied tier that disagrees; for future multi-source rendering, define `privacy_tier = max(tiers across all surfaced inputs)` as the carry rule. |
| F005 | accepted | Default `engram interview export --privacy-tier-max` to `1` (fail-closed Tier 1 ceiling); higher tiers require explicit `--privacy-tier-max <N>` opt-in. Remove the "user's working tier" language since no such concept exists in Engram today. |
| F006 | accepted | Stamp both a candidate-pool snapshot id and an active-learning bias-input version on each label row; reproducibility of `(seed, sampler_version, strata_weights)` requires both. Add `active_learning_signal_version TEXT` (NULL when bias is off) per F018. |
| F007 | accepted | Add a `gold_label_sessions` parent table keyed by `session_id UUID PRIMARY KEY` carrying `(seed, sampler_id, sampler_version, strata_weights, started_at, completed_at, operator_note)`; `gold_labels.session_id` becomes a NOT NULL FK. Without it `interview resume` and the worked example are unimplementable. |
| F008 | accepted_with_modification | Add a verdict-vocabulary table parallel to `audit_reason_vocabulary` (D073) with explicit gloss for each of the six values, distinguishing `false` (claim wrong about world) from `unsupported` (evidence does not establish claim) and aligning with RFC 0018's audit-reason taxonomy. The CLI prompt in the worked example must render all six options. Defer cross-RFC mapping table to v1.5 if it expands the schema review surface. |
| F009 | accepted | Replace the split `prompt_template_id` + `prompt_template_version` columns with a single composite `prompt_template_version TEXT` matching RFC 0017's `{area}.v{N}.{date_or_decision}.{descriptor}` shape, plus a `prompt_template_path TEXT` column referencing `prompts/interview/<id>_v{N}.md`; add a CHECK linking the two if cheap. |
| F010 | accepted | Add explicit prose: "the gold-label loader must not call `engram.consolidator.transitions` (D052)"; add a CHECK or trigger preventing `belief_audit.input_claim_ids` from referencing gold-label-derived synthetic claims. Closes the D044 foothold the ledger flagged. |
| F011 | accepted_with_modification | Add `engram phase3 interview list-sessions` and `engram phase3 interview coverage --strata <expr>` as v1 CLI commands needed to debug append-only failures and discover session ids; defer richer dashboards to v2 web UI. |
| F012 | accepted | Define `current_gold_label` view tiebreaker as "latest `answered_at` per `(target_kind, target_id, version_triple)`" with verdict-rank fallback (`true`/`false`/`stale`/`unsupported` outrank `unsure`/`skip`); cap re-asks under same version triple at 3 by default with operator override. |
| F013 | accepted | Drop the "1-line evidence excerpt" from `prompt_text`; if rendered, store excerpt in a separate `evidence_excerpt TEXT NULL` column that the export path redacts whenever the row's `privacy_tier > requested ceiling`. Combined with F005 default ceiling 1, closes the leak path. |
| F014 | accepted | Sampler reads `current_beliefs` (D077) by default to honor status filtering (excludes `superseded`/`rejected`); operator override via `--include-superseded` flag for adversarial sweeps. Document explicitly in RFC. |
| F015 | accepted | Add a `BEFORE INSERT` trigger that resolves `target_id` against the right parent table per `target_kind` ('claim' → `claims`, 'belief' → `beliefs`), refusing dangling references. Mirrors `contradictions` mutation guard. Without this the polymorphic shape is unsafe. |
| F016 | accepted | Replace `sampler_strata_key JSONB` with typed columns `(stability_class TEXT, conf_band TEXT, recency_band TEXT, belief_status TEXT NULL)` plus a `gold_label_strata_vocabulary` lookup table seeded with the v1 keys; preserve a `strata_extra JSONB` for non-canonical extension keys. Pattern matches `predicate_vocabulary` (D057). |
| F017 | accepted | Move `engram interview` under `engram phase3 interview {start,resume,history,export,list-sessions,coverage}` per RFC 0025 (D078) phase-scoped command surface. The bare `engram interview` namespace is incompatible with the just-landed command contract. |
| F018 | accepted | Add `active_learning_signal_version TEXT NULL` column on `gold_labels`; specify the operator-visible "at scale" trigger as "RFC 0018 reviewer has produced ≥ N audit rows" (N defaulted to 500); add `engram phase3 interview enable-active-learning --signal-version <v>` opt-in command. The bias must not run silently. |
| F019 | deferred | Worked-example contradiction-mode question is informative but not required for v1 schema acceptance. The polymorphic `(target_kind, target_id)` shape (post-F015 fix) accommodates it; defer pilot to v1.5 per RFC's existing open question 3. |
| F020 | accepted | Set default cooldowns: `goal=14d`, `task=7d`, `mood=3d`, `preference=30d`, `relationship=60d`, `identity=90d`, `project_status=30d` per `(target, any verdict)`; per `(target, verdict)` cooldown defaults to half. Define `current_gold_label` view per F012. Empirical tuning post-v1 is fine, but v1 needs concrete starting values. |
| F021 | accepted | Specify mid-session semantics: Ctrl-C / SIGINT commits no half-typed rationale (the row is only inserted on `answered_at` write); `q` and `save-and-quit` mark the session `completed_at=NULL` (resumable); `engram phase3 interview list-sessions --state open` discovers unfinished sessions. `skip` advances cursor and inserts a `skip` verdict row (so cooldown sees it; see F024). |
| F022 | accepted | Cooldown override flag is `--ignore-cooldown` only; it must NOT relax `--privacy-tier-max` or strata-weight floors. RFC must state explicitly: "no flag combination relaxes the privacy tier ceiling below the default". |
| F023 | accepted_with_modification | Cap `rationale TEXT` at 2000 chars at the application layer with an 80%-warning prompt; show `[Enter to skip rationale]` in the worked example; defer the mid-session break/save marker UX to web v2 since CLI v1 already supports `save-and-quit` (F021). |
| F024 | accepted | `skip` is cooldown-free and labeled `[skip - ask later]` in the prompt; the cooldown rule applies only to `true|false|stale|unsupported|unsure` verdicts. A separate `never_ask` blocklist surface is deferred to v1.5; for v1, repeated skip simply re-surfaces on next session. |

## Open decisions

### O021-1 — Should the gold_label_sessions parent table land in the same migration as gold_labels?
- Option A — Single migration `010_gold_labels.sql` adds both tables and the FK in one transaction.
- Option B — Two migrations: `010_gold_label_sessions.sql` then `011_gold_labels.sql` for cleaner archaeology.
- Recommended: A
- Rationale: The session table is load-bearing for resume (F007) and FK integrity; splitting it adds a transient state where `gold_labels.session_id` cannot be added with a NOT NULL FK. Single-migration landing matches the precedent of `006_claims_beliefs.sql` (claims + beliefs + belief_audit in one file).

### O021-2 — Should current_gold_label be a view or a materialized view?
- Option A — Plain `VIEW` over `gold_labels` with a `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY answered_at DESC)` window.
- Option B — `MATERIALIZED VIEW` refreshed by a trigger or a `REFRESH MATERIALIZED VIEW` cron, parallel to `current_beliefs` (D077).
- Recommended: A
- Rationale: Gold-label volume is small (single-user, hundreds-to-thousands of rows in v1) and joins on the typed version triple (post-F002) are cheap. `current_beliefs` materialization (D077) is justified by status filtering across the entire belief surface; gold labels do not have that pressure. Defer materialization to v2 if read latency becomes hot.

### O021-3 — Should active-learning bias enabling require a separate decision-log entry?
- Option A — Enabling the bias at scale is just a CLI flag (`enable-active-learning`); no new DECISION_LOG entry required.
- Option B — Enabling the bias is a project decision (D###) since it changes the sampler's effective contract.
- Recommended: B
- Rationale: Per D044 / D069 posture, anything that re-shapes sampling or inputs to Step 9 evals warrants explicit decision-log capture. The flag is the mechanism; the activation is the decision. This also gives the active-learning signal version stamp (F018) a documented justification trail.

## Recommendation

**revise-rfc**

The ledger contains 3 blocking findings (F001 migration number, F005 fail-open privacy ceiling, F015 polymorphic FK guard) plus 15 majors that touch the schema contract directly: typed version triple (F002), append-only trigger (F003), tier-carry trigger (F004), session/run identity (F007), prompt-template versioning (F009), strata typing (F016), CLI phase scoping (F017), active-learning column (F018), cooldown defaults (F020), excerpt redaction (F013). These are not implementation details an engineer can resolve at code-review time; they are first-class schema and command-surface decisions that need to be committed in the RFC text before a build prompt can land cleanly. **revise-rfc** is the right call: amend the RFC text to incorporate the 23 accepted deltas (F019 deferred), then re-enter the acceptance phase with a clean buildable contract. The cleanest next implementation step is to apply these revisions to `docs/rfcs/0021-gold-set-interview-curation.md`, then re-run acceptance which will produce concrete deltas for migration `010_gold_labels.sql`, BUILD_PHASES Phase 3 follow-on, and a new D079 entry.

If the orchestrator prefers to short-circuit revision and proceed directly to acceptance, the alternative path is **accept-rfc** with the deltas below applied during implementation rather than during revision; this is honest but lossier (the RFC text would document the original proposal and the implementation would silently diverge). Revision is preferred for archaeology.

## Acceptance deltas (only if accept-rfc)

These are provided in case the orchestrator chooses to short-circuit revision and treat the synthesis as the de facto acceptance contract. They are *not* required when the recommendation is **revise-rfc**; revision should regenerate them.

### Migration number
Next available: `010_gold_labels.sql`. The `migrations/` listing shows `001..009` taken (with `004_segments_embeddings.sql` and `004_source_kind_gemini.sql` co-numbered, and 005-009 single-file). The next available numeric prefix is `010`. The proposed `008_gold_labels.sql` filename in RFC § Storage and § Promotion Path step 3 must be replaced with `010_gold_labels.sql` in both citations.

### BUILD_PHASES.md insert

```text
## Phase 3 follow-on — Gold-set interview curation (RFC 0021)

Continuous gold-label authoring substrate that samples from claims/beliefs and
records verdicts in append-only `gold_labels` (migration `010_gold_labels.sql`)
with a `gold_label_sessions` parent. Surfaced via `engram phase3 interview
{start,resume,history,export,list-sessions,coverage}` (RFC 0025 / D078). Labels
are advisory inputs to Step 9 evals; D044's no-auto-promote rule holds. Privacy
tier defaults to fail-closed (Tier 1 export ceiling); higher-tier export
requires explicit `--privacy-tier-max <N>` opt-in. Active-learning bias is
opt-in via `enable-active-learning` and stamps `active_learning_signal_version`
on every emitted row. Append-only enforced via `fn_gold_labels_append_only`
trigger (`BEFORE UPDATE OR DELETE`) raising P0001. Polymorphic
`(target_kind, target_id)` parent validation enforced via `BEFORE INSERT`
trigger.

**Leaves for the smoke gate:** `gold_labels` insert/append/export
round-trips against the consolidated V1 corpus; `current_gold_label` view
returns the most recent verdict per `(target_kind, target_id, version_triple)`;
no UPDATE/DELETE permitted at any tier; export with default ceiling redacts
Tier 2+ rows.
```

### DECISION_LOG.md insert

```text
| <a id="d079"></a>D079 | accepted | RFC 0021 gold-set interview curation is accepted as the continuous gold-label authoring substrate. Migration `010_gold_labels.sql` adds `gold_label_sessions` and `gold_labels` (typed version-triple columns mirroring claims/belief_audit, typed strata columns referencing `gold_label_strata_vocabulary`, append-only trigger, polymorphic parent-validation trigger, privacy-tier carry trigger). CLI surface is `engram phase3 interview {start,resume,history,export,list-sessions,coverage}` per D078. Export defaults to fail-closed Tier 1 ceiling; higher tiers require explicit `--privacy-tier-max` opt-in. Active-learning bias is opt-in (`enable-active-learning`) and stamps `active_learning_signal_version` on emitted rows. Labels are advisory inputs to Step 9 evals only; D044's no-auto-promote rule holds, and the loader must not call `engram.consolidator.transitions` (D052). | The synthesis of the RFC 0021 gold-set review run identified 3 blocking findings (migration-number collision, fail-open export ceiling, polymorphic FK guard) and 15 major findings that the accepted deltas resolve at the schema and CLI-surface layer. Without the typed version triple, indexed equality joins against `claims`/`beliefs`/`belief_audit` degrade silently. Without the append-only trigger, the table can be mutated at any tier. Without the parent-validation trigger, dangling labels are accepted. Without fail-closed export defaults, Tier 1 rows can leak on first invocation. The phase-scoped CLI placement aligns with D078's just-landed command-surface contract. Active-learning gating prevents silent replay-divergence per F006/F018. | The accepted deltas land in a new RFC 0021 revision before migration 010 is written; the implementation prompt targets the revised RFC text. The CLI commands must register under `engram phase3 interview` (RFC 0025) and not as bare `engram interview`. `current_gold_label` is a plain VIEW in v1; materialization deferred. Cooldown defaults are committed in the RFC body and tunable post-v1. The `gold_label_sessions` table is load-bearing for `interview resume` and `list-sessions`. | Revisit when the gold-label volume justifies materialization, when active-learning is enabled at scale (separate decision per O021-3), when contradiction-mode questions (RFC § Open Q 3) move to v1.5 implementation, or when the web UI replaces CLI v1 as the primary surface. |
```

## Risks the synthesis carries

- **F008 partial deferral.** The synthesis accepts adding a verdict-vocabulary table but defers a cross-walk to RFC 0018's `audit_reason_vocabulary`; if Step 9 consumers cannot mechanically distinguish "fact-correction" from "trace-broken" signal without that mapping, the gloss alone may not be enough. The ledger called for both gloss and parallel-table; the synthesis chose gloss-now, mapping-later.
- **F011 minimal CLI surface.** The synthesis adds `list-sessions` and `coverage` but nothing richer (e.g., `inspect-strata-balance`, `dry-run`); if operators need deeper introspection to debug append-only or sampler regressions, v1 will feel undersupplied. The ledger flagged this as minor; if a Phase 3 follow-on operator hits a debugging wall, a v1.1 CLI expansion is cheap.
- **F018 active-learning gate threshold.** The synthesis picks "RFC 0018 reviewer has produced ≥ 500 audit rows" as the operator-visible at-scale trigger; this number is not grounded in measurement. If 500 is too low, bias engagement on noisy reviewer scores can degrade sampler quality. If too high, the bias never enables on a single-user corpus. Empirical tuning is required and should be flagged in the v1 build prompt.
- **F020 cooldown defaults.** The synthesis commits concrete cooldown values per stability class (`goal=14d`, `task=7d`, ...) without any usage data; these are best-guess starting points and will almost certainly need tuning. Implementation prompt should make these tunable via env-var (`ENGRAM_GOLD_COOLDOWN_*`) per the Python coding standard.
- **F015 polymorphic-FK trigger correctness.** The synthesis prescribes a `BEFORE INSERT` trigger that branches on `target_kind` and queries the corresponding parent table; this trigger has a non-trivial test surface (parent deleted vs missing vs version-mismatch vs cross-tenant in a single-user system). The implementation phase must include explicit test cases for each branch.
- **Revision vs acceptance decision.** The synthesis recommends revise-rfc, but the user's autonomous mandate is to accept and implement. If the orchestrator overrides to accept-rfc directly, the acceptance deltas above must be applied verbatim during implementation; any drift between RFC text and implementation will create archaeology problems for future review rounds.
- **D052 transition-API exclusion.** The synthesis accepts F010 by adding prose forbidding the gold-label loader from calling `engram.consolidator.transitions`; this is a code-review invariant, not a schema-enforced one. A future refactor that wraps the loader in a "convenience helper" can re-introduce the path. A stronger but more invasive option (separate DB role / GUC for the loader) was not chosen to avoid cross-cutting D052.
