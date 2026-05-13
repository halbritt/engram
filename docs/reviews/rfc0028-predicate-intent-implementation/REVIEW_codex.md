# RFC 0028 Predicate Intent Implementation Review — codex
author: reviewer-codex-gpt-5.5-002

Status: review
Date: 2026-05-09
RFC refs: RFC-0028
Decision refs: D-082
Phase refs: PHASE-0003, PHASE-0003-FOLLOWON

## Findings

### F001 — subject_kind_warning treats mixed allowed hints as person-only
Severity: major
Source: src/engram/interview/render.py:255; src/engram/interview/render.py:265; src/engram/extractor.py:117
Rationale: The warning heuristic gates on substring membership, so any hint containing `person` enters the person-only warning path. That includes advisory hints that explicitly allow non-person subjects, such as `uses_tool` with `persons or projects`, `works_with` with `persons or organizations`, and `owns_repo` with `persons or organizations`. Once in that path, an active entity kind of `project` or `organization` is formatted as a mismatch warning and shown as "Likely a `false` extraction", even though the predicate hint allows that subject kind. This can bias both CLI and web operators toward false verdicts on valid claims, which directly undercuts D-082's purpose. The current tests cover `projects only` being skipped but do not cover mixed hints where the non-person kind is allowed.

### F002 — Phase 3 preflight does not fail cleanly when migration 012 is missing
Severity: major
Source: src/engram/cli.py:974; src/engram/cli.py:1044
Rationale: `phase3_schema_preflight` added semantic parity checks for `predicate_vocabulary.subject_kind_hint`, but the required-column list still omits both `description` and `subject_kind_hint`. `_check_phase3_predicate_vocabulary` then unconditionally selects `subject_kind_hint`; on a database migrated through 011, this raises a raw database `UndefinedColumn` instead of the intended `Phase3SchemaPreflightError` with an actionable schema message. The migration integrity check only confirms `006_claims_beliefs.sql` is recorded, so a missing `012_predicate_subject_kind_hint.sql` record is not caught before that select. This is a preflight coverage gap for exactly the DB/runtime vocabulary parity this implementation is trying to enforce.

## Open questions

None.

verdict: accept_with_findings
