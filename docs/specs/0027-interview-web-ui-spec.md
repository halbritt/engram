<a id="spec-0027"></a>
# Spec 0027: Interview Web UI Implementation Contract

| Field | Value |
|-------|-------|
| Spec | 0027 |
| Title | Interview Web UI |
| Status | accepted |
| Source RFC | [RFC 0027](../rfcs/0027-interview-web-ui.md) (promoted via D080) |
| Source synthesis | [RFC_0027_INTERVIEW_WEB_UI_SYNTHESIS.md](../reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_SYNTHESIS.md) |
| Date | 2026-05-08 |
| Decision refs | D016, D020, D044, D069, D078, D079, D080 |
| Phase refs | PHASE-0003-FOLLOWON |

## Purpose

This document is the implementation contract for the Engram Interview Web UI
(RFC 0027). RFC 0027 was promoted via D080 after the 2026-05-08 multi-agent
review (claude / codex / gemini → ledger → synthesis). Future implementation
prompts, reviews, and acceptance gates target this spec; the RFC remains as
historical context and provenance for *why* the contract exists, not as the
load-bearing implementation target. A builder agent reading this document
should be able to implement the surface without re-deriving design decisions
from the RFC, the synthesis, or the findings ledger.

## Out of scope

The following are explicitly out of v1 scope:

- Hosted service, authentication layer, multi-user / multi-tenant support, or
  any mode where the UI accepts requests from a non-loopback origin.
- Any change to the gold-label schema beyond migration 011 below.
- A build pipeline (npm, webpack, esbuild) or a JS framework (React, Vue,
  Svelte). htmx is the only client-side library; templates render
  server-side.
- Export-from-UI. CLI `engram phase3 interview export` remains canonical.
- History-from-UI. CLI `engram phase3 interview history` remains canonical.
- Coverage dashboard route (`/coverage`). The inline strata strip on
  `/q/{idx}` ships in v1; the dashboard surface is deferred to v1.1.
- Active-learning toggle UI. `enable-active-learning` stays a CLI-only
  project decision.
