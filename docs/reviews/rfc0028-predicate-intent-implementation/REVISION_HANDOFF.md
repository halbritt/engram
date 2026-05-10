author: author-codex-gpt-5.5-002

# RFC 0028 Revision Handoff

## Summary

Applied the accepted findings from `REVISION_SYNTHESIS.md`.

L001 is fixed by restricting `subject_kind_warning` to strictly person-only
hints and adding regression coverage for mixed allowed hints such as
`persons or projects`, `persons or organizations`, and
`persons or households`.

L002 is fixed by adding `predicate_vocabulary.description` and
`predicate_vocabulary.subject_kind_hint` to Phase 3 required columns, carrying
the discovered table columns into the semantic vocabulary check, and skipping
the SELECT-based semantic comparison when required vocabulary columns are
absent so `Phase3SchemaPreflightError` reports missing columns cleanly.

L004 is fixed by preserving whitespace for web summary lines in
`question.html` and pinning that markup hook with a web test.

L005 is fixed by adding a `predicate_vocabulary.description` drift case to the
Phase 3 preflight drift test.

L003 remains deferred per synthesis. The curated substring warning heuristic
is advisory and render-only; tightening it should wait for concrete operator
feedback.

## Changed Files

- `src/engram/cli.py`
- `src/engram/interview/render.py`
- `src/engram/interview/templates/question.html`
- `tests/test_interview_render.py`
- `tests/test_interview_web.py`
- `tests/test_phase3_claims_beliefs.py`

## Verification

Focused RFC 0028 test slice:

```text
ENGRAM_TEST_DATABASE_URL="postgresql:///engram_test" .venv/bin/python -m pytest tests/test_interview_render.py tests/test_migrations.py::test_rfc0028_migration_012_exists_on_disk tests/test_migrations.py::test_012_predicate_subject_kind_hint_applies tests/test_phase3_claims_beliefs.py::test_predicate_vocabulary_and_extractor_schema_parity tests/test_phase3_claims_beliefs.py::test_build_extraction_prompt_surfaces_predicate_intent tests/test_phase3_claims_beliefs.py::test_phase3_schema_preflight_accepts_current_schema tests/test_phase3_claims_beliefs.py::test_phase3_schema_preflight_detects_semantic_schema_drift tests/test_interview_web.py::test_question_page_uses_shared_false_rationale_prompt tests/test_interview_web.py::test_question_page_preserves_summary_line_whitespace
```

Result: `57 passed in 13.54s`.

Whitespace check:

```text
git diff --check
```

Result: passed.
