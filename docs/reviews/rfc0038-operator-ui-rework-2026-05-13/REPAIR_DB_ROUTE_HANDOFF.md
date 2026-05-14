author: operator [self-declared: rfc0038-followup-db-route-repair]

# RFC 0038 DB-Backed Interview Route Repair Handoff

Date: 2026-05-13
Lane: `codex_interview`
Job: `repair_interview_db_route_seed`

## Summary

Resolved the remaining DB-backed interview route evidence blocker without
changing migrations, predicate vocabulary constraints, route behavior, or
interview rendering code.

The failure was invalid test fixture data. `tests/test_interview_web.py` seeded
a `has_name` claim through the real database path, but its local helper let
`insert_extracted_claim()` fall back to the helper's default unknown-predicate
stability class of `preference`. PostgreSQL correctly rejected that insert
because `predicate_vocabulary.has_name` requires `stability_class='identity'`.

## Root Cause

- The production database trigger `fn_claims_insert_prepare_validate()` was
  working as intended.
- The test's generic claim seed helper had drifted from the canonical
  `predicate_vocabulary` table.
- The materialized session-target helper also hard-coded `preference`, which
  made the frozen target metadata inconsistent for non-preference predicates.

## Files Changed

- `tests/test_interview_web.py`
  - Added `_stability_class_for_predicate()` to read the canonical stability
    class from `predicate_vocabulary` for seeded route-test claims.
  - Passed that canonical value into `insert_extracted_claim()` so real DB
    predicate/stability validation remains active.
  - Materialized `gold_label_session_targets.stability_class` from the parent
    claim row instead of hard-coding `preference`.

## Commands Run

| Command | Result |
|---------|--------|
| `striatum ack --session-id sess_8dc6ed47a7aa4466b57835ea3c42784c --message-id msg_808fe9e0e27347179161184103b4bd66 --lease-id lease_15e6d5d702dc42a086684f726ff1394d` | Pass. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py::test_question_renders_predicate_intent_and_warning` | Initially failed with `claim stability_class does not match predicate vocabulary`; after repair, pass: `1 passed in 1.70s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py` | Pass: `49 passed in 50.53s`. |
| `PYTHONPATH=/home/halbritt/.local/lib/python3.12/site-packages ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test .venv/bin/python -m pytest -p no:cacheprovider -q tests/test_interview_web.py tests/test_bench_review.py` | Pass: `73 passed in 49.65s`. |
| `.venv/bin/python -m ruff check tests/test_interview_web.py` | Pass: `All checks passed!`. |
| `.venv/bin/python -m ruff format --check tests/test_interview_web.py` | Pass: `1 file already formatted`. |
| `git diff --check -- tests/test_interview_web.py` | Pass. |

## Remaining Risks

- The active venv still appears to need the same local user-site `httpx`
  workaround recorded in `REPAIR_EVIDENCE.md`; no dependency install was
  attempted because the packet forbids network use.
- `CHANGELOG.md` was read but not edited because this job's write scope
  forbids it.
