# RFC 0028 Predicate Intent Implementation Review — Codex
author: operator [self-declared: rfc0028-review-codex]

Status: review
Date: 2026-05-13
RFC refs: RFC-0028
Decision refs: current RFC 0028 proposal and fresh review evidence
Phase refs: PHASE-0003, PHASE-0003-FOLLOWON

## Findings

### F001 — Prompt-version provenance is not yet promotion-clean
Severity: major
Source: `src/engram/extractor.py:37`; `migrations/012_predicate_subject_kind_hint.sql:1`; `docs/rfcs/0017-extraction-prompt-versioning.md:64-69`; `docs/rfcs/0028-predicate-intent-surfacing.md:164-168`; `DECISION_LOG.md:104-105`

Rationale: The runtime prompt version is already `extractor.v9.d082.predicate-intent`, and migration 012 also cites `D-082`, but `DECISION_LOG.md` currently stops at D081. RFC 0017 treats the version string as the join key between persisted extraction rows and a governed prompt artifact, and RFC 0028 says the new prompt artifact should land under the conventional extraction-prompt path. I found no `prompts/extraction/` artifact for v9; the only prompt files under `prompts/` are the interview templates. Before promotion or any non-scratch re-extraction writes rows under v9, either record the binding D082 decision and add the immutable extraction prompt artifact, or switch the version/comment to a non-decision tag and explicitly document the artifact exception.

### F002 — Subject-kind warnings can false-positive on ambiguous entities
Severity: major
Source: `src/engram/interview/render.py:274-278`; `src/engram/interview/render.py:301-314`

Rationale: `subject_kind_warning()` warns when any active entity row for the subject has a non-person kind. Because `entities` is unique on `(entity_kind, canonical_key)`, the same canonical key can legitimately have both `person` and `place` rows for ambiguous names. In that case the current loop skips the `person` row, then returns a "Likely a `false` extraction" warning for the non-person row. The warning is intentionally advisory, but this exact wording can bias operator verdicts on valid person-subject claims. Suppress the warning when an active `person` entity is also present, and add a regression test with `fetchall()` returning both `("person",)` and a non-person kind.

## Open questions

- Should the curated `_KNOWN_NON_PERSON_SUBJECTS` substring fallback stay substring-based after promotion? It is useful for known bad labels like Hobnob, but it can warn on longer valid subject strings that merely contain a listed token.
- Is the promotion pass expected to create D082 immediately, or should the prompt version use a date/proposal tag until the bounded bench result is accepted?

## Verification

Focused local tests passed:

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

Result: `57 passed in 13.66s`.

verdict: needs_revision
