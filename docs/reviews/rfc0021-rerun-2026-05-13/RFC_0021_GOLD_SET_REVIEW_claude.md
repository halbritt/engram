---
schema_version: "striatum.finding.v1"
artifact_kind: "finding"
verdict_intent: "accept_with_findings"
severity: "medium"
---

author: operator [self-declared: rfc0021-review-claude]

# RFC 0021 Gold-Set Interview Curation Review — claude

Status: review
Date: 2026-05-13
RFC refs: RFC-0021, RFC-0011, RFC-0017, RFC-0018, RFC-0025
Decision refs: D020, D044, D052, D057, D069, D073, D077, D078, D079
Phase refs: PHASE-0003

This is the rerun review requested by the RFC 0032 follow-on; the prior
multi-lane review evidence under `docs/reviews/rfc0021/` is quarantined for
provenance reasons and was not consulted as authoritative. The reading is of
the current `docs/rfcs/0021-gold-set-interview-curation.md` text against
`migrations/006_claims_beliefs.sql`, `migrations/007_claim_audits.sql`,
`migrations/010_gold_labels.sql`, and the present `src/engram/cli.py` /
`src/engram/interview/` surface. The RFC is already `accepted` with
`Implementation: scaffolded` and D079 records the prior synthesis; this review
treats it as a re-confirmation pass rather than a fresh decision.

## Summary

The RFC's privacy posture, append-only discipline, D044 alignment, sampler
opt-in bias gating, and phase-scoped CLI surface are all sound and
schema-enforced. The two real gaps are (a) a delta between the RFC text and
migration 010 around a fourth named trigger
(`fn_gold_labels_block_synthetic_audit_input`) and (b) overstated reproducibility
claims for `candidate_pool_snapshot_id`. One smaller schema-fit concern is
worth a note in the RFC body even if it does not change the migration: the
"belief version triple" the RFC asserts as the join target for indexed equality
joins is not actually present on `beliefs` or `belief_audit` at the
`request_profile_version` axis.

Verdict: **accept_with_findings**. The architecture is settled and shipped;
the findings below are RFC-text accuracy nits, one trigger gap, and an open
question about pool-snapshot semantics that should be answered before
"replay" is described as a hard guarantee.

## Findings

### F001 — Fourth named trigger (`fn_gold_labels_block_synthetic_audit_input`) is in the RFC but not in migration 010
Severity: major
Source: `docs/rfcs/0021-gold-set-interview-curation.md:219-222`,
`docs/rfcs/0021-gold-set-interview-curation.md:529-535` vs
`migrations/010_gold_labels.sql:162-276`

The RFC § Storage / Triggers names four schema-level triggers (append-only,
privacy-tier carry, target validation, and
`fn_gold_labels_block_synthetic_audit_input`). The Relationship-to-other-artifacts
section repeats the invariant: "a CHECK / trigger prevents
`belief_audit.input_claim_ids` from referencing any gold-label-derived
synthetic claim". Migration 010 implements three of those four
(`fn_gold_labels_append_only`, `fn_gold_labels_carry_privacy_tier`,
`fn_gold_labels_validate_target`). The fourth is absent — and would in any
case have to attach to `belief_audit` rather than `gold_labels`, which is
outside the RFC's stated `gold_labels`-only write scope.

The substantive control (D044) is layered: (1) the RFC forbids the loader
from calling `engram.consolidator.transitions`; (2) the gold-label table never
inserts claims, so synthesizing a claim from a label requires writing to
`claims`, which is insert-only and itself has a parent-trigger chain; (3) any
`belief_audit.input_claim_ids` element has to resolve to a real `claims.id`
via FK / harness contract. So in practice the invariant is enforced by the
absence of a code path, not by a trigger. That is acceptable for V1, but the
RFC overstates what migration 010 does. Either drop the trigger naming from
the RFC and call out the loader-discipline + insert-only-claims chain as the
mechanism, or schedule the trigger as a follow-up migration referenced by
RFC. Without one of those, future implementers can read the RFC and search
the schema for an enforcement they expect to exist.

### F002 — `candidate_pool_snapshot_id` does not actually anchor replay against corpus drift
Severity: major
Source: `docs/rfcs/0021-gold-set-interview-curation.md:175`,
`docs/rfcs/0021-gold-set-interview-curation.md:296-307`,
`src/engram/interview/sampler.py:15-16,140-457`

