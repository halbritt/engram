# RFC 0027 Interview Web UI Review — claude

author: operator [self-declared: rfc0027-review-claude]

Status: review
Date: 2026-05-13
RFC refs: RFC-0027 (under review); RFC-0021 (upstream); RFC-0022 (server-binary precedent for D020); RFC-0012 (Python coding standard); RFC-0017 (prompt-template versioning)
Decision refs: D016, D020, D044, D052, D069, D074, D079, D080
Phase refs: PHASE-0003-FOLLOWON

Scope: this rerun review reads only RFC 0027 (`docs/rfcs/0027-interview-web-ui.md`)
and grounds findings in the canonical inputs listed in the work packet
(RFC 0021, RFC 0022, `src/engram/cli.py`, `src/engram/interview/{render,
sampler, agent, storage, web}.py`, `migrations/010_gold_labels.sql`,
`migrations/011_gold_label_session_targets.sql`, the three v1 templates,
and `tests/test_interview_web.py`). Earlier RFC-0027 review artifacts are
quarantined per RFC 0032 and are not treated as authoritative.

## Findings

### F001 — Origin allowlist has an undocumented env-var escape clause
Severity: major
Source: `src/engram/interview/web.py:66-101` vs `docs/rfcs/0027-interview-web-ui.md:283-302`
Rationale: the RFC's "Privacy posture" section sets two non-negotiables —
"Loopback-only, no escape clause" for the bind host, and a fixed
"`Origin` allowlist (`http://127.0.0.1:<port>` and `http://localhost:<port>`)"
for mutating routes. The implementation reads
`ENGRAM_INTERVIEW_ALLOWED_ORIGINS` at module load and appends the
comma-separated hosts to the loopback allowlist
(`web.py:66-101`, annotated "extended per D081"). That changes a
load-bearing CSRF surface — an operator running a TCP bridge or tailnet
proxy can quietly accept POSTs from a tailnet hostname — without any
mention in the RFC. Either the RFC needs to be updated to enumerate
`ENGRAM_INTERVIEW_ALLOWED_ORIGINS`, its `ENGRAM_*` env-var-policy
acknowledgement, and the threat-model implications (operator opt-in vs.
quiet escape), or the env var should be reverted out of the v1 scope so
the RFC's "no escape clause" claim is actually true. Because the RFC was
promoted on a strict-loopback posture, an undocumented widening of the
trust boundary is a major correctness/provenance concern.

### F002 — `unsure` rationale-required is silently inconsistent with the CLI
Severity: major
Source: `src/engram/interview/render.py:35-43`; `src/engram/interview/web.py:134-136, 813-821`; `docs/rfcs/0027-interview-web-ui.md:181-183`
Rationale: the shared `RATIONALE_PROMPT_BY_VERDICT` in `render.py:35-43`
makes `unsure` an *optional* rationale ("note (Enter to skip) > "), and
the CLI honours that — `_prompt_rationale` calls `rationale_prompt_for`
and returns `None` when the operator hits Enter. The web layer puts
`unsure` inside `_RATIONALE_REQUIRED_VERDICTS` (`web.py:134-136`) and
returns 422 `rationale_required` on a blank submission
(`web.py:813-821`; covered by `test_post_verdict_blank_rationale_rejected_server_side`).
The RFC's route table only says the rationale textarea is "auto-shown
only on `false` / `stale` / `unsupported` / `unsure`"; it does not say
which of those four require a non-empty rationale. The result is a
CLI/web parity gap on a verdict the operator is most likely to leave
blank, and the RFC underspecifies the rule that the implementation
enforced. Either pin the contract in the RFC (CLI parity: only the four
`false / stale / unsupported` are required; `unsure` accepts empty) or
state that `unsure` is required and document the CLI deviation.

