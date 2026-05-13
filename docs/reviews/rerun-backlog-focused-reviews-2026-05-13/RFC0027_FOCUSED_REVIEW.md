# RFC 0027 Interview Web UI Focused Review

author: operator [self-declared: focused-claude-1]

Status: review
Date: 2026-05-13
RFC refs: RFC-0027
Spec refs: spec-0027
Backlog refs: B003, B004, B005, B006, B008 (focused subset)
Decision refs: D020, D044, D069, D080, D081
Phase refs: PHASE-0003-FOLLOWON

## Scope

This re-review evaluates the focused subset of the RFC 0027 fix lane:
question-page Tier 1 ceiling, mutating-GET removal, the Origin /
Sec-Fetch-Site contract, evidence-scoped message reachability, frozen
session-target resume/completion behavior, and the migration 011/013
baseline. The prior `needs_revision` review is
`docs/reviews/rfc0027-rerun-2026-05-13/RFC_0027_INTERVIEW_WEB_UI_REVIEW_codex.md`
(findings F001–F009). Other findings from that review (F010–F012:
serve-extra docs, 422 banner UX, import-graph guard) are outside this
focused scope.

I inspected the implementation (`src/engram/interview/web.py`,
`storage.py`, `sampler.py`), spec text (`docs/specs/0027-interview-web-ui-spec.md`),
RFC text (`docs/rfcs/0027-interview-web-ui.md`), migrations 011 and 013,
the tests under `tests/test_interview_web.py`, and the operator-facing
howto. The OPERATOR_REPORT records `make test-docker` at `517 passed`
and 50 passing tests across the web/storage surface for this batch.

## Findings

### 1. Question-page Tier 1 ceiling (B003 / prior F001) — Resolved

`_render_question_template` at `src/engram/interview/web.py:483-555` now
gates *before* template render: it loads the parent target row, calls
`_target_tier` to read `claims.privacy_tier` or `beliefs.privacy_tier`,
and short-circuits with a structured 403 if `tier > 1` via
`_check_tier_1`. After `fetch_target_display` returns the excerpt list,
`_check_display_tier_1` walks every excerpt and hits the messages table
again, raising the same envelope on any tier > 1 row. The same gate
runs in `/q/{idx}/evidence/all` against the full (non-capped) excerpt
list at `web.py:1036-1041`, so the disclosure path cannot leak rows
that the capped preview hid. The reserved
`ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX` env var is documented as
unimplemented (`web.py:108-114`); v1 hard-codes ceiling = 1.

Test coverage at `tests/test_interview_web.py:382-392` (question page)
and `tests/test_interview_web.py:900-976` (evidence-all preview-limit
bypass) verifies tier-2 rejection on both paths, including a row that
sits past `EVIDENCE_ROWS_SHOWN`. The previous "Tier 2 leaks before the
guarded routes" path is closed.

### 2. Mutating GET removal and final-question completion (B004 / prior F002) — Resolved

The verdict POST handler at `web.py:842-871` calls
`mark_session_completed(conn, session_id)` inside the same
`record_verdict` transaction when `idx >= n_targets`, then commits and
returns `HX-Redirect: /` with no intermediate route. `POST /complete`
remains at `web.py:1073-1083` as a guarded, Origin-checked form path,
but the final-question flow never depends on it. There is no
`@app.get("/sessions/{id}/complete")` route; the regression test at
`tests/test_interview_web.py:705-715` does a direct `client.get` on
`/complete` and asserts 405 plus `completed_at IS NULL`. The spec text
at `docs/specs/0027-interview-web-ui-spec.md:488-495` now explicitly
states that "the final verdict handler no longer redirects to a
mutating GET or auto-fires this route."

### 3. Origin / Sec-Fetch-Site contract (B004 / prior F003) — Resolved

`_origin_check` (`web.py:187-233`) now enforces, on every mutating
route, all of:

- `Origin` header is present (missing → 403, no longer treated as a
  TestClient/curl concession);
- the URL parses cleanly;
- `scheme == "http"` (no silent https acceptance);
- `hostname` is in the resolved `ALLOWED_ORIGIN_HOSTS` set
  (loopback default plus the comma-separated
  `ENGRAM_INTERVIEW_ALLOWED_ORIGINS` extension per D081);
- the `Origin` port equals the *bound* port derived from the request
  Host header (`_request_host_port`), closing the "any port for
  allowlisted host" gap from the prior implementation;
- the Origin path is empty or `/`;
- `Sec-Fetch-Site: same-origin` is present.

Tests pin every failure mode: cross-host
(`test_post_verdict_403_origin_mismatch`), missing header
(`test_post_verdict_requires_origin_header`), missing Sec-Fetch-Site
(`test_post_verdict_requires_same_origin_sec_fetch`), allowlisted host
on the wrong port (`test_post_verdict_rejects_allowed_host_on_wrong_port`).
The D081 env-var extension is covered by
`test_allowed_origin_hosts_env_var_extends_default` and the
loopback-only default is pinned by
`test_allowed_origin_hosts_default_is_loopback_only`. Spec § Origin
allowlist behavior (`spec:504-521`) matches the implementation.

The dependency-based wiring (`_ORIGIN_CHECK_DEPENDENCY`, attached only
to POST routes) keeps GETs free of the check, consistent with the spec
guidance.

### 4. Evidence-scoped reachability (B005 / prior F004) — Resolved

