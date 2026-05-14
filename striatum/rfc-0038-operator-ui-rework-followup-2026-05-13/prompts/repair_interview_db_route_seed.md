You are the RFC 0038 follow-up implementer for the DB-backed interview route
evidence blocker.

Read the required context and `REPAIR_EVIDENCE.md`. Resolve the remaining
failure:

`tests/test_interview_web.py::test_question_renders_predicate_intent_and_warning`

The evidence reports a PostgreSQL trigger rejection:

`claim stability_class does not match predicate vocabulary`

Stay inside your write scope. Diagnose whether the blocker is invalid test
fixture data, an interview route test helper issue, or a narrow interview
surface bug. Do not weaken database predicate/stability validation, do not edit
migrations, and do not touch bench-review or shared UI files. Preserve local
only/no-network behavior.

Use maximal useful internal sub-agents if your environment supports them, with
disjoint ownership inside the assigned write scope.

Run focused tests that prove the blocker is resolved, including the DB-backed
route test when `ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test` is
available. Publish the required handoff artifact with the root cause, changed
files, exact commands, and remaining risks.
