author: ledger-codex-gpt-5.5-002

# RFC 0028 Findings Ledger

## Summary

The three-lane review completed with Gemini accepting the implementation,
Codex accepting with two major findings, and Claude accepting with non-blocking
findings. The ledger carries forward five actionable items: two major
correctness issues, one minor heuristic risk, and two nits around web
formatting and test symmetry. Informational PASS findings from Claude are not
carried forward as work items.

## Findings Table

| ID | Severity | Title | Affected files | Source reviews |
| --- | --- | --- | --- | --- |
| L001 | major | Mixed allowed subject hints warn as person-only | `src/engram/interview/render.py`, `tests/test_interview_render.py` | Codex F001; Claude F005 |
| L002 | major | Phase 3 preflight can raise raw SQL when migration 012 column is absent | `src/engram/cli.py`, `tests/test_phase3_claims_beliefs.py` | Codex F002 |
| L003 | minor | Curated non-person subject substring matching can over-trigger | `src/engram/interview/render.py` | Claude F006 |
| L004 | nit | Web summary line indentation may collapse | `src/engram/interview/templates/question.html` | Gemini F001 |
| L005 | nit | Preflight drift tests cover `subject_kind_hint` but not `description` | `tests/test_phase3_claims_beliefs.py` | Claude F008 |

## L001: Mixed Allowed Subject Hints Warn As Person-Only

Severity: major

Source reviews: Codex F001; Claude F005

Rationale: The warning helper gates on substring membership in the
`subject_kind_hint`, so hints such as `persons or projects`,
`persons or organizations`, and `persons or households` enter the warning path
even though those predicates explicitly allow non-person subjects. This can
show "Likely a `false` extraction" for valid claims and can bias operator
verdicts against D082's intent.

Recommended action: Restrict the warning trigger to strictly person-only hints
and add regression coverage proving mixed allowed hints do not query entity
kinds or emit warnings.

## L002: Phase 3 Preflight Can Raise Raw SQL When Migration 012 Column Is Absent

Severity: major

Source reviews: Codex F002

Rationale: The semantic vocabulary parity check selects `description` and
`subject_kind_hint`, but the required-column list omitted those columns. A
database migrated only through 011 can therefore raise `UndefinedColumn` from
PostgreSQL instead of the intended `Phase3SchemaPreflightError` with an
actionable missing-column message.

Recommended action: Include both vocabulary intent columns in the Phase 3
required-column check, and skip semantic vocabulary SELECTs when any required
vocabulary column is absent because the missing-column errors already explain
the problem. Add regression coverage for dropping `subject_kind_hint`.

## L003: Curated Non-Person Subject Substring Matching Can Over-Trigger

Severity: minor

Source reviews: Claude F006

Rationale: `_known_non_person_subject_label` first checks exact normalized
subject text but then falls back to substring matching for curated labels such
as `alameda`, `encinal`, and `hobnob`. That can warn for a person or unrelated
entity whose name merely contains one of those tokens. The warning is advisory
and does not mutate state, so this is not a blocking correctness issue.

Recommended action: Defer unless operator feedback reports concrete false
positives, or tighten the curated lookup to whole-string or whole-token
matching in a follow-up.

## L004: Web Summary Line Indentation May Collapse

Severity: nit

Source reviews: Gemini F001

Rationale: `format_summary_line` intentionally prefixes intent and warning
lines with two spaces for CLI hierarchy. The web template renders each line in
a `<div>`, where leading whitespace can be collapsed by normal browser layout.

Recommended action: Preserve summary-line whitespace in the web CSS or accept
the minor visual difference if the product does not require CLI-style indenting
in the web surface.

## L005: Preflight Drift Tests Cover `subject_kind_hint` But Not `description`

Severity: nit

Source reviews: Claude F008

Rationale: Production preflight compares both `description` and
`subject_kind_hint`, while the drift regression only mutates
`subject_kind_hint`. The parity path already covers both fields, so this is
test symmetry rather than an implementation gap.

Recommended action: Add a parameterized drift case for a changed
`predicate_vocabulary.description`.

## Items Intentionally Not Carried Forward

Claude F001, F002, F003, F004, F007, F009, and F010 were informational PASS
findings confirming migration safety, runtime vocabulary parity, prompt
versioning, prompt shape, CLI/web prompt sharing, docs updates, and local-first
invariants. They do not require revision tasks.

Gemini had no findings beyond L004.
