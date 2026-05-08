# RFC 0027 Interview Web UI Findings Ledger
author: ledger-codex-gpt-5.5-001

Status: ledger
Date: 2026-05-08
Sources:
  - RFC_0027_INTERVIEW_WEB_UI_REVIEW_claude.md
  - RFC_0027_INTERVIEW_WEB_UI_REVIEW_codex.md
  - RFC_0027_INTERVIEW_WEB_UI_REVIEW_gemini.md

## Findings

### F001 — Cited `striatum serve` precedent does not exist; D020/exit-8 anchor is wrong
Severity: blocking
Sources: [claude, codex]
Affects: RFC citations / privacy posture / `--allow-non-loopback` CLI flag
Rationale: The RFC anchors its localhost-only posture and the "refuse with exit 8" non-loopback contract on a `striatum serve` precedent and "RFC 0012 § Local HTTP service" that do not exist; the actual D020 precedent is RFC 0022 / `engramd`, which warns rather than refuses on non-loopback bind, so the borrowed contract is fictional and the exit-code claim has no source.
merged_from:
  - claude § F001 (blocking — `striatum serve` precedent and RFC 0012 anchor are fabricated)
  - codex § F007 (minor — exit-code 8 claim mirrors a `striatum serve` posture not implemented anywhere)

### F002 — Parallel surface to `engramd`; collides with RFC 0022 promotion path
Severity: blocking
Sources: [claude]
Affects: route surface / process model / RFC 0022 relationship
Rationale: RFC 0022 places the interview endpoints inside `engramd` precisely to avoid a parallel HTTP surface, yet RFC 0027 stands up a separate FastAPI app with its own Uvicorn lifecycle and bind logic without acknowledging RFC 0022 in § Relationship to other artifacts; the RFC must either mount onto `engramd`, supersede the RFC 0022 endpoint list, or justify a second loopback listener.
merged_from:
  - claude § F002

### F003 — `render.py` extraction is incomplete; CLI rendering will drift
Severity: major
Sources: [claude, codex]
Affects: render boundary (`src/engram/interview/render.py`, `src/engram/cli.py:1658-1862`)
Rationale: The four named exports (`fetch_target_display`, `fetch_evidence_excerpts`, `pick_question`, `rationale_prompt_for`) are insufficient — the CLI loop also depends on `_VERDICT_PROMPT` / `_VERDICT_ALIAS` / `_VERDICT_VALID`, the `_EVIDENCE_EXCERPT_LIMIT` / `_EVIDENCE_ROWS_SHOWN` constants, `_print_evidence_excerpts`, the header builder, predicate-doc append, and the valid-from formatter, so partial extraction guarantees the silent CLI/web drift the RFC claims to prevent.
merged_from:
  - claude § F003
  - codex § F001

### F004 — htmx CDN escape clause invites D020 drift
Severity: major
Sources: [claude]
Affects: template / static-asset packaging / privacy posture
Rationale: § Templates and § Privacy posture leave a CDN reference for htmx on the table and reopen the choice in Open Question O2, but D020's "no network egress" plus HUMAN_REQUIREMENTS' no-cloud frame make a `<script src="https://unpkg.com/...">` from the operator's browser obviously wrong; the v1 contract should remove the CDN option entirely and pin a single vendored `/static/htmx.min.js`.
merged_from:
  - claude § F004

### F005 — `--allow-non-loopback` escape clause is excessive for the stated use case
Severity: major
Sources: [claude]
Affects: CLI (`engram phase3 interview serve`) / privacy posture
Rationale: The RFC ships v1 with no auth, no TLS, and no CSRF yet adds a `--allow-non-loopback --reason` flag that, the moment it is used, exposes write access to `gold_labels` to whatever is on the wire; RFC 0022 pairs non-loopback bind with a token-auth roadmap, RFC 0027 has neither, so the flag should not exist in v1 (or must be gated on auth that does not yet exist).
merged_from:
  - claude § F005

