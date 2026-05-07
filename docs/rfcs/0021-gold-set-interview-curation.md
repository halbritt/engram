<a id="rfc-0021"></a>
# RFC 0021: Gold-Set Interview Curation

| Field | Value |
|-------|-------|
| RFC | 0021 |
| Title | Gold-Set Interview Curation |
| Status | proposal |
| Implementation | none |
| Date | 2026-05-07 |
| Context | ROADMAP Step 5 (gold-set authoring); HUMAN_REQUIREMENTS § "the eval gold set is the actual specification"; BUILD_PHASES Phase 3 acceptance row; D016, D040, D044, D069, F010, O008; RFC 0011 §§ Stage A / Stage B; RFC 0018 § Promotion Path step 4 (cascade reviewer scheduled post-Step-5); `migrations/006_claims_beliefs.sql:131` (`claims`); `migrations/006_claims_beliefs.sql:178` (`beliefs`) |

Decision refs:
  - D016
  - D040
  - D044
  - D069
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

An **interview agent** running locally drives a CLI loop:

```
$ engram interview
[1/10] Sampled belief b-7f3a... "user works at Acme Corp" (project_status, accepted, conf 0.87)
       Evidence: 3 messages, 2024-11-12 → 2025-08-04 (range 9 months).
       Q: Is this currently true?
       [t]rue / [f]alse / [s]tale / [unsure] / [skip] >
       Optional rationale: _
```

Each interview turn is a single `(claim_id | belief_id, version, prompt,
verdict, rationale, asked_at, answered_at)` tuple committed to a new
append-only local table. The agent never modifies the underlying claim or
belief; verdicts are derived data that joins onto existing IDs.

### Storage

A new migration `008_gold_labels.sql` adds:

```
gold_labels
  id                    UUID PRIMARY KEY
  target_kind           TEXT CHECK (target_kind IN ('claim','belief'))
  target_id             UUID NOT NULL
  -- The version stamp captured at interview time. For claims:
  --   (extraction_prompt_version, extraction_model_version, request_profile_version).
  -- For beliefs: (consolidation_prompt_version, consolidation_model_version,
  --   request_profile_version) — equivalents already stored on belief_audit.
  target_version_stamp  JSONB NOT NULL
  prompt_text           TEXT NOT NULL
  prompt_template_id    TEXT NOT NULL
  prompt_template_version TEXT NOT NULL
  verdict               TEXT NOT NULL CHECK (verdict IN
                          ('true','false','stale','unsupported','unsure','skip'))
  rationale             TEXT NULL
  sampler_id            TEXT NOT NULL
  sampler_version       TEXT NOT NULL
  sampler_strata_key    JSONB NOT NULL  -- e.g. {"stability_class":"goal","conf_band":"0.6-0.8"}
  asked_at              TIMESTAMPTZ NOT NULL
  answered_at           TIMESTAMPTZ NOT NULL
  privacy_tier          INT NOT NULL    -- carried from target row
```

Append-only. No `UPDATE`/`DELETE` enforcement matches the raw-evidence
discipline; later verdicts on the same target produce new rows.
Re-derivation of "current verdict per target" is a view, not a table.

The table is not a `gold_entries` table — it does not author the
`expected_facts` shape consumed by Step 9 evals. Promotion of label clusters
into formal gold-set entries is a downstream step (open question; see
§ Open questions).

### Sampler

Random sampling burns interviews on easy cases and clusters them by whatever
the corpus happens to over-produce. The proposal is **stratified sampling
with active-learning bias**, version-stamped:

- **Strata.** Cross product of `stability_class` × confidence band ×
  recency band, reweighted to over-sample under-labeled strata. For
  beliefs, also stratify on `status` ('candidate', 'provisional', 'accepted')
  and on whether a `belief_audit` or `claim_audits` row already exists.
- **Active-learning bias.** Within a stratum, prefer (a) targets near the
  decision boundary of any existing local reviewer (RFC 0018) and
  (b) targets with no prior `gold_labels` row at the current
  `target_version_stamp`.
- **Cooldowns.** A target answered in the last N days is suppressed for that
  window unless the user explicitly requests "show me everything." Prevents
  fatigue on the same easy cases.
- **Determinism.** The sampler is seeded; the sampler ID + version + seed +
  strata weights are stamped on each emitted question so an interview pass
  is reproducible.

V1 sampler is the simplest version that respects strata + cooldowns; the
active-learning bias is wired but defaulted off until RFC 0018 reviewer
output exists at scale.

### Interview agent

A locally-run agent (small local model is sufficient — this is reading
structured rows, not generating freeform claims) renders each sampled target
into a question using a versioned prompt template:

- For a claim: "Is this an accurate paraphrase of your situation at the
  time of the cited evidence?" + the canonical paraphrase + a 1-line
  evidence excerpt (privacy-tier-respecting).
- For a belief: "Is this currently true?" / "Was this true between
  `valid_from` and `valid_to`?" + the canonical paraphrase + an evidence
  count and date span (no raw quotes by default).
- For a contradiction (RFC 0011 § contradictions): "Which of these is
  closer to the truth, or are both wrong?"

