# RFC 0021 Gold-Set Implementation — Final Review
author: reviewer-codex-gpt-5.5-002

Status: final-review
Date: 2026-05-08
RFC refs: RFC-0021
Decision refs: D044, D052, D069, D077, D078, D079
Phase refs: PHASE-0003-FOLLOWON

## Scope

Final code-review pass over the uncommitted RFC 0021 v1 implementation
(migration `010_gold_labels.sql`, `src/engram/interview/*`, prompts,
CLI wiring under `engram phase3 interview …`, Makefile targets, tests),
auditing against the RFC 0021 contract, D044 / D052 invariants, the
RFC 0025 / D078 phase-scoped CLI surface, RFC 0017 template versioning,
and the priorities listed in the review prompt. Verifier already ran
landed migration / pytest / `--help` checks (see `VERIFICATION_REPORT.md`,
verdict `accept_with_findings`); this review re-walks the load-bearing
invariants in the source directly and cross-checks the verifier's
findings.

## Audit findings

### A001 — Append-only enforcement is wired and exercised end-to-end
Severity: nit
Source: `migrations/010_gold_labels.sql:162-174`, `tests/test_interview_storage.py:155-192`, `tests/test_interview_storage.py:195-227`
Rationale: `fn_gold_labels_append_only` is a `BEFORE UPDATE OR DELETE`
plpgsql function that raises `P0001` with operator-readable text
(`'gold_labels is append-only; % is not allowed'`). The trigger
(`gold_labels_append_only`) binds it on both events, and the
`tests/test_interview_storage.py::test_label_update_is_blocked_by_append_only_trigger`
and `::test_label_delete_is_blocked_by_append_only_trigger` cases drive
real SQL through `conn.execute` to confirm the failure path raises
`GoldLabelStorageError` with `match="append-only"`. The translation in
`src/engram/interview/storage.py:45-46` (`errors.RaiseException` →
`GoldLabelStorageError`) is what makes the test's regex match work.
Recording as a nit only because it's the first audit item the prompt
calls out; this is correct and tested.

### A002 — Polymorphic FK guard refuses dangling target_ids per kind
Severity: nit
Source: `migrations/010_gold_labels.sql:177-223`, `tests/test_interview_storage.py:230-261`
Rationale: `fn_gold_labels_validate_target` routes per `target_kind`,
performs `SELECT EXISTS … FROM claims WHERE id = NEW.target_id` /
`… FROM beliefs …`, and raises `P0001 'gold_labels target_id … not
found in claims/beliefs'` on miss. It also pre-validates the version
triple shape inline (`extraction_*` populated for claim, NULL for
belief; reverse for belief) so the polymorphic FK error always emits
before the carry trigger has a chance to raise its own miss message
— the trigger naming convention (`gold_labels_00_validate_target` vs.
`gold_labels_01_carry_privacy_tier`, lines 230 / 274) is the
ordering mechanism. `test_dangling_target_id_is_rejected` exercises
the missing-claim path with a synthetic UUID; it asserts the
`"not found in claims"` string, which is the load-bearing guard.

### A003 — Privacy-tier carry copies parent and rejects disagreement
Severity: nit
Source: `migrations/010_gold_labels.sql:235-272`, `tests/test_interview_storage.py:264-296`
Rationale: `fn_gold_labels_carry_privacy_tier` reads the parent
`privacy_tier` from `claims` or `beliefs` per `target_kind`, raises
`P0001` if the parent isn't found, raises `P0001 'gold_labels
privacy_tier % disagrees with parent …'` on operator/parent
mismatch, then unconditionally writes `NEW.privacy_tier := parent_tier`.
The negative test `test_privacy_tier_mismatch_with_parent_is_rejected`
inserts a label with `privacy_tier=2` against a parent claim seeded
at tier 1 and asserts the trigger raises with `match="disagrees with
parent"`. The happy-path `test_session_and_label_happy_path` confirms
the carry value (1) lands in the row even though the storage helper
sends `None` (see A009). Both paths verified.

### A004 — Fail-closed export ceiling defaults to 1 and is operator-visible
Severity: nit
Source: `src/engram/cli.py:440-455`, `tests/test_interview_cli.py:61-78`, `tests/test_interview_cli.py:81-94`
Rationale: The `phase3 interview export` parser is constructed with
`formatter_class=argparse.ArgumentDefaultsHelpFormatter` and
`--privacy-tier-max … type=int, default=1`, so `engram phase3
interview export --help` surfaces `(default: 1)` next to the flag —
a real operator-visible default rather than a hidden one. The CLI
runtime (`run_phase3_interview_export`, `cli.py:1743-1806`) reads
`int(args.privacy_tier_max)` and passes it as `WHERE privacy_tier <=
%s` directly. The dispatch test
`test_phase3_interview_export_default_privacy_tier_max_is_one`
asserts the default flows through to the driver namespace as `1`,
and `test_phase3_interview_export_explicit_tier_max_passthrough`
confirms the override mechanism. RFC 0021 § Privacy and provenance:
satisfied.

