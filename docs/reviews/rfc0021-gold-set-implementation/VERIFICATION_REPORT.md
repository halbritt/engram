# RFC 0021 Gold-Set Implementation — Verification Report
author: reviewer-codex-gpt-5.5-001

Status: verification
Date: 2026-05-08
RFC refs: RFC-0021
Decision refs: D044, D052, D069, D077, D078, D079
Phase refs: PHASE-0003-FOLLOWON

## Scope

The implementation under review is uncommitted (`git status --short`
reports modified `CHANGELOG.md`, `Makefile`, `README.md`,
`src/engram/cli.py`, `tests/conftest.py`, `tests/test_migrations.py`
plus untracked `migrations/010_gold_labels.sql`,
`prompts/interview/`, `src/engram/interview/`, three new
`tests/test_interview_*.py`, and the review/striatum directories). The
last committed work on the branch is `b1770d5` ("Accept RFC 0021…")
which only landed the accepted RFC text.

## Commands run

| # | Command | Exit | Result |
|---|---------|------|--------|
| 1 | `git diff --stat HEAD~1 HEAD` | 0 | only docs/striatum churn from `b1770d5`; implementation lives in working tree (`git status --short` lists 6 modified + 7 untracked entries) |
| 2 | `make check-refs 2>&1 \| tail -5` | 0 | `0 error(s), 5 warning(s), 158 check(s) ok` (warnings pre-date this work — they touch `D042#request-profile`, `PHASE-0002#generation-activation`, and an unrelated prompt-ordinal collision) |
| 3 | `pytest tests/test_interview_cli.py tests/test_interview_sampler.py -x` | 0 | `25 passed in 0.17s` |
| 4 | `pytest tests/test_cli.py -x` | 0 | `15 passed, 10 skipped` (skips require DB) — matches pre-implementation regression baseline |
| 5 | `engram phase3 interview --help` | 0 | lists 7 subcommands `{start, resume, history, export, list-sessions, coverage, enable-active-learning}` |
| 6 | `engram phase3 interview export --help` | 0 | shows `--privacy-tier-max ... (default: 1)` via `ArgumentDefaultsHelpFormatter` |
| 7 | `engram interview --help; echo exit=$?` | 2 | argparse rejects bare `interview`: `invalid choice: 'interview' (choose from … phase3, phase4)`; matches RFC 0025 |
| 8 | `ls migrations/010_gold_labels.sql && head -20` | 0 | header `RFC 0021: Gold-Set Interview Curation`, `Decision refs: D044, D052, D057, D069, D073, D077, D078, D079`, and `gold_label_sessions` CREATE follows immediately |
| 9 | `ls prompts/interview/` | 0 | `belief_v1.md`, `claim_v1.md` |
| 10 | `grep -c "fn_gold_labels_append_only\|…validate_target\|…carry_privacy_tier" migrations/010_gold_labels.sql` | 0 | `7` (≥3 required) |
| 11 | `grep -c "phase3-interview-" Makefile` | 0 | `7` (1 .PHONY line + 6 rule lines; ≥6 required) |
| 12 | `grep -n "phase3 interview" src/engram/cli.py \| head -5` | 0 | wired at lines 903, 1680, 1692, 1693, 1702 |
| 13 | `grep -E "engram interview\b" src/engram/cli.py \|\| echo NO bare engram interview` | 0 | `NO bare engram interview` |
| 14 | `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test pytest tests/test_interview_storage.py -x` | 0 | `7 passed in 6.87s` (env var unset in shell; supplied locally for this run) |
| — | `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test pytest tests/test_migrations.py -x` | 0 | `3 passed in 1.92s` (covers the new `010_gold_labels.sql` landmarks) |

## Structural confirmation

### Migration `migrations/010_gold_labels.sql`

- Header (`migrations/010_gold_labels.sql:1-7`) cites `RFC 0021` and
  decisions `D044, D052, D057, D069, D073, D077, D078, D079`. Match.
- `gold_label_sessions` table created (`migrations/010_gold_labels.sql:9-18`)
  with `seed BIGINT NOT NULL`, `sampler_id`, `sampler_version`,
  `strata_weights JSONB`, `started_at` default `now()`, `completed_at NULL`,
  `operator_note NULL`. Match.
- `gold_label_strata_vocabulary` (`migrations/010_gold_labels.sql:27-32`)
  PK `(stratum_kind, key)`; seed (`:34-55`) covers the seven RFC
  stability classes, five confidence bands and five recency bands plus
  three `belief_status` values. Match (column names diverge from the RFC
  literal `key_name/key_value/gloss` — implementation uses
  `stratum_kind/key/display`; functionally equivalent).
- `gold_label_verdict_vocabulary` (`migrations/010_gold_labels.sql:58-71`)
  seeded with all six verdicts (`true|false|stale|unsupported|unsure|skip`)
  and per-row glosses. Match.