- The `--allow-non-loopback` flag from the original RFC. v1 ships
  loopback-only with no escape clause; non-loopback bind is a follow-on RFC
  paired with token auth (RFC 0022 Open Question 7's roadmap).
- The `ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX` environment variable. v1
  hard-codes a Tier 1 ceiling on the message-rendering routes; the env var
  is reserved but unimplemented.
- `--include-superseded` and `--ignore-cooldown` checkboxes on the
  new-session form. Adversarial-sweep mode requires dropping to the CLI.
- Per-form CSRF tokens. v1 enforces an Origin / Sec-Fetch-Site allowlist
  instead. Per-form tokens are deferred to v1.1 with a documented trigger
  (any new mutating route added after v1).
- Web-side population of `gold_labels.evidence_excerpt`. v1 leaves the
  column NULL on every web-committed verdict, matching CLI behavior.
- Promote-belief / accept / reject / pin affordances in any web template
  or route. D044 / D069 hold on the web surface as on the CLI.

## Architecture

### Modules

- `src/engram/interview/render.py` — shared CLI/web rendering helpers (NEW).
- `src/engram/interview/web.py` — FastAPI app (NEW).
- `src/engram/interview/templates/base.html` — page chrome (NEW).
- `src/engram/interview/templates/index.html` — open-session list and
  new-session form (NEW).
- `src/engram/interview/templates/question.html` — one-question page (NEW).
- `src/engram/interview/templates/_evidence_excerpt.html` — partial for one
  evidence row (NEW).
- `src/engram/interview/templates/_strata_strip.html` — inline strata
  footer partial (NEW).
- `src/engram/interview/static/htmx.min.js` — vendored htmx, no CDN (NEW).
- `src/engram/cli.py` — adds `engram phase3 interview serve` subparser;
  refactored to import verdict vocabulary, evidence layout caps, and
  rendering helpers from `engram.interview.render`. The
  `run_phase3_interview_start` driver is updated to also INSERT the
  materialized sampled order into `gold_label_session_targets` so
  CLI-started sessions are web-resumable.
- `migrations/011_gold_label_session_targets.sql` — materialized
  session-targets table with append-only trigger (NEW).
- `pyproject.toml` — adds the `serve` optional extra and a
  `[tool.setuptools.package-data]` block.

### Forward-compat to RFC 0022

RFC 0022 proposes `engramd`, a server binary with first-class interview
HTTP endpoints (`POST /v1/interview/sessions`,
`GET /v1/interview/sessions/{id}/next`,
`POST /v1/interview/sessions/{id}/answer`, etc.). RFC 0022 is currently
`Status: proposal` / `Implementation: none` — there is no `engramd` binary,
no `src/engram/api/` module, and no FastAPI in `pyproject.toml` today, so
the parallel-surface concern is theoretical. v1 of this spec stands as a
separate FastAPI app under `src/engram/interview/web.py`, calling
`engram.interview.{agent, sampler, storage}` directly.

When `engramd` lands, this spec's web routes migrate from those direct
module calls to POSTing `engramd`'s interview HTTP endpoints. The FastAPI
app in `engram.interview.web` becomes a Jinja layer mounted on `engramd`'s
ASGI tree (resolving RFC 0022 Open Question 9 in favor of "yes, eventually,
but not yet"). Implementers should keep the route handlers' call shape
close to `agent.record_verdict(session_id, target, verdict, rationale)` so
the migration is mechanical: one indirection layer (a thin client to
`engramd`'s HTTP surface) replaces the direct call. The migration is not
this spec's responsibility, but the assumption that RFC 0022's interview
endpoint shape stays close to `record_verdict`'s parameter list is
recorded under § Risks below so the RFC 0022 reviewer can validate it
when RFC 0022 reaches synthesis.

## render.py API

`src/engram/interview/render.py` is a new module that owns the verdict
vocabulary, evidence-layout caps, and rendering helpers shared by CLI and
web. The CLI re-imports the public symbols from this module; the
underscore-prefixed copies in `cli.py` are deleted. `tests/test_interview_cli.py`
gains golden-output tests pinning the rendered text to its current shape so
the extraction is verified to be no-behavior-change (F003).

```python
"""Shared rendering helpers for CLI and web (RFC 0027)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import psycopg

from engram.interview.sampler import SampledTarget


# Verdict vocabulary (moved verbatim from cli.py:1658-1666).
VERDICT_PROMPT: str = (
    "verdict [t/f/stale/unsupported/unsure/skip] (q to save and quit) > "
)
VERDICT_ALIAS: dict[str, str] = {
    "t": "true",
    "f": "false",
    "true": "true",
    "false": "false",
}
VERDICT_VALID: frozenset[str] = frozenset(
    {"true", "false", "stale", "unsupported", "unsure", "skip"}
)
RATIONALE_PROMPT_BY_VERDICT: dict[str, str] = {
    "false": "correct value > ",
    "stale": "when did it change? > ",
    "unsupported": "what's missing from the evidence? > ",
    "unsure": "note (Enter to skip) > ",
}

# Evidence layout caps (moved verbatim from cli.py:1667-1668).
EVIDENCE_EXCERPT_LIMIT: int = 280
EVIDENCE_ROWS_SHOWN: int = 3


def fetch_evidence_excerpts(
    conn: psycopg.Connection, evidence_ids: list[str]
) -> list[dict[str, Any]]:
    """Fetch up to EVIDENCE_ROWS_SHOWN messages by id, in chronological order.

    Lifted verbatim from ``_fetch_evidence_excerpts`` at ``cli.py:1671-1708``.
    Returns a list of dicts with keys ``id``, ``role``, ``created_at``,
    ``content`` (truncated at ``EVIDENCE_EXCERPT_LIMIT`` with a trailing
    ellipsis), ``source_kind``, and ``conv_title``. The caller decides
    whether to print or render.
    """


def fetch_target_display(
    conn: psycopg.Connection, target: SampledTarget
) -> dict[str, Any]:
    """Pull operator-readable summary plus evidence excerpts for a target.

    Lifted verbatim from ``_fetch_target_display`` at ``cli.py:1728-1814``.
    Dispatches on ``target.target_kind``. Returns a dict with keys
    ``summary``, ``predicate``, ``predicate_doc``, ``cardinality_class``,
    ``excerpts``, ``evidence_count``, ``evidence_min``, ``evidence_max``,
    ``valid_from``, ``valid_to``. Missing target rows return a dict with
    ``summary='<missing claim row>'`` or ``'<missing belief row>'`` and an
    empty ``excerpts`` list — the caller is expected to render the missing
    row visibly rather than crash.
    """


def pick_question(
    target: SampledTarget,
    display: dict[str, Any],
    *,
    now: datetime | None = None,
) -> str:
    """Choose a question framing based on stability_class and cardinality.

    Lifted from ``_pick_question`` at ``cli.py:1817-1835`` and adjusted per
    F015: ``now`` defaults to ``datetime.now(timezone.utc)``;
    ``evidence_max`` is rendered via UTC ``.date().isoformat()`` so CLI and
    web verdicts on the same belief render identical ``ev_date`` strings.
    Claim targets always ask about cited evidence; belief targets dispatch
    on ``cardinality_class == 'event'`` (point-in-time framing) or
    ``stability_class in {'mood', 'task'}`` (transient framing); else the
    "currently true" framing.
    """


def rationale_prompt_for(verdict: str) -> str | None:
    """Verdict-specific rationale prompt; returns None for ``true``/``skip``.

    Lifted from ``_prompt_rationale`` at ``cli.py:1853-1862`` minus the
    ``input()`` call. Returns the prompt string the caller should display.
    """


def format_header(target: SampledTarget, idx: int, total: int) -> str:
    """Render the ``[idx/total] target_kind target_id stability= conf= ...``
    header line.

    Lifted from ``cli.py:1929-1936``. Includes the ``status=...`` suffix
    when ``target.target_kind == 'belief' and target.belief_status`` is
    truthy. Implementations must reproduce the same whitespace and
    ordering: ``[i/n] kind id  stability=...  conf=N.NN  conf_band=...
    recency=...`` with two-space separators and a four-space prefix on the
    ``status=...`` suffix.
    """


def format_summary_line(display: dict[str, Any]) -> str:
    """Render summary plus predicate-doc append.

    Lifted from ``cli.py:1937-1941``. If ``display['predicate_doc']`` is
    truthy, returns ``f"{summary}    ({predicate_doc})"``; otherwise
    returns ``summary`` unchanged. The four-space prefix that the CLI
    prepends before printing is the *caller's* responsibility, not this
    helper's.
    """


def format_evidence_dates(display: dict[str, Any]) -> str | None:
    """Render the evidence-dates / valid-from suffix line.

    Lifted from ``cli.py:1942-1961``. Returns ``None`` when
    ``display['evidence_count']`` is None (the CLI suppresses the line in
    that case). Otherwise returns the
    ``"evidence: N row(s)[, evidence dates: ...][, valid_from ...]"`` line
    without leading whitespace; caller prepends.
    """


def format_evidence_excerpts(
    excerpts: list[dict[str, Any]], total: int
) -> list[str]:
    """Return chronological evidence-row text lines.

    Lifted from ``_print_evidence_excerpts`` at ``cli.py:1711-1725``. Each
    rendered row produces one header line (``"  ts  role  (src)  [title]"``)
    followed by indented body lines (``"      <line>"`` for each line of
    ``content.splitlines()``). The CLI joins with newlines and prints; the
    web template iterates rows and renders each as
    ``_evidence_excerpt.html``. If ``total > len(excerpts)``, an additional
    line ``"    … {total - len(excerpts)} more row(s) not shown"`` is
    appended.
    """
```

`cli.py` re-imports `VERDICT_PROMPT`, `VERDICT_ALIAS`, `VERDICT_VALID`,
`RATIONALE_PROMPT_BY_VERDICT`, `EVIDENCE_EXCERPT_LIMIT`,
`EVIDENCE_ROWS_SHOWN`, `fetch_evidence_excerpts`, `fetch_target_display`,
`pick_question`, `rationale_prompt_for`, `format_header`,
`format_summary_line`, `format_evidence_dates`, `format_evidence_excerpts`
from `engram.interview.render` and uses them directly. The
`_prompt_verdict` helper stays in `cli.py` because it owns the
`input()` call and the EOF/q handling that only the CLI needs.

## Routes

All routes live in `src/engram/interview/web.py` on a single
`fastapi.FastAPI` instance. Route handlers are sync `def` (not `async def`)
so the synchronous psycopg calls in `engram.interview.{agent, sampler,
storage}` do not block the event loop. URL `idx` is 1-indexed for parity
with the CLI's `[idx/total]` framing; the table column `idx` is 0-indexed,
and route handlers translate `url_idx - 1` on entry.

### Route table

| Verb | Path | Purpose | HX-Swap |
|------|------|---------|---------|
| GET | `/` | Open-session list and new-session form. | full page |
| POST | `/sessions` | Create session, materialize sampled order, redirect to q1. | redirect |
| GET | `/sessions/{session_id}` | Session summary; redirect to current target or `/`. | redirect |
| GET | `/sessions/{session_id}/q/{idx}` | Render one question. | full on direct GET; `outerHTML` swap of `<main>` on htmx swap |
| POST | `/sessions/{session_id}/q/{idx}/verdict` | Commit a verdict. | `HX-Redirect` |
| GET | `/sessions/{session_id}/messages/{message_id}` | Full message body. | `outerHTML` swap of evidence row |
| GET | `/sessions/{session_id}/messages/{message_id}/context` | Cited message + neighbors. | `innerHTML` swap of context panel |
| GET | `/sessions/{session_id}/q/{idx}/evidence/all` | All evidence rows for current target. | `innerHTML` swap of evidence section |
| POST | `/sessions/{session_id}/save-and-quit` | Discard in-progress, redirect to `/`. | redirect |
| POST | `/sessions/{session_id}/complete` | Mark complete, redirect to `/`. | redirect |
| POST | `/sessions/{session_id}/abandon` | Mark complete with abandon note. | redirect |
| GET | `/static/htmx.min.js` | Vendored htmx. | n/a |

### GET `/`

- Status: 200.
- Renders `index.html` with two slots: an `open_sessions` list and the
  new-session form.
- `open_sessions` is computed by a single
  `LEFT JOIN gold_labels ON session_id` query producing `(session_id,
  started_at, n_targets, n_answered)`. Each row renders as
  `K/N answered, opened Xh ago` with an `[Abandon]` link that POSTs to
  `/sessions/{session_id}/abandon`.
- `n_targets` comes from `SELECT count(*) FROM gold_label_session_targets
  WHERE session_id = ?` so the index is consistent regardless of how the
  session was created.
- The new-session form has only two fields: `n` (int, default 10) and
  `seed` (int, optional). No `include_superseded` checkbox, no
  `ignore_cooldown` checkbox.
- The page title is `Engram interview — open sessions`.
- Origin allowlist: not enforced on GET (read-only).

### POST `/sessions`

- Request body (form-encoded): `n=<int>`, optionally `seed=<int>`.
- Origin allowlist enforced: `Origin` header must be exactly
  `http://127.0.0.1:<port>` or `http://localhost:<port>`, and
  `Sec-Fetch-Site` (when present) must be `same-origin`. 403 on mismatch.
- Behavior:
  1. Allocate a `seed` if not provided.
  2. Call `insert_session(conn, seed=..., sampler_id=...,
     sampler_version=..., strata_weights={})` and `conn.commit()`.
  3. Construct `GoldLabelSampler(conn, seed=seed,
     include_superseded=False, ignore_cooldown=False)` and call
     `sampler.sample(n)`.
  4. If `sampled == []`: do **not** retain the session (per F029, the route
     re-renders `index.html` with the empty-corpus diagnostic
     `"no targets matched (empty corpus, all on cooldown, or
     current_beliefs not refreshed)"` and the
     `engram phase4 refresh-current-beliefs` hint). The session row may be
     left in place since it is harmless once `mark_session_completed` is
     called; the implementation may either delete it (within a single
     transaction) or call `mark_session_completed` to keep it out of the
     open-sessions list — implementers should pick the path that preserves
     `gold_label_sessions` append-only-ish semantics. Recommendation: call
     `mark_session_completed(conn, session_id, operator_note='empty corpus')`
     so the table is never `DELETE`d.
  5. Otherwise, batch-insert one `gold_label_session_targets` row per
     sampled target, populating the typed version triple from the target,
     and `conn.commit()`.
  6. Return `RedirectResponse('/sessions/{session_id}/q/1', status_code=303)`.
- Status codes: 303 (redirect on success), 200 (re-render index on empty
  sample), 403 (Origin mismatch), 422 (invalid `n` / `seed`).

### GET `/sessions/{session_id}`

- Status: 303 (redirect) on the happy path, 404 if `session_id` is unknown.
- Behavior: query
  `SELECT MIN(idx) FROM gold_label_session_targets t
   LEFT JOIN gold_labels gl
     ON gl.session_id = t.session_id AND gl.target_id = t.target_id
   WHERE t.session_id = ? AND gl.id IS NULL`
  to find the next unanswered idx; if found, redirect to
  `/sessions/{session_id}/q/{idx + 1}` (URL is 1-indexed). If no
  unanswered rows remain, redirect to `/`. (This is the resume path:
  bookmarks for `/sessions/{id}` survive across restarts.)

### GET `/sessions/{session_id}/q/{idx}`

- Status: 200 on success, 404 on unknown `session_id` or `idx > n` or
  `idx < 1`.
- Translates `url_idx = idx - 1` for the table lookup.
- Loads:
  1. The `gold_label_session_targets` row at `(session_id, url_idx)`.
  2. The verdict row in `gold_labels` for that target (if any), to support
     resume rendering.
  3. The full target display via `render.fetch_target_display(conn,
     target)`.
  4. The strata strip via `SELECT stability_class, count(*)
     FROM gold_labels WHERE session_id = ? GROUP BY 1`.
- Renders `question.html`. The page sets `hx-push-url="true"` so back /
  forward and bookmarks work.
- The page header line carries the version triple the session was created
  against (per § Risks: this lets the operator see the freeze under
  re-extraction).
- Returns the page wrapped in `base.html`. On htmx swap from a verdict
  commit, only the `<main>` block is swapped.

### POST `/sessions/{session_id}/q/{idx}/verdict`

- Request body (form-encoded): `verdict=<one of true|false|stale|
  unsupported|unsure|skip>`, optionally `rationale=<str>`.
- Origin allowlist enforced. 403 on mismatch.
- Status codes:
  - 200 with `HX-Redirect: /sessions/{session_id}/q/{idx + 1}` (or
    `HX-Redirect: /sessions/{session_id}/complete` if `idx == n`) on
    success.
  - 200 with re-render of the same question + error banner if
    `record_verdict` raises `GoldLabelStorageError` or
    `GoldLabelVerdictError` (the trigger-rejection path; see § Verdict
    commit flow).
  - 404 on unknown `session_id` or out-of-range `idx`.
  - 422 on `verdict` not in `VERDICT_VALID`.
- Behavior:
  1. Validate `verdict in VERDICT_VALID`.
  2. Load the target row from `gold_label_session_targets`.
  3. Reconstruct a `SampledTarget` with the version triple stamped at
     session creation (so re-extraction between renders does not drift).
  4. Call `agent.record_verdict(session_id, target, verdict,
     rationale=rationale or None)`. `evidence_excerpt` is **not** passed —
     the column stays NULL on every web-committed verdict (F017).
  5. `conn.commit()`. On exception, `conn.rollback()` and re-render with
     the error banner.
- Single-click commit: `verdict in {'true', 'skip'}` posts immediately
  with `rationale=''`. Two-click commit: `verdict in {'false', 'stale',
  'unsupported', 'unsure'}` swaps in the rationale textarea on first
  click; the second click submits the textarea content.

### GET `/sessions/{session_id}/messages/{message_id}`

- Status: 200 on success, 403 if parent message tier > 1, 404 if the
  message is not in the conversation graph reachable from this session's
  evidence.
- Tier 1 ceiling enforced by route logic: query
  `SELECT privacy_tier, content_text, role, created_at, source_kind, ...
   FROM messages WHERE id = ?`; if `privacy_tier > 1`, return a 403 with a
  structured envelope `{"error": "privacy_tier_ceiling",
  "message_id": "...", "tier": <n>, "ceiling": 1}`.
- Returns the full message body wrapped in
  `_evidence_excerpt.html` rendering with `content` un-truncated (no
  `EVIDENCE_EXCERPT_LIMIT` cut). htmx swap target is the existing evidence
  row, swapped via `outerHTML`.

### GET `/sessions/{session_id}/messages/{message_id}/context`

- Query parameters: `before=<int>` (default 2), `after=<int>` (default 2).
- Hard cap: `before + after <= 20`. Exceeding caps return 422.
- Status: 200, 403, 404, 422.
- Tier ceiling: max-tier carry across all returned rows. Query
  `SELECT id, role, created_at, content_text, source_kind, privacy_tier,
   sequence_index FROM messages WHERE conversation_id = (
     SELECT conversation_id FROM messages WHERE id = ?
   ) AND sequence_index BETWEEN target_seq - before AND target_seq + after
   ORDER BY sequence_index`. If any returned row has `privacy_tier > 1`,
  the *entire* response is 403 with the same structured envelope as
  `/messages/{id}` (F023).
- htmx swap target: the context panel (a `<section id="context-panel">` on
  the question page); swap mode is `innerHTML`.

### GET `/sessions/{session_id}/q/{idx}/evidence/all`

- Same loader as `/q/{idx}` minus the 3-row cap. Renders all evidence
  rows for the current target.
- Tier 1 ceiling enforced by the same logic as `/messages/{id}`: any row
  with `privacy_tier > 1` causes a 403.
- htmx swap target: the evidence section on the question page; swap mode
  is `innerHTML`.

### POST `/sessions/{session_id}/save-and-quit`

- Origin allowlist enforced.
- Behavior: no verdict commit. Any in-progress rationale text is
  discarded (per F022, option 1 — discard for CLI parity). Returns a
  redirect to `/` with a transient banner attached via flash-style
  query parameter or session-scoped state; the banner reads
  `"Saved and quit. Resume with: engram phase3 interview resume
  --session-id <uuid>"`.
- Status: 303.

### POST `/sessions/{session_id}/complete`

- Origin allowlist enforced.
- Behavior: calls `mark_session_completed(conn, session_id)`, commits,
  redirects to `/`. Auto-fired by the verdict-commit handler when
  `idx == n` (F019). There is no explicit "Complete" button on the
  question page.
- Status: 303 on success, 404 on unknown session.

### POST `/sessions/{session_id}/abandon`

- Origin allowlist enforced.
- Behavior: calls `mark_session_completed(conn, session_id,
  operator_note='abandoned via web')`, commits, redirects to `/`.
- Status: 303 on success, 404 on unknown session.

### Origin allowlist behavior

All POST routes (`/sessions`, `/sessions/{id}/q/{idx}/verdict`,
`/sessions/{id}/save-and-quit`, `/sessions/{id}/complete`,
`/sessions/{id}/abandon`) enforce:

1. The `Origin` header equals exactly `http://127.0.0.1:<port>` or
   `http://localhost:<port>` where `<port>` is the port the server was
   bound to.
2. If `Sec-Fetch-Site` is present, its value is `same-origin`.

A request that fails either check returns 403 with body
`{"error": "origin_mismatch", "expected": [...]}` and no side effects.
The check is implemented as a FastAPI dependency or middleware
attached to the POST routes — implementers should pick the path that
keeps GETs free of the check.

## Templates

All templates live at `src/engram/interview/templates/`. Jinja2 is the
template engine (declared as a `serve` extra dependency). Templates use
Jinja2's autoescape; raw HTML insertion is forbidden.

### `base.html`

- Extends: nothing (root template).
- Blocks: `title`, `head_extra`, `main`, `body_extra`.
- htmx attributes used: none on `base.html` itself; child templates use
  them.
- Key elements:
  - `<script src="/static/htmx.min.js" defer></script>` — single,
    vendored. No CDN reference reachable from any rendered page (F004).
  - `<style>` — single inline block, no external stylesheet.
  - `<div id="live-region" aria-live="polite" class="visually-hidden"></div>`
    — announces "Question K of N" on each htmx swap (F026).
  - `<div id="help-modal" hidden role="dialog" aria-modal="true"
    aria-labelledby="help-modal-title">…</div>` — help modal, hidden by
    default; bound to `?` and dismissed with `Esc` (F024). Modal content
    is the verdict-glosses table (sourced from
    `gold_label_verdict_vocabulary` at template-render time) plus the
    keyboard-shortcut table.
  - Inline `<script>` blocks:
    - Keyboard dispatcher: bare-key listener with `accesskey` fallback;
      ignores keystrokes when `document.activeElement.tagName` is `INPUT`
      or `TEXTAREA` (except `Esc`, which always closes the modal).
    - `htmx:afterSwap` listener: updates `#live-region` text and moves
      focus to `<h2 tabindex="-1">` when present.

### `index.html`

- Extends: `base.html`.
- Blocks: `title` ("Engram interview — open sessions"), `main`.
- htmx attributes: minimal — the new-session form uses a plain
  `<form method="post" action="/sessions">` (the redirect-to-question-1
  pattern from F025 means the second click hits the redirected URL, not
  the form, debouncing duplicate sessions).
- Key elements / ids:
  - `<section id="open-sessions">` listing rows
    `<a href="/sessions/{id}">{K}/{N} answered, opened {Xh} ago</a>` plus
    a `<form method="post" action="/sessions/{id}/abandon">[Abandon]</form>`
    per row.
  - `<section id="empty-corpus-banner" hidden>` containing the
    diagnostic + refresh hint. Rendered visible only when the POST
    `/sessions` re-render path sets it.
  - `<form id="new-session" method="post" action="/sessions">` with
    `<input name="n" type="number" min="1" value="10" aria-label="number
    of questions">` and `<input name="seed" type="number"
    aria-label="random seed (optional)">`.
- Accessibility: every form input has an `aria-label`; the empty-corpus
  banner uses `role="status"` so screen readers announce it.

### `question.html`

- Extends: `base.html`.
- Blocks: `title` ("Engram interview — Q{idx}/{n}"), `main`.
- htmx attributes:
  - Each verdict button has `hx-post="/sessions/{id}/q/{idx}/verdict"
    hx-swap="outerHTML" hx-target="#main"`. Single-click verdicts
    (`true`, `skip`) include a hidden `verdict` input with their value
    and an empty `rationale` field; the form submits in one round-trip.
  - Two-click verdicts (`false`, `stale`, `unsupported`, `unsure`) use
    `hx-get="/sessions/{id}/q/{idx}/rationale-form?verdict=..."` (or
    pure client-side toggling with no extra route — implementers may
    pick) to swap in the rationale textarea; the second submit is
    `hx-post="/sessions/{id}/q/{idx}/verdict"` carrying both `verdict`
    and `rationale`.
  - The "show full message" link on each evidence row uses
    `hx-get="/sessions/{id}/messages/{message_id}"` `hx-swap="outerHTML"`
    `hx-target="closest .evidence-row"`.
  - The "show all N evidence rows" disclosure uses
    `hx-get="/sessions/{id}/q/{idx}/evidence/all"` `hx-swap="innerHTML"`
    `hx-target="#evidence-section"`.
  - The "show conversation context" link uses
    `hx-get="/sessions/{id}/messages/{message_id}/context?before=2&after=2"`
    `hx-swap="innerHTML"` `hx-target="#context-panel"`.
- Key elements / ids:
  - `<main id="main">` wrapping the question content (htmx swap target).
  - `<h2 tabindex="-1">[idx/total] target_kind ...</h2>` carrying the
    header line; tabindex=-1 lets `htmx:afterSwap` move focus here.
  - `<section id="evidence-section">` rendering each evidence row via
    `_evidence_excerpt.html`.
  - `<section id="context-panel">` initially empty, populated by
    `/messages/{id}/context` swap.
  - `<div id="strata-strip">` rendering `_strata_strip.html`.
  - `<div id="verdict-row" role="group" aria-label="Verdict buttons">`
    containing buttons in order
    `[true] [false] [stale] [unsupported] [unsure] [skip]` (F028). Each
    button face shows the accesskey letter as a `<sup>` superscript.
    Each button has `aria-label` carrying the gloss verbatim from
    `gold_label_verdict_vocabulary` (F026). Verdict differentiation uses
    icon + underline + color so WCAG 1.4.1 is satisfied without
    color-only.
  - `<textarea id="rationale" name="rationale" hidden
    aria-describedby="rationale-prompt"></textarea>` — initially
    hidden; revealed by the two-click flow.
  - `<span id="rationale-prompt" hidden>` — verdict-specific prompt
    text from `RATIONALE_PROMPT_BY_VERDICT`.
  - `<form action="/sessions/{id}/save-and-quit" method="post">[Save and
    quit]</form>` — debounced via the redirect pattern.
  - `<p id="status-line">K/N answered — closing this tab is safe;
    verdicts are saved as you commit them.</p>`.

### `_evidence_excerpt.html`

- Used both as a partial inside `question.html` for the initial render
  and as the response body for `GET /messages/{id}` swaps.
- Inputs: `excerpt` (a dict with the keys `fetch_evidence_excerpts`
  returns) plus `full` (bool: when True, render `excerpt['content']`
  un-truncated).
- Key elements:
  - `<article class="evidence-row" id="evidence-{message_id}">`
    containing the date / role / source-kind / conversation-title
    header line and the (truncated or full) body.
  - `<a hx-get="/sessions/{session_id}/messages/{message_id}" ...>show
    full message</a>` link, present only when `full == False`.

### `_strata_strip.html`

- One-line footer: `"this session: identity=2 mood=1 task=1 ..."`
  rendered from a single
  `SELECT stability_class, count(*) FROM gold_labels WHERE session_id = ?
   GROUP BY 1`. No row sorting or color is required; alphabetical by
  `stability_class` is sufficient.

## Migration 011

`migrations/011_gold_label_session_targets.sql` materializes the sampled
order at session creation. The append-only trigger and the version-triple
CHECK constraint mirror migration 010's pattern.

```sql
-- 011_gold_label_session_targets.sql
-- RFC 0027 § Persistent target order. Materializes the sampled order at
-- session creation so the web UI can index into it by URL idx without
-- re-sampling on every request (F004 / F009 / F010 / F016).

CREATE TABLE gold_label_session_targets (
    session_id UUID NOT NULL
        REFERENCES gold_label_sessions(session_id) ON DELETE CASCADE,
    idx INT NOT NULL CHECK (idx >= 0),  -- 0-indexed in the table; URL is 1-indexed
    target_kind TEXT NOT NULL CHECK (target_kind IN ('claim', 'belief')),
    target_id UUID NOT NULL,
    candidate_pool_snapshot_id UUID NOT NULL,
    -- Typed version triple stamped at session creation (F010 / O002).
    -- Same shape as gold_labels: extraction triple iff target_kind=claim,
    -- consolidation triple iff target_kind=belief, request_profile_version always.
    extraction_prompt_version TEXT NULL,
    extraction_model_version TEXT NULL,
    consolidation_prompt_version TEXT NULL,
    consolidation_model_version TEXT NULL,
    request_profile_version TEXT NOT NULL,
    stability_class TEXT NOT NULL,
    conf_band TEXT NOT NULL,
    recency_band TEXT NOT NULL,
    belief_status TEXT NULL,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, idx),
    CONSTRAINT chk_session_targets_version_triple CHECK (
        (target_kind = 'claim'
            AND extraction_prompt_version IS NOT NULL
            AND extraction_model_version IS NOT NULL
            AND consolidation_prompt_version IS NULL
            AND consolidation_model_version IS NULL)
        OR
        (target_kind = 'belief'
            AND consolidation_prompt_version IS NOT NULL
            AND consolidation_model_version IS NOT NULL
            AND extraction_prompt_version IS NULL
            AND extraction_model_version IS NULL)
    )
);

CREATE INDEX idx_session_targets_session_id
    ON gold_label_session_targets (session_id);
CREATE INDEX idx_session_targets_target
    ON gold_label_session_targets (target_kind, target_id);

-- Append-only at the schema layer (mirrors gold_labels pattern from migration 010).
CREATE OR REPLACE FUNCTION fn_gold_label_session_targets_append_only()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'gold_label_session_targets is append-only; % is not allowed', TG_OP
        USING ERRCODE = 'P0001';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER gold_label_session_targets_00_append_only
    BEFORE UPDATE OR DELETE ON gold_label_session_targets
    FOR EACH ROW EXECUTE FUNCTION fn_gold_label_session_targets_append_only();
```

The `POST /sessions` route inserts one row per sampled target inside the
same transaction as `insert_session`. `run_phase3_interview_start` is
updated to do the same after `sampler.sample(n)` so a CLI-created session
is web-resumable.

### Test plan

Three tests added to `tests/test_migrations.py`:

- `test_011_session_targets_append_only` — INSERT a row; UPDATE raises
  `psycopg.errors.RaiseException` with code `P0001`; DELETE raises the
  same. The fixture uses the real-DB `conn` fixture from
  `tests/conftest.py:13-83`.
- `test_011_session_targets_version_triple_check` — INSERT a `claim` row
  with `consolidation_prompt_version` set raises a CHECK-constraint
  violation; INSERT a `belief` row with `extraction_prompt_version` set
  raises the same.
- `test_011_session_targets_pk_uniqueness` — insert two rows with the
  same `(session_id, idx)`; second raises a unique-violation error.

## CLI integration

A new subparser `phase3_interview_serve_parser` is added under the
existing `phase3 interview` subparser group in `src/engram/cli.py`:

- Args: `--host` (default `127.0.0.1`), `--port` (default `8765`).
- The `--allow-non-loopback` flag is **not** added (per F005).
- A non-loopback `--host` value (anything other than `127.0.0.1` or
  `localhost`) causes the driver to print
  `"phase3 interview serve: refusing non-loopback host (--host=...);
   v1 is loopback-only"` to stderr and `sys.exit(8)`.
- Driver function `run_phase3_interview_serve(args)`:
  1. Imports `engram.interview.web` lazily. If the import fails (FastAPI
     / Uvicorn / Jinja2 missing), prints
     `"phase3 interview serve: missing dependency. Install with:
      pip install engram[serve]"` and `sys.exit(2)`.
  2. Calls `uvicorn.run(web.app, host=args.host, port=args.port,
     workers=1)`.
- `run_phase3_interview_start` is updated to also execute a single batch
  insert into `gold_label_session_targets` after `sampler.sample(n)` so
  CLI-created sessions are web-resumable. Where the existing CLI logic
  early-returns on empty-sample (`if not sampled:`), the materialization
  step is skipped (no rows to insert). The CLI's existing
  `mark_session_completed` for the empty-sample case is preserved.
- `tests/test_interview_cli.py` is updated to expect the materialized
  rows. The CLI behavior is otherwise unchanged; render output stays
  byte-identical (validated by golden-output tests in
  `tests/test_interview_render.py`).

## Dependencies

`pyproject.toml` deltas:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8,<9",
    "ruff>=0.6,<1",
    "pyright>=1.1.380,<2",
    "engram[serve]",  # so `make typecheck` resolves engram.interview.web imports
]
serve = [
    "fastapi>=0.110,<1",
    "uvicorn>=0.30,<1",
    "jinja2>=3.1,<4",
]

[tool.setuptools.package-data]
"engram.interview" = ["templates/*.html", "templates/*", "static/*"]
```

The `dev` extra grows `"engram[serve]"` so `make typecheck` keeps passing
without a pyright exclusion. The `[tool.setuptools.package-data]` block
ships templates and `htmx.min.js` inside the wheel; without it,
`pip install engram` does not include the static assets and the route
fails at runtime.

The CLI subcommand raises an actionable `ImportError` -> `SystemExit(2)`
with message `pip install engram[serve]` if FastAPI / Uvicorn / Jinja2
imports fail (see § CLI integration above).

## Privacy and security

- **Loopback-only bind.** Default `127.0.0.1`. The driver refuses
  non-loopback `--host` with `sys.exit(8)`. No `--allow-non-loopback`
  escape clause in v1.
- **Origin allowlist on POST routes.** Every POST route enforces the
  Origin / Sec-Fetch-Site allowlist described above. Origin mismatch
  returns 403 with no side effect.
- **Sec-Fetch-Site: same-origin.** When the header is present, it must be
  `same-origin`. (Older browsers may omit it; the Origin check is the
  primary defense.)
- **Tier 1 ceiling.** `/messages/{id}`, `/messages/{id}/context`, and
  `/q/{idx}/evidence/all` enforce a hard Tier 1 ceiling in the route
  handler. `/messages/{id}/context` carries the max tier across all
  returned rows: any row with `tier > 1` causes a 403 for the entire
  response. The ENV var `ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX` named in
  RFC 0027 § Open Question O3 is reserved but unimplemented in v1.
- **Per-form CSRF tokens deferred to v1.1.** The Origin-header check is
  sufficient against the documented attack (any-tab autosubmit). The
  deferral has a documented trigger: any new mutating route added after
  v1 forces a re-evaluation of per-form tokens.
- **`gold_labels.evidence_excerpt` left NULL.** Web verdicts do not
  populate the column. Migration 010's `fn_gold_labels_carry_privacy_tier`
  carries the parent tier but does not redact the excerpt itself, so
  populating `evidence_excerpt` from a tier-N message would write a
  higher-tier excerpt into a row whose declared `privacy_tier` reflects
  the parent. v1.1 may introduce a redactor.
- **D044 / D069 invariant.** No web route may import
  `engram.consolidator.transitions`; no template may render a
  promote-belief / accept / reject / pin affordance. Mechanically
  guarded by `test_consolidator_transitions_unimportable_from_web`
  (see § Test surface).

## Process model

- **Sync `def` route handlers + threadpool dispatch.** All FastAPI route
  handlers are sync `def`. FastAPI dispatches them on its threadpool, so
  the synchronous `psycopg.Connection` calls do not block the event
  loop. `async def` would block the event loop on the first DB call and
  is forbidden in v1.
- **`uvicorn --workers 1`.** Single worker. Multiple workers complicate
  the connection-pool story without adding throughput on a single-user
  localhost surface.
- **One `psycopg.Connection` per request.** Each route opens a single
  sync connection via `engram.db.connect()` (the existing helper used by
  the CLI loop), uses it for the duration of the request, and closes it
  on exit. No connection pool in v1; the single-operator workload does
  not justify one. `connect()` is called inside the handler, not as a
  module-level singleton, so every request gets a fresh connection.

## Verdict commit flow

The verdict-button row is the load-bearing UX. The flow has two paths
depending on whether the verdict requires a rationale.

### Single-click commit (`true`, `skip`)

1. Operator clicks `[true]` (or `[skip]`).
2. The button's `hx-post` fires immediately, posting
   `{verdict: 'true', rationale: ''}` to
   `/sessions/{id}/q/{idx}/verdict`.
3. The route validates the verdict, calls
   `agent.record_verdict(session_id, target, 'true', rationale=None)`,
   commits, and returns 200 with header
   `HX-Redirect: /sessions/{id}/q/{idx + 1}` (or
   `/sessions/{id}/complete` if `idx == n`).
4. htmx follows the redirect, swapping `<main>` with the next question's
   render. The `htmx:afterSwap` handler updates `#live-region` with
   "Question K of N" and moves focus to `<h2 tabindex="-1">`.

Round-trip count: **1**. This matches the CLI's two-keystroke `t-Enter`
loop at the wire level.

### Two-click commit (`false`, `stale`, `unsupported`, `unsure`)

1. Operator clicks `[false]` (or `[stale]` / `[unsupported]` /
   `[unsure]`).
2. The button's `hx-get` (or pure client-side handler) reveals the
   `<textarea id="rationale">` below the button row, populates
   `<span id="rationale-prompt">` with
   `RATIONALE_PROMPT_BY_VERDICT[verdict]`, and focuses the textarea.
3. The operator types rationale text. Enter inside the textarea inserts
   a newline; Shift-Enter submits the form.
4. On submit, the form posts
   `{verdict: 'false', rationale: '...'}` to
   `/sessions/{id}/q/{idx}/verdict`.
5. The route validates, calls
   `agent.record_verdict(session_id, target, 'false',
    rationale='<text>')`, commits, returns the same `HX-Redirect` as the
   single-click path.

Round-trip count: **2** (one for the textarea reveal — which can be
client-side only, eliminating the round-trip; one for the commit). The
implementer may choose pure client-side reveal to reduce the wire count
to 1; either path satisfies the contract.

### htmx swap dance (numbered)

For a single-click `true` commit on `/q/{idx}` advancing to `/q/{idx+1}`:

1. Click event fires on `<button verdict="true">`.
2. htmx serializes the form (`verdict=true`, `rationale=`), POSTs to
   `/sessions/{id}/q/{idx}/verdict`.
3. Server: `agent.record_verdict(...)`; commit; build response with
   header `HX-Redirect: /sessions/{id}/q/{idx + 1}` and empty body.
4. htmx receives the response, sees `HX-Redirect`, issues a GET to
   `/sessions/{id}/q/{idx + 1}` with `HX-Request: true` so the server
   knows to return the htmx-shaped fragment (just the `<main>` block) or
   a full page.
5. Server renders `question.html` with idx+1; returns the fragment.
6. htmx swaps `<main>` (`outerHTML`); fires `htmx:afterSwap`.
7. Client `htmx:afterSwap` handler updates `#live-region` with
   "Question {idx + 1} of {n}" and moves focus to the new
   `<h2 tabindex="-1">`.

### Trigger-rejection path

If the verdict POST fails because of a `gold_labels` trigger (e.g.,
`fn_gold_labels_validate_target` rejects a deleted claim), the route:

1. Catches `GoldLabelStorageError` / `GoldLabelVerdictError`.
2. `conn.rollback()`.
3. Re-renders `question.html` with an error banner
   (`<div id="error-banner" role="alert">`) saying
   `"the target was not labeled; details: <exc.message>"`.
4. Returns 200 with `HX-Reswap: outerHTML` so the htmx flow sees the
   error rendering rather than a redirect.

The session stays open. The operator can move on (Save and quit, or pick
a different target via direct URL navigation).

## Keyboard shortcuts

The dispatcher in `base.html` listens for `keydown` events on the
document and dispatches per the table below. Bare-key presses are
ignored when `document.activeElement.tagName` is `INPUT` or `TEXTAREA`,
except `Esc` which always closes the help modal.

| Verdict / Action | Letter | Mechanism |
|------------------|--------|-----------|
| true | `t` | bare-key + `accesskey="t"` fallback |
| false | `f` | bare-key + `accesskey="f"` fallback |
| stale | `s` | bare-key + `accesskey="s"` fallback |
| unsupported | `n` | bare-key + `accesskey="n"` fallback (`u` reserved for `unsure`) |
| unsure | `u` | bare-key + `accesskey="u"` fallback |
| skip | `k` | bare-key + `accesskey="k"` fallback |
| help modal | `?` | bare-key (Shift-/) + `accesskey="?"` fallback |
| save-and-quit | `q` | bare-key + `accesskey="q"` fallback (matches CLI's `q to save and quit`) |
| close help modal / restore focus | `Esc` | `keydown` listener on document |

Resolution of letter conflicts (per F021):

- `s` keeps `stale` (matches CLI verdict glossary in
  `gold-set-interview.md`); the CLI's `q to save and quit` rebinds in
  the web to `q` (matches CLI's already-existing `q` verb at
  `cli.py:1845` in `_prompt_verdict`).
- `unsupported` rebinds from any imagined `u` to `n` (a freer letter;
  survives the `u` / `unsure` collision).
- `?` requires Shift on US keyboards but is the discoverable
  convention for "help"; the dispatcher accepts both raw `?` and
  `Shift-/` keydown.
- Enter inside the rationale textarea inserts a newline (does NOT
  submit). Shift-Enter submits the form. Enter on a focused button
  activates the button (browser default).
- The dispatcher ignores all bare-key presses when
  `document.activeElement.tagName` is `INPUT` or `TEXTAREA`, except
  `Esc` (closes modal regardless of focus).

## Test surface

All tests live under `tests/`. The `conn` fixture in
`tests/conftest.py:13-83` provides a real Postgres connection with
migrations applied (web tests do not monkeypatch storage; the
trigger-rejection banner test depends on real triggers firing).

### `tests/test_interview_web.py` (NEW)

- `test_index_renders_no_open_sessions` — GET `/` returns 200, page
  title `"Engram interview — open sessions"`, empty session list.
- `test_index_renders_open_sessions_with_progress` — fixture inserts
  a session + 3 verdicts; GET `/` shows `3/10 answered, opened ...`.
- `test_post_sessions_redirects_to_q1` — POST `/sessions` with
  `n=3, seed=4`; verifies one `gold_label_sessions` row, three
  `gold_label_session_targets` rows, redirect (303) to
  `/sessions/{id}/q/1`.
- `test_post_sessions_empty_corpus_renders_diagnostic` — fixture
  produces an empty sample; POST `/sessions` returns 200 rendering
  `index.html` with the empty-corpus diagnostic banner; either no
  session row or a session row marked `completed_at` (F029
  implementer choice).
- `test_get_question_renders` — fixture session; GET `/sessions/{id}/q/1`
  returns 200; body contains the header, summary line, evidence
  excerpts, six verdict buttons each with the expected `accesskey`
  letter and `aria-label` from `gold_label_verdict_vocabulary`.
- `test_post_verdict_true_single_click_commit` — POST
  `/sessions/{id}/q/1/verdict` with `verdict=true, rationale=`; verifies
  one `gold_labels` row with `verdict='true'` and `rationale` NULL,
  `evidence_excerpt` NULL, response header
  `HX-Redirect: /sessions/{id}/q/2` (F020).
- `test_post_verdict_skip_single_click_commit` — same shape with
  `verdict=skip`.
- `test_post_verdict_false_two_click_flow` — POST with
  `verdict=false, rationale=correct value text`; verifies
  `gold_labels.rationale = 'correct value text'`.
- `test_post_verdict_trigger_rejection_renders_banner` — fixture
  inserts a `gold_label_session_targets` row whose `target_id` will
  fail `fn_gold_labels_validate_target` (e.g., a deleted claim); POST
  verdict; verifies route catches `GoldLabelStorageError` and renders
  the same question with an error banner whose text contains
  `"target was not labeled"` (F013).
- `test_post_verdict_404_unknown_session` — POST to nonexistent
  `session_id`; 404.
- `test_post_verdict_404_out_of_range_idx` — POST to `idx=99` on a
  10-target session; 404.
- `test_post_verdict_422_unknown_verdict` — POST with `verdict=garbage`;
  422.
- `test_post_verdict_403_origin_mismatch` — POST with
  `Origin: http://evil.example`; 403 with body containing
  `"origin_mismatch"` (F006).
- `test_post_verdict_completes_session_at_n` — POST the n-th verdict;
  verifies HX-Redirect goes to `/sessions/{id}/complete` and that a
  subsequent GET on `/` shows the session as completed (F019).
- `test_get_messages_tier_1_enforced` — fixture message at
  `privacy_tier=2`; GET `/sessions/{id}/messages/{message_id}` returns
  403 with structured envelope `{"error": "privacy_tier_ceiling", ...}`
  (F008).
- `test_get_messages_context_max_tier_carry` — fixture conversation
  with one tier-2 row in the context window; GET
  `/messages/{id}/context?before=2&after=2` returns 403 (F023).
- `test_get_messages_context_caps` — GET with `before=15&after=15`
  returns 422 (cap is `before + after <= 20`).
- `test_get_evidence_all_tier_1_enforced` — same shape for
  `/q/{idx}/evidence/all`.
- `test_post_save_and_quit_discards_in_progress` — POST
  `/save-and-quit` after rendering the question; verifies no
  `gold_labels` row was committed; redirect target is `/`; banner
  carries the resume command string (F022).
- `test_post_abandon_marks_completed` — POST `/abandon`; verifies
  `gold_label_sessions.completed_at` is set and `operator_note =
  'abandoned via web'` (F025).
- `test_consolidator_transitions_unimportable_from_web` — imports
  `engram.interview.web`; iterates the module's symbols and asserts
  no symbol resolves to anything in `engram.consolidator.transitions`
  (F007).
- `test_htmx_loaded_from_static_not_cdn` — GET `/`; verifies the
  `<script>` tag points at `/static/htmx.min.js`, not `unpkg.com` or
  any external host (F004).
- `test_static_htmx_served` — GET `/static/htmx.min.js` returns 200
  with non-empty body (Content-Type
  `application/javascript`).
- `test_aria_live_region_present` — GET `/sessions/{id}/q/1`; verifies
  the response HTML contains an element with `aria-live="polite"`
  (F026).

### `tests/test_interview_render.py` (NEW)

- `test_format_header_pinned_against_cli_output` — fixture target;
  asserts `format_header` returns the exact string the CLI's existing
  `cli.py:1929-1936` block produced before extraction (golden
  output).
- `test_format_summary_line_pinned` — same shape for
  `format_summary_line`.
- `test_format_evidence_dates_pinned` — same shape for
  `format_evidence_dates`; covers both single-date and date-range
  branches plus `valid_from` / `valid_to` permutations.
- `test_format_evidence_excerpts_pinned` — same shape for
  `format_evidence_excerpts`; covers truncation at
  `EVIDENCE_EXCERPT_LIMIT` and the trailing
  `"… N more row(s) not shown"` line.
- `test_pick_question_event_predicate` — claim target produces the
  "accurate paraphrase" framing.
- `test_pick_question_belief_event_cardinality` — belief target with
  `cardinality_class='event'` produces the "Did this event happen as
  paraphrased on {ev_date}?" framing.
- `test_pick_question_belief_mood_stability` — belief target with
  `stability_class in {mood, task}` produces the "Was this true around
  {ev_date}?" framing.
- `test_pick_question_belief_default` — falls through to the
  "currently true" framing.
- `test_pick_question_uses_utc_now` — explicit UTC `now` keyword
  produces stable `ev_date` regardless of the host machine's local
  timezone (F015). Uses `freezegun` or a `now=...` explicit keyword.
- `test_rationale_prompt_for_verdicts` — every value in
  `VERDICT_VALID` produces the expected prompt (or `None` for `true` /
  `skip`).

### `tests/test_migrations.py` (extend)

- `test_011_session_targets_append_only` — INSERT, then UPDATE / DELETE
  both raise `P0001`.
- `test_011_session_targets_version_triple_check` — claim row with
  consolidation columns set raises CHECK; belief row with extraction
  columns set raises CHECK.
- `test_011_session_targets_pk_uniqueness` — duplicate `(session_id,
  idx)` raises unique-violation.

### `tests/test_interview_cli.py` (extend)

- `test_phase3_interview_start_writes_session_targets` — running
  `run_phase3_interview_start` (non-interactive) inserts one row per
  sampled target into `gold_label_session_targets` (this is the
  implicit CLI behavior change called out under § Risks).
- Existing CLI tests must continue to pass byte-for-byte against the
  refactored `cli.py` (validated by the golden-output tests in
  `test_interview_render.py`).

## Acceptance criteria (Tier 0 smoke)

These criteria define the Tier 0 smoke gate the implementation must
pass. Each is testable; the tests under § Test surface map to these
criteria.

- `engram phase3 interview serve` boots on `127.0.0.1:8765`, refuses
  non-loopback bind with `sys.exit(8)` (no escape clause in v1).
- The index page lists open sessions with progress; the new-session
  form creates a session, samples `n` targets, materializes the order
  in `gold_label_session_targets`, and redirects to `/q/1`.
- Verdict commit round-trips through the existing `gold_labels`
  triggers (`fn_gold_labels_append_only`,
  `fn_gold_labels_validate_target`,
  `fn_gold_labels_carry_privacy_tier`).
- Trigger rejections render an inline error banner; the session stays
  open.
- Non-Origin-allowlisted POSTs return 403.
- `/messages/{id}` and `/messages/{id}/context` reject Tier 2+ rows
  with 403.
- `/static/htmx.min.js` is served from the wheel; no CDN reference is
  reachable from any rendered page.
- A web import-graph test verifies `engram.consolidator.transitions`
  is unreachable from `engram.interview.web` (D044 / D069).

## Implementation sequencing

A suggested build order (an implementation agent may re-order if a
dependency graph allows; the spec only mandates the contract, not the
order):

1. **Migration 011 + extend `test_migrations.py`.** Land the schema
   first so subsequent steps can rely on the table existing.
2. **`render.py` extraction with golden-output tests** pinning the
   current CLI behavior. Verifies "no behavior change in the CLI"
   before any web code lands.
3. **Refactor `cli.py`** to import from `render.py`. Delete the
   underscore-prefixed copies. Existing CLI tests continue to pass.
4. **Update `run_phase3_interview_start`** to write
   `gold_label_session_targets`. Add the test exercising this
   materialization.
5. **FastAPI app skeleton** (`web.py` with `app = FastAPI()`, route
   stubs returning 501) + first `tests/test_interview_web.py` test
   verifying the app boots.
6. **`base.html` + `static/htmx.min.js` + `index.html`.** Static asset
   serving and the open-sessions list.
7. **POST `/sessions` + GET `/sessions/{id}`** routes. Includes the
   empty-corpus diagnostic path.
8. **`question.html` + GET `/sessions/{id}/q/{idx}`.** Includes
   `_evidence_excerpt.html` and `_strata_strip.html` partials.
9. **POST `/sessions/{id}/q/{idx}/verdict`** with single-click and
   two-click flows. Trigger-rejection banner.
10. **`/messages/{id}` + `/messages/{id}/context` +
    `/q/{idx}/evidence/all`** routes with Tier 1 enforcement.
11. **Origin allowlist middleware** attached to all POST routes.
12. **`/save-and-quit` + `/complete` + `/abandon`** routes.
13. **Help modal + keyboard dispatcher** in `base.html`.
14. **`aria-live` region + focus management** in `base.html`.
15. **CLI subparser + driver** (`run_phase3_interview_serve`).
16. **`tests/test_interview_web.py`** completes the suite; verify Tier 0
    smoke gate.

## Risks and mitigations

These risks travel forward from the synthesis to the implementation
phase.

- **The forward-compat path to RFC 0022 is asserted, not engineered.**
  The synthesis commits this spec to migrating to `engramd` when
  `engramd` lands, but the migration plan is one paragraph. If RFC
  0022's interview endpoint shape diverges from what
  `engram.interview.{agent, sampler, storage}` exposes today (e.g., it
  gates verdict-write on a request schema this spec cannot satisfy
  without UI rework), the migration is more than mechanical.
  *Mitigation:* when RFC 0022 reaches synthesis, the RFC 0022 reviewer
  must explicitly check this spec's call sites against the proposed
  endpoint shape and flag any gap. This spec assumes the call shape
  stays close to `record_verdict(session_id, target, verdict,
  rationale)`.

- **Origin-header allowlist may be insufficient against a determined
  attacker.** F006 was about any-tab autosubmit, which the Origin check
  handles. But a malicious browser extension (or a Chrome flag like
  `--disable-web-security` set for unrelated reasons) can suppress or
  rewrite the `Origin` header. The deferral of per-form CSRF tokens to
  v1.1 is acceptable for a single-user local UX but should not be
  transferred without scrutiny to any future multi-user surface.

- **The "frozen at session creation" semantics for migration 011
  conflict with the operator's intuition that `--rebuild` reflows
  everything.** A session created against extraction prompt v1 stays
  bound to v1 even if the operator runs `engram phase3 re-extract`
  between q1 and q5. The synthesis chose this for replay determinism
  (RFC 0017 discipline), but operators may experience it as "the UI
  is showing stale beliefs." *Mitigation:* the question page's header
  must display the version triple the session was created against, so
  the operator can see the freeze and start a new session if they
  want fresh extraction. The implementer must add this to the header
  rendering on `question.html` (it is *not* covered by the `format_header`
  signature above, which renders the existing CLI header line — the
  web template adds the version-triple line explicitly).

- **Single-click commit for `true` and `skip` makes those verdicts the
  path of least resistance.** F020 closed the throughput gap, but the
  asymmetry creates a small bias toward those verdicts when the
  operator is fatigued at q40 of a 50-question session. The risk is
  documented but not designed against; if observed in practice
  (verdict distributions skewing toward `true` / `skip` in web sessions
  vs CLI sessions), v1.1 may add a confirmation gesture.

- **`/messages/{id}/context` max-tier-carry is enforced by route
  logic, not by trigger.** If the route is bypassed (e.g., by a future
  MCP transport that calls the same handler layer), the carry rule may
  not transfer. RFC 0022 plans to handle privacy-tier carry on
  `/v1/evidence/{message_id}` in HTTP, holding MCP exposure until the
  Phase 5 snapshot renderer owns redaction; this spec's tier ceiling
  needs to inherit that posture when the migration to `engramd`
  happens.

- **The render extraction may break golden-output tests on the first
  run.** F003 + F015 + F027 together require touching every line of
  the CLI rendering surface. A naive lift-and-shift will produce
  subtle changes (timezone normalization for `pick_question`,
  predicate-doc append ordering, `[Conversation: ...]` vs `[<title>]`
  formatting). The implementer must run the existing
  `tests/test_interview_cli.py` against the refactored CLI and
  reconcile any drift before promotion. The risk is that "no behavior
  change" is asserted but discovered to require small CLI output
  changes during implementation.

- **Migration 011 ships with the v1 CLI as well, which is an implicit
  CLI behavior change.** The CLI loop currently materializes the
  sampled order in memory; the synthesis requires the CLI to also
  write to `gold_label_session_targets` so CLI-started sessions are
  web-resumable. This is a small but real behavior change that the
  RFC originally framed as web-only. The implementer must update
  `tests/test_interview_cli.py` to expect the materialized rows.

- **htmx swap state and screen reader announcement are coupled.** The
  `htmx:afterSwap` listener that updates `#live-region` and moves
  focus must fire reliably across all swap modes (`outerHTML`,
  `innerHTML`, redirects). Implementers should test the screen-reader
  announcement explicitly with VoiceOver / NVDA / Orca; the
  `test_aria_live_region_present` test only verifies the element
  exists in the rendered HTML, not that the announcement fires.

- **Connection lifecycle on slow Postgres.** Each route opens a fresh
  `psycopg.Connection` via `connect()`. On a slow Postgres this can add
  measurable latency per request. v1 accepts the cost (the workload is
  single-operator); if measured latency is a problem in practice,
  v1.1 may introduce a per-process connection pool. The risk is
  recorded but not addressed in v1.