### F006 — CSRF dismissal is wrong on the threat model
Severity: major
Sources: [claude]
Affects: route surface / privacy posture (POST verdict, complete, save-and-quit, sessions create)
Rationale: "Localhost forms with a single user are not a CSRF threat" is incorrect: any tab the operator visits can drive a hidden auto-submitting form at `127.0.0.1:8765/...` and silently commit gold-label rows, so v1 must ship `SameSite=Strict` cookies plus an `Origin`/`Sec-Fetch-Site` allowlist or per-form CSRF tokens rather than deferring to "synthesis to challenge."
merged_from:
  - claude § F006

### F007 — D044/D069 invariant is asserted but not mechanically guarded in the route surface
Severity: major
Sources: [claude]
Affects: route table / templates / DECISION_LOG D044 / D069 invariants
Rationale: The RFC asserts no consolidator coupling but never restates the D044 invariant in the web layer, leaving nothing to forbid a future "Promote belief" route or template affordance from re-entering the consolidator transition path; the spec needs an explicit "no web route may invoke any consolidator transition; no template may render a promote-belief affordance" section that names D044/D069.
merged_from:
  - claude § F007

### F008 — `/sessions/{id}/messages/{id}` privacy-tier ceiling is under-specified
Severity: major
Sources: [claude]
Affects: route surface (`GET /sessions/{session_id}/messages/{message_id}`) / privacy posture
Rationale: The route table claims "Tier 1 enforced" but defers the enforcement mechanism (env var, hard ceiling) to Open Question O3, leaving a programmatic privacy-critical surface under-specified; v1 must either hard-code a Tier 1 ceiling on `/messages/{id}` or define the env var with default=1 and reject higher-tier rows with 403.
merged_from:
  - claude § F008

### F009 — Persistent target order: Option B sketch and migration 011 schema are too thin
Severity: major
Sources: [claude, codex]
Affects: schema / migration `011_gold_label_session_targets.sql`
Rationale: The recommended option B table is given as `(session_id, idx, target_kind, target_id, ...)` with `...` doing all the work; the spec must pin the PK (`(session_id, idx)`), `idx` type and 0-vs-1-indexing relative to the URL, the `candidate_pool_snapshot_id` placement (and whether the typed version triple plus `request_profile_version` are stamped at session creation so re-extraction between q1 and qN does not drift), append-only semantics, and the BEFORE-INSERT trigger naming convention from migration 010.
merged_from:
  - claude § F009
  - codex § F005

### F010 — Sampler determinism + re-sample-on-resume corner case not addressed
Severity: minor
Sources: [claude]
Affects: sampler (`src/engram/interview/sampler.py`) / session resume semantics
Rationale: A session created with `seed=k` is deterministic only against a frozen candidate-pool snapshot; the RFC neither says the materialized order is the contract nor that the snapshot id is carried on the session, so a session resumed days later silently chooses between "freeze stale" and "re-sample drift" with eval-replay consequences that RFC 0021's `candidate_pool_snapshot_id` discipline is meant to prevent.
merged_from:
  - claude § F010

### F011 — `--include-superseded` and `--ignore-cooldown` exposed as form checkboxes is an adversarial-sweep footgun
Severity: minor
Sources: [claude]
Affects: template (`index.html` new-session form)
Rationale: RFC 0021 frames `--include-superseded` as adversarial-sweep mode; presenting it plus `--ignore-cooldown` as plain index-page checkboxes (the surface RFC 0027 says non-developers will use most) makes adversarial-sweep mode one click away with no warning, no consent banner, and no audit, which the CLI flag's deliberateness was meant to prevent.
merged_from:
  - claude § F011

