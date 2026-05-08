# RFC 0021 Gold-Set Interview Curation Final Review
author: reviewer-codex-gpt-5.5-002

Status: final-review
Date: 2026-05-08
RFC refs: RFC-0021
Decision refs: D016, D040, D044, D052, D057, D069, D073, D077, D078, F010, O008
Phase refs: PHASE-0003 (follow-on), Step 5 (gold-set authoring substrate)

## Audit findings

### A001 — Synthesis-to-ledger consistency holds across all 24 findings
Severity: nit
Source: `RFC_0021_GOLD_SET_SYNTHESIS.md` § Findings outcome; `RFC_0021_GOLD_SET_FINDINGS_LEDGER.md` F001-F024
Rationale: Every ledger entry is reflected in the outcome table with a reason aligned to its severity. The three blocking findings (F001 migration collision, F005 fail-open Tier-1 export, F015 polymorphic FK guard) are each accepted with concrete, schema-level remediations rather than prose patches. The 15 majors all carry concrete schema/CLI deltas (typed triple, append-only trigger, tier-carry trigger, session table, prompt-template versioning, strata typing, CLI scoping, active-learning column, cooldown defaults, excerpt redaction, sampler reads `current_beliefs`, mid-session semantics, override-floor, D044 foothold closure). The two `accepted_with_modification` choices (F008 vocabulary table without cross-RFC mapping; F011 minimal CLI surface; F023 fatigue prompts with web-UI deferral) all explain the deferred slice and connect it to a v1.5/v2 surface, which matches the ledger's minor/major framing without escalating scope. The single `deferred` choice (F019 contradiction-mode worked example) maps to the RFC's pre-existing Open Question 3 and does not block schema acceptance once F015 lands.

### A002 — `revise-rfc` is the conservative-but-defensible recommendation
Severity: minor
Source: `RFC_0021_GOLD_SET_SYNTHESIS.md` § Recommendation; ledger F001/F005/F015 (blocking)
Rationale: With three blocking findings that each touch the schema contract, a defensible `accept-rfc` path was available because the synthesis ships fallback acceptance deltas (migration number, BUILD_PHASES insert, DECISION_LOG D079 entry) that resolve the blockers at implementation time. The synthesis's own narrative concedes this in its second paragraph and frames the choice as archaeology preference rather than correctness. `revise-rfc` is the cleaner choice given (a) the RFC text currently still cites `008_gold_labels.sql`, the wrong export ceiling phrasing, and the bare `engram interview` namespace (incompatible with the just-landed RFC 0025 / D078 contract), and (b) committing 23 deltas would otherwise have to live as out-of-band synthesis amendments rather than in `docs/rfcs/0021-...`. Either path is supportable; the synthesis's choice is grounded.

### A003 — Privacy invariants are preserved and tightened
Severity: nit
Source: `RFC_0021_GOLD_SET_SYNTHESIS.md` F004, F005, F013, F022; HUMAN_REQUIREMENTS § privacy tier carry
Rationale: The privacy-tier carry rule is upgraded from RFC prose ("carried from target row") to a `BEFORE INSERT` trigger that copies tier from the parent and refuses operator-supplied disagreement (F004), with a `max(tiers across all surfaced inputs)` rule for future multi-source rendering. Export defaults to fail-closed Tier 1 ceiling with explicit `--privacy-tier-max <N>` opt-in (F005), redacts `evidence_excerpt` above ceiling (F013), and the cooldown override is explicitly bounded to never relax the tier ceiling (F022). The no-egress invariant is unchanged: sampler, agent, and storage remain local; export is a local-only file emission. None of the deltas introduce a network call, a hosted service, or a path that demotes privacy below the parent row's tier.

### A004 — D044 / D069 advisory-only stance is preserved and hardened
Severity: nit
Source: `RFC_0021_GOLD_SET_SYNTHESIS.md` F010; ledger F010; RFC 0021 § "What this RFC does not propose"; DECISION_LOG D044, D069
Rationale: F010's accepted delta closes the foothold the ledger flagged: explicit RFC prose forbids the gold-label loader from calling `engram.consolidator.transitions` (D052), and a CHECK or trigger prevents `belief_audit.input_claim_ids` from referencing gold-label-derived synthetic claims. The DECISION_LOG D079 fallback entry repeats the no-auto-promote rule and re-cites D044. Gold labels remain advisory inputs to Step 9 evals; they do not gate extraction or consolidation, and a `false` verdict does not flip belief status. The synthesis's own Risks section flags that F010's prohibition is a code-review invariant rather than a schema-enforced one, which is honest provenance for the boundary case but does not undermine the invariant.

