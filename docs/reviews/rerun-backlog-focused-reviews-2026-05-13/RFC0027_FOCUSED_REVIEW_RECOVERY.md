# RFC 0027 Web Privacy And Session-State Focused Review Recovery

author: operator [self-declared: recovery-codex-rfc0027]

Status: review
Date: 2026-05-13
RFC refs: RFC-0027, RFC-0021
Backlog refs: B003, B004, B005, B006, B011
Decision refs: D020, D044, D069, D080, D081
Phase refs: PHASE-0003-FOLLOWON

## Scope

This is the recovery review for the RFC 0027 focused web/privacy/session-state
lane after the original Claude lane exited without publishing an artifact. I
reviewed only the assigned RFC 0027 backlog fixes: Tier ceilings, mutating GET
removal, Origin / Sec-Fetch behavior, evidence-scoped reachability, frozen
target resume/completion behavior, and baseline documentation truthfulness.

## Findings

### F001 - `evidence/all` bypasses the parent-target Tier 1 ceiling

Severity: major

Source: `src/engram/interview/web.py:500-509`;
`src/engram/interview/web.py:1035-1041`;
`docs/rfcs/0027-interview-web-ui.md:310-319`;
`docs/specs/0027-interview-web-ui-spec.md:397-398`;
`docs/specs/0027-interview-web-ui-spec.md:468-473`;
`tests/test_interview_web.py:900-976`

Rationale: The normal question renderer reconstructs the frozen target, checks
the parent claim/belief tier with `_target_tier()`, then checks the rendered
evidence-message tiers before rendering. The direct show-all route reconstructs
the same target but only checks the tiers of the evidence rows returned by
`fetch_target_display()`. A Tier 2 target with Tier 1 cited messages therefore
403s on `/sessions/{id}/q/{idx}` but can still render evidence through
`/sessions/{id}/q/{idx}/evidence/all`.

The RFC/spec contract says the question page and evidence-all route enforce the
same hard Tier 1 ceiling before any evidence excerpt renders. Current tests
cover Tier 2 evidence rows and rows beyond the preview limit, but not the
parent-target Tier 2 / evidence-row Tier 1 case.

Proposed fix: make `get_evidence_all()` call the same parent-tier guard as
`_render_question_template()` before fetching/rendering evidence, and add a
regression with a Tier 2 claim or belief target whose cited message rows remain
Tier 1.

### F002 - Completed or abandoned sessions can still be resumed and mutated

Severity: major

Source: `src/engram/interview/web.py:737-774`;
`src/engram/interview/web.py:777-802`;
`src/engram/interview/web.py:805-871`;
`src/engram/interview/web.py:1072-1096`;
`src/engram/interview/agent.py:77-122`;
`tests/test_interview_web.py:1001-1015`

Rationale: `/complete` and `/abandon` set `gold_label_sessions.completed_at`,
but the resume route, question route, and verdict POST only check that the
session row exists and that materialized targets exist. They do not reject a
closed session. Because `InterviewAgent.record_verdict()` also does not check
session state, a direct URL or POST can append new labels after a session has
been completed or abandoned.

This matters for the recovery scope because B006 is about preserving frozen
session state. Once the web UI marks a session complete or abandoned, that
state should be a terminal UI boundary unless a separate explicit reopen
operation exists. The current tests only assert that abandon stamps
`completed_at` and `operator_note`; they do not assert that closed sessions stop
rendering questions or accepting verdicts.

Proposed fix: have web resume, question rendering, verdict commit, and
form-driven completion/abandon paths load session state and reject
`completed_at IS NOT NULL` where mutation or continued answering would occur.
Add tests for direct GET `/q/{idx}` and POST `/verdict` after `/abandon` and
after `/complete`.

### F003 - Final completion is based on URL position, not remaining frozen targets

Severity: major

Source: `src/engram/interview/web.py:819-850`;
`src/engram/interview/web.py:744-764`;
`src/engram/interview/storage.py:564-619`;
`tests/test_interview_web.py:677-702`

Rationale: The verdict POST marks the session complete whenever `idx >=
n_targets`. The route is directly addressable, so posting a verdict for the
last URL index before answering earlier materialized targets closes the session
with unanswered rows still present. Resume/storage now have the right
full-target/version-triple predicate for unanswered targets; completion should
derive from that predicate after the label write rather than from the URL index
the operator happened to post.

