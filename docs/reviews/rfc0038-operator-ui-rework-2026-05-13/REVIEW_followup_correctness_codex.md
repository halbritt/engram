author: operator [self-declared: rfc0038-followup-correctness-review]

# RFC 0038 Follow-up Correctness Review

Date: 2026-05-13
Lane: review_followup_correctness_codex
Verdict: needs_revision

## Scope

Fresh document-only follow-up review of whether the RFC 0038 correctness
blockers are resolved, with special attention to the DB-backed interview route
evidence. I read only the listed packet inputs. I did not inspect implementation
files and did not run tests.

## Findings

### FC001 - Blocking - DB-backed interview route evidence is still failing

Affected evidence / contract:

- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_EVIDENCE.md:12`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_EVIDENCE.md:16`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_EVIDENCE.md:19`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_EVIDENCE.md:53`
- `ENGRAM_UI_REWORK_HANDOFF.md:949`
- `docs/rfcs/0038-operator-ui-rework.md:101`

The follow-up repair evidence explicitly records `Result: fail`. The focused
real-DB command with
`ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test` fails with `1 failed, 72
passed`; the failing case is
`tests/test_interview_web.py::test_question_renders_predicate_intent_and_warning`.
That test is a named RFC 0038 acceptance check for rendering predicate intent
and the subject-kind warning on the interview question route. The evidence says
the route never reaches the render assertion because inserting the test's
`has_name` claim is rejected by the database trigger:

```text
psycopg.errors.CheckViolation: claim stability_class does not match predicate vocabulary
```

This means the route/template acceptance evidence is not green. Skipped-DB
passes and non-DB template/static checks cannot close this blocker because the
contract requires the real route suite to pass, and the failing test is exactly
one of the handoff's required interview route checks.

Minimal fix:

Repair the fixture or route setup so the DB-backed predicate-intent warning
case uses a predicate/stability combination accepted by the schema, then rerun
the focused real-DB command with `ENGRAM_TEST_DATABASE_URL` set and no skipped
DB route cases. Capture passing evidence before treating RFC 0038 correctness
as repaired.

### FC002 - Major - route-suite dependency evidence still depends on a user-site workaround

Affected evidence / prior blocker:

- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_correctness_codex.md:42`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_EVIDENCE.md:36`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_EVIDENCE.md:67`
- `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_EVIDENCE.md:90`

The original C002 blocker was that checked-in route tests could not collect in
the declared dev environment because `httpx` was missing. Repair evidence says
`pyproject.toml` now declares `httpx>=0.27,<0.29`, which addresses the
dependency-declaration side. But the active venv still lacks `httpx`, and the
route-test commands only collect when the pre-existing user-site package path is
added through `PYTHONPATH`.

This is not the main remaining blocker once FC001 exists, but it is still an
evidence gap: the provided documents do not show the route suite collecting and
running in a refreshed declared dev/test environment without the user-site
workaround.

Minimal fix:

Refresh the local environment from the updated dev extra or otherwise document
an offline/local install path, then rerun the focused route suite without
`PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages`.

## Prior Correctness Finding Status

| Prior finding | Follow-up status from supplied documents |
|---------------|-------------------------------------------|
| C001 bench app cannot start | Appears repaired. `create_app(...)` smoke passed and focused bench route tests are reported passing in the repair evidence. |
| C002 route tests cannot collect | Partially repaired. Dependency declaration is reportedly fixed, but active evidence still uses a user-site `httpx` workaround. |
| C003 shared substrate not integrated | Not closable from this follow-up packet. The repair evidence proves shared resources, template parsing, and no-CDN/static checks, but does not provide route-level evidence that interview and bench render through the shared shell/future-slot/audit-footer output. |
| C004 bench origin guard fails open | Not closable from this follow-up packet. The repair evidence does not name missing-Origin / missing-`Sec-Fetch-Site` coverage or a shared-origin-helper route assertion. |
| C005 formatting checks fail | Appears repaired. Focused Ruff check and format check both pass in the repair evidence. |

## Verdict

`needs_revision`.

The main correctness blockers are not fully resolved because the follow-up
DB-backed route evidence remains red. The next review should receive a fresh
repair-evidence artifact showing the real DB-backed interview and bench route
suite passing without skipped DB cases, plus a no-workaround route-test
collection run for the refreshed dev environment.