Templates live under `prompts/interview/` and carry `prompt_template_id`
+ `prompt_template_version` (RFC 0017 versioning convention). The agent's
job is rendering and capture, not judgment. It does not auto-vote.

### CLI v1 (smoke-test surface)

`engram interview` subcommands, mirroring the existing CLI shape
(`src/engram/cli.py`):

- `engram interview start [--n 10] [--strata <expr>] [--seed <int>]`
- `engram interview resume [--session-id <id>]`
- `engram interview history [--target <id>] [--since <ts>]`
- `engram interview export --format jsonl [--privacy-tier-max <N>]`
  — local-only export for offline analysis; default tier ceiling matches
  the user's working tier.

CLI v1 is a thin loop over the sampler + storage. Its job is to prove the
schema, the sampler, the version stamping, and the idempotent commit
behavior. UX work belongs to the web surface.

### Web UI (v2 — out of scope here)

Captured here only to clarify v1 boundaries. The web surface is the only
plausible interview UX for a non-developer user; CLI v1 exists to keep the
backend contract honest before that work starts. Web surface design is a
separate RFC.

## Worked example

Single CLI session; numbers are illustrative.

```
$ engram interview start --n 5 --seed 4
session: gl-sess-2026-05-07-00
sampler: stratified.v1, strata={stability x conf-band x recency}

[1/5] belief b-7f3a... "user works at Acme Corp"  status=accepted, conf=0.87
      stability=project_status, ev=3 msgs over 9mo (2024-11 .. 2025-08)
      Q: Is this currently true?
      > t
      rationale: still here, role unchanged

[2/5] claim c-91d2... predicate=has_pet, object={"name":"Mochi","species":"cat"}
      stability=identity, conf=0.62
      Q: Is this an accurate paraphrase at the time of the cited evidence?
      > t
      rationale:

[3/5] belief b-c4e1... "user prefers vim"  status=accepted, conf=0.71
      stability=preference, ev=4 msgs over 18mo
      Q: Is this currently true?
      > stale
      rationale: switched to helix Apr 2026

[4/5] claim c-2210... predicate=goal_to, object_text="learn rust"
      stability=goal, conf=0.55
      Q: Is this an accurate paraphrase at the time of the cited evidence?
      > unsure

[5/5] belief b-aa90... "user is_related_to {name:'Sam',kind:'sibling'}"
      stability=relationship, ev=1 msg
      Q: Is this currently true?
      > t

5 verdicts committed to gold_labels.
session summary: 3 true, 0 false, 1 stale, 1 unsure, 0 skip.
```

After session: a `current_gold_label` view returns the most recent verdict per
`(target_kind, target_id, target_version_stamp)`; the `belief_audit`,
`claim_audits`, and `contradictions` tables are unchanged.

## Privacy and provenance

- **No outbound network.** Sampler, agent, and storage all run against the
  local Postgres + local LLM endpoint. Same constraint as every other
  Engram pipeline (D020).
- **`privacy_tier` carry.** The label row inherits the target's privacy
  tier; export respects a tier ceiling. No raw evidence text is required
  in the label row; the `prompt_text` column contains the rendered
  question, which the user has by definition seen.
- **Provenance preserved.** Each label cites the target ID, the target
  version stamp, the sampler ID + version + seed, and the prompt template
  ID + version. A future re-extraction that produces a new claim version
  does not invalidate prior labels; they remain attached to the version
  they were authored against (RFC 0017 versioning discipline).
- **Append-only.** Matches the raw-evidence rule (D002 / P4). Re-asking
  produces a new row.

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
  adversarial round (Step 6).
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

1. **Promotion path from labels to gold-set entries.** What set of label
   rows constitutes evidence for a `GOLD_SET_TEMPLATE` entry? A simple
   "k labels agreeing across N days" rule is likely fine for v1, but
   needs spec.
2. **Web UI handoff.** When the web surface arrives, does the CLI go away
   or stay as an admin/back-channel tool? Lean toward keep, since
   smoke-testing the backend remains useful indefinitely.
3. **Contradiction-mode questions.** Worth piloting? They produce richer
   signal than per-row verdicts but are harder to render. Defer to v1.5.
4. **Active-learning bias signal source.** RFC 0018 reviewer scores are
   the obvious feed once present at scale. Until then, the bias defaults
   to "no prior label at current version stamp."
5. **New-claim capture during interview.** Out of scope here, but a real
   open product question. Likely its own RFC, since it touches raw
   immutability framing.
6. **Cooldown defaults.** N days per (target, verdict) and per
   (target, any verdict) — values to be tuned empirically once any
   real usage data exists.
7. **Export shape.** JSONL with `(target, verdict, version_stamp)` is the
   minimum; whether additional pivots are useful enough to bake in
   depends on Step 9 needs.

## Promotion path

1. Discuss / amend in review.
2. If accepted, add a BUILD_PHASES entry under Phase 3 follow-on or
   Step 5 substrate work; mark this RFC `accepted`.
3. Land migration `008_gold_labels.sql` and the sampler/agent/CLI
   skeleton on a separate branch (this RFC is documentation only).
4. Wire the export path; confirm Step 9 eval runners can ingest it.
5. Defer web UI to its own RFC after CLI v1 produces real label data.