The existing final-completion test only covers the sequential q1 then q2 path,
so it does not catch out-of-order direct posts or stale browser tabs.

Proposed fix: after `record_verdict()` succeeds, compute whether any
materialized target remains unanswered using the same frozen target/version
predicate as resume. Mark complete only when that set is empty. Add a
regression that posts the last question first and verifies the session remains
open with the earlier target still resumable.

### F004 - Web progress counts ignore the frozen target/version predicate

Severity: medium

Source: `src/engram/interview/web.py:279-319`;
`src/engram/interview/web.py:436-441`;
`src/engram/interview/web.py:744-764`;
`tests/test_interview_web.py:263-311`

Rationale: Web resume now correctly ignores labels whose target/version triple
does not match the materialized session target. The open-session list and
question-page status line still count all `gold_labels` rows by `session_id`.
That can count duplicate labels, labels inserted outside the materialized
target set, or historical/mismatched-version labels that resume correctly
ignores. The UI can therefore display `K/N answered` values that disagree with
the actual next target and with the frozen target contract.

This is not the old blocker where resume itself skipped the wrong target; that
query is fixed. The remaining issue is status truthfulness under the same
state model.

Proposed fix: compute `n_answered` as the count of materialized targets with a
matching label under the same predicate used by `GET /sessions/{id}`. Extend
the frozen-version regression so the mismatched label does not increment index
or question status counts.

### F005 - Targetless open sessions are still stranded in the web path

Severity: medium

Source: `src/engram/interview/web.py:279-319`;
`src/engram/interview/web.py:744-770`;
`src/engram/interview/storage.py:596-618`;
`tests/test_interview_storage.py:559-568`

Rationale: Storage now rejects an open session with zero materialized targets
as non-inferrable, which is the right recovery from the pre-011 case. The web
path bypasses that guard. The index lists every `completed_at IS NULL` session,
including `0/0` targetless rows, and clicking such a session makes the resume
route silently redirect to `/` because `MIN(idx)` is null.

That avoids silently marking the row complete, but it still leaves the operator
with a stranded open session and no explanation. B006 asked that pre-011
sessions without materialized targets not be silently completed; the web UI
should also not silently bounce them.

Proposed fix: make web resume use `unanswered_session_targets()` or an
equivalent targetless-open guard, then render a clear diagnostic or require an
explicit abandon. Add a web regression for an open session row with no
`gold_label_session_targets`.

## Resolved Checks

- B003 is mostly resolved on the normal question path: `/q/{idx}` now checks
  both parent target tier and rendered evidence-message tiers before rendering.
  F001 is the remaining direct-route bypass.
- B004 mutating GET removal is resolved. Final verdict completion now happens
  inside the guarded verdict POST, and `GET /sessions/{id}/complete` is not
  registered.
- B004 Origin / Sec-Fetch behavior is resolved in code for the reviewed
  contract. `_origin_check()` requires a present `Origin`, exact allowed
  host/port, and `Sec-Fetch-Site: same-origin`; every POST route attaches the
  shared dependency. Residual test risk: negative tests are concentrated on
  the verdict POST path, while `/sessions`, `/save-and-quit`, `/complete`, and
  `/abandon` rely on the shared dependency.
- B005 evidence-scoped reachability is resolved for full-message and context
  routes. The anchor message must be one of the claim/belief evidence IDs for a
  materialized session target, and same-conversation non-evidence access is
  tested.
- The baseline docs now truthfully include migration 013 carry fields,
  `python-multipart`, and D020 no-egress wording. The no-egress boundary is
  still operator-enforced outside the Python process, which matches the revised
  spec language.

## Verification

No network access was used. I ran the focused pytest target from the local
virtualenv:

```sh
.venv/bin/pytest tests/test_interview_web.py tests/test_interview_storage.py
```

Result: `3 passed, 47 skipped in 0.31s`. The database-backed tests skipped
because `ENGRAM_TEST_DATABASE_URL` is not set in this environment, so the
review is primarily static inspection plus the non-DB test coverage that did
run.

verdict: needs_revision
