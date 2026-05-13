# RFC 0028 Prompt Literal Re-Review

author: operator [self-declared: rfc0028-prompt-literal-review]

Status: review
Date: 2026-05-13
RFC refs: RFC-0028, RFC-0017
Decision refs: D082
Phase refs: PHASE-0003

## Scope

This is a narrow re-review of the RFC 0028 prompt-literal repair after the
prior focused review found that the governed v9 prompt artifact recorded Python
f-string escape syntax instead of the runtime zero-claim literal. I reviewed
only the zero-claim prompt literal in `prompts/extraction/extractor_v9.md`, the
runtime prompt builder in `src/engram/extractor.py`, and the focused tests in
`tests/test_phase3_claims_beliefs.py`.

This review does not promote RFC 0028 and does not resolve D082. D082 remains a
proposed prompt-version reservation.

## Findings

No findings.

## Resolved Checks

### 1. Governed artifact now records the rendered runtime literal

Resolved. `prompts/extraction/extractor_v9.md:112` now records:

```text
- If no valid claims remain, return exactly {"claims":[]}.
```

I found no `{{"claims":[]}}` occurrence in `prompts/extraction/extractor_v9.md`.
The remaining doubled-brace occurrences are in Python f-string source or in the
prior review text; they are not present in the governed v9 prompt artifact.

### 2. Artifact test guards against the escaped-source regression

Resolved. `tests/test_phase3_claims_beliefs.py:296-311` derives the governed
artifact path from `EXTRACTION_PROMPT_VERSION`, reads the artifact, asserts the
single-brace zero-claim line is present, and asserts the double-brace escaped
variant is absent. That directly covers the prior artifact drift.

### 3. Runtime prompt behavior is pinned

Resolved. `tests/test_phase3_claims_beliefs.py:314-339` builds a real runtime
prompt through `build_extraction_prompt()` and asserts the rendered prompt
contains the single-brace `{"claims":[]}` instruction. This guards the f-string
escape boundary: `src/engram/extractor.py:2288` must use doubled braces in
source so the runtime string sent to the model renders as the single-brace JSON
literal.

## Verification

No network access was used.

Focused local tests passed:

```sh
PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_phase3_claims_beliefs.py::test_extraction_prompt_version_has_governed_artifact \
  tests/test_phase3_claims_beliefs.py::test_build_extraction_prompt_surfaces_predicate_intent
```

Result: `2 passed in 0.06s`.

## Verdict

verdict: accept