- `gold_labels` table (`migrations/010_gold_labels.sql:74-137`) has the
  typed extraction triple, consolidation triple, required
  `request_profile_version`, prompt template version + path, evidence
  excerpt, verdict FK, rationale CHECK ≤ 2000 chars, sampler stamps,
  candidate-pool snapshot id, optional active-learning signal version,
  typed strata columns, `strata_extra` JSONB default, asked/answered
  timestamps and `privacy_tier`. The `chk_gold_labels_version_triple`
  CHECK (`:112-127`) enforces the per-kind triple shape; the
  `chk_gold_labels_template_path_matches_version` CHECK (`:128-136`)
  matches handoff note about substring rather than regex. Match.
- All three required trigger functions exist and are named per RFC §
  Storage:
  - `fn_gold_labels_append_only` (`:162-170`) raising `P0001` on UPDATE
    or DELETE.
  - `fn_gold_labels_validate_target` (`:177-223`) routes per
    `target_kind`, refuses dangling references, and pre-validates the
    triple shape so the trigger emits the polymorphic error before the
    next trigger.
  - `fn_gold_labels_carry_privacy_tier` (`:235-272`) reads parent tier,
    rejects operator-supplied disagreement, and forces NEW.privacy_tier
    to the parent value.
- Trigger ordering: `gold_labels_00_validate_target` (`:230`) and
  `gold_labels_01_carry_privacy_tier` (`:274`). PostgreSQL fires
  same-event row triggers in alphabetical order, so the `00`/`01`
  prefix guarantees parent-existence is checked before tier carry. The
  function names retain the RFC-literal naming.
- `current_gold_label` view (`:281-334`) returns the latest verdict per
  `(target_kind, target_id, version_triple)`, ordered by `answered_at
  DESC` with a verdict-rank tiebreak (`true|false|stale|unsupported`
  outrank `unsure|skip`). Match.

### Source

- `src/engram/interview/__init__.py:3`, `errors.py:1`, `storage.py:15`,
  `sampler.py:22`, `agent.py:9` all start with
  `from __future__ import annotations`. Match.
- Domain root + three subclasses (`src/engram/interview/errors.py:4-17`):
  `InterviewError`, `GoldLabelStorageError`, `GoldLabelSamplerError`,
  `GoldLabelVerdictError`. Match.
- Cooldown env vars read at module top in `sampler.py:36-50` (seven
  `ENGRAM_GOLD_COOLDOWN_<CLASS>_DAYS` constants plus
  `ENGRAM_GOLD_ACTIVE_LEARNING_THRESHOLD` at `:52-54`). Match.
- `INTERVIEW_TEMPLATE_VERSION_*` constants (`agent.py:21-24`) follow
  RFC 0017 shape: `interview.claim.v1.d079.initial` and
  `interview.belief.v1.d079.initial`. Match.
- `RATIONALE_CHAR_LIMIT = 2000` (`agent.py:29`). Match.
- Sampler is seeded (`sampler.py:206`) and reads `current_beliefs`
  (`sampler.py:245-247`) by default with graceful fall-through to an
  empty pool on `psycopg.Error` (`:264-266`); `--include-superseded`
  switches the source to `beliefs` (`:248-249`). D077 honored.
- `VALID_VERDICTS = frozenset({"true","false","stale","unsupported",
  "unsure","skip"})` (`agent.py:26-28`). Six values, frozen, matches
  vocabulary seed. Match.

### CLI

- `engram phase3 interview` dispatches all 7 subcommands per RFC §
  CLI v1 (verified in command 5).
- `engram phase3 interview export` defaults `--privacy-tier-max=1` and
  surfaces the default in `--help` via
  `argparse.ArgumentDefaultsHelpFormatter` (`src/engram/cli.py:443-449`,
  verified in command 6). Fail-closed Tier ceiling. Match.
- Bare `engram interview` is rejected with exit code 2 (verified in
  command 7). RFC 0025 / D078 honored.

### Prompts

- `prompts/interview/claim_v1.md` and `prompts/interview/belief_v1.md`
  carry RFC 0017 front-matter (`template_id`, `template_version`,
  `target_kind`) and the canonical 6-verdict legend. The on-disk
  `template_version` strings match the constants stamped in
  `agent.py:21-22`.

### Tests

- `tests/test_interview_cli.py` and `tests/test_interview_sampler.py`
  pass deterministically without DB (25/25, command 3).
- `tests/test_interview_storage.py` is DB-bound; with
  `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test` set locally,
  7/7 pass and `tests/test_migrations.py` 3/3 pass (command 14 plus
  the migration suite). The shell that fired the verification job had
  `ENGRAM_TEST_DATABASE_URL` unset; results above were obtained by
  exporting it for these two suites.
- `tests/test_cli.py` regression: 15 passed / 10 skipped (command 4),
  matching the pre-implementation baseline. The known
  `tests/test_phase3_claims_beliefs.py::test_cli_pipeline_is_phase2_only_and_pipeline3_warns`
  failure called out in the handoff is RFC 0025 / pre-existing and not
  reproduced here because the test was not part of the required
  command set.

