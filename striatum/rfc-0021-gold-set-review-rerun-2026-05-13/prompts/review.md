# RFC 0021 Gold-Set Interview Curation — Review Task

You are reviewing RFC 0021, the proposal for an agent-driven interview loop
that samples claims and beliefs, asks the user one structured question at a
time, and stores verdicts in an append-only `gold_labels` table. Your job is
to surface schema-fit, privacy, sampler-soundness, append-only, and CLI-v1
risks before the owner decides whether to accept the RFC.

This is a fresh provenance rerun after RFC 0032. Do not rely on quarantined
RFC 0021 review artifacts as authoritative evidence. If your runtime supports
sub-agents, use the maximum useful number of sub-agents for independent schema,
privacy, sampler, CLI, and auditability checks, then write only the expected
single review artifact.

## Inputs

- `docs/rfcs/0021-gold-set-interview-curation.md` — the RFC under review.
- `docs/rfcs/0011-phase-3-claims-beliefs.md` — claim/belief schemas the RFC
  joins onto.
- `docs/rfcs/0017-extraction-prompt-versioning.md` — versioning convention
  RFC 0021 says interview prompts should follow.
- `docs/rfcs/0018-evidence-to-claim-audit-cascade.md` — the audit cascade
  RFC 0021 says gold labels feed.
- `migrations/006_claims_beliefs.sql`, `migrations/007_claim_audits.sql` —
  baseline schema; the proposed `gold_labels` table joins `claims.id` and
  `beliefs.id` from these.
- `HUMAN_REQUIREMENTS.md`, `DECISION_LOG.md` — local-first, privacy-tier,
  D044 (no auto-promotion), D069 (audit cascade advisory in V1) constraints.
- `BUILD_PHASES.md`, `ROADMAP.md` — Phase 3 acceptance and Step 5 gold-set
  authoring positioning.
- `src/engram/cli.py`, `Makefile` — current command surface (where
  `engram interview` would land).

## Review checklist

1. **Privacy-tier carry.** Does the RFC's `gold_labels.privacy_tier`
   inheritance correctly reflect the target row's tier? Is export's
   `--privacy-tier-max` ceiling sufficient, or does it need a default that
   matches the user's working tier?
2. **Append-only discipline.** Is the table append-only as claimed? Are
   re-asks correctly handled as new rows rather than UPDATEs? Should there
   be a Postgres-level enforcement (trigger / role grant) similar to raw
   evidence?
3. **D044 / D069 alignment.** Does the RFC clearly forbid auto-flipping
   `beliefs.status` from a `false` verdict? Is "advisory only" stated
   strongly enough that a future implementer cannot accidentally wire it
   into consolidation?
4. **Schema fit against claims/beliefs.** Is `target_version_stamp` JSONB
   the right shape, given that claims have a 3-tuple
   (`extraction_prompt_version`, `extraction_model_version`,
   `request_profile_version`) and beliefs have a different 3-tuple
   (`prompt_version`, `model_version`, plus `request_profile_version` on
   `belief_audit`)? Should the version stamp be a typed column instead?
5. **Sampler determinism.** Is "seeded sampler with strata weights and
   active-learning bias defaulted off" implementable in a way that lets a
   later replay reproduce the exact question sequence?
6. **Cooldowns.** Are the cooldown defaults concrete enough to land, or
   does the RFC defer them too aggressively? Is there a risk of a "show me
   everything" override leaking past the privacy ceiling?
7. **Verdict vocabulary.** Are the six verdict states (`true`, `false`,
   `stale`, `unsupported`, `unsure`, `skip`) sufficient and mutually
   distinct? Is `unsupported` vs `false` clearly differentiated?
8. **RFC 0017 versioning fit.** Do `prompt_template_id` and
   `prompt_template_version` follow the RFC 0017 pattern
   (`prompts/<area>/<id>_v{N}.md`, immutable per version)?
9. **CLI v1 boundaries.** Is `engram interview start | resume | history |
   export` enough to smoke-test the storage and sampler, or is anything
   missing (e.g., a status command, a re-render command, a corpus-stat
   command)?
10. **Migration numbering.** The RFC names the migration
    `008_gold_labels.sql`, but migrations 008 and 009 already exist in
    `migrations/`. Should the RFC be amended to call out renumbering, or
    is the next-available-number convention assumed?
11. **What is missing.** Identify any field, command, or failure mode the
    RFC does not cover. Specifically: where is the run/session ID
    recorded? Is there a `gold_label_session` table or just a free-text
    `sampler_strata_key` carrying the session?

## Output

Write your review to the path in your job packet:
`docs/reviews/rfc0021-rerun-2026-05-13/RFC_0021_GOLD_SET_REVIEW_<lane>.md`.

Use this structure:

```md
# RFC 0021 Gold-Set Interview Curation Review — <lane>

Status: review
Date: <YYYY-MM-DD>
RFC refs: RFC-0021
Decision refs: ...
Phase refs: ...

## Findings

### F001 — <one-line title>
Severity: <blocking | major | minor | nit>
Source: <path>:<line range or section anchor>
Rationale: <one paragraph>

[... more findings ...]

## Open questions

- <questions to resolve before acceptance or implementation>

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Do not modify any file outside the path your packet specifies. Do not edit the
RFC, `BUILD_PHASES.md`, `DECISION_LOG.md`, `HUMAN_REQUIREMENTS.md`,
`Makefile`, `src/engram/cli.py`, or any migration.
