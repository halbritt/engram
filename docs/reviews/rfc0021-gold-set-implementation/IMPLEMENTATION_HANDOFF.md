# RFC 0021 — Gold-Set Interview Curation: Implementation Handoff
author: author-codex-gpt-5.5-001

## Status / Date / RFC refs / Decision refs / Phase refs

- Status: implemented (v1, schema + sampler + storage + CLI surface)
- Date: 2026-05-08
- RFC refs: RFC 0021 (accepted), RFC 0017 (template versioning), RFC 0018
  (audit cascade reviewer — relationship), RFC 0025 (phase-scoped CLI)
- Decision refs: D044, D052, D057, D069, D073, D077, D078, D079
- Phase refs: PHASE-0003 (Phase 3 follow-on)

## Files changed

### Created

- `migrations/010_gold_labels.sql` — RFC 0021 schema: `gold_label_sessions`,
  `gold_label_strata_vocabulary`, `gold_label_verdict_vocabulary`,
  `gold_labels`, three named triggers (`fn_gold_labels_append_only`,
  `fn_gold_labels_validate_target`, `fn_gold_labels_carry_privacy_tier`),
  per-target-kind partial indexes, `current_gold_label` view.
- `src/engram/interview/__init__.py` — re-exports the public API
  (`GoldLabelStorage`, `GoldLabelSampler`, `InterviewAgent`, errors,
  template version constants, env defaults).
- `src/engram/interview/errors.py` — `InterviewError` domain root +
  `GoldLabelStorageError`, `GoldLabelSamplerError`, `GoldLabelVerdictError`.
- `src/engram/interview/storage.py` — `insert_session`, `insert_label`,
  `mark_session_completed`, `list_sessions`. Translates psycopg
  `errors.RaiseException` into `GoldLabelStorageError`.
- `src/engram/interview/sampler.py` — stratified sampler with seeded RNG;
  `ENGRAM_GOLD_COOLDOWN_<CLASS>_DAYS` env-var defaults; `SampledTarget`
  dataclass; `build_strata_key` pure helper; opt-in
  `active_learning_signal_version` stamping; per-call
  `candidate_pool_snapshot_id`.
- `src/engram/interview/agent.py` — `InterviewAgent` rendering surface;
  loads `prompts/interview/<kind>_v1.md`; verifies verdict membership and
  rationale length; routes to `storage.insert_label`.
- `prompts/interview/claim_v1.md` — RFC 0017 front-matter +
  claim-paraphrase question template + 6-verdict legend.
- `prompts/interview/belief_v1.md` — belief currently-true template with
  `valid_from` / `valid_to` placeholders.
- `tests/test_interview_cli.py` — 13 dispatch tests (help, fail-closed
  default tier 1, bare `engram interview` rejected, all 7 subcommands).
- `tests/test_interview_sampler.py` — 12 pure-python tests
  (band boundaries, env-var override, seed determinism, cooldown filter,
  skip exemption, snapshot id uniqueness, active-learning stamping).
- `tests/test_interview_storage.py` — 7 schema-level tests against the
  test DB (happy path, append-only UPDATE block, append-only DELETE
  block, dangling target_id, privacy-tier mismatch, current_gold_label
  view tiebreak, list_sessions state filter).
- `docs/reviews/rfc0021-gold-set-implementation/IMPLEMENTATION_HANDOFF.md`
  — this document.

### Modified

- `src/engram/cli.py` — added `phase3 interview {start,resume,history,
  export,list-sessions,coverage,enable-active-learning}` subparsers;
  driver functions; `--privacy-tier-max` defaults to `1`;
  `argparse.ArgumentDefaultsHelpFormatter` on the export parser so the
  fail-closed default is operator-visible. Added catch for
  `GoldLabelStorageError` / `GoldLabelVerdictError`.
- `Makefile` — six new phase3-interview-* targets next to existing
  phase3 targets; same names added to `.PHONY`.
- `tests/conftest.py` — extended schema-drop list with
  `gold_labels`, `gold_label_sessions`, `gold_label_verdict_vocabulary`,
  `gold_label_strata_vocabulary`, the `current_gold_label` view, and the
  three `fn_gold_labels_*` functions.
- `tests/test_migrations.py` — two new tests asserting migration 010 is
  on disk with the expected schema landmarks and applies cleanly via the
  conftest fixture.
- `README.md` — new "Phase 3 follow-on: Gold-set interview (RFC 0021)"
  subsection under Operator Quick Start.
- `CHANGELOG.md` — `## [Unreleased]` → `### Added` entry for the RFC
  0021 implementation.

### Files NOT edited (per work packet)

- `BUILD_PHASES.md`, `DECISION_LOG.md`, `HUMAN_REQUIREMENTS.md`
- `docs/rfcs/0021-gold-set-interview-curation.md`
- Any other RFC.

## Implementation notes

- **Trigger ordering.** PostgreSQL fires same-event row triggers in
  alphabetical order by trigger name. Naming the validate-target trigger
  `gold_labels_00_validate_target` (and the carry trigger
  `gold_labels_01_carry_privacy_tier`) ensures the parent-existence check
  emits "not found in claims/beliefs" before the carry trigger has a
  chance to complain about a missing parent row. The function names
  themselves remain `fn_gold_labels_validate_target` and
  `fn_gold_labels_carry_privacy_tier` per the RFC.
