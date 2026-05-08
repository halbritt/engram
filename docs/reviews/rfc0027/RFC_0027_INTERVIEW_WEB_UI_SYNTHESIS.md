# RFC 0027 Interview Web UI Synthesis
author: synthesizer-claude-opus-001

Status: synthesis
Date: 2026-05-08
RFC refs: RFC-0027, RFC-0021, RFC-0022, RFC-0017, RFC-0018, RFC-0025
Decision refs: D016, D020, D044, D052, D069, D074, D077, D078, D079, **D080** (proposed)
Phase refs: PHASE-0003-FOLLOWON

## Findings outcome

| ID  | Outcome  | Reason |
|-----|----------|--------|
| F001 | accepted | The cited `striatum serve` precedent and "RFC 0012 § Local HTTP service" are fictional. RFC text must replace both with RFC 0022 / `engramd` (D020) and own the exit-8 contract directly rather than borrowing it; spec-time citation fix. |
| F002 | accepted_with_modification | RFC 0022 is `proposal` / `Implementation: none` — the surface it would collide with does not exist (no `src/engram/api/`, no `engramd` script, no FastAPI in `pyproject.toml`). The collision is on paper. RFC 0027 keeps a separate FastAPI app as v1 but must add a § Relationship-to-RFC-0022 paragraph committing to a forward-compat migration: routes call `engram.interview.{agent,sampler,storage}` directly today; when `engramd` lands, those calls move to `engramd`'s interview HTTP endpoints (RFC 0022 lines 151-159) and the web app becomes a Jinja layer mounted on `engramd`'s ASGI tree. RFC 0022 Open Question 9 ("does engramd serve the web UI's static bundle?") is resolved in favor of "yes, eventually, but not yet." |
| F003 | accepted | The render-extraction surface is wider than the four named exports. Spec freezes the full list (see § `render.py` API below) including `_VERDICT_PROMPT`, `_VERDICT_ALIAS`, `_VERDICT_VALID`, `_RATIONALE_PROMPT_BY_VERDICT`, `_EVIDENCE_EXCERPT_LIMIT`, `_EVIDENCE_ROWS_SHOWN`, `_print_evidence_excerpts` (renamed `format_evidence_excerpts`), the header builder, the predicate-doc append, and the valid-from formatter. CLI is refactored to import from `render`; "no behavior change in the CLI" is verified by golden-output tests. |
| F004 | accepted | CDN reference is removed from § Templates and § Open Questions. v1 contract is single `<script src="/static/htmx.min.js">`, vendored under `src/engram/interview/static/htmx.min.js`. Open Question O2 closes. |
| F005 | accepted | `--allow-non-loopback` is dropped from v1 entirely. v1 ships loopback-only with no auth and no escape clause. If a future operator needs non-loopback, that lands as a follow-on RFC paired with token auth (RFC 0022 Open Question 7's roadmap). |
| F006 | accepted | "Localhost is single-user" is wrong threat-modeling for browsers. v1 ships an Origin-header allowlist (`http://127.0.0.1:<port>` and `http://localhost:<port>`) plus `Sec-Fetch-Site: same-origin` requirement on all POST routes; verdict / complete / save-and-quit / abandon / sessions-create reject with 403 on mismatch. CSRF token is deferred to v1.1 only because Origin-check is sufficient against the documented attack (any-tab autosubmit) — the deferral is conditional on an enforcement test landing in v1. |
| F007 | accepted | Spec adds an explicit invariant block: "no web route may import `engram.consolidator.transitions`; no template may render a promote-belief / accept / reject / pin affordance; D044 / D069 hold on the web surface as on the CLI." Mechanically guarded by a test that imports `engram.interview.web` and asserts no symbol from `engram.consolidator.transitions` is reachable. |
| F008 | accepted | Hard-code Tier 1 ceiling on `GET /sessions/{session_id}/messages/{message_id}` in v1. A higher-tier env var ceiling is deferred. The ceiling is enforced by the route, not by template prose: parent message tier > 1 returns 403 with a structured envelope. Open Question O3 resolves to "hard-coded Tier 1; env var deferred to v1.1." |
| F009 | accepted | Migration `011_gold_label_session_targets.sql` (see § Migration plan below) pins PK as `(session_id, idx)`, `idx` is `INT NOT NULL CHECK (idx >= 0)` (0-indexed in the table; URL exposes `idx` 1-indexed via `q/{idx}` for parity with the CLI's `[1/n]` framing — the route translates `url_idx - 1` on entry), stamps `candidate_pool_snapshot_id`, the typed version triple at session creation, and `request_profile_version` on every row. Append-only by `fn_gold_label_session_targets_append_only` BEFORE UPDATE OR DELETE trigger, naming-prefixed `00_` to match the migration 010 trigger ordering. |
| F010 | accepted_with_modification | Materialized order in migration 011 *wins* on resume — the candidate pool is frozen at session creation. The session table carries `candidate_pool_snapshot_id`, `extraction_prompt_version` / `extraction_model_version` / `consolidation_prompt_version` / `consolidation_model_version` / `request_profile_version` so a session resumed three days later replays against the pool that existed at session creation, regardless of corpus drift. If the operator wants a fresh pool, they start a new session. This makes "freeze stale" the contract; "re-sample drift" is rejected. RFC 0021's `candidate_pool_snapshot_id` discipline is preserved; the per-row stamp on `gold_labels` continues to come from the session's frozen snapshot id rather than the sampler's per-call generation. |
| F011 | accepted_with_modification | `--include-superseded` and `--ignore-cooldown` are CLI-only in v1 web. The new-session form on `index.html` exposes only `n` and `seed`. Adversarial-sweep mode requires the operator to drop to the CLI (`engram phase3 interview start --include-superseded ...`); rationale is RFC 0021's framing of `--include-superseded` as deliberate. v1.1 may add an `[Advanced]` collapse with a consent banner; v1 omits. |
| F012 | accepted | `pyproject.toml` gains `[project.optional-dependencies] serve = ["fastapi>=0.110,<1", "uvicorn>=0.30,<1", "jinja2>=3.1,<4"]`. The `dev` extra grows `"engram[serve]"` so `make typecheck` keeps passing without a pyright exclusion. `[tool.setuptools.package-data]` block ships templates and `htmx.min.js` inside the wheel. CLI subcommand raises an actionable `pip install engram[serve]` error if FastAPI / Uvicorn / Jinja2 imports fail. |
| F013 | accepted | Test surface is enumerated, not deferred (see § Test surface below). `tests/test_interview_web.py` exercises every route; the trigger-rejection banner test uses the existing real-DB `conn` fixture from `tests/conftest.py:13-83` rather than monkeypatching `record_verdict`. |
| F014 | accepted | Sync `def` route handlers + `uvicorn --workers 1` is the v1 contract. `psycopg.Connection` is sync; `async def` would block the event loop. Open Question O6 closes. |
| F015 | accepted | `pick_question` gains an explicit `now: datetime | None = None` keyword (defaults to `datetime.now(timezone.utc)`); `evidence_max` is rendered via UTC `.date().isoformat()` so CLI and web verdict on the same belief produce identical `ev_date` strings. |
| F016 | accepted | RFC text revision: Option A description drops "deterministic" and reads "re-sample with order that drifts as you label" (matches sampler.py:286-302 + 341-342 behavior). Recommendation flips from "chosen" to "forced" — Option B is the only correctness-preserving option. Migration 011 ships in v1, not as a follow-up. |
| F017 | accepted | Web verdicts leave `gold_labels.evidence_excerpt` NULL in v1, matching CLI (cli.py:1977). The "show full message" surface is read-only and never round-trips through `record_verdict`. Rationale: migration 010's `fn_gold_labels_carry_privacy_tier` carries the parent tier but does not redact the excerpt itself, so populating `evidence_excerpt` from a privacy-tier-N message would write a higher-tier excerpt into a row whose `privacy_tier` reflects the parent — the privacy carry is honest only if `evidence_excerpt` is NULL or comes from a redaction-aware source. v1.1 may introduce a redactor. |
| F018 | accepted_with_modification | Coverage dashboard (`/coverage`) is deferred to v1.1, but a small inline strata strip ships in v1 on `/sessions/{id}/q/{idx}`: one `SELECT stability_class, count(*) FROM gold_labels WHERE session_id = ? GROUP BY 1` rendered as a footer line. No new schema, no new route. This honors the §Background promise of friction-source 3 without committing the dashboard surface. |
| F019 | accepted | `/complete` semantics: auto-redirect after the final verdict (option A — implicit). Worked example already implies this. There is no explicit "Complete" button on the question page; the verdict-commit handler issues `HX-Redirect` to `/sessions/{id}/complete` if `idx == n`, and `/complete` calls `mark_session_completed` and redirects to `/`. Save-and-quit remains a separate explicit button. |
| F020 | accepted | Single-click commit for `true` and `skip`: those buttons POST verdict + empty rationale in a single htmx round-trip. `false` / `stale` / `unsupported` / `unsure` swap in the rationale textarea and require Submit; the rationale-required path keeps the existing flow. The two single-click verdicts live at opposite ends of the row (per F028); the four rationale-required verdicts are in the middle. |
| F021 | accepted | Spec adds an explicit binding table (see § Verdict keyboard shortcuts), an `accesskey`-plus-bare-key dispatcher in `base.html` that ignores keystrokes when `<input>` / `<textarea>` is focused, and a documented Enter-vs-Shift-Enter contract in the rationale textarea (Enter = newline; Shift-Enter = submit). |
| F022 | accepted | Save-and-quit semantics: option (1) — discard the in-progress verdict for CLI parity. The route returns the resume command string `engram phase3 interview resume --session-id <uuid>` in the response banner. `/q/{idx}` uses `hx-push-url="true"` so back/forward and bookmarks work. Status line on the question page reads "K/N answered — closing this tab is safe; verdicts are saved as you commit them." |
| F023 | accepted_with_modification | `GET /sessions/{session_id}/messages/{message_id}/context?before=N&after=M` ships in v1 with hard caps `N + M <= 20` and the same hard-coded Tier 1 ceiling from F008 applied as the *max* across all returned rows (matching RFC 0021's multi-source carry rule). The 3-row `_EVIDENCE_ROWS_SHOWN` cap on the question page becomes a "show all N evidence rows" disclosure that hits an additional route `GET /sessions/{session_id}/q/{idx}/evidence/all` (Tier 1 ceiling); the CLI cap stays at 3 for backward parity. |
| F024 | accepted | `?` opens a help modal listing keyboard shortcuts and verdict glosses sourced verbatim from `gold_label_verdict_vocabulary` rows (single source of truth). `Esc` closes the modal and restores focus to the previously focused element. Verdict glosses also render under each verdict button on the question page (no need to open the modal in the common case). |
| F025 | accepted | `POST /sessions/{session_id}/abandon` is added (calls `mark_session_completed` with `operator_note='abandoned via web'`). Index page lists open sessions with progress (`3/10 answered, opened 2h ago`) computed via a single `LEFT JOIN gold_labels ON session_id` query. New-session form is debounced via Origin-checked POST + redirect-to-question-1 (a second submit hits the redirected URL, not the form). Index page title is `Engram interview — open sessions`. |
| F026 | accepted | `aria-live="polite"` live region in `base.html` announces "Question K of N" on each htmx swap. `htmx:afterSwap` listener moves focus to `<h2 tabindex="-1">` on the question page. Verdict buttons get `aria-label` carrying the gloss verbatim from `gold_label_verdict_vocabulary`. Rationale textarea gets `aria-describedby` pointing at the verdict-specific prompt span. Verdict differentiation uses icon + underline + color (WCAG 1.4.1 satisfied without color-only). |
| F027 | accepted | Worked example is reconciled with actual CLI output: the `[ ]` glyph is dropped, the `Conversation:` prefix is dropped (CLI prints `[<title>]` bare), and the example title is replaced with a plausible ChatGPT title (`"rust ownership question"`). Drift between worked example and CLI render path is treated as evidence the spec is not ready to promote until reconciled. |
| F028 | accepted | Verdict button row order in v1 is `[true]  [false]  [stale]  [unsupported]  [unsure]  [skip]` with `true` at the leftmost end and `skip` at the rightmost end (the two single-click commits are at the extremes per F020). Each button face shows the accesskey letter as a small superscript (`<sup>t</sup>` etc.) so operators can learn the bindings without consulting `?`. |
| F029 | accepted | When `sampler.sample(n)` returns `[]` on `POST /sessions`, the route does *not* create the session: it re-renders `index.html` with the CLI's diagnostic verbatim ("no targets matched (empty corpus, all on cooldown, or current_beliefs not refreshed)") and the `engram phase4 refresh-current-beliefs` hint. New operators see the same fix path as in the CLI. |

## Open decisions

### O001 — Does RFC 0027 stand alone, fold into RFC 0022, or front RFC 0022's API?
- Option A — RFC 0027 stands alone as a separate FastAPI app under `src/engram/interview/web.py`, with explicit forward-compat to RFC 0022 (when `engramd` lands, web routes migrate to call `engramd`'s interview endpoints).
- Option B — RFC 0027 is rejected; web UI defers entirely to RFC 0022 acceptance + implementation.
- Recommended: **A**.
- Rationale: RFC 0022 is `proposal` / `Implementation: none`. Its acceptance is gated on Phase 5 sequencing (it brings forward MCP serving) and has open-question debt (auth roadmap, process isolation, transport priority). RFC 0027 solves a Phase-3-follow-on operator pain (50-question sessions in 30 minutes) that does not need to wait on Phase-5-prelude server work. Standing up a separate FastAPI app under `engram.interview.web` adds ~200 lines on top of helpers that already exist; the surface is small and the migration path to RFC 0022 is mechanical (route handlers go from calling `record_verdict` directly to POSTing `engramd`'s interview HTTP endpoint, which RFC 0022 already specifies). The risk of "two surfaces forever" is mitigated by writing the migration plan into RFC 0027 explicitly. The alternative — wait for RFC 0022 — sacrifices a load-bearing operator UX gain on a sequencing bet.

### O002 — Migration 011 schema: PK + version-triple stamping
- Option A — `(session_id, idx)` PK with no version-triple columns; sample's snapshot_id only.
- Option B — `(session_id, idx)` PK with `candidate_pool_snapshot_id` + full typed version triple stamped at session creation (per F009 + F010).
- Recommended: **B**.
- Rationale: Codex F005 + Claude F009 + F010 converge on the same point — without the version triple stamped at session creation, a re-extraction between q1 and q5 (RFC 0017) lets the question render against a freshly re-versioned belief that the operator already labeled at q1, drifting away from the immutable `candidate_pool_snapshot_id` discipline. Stamping the triple on the session-targets row (not just on the per-verdict `gold_labels` row) is the only way to keep "the order frozen at session creation" semantically meaningful when re-extraction lands between question renders.

### O003 — CSRF threat-modeling stance
- Option A — No CSRF protection; rely on "single-user localhost."
- Option B — Origin / Sec-Fetch-Site allowlist on POST routes; per-form token deferred.
- Option C — Per-form CSRF token; Origin check as belt-and-suspenders.
- Recommended: **B**.
- Rationale: Claude F006 is correct that any tab can drive forms at `127.0.0.1:8765`; the "single user" framing is a process-of-the-machine claim that does not extend to the browser as a multi-tenant context. Origin-header check is sufficient against the documented attack (autosubmit form from another tab) because the attacking page's `Origin` is its own origin, not `127.0.0.1:<port>`. Per-form tokens are belt-and-suspenders that v1 can defer; the deferral becomes a v1.1 follow-up with a concrete trigger (any new mutating route added after v1).

### O004 — Sync `def` vs `async def` route handlers
- Option A — `async def` handlers (FastAPI default).
- Option B — Sync `def` handlers + threadpool dispatch + `uvicorn --workers 1`.
- Recommended: **B**.
- Rationale: Every `engram.interview.{storage, sampler, agent}` helper is sync `psycopg`. `async def` handlers would block the event loop on the first DB call. Codex F009 and Claude F014 agree. `--workers 1` is the canonical invocation for a single-operator localhost surface; multiple workers complicate the connection-pool story without adding throughput.

### O005 — Inline coverage strip on `/q/{idx}` in v1, vs deferred
- Option A — Strip ships in v1 (one extra `SELECT ... GROUP BY stability_class`).
- Option B — All coverage UX deferred to v1.1.
- Recommended: **A**.
- Rationale: Gemini F009 + Codex F010 both flag the §Background overpromise: friction-source 3 is one of three load-bearing arguments for the web UI's existence. Deferring all in-session strata feedback means v1 only fixes 2/3 of the stated problems — and the existing `engram phase3 interview coverage` already covers the dashboard surface. The strip is one query per render (cheap on a local Postgres) and one footer line; the dashboard route stays deferred.

## Recommendation

**revise-rfc**

RFC 0027 is the right idea — a thin Jinja+htmx UI surface over the existing `engram.interview` helpers is independently valuable for Phase 3 follow-on, and it does not need to wait on RFC 0022's Phase-5-prelude server work. But the RFC-as-written has two load-bearing problems that block promotion: (1) it cites a non-existent `striatum serve` precedent and the wrong RFC 0012 section as anchors for its localhost-only posture (F001), and (2) it ignores RFC 0022's interview endpoint surface entirely, even though RFC 0022 explicitly proposes those endpoints and warns against parallel-track problems (F002). The collision is currently theoretical — RFC 0022 is `proposal` with `Implementation: none`, no `engramd` binary, no `src/engram/api/`, no FastAPI in `pyproject.toml` — so RFC 0027 can stand as a separate FastAPI app today, but only if it commits in writing to a forward-compat path: when `engramd` lands, the web routes migrate from calling `engram.interview.{agent,sampler,storage}` directly to calling `engramd`'s interview HTTP endpoints, and the FastAPI app becomes a Jinja layer mounted on `engramd`'s ASGI tree.

The 27 non-blocking findings are concrete edits — `render.py` extraction surface, migration 011 schema, CSRF posture, privacy-tier ceiling, keyboard-shortcut dispatch, single-click vs two-click verdict commit, accessibility, worked-example reconciliation, empty-corpus UX. Most have a clear majority signal across the three reviews. Spec deltas below pin every choice. Promotion path: synthesis-accepted deltas land in the RFC 0027 text; spec lands at `docs/specs/0027-interview-web-ui-spec.md`; RFC 0027 moves to `promoted`; D080 records the project decision; BUILD_PHASES gains a Phase 3 follow-on web-UI line under the existing gold-set entry.

## Spec deltas

### Routes

| Verb | Path | Purpose | HX-Swap |
|------|------|---------|---------|
| GET | `/` | Open-session list (with progress: `K/N answered, opened Xh ago`) and "New session" form (`n`, `seed` only — no superseded / cooldown checkboxes per F011). Page title `Engram interview — open sessions`. | full page |
| POST | `/sessions` | `insert_session` + `sampler.sample(n)`; if sampler returns `[]`, do NOT create session — re-render `index.html` with empty-corpus diagnostic + refresh hint (F029). Otherwise insert sampled order into `gold_label_session_targets`, redirect to `/sessions/{id}/q/1`. Origin allowlist enforced. | redirect |
| GET | `/sessions/{session_id}` | Session-level summary; redirect to current target's `q/{idx}` if any unanswered remain, else redirect to `/`. | redirect |
| GET | `/sessions/{session_id}/q/{idx}` | Render the `idx`-th sampled target (URL `idx` is 1-indexed; table `idx` is 0-indexed; route translates `url_idx - 1`): header, predicate gloss, evidence excerpts (3-row cap with "show all N rows" disclosure), question, six verdict buttons with glosses, rationale textarea (auto-shown only on `false`/`stale`/`unsupported`/`unsure`), inline strata strip footer, Save-and-quit button. `hx-push-url="true"`. | full page on direct GET; `outerHTML` swap of `<main>` on htmx swap from a verdict commit |
| POST | `/sessions/{session_id}/q/{idx}/verdict` | `agent.record_verdict(session_id, target, verdict, rationale)`. On `true` / `skip`: rationale defaults to NULL; single round-trip. On `false` / `stale` / `unsupported` / `unsure`: rationale required (or empty string for `unsure`); two round-trips. On commit: `HX-Redirect` to next idx, or to `/sessions/{id}/complete` if `idx == n`. Origin allowlist enforced. | HX-Redirect |
| GET | `/sessions/{session_id}/messages/{message_id}` | Full message body for one evidence row. **Tier 1 enforced** (parent message tier > 1 returns 403). | `outerHTML` swap of evidence row |
| GET | `/sessions/{session_id}/messages/{message_id}/context?before=N&after=M` | Cited message + N predecessors + M successors from same `conversation_id`. Hard cap `N + M <= 20`. **Max-tier carry**: if any returned row has tier > 1, the entire response is 403 (F023). | `innerHTML` swap of context panel |
| GET | `/sessions/{session_id}/q/{idx}/evidence/all` | All evidence rows for the current target (no 3-row cap). Tier 1 enforced. | `innerHTML` swap of evidence section |
| POST | `/sessions/{session_id}/save-and-quit` | No verdict commit; in-progress rationale discarded for CLI parity (F022). Returns banner with resume command string `engram phase3 interview resume --session-id <uuid>`; redirects to `/`. Origin allowlist enforced. | redirect |
| POST | `/sessions/{session_id}/complete` | `mark_session_completed`; redirects to `/`. Auto-fired by verdict-commit handler when `idx == n` (F019); no explicit Complete button. Origin allowlist enforced. | redirect |
| POST | `/sessions/{session_id}/abandon` | Calls `mark_session_completed(operator_note='abandoned via web')`; redirects to `/`. Origin allowlist enforced. | redirect |

V1 explicitly does not expose `export`, `history`, `/coverage` (dashboard), or `enable-active-learning` as web routes. Those stay CLI-only until v1.1.

### Templates

`src/engram/interview/templates/`:

- `base.html` — page chrome, single inline `<style>`, single `<script src="/static/htmx.min.js">` (vendored, no CDN per F004), inline `<script>` keyboard dispatcher (bare-key + `accesskey` fallback, ignores when `<input>`/`<textarea>` focused), `aria-live="polite"` live region, `htmx:afterSwap` focus-anchor handler, help modal markup (hidden by default; bound to `?` and dismissed with `Esc`).
- `index.html` — open-session list with progress columns and per-row `[Abandon]` link; new-session form (`n` and `seed` only); empty-corpus diagnostic banner slot; page title `Engram interview — open sessions`. Extends `base.html`.
- `question.html` — header line, summary line with predicate-doc append, evidence-dates / valid-from line, evidence excerpts section (3-row cap with "show all N" disclosure), evidence-context panel (initially empty; populated by htmx swap from `/messages/{id}/context`), question line, six verdict buttons in row `[true] [false] [stale] [unsupported] [unsure] [skip]` with `aria-label` carrying the gloss and `<sup>` accesskey letter on the button face (F028), rationale textarea (initially `display:none`; revealed by htmx swap when the operator clicks `false`/`stale`/`unsupported`/`unsure`), Save-and-quit button, status-line "K/N answered — closing this tab is safe", inline strata strip footer (F018). Extends `base.html`.
- `_evidence_excerpt.html` — partial for a single evidence row; reused on full-render and on htmx swap from `/messages/{id}/context`.
- `_strata_strip.html` — partial for the inline strata footer; one `SELECT stability_class, count(*)` rendered as a single line.

### `src/engram/interview/render.py` API

```python
"""Shared rendering helpers for CLI and web (RFC 0027)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import psycopg

from engram.interview.sampler import SampledTarget


# Verdict vocabulary (moved verbatim from cli.py).
VERDICT_PROMPT: str = "verdict [t/f/stale/unsupported/unsure/skip] (q to save and quit) > "
VERDICT_ALIAS: dict[str, str] = {"t": "true", "f": "false", "true": "true", "false": "false"}
VERDICT_VALID: frozenset[str] = frozenset(
    {"true", "false", "stale", "unsupported", "unsure", "skip"}
)
RATIONALE_PROMPT_BY_VERDICT: dict[str, str] = {
    "false": "correct value > ",
    "stale": "when did it change? > ",
    "unsupported": "what's missing from the evidence? > ",
    "unsure": "note (Enter to skip) > ",
}

# Evidence layout caps (moved verbatim from cli.py).
EVIDENCE_EXCERPT_LIMIT: int = 280
EVIDENCE_ROWS_SHOWN: int = 3


def fetch_evidence_excerpts(
    conn: psycopg.Connection, evidence_ids: list[str]
) -> list[dict[str, Any]]:
    """Fetch up to EVIDENCE_ROWS_SHOWN messages by id, in chronological order."""

def fetch_target_display(
    conn: psycopg.Connection, target: SampledTarget
) -> dict[str, Any]:
    """Pull operator-readable summary plus evidence excerpts for a target."""

def pick_question(
    target: SampledTarget,
    display: dict[str, Any],
    *,
    now: datetime | None = None,
) -> str:
    """Choose a question framing. ``now`` defaults to ``datetime.now(timezone.utc)``;
    ``evidence_max`` is rendered via UTC ``.date().isoformat()`` (F015)."""

def rationale_prompt_for(verdict: str) -> str | None:
    """Verdict-specific rationale prompt; returns None for ``true``/``skip``."""

def format_header(target: SampledTarget, idx: int, total: int) -> str:
    """Render the ``[idx/total] target_kind target_id stability= conf= ...`` header
    line (moved verbatim from cli.py:1929-1936)."""

def format_summary_line(display: dict[str, Any]) -> str:
    """Render summary + predicate-doc append (moved from cli.py:1937-1941)."""

def format_evidence_dates(display: dict[str, Any]) -> str | None:
    """Render evidence-dates / valid-from suffix line (moved from cli.py:1942-1961).
    Returns None when display has no evidence dates to render."""

def format_evidence_excerpts(
    excerpts: list[dict[str, Any]], total: int
) -> list[str]:
    """Return the chronological evidence-row text lines (moved from
    cli.py:1711-1725's ``_print_evidence_excerpts``). Caller decides whether to
    print or render. The CLI joins with newlines; the web template iterates rows
    and renders each as ``_evidence_excerpt.html``."""
```

`cli.py` re-imports the verdict vocabulary and helper functions from `engram.interview.render`; the underscore-prefixed copies in `cli.py` are deleted. `tests/test_interview_cli.py` adds a golden-output test pinning the rendered text to its current shape, so the extraction is verified to be no-behavior-change.

### Migration plan

`migrations/011_gold_label_session_targets.sql`:

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

The `POST /sessions` route inserts one row per sampled target inside the same transaction as `insert_session`. The CLI loop is updated to also write the materialized order so a session created via the CLI is resumable from the web UI; this is a single batch-insert added to `run_phase3_interview_start`.

### `pyproject.toml` deltas

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

CLI subcommand `engram phase3 interview serve` raises an actionable `ImportError` re-raised as `SystemExit(2)` with message `pip install engram[serve]` if FastAPI / Uvicorn / Jinja2 imports fail.

### Test surface

`tests/test_interview_web.py` (new):

- `test_index_renders_no_open_sessions` — GET `/` returns 200, page title, empty session list.
- `test_index_renders_open_sessions_with_progress` — fixture inserts a session + 3 verdicts; GET `/` shows `3/10 answered, opened ...`.
- `test_post_sessions_redirects_to_q1` — POST `/sessions` with `n=3, seed=4` against the real-DB `conn` fixture; verifies session row, 3 `gold_label_session_targets` rows, redirect to `/sessions/{id}/q/1`.
- `test_post_sessions_empty_corpus_renders_diagnostic` — fixture wipes `current_beliefs`; POST `/sessions` returns `index.html` with empty-corpus diagnostic banner; no session row created (F029).
- `test_get_question_renders` — fixture session; GET `/sessions/{id}/q/1` returns 200, contains header, summary, evidence excerpts, six verdict buttons with accesskey letters.
- `test_post_verdict_true_single_click_commit` — POST `/sessions/{id}/q/1/verdict` with `verdict=true, rationale=` (empty); verifies one `gold_labels` row, HX-Redirect to `/sessions/{id}/q/2` (F020).
- `test_post_verdict_skip_single_click_commit` — same shape with `verdict=skip`.
- `test_post_verdict_false_two_click_flow` — POST with `verdict=false, rationale=correct value text`; verifies `gold_labels.rationale` carries the text.
- `test_post_verdict_trigger_rejection_renders_banner` — fixture inserts a row whose target_id will fail `fn_gold_labels_validate_target` (e.g., a deleted claim); POST verdict; verifies route catches `GoldLabelStorageError` and renders the same question with an error banner (uses real-DB `conn` fixture per F013).
- `test_post_verdict_404_unknown_session` — POST to nonexistent session_id; 404.
- `test_post_verdict_404_out_of_range_idx` — POST to `idx=99` on a 10-target session; 404.
- `test_post_verdict_422_unknown_verdict` — POST with `verdict=garbage`; 422.
- `test_post_verdict_403_origin_mismatch` — POST with `Origin: http://evil.example`; 403 (F006).
- `test_post_verdict_completes_session_at_n` — POST the n-th verdict; verifies `mark_session_completed` was called and HX-Redirect goes to `/sessions/{id}/complete` (F019).
- `test_get_messages_tier_1_enforced` — fixture message at `privacy_tier=2`; GET `/sessions/{id}/messages/{message_id}` returns 403 with structured envelope (F008).
- `test_get_messages_context_max_tier_carry` — fixture conversation with one tier-2 row in the context window; GET `/messages/{id}/context?before=2&after=2` returns 403 (F023).
- `test_get_evidence_all_tier_1_enforced` — same shape for the show-all-rows route.
- `test_post_save_and_quit_discards_in_progress` — POST `/save-and-quit`; verifies no `gold_labels` row was committed, banner contains resume command string (F022).
- `test_post_abandon_marks_completed` — POST `/abandon`; verifies `gold_label_sessions.completed_at` is set and `operator_note='abandoned via web'` (F025).
- `test_consolidator_transitions_unimportable_from_web` — imports `engram.interview.web` and asserts `engram.consolidator.transitions` is not in the module's reachable symbol graph (F007).
- `test_htmx_loaded_from_static_not_cdn` — GET `/` and verify the `<script>` tag points at `/static/htmx.min.js`, not `unpkg.com` (F004).
- `test_static_htmx_served` — GET `/static/htmx.min.js` returns 200 with non-empty body.
- `test_aria_live_region_present` — GET `/sessions/{id}/q/1` and verify `aria-live="polite"` element is in the rendered HTML (F026).

`tests/test_interview_render.py` (new):

- Golden-output tests for `format_header`, `format_summary_line`, `format_evidence_dates`, `format_evidence_excerpts`, `pick_question` against fixture targets — pin current CLI rendering to verify the extraction is no-behavior-change (F003).
- `test_pick_question_uses_utc_now` — explicit UTC `now` keyword produces stable `ev_date` regardless of local timezone (F015).

`tests/test_migrations.py` (extend):

- `test_011_session_targets_append_only` — INSERT, then UPDATE / DELETE both raise `P0001`.
- `test_011_session_targets_version_triple_check` — claim row with consolidation columns set raises CHECK constraint; belief row with extraction columns set raises CHECK constraint.
- `test_011_session_targets_pk_uniqueness` — duplicate `(session_id, idx)` raises unique-violation.

### Privacy-tier env var

**Deferred to v1.1.** v1 hard-codes Tier 1 ceiling on `/messages/{id}`, `/messages/{id}/context`, and `/q/{idx}/evidence/all`. The `ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX` env var named in RFC 0027 § Open Question O3 is reserved but not implemented; v1.1 may introduce it with default `1` for symmetry with the CLI export ceiling.

### Verdict keyboard shortcuts

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
- `s` keeps `stale` (matches CLI verdict glossary in `gold-set-interview.md`); CLI's `q to save and quit` rebinds in the web to `q` (matches CLI's already-existing `q` verb at cli.py:1845 in `_prompt_verdict`).
- `unsupported` rebinds from any imagined `u` to `n` (a freer letter; survives the `u`/`unsure` collision).
- `?` requires Shift on US keyboards but is the discoverable convention for "help"; the dispatcher accepts both raw `?` and `Shift-/` keydown.
- Enter inside the rationale textarea inserts a newline (does NOT submit). Shift-Enter submits the form. Enter on a focused button activates the button (browser default).
- The dispatcher ignores all bare-key presses when `document.activeElement.tagName` is `INPUT` or `TEXTAREA`, except `Esc` (closes modal regardless of focus).

### BUILD_PHASES.md insert

Add after the existing PHASE-0003-FOLLOWON entry on line 265:

```markdown
**Web UI (RFC 0027 / D080):** local-only browser UI over the same gold-label
substrate, surfaced via `engram phase3 interview serve [--port 8765]`.
FastAPI + Jinja2 + htmx; no JS framework, no build step. Renders share
helpers in `src/engram/interview/render.py` (extracted from `cli.py`); CLI
loop continues to exist and is unchanged in behavior. Loopback-only bind;
no auth, no TLS, no CSRF token in v1 (Origin-header allowlist enforced
instead). Tier 1 ceiling hard-coded on full-message and context routes.
Verdict-button single-click commit for `true` / `skip`; rationale-required
flow for `false` / `stale` / `unsupported` / `unsure`. Sampled order
materialized at session creation in
`gold_label_session_targets` (migration `011_gold_label_session_targets.sql`)
with the typed version triple stamped to preserve resume-against-frozen-pool
semantics under re-extraction. Inline strata strip ships in v1; coverage
dashboard, export, history, and active-learning toggle remain CLI-only
until v1.1. Ships as `engram[serve]` optional extra; headless / CI installs
unchanged.

**Acceptance criteria (Tier 0 smoke):**

- `engram phase3 interview serve` boots on `127.0.0.1:8765`, refuses
  non-loopback bind (no escape clause in v1).
- Index page lists open sessions with progress; new-session form creates a
  session, samples `n` targets, materializes the order in
  `gold_label_session_targets`, and redirects to `/q/1`.
- Verdict commit round-trips through the existing `gold_labels` triggers
  (`fn_gold_labels_append_only`, `fn_gold_labels_validate_target`,
  `fn_gold_labels_carry_privacy_tier`).
- Trigger rejections render an inline error banner; the session stays open.
- Non-`Origin`-allowlisted POSTs return 403.
- `/messages/{id}` and `/messages/{id}/context` reject Tier 2+ rows with 403.
- `/static/htmx.min.js` is served from the wheel; no CDN reference is
  reachable from any rendered page.
- A web import-graph test verifies `engram.consolidator.transitions` is
  unreachable from `engram.interview.web` (D044 / D069).

**Leaves for next phase:** when `engramd` (RFC 0022) lands, web routes
migrate from calling `engram.interview.{agent,sampler,storage}` directly
to calling `engramd`'s interview HTTP endpoints; the FastAPI app becomes
a Jinja layer mounted on `engramd`'s ASGI tree.
```

### DECISION_LOG.md entry

Append as `D080` after `D079`:

```markdown
| <a id="d080"></a>D080 | accepted | RFC 0027 interview web UI is accepted as a local-only Jinja+htmx surface
over the existing `engram.interview` helpers, shipping under
`engram phase3 interview serve` as part of Phase 3 follow-on. The web app stands
as a separate FastAPI module under `src/engram/interview/web.py` in v1, with an
explicit forward-compat path to RFC 0022 (`engramd`): when `engramd` lands, the
web routes migrate from calling `engram.interview.{agent,sampler,storage}`
directly to calling `engramd`'s interview HTTP endpoints, and the web app
becomes a Jinja layer mounted on `engramd`'s ASGI tree. Migration
`011_gold_label_session_targets.sql` materializes the sampled order at session
creation with the typed version triple stamped (extraction or consolidation
pair plus `request_profile_version`) so re-extraction between question renders
does not drift the rendered question. v1 is loopback-only with no
`--allow-non-loopback` escape clause; Origin-header allowlist enforces CSRF
posture; Tier 1 ceiling is hard-coded on full-message and context routes. v1
exposes `n` and `seed` only on the new-session form; `--include-superseded`
and `--ignore-cooldown` remain CLI-only. Verdict commit is single-click for
`true`/`skip` and two-click rationale-required for
`false`/`stale`/`unsupported`/`unsure`. FastAPI + Uvicorn + Jinja2 ship under
the `engram[serve]` optional extra so headless installs are unchanged.
| RFC 0022 is `proposal` / `Implementation: none` (no `engramd` binary, no
`src/engram/api/` module, no FastAPI in `pyproject.toml`); waiting for it would
sacrifice a load-bearing Phase-3 follow-on operator UX gain on a Phase-5-prelude
sequencing bet. The 2026-05-08 multi-agent review (claude / codex / gemini)
identified two blocking findings — fictional `striatum serve` precedent (F001)
and parallel-surface concern with RFC 0022 (F002) — and 27 non-blocking
findings. The fictional precedent is a citation fix; the parallel-surface
concern is theoretical until `engramd` exists, so v1 stands as a separate
FastAPI app with a documented migration path. Materializing the sampled order
at session creation is forced (not chosen): every successful verdict POST
shifts the cooldown filter, so option A ("re-sample on each request") drifts
the index map across renders within a single session.
| Migration `011_gold_label_session_targets.sql` adds the materialized order
table with `(session_id, idx)` PK, `idx INT NOT NULL CHECK (idx >= 0)`,
typed version-triple columns mirroring `gold_labels`, append-only trigger
`fn_gold_label_session_targets_append_only`, and FK to `gold_label_sessions`
with `ON DELETE CASCADE`. The CLI loop is updated to also write the
materialized order so sessions created via CLI are resumable from the web UI.
`render.py` extraction unifies CLI and web rendering paths; CLI behavior is
verified unchanged via golden-output tests. Origin-allowlist CSRF posture is
the v1 enforcement; per-form CSRF tokens are deferred to v1.1 with the trigger
"any new mutating route added after v1." `ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX`
env var is reserved but not implemented in v1 (Tier 1 hard-coded). Coverage
dashboard, export, history, and active-learning toggle remain CLI-only until
v1.1. The implementation lands under
`striatum/rfc-0027-interview-web-ui-implementation/`; the implementation spec
lands at `docs/specs/0027-interview-web-ui-spec.md` and RFC 0027 moves to
`promoted` status.
| Revisit when (a) RFC 0022 / `engramd` is accepted and built and the web app
must migrate to mount on `engramd`'s ASGI tree; (b) any new mutating web route
is added (re-evaluate per-form CSRF token deferral); (c) operators routinely
work with Tier 2+ data and need `ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX`; (d)
the inline strata strip proves insufficient and the `/coverage` dashboard
needs to ship; (e) a justified non-loopback use case appears (re-evaluate
`--allow-non-loopback` deferral, paired with token auth per RFC 0022 Open
Question 7). |
```

## Risks the synthesis carries

- **The forward-compat path to RFC 0022 is asserted, not engineered.** The synthesis commits RFC 0027 to migrating to `engramd` when `engramd` lands, but the migration plan is one paragraph. If RFC 0022's interview endpoint shape diverges from what `engram.interview.{agent,sampler,storage}` exposes today (e.g., it gates verdict-write on a request schema RFC 0027 cannot satisfy without UI rework), the migration is more than mechanical. Mitigation: when RFC 0022 reaches synthesis, the RFC 0022 reviewer must explicitly check RFC 0027's call sites against the proposed endpoint shape and flag any gap. This synthesis assumes the call shape stays close to `record_verdict(session_id, target, verdict, rationale)`.

- **Origin-header allowlist may be insufficient against a determined attacker.** F006 was about any-tab autosubmit, which the Origin check handles. But a malicious browser extension (or a chrome flag like `--disable-web-security` set for unrelated reasons) can suppress or rewrite the `Origin` header. The synthesis defers per-form CSRF tokens to v1.1 on a documented threat model; if an operator runs a non-default browser configuration, the protection weakens. The deferral is acceptable for a single-user local UX but should not be transferred without scrutiny to any future multi-user surface.

- **The "frozen at session creation" semantics for migration 011 conflict with the operator's intuition that `--rebuild` reflows everything.** A session created against extraction prompt v1 stays bound to v1 even if the operator runs `engram phase3 re-extract` between q1 and q5. The synthesis chose this for replay determinism (RFC 0017 discipline), but operators may experience it as "the UI is showing stale beliefs." Mitigation: the question page's header should display the version triple the session was created against, so the operator can see the freeze and start a new session if they want fresh extraction. This is implied in the spec's `format_header` extraction but should be made explicit in the implementation spec.

- **Single-click commit for `true` and `skip` makes those verdicts the path of least resistance.** F020 closed the throughput gap, but the asymmetry creates a small bias toward those verdicts when an operator is fatigued at q40 of a 50-question session. The synthesis accepts the throughput argument over the fatigue-bias counterargument; if observed in practice (gold-set verdict distributions skew toward `true`/`skip` in web sessions vs CLI sessions), v1.1 may add a confirmation gesture. The risk is documented but not designed against.

- **`/messages/{id}/context` max-tier-carry is enforced by route logic, not by trigger.** The synthesis hard-codes Tier 1 in route handlers rather than via a privacy-tier-aware view. If the route is bypassed (e.g., by a future MCP transport that calls the same handler layer), the carry rule may not transfer. RFC 0022 already plans to handle privacy-tier carry on `/v1/evidence/{message_id}` in HTTP, holding MCP exposure until the Phase 5 snapshot renderer owns redaction; RFC 0027's tier ceiling needs to inherit that posture when the migration to `engramd` happens. The risk is documented as part of the "deferred ENV var" item.

- **The render extraction may break golden-output tests on the first run.** F003 + F015 + F027 together require touching every line of the CLI rendering surface. A naive lift-and-shift will produce subtle changes (timezone normalization for `pick_question`, predicate-doc append ordering, `[Conversation: ...]` vs `[<title>]` formatting). The implementation phase must run the existing `tests/test_interview_cli.py` against the refactored CLI and reconcile any drift before promotion. The spec deltas above call this out; the risk is that "no behavior change" is asserted in the RFC but discovered to require small CLI changes during implementation.

- **Migration 011 ships with the v1 CLI as well, which is an implicit CLI behavior change.** The CLI loop currently materializes the sampled order in memory; the synthesis requires the CLI to also write to `gold_label_session_targets` so CLI-started sessions are web-resumable. This is a small but real behavior change that the RFC originally framed as web-only. The implementation must update `tests/test_interview_cli.py` to expect the materialized rows. The risk is that a reviewer reading "no behavior change in the CLI" misses the materialization step; the spec deltas above name it explicitly.