### A005 — All interview commands live under `engram phase3 interview`
Severity: nit
Source: `src/engram/cli.py:402-487`, `src/engram/cli.py:879-892`, `tests/test_interview_cli.py:34-58`
Rationale: The seven subcommands (`start`, `resume`, `history`,
`export`, `list-sessions`, `coverage`, `enable-active-learning`)
are added to the `phase3` subparser group only — no bare
`subparsers.add_parser("interview", …)` call exists at the top
level (verified by `grep "subparsers.add_parser"` enumeration of
top-level parsers; only `phase1` / `phase2` / `phase3` / `phase4`
group commands appear). The dispatch table at lines 879-892
routes each `phase3-interview-*` command to its driver. The
test `test_bare_engram_interview_is_rejected` confirms argparse
exits non-zero on `cli.main(["interview", "--help"])`. RFC 0025 /
D078 honored.

### A006 — D044 / D052 invariants hold at the loader layer
Severity: nit
Source: `src/engram/interview/agent.py:1-122`, `src/engram/interview/storage.py:1-272`, `src/engram/interview/sampler.py:1-369`
Rationale: A repository-wide grep (`grep -rn
"consolidator.transitions" src/engram/interview src/engram/cli.py`)
returns no hits — the gold-label loader does not call
`engram.consolidator.transitions`, so a `false` verdict cannot
mechanically flip `beliefs.status`. The agent's `record_verdict`
(agent.py:77-122) inserts one `gold_labels` row and stops; no
subsequent `UPDATE beliefs SET status …` exists in the v1 surface.
Belief status appears only as a *read* column in
`sampler.py:259-260` (the strata pull) and in the schema's
`belief_status` column. RFC 0021 § Relationship to other artifacts
§ D044 / D052 invariants: satisfied at code-review level. The
companion synthetic-audit-input guard is a separate concern; see
A011.

### A007 — Prompt template versioning matches RFC 0017
Severity: nit
Source: `src/engram/interview/agent.py:21-24`, `prompts/interview/claim_v1.md:1-5`, `prompts/interview/belief_v1.md:1-5`, `migrations/010_gold_labels.sql:128-136`
Rationale: The Python constants
`INTERVIEW_TEMPLATE_VERSION_CLAIM_V1 = "interview.claim.v1.d079.initial"`
and `INTERVIEW_TEMPLATE_VERSION_BELIEF_V1 = "interview.belief.v1.d079.initial"`
match the front-matter `template_version` values in the on-disk
templates verbatim. The path constants (`prompts/interview/
claim_v1.md`, `belief_v1.md`) match the actual files. The
schema-level `chk_gold_labels_template_path_matches_version`
CHECK accepts substring matches in three forms (third-dot
component, raw version, dot-to-underscore) — the canonical
combination passes via `'v1'` substring. RFC 0017 versioning:
satisfied. The CHECK is loose by design (verifier V004 nit;
RFC § Storage already calls it "best-effort").

### A008 — Cooldown env vars are read at module top
Severity: nit
Source: `src/engram/interview/sampler.py:36-54`, `tests/test_interview_sampler.py:67-104`
Rationale: All seven `ENGRAM_GOLD_COOLDOWN_<CLASS>_DAYS` constants
(plus `ENGRAM_GOLD_ACTIVE_LEARNING_THRESHOLD`) are bound at module
import via `int(os.environ.get(…, default))`, matching RFC 0012's
"tunables live behind ENGRAM_-prefixed env vars read at module
top." `test_cooldown_env_var_overrides_apply_at_module_top` proves
the contract by calling `importlib.reload(sampler_module)` after
`monkeypatch.setenv(…)` and asserting `cooldown_days_for("goal")`
returns the new value. The defaults (mood 3, task 7, goal 14,
preference 30, project_status 30, relationship 60, identity 90)
match the RFC § Sampler § Cooldowns table exactly.

