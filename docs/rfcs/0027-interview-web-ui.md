<a id="rfc-0027"></a>
# RFC 0027: Interview Web UI

| Field | Value |
|-------|-------|
| RFC | 0027 |
| Title | Interview Web UI |
| Status | promoted |
| Implementation | scaffolded |
| Date | 2026-05-08 |
| Context | RFC 0021 § Web UI (v2 — out of scope there); D079 (RFC 0021 acceptance); RFC 0022 (server binary, HTTP API, MCP); D016 (eval gate sequencing); D044 / D069 (advisory-only labels); HUMAN_REQUIREMENTS § "the eval gold set is the actual specification" / § "no cloud, no telemetry"; `src/engram/cli.py` lines 1700+ (interactive interview loop); `src/engram/interview/` (sampler, agent, storage); `migrations/010_gold_labels.sql`; `docs/howto/gold-set-interview.md` |
| Spec | docs/specs/0027-interview-web-ui-spec.md |

Decision refs:
  - D016
  - D044
  - D069
  - D074
  - D079
  - D080

Review refs:
  - none

Phase refs:
  - PHASE-0003-FOLLOWON

**Promoted:** the implementation contract for this RFC lives at
`docs/specs/0027-interview-web-ui-spec.md`. Future implementation work,
test enumeration, and route-level details should target the spec; this
RFC remains as the reasoned proposal and provenance for why the contract
exists.

This RFC proposes a **local-only, browser-based UI** for the gold-set
interview surface so the operator can rule on claims and beliefs at the
pace of reading rather than the pace of typing. The CLI loop landed under
RFC 0021 v1 (D079) is honest about being a smoke surface; live operator
testing produced concrete UX failures (no evidence excerpt, missing
predicate gloss, wrong question framing for transient predicates) that the
CLI fixed individually but that compose into a workflow the CLI cannot
ergonomically host. The web UI is the surface where ruling on 25–50
labels in a sitting becomes achievable.

This RFC does **not** introduce a hosted service, an authentication
layer, multi-user support, or any change to the gold-label schema. It is
strictly an additional rendering of the data already produced by
`engram.interview.{sampler, agent, storage}` against the same local
Postgres. Nothing leaves the machine.

## Background

RFC 0021 § Web UI deferred the web surface explicitly: "Captured here
only to clarify v1 boundaries. The web surface is the only plausible
interview UX for a non-developer user; CLI v1 exists to keep the backend
contract honest before that work starts." That framing has played out
cleanly: the schema, sampler, append-only triggers, and verdict
vocabulary all survived live operator use; the CLI loop is functional
but ergonomically lossy. Three friction sources surfaced repeatedly:

1. **Verdict-per-line throughput.** A 50-question session in the CLI
   takes ~30 minutes because every prompt is line-buffered: read
   header, read question, type verdict, type rationale (or skip), wait
   for next render. Each context switch between reading and typing
   costs attention. A web UI lets the operator click a verdict button
   while reading the next question.
2. **Evidence inspection.** Even with the inline excerpt
   improvements (commit `40cfcbc`), the CLI shows up to three
   excerpts truncated at 280 characters. Real verdicts often need the
   full conversation around an excerpt; the CLI cannot do that without
   a second tool call. A web UI can show the full message thread on
   demand without breaking the loop.
3. **Stratum visibility.** `engram phase3 interview coverage` exists
   but is a separate command; the operator does not see "you just
   labeled 4 mood targets in a row, here's the strata distribution"
   until they leave the loop. A web UI can show a small coverage
   panel in the sidebar.

The CLI loop is also useful and stays. It is the only smoke-test
surface that can be exercised without browser automation, and it is
the only surface that runs against headless / scripted contexts
(seeded labels, batch eval prep). Keep it.

The proposed Web UI uses **FastAPI + Jinja2 + htmx** because the
implementation footprint is small and the resulting build has zero
JavaScript bundling. htmx attributes (`hx-post`, `hx-target`,
`hx-swap`) implement the per-question swap-in pattern in declarative
HTML; no React, no Vue, no Svelte, no esbuild, no npm. Server
templates render the full page; htmx swaps fragments. The whole UI is
~3 templates and ~200 lines of route code on top of the existing
`engram.interview` package.