## Findings

### V001 — `fn_gold_labels_block_synthetic_audit_input` not implemented
Severity: minor
Source: `migrations/010_gold_labels.sql` has only three triggers
(append-only, validate-target, carry-privacy-tier);
`grep "fn_gold_labels_block_synthetic_audit_input"` returns nothing.
RFC 0021 § Storage names a fourth trigger and § Promotion path /
Relationship to other artifacts § D044 say a CHECK or trigger should
"prevent `belief_audit.input_claim_ids` from referencing any
gold-label-derived synthetic claim." The handoff document acknowledges
this scope cut explicitly ("three named triggers"). v1 ships no
gold-label → synthetic-claim promotion path, so the invariant has no
opportunity to fire today. Land it before any auto-promotion machinery
or the D044 invariant becomes a code-review-only invariant.

### V002 — `enable-active-learning` lacks a Makefile target
Severity: minor
Source: `Makefile` lines 147–162 wire six `phase3-interview-*` targets
(start, resume, history, export, list-sessions, coverage). The CLI
exposes a seventh subcommand `enable-active-learning` (verified in
command 5; required by RFC § CLI v1 and by handoff line 56). Operators
relying on `make` cannot reach the bias-enable surface from the
Makefile; they must drop to `engram phase3 interview
enable-active-learning` directly. The work-packet criterion ("at least
6 phase3-interview-* targets") is met, but the surface is asymmetric
relative to the RFC.

### V003 — Strata-vocabulary column names differ from the RFC literal
Severity: nit
Source: `migrations/010_gold_labels.sql:27-32` declares
`gold_label_strata_vocabulary (stratum_kind TEXT, key TEXT, display TEXT,
PRIMARY KEY (stratum_kind, key))`. RFC § Storage shows
`(key_name TEXT, key_value TEXT, gloss TEXT)`. Function is identical;
the divergence does not block the contract. If the synthesis intends
strict mirror with `predicate_vocabulary` (D057), a column rename plus
matching seeded rows would land that intent. Out of scope for blocking.

### V004 — `chk_gold_labels_template_path_matches_version` is loose
Severity: nit
Source: `migrations/010_gold_labels.sql:128-136` accepts any of three
substring tests (split-on-`.`-third-part inside the path, raw version
inside the path, or dot-to-underscore version inside the path). RFC §
Storage already says "best-effort CHECK … kept lightweight (substring
match)" so this is in spec; flagging for completeness because a
caller writing
`prompt_template_version='interview.claim.v1.d079.initial'` paired
with `prompt_template_path='prompts/interview/claim_v1.md'` only passes
because `'v1'` appears as a substring of both. A future template-path
rename without bumping the version constant would silently re-pass.

### V005 — Storage helper sets `privacy_tier=NULL` on insert
Severity: nit
Source: `src/engram/interview/storage.py:144` and `:216` insert
`None` for `privacy_tier` when the operator omits the column;
`gold_labels.privacy_tier` is declared `NOT NULL`
(`migrations/010_gold_labels.sql:110`). The carry trigger
(`fn_gold_labels_carry_privacy_tier`) writes `NEW.privacy_tier := parent_tier`
**before** the NOT NULL check fires, so the path works in practice and
is exercised by `tests/test_interview_storage.py`. Worth a comment in
the helper noting the dependency on the BEFORE-INSERT trigger so a
future "ORDER BY trigger name" change does not silently regress.

## Residual risks

- `current_beliefs` falls through to an empty belief slice on any
  `psycopg.Error` (`sampler.py:264-266`). Smart for fresh schemas, but
  it could mask a real query bug; an operator-visible warning would
  pay for itself once Phase 3 follow-on operators start sampling.
- Trigger ordering is a naming convention (`gold_labels_00_*` /
  `gold_labels_01_*`). Renaming either trigger silently regresses the
  parent-validation message ordering. The handoff documents the
  convention; a future migration touching these triggers should keep
  the alphabetical prefix.
- v1 sampler is shuffle-and-take; strata weights are stamped onto the
  session row but do not bias pulls. v1.1 work per RFC § Sampler v1.
- Active-learning bias is opt-in stamping only; no re-ranking. RFC
  Open Q 4 deferred to v1.1.
- No interactive Ctrl-C / save-and-quit shell — CLI v1 commands are
  smoke-test surfaces. Handoff acknowledges; web v2 lands the loop.

verdict: accept_with_findings

One-sentence rationale: every required command passes, the schema
contract (three named triggers, typed version triple, fail-closed
Tier ceiling) and CLI surface (`engram phase3 interview …`, bare
`engram interview` rejected) are wired exactly as RFC 0021 and the
handoff describe; the residual gaps (`fn_gold_labels_block_synthetic_audit_input`
deferred, `enable-active-learning` missing a Makefile target, minor
schema-naming nits) are minor and tracked findings, none blocking
landing.