### F003 — Empty-corpus path: RFC says "do NOT create the session"; impl creates and immediately closes
Severity: minor
Source: `docs/rfcs/0027-interview-web-ui.md:180`; `src/engram/interview/web.py:687-722`
Rationale: the RFC's `POST /sessions` row reads "if sampler returns
`[]`, do NOT create the session — re-render `index.html` with the
empty-corpus diagnostic banner." The scaffolded implementation calls
`insert_session` *before* sampling, then on `sampled == []` calls
`mark_session_completed` and commits. This leaves a stub
`gold_label_sessions` row with `completed_at = now()` and zero targets,
which is observable from `list_sessions(state="completed")` and from
any operator inspection. Either rewrite the RFC line so the
implementation's "session row exists but is immediately closed"
behaviour is the documented contract (cleanly resumable / auditable),
or change the implementation to defer the insert until after sampling
succeeds. The current diverged state has bitten reviewers before; the
RFC should not silently disagree with the code it promoted.

### F004 — Error rerender returns a full HTML page into an htmx `outerHTML` swap of `#main`
Severity: minor
Source: `src/engram/interview/templates/question.html:59-104`; `src/engram/interview/web.py:826-845`
Rationale: the verdict form swaps `#main` with `outerHTML`. On a
trigger rejection, the route returns `_render_question_template(...)`,
which calls `TemplateResponse("question.html", ...)` — i.e. a full page
that extends `base.html`. htmx will then replace `#main` with a payload
that itself contains `<html><head>...</body>` chrome, producing nested
document fragments in the live DOM. The RFC's "Error handling" section
says "the route catches, rolls back, and renders the same question with
an error banner" without specifying whether the response is a full
page or an htmx fragment. Two reasonable fixes: (a) render only the
`#main` block (e.g. a `_question_main.html` partial) on the error path,
or (b) document a full-page reload semantics by clearing the htmx swap
on error (`HX-Retarget: body` / `HX-Reswap: outerHTML`). Either way the
RFC should pin the contract so the swap behaviour is not an accident.

### F005 — Resume "next unanswered idx" query ignores the version triple and target_kind
Severity: minor
Source: `src/engram/interview/web.py:737-755` vs `src/engram/interview/storage.py:478-510`
Rationale: `GET /sessions/{id}` resolves "next unanswered idx" with a
LEFT JOIN that matches only on `session_id` and `target_id::text`. The
canonical helper `unanswered_session_targets` (used by the CLI) matches
on session_id, target_kind, target_id, *and* the full version triple
— that is the level of identity the spec stamps onto
`gold_label_session_targets` at session creation. Two consequences: (1)
the resume route can skip a target if a stray prior `gold_labels` row
exists for the same `target_id` under a different version triple
(re-extraction landed mid-session); (2) it can also resume to the wrong
target if the same UUID exists in `claims` and `beliefs` (PK spaces are
independent). The RFC's `GET /sessions/{session_id}` row says
"redirect to current target's `q/{idx}` if any unanswered remain";
it does not specify the identity by which "unanswered" is decided.
Pin the rule (full version triple + target_kind, per
`unanswered_session_targets`) in the RFC and align the route.

### F006 — Origin check accepts requests with no `Origin` header
Severity: minor
Source: `src/engram/interview/web.py:193-217`
Rationale: the RFC commits to enforcing an `Origin` allowlist plus
`Sec-Fetch-Site: same-origin` on every mutating route. The
implementation explicitly waives the check when no `Origin` header is
present "so curl / TestClient flows are not gratuitously broken"
(`web.py:193-217`). Browsers do attach `Origin` to cross-origin POSTs,
so the practical CSRF posture survives — but a local non-browser
attacker (any process the operator runs) can POST without `Origin` and
skip the allowlist entirely. The RFC's threat-model paragraph already
says "Origin-header allowlist on POST routes" because "any tab on the
local machine can drive forms at `127.0.0.1:<port>`". The same single-
host threat model says non-browser local processes are also untrusted-
adjacent. Either tighten the RFC's wording to acknowledge the explicit
no-header bypass (and the test-only justification), or require an
`Origin` header on every mutating route and provide TestClient flows
that supply it (the existing tests already do).