The RFC explicitly justifies the snapshot id with: "the full set is what
makes a session re-derivable; without the snapshot id, replay drifts as the
corpus grows." But the implementation only generates a fresh UUID per
`sample()` invocation and stamps it onto emitted rows — there is no
`candidate_pools` materialization table, and the snapshot id is not a
content hash. Two sessions seeded identically against a different corpus
state will get different pool contents and different `candidate_pool_snapshot_id`
values, but the UUID has no way to identify "the pool I'd need to reproduce
this." Replay reproducibility today rests entirely on the `gold_label_session_targets`
table introduced in migration 011 (RFC 0027), which materializes the
*sampled order*, not the wider candidate pool from which the sample was
drawn.

This is fine for v1 — re-rendering a session from materialized targets is
enough to keep CLI and web in sync — but the RFC's framing claims more than
the schema delivers. Two suggested fixes (either is sufficient):

1. Reframe the snapshot id as a "session-instance tag" rather than as a
   replay anchor, and point readers to `gold_label_session_targets` as the
   actual re-derivation surface.
2. Define a `gold_label_candidate_pools(snapshot_id UUID PK, captured_at,
   sampler_id, sampler_version, member_ids UUID[])` table and have the
   sampler insert a row before drawing. This makes the replay claim load-bearing
   instead of aspirational.

The RFC text as it stands sets up future implementers to add a snapshot table
when they discover replay drift and find the existing UUID column is empty
of content. Better to name that explicitly now.

### F003 — Belief-side `request_profile_version` has no canonical join target
Severity: major
Source: `docs/rfcs/0021-gold-set-interview-curation.md:150-157`,
`docs/rfcs/0021-gold-set-interview-curation.md:196-199`,
`docs/rfcs/0021-gold-set-interview-curation.md:514-518`,
`migrations/006_claims_beliefs.sql:239-264` (`belief_audit`)

The RFC defends the typed version-triple columns by saying they "mirror the
columns on `claims` (RFC 0011) and `belief_audit` (RFC 0011 Stage B / RFC
0018) so equality joins against the canonical version stamps stay indexed."
For claims, the triple
`(extraction_prompt_version, extraction_model_version, request_profile_version)`
lines up with `claims` 1:1. For beliefs, however, `belief_audit` carries
`prompt_version` and `model_version` but **not** `request_profile_version`
(see `migrations/006_claims_beliefs.sql:239-264`), and `beliefs` doesn't
carry the request profile either. So
`idx_gold_labels_belief_triple` indexes a third column that does not exist
on any canonical join target on the belief side; the only thing it can join
against is the request profile the *interview* loader chose to stamp, which
is by definition local to the interview session, not to the consolidator.

This is fine if the intent is "interview-side request profile, recorded for
audit", but the RFC reads as if `request_profile_version` is part of the
canonical belief version-stamp on `belief_audit`, which it isn't. Either:

1. Update the § Relationship / RFC 0011 paragraph to say belief-side
   `request_profile_version` is interview-side metadata and *not* a belief
   version-stamp axis; or
2. Add `request_profile_version` to `belief_audit` in a follow-up RFC so the
   triple is symmetric across claim and belief sides.

This is a doc-and-intent issue rather than a runtime defect — the column is
populated, the index is fine — but the rationale paragraph misrepresents the
schema.

### F004 — Evidence-excerpt redaction is described as a separate step but is structurally subsumed by the row-level filter
Severity: minor
Source: `docs/rfcs/0021-gold-set-interview-curation.md:494-499`,
`src/engram/cli.py:2154-2217`

§ Privacy says: "The export path drops `evidence_excerpt` on any row whose
`privacy_tier` exceeds the requested ceiling." But the export query is
`SELECT ... FROM gold_labels WHERE privacy_tier <= %s`; rows above the
ceiling are filtered, so there is no row left on which the excerpt would
need to be separately stripped. This is benign — the policy is more
restrictive than needed — but a future reader trying to reason about a
contradiction-mode question (where `privacy_tier = max(tiers across all
surfaced inputs)`) might add a separate "strip excerpt but keep the row"
code path expecting it to already exist.

Suggested fix: reword to say "the row-level `WHERE privacy_tier <= ceiling`
filter is the export's only privacy gate; multi-source contradiction-mode
rendering will need a separate excerpt-stripping step when its ceiling
inversion is in play, and that work is deferred with v1.5 contradiction-mode."

