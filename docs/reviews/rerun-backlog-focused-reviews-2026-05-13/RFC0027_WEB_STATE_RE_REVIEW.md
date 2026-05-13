# RFC 0027 Web Privacy And Session-State Focused Re-Review

author: operator [self-declared: rfc0027-web-state-rereview]

Status: review
Date: 2026-05-13
RFC refs: RFC-0027

## Scope

This is the re-review of the RFC 0027 focused web/privacy/session-state repairs following the recovery review. The scope is limited to confirming the resolution of the five specific findings (F001-F005) related to Tier ceilings, completed session mutations, completion indexing, progress counts, and targetless open session behavior.

## Findings

### F001 - `evidence/all` bypasses the parent-target Tier 1 ceiling

Status: Resolved
Rationale: `get_evidence_all` in `src/engram/interview/web.py` now reconstructs the parent tier and enforces the Tier 1 ceiling via `_check_tier_1(_target_tier(conn, sampled))` prior to fetching or rendering evidence rows. A regression test `test_get_evidence_all_enforces_parent_target_tier` was added.

### F002 - Completed or abandoned sessions can still be resumed and mutated

Status: Resolved
Rationale: The `_require_open_session` and `_require_open_session_for_label` functions are now rigorously applied across all web endpoints that render questions, resume, post verdicts, or execute completion/abandon actions. This prevents any further interaction with sessions where `completed_at IS NOT NULL`. Regression tests for completed and abandoned rejections were added.

### F003 - Final completion is based on URL position, not remaining frozen targets

Status: Resolved
Rationale: Final completion inside the `post_verdict` route is now governed by checking for remaining unanswered materialized targets via `_unanswered_table_indices`, matching the frozen target predicate, rather than depending on URL index order. A regression test verifying out-of-order posting does not prematurely close the session was added.

### F004 - Web progress counts ignore the frozen target/version predicate

Status: Resolved
Rationale: The web progress logic now relies on `_n_answered`, which employs the same strict target/version predicate as the session target reconstruction queries.

### F005 - Targetless open sessions are still stranded in the web path

Status: Resolved
Rationale: The `unanswered_session_targets` function in `src/engram/interview/storage.py` now explicitly returns a `GoldLabelStorageError` for open sessions with zero targets. The `get_session` web route catches this and raises a `409` HTTP exception requiring an explicit abandon.

## Verification

The fixes for F001-F005 are confirmed correct.

Tested locally with: `.venv/bin/pytest tests/test_interview_web.py tests/test_interview_storage.py`

verdict: accepted