### A005 — Acceptance deltas are concrete and reconcile with current repo state
Severity: minor
Source: `RFC_0021_GOLD_SET_SYNTHESIS.md` § Acceptance deltas; `migrations/` listing; `BUILD_PHASES.md`; `DECISION_LOG.md`
Rationale: The migration-number delta (`010_gold_labels.sql`) reconciles with the actual `migrations/` directory, which contains 001-009 with `004` co-numbered between `004_segments_embeddings.sql` and `004_source_kind_gemini.sql`; the next free numeric prefix is indeed 010. The BUILD_PHASES insert is phase-aligned to "Phase 3 follow-on" (consistent with the RFC's PHASE-0003 ref and ROADMAP Step 5) and names the trigger function `fn_gold_labels_append_only` to mirror the existing claims/belief_audit/claim_audits convention. The DECISION_LOG D079 row carries the four-column `accepted | summary | rationale | revisit` structure used elsewhere and binds the CLI surface to D078 (RFC 0025). The deltas are buildable as written.

### A006 — Implementation readiness is sufficient for the revise-and-rebuild flow
Severity: minor
Source: `RFC_0021_GOLD_SET_SYNTHESIS.md` § Findings outcome; § Acceptance deltas
Rationale: An RFC author handed the 23 accepted-deltas table can produce a buildable revision: schema columns are spelled out (typed triple, typed strata columns + `gold_label_strata_vocabulary`, `evidence_excerpt`, `active_learning_signal_version`, `session_id` FK), trigger names are committed (`fn_gold_labels_append_only` + tier-carry + parent-validation), CLI surface is named (`engram phase3 interview {start,resume,history,export,list-sessions,coverage}` + `enable-active-learning`), tiebreaker for `current_gold_label` is defined, cooldown defaults are concrete (`goal=14d`, etc.), and mid-session SIGINT/skip/save-and-quit semantics are pinned. The remaining empirical gaps (cooldown numbers, active-learning threshold of 500) are explicitly flagged as tunable post-v1 in the Risks section, which matches the Python coding standard's `ENGRAM_`-prefixed env-var pattern.

### A007 — Provenance carry uses RFC, decision, and phase references correctly
Severity: nit
Source: `RFC_0021_GOLD_SET_SYNTHESIS.md` header; cited deltas
Rationale: D044 (no auto-promote), D052 (consolidator transitions API), D057 (predicate-vocabulary lookup-table pattern), D069 (advisory cascade), D073 (audit-reason vocabulary parallel), D077 (current_beliefs materialized view), D078 (phase-scoped CLI surface), and F010 / O008 (gold authorship deferral and authorship model open question) are each cited where their content actually lands. RFC 0017 is invoked for the prompt-template version-string convention, RFC 0018 for the audit-reason taxonomy, and RFC 0025 for command surface. PHASE-0003 follow-on placement matches the RFC's existing phase ref. No fabricated decisions or phase numbers; the references stay grounded.

### A008 — Risks section honestly enumerates the deltas the synthesis carries
Severity: nit
Source: `RFC_0021_GOLD_SET_SYNTHESIS.md` § Risks the synthesis carries
Rationale: The synthesis explicitly flags six residual risks: F008 partial cross-walk deferral, F011 minimal CLI surface, F018 ungrounded 500-row threshold, F020 untuned cooldown defaults, F015 trigger test surface, the revise-vs-accept decision under autonomous mandate, and F010's code-review-only prohibition on the consolidator transitions API. None of these rise to a blocker but each is the right thing to name. The note about autonomous-mandate override behavior is especially useful: if the orchestrator chooses `accept-rfc`, it has the verbatim deltas to apply; if it chooses `revise-rfc`, the regeneration path is clean.

verdict: accept_with_findings