### F005 — `unsupported` vs `false` orthogonality is real but uncalled-out
Severity: minor
Source: `docs/rfcs/0021-gold-set-interview-curation.md:225-241`,
`migrations/010_gold_labels.sql:58-71`

The verdict vocabulary collapses two orthogonal axes — world-truth and
evidence-grounding — onto a single string. A claim can be `unsupported` and
also `true` in the world; the user has to pick one. The RFC acknowledges
this implicitly by reserving the cross-walk to `audit_reason_vocabulary` for
v1.5, but the prompt-side does not warn the user that the verdicts are not
mutually exclusive. For v1, the operator is the user — so this is mostly a
documentation issue — but Step 9 consumers will eventually have to handle
"the user marked it false, but the evidence is fine" vs "the user marked it
unsupported, but it's true." A short § Verdict-vocabulary semantics note
naming the axis collapse explicitly would help. Not a blocker; the gloss
column on `gold_label_verdict_vocabulary` is fine as-is for v1.

### F006 — RFC text still references migration `010_gold_labels.sql` correctly, but the prompt's "008" concern is outdated
Severity: nit
Source: `docs/rfcs/0021-gold-set-interview-curation.md:619-621`,
`migrations/010_gold_labels.sql` exists, `migrations/011_gold_label_session_targets.sql`
exists, `migrations/012_predicate_subject_kind_hint.sql` exists,
`migrations/013_interview_active_learning_state.sql` exists

The review prompt asks whether the RFC should "be amended to call out
renumbering" because the RFC originally named `008_gold_labels.sql`. The
current RFC text correctly says `010_gold_labels.sql`, and the file is
landed. The implementation has continued through migrations 011–013, all
under the RFC 0021 / RFC 0027 surface. No amendment needed.

### F007 — Active-learning "≥ 500 audit rows" trigger is a project-decision-grade choice but is not yet a DECISION_LOG entry
Severity: minor
Source: `docs/rfcs/0021-gold-set-interview-curation.md:271-281`,
`docs/rfcs/0021-gold-set-interview-curation.md:593-599`, DECISION_LOG D079

The RFC explicitly flags activation as "a project-level decision (see Open
Questions)"; Open Question 4 says "Whether the activation itself warrants a
DECISION_LOG entry is its own open project question." D079 captures
acceptance of RFC 0021 but does not pre-decide activation. This is the
correct posture for the RFC, but worth a one-line note that the flag exists
in v1 (CLI: `enable-active-learning --signal-version <v>`) while the
*decision to flip it on at scale* remains open. The current
`run_phase3_interview_enable_active_learning` in `cli.py:2255-2272` is the
mechanism; the activation policy isn't. Not blocking; tracker.

### F008 — `chk_gold_labels_template_path_matches_version` is best-effort by RFC's own admission and could mask version/path drift
Severity: nit
Source: `docs/rfcs/0021-gold-set-interview-curation.md:192-195`,
`migrations/010_gold_labels.sql:128-136`

The CHECK uses three OR'd substring tests (third-segment match, full
version-string match, or `replace('.', '_')` match). This is intentionally
permissive so the cost stays negligible. Note: a path like
`prompts/interview/foo_v2.md` will pass for both `area.v2.…` and
`area.v3.…` if `v3` happens to substring-contain `v2`-shaped tokens.
Failure mode is mostly a "wrong version stamped" rather than "wrong file
loaded" because the loader reads the file at the path, not at the version.
Acceptable; just acknowledge in the RFC body that the CHECK is a substring
sanity check, not a hash.

### F009 — Re-ask cap of 3 per version triple is enforced application-side; the RFC could note its absence from the schema
Severity: nit
Source: `docs/rfcs/0021-gold-set-interview-curation.md:470-475`

The RFC text mentions a 3-cap "by default, with operator override" (CLI
flag `--ignore-reask-cap`). Migration 010 does not encode this; it is a
sampler-side filter. That is the right place for it — cap policy is
operator-facing, not invariant — but the RFC could be explicit: "the
re-ask cap is sampler-side filter, not a schema constraint; overriding it
does not produce constraint violations." Worth a sentence.

### F010 — CLI v1 surface is complete for smoke-testing; no missing top-level verb
Severity: nit (positive)
Source: `docs/rfcs/0021-gold-set-interview-curation.md:367-379` vs `src/engram/cli.py:2154-2272`

