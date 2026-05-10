author: synthesizer-codex-gpt-5.5-001

# RFC 0028 Revision Synthesis

## Finding Classifications

L001: accepted. Mixed `persons or ...` hints must not be treated as
person-only because that can bias operators toward false verdicts on valid
project, organization, or household subjects.

L002: accepted. Phase 3 preflight must report missing RFC 0028 vocabulary
columns through `Phase3SchemaPreflightError`, not a raw PostgreSQL
`UndefinedColumn`.

L003: deferred. The curated substring heuristic is advisory and does not
mutate state; tighten it later only if operator feedback shows concrete false
positives.

L004: accepted. Preserving whitespace in the web summary is a small, local
template change that keeps the CLI and web hierarchy visually aligned.

L005: accepted. Adding `description` drift coverage is low-risk test symmetry
for a field already enforced by production preflight.

## Revision Tasks

1. Update `subject_kind_warning` so it only enters the non-person warning path
   for strictly person-only hints, and add tests proving mixed allowed hints
   return no warning and perform no entity lookup.

2. Update `phase3_schema_preflight` so `predicate_vocabulary.description` and
   `predicate_vocabulary.subject_kind_hint` are required columns. Ensure the
   semantic vocabulary comparison is skipped when required vocabulary columns
   are absent so the accumulated missing-column errors are raised cleanly.

3. Add a regression case that drops `predicate_vocabulary.subject_kind_hint`
   and expects an actionable `Phase3SchemaPreflightError`.

4. Preserve leading whitespace for rendered web summary lines in
   `question.html`, and add a web-rendering test that pins the CSS or markup
   hook.

5. Add a `predicate_vocabulary.description` drift case to the Phase 3 semantic
   preflight test.

6. Do not change the curated substring lookup for L003 in this pass. Record the
   deferral in the revision handoff.

7. Rerun the focused RFC 0028 test slice and `git diff --check`.