### F012 — Packaging: `[serve]` extra, package-data block, and typecheck wiring are unspecified
Severity: major
Sources: [claude, codex]
Affects: packaging (`pyproject.toml` extras + `[tool.setuptools.package-data]`) / `make typecheck`
Rationale: FastAPI / Uvicorn / Jinja2 are introduced as new deps but no `[project.optional-dependencies] serve = [...]` is declared, no `[tool.setuptools.package-data] "engram.interview" = ["templates/*", "static/*"]` block ships templates and `htmx.min.js` inside the wheel, and pyright's `reportMissingImports = "error"` will fail for `engram.interview.web` without `fastapi` in the dev venv — so the spec must commit to an extra name, the package-data declaration, and either folding `serve` into `dev` or excluding `engram.interview.web` from pyright when the extra is absent.
merged_from:
  - claude § F012 (minor — `[serve]` extra missing)
  - codex § F003 (major — extra + package-data + dev/pyright wiring)
  - codex § F011 (minor — package-data block needed for templates/static under packages.find)

### F013 — Test surface is hand-waved; trigger-rejection banner needs real DB coverage
Severity: major
Sources: [claude, codex]
Affects: tests (`tests/test_interview_web.py`, `tests/conftest.py:13-83`)
Rationale: Open Question 7 leaves the test plan as "TestClient + a `conn` fixture; do triggers need to fire?" — but `fn_gold_labels_append_only`, `fn_gold_labels_validate_target`, and `fn_gold_labels_carry_privacy_tier` are the only production source of `GoldLabelStorageError`, so the spec must enumerate required coverage (verdict happy-path, trigger-rejection banner against the real-DB fixture, 404 on unknown session, 422 on unknown verdict, 404 on out-of-range idx, `/messages/{id}` Tier 1 enforcement, `--allow-non-loopback` refusal, htmx loaded only from `/static/htmx.min.js`, save-and-quit, complete) rather than deferring to synthesis.
merged_from:
  - claude § F013 (minor)
  - codex § F008 (major)

### F014 — Sync `def` vs `async def` route handlers have connection-pool implications, not just style
Severity: minor
Sources: [claude, codex]
Affects: route handler signatures / process model / `psycopg.Connection` use in `engram.interview.{storage, sampler, agent}`
Rationale: Every interview helper is synchronous psycopg, so `async def` route handlers would block the FastAPI event loop on the first DB call and head-of-line-block every other request; v1 must commit to sync `def` handlers + threadpool dispatch + `uvicorn --workers 1` rather than leaving the choice as cosmetic in Open Question O6.
merged_from:
  - claude § F014 (nit)
  - codex § F009 (minor)

### F015 — `pick_question` has a hidden `now`/timezone dependency the signature elides
Severity: major
Sources: [codex]
Affects: render boundary (`_pick_question` in `src/engram/cli.py:1817-1835`, `_fetch_target_display` at 1744-1745, 1786-1787)
Rationale: `_pick_question` formats `evidence_max` via `.date().isoformat()` in the server's local timezone implicitly while the rest of the codebase uses `datetime.now(timezone.utc)`, so a CLI verdict and a web verdict on the same belief can render different `ev_date` strings; the spec must pin UTC (or pass an explicit `now`/tz keyword) so "no behavior change in the CLI" actually holds.
merged_from:
  - codex § F002

### F016 — Persistent target order Option A is misframed; Option B is forced, not chosen
Severity: major
Sources: [codex]
Affects: sampler / persistent-targets schema decision
Rationale: Option A claims "deterministic re-sample given seed" but each verdict POST writes a `gold_labels` row that `_last_blocking_label_at` folds into the cooldown filter, so `_rng.shuffle` re-runs on a shorter list at q5 than at q1 and the index map drifts between requests; Option A is therefore "re-sample with order that drifts as you label" and Option B (migration 011) is the only correct choice — the RFC text must remove "deterministic" from Option A and mark the recommendation as forced.
merged_from:
  - codex § F004

### F017 — `record_verdict` payload from the route has no defined `evidence_excerpt` source
Severity: major
Sources: [codex]
Affects: route surface (POST verdict) / `InterviewAgent.record_verdict` / privacy posture
Rationale: `record_verdict` accepts `evidence_excerpt: str | None = None`, the CLI never passes one, but the web question page does render evidence excerpts; the RFC never says whether a web verdict leaves the column NULL, populates it from the first rendered excerpt, or carries a hidden-input excerpt the operator was actually looking at — and migration 010's `fn_gold_labels_carry_privacy_tier` carries the parent tier without redacting the excerpt, so the privacy-tier story changes by option and the spec must close it before promotion.
merged_from:
  - codex § F006

