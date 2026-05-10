# RFC 0028 Predicate Intent Implementation Review — claude
author: reviewer-claude-opus-002

Status: review
Date: 2026-05-09
RFC refs: RFC-0028
Decision refs: D082
Phase refs: PHASE-0003, PHASE-0003-FOLLOWON

## Scope

Contract review of the RFC 0028 / D082 implementation against the eight-item
checklist in `striatum/rfc-0028-predicate-intent-implementation/prompts/review.md`.
The review is contract-only: read the touched code, schema, tests, and docs;
do not re-run the focused tests reported in the handoff. Implementation
surface inspected:

- `migrations/012_predicate_subject_kind_hint.sql`
- `src/engram/extractor.py` (PREDICATE_INTENT_METADATA, PREDICATE_VOCABULARY,
  EXTRACTION_PROMPT_VERSION, build_extraction_prompt)
- `src/engram/cli.py::phase3_schema_preflight` and
  `_check_phase3_predicate_vocabulary`
- `src/engram/interview/render.py` (RATIONALE_PROMPT_BY_VERDICT,
  fetch_target_display, format_summary_line, subject_kind_warning, helpers)
- `src/engram/interview/web.py` and `templates/question.html`
- `tests/test_phase3_claims_beliefs.py`,
  `tests/test_interview_render.py`, `tests/test_migrations.py`,
  `tests/test_interview_web.py`
- `CHANGELOG.md`, `DECISION_LOG.md`, `docs/rfcs/0028-…`,
  `docs/rfcs/README.md`, `docs/schema/README.md`

## Findings

### F001 — Migration 012 is additive, nullable, idempotent under the runner, and does not weaken append-only invariants
Severity: nit (informational; PASS)
Source: `migrations/012_predicate_subject_kind_hint.sql:1-46`,
`tests/test_migrations.py:111-156`
Rationale: The migration adds a single nullable column
`predicate_vocabulary.subject_kind_hint TEXT NULL` (line 5–6), guards it with
`chk_predicate_vocabulary_subject_kind_hint_nonblank` allowing NULL but
forbidding blank text (line 8–10), and seeds 29 rows via a single VALUES-driven
UPDATE keyed on `predicate` (line 12–46). No claim, belief, gold-label, or
evidence table is touched; the touched table is the small vocabulary lookup
that has never been append-only by design (it is updated by migrations as the
vocabulary evolves). Idempotency is delegated to the standard
`schema_migrations` checksum ledger that already governs every migration in
this repo (see `test_migration_checksums_detect_changed_applied_file` and the
ledger-driven `migrate(...)` helper); the file itself is run once and then
checksum-pinned, so it correctly does not need `IF NOT EXISTS` guards.
`tests/test_migrations.py:111-156` covers (a) the migration file exists,
mentions RFC 0028 and the column, and (b) post-migration the seeded value for
`has_name` is `('legal or preferred name', 'persons only')` and a blank
`subject_kind_hint` UPDATE raises CheckViolation. PASS.

### F002 — Runtime predicate vocabulary matches DB; preflight catches drift on description and subject_kind_hint
Severity: nit (informational; PASS)
Source: `src/engram/extractor.py:83-152`,
`src/engram/extractor.py:388-393`,
`src/engram/cli.py:1025-1076`,
`tests/test_phase3_claims_beliefs.py:227-293`,
`tests/test_phase3_claims_beliefs.py:2289-2330`
Rationale: `PREDICATE_INTENT_METADATA` (extractor.py:83-152) carries a
`{description, subject_kind_hint}` pair for all 29 base predicates and is
merged into `PREDICATE_VOCABULARY` via dict-spread at module load
(388-391). `_check_phase3_predicate_vocabulary` selects the seven structural
columns plus `description` and `subject_kind_hint` from
`predicate_vocabulary` (cli.py:1044-1051) and compares each predicate row
against the runtime expected row across both new keys (1062-1075). The DB-
backed parity test (`test_predicate_vocabulary_and_extractor_schema_parity`,
test_phase3_claims_beliefs.py:227-293) explicitly asserts
`intent_rows[predicate] == {description, subject_kind_hint}` for every
runtime entry. The parameterized drift test
`test_phase3_schema_preflight_detects_semantic_schema_drift`
(test_phase3_claims_beliefs.py:2289-2330) covers `subject_kind_hint` drift
(`UPDATE … SET subject_kind_hint = 'places only' WHERE predicate = 'has_name'`
expected to raise `Phase3SchemaPreflightError` matching
`has_name\.subject_kind_hint`). The 29 hint values in the migration match the
runtime metadata one-for-one (spot-checked: has_name=persons only,
uses_tool=persons or projects, project_status_is=projects only,
lives_at=persons or households, owns_repo=persons or organizations, …).
PASS.