The listed seven commands all have implementations under `engram phase3
interview {start, resume, history, export, list-sessions, coverage,
enable-active-learning}`. `coverage` is admitted as a v1 stub; that's
appropriate. The web UI (RFC 0027) handles the operator-facing path. No
gaps identified relative to "prove the schema, the sampler, the version
stamping, and the idempotent commit behavior" — the stated v1 goal.

### F011 — Skip semantics correctly avoid the privacy ceiling and cooldown override risks
Severity: nit (positive)
Source: `docs/rfcs/0021-gold-set-interview-curation.md:314-319`,
`docs/rfcs/0021-gold-set-interview-curation.md:380-395`

The RFC is explicit that `--ignore-cooldown` does not relax the privacy
tier ceiling and that no flag combination relaxes the ceiling below the
default Tier-1. Combined with the schema-enforced tier carry, this closes
the "show me everything" leak path the review prompt asks about. Skip-row
cooldown-free behavior is the right call for v1 since `never_ask` is
deferred and skip + resurface is the only way the operator can defer a
target without committing a verdict; the cost is a slightly noisier
sampling distribution if the operator skips repeatedly, which the cooldown
defaults will mostly absorb.

## Per-checklist disposition

1. **Privacy-tier carry.** Sound. Schema-enforced (carry trigger), parent
   resolution exact, mismatch refused, exported only via the fail-closed
   ceiling. See F004 for a documentation nit.
2. **Append-only discipline.** Sound. `fn_gold_labels_append_only` raises
   `P0001` on UPDATE or DELETE. Re-asks produce new rows; `current_gold_label`
   is the view that returns the latest verdict per version triple. The
   schema enforcement is in place (not just a policy).
3. **D044 / D069 alignment.** Sound at the text layer ("Does not auto-promote
   or auto-demote", loader prohibition on `engram.consolidator.transitions`).
   See F001 for the one delta between text and schema (the fourth trigger).
4. **Schema fit against claims/beliefs.** Mostly sound: typed version triple
   with a CHECK constraint is the right shape. See F003 for the belief-side
   `request_profile_version` framing issue.
5. **Sampler determinism.** Implementable in principle. See F002: the RFC
   names `candidate_pool_snapshot_id` as the anchor but the implementation
   uses a per-call UUID with no pool materialization. Determinism today
   relies on `gold_label_session_targets`, which materializes the sampled
   order.
6. **Cooldowns.** Concrete enough to land. Defaults named per stability
   class, tunable via env vars per the Python coding standard, `skip`
   exempt by design. Privacy ceiling cannot be overridden by any cooldown
   flag combination; the RFC text says so and the export CLI enforces it.
7. **Verdict vocabulary.** Six states are sufficient for v1. See F005 on
   the world-truth vs evidence-grounding axis collapse.
8. **RFC 0017 versioning fit.** Aligned. The single composite
   `prompt_template_version` matches RFC 0017's
   `{area}.v{N}.{date_or_decision}.{descriptor}` shape, and the path/version
   CHECK is in place. See F008 on the CHECK being substring-based.
9. **CLI v1 boundaries.** Complete for smoke-testing per F010.
10. **Migration numbering.** Resolved (F006). The prompt's "008 collision"
    concern reflects an earlier RFC draft; current RFC says 010, file exists.
11. **What is missing.** Session table exists (`gold_label_sessions`), so
    no free-text session key. The genuinely-missing piece is the
    candidate-pool snapshot table referenced by `candidate_pool_snapshot_id`
    (F002). The trigger named in the RFC but missing from migration 010 is
    the other (F001).

## Open questions

- Does the project want a `gold_label_candidate_pools` table now to make the
  RFC's replay claim concrete, or is "session targets materialization is
  enough" the accepted answer? If the latter, F002 reduces to a doc fix.
- Should the fourth named trigger
  (`fn_gold_labels_block_synthetic_audit_input`) be added as a follow-up
  migration on `belief_audit` (the table it would need to attach to), or
  should the RFC drop the naming and rely on the loader-discipline plus
  insert-only-claims chain to enforce D044? Either is defensible; current
  RFC text implies the trigger exists and it does not.
- When (if) `belief_audit` gains `request_profile_version`, does
  `gold_labels.consolidation_*` and `request_profile_version` align as a
  single canonical join target? F003's preferred resolution depends on
  this.
- Activation of the active-learning bias at scale (Open Question 4) is
  named as its own project decision; this review is not the place to decide
  it, but it should be tracked as an explicit DECISION_LOG candidate before
  ≥500 RFC 0018 audit rows exist.

verdict: accept_with_findings