### F018 — Coverage / strata visibility is promised in §Background but missing from v1 routes
Severity: major
Sources: [codex, gemini]
Affects: route surface / template (`index.html` or `/q/{idx}` sidebar) / §Background promise
Rationale: Friction source 3 (stratum visibility) is the third leg the RFC uses to justify the web UI, yet `coverage` is deferred to v1.1, so v1 only fixes 2/3 of the stated problems and the CLI's `engram phase3 interview coverage` already covers what v1 ships; the spec should add a small inline strata readout on `/q/{idx}` (one `SELECT stability_class, count(*) ... WHERE session_id=?`) in v1 and keep the `/coverage` dashboard deferred, or downgrade friction source 3 to a non-goal.
merged_from:
  - codex § F010 (minor)
  - gemini § F009 (major)

### F019 — `POST /complete` and `POST /save-and-quit` semantics are redundant / unstated
Severity: nit
Sources: [codex]
Affects: route surface (`POST /sessions/{id}/complete`, `POST /sessions/{id}/save-and-quit`)
Rationale: The CLI calls `mark_session_completed` only after all `n` verdicts; the web route shape preserves both an explicit `/complete` and a no-op-redirect `/save-and-quit`, but the RFC never names what fires `/complete` — auto-redirect after the final verdict (worked example implies A) or an explicit button on the question page (option B) — and the spec must pin it.
merged_from:
  - codex § F012

### F020 — Throughput claim is asserted, not engineered (verdict-commit round-trip count)
Severity: major
Sources: [gemini]
Affects: template / question-page UX / `/q/{idx}` route
Rationale: §Background promises "click a verdict button while reading the next question" but the worked example's button → swap → type → submit → HX-Redirect → render flow is *more* round-trips than the CLI's two-keystroke `t`-Enter loop on the no-rationale path; the spec must commit single-click verdict-and-empty-rationale commit for `true`/`skip` and keep the rationale-textarea-then-submit pattern only for verdicts that genuinely require explanation.
merged_from:
  - gemini § F001

### F021 — Keyboard shortcut letters conflict with browser defaults and need a dispatch mechanism
Severity: major
Sources: [gemini]
Affects: template (`base.html`) / accesskey letter assignments / Open Question O8
Rationale: `accesskey="..."` only fires under browser-specific modifier prefixes, so bare `t`/`f`/`s`/`u`/`?`/`k` does nothing without a `keydown` listener; additionally `s` collides with the CLI's save-and-quit binding, `?` requires Shift on US keyboards, and Enter-vs-Shift-Enter behavior in the rationale textarea is unstated — the spec needs an explicit binding table, an input/textarea-aware bare-key dispatcher with `accesskey` fallback, and a documented Enter-vs-Shift-Enter contract.
merged_from:
  - gemini § F002

### F022 — "Save and quit" semantics drift from CLI Ctrl-C contract; back/forward unstated
Severity: major
Sources: [gemini]
Affects: route surface (`POST /save-and-quit`) / template / browser history
Rationale: The CLI contract is "torn turn produces no row" but the web has no defined behavior for "verdict pressed, rationale textarea open, Save-and-quit clicked" (discard / commit-with-current-text / modal) and never says whether `/q/{idx}` pushes onto browser history; the spec must pick discard-for-CLI-parity, surface a "K/N answered, closing this tab is safe" status line, return the `engram phase3 interview resume --session-id` string, and commit `hx-push-url="true"` so back/forward and bookmarks work.
merged_from:
  - gemini § F003

### F023 — Evidence "show full message" is one-shot; no contextual `/messages/{id}/context` endpoint
Severity: major
Sources: [gemini]
Affects: route surface (`GET /sessions/{session_id}/messages/{message_id}` and proposed `/context`) / template
Rationale: §Background promises showing "the full conversation around an excerpt," but the route only delivers a single message body — operators inspecting `false`/`stale` typically need adjacent turns; the spec should add `GET /sessions/{session_id}/messages/{message_id}/context?before=N&after=M` (max-tier-carry across all returned rows) and either parameterize the 3-row CLI excerpt cap or expose a "show all N evidence rows" disclosure.
merged_from:
  - gemini § F004