### A009 — Storage helper passes NULL for a NOT NULL column
Severity: nit
Source: `src/engram/interview/storage.py:140-216`, `migrations/010_gold_labels.sql:110`, `migrations/010_gold_labels.sql:230` (BEFORE INSERT trigger ordering)
Rationale: When the operator omits `privacy_tier`, the
`insert_label` helper computes `effective_tier = 0` (dead code)
but then passes `effective_tier if privacy_tier is not None else
None` as the SQL parameter (line 216) — i.e. literal NULL for a
column declared `NOT NULL`. The path works only because
`fn_gold_labels_carry_privacy_tier` is a `BEFORE INSERT` trigger
that writes `NEW.privacy_tier := parent_tier` before PostgreSQL
checks the NOT NULL constraint. The storage tests
(`tests/test_interview_storage.py:106-152`) exercise the path so
the dependency is demonstrably honored. Worth a single-line code
comment ("relies on `gold_labels_01_carry_privacy_tier` BEFORE
INSERT to satisfy NOT NULL") so a future trigger rename — already
called out as a brittle naming convention — does not silently
regress to a NOT NULL violation. The verifier flagged the same
hazard as V005; concur.

### A010 — `enable-active-learning` is reachable from the CLI but not from `make`
Severity: minor
Source: `src/engram/cli.py:479-487`, `Makefile:147-163`
Rationale: The CLI subparser exists and the driver
`run_phase3_interview_enable_active_learning` is wired and tested
(`tests/test_interview_cli.py:209-237`). The Makefile, however,
adds only six `phase3-interview-*` rule lines (start, resume,
history, export, list-sessions, coverage; lines 147-163) and the
`.PHONY` declaration on line 11 likewise omits the seventh target.
The work-packet criterion was "≥ 6 phase3-interview-* targets" so
the contract is met, but RFC § CLI v1 names seven subcommands and
the operator surface should be symmetric — `make
phase3-interview-enable-active-learning SIGNAL_VERSION=…` is the
expected ergonomic. Already flagged by the verifier (V002);
non-blocking, fix in a follow-up.

### A011 — `fn_gold_labels_block_synthetic_audit_input` is deferred
Severity: minor
Source: `migrations/010_gold_labels.sql` (no occurrence of `fn_gold_labels_block_synthetic_audit_input`), `docs/rfcs/0021-gold-set-interview-curation.md:219-222`, `docs/rfcs/0021-gold-set-interview-curation.md:528-535`
Rationale: RFC 0021 § Storage names four triggers; the migration
ships three. The fourth — a CHECK or trigger preventing
`belief_audit.input_claim_ids` from referencing a gold-label-derived
synthetic claim — would defend D044's "no auto-promotion" rule on
the audit table, separate from the loader-level invariant the
implementation does honor (A006). RFC § Relationship to other
artifacts § D044 frames the rule as "code-review invariant on the
loader **plus** a schema-level guard on the audit table"; v1 ships
only the first half. Acknowledged-risk: v1 ships **no** gold-label
→ synthetic-claim promotion path, so there is no producer that
could violate the invariant today. The handoff explicitly calls
this out ("three named triggers"), and F010 / RFC § What this RFC
does **not** propose ("not auto-promote synthetic claims") frames
synthetic-claim promotion as deferred. The trigger should land
before any auto-promotion machinery — once that path exists, the
guard becomes load-bearing rather than defense-in-depth — but it
is not blocking for v1 acceptance. Verifier reached the same
conclusion (V001).

### A012 — Strata vocabulary column names diverge from RFC literal
Severity: nit
Source: `migrations/010_gold_labels.sql:27-32`, `docs/rfcs/0021-gold-set-interview-curation.md:243-248`
Rationale: RFC § Storage shows
`gold_label_strata_vocabulary (key_name TEXT, key_value TEXT, gloss
TEXT, PRIMARY KEY (key_name, key_value))`. The migration declares
`(stratum_kind TEXT, key TEXT, display TEXT, PRIMARY KEY
(stratum_kind, key))`. Functionally identical; the seed covers all
four required RFC key types (stability_class × seven values,
conf_band × five, recency_band × five, belief_status × three) —
pulled in directly from the migration body. If the synthesis intent
was strict mirror with `predicate_vocabulary` (D057), the column
rename plus matching seed text would land that intent. Out of
scope for blocking acceptance; verifier (V003) flagged the same.

### A013 — Verdict vocabulary seeded with all six values plus ordinal
Severity: nit
Source: `migrations/010_gold_labels.sql:58-71`
Rationale: The migration seeds the six RFC-required verdicts
(`true`, `false`, `stale`, `unsupported`, `unsure`, `skip`) with
glosses and ordinals 1-6. The `gold_labels.verdict` column has a
FK to this table (`migrations/010_gold_labels.sql:94`), so any
attempt to insert a verdict outside the six fails at write time
in addition to the application-level `VALID_VERDICTS` frozenset
(`agent.py:26-28`). The agent tests confirm
`record_verdict("bogus", …)` raises `GoldLabelVerdictError`
before reaching SQL. The `ordinal` column is a v1 extension over
the RFC literal `(verdict TEXT, gloss TEXT)`; harmless.

### A014 — `current_gold_label` view tiebreaker matches RFC § Storage
Severity: nit
Source: `migrations/010_gold_labels.sql:281-334`, `tests/test_interview_storage.py:299-358`
Rationale: The view partitions by
`(target_kind, target_id, COALESCE(extraction_*, ''), COALESCE(
consolidation_*, ''), request_profile_version)` — exactly the
"per-version-triple" partition the RFC § Storage worked example
calls for, with the COALESCE handling the kind-disjoint NULLs.
Ordering is `answered_at DESC` then a verdict-rank `CASE`
mapping `true|false|stale|unsupported → 0` (outranks) and
`unsure|skip → 1` (loses ties). The schema test
`test_current_gold_label_returns_latest_per_version_triple`
inserts an older `false` and a newer `true` and asserts the view
returns `true` — the latest-`answered_at` half of the tiebreak.
The verdict-rank arm is not directly exercised but is correctly
written. RFC § Storage / promotion path: satisfied for v1.

### A015 — Test coverage rules out live-LLM contamination
Severity: nit
Source: `tests/test_interview_cli.py:1-238`, `tests/test_interview_sampler.py:1-286`, `tests/test_interview_storage.py:1-384`
Rationale: All three new test modules are deterministic. The CLI
tests stub `cli.connect` with a `SimpleNamespace` (`fake_cli_connect`
fixture) and monkeypatch driver functions to capture argv. The
sampler tests use a hand-rolled `MockConn` that switches on query
substrings; no `psycopg.connect` calls. The storage tests rely on
the existing `conn` fixture (test DB), but seed data via plain
`INSERT` helpers from sister test modules (`test_phase2_segments`,
`test_phase3_claims_beliefs`) — no live LLM, no network. Each of
the three load-bearing triggers has a dedicated negative test
(append-only UPDATE *and* DELETE, dangling target_id, privacy-tier
mismatch). RFC 0012 / coding-standard "deterministic, no live LLM"
test rule: satisfied.

## Verifier alignment

The standalone verification report (`VERIFICATION_REPORT.md`,
verdict `accept_with_findings`) reaches the same shape this
review reaches: load-bearing schema, sampler, storage, CLI, and
template wiring all match the contract; the residual gaps
(`fn_gold_labels_block_synthetic_audit_input` deferred,
`enable-active-learning` Makefile target missing, schema-naming
nits) are minor. A001–A009 above are this review's independent
re-walk of the audit checklist; A010 / A011 / A012 cross-reference
the verifier's V002 / V001 / V003 respectively, with the same
severity. No conflicts with the verifier's findings.

## Residual risks (acknowledged, not blocking)

- **F010 trigger deferred.** A011 above. v1 has no synthetic-claim
  promotion path, so there is no producer that could violate the
  invariant today. Land the trigger before any auto-promotion
  machinery does.
- **Trigger ordering by alphabetical naming.** Renaming
  `gold_labels_00_validate_target` or `gold_labels_01_carry_privacy_tier`
  silently regresses the parent-validation message and (per A009)
  the storage helper's NULL-tier path. Handoff documents the
  convention; future migrations touching these triggers must keep
  the prefix.
- **Sampler is shuffle-and-take.** v1 stamps `strata_weights` onto
  the session row but does not yet rebalance pulls. RFC § Sampler
  v1 explicitly defers to v1.1.
- **Active-learning bias is opt-in stamping only.** No re-ranking;
  RFC Open Q 4 deferred to v1.1.
- **CLI `start` is non-interactive.** v1 commands are smoke-test
  surfaces; web v2 lands the operator loop. Handoff acknowledges.
- **Loose template-path CHECK.** A007 / verifier V004. Substring
  match is RFC-spec; flagged for completeness.

## Verdict

verdict: accept_with_findings

One-sentence rationale: the load-bearing contract — append-only
trigger, polymorphic FK guard, privacy-tier carry, fail-closed
Tier 1 export, phase-scoped CLI under `engram phase3 interview …`,
RFC 0017 template versioning, and D044 / D052 loader invariants —
is implemented and exercised by deterministic negative tests; the
residual gaps (F010 trigger deferred per RFC text and a v1 with no
producer that could violate it, `enable-active-learning` Makefile
target missing, NOT-NULL helper hazard documented as a comment-only
fix, minor schema-naming and CHECK-looseness nits) are minor and
non-blocking, matching the verifier's accept_with_findings disposition.
