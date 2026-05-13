# RFC 0021 Contract Re-Review

author: operator [self-declared: focused-codex-1]

Status: review
Date: 2026-05-13
RFC refs: RFC-0021
Backlog refs: B007, B011
Decision refs: D020, D044, D052, D057, D077, D078, D079
Phase refs: PHASE-0003-FOLLOWON

## Scope

This is a narrow re-review of `docs/rfcs/0021-gold-set-interview-curation.md`
after the B007 contract revision. I checked the revised RFC against the fresh
rerun reviews under `docs/reviews/rfc0021-rerun-2026-05-13/`, the current
claims/beliefs and gold-label migrations, and the current interview
CLI/sampler/storage implementation. The focus was synthetic-audit wording,
candidate-pool/session-target replay claims, belief version stamps, strata
validation, stale/status wording, and migration baseline truthfulness.

## Findings

### 1. Synthetic-audit trigger wording — Resolved

The prior blocker was that RFC 0021 promised
`fn_gold_labels_block_synthetic_audit_input`, but the schema had no inspectable
claim-origin discriminator for such a trigger. The revised RFC now explicitly
states that the trigger is intentionally absent and that SQL cannot detect a
gold-label-derived synthetic claim without a future `claims` origin shape
(`docs/rfcs/0021-gold-set-interview-curation.md:234-240`). The D044 relationship
section repeats the same mechanism and constrains v1 to code-path discipline:
record labels only, do not synthesize claims, and do not call
`engram.consolidator.transitions`
(`docs/rfcs/0021-gold-set-interview-curation.md:597-606`).

That is truthful against the schema. Migration 010 implements only append-only,
target-validation, and privacy-tier-carry triggers
(`migrations/010_gold_labels.sql:162-276`), and the Phase 3 `claims` table has
prompt/model/request-profile fields but no origin discriminator
(`migrations/006_claims_beliefs.sql:131-160`). No RFC 0021 promotion path now
depends on a fictional SQL trigger.

### 2. Candidate-pool/session-target replay claims — Resolved, with one code-comment nit

The RFC no longer claims full replay from `candidate_pool_snapshot_id`. It now
calls that value an opaque session-instance tag
(`docs/rfcs/0021-gold-set-interview-curation.md:146-150`), says
`gold_label_session_targets` materializes only the selected order
(`docs/rfcs/0021-gold-set-interview-curation.md:268-273`), and repeats that
full pool replay is out of scope
(`docs/rfcs/0021-gold-set-interview-curation.md:644-646`,
`docs/rfcs/0021-gold-set-interview-curation.md:689-692`).

That matches the implementation: each sampler call generates a fresh UUID
(`src/engram/interview/sampler.py:417-456`), and storage persists the sampled
order into `gold_label_session_targets`
(`src/engram/interview/storage.py:412-489`). The remaining nit is in the sampler
module docstring, which still says the UUID exists "so replays are anchored"
(`src/engram/interview/sampler.py:15-16`). That is not an RFC contract defect,
but it should be cleaned up with the next touch so code comments do not
reintroduce the old replay claim.

### 3. Belief version stamps — Resolved

The RFC now distinguishes claim-side derivation stamps from belief-side
interview metadata. For claims, `request_profile_version` mirrors the `claims`
column. For beliefs, it is explicitly interview/sampler metadata because neither
`beliefs` nor `belief_audit` has a canonical request-profile column
(`docs/rfcs/0021-gold-set-interview-curation.md:159-163`,
`docs/rfcs/0021-gold-set-interview-curation.md:198-214`,
`docs/rfcs/0021-gold-set-interview-curation.md:583-590`).

That matches migration 006: `claims` stores
`extraction_prompt_version`, `extraction_model_version`, and
`request_profile_version` (`migrations/006_claims_beliefs.sql:155-157`), while
`beliefs` stores only `prompt_version` and `model_version`
(`migrations/006_claims_beliefs.sql:218-220`) and `belief_audit` likewise lacks
request-profile metadata (`migrations/006_claims_beliefs.sql:257-263`).
Storage validation now verifies parent claim triples and parent belief
prompt/model pairs before inserting labels or session targets
(`src/engram/interview/storage.py:72-139`, `src/engram/interview/storage.py:268-278`,
`src/engram/interview/storage.py:443-454`).

### 4. Strata validation — Resolved as an explicitly deferred SQL guarantee

The RFC no longer claims schema validation against
`gold_label_strata_vocabulary`. It says migration 010 seeds the vocabulary but
does not attach FKs or a validation trigger, and it assigns hard validation to a
follow-up if Step 9 needs it
(`docs/rfcs/0021-gold-set-interview-curation.md:301-310`,
`docs/rfcs/0021-gold-set-interview-curation.md:647-649`).