### F007 — Save-and-quit reflects an unsanitized banner string in `/?banner=...`
Severity: nit
Source: `src/engram/interview/web.py:1040-1054`; `src/engram/interview/templates/index.html:19-23`
Rationale: `POST /sessions/{id}/save-and-quit` builds a redirect to
`/?banner=<text containing session_id>` and the index page renders
`save_and_quit_banner` verbatim. Jinja2 autoescape neutralises HTML
injection, so this is not XSS. But it does mean *any* incoming
`GET /?banner=<arbitrary text>` reflects directly onto the index page
— a phishing primitive on a localhost-only surface is low-impact but
trivially avoidable. The RFC's Save-and-quit row should pin a
session-id-keyed banner-flash mechanism (e.g. a cookie or a database
field on `gold_label_sessions`) rather than an unsanitized query
string. Cheap to fix; worth pinning in the RFC.

### F008 — CSRF tokens deferred to v1.1 "conditional on enforcement test landing" — the test exists, the deferral wording is now stale
Severity: nit
Source: `docs/rfcs/0027-interview-web-ui.md:298-302`; `tests/test_interview_web.py:512-561`
Rationale: the privacy-posture text says "Per-form CSRF tokens are
deferred to v1.1 (the deferral is conditional on an enforcement test
landing in v1; rationale at `docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_FINDINGS_LEDGER.md` F006)."
The test (`test_post_verdict_403_origin_mismatch`) and the env-var
extension test (`test_allowed_origin_hosts_env_var_extends_default`)
both exist. The cross-reference to
`docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_FINDINGS_LEDGER.md`
is to a quarantined artifact (per RFC 0032). Either inline the F006
rationale verbatim in the RFC or re-anchor the citation to a non-
quarantined source. The rerun review process exists precisely so a
promoted RFC does not survive on dangling references to quarantined
ledgers.

### F009 — Render extraction is real, but `VERDICT_PROMPT` is dead-coded in `render.py`
Severity: nit
Source: `src/engram/interview/render.py:23-31` vs `src/engram/cli.py:67-71, 1917-1929`
Rationale: the RFC promises that `render.py` "actually unifies" the
underscore-prefixed CLI helpers, and the extraction is genuinely
no-behaviour-change: `cli.py:1917-1929` imports `format_header`,
`format_summary_line`, `format_evidence_dates`, `format_evidence_excerpts`,
and `pick_question` from `render`. Good. But `VERDICT_PROMPT` (line
23-25) and the alias map at lines 26-31 are only consumed by the CLI's
own input loop; `web.py` does not import them. Either move them back
to the CLI module or document them in the RFC as "shared verdict
vocabulary, even if only the CLI uses VERDICT_PROMPT today." Small
hygiene issue, but the RFC's "no copies that can drift" claim is what
sells the extraction.

### F010 — Persistent target order reasoning is correct; option A is genuinely impossible, not just dispreferred
Severity: nit (commendation)
Source: `docs/rfcs/0027-interview-web-ui.md:249-280`; `src/engram/interview/sampler.py:292-308`
Rationale: the RFC's argument that option A (deterministic re-sample
per render) is forced out by the cooldown filter is correct. The
sampler's `_last_blocking_label_at` (sampler.py:292-308) reads
`gold_labels` and uses it inside `_cooldown_filter`. Every committed
verdict (any verdict other than `skip`) extends that map, so a re-
sample mid-session has a strictly different filtered pool than the
original sample. "Same seed, same shuffle" is not enough because the
indices being shuffled are different. The migration 011 design is the
right call, the version-triple stamp at session creation is the right
identity for the resume path, and the `chk_session_targets_version_triple`
CHECK mirrors `chk_gold_labels_version_triple`. This is the load-
bearing correctness story for the rerender model and the RFC argues it
cleanly.

