# RFC 0027 Interview Web UI Review — gemini
author: reviewer-gemini-3.1-pro-preview-001

Status: review
Date: 2026-05-08
RFC refs: RFC-0027, RFC-0021
Decision refs: D016, D020, D044, D069, D074, D079
Phase refs: PHASE-0003-FOLLOWON

Lane focus: operator UX. The lane checks whether the proposed web surface
actually relieves the three friction sources called out in §Background
(verdict-per-line throughput, evidence inspection, stratum visibility),
and whether the keyboard / save-and-quit / evidence / session-lifecycle
/ accessibility / worked-example shapes hold up when an operator drives
50 verdicts in a sitting.

## Findings

### F001 — Throughput claim is asserted, not engineered
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:50-58 (friction source 1);
docs/rfcs/0027-interview-web-ui.md:255-287 (worked example);
docs/rfcs/0027-interview-web-ui.md:140-141 (`/q/{idx}` route).
Rationale: §Background promises "click a verdict button while reading
the next question," but the proposed swap-then-rationale-then-redirect
flow in the worked example is *more* round-trips than the CLI on the
common case. CLI today: type `t`, blank rationale Enter, next prompt
prints — two keystrokes, one render. Web today (per worked example):
press button or `t`, htmx fragment swap shows rationale textarea, type
optional rationale, press Submit, server records verdict, htmx HX-Redirect
to `/q/{idx+1}`, full question rerender. That is 1 click + 1 swap + 1
type + 1 click + 1 redirect + 1 render — net more friction on the
no-rationale path. The fix is for the `true`/`skip` path (and a
to-be-defined `--default-blank-rationale` for `unsure`) to commit
verdict-and-empty-rationale in a single click without showing the
rationale region at all. The RFC mentions auto-hide on `true`/`skip`
(line 140) but does not say whether the verdict commits *immediately*
on those buttons or whether it still requires a confirmation step. The
spec should pin that down: `true`/`skip` = single click commits;
`false`/`stale`/`unsupported`/`unsure` = swap to rationale, second
click to commit. Otherwise the throughput goal is not met.

### F002 — Keyboard shortcut letters conflict with browser defaults
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:340-343 (Open Q 8);
docs/rfcs/0027-interview-web-ui.md:271 (worked example shows
`[ true ]  [ false ]  [ stale ]  [ unsupported ]  [ unsure ]  [ skip ]`).
Rationale: the RFC defers the exact letter assignment to synthesis. In
practice `accesskey="..."` on a button only fires under modifier prefixes
that vary by browser (Chrome: `Alt`, Firefox: `Alt+Shift`, Safari:
`Ctrl+Alt`). That means a bare `t`/`f`/`s`/`u`/`?`/`k` keystroke does
nothing unless the page also installs a `keydown` listener. The RFC
does not commit to one mechanism. Recommend: ship a small inline
`<script>` in `base.html` that listens for bare-key keydown when no
input is focused, dispatches to the matching button, and falls back to
`accesskey` for a11y. Letter conflicts to call out:

- `s` is already "save and quit" in the CLI; the worked example puts
  `s` on `stale`. Pick one. Recommend `stale` keeps `s` (matches the
  CLI verdict glossary in `gold-set-interview.md:80`) and save-and-quit
  rebinds to a chord (`Ctrl-S`, browser-safe outside text input) or a
  visible button.
- `?` cannot be a bare key (most US keyboards require Shift). RFC 0021
  used `?` for "unsure" abbreviation. Web should bind `u` to `unsure`
  and reserve `?` for a help overlay (which the spec should add — see
  F005).
- `k` for `skip` is fine.
- `Tab`/`Enter` defaults must not be hijacked: pressing Enter inside
  the rationale textarea should *not* submit (multi-line rationales
  are realistic); pressing Enter on a focused button should commit.

The spec needs: (a) explicit letter binding table; (b) handler that
ignores keystrokes when an `<input>`/`<textarea>` is focused; (c)
documented Enter-vs-Shift-Enter behavior in the rationale textarea.

### F003 — "Save and quit" semantics drift from CLI Ctrl-C contract
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:143 (`POST /save-and-quit`);
src/engram/cli.py:1845 (CLI `q`/`save-and-quit`); src/engram/cli.py:1968-1973
(CLI on save-and-quit prints resume hint with session id). RFC 0021
mid-session semantics at docs/rfcs/0021-gold-set-interview-curation.md:351-360.
Rationale: the CLI contract is "torn turn produces no row" — the verdict
only commits when both verdict and (optional) rationale are answered.
The web surface's `POST /save-and-quit` has no defined behavior for
"operator clicked a verdict, the rationale textarea is open, then
clicks Save and quit." Three reasonable answers — all very different
to the user:

1. discard the in-progress verdict (matches CLI Ctrl-C);
2. commit the verdict with whatever rationale text is in the textarea;
3. confirm-via-modal.

The RFC must pick one. Recommend (1) for parity with CLI. The spec
should also commit to: (a) a visible status line on `/sessions/.../q/{idx}`
showing "answered K/N — closing this tab is safe, your verdicts are
already saved" so the operator never has to wonder; (b) `POST /save-and-quit`
returning the resume command string the same way the CLI does
(`engram phase3 interview resume --session-id <uuid>`), so users who
want to bounce between web and CLI can.

The browser refresh / back-button semantics are also missing. If the
operator presses browser-back from `/q/3`, do they get `/q/2`? Does
htmx history fall back to a full-page render? The RFC implies htmx
swap with HX-Redirect, but never says whether the swapped fragment
pushes onto browser history. Pin this down: each `/q/{idx}` should be
a real URL with `hx-push-url="true"`, so back/forward and bookmarking
work and the operator can deep-link a specific question to a colleague
on the same machine.

### F004 — Evidence "show full message" is one-shot, not contextual
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:142
(`GET /sessions/{session_id}/messages/{message_id}`);
docs/rfcs/0027-interview-web-ui.md:62-63 ("show the full message thread on
demand"); src/engram/cli.py:1671-1708
(`_fetch_evidence_excerpts` caps at 3 rows, 280 chars each).
Rationale: the §Background promises showing "the full conversation
around an excerpt"; the route surface only delivers "the full body of
one cited message." The operator inspecting a `false`/`stale` verdict
typically needs the *adjacent* messages — the user's reply, the
assistant's prior turn, the message that disambiguates a pronoun — not
just the cited row in isolation. The single-message route does not let
the operator widen the window without reverting to the SQL shell.

Recommend the spec add `GET /sessions/{session_id}/messages/{message_id}/context?before=N&after=M`
returning the cited message plus N predecessors and M successors from
the same `conversation_id`, with sane caps (e.g. `N+M <= 20`). Privacy
tier carry rule: the *max* tier across all returned rows gates
rendering, identical to RFC 0021's multi-source carry rule (line
210-213). Without this, the web UI loses one of its three claimed
advantages over the CLI.

Secondary issue: the cited-row excerpt cap of 3 (CLI's
`_EVIDENCE_ROWS_SHOWN`) is also the implicit web cap because the
template reuses `fetch_evidence_excerpts`. The web version has no
reason to cap at 3 — CRT real estate is not 80×24 anymore. Spec should
either parameterize the cap or expose a "show all N evidence rows"
disclosure on the question page. The route surface needs this; absence
is currently invisible because §Routes shows `/messages/{message_id}`
not `/evidence/all`.

### F005 — No help / shortcut overlay; operator-discoverability gap
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:140-141 (question page
description); whole RFC has no `?`-key or `/help` route.
Rationale: a 50-question session is the regime where the operator
forgets which letter does what after a 10-minute break. The CLI has
the verdict line printed every prompt. The web UI proposal renders six
buttons with labels (good) and verdict glossing in small parens under
each (the worked example at docs/rfcs/0027-interview-web-ui.md:271-275
implies but does not commit to this). The spec should:

- print the gloss of each verdict directly under its button (operator
  does not have to remember `unsupported` vs `false`);
- bind `?` to a small modal listing the keyboard shortcuts and a
  one-line gloss of each verdict (matching `gold_label_verdict_vocabulary`
  rows verbatim — single source of truth);
- make `Esc` close the modal and return focus to the previously
  focused button (a11y).

This is one template change and ~30 lines of inline JS. Skipping it
makes the UI worse than the CLI for the same operator.

### F006 — Session lifecycle UX is underspecified for "abandon" / multi-session
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:138 (GET `/`);
docs/rfcs/0027-interview-web-ui.md:144 (POST `/complete`);
docs/rfcs/0021-gold-set-interview-curation.md:355-358 (RFC 0021
mid-session semantics names `save-and-quit` but never `abandon`).
Rationale: the index page lists open sessions and a new-session form,
but the route surface offers no `abandon`/`close` for an open session
the operator no longer wants. Three concrete failure modes:

1. operator opens session A with `n=10`, answers 3, decides the seed
   was wrong, opens session B with a different seed. Session A stays
   open forever. There is no UI to mark it complete-without-finishing.
2. operator has 5 stale open sessions and the index page becomes
   noisy. The CLI has the same bug, but the web UI promised to *fix*
   stratum/coverage visibility — it should also fix session hygiene.
3. operator clicks "New session" twice in quick succession (laggy
   network, double-click); two sessions get created and the second
   redirect wins. A POST-redirect-GET pattern + idempotency token on
   the form fixes this; the RFC should commit.

Spec adds: (a) `POST /sessions/{session_id}/abandon` that calls
`mark_session_completed` with `operator_note='abandoned via web'` (no
schema change needed — that column already exists per RFC 0021
storage); (b) on the index page, list open sessions with progress
(`3/10 answered, opened 2h ago`) and an inline "abandon" link; (c)
debounce or csrf-token the new-session form to make double-submit a
no-op. The session-list query should join on `gold_labels` to compute
progress; one-shot SQL.

The page title for `/` is also unspecified. Make it
`Engram interview — open sessions` so a tab in a browser pile is
findable.

### F007 — Accessibility (keyboard-only, focus management, htmx swap announcements)
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:151-164 (templates section,
no a11y notes); docs/rfcs/0027-interview-web-ui.md:140-141 (htmx
fragment swap); HUMAN_REQUIREMENTS.md (no explicit a11y guidance, but
local-first single-operator UX still needs to work for keyboard-only
users).
Rationale: htmx swaps are a known a11y trap. When `hx-swap="innerHTML"`
replaces the question fragment, screen readers and focus state have no
idea anything happened — focus stays on the now-removed button until
it is silently moved to `<body>`. For a 50-question session this is
the difference between "usable with a screen reader" and "unusable."
Concrete spec asks:

- the swapped fragment must include a live region (`aria-live="polite"`)
  announcing "Question 4 of 10, belief, project_status" each swap;
- after swap, focus moves explicitly to a known anchor — either the
  question heading (`<h2 tabindex="-1">`) or the first verdict button —
  via `htmx:afterSwap` listener;
- verdict buttons need `aria-label` that includes the gloss (`<button
  aria-label="true: claim or belief is correct about the world">t</button>`)
  so screen-reader output matches the visual gloss;
- the rationale textarea needs `aria-describedby` pointing at the
  verdict-specific prompt (`correct value`, `when did it change?`,
  etc.) so the prompt is read as part of the textarea label;
- color is not the only verdict differentiator (currently the worked
  example carries no color, but the spec should commit to icon /
  underline for verdict buttons too — green-only `true` would fail
  WCAG 1.4.1).

Without these, the web UI is a regression from the CLI for a portion
of users. The CLI works fine with screen readers because each prompt
is a fresh line of stdout.

### F008 — Worked example evidence row does not match real CLI output
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:259-276 (worked example);
src/engram/cli.py:1711-1725 (`_print_evidence_excerpts`) and
src/engram/cli.py:1928-1964 (the CLI render path).
Rationale: the worked example shows
```
  [ ] 2025-12-25  user  (chatgpt)  [Conversation: "year-end review"]
      I can't believe how much has happened this year — 
      [show full message]
```
Three drifts from what the CLI actually emits today (verified at
src/engram/cli.py:1714-1723):

- the CLI prints `evidence:` once and then `    YYYY-MM-DD  role
  (source_kind)  [conv_title]` per row. The web mockup adds a
  leading `[ ]` checkbox-ish glyph that has no defined meaning. Drop
  it, or commit to it in the spec (e.g. "checkbox marks a row to
  cite in the rationale textarea via JS-prefill" — but that is a
  scope expansion).
- the conversation title in the CLI is shown as `[<title>]` — bare,
  no `Conversation:` prefix. Either make the CLI match the web form
  (better — more legible) or vice versa. Drift between the two is
  exactly the duplication risk the `render.py` extraction is
  supposed to prevent.