That is truthful against migration 010: the vocabulary exists
(`migrations/010_gold_labels.sql:27-55`), while `gold_labels.stability_class`,
`conf_band`, `recency_band`, and `belief_status` are plain text columns without
FKs (`migrations/010_gold_labels.sql:102-106`). The CLI/parser and sampler
validate allowed filter keys, not the full canonical value set
(`src/engram/cli.py:109-135`, `src/engram/interview/sampler.py:391-414`), which
is consistent with the RFC's "application-side and operator convention" wording.

### 5. Status/stale wording — Mostly resolved; one future wording cleanup

The RFC correctly anchors default belief sampling on `current_beliefs`, which
filters to valid, unclosed candidate/provisional/accepted rows
(`docs/rfcs/0021-gold-set-interview-curation.md:322-325`;
`migrations/009_phase4_entities_review.sql:143-173`). Its six-state verdict
vocabulary is also now explicit, including the lack of any current
eight-verdict contract and the `false`/`unsupported` axis split
(`docs/rfcs/0021-gold-set-interview-curation.md:280-294`).

One small cleanup remains outside the B007 blockers: the RFC says belief
questions may ask "Was this true between `valid_from` and `valid_to`?"
(`docs/rfcs/0021-gold-set-interview-curation.md:397-399`), but the current
renderer does not branch on `valid_to`; it asks event, transient, or current
truth questions based on cardinality/stability only
(`src/engram/interview/render.py:328-362`). This is not a default-path defect
because `current_beliefs` rows are current by construction, but if
`--include-superseded` is used for historical/adversarial sweeps, the wording is
more precise than the current renderer. Either weaken the RFC sentence to the
implemented framing or teach the renderer to ask interval questions for closed
beliefs.

### 6. Migration baseline truthfulness — Resolved in RFC text; one migration-comment nit

The RFC now states `Implementation: partial`, references the Phase 3 follow-on
row, names D079, and accurately describes migrations 010, 011, and 013 as the
current storage baseline
(`docs/rfcs/0021-gold-set-interview-curation.md:8-11`,
`docs/rfcs/0021-gold-set-interview-curation.md:43-47`,
`docs/rfcs/0021-gold-set-interview-curation.md:122-132`). It also records the
remaining follow-ups rather than pretending the RFC is fully done
(`docs/rfcs/0021-gold-set-interview-curation.md:694-712`).

The only baseline nit I found is in migration 010's file header, which still
says "four named triggers" while parenthetically listing only three implemented
trigger families (`migrations/010_gold_labels.sql:4-7`). The executable SQL is
correct, and the RFC text is now correct; the migration comment is stale
provenance text.

### 7. Residual contract mismatch: rendered evidence excerpts are not persisted

Severity: medium

The RFC still says that when a 1-line evidence excerpt is rendered, it is
stored in `gold_labels.evidence_excerpt` rather than embedded in `prompt_text`
(`docs/rfcs/0021-gold-set-interview-curation.md:392-396`,
`docs/rfcs/0021-gold-set-interview-curation.md:560-565`). The current CLI and
web paths render evidence excerpts from the target display, but they commit
verdicts without passing an excerpt into `InterviewAgent.record_verdict`:

- CLI renders excerpts via `format_evidence_excerpts` and then records only
  `session_id`, `target`, `verdict`, and `rationale`
  (`src/engram/cli.py:1916-1940`).
- Web renders excerpts in the question template context and likewise records
  only `session_id`, `sampled`, `verdict`, and `rationale`
  (`src/engram/interview/web.py:504-523`,
  `src/engram/interview/web.py:842-848`).
- The web regression test currently asserts the committed `evidence_excerpt` is
  `NULL` after a normal verdict commit (`tests/test_interview_web.py:395-414`).

Impact: export remains privacy-safe because it filters whole rows by
`privacy_tier`, but the RFC overstates what the label row preserves. The exact
excerpt shown to the operator is not persisted in v1 unless a custom caller
passes it manually. Either revise RFC 0021 to say `evidence_excerpt` is optional
and currently not populated by the CLI/web commit paths, or pass a bounded
excerpt string through both commit paths and update tests accordingly.

## Verdict

verdict: accept_with_findings

The B007 blockers from the fresh rerun are resolved in the RFC contract text:
synthetic-audit enforcement is no longer fictional, candidate-pool replay is
scoped down to selected-order materialization, belief request profiles are no
longer described as canonical belief derivation stamps, strata validation is
explicitly not schema-enforced, and migration/status wording is mostly aligned.
The remaining issues are small provenance/comment drift plus one real
excerpt-persistence mismatch that should be fixed before anyone treats
`gold_labels.evidence_excerpt` as populated audit data.

## Verification

No network access was used. I did not run the test suite for this review; the
operator report records the current batch at `make test-docker` = 517 passed and
the focused interview CLI/storage target = 14 passed. This review is based on
static inspection of the assigned docs, migrations, implementation, and tests.
