# RFC 0021 Gold-Set Interview Curation Review

author: operator [self-declared: rfc0021-review-codex]

## Scope

Reviewed `docs/rfcs/0021-gold-set-interview-curation.md` against the canonical
project docs, RFC 0011 / 0017 / 0018, migrations 006 / 007, the existing
gold-label migrations, `src/engram/cli.py`, and `Makefile`. Focus areas were
SQL feasibility, sampler determinism, argparse command integration, prompt
versioning compatibility, and concrete replacement shapes for
`target_version_stamp` / `sampler_strata_key`.

Verdict: **needs_revision**. The direction is sound and the phase-scoped CLI
surface is aligned with D078, but the RFC text still specifies several
contracts that are not implementable or not replayable as written.

## Findings

### F001 - Blocking - Synthetic-audit trigger is not implementable from the stated schema

RFC 0021 requires four schema-level triggers and names
`fn_gold_labels_block_synthetic_audit_input` as a CHECK/trigger that prevents
`belief_audit.input_claim_ids` from referencing a claim derived from a
gold-label promotion path (`docs/rfcs/0021-gold-set-interview-curation.md:120`,
`:201`, `:219`, `:525`). The Phase 3 baseline has no source/origin column on
`claims` and no "gold-label-derived synthetic claim" table or discriminator:
`claims` stores extraction prompt/model/request-profile columns, while
`belief_audit.input_claim_ids` is just `UUID[]` (`migrations/006_claims_beliefs.sql:131`,
`:155`, `:239`, `:259`). Migration 010 implements append-only, target
validation, and privacy-tier carry triggers, but not this fourth trigger
(`migrations/010_gold_labels.sql:162`, `:177`, `:235`).

Impact: the migration cannot satisfy the RFC literally. More importantly, the
RFC promises a schema-level D044 guard without defining the data that SQL would
inspect.