### F003 — Extraction prompt version bumped to v9.d082; old rows stay versioned under prior prompts
Severity: nit (informational; PASS)
Source: `src/engram/extractor.py:37-40`,
`src/engram/extractor.py:2243-2298`,
`src/engram/extractor.py:2960-2975`,
`tests/test_phase3_claims_beliefs.py:228`
Rationale: `EXTRACTION_PROMPT_VERSION = "extractor.v9.d082.predicate-intent"`
matches `EXTRACTION_PROMPT_VERSION_REGEX` (`^extractor\.v\d+\.[a-z0-9_-]+\.[a-z0-9_-]+$`).
The default kwarg propagates through `extract_pending_claims`,
`extract_pending_claims_concurrently`, and the re-extract entry point
(extractor.py:2319/2378/2960). The regex enforces the version-bump
discipline from RFC 0017; the re-extract guard
(`re-extracting under the same version` short-circuit at 2965-2975) keeps
old rows attached to their prior prompt version because each row's
`extraction_prompt_version` is stamped at INSERT and never UPDATEd in
place (RFC 0017 immutability remains the contract).
`test_predicate_vocabulary_and_extractor_schema_parity` pins the literal
string `extractor.v9.d082.predicate-intent` so any future bump that breaks
the format trips the test. The RFC text's earlier draft figure
(`extractor.v6.d082.predicate-intent` in § Proposal) is harmless drift
inside an internal RFC pass; the same RFC's Promotion path (lines 366-369)
specifies `extractor.v9.d082.predicate-intent`, which is what shipped.
PASS.

### F004 — `build_extraction_prompt` renders descriptions and hints visibly without changing the JSON output contract
Severity: nit (informational; PASS)
Source: `src/engram/extractor.py:2243-2298`,
`tests/test_phase3_claims_beliefs.py:295-318`
Rationale: The vocabulary block now emits two lines per predicate, the
existing `- {predicate}: stability=…, cardinality=…, object_kind=…,
required_object_keys=…` line followed by `  intent: {description}
({subject_kind_hint})` (extractor.py:2251-2257). The system prompt
(`'Extract atomic, evidence-backed claims …'`),
`Return one JSON object with key "claims"`, the
`subject_text/predicate/object_text/object_json/stability_class/confidence/
evidence_message_ids/rationale` claim contract, and the explicit
`If no valid claims remain, return exactly {"claims":[]}` instruction are all
preserved verbatim around the augmented vocabulary block. The
extraction_json_schema is unchanged (parity test confirms `oneOf` absence,
strict and relaxed schemas, and the predicate enum still match the DB
predicates set; test_phase3_claims_beliefs.py:263-292). The new test
`test_build_extraction_prompt_surfaces_predicate_intent`
(test_phase3_claims_beliefs.py:295-318) asserts the literal substrings
`- has_name: stability=identity`,
`intent: legal or preferred name (persons only)`,
`intent: software or hardware tool (persons or projects)`, and the
unchanged `Return one JSON object with key "claims"`. PASS.

### F005 — `format_summary_line` puts intent on its own line; warning text is advisory and not overconfident
Severity: minor (non-blocking; advisory)
Source: `src/engram/interview/render.py:35-43`,
`src/engram/interview/render.py:113-241`,
`src/engram/interview/render.py:244-307`,
`src/engram/interview/render.py:378-395`,
`tests/test_interview_render.py:136-189`,
`tests/test_interview_render.py:481-505`
Rationale: `format_summary_line` (render.py:378-395) prepends the existing
summary (`subject -[predicate]-> object`), then emits `  intent: {description}`
optionally followed by ` ({subject_kind_hint})` when the hint is present, then
emits `  [warning] {subject_kind_warning}` when the heuristic fires. Three
golden-output tests pin every variant
(`test_format_summary_line_with_predicate_doc`,
`…_with_subject_kind_hint`, `…_with_subject_kind_warning`). The
warning helper (`subject_kind_warning`, render.py:244-270) is render-time
advisory only: it does not mutate, validate, or transition any belief or
claim row, and the docstring states this explicitly (RFC 0028 §
"Privacy and provenance" / "What this RFC does not propose"). Importantly, the
warning trigger keys on `"person" not in (subject_kind_hint or "").lower()`
which means the warning line fires for any predicate whose hint contains the
substring "person" (e.g. "persons only", "persons or projects",
"persons or organizations", "persons or households"). The rendered warning
sentence then hard-codes "predicate intent is persons" regardless of which
of those four hint phrasings produced the trigger
(`_format_subject_kind_warning`, render.py:303-307). For
`uses_tool`/`works_with`/`owns_repo` (hint values that include the word
"projects" or "organizations"), the warning slightly mischaracterizes the
predicate's intent. Recommendation (non-blocking): consider rendering the
exact `subject_kind_hint` value in the warning sentence, or scoping the
trigger to `subject_kind_hint == "persons only"` so the wording matches the
predicate's stated intent. The warning remains advisory either way and the
ambiguous wording does not weaken any invariant; this is a UX polish call.