### F011 — D044/D069 invariants are mechanically guarded; web surface introduces no auto-flip path
Severity: nit (commendation)
Source: `docs/rfcs/0027-interview-web-ui.md:316-324`; `src/engram/interview/web.py:1-16`; `tests/test_interview_web.py:828-844`
Rationale: the RFC's "no web route may import
`engram.consolidator.transitions`" / "no template may render a
promote-belief / accept / reject / pin affordance" invariants are
guarded by `test_consolidator_transitions_unimportable_from_web`, and
spot-reading `question.html` / `index.html` confirms no
accept/reject/promote affordance is rendered. The route surface is
purely (sample, render, record verdict, render, redirect); no path
touches belief status or transition. D044 / D069 hold across this
surface; D044's "no auto-promotion or auto-demotion of beliefs from
gold labels" is structurally preserved. The RFC's invariants are
specific, testable, and tested — good engineering discipline.

### F012 — Single Uvicorn worker + sync `def` is correct for psycopg, but the RFC should pin the connection lifecycle
Severity: minor
Source: `docs/rfcs/0027-interview-web-ui.md:344-349`; `src/engram/interview/web.py:159-165`
Rationale: the RFC commits to "sync `def` route handlers + threadpool
dispatch + `uvicorn --workers 1`" because `engram.interview.{storage,
sampler, agent}` is sync `psycopg`. The implementation matches. But
the RFC does not spell out the connection-per-request model
(`_get_conn` opens a new `connect()` per FastAPI dependency, yields it,
closes on exit). RFC 0022's `engramd` proposal uses
`psycopg_pool.ConnectionPool`; RFC 0027 silently chooses
connect-per-request. For a single-operator local UX that is fine, but
when this surface migrates onto `engramd` (per the RFC's "Relationship
to RFC 0022" section), the pool ownership will move under the daemon.
Pin the v1 contract ("one psycopg connection per request, no pool")
in the RFC so the engramd migration carries a documented diff rather
than an implementation accident.

## Open questions

- **F001 follow-up.** Is `ENGRAM_INTERVIEW_ALLOWED_ORIGINS` actually in
  scope for v1, or did it land between the RFC's promotion and the
  current scaffold? If in scope, what is the operator opt-in surface
  — env var only, or also a CLI flag with a startup warning analogous
  to the (deliberately-absent) `--allow-non-loopback`? If not in scope,
  is there a follow-on RFC (D081?) that I have not been pointed at?
- **F002 follow-up.** Confirm CLI parity for `unsure`. The CLI accepts
  empty rationale; the web rejects it. Either is defensible, but the
  RFC must pin one rule. Recommendation: accept empty for `unsure`
  (matches CLI; matches the "note (Enter to skip)" gloss).
- **F003 follow-up.** Does the implementation's "create session, then
  immediately close on empty pool" leave undesirable rows in
  `gold_label_sessions`? If yes, the RFC's "do NOT create the session"
  wording is the right contract. If no, document the
  always-create-then-maybe-close behaviour explicitly.
- **F004 follow-up.** Confirm the error rerender's swap shape. A real
  browser exercise (the user's "yeesh" UX session noted in the project
  memory) would surface whether the nested `<html>` artifact actually
  renders cleanly, partially, or visibly broken. Worth a smoke
  before the next promotion gate.
- **F008 follow-up.** Re-anchor the FINDINGS_LEDGER F006 cross-
  reference to a non-quarantined location. If the ledger is gone for
  good (RFC 0032), inline the deferral rationale into RFC 0027 text.
- **D080 anchor.** The RFC's `Decision refs` block includes D080, but
  the rerun packet doesn't include a DECISION_LOG snippet for D080.
  Confirm D080 is actually recorded and matches the RFC's stated
  promotion intent.

verdict: accept_with_findings