RFC 0022 (`engramd`, the server binary with HTTP API and MCP interface)
is the actual D020 precedent for "localhost-bound HTTP service inside
the Engram stack": it commits to a `127.0.0.1` default bind with any
non-loopback bind requiring an explicit flag and a startup warning. The
interview web UI owns the same posture directly. (RFC 0012 is the
Python agentic coding standard, not an HTTP-service spec; earlier drafts
of this RFC cited it in error.)

## Relationship to RFC 0022

RFC 0022 proposes `engramd` with first-class interview HTTP endpoints
(`POST /v1/interview/sessions`, `GET /v1/interview/sessions/{id}/next`,
`POST /v1/interview/sessions/{id}/answer`, ...). On paper that is a
parallel surface to what this RFC proposes; in practice RFC 0022 is
`Status: proposal` / `Implementation: none` — there is no `engramd`
binary, no `src/engram/api/` module, and no FastAPI in `pyproject.toml`
today. The collision is theoretical.

V1 of this RFC therefore stands as a **separate FastAPI app under
`src/engram/interview/web.py`**, calling `engram.interview.{agent,sampler,
storage}` directly. The forward-compat path is explicit: when `engramd`
lands, the web routes migrate from those direct module calls to POSTing
`engramd`'s interview HTTP endpoints, and the FastAPI app becomes a
Jinja layer mounted on `engramd`'s ASGI tree. This resolves RFC 0022's
Open Question 9 ("does engramd serve the web UI's static bundle?") in
favor of "yes, eventually." Until then, deferring this RFC on a
Phase-5-prelude server-binary RFC sacrifices a load-bearing Phase-3
follow-on operator UX gain on a sequencing bet.

## Problem

How do we let the operator rule on gold labels at the pace of reading,
without:

- letting the gold-label corpus or any evidence excerpt leave the
  machine;
- introducing a build pipeline (npm, webpack, esbuild) that complicates
  install and breaks D020's local-first posture;
- duplicating the rendering logic that already lives in the CLI loop's
  `_fetch_target_display`, `_fetch_evidence_excerpts`, `_pick_question`,
  and `_RATIONALE_PROMPT_BY_VERDICT` helpers;
- adding a schema layer above `gold_labels` that the CLI loop and the
  web UI would have to keep in sync;
- relaxing the `--privacy-tier-max 1` default ceiling on export;
- adding authentication, TLS, sessions, or any surface that has no
  meaning on a single-user local machine?

## Proposal

### Shape

