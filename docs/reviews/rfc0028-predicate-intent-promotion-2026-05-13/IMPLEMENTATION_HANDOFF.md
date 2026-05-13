author: operator [self-declared: rfc0028-author-codex]

# RFC 0028 Implementation Handoff

## Summary

The owner-directed RFC 0028 implementation slice is present in the worktree
and was audited against the fresh 2026-05-13 implementation prompt.

The implemented code adds advisory predicate subject-kind metadata,
surfaces predicate intent in the extraction prompt, shows predicate intent and
advisory subject-kind warnings in the shared CLI/web interview render path,
and broadens the `false` rationale prompt. No claim, belief, or gold-label row
contract changes were introduced.

Because this is the author pass, not the final-review/promotion pass, no
`DECISION_LOG.md` row was added. RFC 0028 remains `proposal`; its
implementation status is now recorded as `implemented` pending fresh review.

## Implementation Files Audited

- `migrations/012_predicate_subject_kind_hint.sql`
- `src/engram/extractor.py`
- `src/engram/cli.py`
- `src/engram/interview/render.py`
- `src/engram/interview/web.py`
- `src/engram/interview/templates/question.html`
- `tests/test_phase3_claims_beliefs.py`
- `tests/test_interview_render.py`
- `tests/test_interview_web.py`
- `tests/test_migrations.py`
- `docs/schema/README.md`

## Files Changed In This Pass

- `CHANGELOG.md`
- `docs/rfcs/0028-predicate-intent-surfacing.md`
- `docs/rfcs/README.md`
- `docs/reviews/rfc0028-predicate-intent-promotion-2026-05-13/IMPLEMENTATION_HANDOFF.md`

`docs/schema/README.md` was regenerated from the local test database after
removing stale migration-checksum probe tables; the generated schema output
matched the checked-in file, so it has no diff.

## Verification

```sh
PYTHONPATH=src ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test \
  /home/halbritt/git/engram/.venv/bin/python -m pytest \
  tests/test_interview_render.py \
  tests/test_migrations.py::test_rfc0028_migration_012_exists_on_disk \
  tests/test_migrations.py::test_012_predicate_subject_kind_hint_applies \
  tests/test_phase3_claims_beliefs.py::test_predicate_vocabulary_and_extractor_schema_parity \
  tests/test_phase3_claims_beliefs.py::test_build_extraction_prompt_surfaces_predicate_intent \
  tests/test_phase3_claims_beliefs.py::test_phase3_schema_preflight_accepts_current_schema \
  tests/test_phase3_claims_beliefs.py::test_phase3_schema_preflight_detects_semantic_schema_drift \
  tests/test_interview_web.py::test_question_page_uses_shared_false_rationale_prompt \
  tests/test_interview_web.py::test_question_page_preserves_summary_line_whitespace
```

Result: `57 passed in 12.96s`.

```sh
PYTHONPATH=src ENGRAM_DATABASE_URL=postgresql:///engram_test \
  /home/halbritt/git/engram/.venv/bin/python scripts/gen_schema_docs.py
```

Result: schema docs regenerated successfully; no checked-in schema diff
remained after removing temporary `migration_checksum_probe_%` tables from the
test database.

```sh
python3 scripts/check_artifact_refs.py --root .
```

Result: 0 errors, 5 pre-existing warnings.

## Residual Risks

- Full-corpus re-extraction was intentionally not run. RFC 0028 still requires
  a bounded extractor bench before any corpus-wide `phase3 re-extract`.
- The subject-kind warning heuristic is deliberately small and advisory. It
  can miss non-person subjects outside the curated/local-entity cases, and it
  should not be treated as validation or lifecycle state.
- Promotion remains pending fresh review. This handoff records implementation
  status only.