- "year-end review" is unlikely to be a real ChatGPT conversation
  title; titles are usually the first user-line. Pick a more
  realistic example to keep the worked example honest. (Real titles
  in the corpus include things like "make me a pun about X" or "rust
  ownership question.")

These are nits individually, but the worked example is the main
operator-facing artifact in the RFC; drift here suggests the spec
will reproduce drift in `render.py`.

### F009 — Coverage panel promised in §Background, missing from §Routes
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:65-68 (friction source 3:
"A web UI can show a small coverage panel in the sidebar");
docs/rfcs/0027-interview-web-ui.md:131-148 (route table, no coverage);
docs/rfcs/0027-interview-web-ui.md:146-148 (v1.1 deferral list
includes `coverage`).
Rationale: the RFC argues the third friction source is stratum
visibility — "you just labeled 4 mood targets in a row, here's the
strata distribution." Then defers `coverage` to v1.1 in the next
section. The two are contradictory: deferring coverage *is* deferring
the third friction source, which means v1 only fixes 2/3 of the
stated problems. The CLI already has a separate `engram phase3
interview coverage` command (cli.py:475-482); a web UI that does not
beat it on this dimension has not justified its v1 cost.

Recommend: keep `/coverage` (the dashboard) deferred to v1.1, but
*do* add a small live sidebar / footer on `/q/{idx}` showing the
running session's stratum distribution as a textual readout. The data
is already in `gold_labels WHERE session_id = ?`; one
`SELECT stability_class, count(*) GROUP BY 1` per render. No new
schema, no new route. This delivers the §Background promise without
the v1.1 surface.

If §Routes truly cannot ship the panel in v1, the RFC should drop
friction source 3 from §Background or downgrade it to a non-goal —
otherwise the RFC overpromises.

### F010 — Verdict-button row ordering and visual weight
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:271 (worked example button
row); docs/howto/gold-set-interview.md:148-160 (verdict glossary).
Rationale: the proposed left-to-right ordering is
`true / false / stale / unsupported / unsure / skip`, which puts the
two destructive-ish verdicts (`false`, `stale`) immediately to the
right of `true`. With keyboard-only navigation via Tab, that means a
single mistab over `true` lands on `false` — and `false` is exactly
the verdict the operator wants the *most* friction on (it is the
verdict that drives downstream re-extraction work).

Recommend the spec commit to: (a) `true` / `skip` are the two
single-click commits and they live at opposite ends of the row, with
the higher-cost verdicts in the middle; OR (b) all verdict buttons
require the rationale-then-Submit pattern uniformly, eliminating the
asymmetry. Either is fine; the current shape is the worst of both.

The accesskey letters from F002 should be stamped on the button face
in dim type (e.g. small superscript) so the operator can *learn* them
without consulting `?`.

### F011 — No empty-corpus / no-targets UX path on the index
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:138 (GET `/`);
src/engram/cli.py:1902-1910 (CLI handles "no targets matched" with a
specific message: empty corpus, all on cooldown, or
current_beliefs not refreshed).
Rationale: the CLI tells the operator *why* zero targets came back —
empty corpus vs cooldown vs missing refresh. The web UI proposal does
not specify what `POST /sessions` does when the sampler returns zero.
Two real failure modes the operator hits in practice: (a) brand-new
install with no Phase 3 output yet; (b) `current_beliefs` materialized
view stale because Phase 4 didn't refresh. Both produce zero targets
and require different fixes.

Spec asks: when `sampler.sample(n)` returns `[]`, do *not* create the
session (no point), and re-render the index page with a banner that
mirrors the CLI's diagnostic, plus the same `engram phase4
refresh-current-beliefs` hint the howto names at line 290-292. Without
this, the web UI sends new operators down a worse path than the CLI.

## Open questions

- Single-click vs two-click `true`/`skip` commit (F001) — confirm.
- Keyboard binding mechanism: bare-key listener vs `accesskey`-only
  vs both (F002).
- Save-and-quit-with-open-rationale-textarea behavior (F003): drop
  the in-progress verdict, or commit it?
- Should `/messages/{message_id}/context?before=N&after=M` ship in
  v1, or v1.1 (F004)? My read: v1, because the friction-source
  promise is load-bearing.
- Inline coverage strip in v1 vs dashboard in v1.1 (F009) —
  recommend the strip ships v1, dashboard defers.
- Verdict button ordering (F010): confirm `true` / ... / `skip` at
  the ends, with destructive verdicts in the middle.
- Does the spec mandate `hx-push-url="true"` per-question for
  back-button parity (F003)?
- Does `?` open a modal with the verdict glossary, and is the
  glossary sourced from `gold_label_verdict_vocabulary` to keep the
  CLI and web UI in sync (F005)?

verdict: needs_revision
