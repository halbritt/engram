author: author-codex-gpt-5.5-001

# RFC 0028 Predicate-Intent Implementation Handoff

## Summary

This implementation surfaces predicate intent in both extraction and gold-label interview review without changing claim, belief, or gold-label row contracts.

The extractor prompt version is now `extractor.v9.d082.predicate-intent`. Runtime predicate vocabulary entries carry both the existing `description` and a new advisory `subject_kind_hint`; `build_extraction_prompt` renders both as an `intent:` line for every predicate.

Migration `012_predicate_subject_kind_hint.sql` adds nullable `predicate_vocabulary.subject_kind_hint`, checks nonblank values when present, and seeds hints for the current predicate vocabulary. Phase 3 schema preflight now compares DB and runtime `description` plus `subject_kind_hint` to catch semantic vocabulary drift.

The shared interview rendering layer now renders predicate intent on a separate line, broadens the `false` rationale prompt beyond "correct value", and adds an advisory local heuristic warning when a person-only predicate is shown on an obviously non-person subject. The warning is render-time guidance only; it does not validate, mutate, or relabel claims.

## Changed Files

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
- `docs/rfcs/0028-predicate-intent-surfacing.md`
- `docs/rfcs/README.md`
- `DECISION_LOG.md`
- `CHANGELOG.md`
- `docs/schema/README.md`

The run also refreshed local Striatum skills under `.claude/skills` and `.codex/agents`, and added the workflow scaffold under `striatum/rfc-0028-predicate-intent-implementation/`.

## Verification

Focused test run:

```text
ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test" .venv/bin/python -m pytest tests/test_interview_render.py tests/test_migrations.py::test_rfc0028_migration_012_exists_on_disk tests/test_migrations.py::test_012_predicate_subject_kind_hint_applies tests/test_phase3_claims_beliefs.py::test_predicate_vocabulary_and_extractor_schema_parity tests/test_phase3_claims_beliefs.py::test_build_extraction_prompt_surfaces_predicate_intent tests/test_phase3_claims_beliefs.py::test_phase3_schema_preflight_accepts_current_schema tests/test_phase3_claims_beliefs.py::test_phase3_schema_preflight_detects_semantic_schema_drift tests/test_interview_web.py::test_question_page_uses_shared_false_rationale_prompt
```

Result: `51 passed in 11.89s`.

Schema docs were regenerated from a clean `engram_test` database after applying migrations:

```text
DATABASE_URL=postgresql:///engram_test make migrate
make schema-docs DATABASE_URL=postgresql:///engram_test
```

`git diff --check` passes.

## Known Gaps And Review Targets

I did not run a bounded 100-500 segment re-extraction bench; RFC 0028 keeps that as the promotion gate before any full-corpus re-extraction.

The warning heuristic is intentionally small and advisory. Review should pay close attention to false positives in `subject_kind_warning`, especially the curated non-person subject list and the active-entity lookup.

`ruff check` was not treated as a final gate because the touched files still trip existing repository baseline issues outside this slice. The focused tests above are the implementation gate for this pass.