- **Append-only translation.** The append-only enforcement is at the
  schema layer (trigger raises `P0001`). The storage helpers translate
  `errors.RaiseException` → `GoldLabelStorageError` so callers see the
  domain error. The schema-level test uses a small `_exec_translated`
  wrapper around raw SQL for the same effect.
- **CLI v1 drivers are skeletal.** `start` opens a session and runs the
  sampler but does not interactively prompt; `resume`/`history`/
  `export`/`list-sessions`/`coverage`/`enable-active-learning` print
  bounded human-readable output. The schema, sampler determinism, and
  storage contract are the load-bearing v1 work; the interactive loop
  belongs to v1.5 / web v2.
- **Current-beliefs read fall-through.** The sampler reads `claims` and
  `current_beliefs`; if `current_beliefs` errors (e.g. the materialized
  view has not been refreshed in a fresh schema), the belief slice is
  treated as empty. `--include-superseded` switches the source to
  `beliefs` for adversarial sweeps.
- **Trigger CHECK on template path.** The CHECK
  `chk_gold_labels_template_path_matches_version` does a substring
  match (rather than a regex parse of the `{area}.v{N}.{date}.{descr}`
  RFC 0017 shape) to keep the cost negligible; the sampler/agent always
  pair canonical paths with their canonical version constants.

## Verification commands run

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest tests/test_interview_cli.py tests/test_interview_sampler.py -x` | 25 passed |
| `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_interview_storage.py tests/test_migrations.py -x` | 10 passed |
| `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest tests/test_migrations.py tests/test_interview_storage.py tests/test_audit_cascade_schema.py tests/test_phase4_entities_review.py` | 29 passed |
| `.venv/bin/python -m pytest tests/test_cli.py -x` | 15 passed, 10 skipped (skips require DB) |
| `.venv/bin/engram phase3 interview --help` | rc=0; lists 7 subcommands |
| `.venv/bin/engram phase3 interview export --help` | rc=0; shows `--privacy-tier-max ... (default: 1)` |
| `.venv/bin/engram interview --help` | rc=2; argparse rejects bare `interview` |
| `make check-refs` | 0 errors, 5 pre-existing warnings (unrelated) |

### Pre-existing test failure (NOT introduced by this work)

- `tests/test_phase3_claims_beliefs.py::test_cli_pipeline_is_phase2_only_and_pipeline3_warns`
  fails on this branch with and without my changes (verified by
  `git stash && pytest && git stash pop`). The test expects
  `cli.main(["pipeline", "--limit", "1"])` to return 0, but the RFC 0025
  fail-closed contract makes bare `pipeline` exit 2. The test predates
  RFC 0025 implementation. Out of scope for this work packet.

## Residual risks / known gaps

- **Active-learning bias is opt-in only at the stamping layer.** The v1
  sampler writes `active_learning_signal_version` onto every emitted row
  when the operator passes the constructor flag, but it does not yet
  re-rank candidates. The bias selection logic is deferred to v1.1 once
  RFC 0018 reviewer scores exist (RFC 0021 § Open Q 4).
- **CLI subcommands are smoke-test surfaces.** `start` does not
  interactively prompt the operator; `coverage` reports only by
  `stability_class`; `history` lists rows but does not pivot by version
  triple. Each is dispatch-correct and writes the right rows but is
  intentionally minimal.
- **Stratified rebalancing is shuffle-and-take.** v1 honors the strata
  *vocabulary* (typed columns, validation against
  `gold_label_strata_vocabulary`) but does not yet weight pulls per
  stratum. RFC § Sampler v1 explicitly defers deeper introspection
  (`inspect-strata-balance`, `dry-run`) to v1.1.
- **No interactive Ctrl-C / save-and-quit shell.** The mid-session
  semantics described in the RFC apply once the interactive loop lands;
  v1 stores rows only on explicit `record_verdict` calls.
- **Cross-walk to `audit_reason_vocabulary` is deferred.** RFC § D073
  notes a v1.5 mapping between `false` and the cascade reviewer's
  fact-correction reason. v1 ships the gloss-only verdict vocabulary.
- **Trigger ordering is a naming convention.** Renaming the triggers
  (e.g. dropping the `00_` / `01_` prefixes) would silently regress the
  parent-validation message. The names are documented above and
  defended by `test_dangling_target_id_is_rejected`.

## Next steps (per work-packet handoff)

The remaining jobs in this run are:

1. `verify_gold_set` — spec-check the implementation against the
   accepted RFC 0021 contract (schema columns, trigger names, vocabulary
   seed values, CLI surface, prompts).
2. `final_review` — multi-agent review of the implementation; record
   findings under `docs/reviews/rfc0021-gold-set-implementation/`.

Operators wishing to drive the loop programmatically can import
`engram.interview.InterviewAgent` and pair it with `GoldLabelSampler` and
`insert_session` as documented in the module docstrings.