A new module `src/engram/interview/web.py` exposes a FastAPI
application. Templates live in-package at
`src/engram/interview/templates/`; the vendored htmx bundle lives at
`src/engram/interview/static/htmx.min.js`. A new CLI subcommand
`engram phase3 interview serve [--host 127.0.0.1] [--port 8765]` boots
the server via Uvicorn. V1 is **loopback-only with no escape clause**:
any non-loopback `--host` is refused at startup with exit 8 and there
is no `--allow-non-loopback` flag. Non-loopback support, if it is ever
needed, is a follow-on RFC paired with token auth (see RFC 0022 Open
Question 7's auth roadmap).

Shared rendering logic moves out of `cli.py` into a new module
`src/engram/interview/render.py`. The full extraction surface
(verdict vocabulary constants, evidence layout caps, header / summary /
evidence-dates formatters, the renamed `format_evidence_excerpts`, and
the question-picker) is enumerated in the spec; both `cli.py` and
`web.py` call these helpers. The CLI loop is refactored to import from
`render` rather than maintain underscore-prefixed copies, with
no-behavior-change verified by golden-output tests.

`pick_question` gains an explicit `now: datetime | None = None` keyword
that defaults to `datetime.now(timezone.utc)`; `evidence_max` is
rendered via UTC `.date().isoformat()` so the CLI and web verdict on the
same belief produce identical `ev_date` strings regardless of operator
timezone.

### Routes

V1 routes (each returns either a full HTML page or an HTML fragment
suitable for htmx swap; the spec at
`docs/specs/0027-interview-web-ui-spec.md` carries the full route
contract — this section names the routes and their load-bearing
behaviors):

| Verb | Path | Purpose |
|------|------|---------|
| GET | `/` | Open-session list with progress (`K/N answered, opened Xh ago`) and per-row `[Abandon]` link; "New session" form exposes only `n` and `seed`. |
| POST | `/sessions` | `insert_session` + `sampler.sample(n)`; if sampler returns `[]`, do NOT create the session — re-render `index.html` with the empty-corpus diagnostic banner. Otherwise materialize the sampled order into `gold_label_session_targets` and redirect to `/sessions/{id}/q/1`. |
| GET | `/sessions/{session_id}` | Session-level summary; redirect to current target's `q/{idx}` if any unanswered remain, else to `/`. |
| GET | `/sessions/{session_id}/q/{idx}` | Render the `idx`-th sampled target: header, predicate gloss, evidence excerpts (3-row cap with "show all N" disclosure), question, six verdict buttons, rationale textarea (auto-shown only on `false` / `stale` / `unsupported` / `unsure`), inline strata strip footer, Save-and-quit button. Uses `hx-push-url="true"` so back/forward and bookmarks work. |
| POST | `/sessions/{session_id}/q/{idx}/verdict` | `agent.record_verdict(session_id, target, verdict, rationale)`. `true` and `skip` POST verdict + empty rationale in a single htmx round-trip; `false` / `stale` / `unsupported` / `unsure` swap in the rationale textarea and require Submit. On the final commit, the handler marks the session complete inside the same guarded POST transaction and issues `HX-Redirect: /` (no mutating GET, no explicit Complete button). |
| GET | `/sessions/{session_id}/messages/{message_id}` | Full message body for one cited evidence row in this session. **Tier 1 enforced at the route layer**: parent message tier > 1 returns 403 with a structured envelope. Higher-tier env var deferred to v1.1. |
| GET | `/sessions/{session_id}/messages/{message_id}/context?before=N&after=M` | Cited message + N predecessors + M successors from the same `conversation_id`. The anchor `message_id` must itself be cited by a materialized session target. Hard cap `N + M <= 20`. Tier 1 max-carry: if any returned row has tier > 1, the entire response is 403 (matches RFC 0021's multi-source carry rule). |
| GET | `/sessions/{session_id}/q/{idx}/evidence/all` | Show-all-rows disclosure (the 3-row cap on the question page becomes "show all N"). Tier 1 enforced. |
| POST | `/sessions/{session_id}/save-and-quit` | No verdict commit; in-progress rationale is **discarded for CLI parity**. Response banner contains the resume command string `engram phase3 interview resume --session-id <uuid>`. Status line on the question page reads "K/N answered — closing this tab is safe; verdicts are saved as you commit them." Redirects to `/`. |
| POST | `/sessions/{session_id}/complete` | `mark_session_completed`; redirects to `/`. Reserved for guarded form-driven completion only; final-question auto-completion happens inside the verdict POST. |
| POST | `/sessions/{session_id}/abandon` | Calls `mark_session_completed` with `operator_note='abandoned via web'`; redirects to `/`. Surfaced from the index page's per-open-session row. |

The new-session form on `index.html` exposes only `n` and `seed`;
`--include-superseded` and `--ignore-cooldown` remain **CLI-only in v1**
(adversarial-sweep mode is a deliberate CLI verb, per RFC 0021's
framing). v1.1 may add an `[Advanced]` collapse with a consent banner.

V1 explicitly does not expose `export`, `history`, `/coverage`
(dashboard), or `enable-active-learning` as web routes; those stay
CLI-only until v1.1. The inline strata strip footer on
`/sessions/{id}/q/{idx}` is a single
`SELECT stability_class, count(*) FROM gold_labels WHERE session_id = ?
GROUP BY 1` rendered inline — it honors the §Background promise of
friction-source 3 without committing the dashboard surface.

Web verdicts leave `gold_labels.evidence_excerpt` NULL in v1, matching
the CLI (cli.py:1977). The "show full message" surface is read-only and
never round-trips through `record_verdict`; populating
`evidence_excerpt` from a higher-tier message would write a higher-tier
excerpt into a row whose `privacy_tier` reflects the parent, breaking
the privacy carry. v1.1 may introduce a redactor.

### Templates

V1 ships templates at `src/engram/interview/templates/`:

- `base.html` — page chrome, single inline `<style>`, single
  `<script src="/static/htmx.min.js">` (vendored, no CDN per F004),
  inline keyboard dispatcher (see § Worked example), `aria-live="polite"`
  live region announcing "Question K of N" on each htmx swap, an
  `htmx:afterSwap` listener that moves focus to `<h2 tabindex="-1">` on
  the question page, and the help-modal markup (hidden by default).
- `index.html` — open-session list with progress columns and per-row
  `[Abandon]` link; new-session form exposing only `n` and `seed`;
  empty-corpus diagnostic banner slot.
- `question.html` — header line, summary line with predicate-doc
  append, evidence-dates / valid-from line, evidence excerpts
  (3-row cap with "show all N" disclosure), question line, six verdict
  buttons in a single row, rationale textarea (initially hidden;
  revealed by htmx swap on the rationale-required verdicts),
  Save-and-quit button, status line, and inline strata strip footer.
  Verdict buttons get `aria-label` carrying the gloss verbatim from
  `gold_label_verdict_vocabulary`; the rationale textarea gets
  `aria-describedby` pointing at the verdict-specific prompt span;
  verdict differentiation uses icon + underline + color (WCAG 1.4.1
  satisfied without color-only).
- partials `_evidence_excerpt.html` and `_strata_strip.html` (see spec).

CSS is vendored inline in `base.html` (single `<style>` block). No
external stylesheet, no build step, no npm.

### Sampler reuse

The sampler is shared with the CLI: `GoldLabelSampler(conn, seed=...)`
runs once at session creation; the sampled list is materialized into
`gold_label_session_targets` (see § Persistent target order below). The
web routes index into that materialized list by `idx`, so
reload-on-question is stable and refresh does not re-sample.

### Persistent target order

The CLI v1 loop materializes the sampled list in memory and iterates;
the web UI cannot rely on in-memory state across requests. "Re-sample
on every request with the same seed" *is not* a deterministic option:
every successful verdict POST shifts the cooldown filter inside the
sampler (see `sampler.py:286-302` and `sampler.py:341-342`), so
re-sampling between renders within a single session drifts the index
map. Materializing the sampled order at session creation is therefore
**forced, not chosen** — it is the only correctness-preserving option.

Migration `011_gold_label_session_targets.sql` plus
`013_interview_active_learning_state.sql` ship as the **RFC 0027 schema
baseline**. Migration 011 creates the materialized-order table; migration
013 adds the active-learning/confidence carry fields that the current
storage layer needs to reconstruct a frozen `SampledTarget`. The table:

- PK is `(session_id, idx)` with `idx INT NOT NULL CHECK (idx >= 0)`.
  The table is 0-indexed; the URL exposes 1-indexed `q/{idx}` for parity
  with the CLI's `[1/n]` framing — the route translates `url_idx - 1`
  on entry.
- Stamps `candidate_pool_snapshot_id` and the typed version triple
  (extraction prompt + model versions iff `target_kind = 'claim'`,
  consolidation prompt + model versions iff `target_kind = 'belief'`,
  `request_profile_version` always) at session creation. A session
  resumed three days later replays against the pool that existed at
  session creation, regardless of corpus drift; if the operator wants a
  fresh pool, they start a new session.
- Carries `active_learning_signal_version`, `confidence`, and
  `observed_at` (added by migration 013) so resume does not substitute
  defaults or lose the active-learning provenance stamped at sampling time.
- Append-only at the schema layer via
  `fn_gold_label_session_targets_append_only` (BEFORE UPDATE OR DELETE),
  matching the trigger naming convention from migration 010.
- FK to `gold_label_sessions` with `ON DELETE CASCADE`.

The CLI loop is updated to also write the materialized order so a
session created via the CLI is resumable from the web UI. Full schema
text and constraints live in the spec.

### Privacy posture

- **Loopback-only, no escape clause.** `--host` defaults to `127.0.0.1`;
  any non-loopback `--host` is rejected with exit 8. There is no
  `--allow-non-loopback` flag in v1. Non-loopback support is a
  follow-on RFC paired with token auth.
- **No auth, no TLS.** The owner of the local machine is the only user
  inside the loopback boundary; localhost-only means there is no
  transport surface to protect.
- **Origin-header allowlist on POST routes.** "Localhost is single-user"
  is the wrong threat model for browsers — any tab on the local machine
  can drive forms at `127.0.0.1:<port>`. v1 enforces a required
  `Origin` allowlist (`http://127.0.0.1:<bound-port>` and
  `http://localhost:<bound-port>`, plus D081 operator-named hosts)
  plus a required `Sec-Fetch-Site: same-origin` header on every mutating route
  (`POST /sessions`, `POST /sessions/{id}/q/{idx}/verdict`,
  `POST /sessions/{id}/save-and-quit`, `POST /sessions/{id}/complete`,
  `POST /sessions/{id}/abandon`). Mismatch returns 403. Per-form CSRF
  tokens are deferred to v1.1 (the deferral is conditional on an
  enforcement test landing in v1; rationale at
  `docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_FINDINGS_LEDGER.md`
  F006).
- **Tier 1 hard-coded on question, full-message, and context routes.**
  `GET /sessions/{id}/q/{idx}`,
  `GET /sessions/{id}/messages/{message_id}`,
  `GET /sessions/{id}/messages/{message_id}/context`, and
  `GET /sessions/{id}/q/{idx}/evidence/all` enforce a Tier 1 ceiling at
  the route layer before rendering any evidence excerpt. Parent target or
  message tier > 1 (or any row tier > 1 in the context window) returns
  403. The
  `ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX` env var is reserved but not
  implemented in v1; higher-tier rendering is deferred to v1.1.
- **No outbound network.** The web UI is a corpus-reading process under
  D020 and must be run inside the same operator-enforced no-egress
  boundary as other corpus readers (for example a network namespace,
  sandbox, or deny-by-default firewall rule). htmx is vendored at
  `src/engram/interview/static/htmx.min.js` and served from the wheel;
  no CDN reference is reachable from any rendered page, but vendoring is
  not itself the egress control.

#### Invariants (D044 / D069 on the web surface)

- No web route may import `engram.consolidator.transitions`.
- No template may render a promote-belief / accept / reject / pin
  affordance.
- D044 / D069 hold on the web surface as on the CLI.

These invariants are mechanically guarded in the implementation phase by
a test that imports `engram.interview.web` and asserts no symbol from
`engram.consolidator.transitions` is reachable in its module graph.

### Error handling

- Trigger rejections (`fn_gold_labels_append_only`,
  `fn_gold_labels_validate_target`,
  `fn_gold_labels_carry_privacy_tier`) bubble up as
  `GoldLabelStorageError` from `record_verdict`; the route catches,
  rolls back, and renders the same question with an error banner
  ("the target was not labeled; details: ..."). The session stays
  open and the operator can move on.
- 404 on unknown session_id or out-of-range idx.
- 422 on unknown verdict (htmx surfaces this as a banner; the
  buttons in question.html only emit valid verdicts, so 422 is a
  paranoia path).
- 403 on `Origin` allowlist mismatch on any mutating route, with a
  structured envelope (see §Privacy posture).
- Server-side rate limiting: none in v1. Single-user local.

### Process model

V1 uses **sync `def` route handlers + threadpool dispatch +
`uvicorn --workers 1`**. Every `engram.interview.{storage, sampler,
agent}` helper is sync `psycopg`; `async def` handlers would block the
event loop on the first DB call. A single worker keeps the connection
pool simple and matches the single-operator localhost surface.

### Dependencies

`pyproject.toml` gains an optional extra so the headless / CI install is
unchanged:

```toml
[project.optional-dependencies]
serve = [
    "fastapi>=0.110,<1",
    "uvicorn>=0.30,<1",
    "jinja2>=3.1,<4",
    "python-multipart>=0.0.9,<1",
]
```

The `dev` extra grows `"engram[serve]"` so `make typecheck` resolves
`engram.interview.web` imports without a pyright exclusion.
`[tool.setuptools.package-data]` ships templates and `htmx.min.js`
inside the wheel. The CLI subcommand `engram phase3 interview serve`
catches the FastAPI / Uvicorn / Jinja2 / python-multipart `ImportError`
and re-raises as `SystemExit(2)` with an actionable
`pip install engram[serve]` message.

### Test surface

The implementation spec at `docs/specs/0027-interview-web-ui-spec.md`
carries the full test enumeration (route coverage, trigger-rejection
banner test against the real-DB `conn` fixture, accessibility checks,
privacy-tier ceiling enforcement, render golden outputs). This RFC just
names the new files:

- `tests/test_interview_web.py` (new) — every route, including
  `Origin` allowlist enforcement, single-click and two-click verdict
  commit, final POST completion, Tier 1 ceiling on `/q/{idx}`,
  `/messages/{id}` and `/messages/{id}/context`,
  htmx-served-from-static (not CDN), import-graph isolation from
  `engram.consolidator.transitions`, and the `aria-live` region.
- `tests/test_interview_render.py` (new) — golden-output tests for
  `format_header`, `format_summary_line`, `format_evidence_dates`,
  `format_evidence_excerpts`, and `pick_question` (including UTC
  determinism for `evidence_max`).
- `tests/test_migrations.py` (extended) — append-only trigger,
  version-triple CHECK constraint, and PK uniqueness for
  `gold_label_session_targets`, plus the migration 013 carry columns.

## Worked example

```
$ engram phase3 interview serve
phase3 interview serve: listening on http://127.0.0.1:8765
                        ctrl-c to stop; non-loopback hosts refused
```

Operator opens `http://127.0.0.1:8765/`. Index page shows:

```text
Engram interview — open sessions

Open sessions
  • <none>

New session
  n: [10]   seed: [4]
  [ Start ]
```

Click Start. POST `/sessions` opens session `<uuid>`, samples 10
targets, materializes the order in `gold_label_session_targets`, and
redirects to `/sessions/<uuid>/q/1`. The question page renders the same
content the CLI would print (worked example below is reconciled with
actual CLI output: no `[ ]` glyph, no `Conversation:` prefix, plausible
ChatGPT title):

```text
[1/10] belief 8d075c32  stability=mood  conf=0.80  conf_band=0.8-1.0  recency=<365d  status=candidate

User —[feels]—> disbelief    (emotion or disposition)
evidence: 1 row(s), evidence dates: 2025-12-25, valid_from 2025-12-25

  2025-12-25  user  (chatgpt)  ["rust ownership question"]
      I can't believe how much has happened this year —
      [show full message]

Q: Was this true around 2025-12-25?

  [ trueᵗ ]  [ falseᶠ ]  [ staleˢ ]  [ unsupportedⁿ ]  [ unsureᵘ ]  [ skipᵏ ]

  3/10 answered — closing this tab is safe; verdicts are saved as you commit them.
  strata so far: mood=2  stance=1

  [ Save and quit ]
```

Verdict button row order is `[true]  [false]  [stale]  [unsupported]
[unsure]  [skip]` with `true` leftmost and `skip` rightmost — the two
single-click commits live at the extremes. Each button shows its
keyboard letter as a small superscript so operators can learn the
bindings without consulting `?`.

Verdict-commit semantics:

- `true` and `skip` POST verdict + empty rationale in a **single htmx
  round-trip** (no rationale prompt).
- `false` / `stale` / `unsupported` / `unsure` swap in the rationale
  textarea and require Submit (two round-trips).

Click `false`; htmx POSTs `/sessions/<uuid>/q/1/verdict` with
verdict=`false`; rationale textarea pops in below the buttons:

```text
correct value: [ I felt disbelief specifically about the year's pace, not as a general state ]  [ Submit ]
```

Click Submit. The verdict commits; the handler issues `HX-Redirect` to
`/sessions/<uuid>/q/2`. Repeat. When `idx == n`, the verdict-commit
handler calls `mark_session_completed` inside the same POST transaction
and issues `HX-Redirect: /`.

**Keyboard.** `accesskey` plus a bare-key dispatcher in `base.html`
binds `t` / `f` / `s` / `n` (unsupported) / `u` / `k` / `q` (save and
quit) / `?` (help) to their buttons. The dispatcher ignores keystrokes
when an `<input>` or `<textarea>` is focused. Inside the rationale
textarea, Enter inserts a newline; Shift-Enter submits the form. `?`
opens a help modal listing keyboard shortcuts and verdict glosses
sourced verbatim from `gold_label_verdict_vocabulary` (single source of
truth for gloss text); `Esc` closes the modal and restores focus. The
full keyboard binding table lives in the spec.

## What this RFC does not propose

- **No auth, no TLS, no sessions.** Localhost only. Single user.
- **No multi-user / multi-tenant support.** Engram is single-user.
- **No remote access.** Non-loopback hosts refused.
- **No JS framework.** htmx + server-rendered HTML only.
- **No build pipeline.** No npm, no webpack, no esbuild.
- **No new schema beyond the persistent target order table.**
- **No export-from-UI.** CLI export remains canonical; web v1.1 may
  add it.
- **No history-from-UI.** Same — CLI history remains canonical.
- **No coverage dashboard.** Same — `/coverage` stays CLI-only. (An
  inline strata strip footer ships on the question page; the dashboard
  surface remains deferred to v1.1.)
- **No `--include-superseded` / `--ignore-cooldown` checkboxes.** The
  new-session form exposes only `n` and `seed`; adversarial-sweep mode
  remains CLI-only in v1.
- **No `--allow-non-loopback` flag.** v1 is loopback-only with no
  escape clause; non-loopback support is a follow-on RFC paired with
  token auth.
- **No active-learning toggle UI.** `enable-active-learning` stays a
  CLI-only project decision.
- **No raw-evidence redaction of `evidence_excerpt` in the UI.** The
  operator is the same person whose corpus this is; redaction is the
  export-time concern, not the read-time concern.

## Open questions

The questions raised in the proposal draft were resolved during
synthesis (see
`docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_SYNTHESIS.md`).

1. **Template path** — resolved: `src/engram/interview/templates/`
   (in-package) per Python packaging convention.
2. **htmx delivery** — **resolved**: vendored at
   `src/engram/interview/static/htmx.min.js`. No CDN reference
   reachable from any rendered page. (F004.)
3. **Higher-tier rendering env var** — deferred to v1.1. v1 hard-codes
   Tier 1 ceiling at the route layer for `/q/{idx}`,
   `/messages/{id}`, `/messages/{id}/context`, and
   `/q/{idx}/evidence/all`. The
   `ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX` name is reserved.
4. **Persistent target order** — resolved: option B is forced (option
   A drifts the index map; see § Persistent target order). Migration
   011 plus migration 013 carry fields ship in v1.
5. **CSRF tokens** — resolved: deferred to v1.1 conditional on the v1
   `Origin` allowlist + `Sec-Fetch-Site: same-origin` enforcement test
   landing.
6. **Process model** — resolved: sync `def` + threadpool dispatch +
   `uvicorn --workers 1`.
7. **Test surface** — resolved: trigger-rejection banner test uses the
   real-DB `conn` fixture from `tests/conftest.py`. Full enumeration in
   the spec.
8. **Keyboard shortcuts** — resolved: `t` / `f` / `s` / `n`
   (unsupported) / `u` / `k` / `q` / `?` / `Esc`. Full table in the
   spec.
9. **Spec location** — resolved: spec lands at
   `docs/specs/0027-interview-web-ui-spec.md`; this RFC is promoted.

## Promotion path

1. **(done)** Multi-agent review (claude / codex / gemini reviewers +
   ledger + synthesis + final review), scaffolded under
   `striatum/rfc-0027-interview-web-ui-review/`. Synthesis at
   `docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_SYNTHESIS.md`.
2. **(done)** Synthesis recommended **revise-rfc**; the 29 accepted
   deltas have been folded into this RFC text.
3. **(in progress)** Author the implementation spec at
   `docs/specs/0027-interview-web-ui-spec.md` from the accepted RFC
   plus synthesis acceptance deltas. This RFC is marked `promoted`.
4. **(in progress)** Record the project decision as `D080` in
   `DECISION_LOG.md`.
5. **(in progress)** Add a `BUILD_PHASES.md` line under Phase 3
   follow-on (alongside the existing gold-set entry) noting the web
   surface is part of the same follow-on.
6. **(forward)** Implement under
   `striatum/rfc-0027-interview-web-ui-implementation/` with parallel
   builder sub-agents where the dependency graph allows (app code,
   templates, tests).
7. **(forward)** Verify and final-review per the standard implement →
   verify → final-review pattern.