### F006 — Substring matching in the hand-curated non-person list can over-trigger on names that contain a curated needle
Severity: minor (non-blocking; advisory)
Source: `src/engram/interview/render.py:56-62`,
`src/engram/interview/render.py:273-280`,
`tests/test_interview_render.py:481-505`
Rationale: `_KNOWN_NON_PERSON_SUBJECTS` is a small case-folded map (5 entries:
`alameda`, `encinal`, `evnotify`, `hobnob`, `nob hill foods`) drawn from the
operator-rationale evidence in RFC 0028. The lookup
(`_known_non_person_subject_label`, render.py:273-280) first attempts a
whole-string match, then falls through to a substring-`in` test:
`if needle in normalized: return label`. Any subject whose case-folded text
*contains* one of those needles will trip the warning. Concrete plausible
false positives: `"Alameda Schultz"` (a person whose surname or first name
happens to coincide with a curated needle) → warning labeled
`place/street`; `"Encinal Hardware Inc."` would trip the warning despite
already being recognizable as an organization, etc. RFC 0028 § Open
Question 2 explicitly accepts a small hand-curated list ("under 50 entries;
expand only when operators report specific misses") and § "Privacy and
provenance" notes that the heuristic is render-time advisory; it never
mutates a row. So the substring matching is *acceptable in v1* given the
warning's advisory posture, but it is worth tracking. Recommendation
(non-blocking): consider tightening the curated-list lookup to whole-token
matching (split on whitespace, compare each token to the curated set) or
to whole-string-only matching, deferring substring matching to the
`entities.entity_kind` lookup that already runs second. The
`active_entity_kinds_for_subject` SQL path (render.py:283-300) already uses
exact `lower()` and `engram_normalize_subject(...)` equality and is the
better long-term substrate. The handoff explicitly flagged this as a
review target ("Review should pay close attention to false positives in
`subject_kind_warning`") — confirming the implementer's own concern
matches what the heuristic actually does today.

### F007 — CLI and web use the same rationale prompt and summary rendering
Severity: nit (informational; PASS)
Source: `src/engram/interview/render.py:35-43`,
`src/engram/interview/render.py:347-356`,
`src/engram/interview/web.py:41-51`,
`src/engram/interview/web.py:482-554`,
`src/engram/interview/templates/question.html:13-17, 122`,
`tests/test_interview_render.py:419-446, 466-469`,
`tests/test_interview_web.py:465-472`
Rationale: `RATIONALE_PROMPT_BY_VERDICT` lives in `engram.interview.render`
and `web.py` imports it (line 44) and threads it into the question template's
context (`rationale_prompts` key, web.py:550) where the template emits it
through `tojson` (question.html:122) for the in-page two-click rationale
flow. The CLI's `rationale_prompt_for(verdict)` helper (render.py:347-356)
is the same dispatch path. `test_question_page_uses_shared_false_rationale_prompt`
(test_interview_web.py:465-472) renders the question page and asserts the
new false-rationale label is present (`what's wrong? (e.g., wrong
predicate, wrong subject, ...`, escaped as `'` by `tojson`) and the
old `correct value > ` label is absent. The CLI side is pinned by
`test_rationale_prompt_for_false_returns_correct_value`. The `format_summary_line`
output (one string per surface) is split on newlines into `summary_lines`
in `_render_question_template` (web.py:512-513) and rendered as one `<div>`
per line in the question template (question.html:13-17), which is the same
text the CLI prints with a four-space prefix. PASS.

### F008 — Focused tests cover prompt rendering, migration/preflight, rationale label, and warning rendering; no live LLM calls
Severity: nit (informational; PASS)
Source: handoff verification block (`51 passed in 11.89s`),
`tests/test_phase3_claims_beliefs.py:227-318`,
`tests/test_phase3_claims_beliefs.py:2285-2330`,
`tests/test_migrations.py:111-156`,
`tests/test_interview_render.py:136-189, 419-446, 481-505`,
`tests/test_interview_web.py:465-472`
Rationale: The eight tests required by the RFC's Promotion path are all
present and exercised under the focused `pytest` invocation reported in
`IMPLEMENTATION_HANDOFF.md` (51 passing in 11.89s). The extractor unit tests
(`test_phase3_claims_beliefs.py`) use `StaticExtractor` /
`SequenceExtractor` / `RelaxedFallbackExtractor` / `FlakyExtractor` /
`AlwaysFailExtractor` doubles instead of contacting the local LLM endpoint,
and the migration / preflight / render / web tests use psycopg / TestClient
flows against the `engram_test` fixture database with mocked extractors.
This satisfies the AGENTS.md / RFC 0012 contract that no live LLM calls
appear in unit tests. The `subject_kind_warning` helper has three
direct unit tests (`…_uses_curated_non_person_terms`,
`…_uses_active_entity_kind`, `…_skips_non_person_hints`) plus the indirect
coverage via `test_format_summary_line_with_subject_kind_warning`. PASS.
Minor gap (non-blocking): the parameterized
`test_phase3_schema_preflight_detects_semantic_schema_drift` covers
`subject_kind_hint` drift but not `description` drift; the production
preflight checks both columns equally (cli.py:1062-1075). Recommendation:
add one row to the parametrize for `description` to mirror the
`subject_kind_hint` case. Not blocking — the parity test
(`test_predicate_vocabulary_and_extractor_schema_parity`) already covers the
matching path for both columns, and the drift-detection code path is
identical.

### F009 — Docs are updated coherently across CHANGELOG, DECISION_LOG, RFC index, and schema reference
Severity: nit (informational; PASS)
Source: `CHANGELOG.md` Unreleased section (RFC 0028 / D082 entry),
`DECISION_LOG.md` D082 (line 106, accepted) and existing D016/D044/D069/D079/D080
references are intact, `docs/rfcs/0028-predicate-intent-surfacing.md`
front-matter (Status: accepted, Implementation: partial, Date: 2026-05-09,
Decision refs include D082, Review refs:
striatum/rfc-0028-predicate-intent-implementation, Phase refs PHASE-0003 +
PHASE-0003-FOLLOWON), `docs/rfcs/README.md:48`
(`| [0028](0028-predicate-intent-surfacing.md) | accepted | partial |
Predicate-intent surfacing across extraction and interview |`),
`docs/schema/README.md:326` (predicate_vocabulary diagram lists
`TEXT subject_kind_hint`), `docs/schema/README.md:824`
(`| subject_kind_hint | TEXT | YES | |` in the table reference, nullable=YES
matches migration). The handoff reports `make schema-docs` was rerun against
a freshly migrated `engram_test` database, consistent with the AGENTS.md
rule "Do not rewrite generated schema docs by hand; use `make schema-docs`."
PASS. Note: the implementation is correctly marked `partial` in the RFC and
the index — the bench (100–500 segment re-extraction) and full-corpus
re-extraction remain gated, which is the explicit RFC 0028 / D082 promotion
path and an honest characterization of state.

### F010 — Local-first / privacy posture and gold-label/claim/belief contracts are unchanged
Severity: nit (informational; PASS)
Source: `src/engram/interview/web.py:62-93, 215-225` (Tier 1 ceiling and
loopback Origin allowlist unchanged), `src/engram/interview/render.py`
(no new tables, no new mutations, no new outbound calls),
`migrations/012_predicate_subject_kind_hint.sql` (only touches
`predicate_vocabulary`), `D044/D069/D079` invariants intact (the loader does
not import `engram.consolidator.transitions` — the existing
`test_consolidator_transitions_unimportable_from_web` guard remains and the
new code does not reach across that boundary), AGENTS.md "no cloud
dependency" rule (no network calls, no telemetry, no external service
introduced).
Rationale: RFC 0028 promised "no change" to claims, beliefs, gold-label
contracts, no new endpoints, no new auth, no non-loopback bind, no new tier
escape hatch. The implementation honors all of those. The new advisory
warning never persists; the new prompt-version bump goes through the
existing RFC 0017 immutability machinery; the new column is nullable and is
seeded only via migration. The local-first posture is unchanged. PASS.

## Open questions

1. (F005 / F006) Should the warning text and curated-list lookup be tightened
   to reduce false-positive risk, or is the v1 advisory posture sufficient
   given that the warning never mutates state? RFC 0028 § Open Question 2
   already defers heuristic-tightening to v1.1; recommendation is to
   keep v1 as-is and revisit when the operator reports a concrete miss.
2. (F008 nit) Should `description` drift be added as a parameterized case in
   `test_phase3_schema_preflight_detects_semantic_schema_drift`? The
   production code already enforces it; this is a test-coverage symmetry
   nit. Non-blocking.
3. (Promotion path) The 100–500 segment re-extraction bench gate stipulated
   by RFC 0028 § Promotion path is explicitly *not* part of this code-change
   pass (handoff "Known Gaps And Review Targets" calls it out). This is
   correct — the bench gates re-extraction, not the prompt-version bump or
   the rendering changes. Acceptable for `accept_with_findings`.

verdict: accept_with_findings