Proposed fix: either remove the fourth trigger from RFC 0021 and make this a
code/import-graph invariant ("gold-label code must not call
`engram.consolidator.transitions` or synthesize claims"), matching D079, or add
a first-class origin shape such as `claims.origin_kind` / a synthetic-claim
table and then define the trigger against that column. Do not leave the trigger
as prose.

### F002 - Blocking - `candidate_pool_snapshot_id` is only an opaque UUID, not a replayable snapshot

The RFC says `(seed, sampler_id, sampler_version, strata_weights)` plus
`candidate_pool_snapshot_id` makes a session re-derivable and prevents drift as
the corpus grows (`docs/rfcs/0021-gold-set-interview-curation.md:301`). The
specified RFC 0021 storage only has a UUID field on `gold_labels`
(`docs/rfcs/0021-gold-set-interview-curation.md:174`). There is no RFC 0021
table that stores candidate-pool membership, pool ordering, filter inputs, or
the active-learning scores used at sampling time.

The current scaffold shows why this matters: the sampler creates a fresh UUID
with `uuid.uuid4()` and reads `claims` / `current_beliefs` without an `ORDER BY`
before shuffling with a seeded RNG (`src/engram/interview/sampler.py:217`,
`:256`, `:420`, `:438`). PostgreSQL row order is not a replay contract, so the
same seed can select different targets if the physical plan or corpus changes.
Migration 011 later materializes selected session targets (`migrations/011_gold_label_session_targets.sql:1`,
`:6`), which fixes resume stability for the selected list, but that table is
owned by RFC 0027 / D080 rather than RFC 0021 and still does not represent the
full candidate pool.

Impact: sampler sessions are not re-derivable under the RFC 0021 contract, and
active-learning replay becomes especially under-specified once reviewer scores
influence ranking.

Proposed fix: fold a concrete snapshot shape into RFC 0021. Minimal viable
options are either (a) make `gold_label_session_targets` part of RFC 0021 and
weaken the claim from "pool replay" to "selected-order resume", or (b) add
`gold_label_candidate_pool_snapshots` plus pool-member rows containing
`target_kind`, `target_id`, exact target version stamp, strata fields,
confidence, observed time, cooldown/reask eligibility, active-learning signal
version, and deterministic pool ordinal. In all cases, require a stable
`ORDER BY` before applying seeded randomization.

### F003 - Major - Belief version stamps require a request profile with no canonical source

RFC 0021 replaces `target_version_stamp` with typed columns and requires
`request_profile_version` for both claim and belief labels
(`docs/rfcs/0021-gold-set-interview-curation.md:149`, `:187`). That is source
backed for claims: `claims` has `extraction_prompt_version`,
`extraction_model_version`, and `request_profile_version`
(`migrations/006_claims_beliefs.sql:155`). It is not source backed for beliefs:
`beliefs` only has `prompt_version` and `model_version`, while `belief_audit`
has `prompt_version`, `model_version`, and `request_uuid`, not a request profile
(`migrations/006_claims_beliefs.sql:218`, `:257`, `:262`). The current sampler
therefore hard-codes `belief_request_profile = "interview.v1.d079.initial"`
when labeling beliefs (`src/engram/interview/sampler.py:251`, `:285`).

Impact: belief labels are not fully attached to the belief derivation version
they were authored against. The `request_profile_version` value for beliefs
versions the interview/sampler path, not the target belief. That breaks the
RFC 0017-style join-key discipline, where version strings are supposed to join
derived rows back to the artifact that produced them
(`docs/rfcs/0017-extraction-prompt-versioning.md:61`).

Proposed fix: define `target_version_stamp` as a per-kind structured shape.
For claims, keep `(extraction_prompt_version, extraction_model_version,
request_profile_version)`. For beliefs, either use only
`(consolidation_prompt_version, consolidation_model_version)` or add a real
`consolidation_request_profile_version` column to the belief/audit schema
before requiring it on labels. If the interview renderer/sampler has its own
request profile, store that separately from the target version stamp.

### F004 - Major - Strata vocabulary validation is promised but not specified in implementable SQL

RFC 0021 says typed strata replace `sampler_strata_key` and are validated
against `gold_label_strata_vocabulary` (`docs/rfcs/0021-gold-set-interview-curation.md:167`,
`:264`). It also describes the vocabulary as `(key_name, key_value, gloss)`
(`docs/rfcs/0021-gold-set-interview-curation.md:243`, `:536`). Migration 010
uses `(stratum_kind, key, display)` instead (`migrations/010_gold_labels.sql:27`),
and `gold_labels.stability_class`, `conf_band`, `recency_band`, and
`belief_status` are plain text columns with no FK or validation trigger
(`migrations/010_gold_labels.sql:102`).

Impact: invalid strata values can be inserted even though the RFC claims
schema validation. That makes coverage and under-labeled-stratum sampling
unreliable, and it leaves future Step 9 consumers guessing which values are
canonical.

Proposed fix: choose one vocabulary column shape and make it enforceable. The
least invasive SQL options are a `fn_gold_labels_validate_strata` INSERT
trigger, or generated constant-kind columns plus composite FKs, e.g.
`(stability_stratum_kind, stability_class)` -> `(stratum_kind, key)`. A simpler
alternative is separate small vocabulary tables per stratum dimension.

### F005 - Minor - RFC status wording is stale and will confuse future handoffs

The header says status `accepted` / implementation `scaffolded`
(`docs/rfcs/0021-gold-set-interview-curation.md:8`), and D079 records RFC 0021
as accepted with migration and CLI targets (`DECISION_LOG.md:103`). The body
still says "This is an idea-capture RFC, not an accepted architecture decision"
and "does not authorize any model or pipeline change"
(`docs/rfcs/0021-gold-set-interview-curation.md:40`). The promotion path also
still says to land migration 010 and the CLI skeleton after acceptance
(`docs/rfcs/0021-gold-set-interview-curation.md:613`).

Impact: fresh execution contexts can incorrectly treat accepted D079 scope as
non-binding proposal text, or re-review already-decided command and migration
placement.

Proposed fix: rewrite the introduction as an accepted RFC/provenance document,
point to D079 as the binding decision, and either mark completed promotion
steps done or move remaining work into a follow-up implementation handoff.

## Non-Findings

- The argparse command shape matches the RFC surface: `engram phase3 interview`
  has `start`, `resume`, `history`, `export`, `list-sessions`, `coverage`, and
  `enable-active-learning` under the Phase 3 namespace (`src/engram/cli.py:490`).
  The Makefile has matching convenience targets (`Makefile:150`).
- The export CLI defaults to a Tier 1 ceiling, aligned with the RFC's
  fail-closed privacy requirement (`src/engram/cli.py:544`;
  `docs/rfcs/0021-gold-set-interview-curation.md:381`).
- Moving from generic JSON shapes (`target_version_stamp`,
  `sampler_strata_key`) to typed columns is the right direction; the remaining
  work is to make the belief version stamp source-backed and the strata
  vocabulary actually enforced.

## Verification Notes

No network access was used. I attempted a CLI help smoke, but this worktree has
no `.venv/bin/python`; `python` is absent; and `PYTHONPATH=src python3 -m
engram.cli ...` fails before argparse help because `psycopg` is not installed.
The CLI conclusion above is therefore based on static inspection, not runtime
execution.