### F024 — No help / shortcut overlay; operator-discoverability gap
Severity: minor
Sources: [gemini]
Affects: template (`base.html` modal) / accessibility
Rationale: A 50-question session is exactly when operators forget which letter does what, and the CLI prints the verdict line every prompt; the spec should print each verdict's gloss directly under its button, bind `?` to a modal listing shortcuts and verdict glosses sourced verbatim from `gold_label_verdict_vocabulary`, and bind `Esc` to close-and-restore-focus.
merged_from:
  - gemini § F005

### F025 — Session lifecycle UX is underspecified for "abandon" / multi-session hygiene
Severity: major
Sources: [gemini]
Affects: route surface (`POST /sessions/{id}/abandon`) / template (`index.html`) / session-list query
Rationale: The index page lists open sessions but offers no abandon/close affordance, so a wrong-seed session stays open forever, stale sessions clutter the index, and double-clicking "New session" creates two sessions; the spec should add `POST /sessions/{id}/abandon` (calling `mark_session_completed` with `operator_note='abandoned via web'`), surface progress (`3/10 answered, opened 2h ago`) on the index, debounce/CSRF-token the new-session form, and pin the index page title.
merged_from:
  - gemini § F006

### F026 — Accessibility: htmx swap focus, live regions, and verdict-button labelling are absent
Severity: major
Sources: [gemini]
Affects: template / htmx swap configuration / a11y posture
Rationale: htmx `innerHTML` swaps drop screen-reader and focus state silently, so the spec must add an `aria-live="polite"` live region announcing "Question K of N" each swap, move focus to a known anchor on `htmx:afterSwap`, give verdict buttons `aria-label` carrying the gloss, set `aria-describedby` on the rationale textarea pointing at the verdict-specific prompt, and ensure verdict differentiation is not color-only (WCAG 1.4.1).
merged_from:
  - gemini § F007

### F027 — Worked example evidence row drifts from real CLI output
Severity: minor
Sources: [gemini]
Affects: RFC §Worked example / `_print_evidence_excerpts` (`src/engram/cli.py:1711-1725`)
Rationale: The worked example shows a `[ ]` glyph not present in the CLI, prefixes the conversation title with `Conversation:` where the CLI prints it bare, and uses an unrealistic ChatGPT title; if the worked example drifts from the CLI now, `render.py` will reproduce the drift in v1 unless the example is reconciled with the actual CLI render path.
merged_from:
  - gemini § F008

### F028 — Verdict-button row ordering and visual weight invite mistabs onto destructive verdicts
Severity: minor
Sources: [gemini]
Affects: template (verdict button row)
Rationale: `true / false / stale / unsupported / unsure / skip` puts the two destructive-ish verdicts immediately to the right of `true`, so a single mistab from `true` lands on `false` — the verdict the operator most wants friction on; either place `true` and `skip` (the single-click commits) at opposite ends with destructive verdicts in the middle, or apply rationale-then-Submit uniformly so the asymmetry disappears, and stamp accesskey letters on the button face.
merged_from:
  - gemini § F010

### F029 — No empty-corpus / no-targets UX path on the index
Severity: minor
Sources: [gemini]
Affects: route surface (`POST /sessions`) / template (`index.html`)
Rationale: When `sampler.sample(n)` returns `[]` (brand-new install, all targets on cooldown, or stale `current_beliefs`), the CLI prints a specific diagnostic with the `engram phase4 refresh-current-beliefs` hint; the web flow is unstated and should refuse to create the session, re-render the index with the same diagnostic, and surface the refresh hint so new operators do not get stuck.
merged_from:
  - gemini § F011

## Counts

- Total findings: 29
- Severity breakdown: blocking=2, major=19, minor=7, nit=1
- Per-reviewer contributions: claude=14, codex=12, gemini=11