`_session_can_reach_evidence_message` (`web.py:593-627`) joins through
`gold_label_session_targets` to either `claims.evidence_message_ids`
(for claim targets) or `beliefs.evidence_ids` (for belief targets) and
asks whether the requested `message_id` is in either array. Both
columns are real `UUID[]` columns on the parent tables (verified in
`migrations/006_claims_beliefs.sql:154,216`). `_check_message_reachable`
raises a 404 when neither match holds, and both `/messages/{id}` and
`/messages/{id}/context` call it before any tier check.

Test coverage at `tests/test_interview_web.py:803-878` exercises two
distinct scoping failures: a tier-1 message from a different
conversation, and a tier-1 message from the *same* conversation that
was not cited by the claim's evidence array. Both return 404 on
`/messages/{id}` and `/messages/{id}/context`. The
conversation-wide-reach regression from the prior review is closed.

### 5. Frozen target version triple resume and completion (B006 / prior F006, F009) — Resolved with one minor residual

The version-triple match is now complete on both surfaces:

- CLI: `run_phase3_interview_resume` reads via
  `unanswered_session_targets` (`src/engram/cli.py:2066`), which in
  `src/engram/interview/storage.py:564-619` joins
  `gold_label_session_targets` ↔ `gold_labels` on `session_id`,
  `target_kind`, `target_id`, `request_profile_version`, and the
  `COALESCE`-normalized extraction *and* consolidation pairs. A label
  under a different extraction or consolidation version no longer
  counts the materialized target as answered. The same helper raises
  `GoldLabelStorageError("session has no materialized targets; cannot
  infer completion")` when an open session has zero materialized rows
  — i.e., the F009 pre-011 silent-completion path is closed at the
  CLI surface.
- Web: `GET /sessions/{id}` (`web.py:737-774`) uses the same join shape
  inline. `test_get_session_resume_uses_frozen_version_triple` pins
  the behavior with a deliberately mismatched `extraction_model_version`
  on the existing label — the resume route still redirects to
  `/q/1`, not `/`.

**Minor residual (not blocking):** the web `GET /sessions/{id}` route
runs its own raw-SQL variant of the unanswered-target query rather
than calling `unanswered_session_targets`. The query is structurally
equivalent for the answered-vs-unanswered check, but it does not
distinguish between (a) all materialized targets are answered (genuine
completion) and (b) zero materialized targets exist (pre-011 open
session). Both paths silently `RedirectResponse(url="/")` at
`web.py:769-770`. The web route does not *mutate* `completed_at` on a
pre-011 session, so the F009 letter-of-the-finding is satisfied. But
the operator-facing behavior diverges between CLI (explicit error) and
web (no-op redirect). Suggested follow-up: route the web resume
through `unanswered_session_targets` so the same `GoldLabelStorageError`
surfaces as a 410-or-banner, or document the divergence in the spec.
This belongs on the v1.1 list; it does not block the focused fix.

### 6. Migration 011/013 baseline (prior F008) — Resolved

`docs/specs/0027-interview-web-ui-spec.md:650-725` now embeds the
canonical baseline table shape with the active-learning/confidence
carry columns inline, and explicitly names `013_interview_active_learning_state.sql`
as part of the RFC 0027 schema baseline. The promoted RFC text at
`docs/rfcs/0027-interview-web-ui.md:259-282` matches the same baseline
statement.

`migrations/013_interview_active_learning_state.sql:27-52` adds the
three resume-carry columns, disables the append-only trigger to
backfill from `claims` and `beliefs`, then re-enables it. Storage
helpers (`storage.py:412-489` for insert,
`storage.py:514-619` for read) use the carry columns directly. The
"v1 migration 011 contract is incomplete" framing from the prior
review is no longer accurate.

### 7. D020 no-egress contract on the serve process (prior F005, in-scope for "baseline docs") — Resolved at the documentation layer

`docs/specs/0027-interview-web-ui-spec.md:826-830` now records the
contract explicitly: the web UI is a D020 corpus-reading process and
must run in the same operator-enforced no-egress runtime (network
namespace, sandbox, or deny-by-default firewall rule) as other corpus
readers; vendored htmx is *not* a substitute for the process egress
boundary. The howto's "Tailnet access" section
(`docs/howto/gold-set-interview.md:153-188`) is consistent: Engram
itself stays loopback-bound, the optional tailnet reach uses a
separate user-space TCP forwarder plus the env-var Origin-allowlist
extension. There is no in-process network call from
`engram.interview.web`, and the static asset references only
`/static/htmx.min.js`. This matches D020's "ideally enforced outside
code discipline" wording — the spec now names the dependency rather
than silently relying on it.

## Out-of-scope reminders

This review intentionally does not re-evaluate:

- F010 (serve extra missing python-multipart) — `pyproject.toml`
  already lists it; the RFC dependency snippet matches; out of focused
  scope.
- F011 (422 JSON banner vs inline banner) — UX/test contract drift,
  not a privacy/state issue.
- F012 (D044/D069 import-graph guard depth) — same.

A future re-review may take those up.

## Verdict

verdict: accept_with_findings

The focused fix lane resolves every blocker from the prior
`needs_revision` review. F001–F004 (Tier 1 ceiling, mutating GET,
Origin/Sec-Fetch, evidence reachability) and F006 (frozen version
triple) are fully closed at both the implementation and test surfaces.
F008 (migration baseline) and F005 (D020 contract) are documented in
the spec and howto. F009 is closed at the CLI surface and at the
schema layer; the web resume route has a minor operator-UX residual
(silent redirect rather than an explicit pre-011 diagnostic) that is
worth a small follow-up but is not a privacy or state-integrity
defect. The carry-forward item is documentation- or one-route-sized,
not a contract change.
