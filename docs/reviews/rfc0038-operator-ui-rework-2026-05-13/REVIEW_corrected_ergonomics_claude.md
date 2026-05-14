---
schema_version: "striatum.finding.v1"
artifact_kind: "finding"
verdict_intent: "accept_with_findings"
severity: "medium"
---

author: operator [self-declared: rfc0038-corrected-ergonomics-review]

# RFC 0038 Operator UI Rework — Corrected Follow-up Ergonomics Review (claude)

Status: review
Date: 2026-05-13
RFC refs: RFC-0038
Spec refs: ENGRAM_UI_REWORK_HANDOFF.md, Spec 0027, RFC 0027, RFC 0028, RFC 0029
Decision refs: D044, D069, D074, D080, D081
Posture: custom:ergonomics_dx (first-time-user discoverability, decision cost,
scan order, keyboard flow, responsive behavior, warning comprehension,
design-system fit)
Round: corrected follow-up after substrate-wiring repair and DB-route repair
Prior tainted round: docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_followup_ergonomics_claude.md
Originating round: docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_ergonomics_claude.md

## Scope and method

The corrected packet supplies the actual `src/engram/web`, interview, and bench
source surfaces, the DB-route repair handoff
(`REPAIR_DB_ROUTE_HANDOFF.md`), and the pass-verdict follow-up evidence
(`REPAIR_FOLLOWUP_EVIDENCE.md`). The prior follow-up round ran under a
`document_only` policy and could not see the source, so it carried every
F-finding forward unchanged. This pass re-reads the source and reports the
real disposition.

Files re-examined for this round:

- `src/engram/web/templates/_app_shell.html`,
  `_surface_tabs.html`, `_audit_footer.html`, `_help_modal.html`,
  `_status_chip.html`, `_status_banner.html`, `_error_banner.html`,
  `_future_slot.html`, `_cli_command_card.html`
- `src/engram/web/static/keyboard.js`
- `src/engram/web/{chrome,status,assets,origin,tier}.py`
- `src/engram/interview/templates/{base,index,question,_question_content,_question_main,_question_script,_evidence_excerpt,_strata_strip}.html`
- `src/engram/interview/web.py`
- `src/engram/bench_review/templates/{base,index,segments,segment,summary,excerpt}.html`
- `src/engram/bench_review/static/keyboard.js`
- `src/engram/bench_review/web.py`
- `tests/test_web_ui_shared.py`, `tests/test_interview_web.py`,
  `tests/test_bench_review.py`

## Verdict summary

`accept_with_findings`.

The repair lane delivered the load-bearing substrate wiring: both
`src/engram/interview/templates/base.html` and
`src/engram/bench_review/templates/base.html` now begin with
`{% extends "_app_shell.html" %}`, and both surfaces include the shared
`_help_modal.html`, `_audit_footer.html`, `_surface_tabs.html`,
`_status_banner.html`, `_future_slot.html`, and `_cli_command_card.html`
partials at the right insertion points. The DB-route repair (per
`REPAIR_DB_ROUTE_HANDOFF.md` and `REPAIR_FOLLOWUP_EVIDENCE.md`) closes the
remaining red test, so the route-level acceptance assertion that backs the
predicate-intent / subject-kind ergonomics affordance is green. Most of
F001–F019 are demonstrably resolved.

What still warrants follow-up: the interview→bench cross-surface tab is
asymmetrically configured (the bench knows the interview URL via env var,
but the interview has no equivalent for the bench, so the tab is hard-coded
to a path that 404s on the interview's own port — and a route test now
codifies that broken href). Three minor / trivial polish items also remain
open. None of these are blockers for the substrate intent; they are
follow-up polish that should be tracked.

## Finding dispositions (carried from the originating round)

Severity classes match the originating round.

### F001 — Shared chrome substrate exists but neither surface uses it
Disposition: **resolved.**
- `src/engram/interview/templates/base.html:1` → `{% extends "_app_shell.html" %}`.
- `src/engram/bench_review/templates/base.html:1` → `{% extends "_app_shell.html" %}`.
- The duplicate inline design tokens, audit footer, help modal, and header
  CSS that were the centerpiece of F001 are gone from both surface
  `base.html` files; both now scope their own CSS to surface-specific
  selectors (interview's verdict-row, evidence-row, etc.; bench's grid,
  panel, claim, chip-readiness rules) and delegate chrome to the shell.
- `tests/test_web_ui_shared.py` enforces the substrate-side contract; the
  interview/bench TestClient suites (`tests/test_interview_web.py:319–326`
  and `tests/test_bench_review.py:321–334, 403, 454–458`) assert the
  shared shell markers in rendered HTML.

### F002 — Cross-surface tab affordance is broken
Disposition: **partially resolved (one direction still broken).** See
[FU101] below.
- `_surface_tabs.html` now renders real `<a>` links for both tabs and a
  disabled `<span>` for Entities.
- Bench provides `interview_url` from the
  `ENGRAM_BENCH_REVIEW_INTERVIEW_URL` env var (default
  `http://127.0.0.1:8765/`) and `bench_url="/segments?remaining=1&reviewable=1"`,
  so the bench surface's Interview tab points to the configured cross-port URL.
- Interview's `_base_context` (`src/engram/interview/web.py:290`) does not
  set `bench_url` and does not read any `ENGRAM_INTERVIEW_BENCH_URL` env var.
  The template default `/segments?remaining=1&reviewable=1` is therefore
  emitted as a same-origin link on the interview port; the interview app
  has no `/segments` route, so the click is a guaranteed 404.

### F003 — "Copy command" button on bench summary is silently inert
Disposition: **resolved.**
- `src/engram/bench_review/templates/summary.html:33–36` now wraps the
  export command with `{% include "_cli_command_card.html" %}`, which emits
  a `<button data-copy-command="...">copy</button>`. Bench's
  `static/keyboard.js` (lines 79–99, 129–133) handles `[data-copy-command]`
  click events with a clipboard primary path and a `document.execCommand`
  fallback, plus a transient "copied" affordance.
- `tests/test_bench_review.py:454–458` locks the wiring (`data-copy-command`
  attribute on the export panel, and the substrate copy in the visible HTML).

### F004 — Three independent keyboard dispatchers
Disposition: **partially resolved (one of three remains as net-new
divergence).** See [FU102] and [FU104] below.
- The shared dispatcher (`src/engram/web/static/keyboard.js`) is now wired
  into the interview surface via `keyboard_static_url="/shared-static/keyboard.js"`
  in `interview/web.py:296` and the `/shared-static` mount at
  `interview/web.py:765–769`. The interview's old inline dispatcher is gone.
- The bench surface still serves its own
  `src/engram/bench_review/static/keyboard.js` (mounted at `/static`); the
  shared dispatcher is duplicated and extended in the bench's copy with a
  bench-specific `/`-to-`#queue-filter` focus handler and a `tbody tr`
  client-side filter. Bench does not load the shared script.
- The interview `base.html:198–225` still inlines a small `body_extra`
  script that (a) re-binds `data-copy-command` click handlers and (b) sets
  `aria-busy` + disables buttons on `htmx:beforeRequest` / re-enables on
  `htmx:afterRequest`. The copy-command portion now duplicates the shared
  keyboard.js (both call `navigator.clipboard.writeText`); the htmx busy
  state is genuinely additional.

### F005 — Bench help has no decision glosses, no state vocab, no shortcut table
Disposition: **resolved.**
- `bench_review/web.py:31–53` exports `BENCH_DECISION_HELP_ROWS` and
  `BENCH_SHORTCUT_ROWS`. `web.py:90–111` passes both into the Jinja env as
  globals (`decision_help_rows`, `shortcut_rows`, `disclosure_lines`,
  `help_title="Bench review help"`, `verdict_help_rows=()` empty).
- `_help_modal.html` renders the Decisions and Shortcuts tables and the
  scratch-local disclosure lines.
- `tests/test_bench_review.py:332–334` asserts both the modal title and
  the local-only audit footer copy.

### F006 — Bench segment detail does not render the "does not mutate" warning
Disposition: **resolved.**
- `bench_review/templates/segment.html:3–6` includes `_status_banner.html`
  with `kind="warn"` and `message=bench_disclaimer` at the top of the
  segment-detail page, immediately above the segment-id heading.
- The same partial is included from `index.html:3–5` and `summary.html:3–5`,
  so the disclaimer is on every page where a decision can be committed.
- `tests/test_bench_review.py:321, 403, 458` assert the literal disclaimer
  on the relevant pages.

### F007 — Future-slot cards are absent from both surfaces
Disposition: **resolved.**
- `interview/templates/index.html:57–59` wraps `_future_slot.html` with a
  `{% with title=..., subtitle=..., references=... %}` block.
- `bench_review/templates/index.html:45–47` does the same.
- `tests/test_interview_web.py:337–339` and the substrate test in
  `tests/test_web_ui_shared.py:122–136` assert the rendered future-slot
  copy.

### F008 — Scan order on bench `/` buries the resume CTA
Disposition: **carry forward (minor).**
- `bench_review/templates/index.html` renders the metric grid first
  (`<section class="grid">`), then the `<h2>Run readiness</h2>` heading,
  then the readiness panel containing the resume button (`a.button` or
  disabled `span`). The Resume affordance is still inside the readiness
  panel and below the metrics, which is the structure the prior round
  flagged.
- The implementation literally satisfies the handoff (resume is in the
  readiness panel) but the prior round's recommendation to hoist the CTA
  closer to the metrics for "pick up where I left off" speed remains
  unaddressed.

### F009 — Interview new-session form is cramped inline
Disposition: **resolved.**
- `interview/templates/base.html:48–53` defines a `.new-session-form` CSS
  grid (`grid-template-columns: auto minmax(5rem, 8rem) auto minmax(8rem, 1fr) auto`)
  and `index.html:46–54` applies the class to the form. A
  `@media (max-width: 720px)` rule (base.html:168–173) collapses the grid
  to a single column on narrow screens.

### F010 — Bench segment-detail vs. `/` metric sets differ (5 vs. 4)
Disposition: **carry forward (minor).**
- `bench_review/templates/index.html:13–19` renders five metrics including
  Excluded. `summary.html:7–12` renders four (no Excluded). The
  inconsistency the prior round flagged is unchanged.

### F011 — Interview index uses an ad-hoc `cli-command-card` instead of the shared partial
Disposition: **resolved.**
- `interview/templates/index.html:9–11` now uses
  `{% with command="engram phase4 refresh-current-beliefs", description="Refresh current beliefs:" %}{% include "_cli_command_card.html" %}{% endwith %}`.

### F012 — Long IDs (UUIDs, queue fingerprints) can overflow in bench tables/metadata
Disposition: **resolved.**
- `bench_review/templates/base.html:190–199` sets `code { white-space: normal; overflow-wrap: anywhere; }` and `td code, dd code, .metadata-list code { overflow-wrap: anywhere; word-break: break-word; }`. This replaces the old `code { white-space: nowrap }` rule that caused overflow.

### F013 — Interview question stacks 6–9 rows of metadata before evidence
Disposition: **carry forward (minor, density suggestion).**
- `interview/templates/_question_content.html:1–32` still renders the
  header line, version triple, advisory chip + sentence, summary triple,
  predicate intent, conditional warning banner, and evidence dates line
  before the evidence section. The prior round's suggestion to fold the
  version triple into a closed `<details>` to save one row per question
  is not adopted (and was explicitly framed as optional).

### F014 — Interview `[Abandon]` button has decorative brackets and no danger treatment
Disposition: **resolved.**
- `interview/templates/index.html:33–34` renders `<button class="danger-action" type="submit" ...>Abandon</button>` — no brackets, and `base.html:58–61` styles `.danger-action` with the danger color and border tokens.

### F015 — Bench segment detail has no explicit "Next in queue" affordance
Disposition: **carry forward (minor).**
- `bench_review/templates/segment.html:133` still renders only `Back to this queue`. The handoff's "Next in queue (no decision)" affordance is not present.

### F016 — Help and "shortcuts" buttons on interview header are functionally identical
Disposition: **resolved.**
- The two duplicate `<button class="button-link" data-action="help">` buttons in the previous interview `base.html` header are gone. The shared `_app_shell.html:300–302` renders a single `<button data-help-open data-key="?" aria-label="Open help">?</button>` in the header actions.

### F017 — Disabled "Entities (future)" tab tooltip duplicated in three places
Disposition: **carry forward (trivial, partly addressed).**
- The literal `title="Phase 4: not yet built"` lives in
  `src/engram/web/templates/_surface_tabs.html:10` and in
  `src/engram/web/chrome.py:36` (`DEFAULT_SURFACE_TABS`). The interview's
  inline copy is gone (the surface now uses the shared template). The
  remaining redundancy is two literals, not three; the `chrome.py`
  constant is currently unused at render time (the template doesn't read
  from it). Either consume `DEFAULT_SURFACE_TABS` from the template (via
  context-pass) or remove it. Marked as a code-hygiene cleanup.

### F018 — Single-click and two-click verdict buttons are visually indistinguishable
Disposition: **carry forward (trivial).**
- `interview/templates/_question_content.html:70–101` adds verdict icons
  (`✓`, `✗`, `⌛`, `⚠`, `?`, `»`) alongside the underline styles. Icons
  help, but they don't directly cue "commit on click vs. rationale
  required." The prior round's recommendation (an explicit "commit on
  click" badge on `true`/`skip`) was not adopted.

### F019 — Audit footer port-string drifts between interview and bench
Disposition: **resolved.**
- Both surfaces now render the shared `_audit_footer.html`. Interview
  passes `bind_address` via `_bind_address_for_request(...)` in
  `interview/web.py:282–287`; bench passes `bind_address=f"{host}:{port}"`
  via the Jinja env globals in `bench_review/web.py:90–96`. The shared
  template falls back to `"127.0.0.1:<port>"` if missing — both surfaces
  pass a real value in practice.

## Net-new findings (FU1xx, from this round)

### FU101 — Interview → bench cross-surface tab is a confidently broken link
Severity: major
Source: src/engram/interview/web.py:290–317 (`_base_context` does not set
`bench_url`); src/engram/web/templates/_surface_tabs.html:5
(`href="{{ bench_url|default('/segments?remaining=1&reviewable=1') }}"`);
tests/test_interview_web.py:323
(`assert 'href="/segments?remaining=1&amp;reviewable=1">Bench review</a>' in body`);
src/engram/bench_review/web.py:30
(`INTERVIEW_URL: str = os.environ.get("ENGRAM_BENCH_REVIEW_INTERVIEW_URL", "http://127.0.0.1:8765/")`)

The bench surface knows how to reach the interview surface: an env var
(`ENGRAM_BENCH_REVIEW_INTERVIEW_URL`) seeds the `interview_url` template
variable with a sensible default. The interview surface has no symmetric
configuration — no `ENGRAM_INTERVIEW_BENCH_URL` env var, no `bench_url`
override in `_base_context`. The template default for `bench_url` is the
relative path `/segments?remaining=1&reviewable=1`, which is a same-origin
link to the interview's own port. The interview FastAPI app does not
register a `/segments` route, so the click returns a 404 (with the JSON
error envelope from the interview's exception handler — not a friendly
404 page).

A first-time operator dropped into the interview surface will see what
looks like a normal cross-surface tab. They will click it. They will get
a 404 / "Detail: Not Found" envelope. That is a sharper trust failure than
the prior `aria-disabled` span the original review flagged, because a live
link is a promise of navigation. The asymmetry — bench knows about
interview; interview is uninformed about bench — is the root cause; the
test at `test_interview_web.py:323` then pins the broken href in place,
so any fix has to update the test too.

Recommendation: mirror the bench's env-var pattern in interview
(`ENGRAM_INTERVIEW_BENCH_URL`, default `http://127.0.0.1:8770/segments?remaining=1&reviewable=1`),
inject it into `_base_context`, and degrade to a `is-disabled` span when
no URL is configured. Update `test_index_renders_no_open_sessions` to
assert the configured URL (or the disabled-span state when unset). Five-
line change in the route module + one test update; small enough to land as
a focused follow-up.

### FU102 — Bench surface duplicates the keyboard dispatcher rather than consuming the shared one
Severity: minor
Source: src/engram/bench_review/static/keyboard.js (179 lines, near-clone
of shared dispatcher + queue-filter logic);
src/engram/bench_review/web.py:104
(`keyboard_static_url="/static/keyboard.js"`);
src/engram/web/static/keyboard.js (133 lines, the shared dispatcher)

The shared `engram.web/static/keyboard.js` already implements `data-key`,
`data-help-open`/`data-help-close`, `data-copy-command`, the textarea
short-circuit, htmx-aware focus restoration, and the live-region update.
The bench's own copy reimplements all of that and adds two
bench-specific behaviors: `/` focuses `#queue-filter`, and the input
event filters `tbody tr` by needle match.

A consolidated approach: keep a shared keyboard.js, and let the bench
register the queue-filter behavior as a small additional script (or load
`/shared-static/keyboard.js` first, then a tiny bench-only enhancement).
The current state means: a future fix to the shared `markCopied` /
`copyCommand` won't reach bench, and a future tweak to bench (e.g.,
focus-on-swap behavior) won't reach interview. Drift risk is the same
class as the F001 substrate-fork the prior round called out, just
narrower in scope.

This is minor because the bench dispatcher works today and the duplication
is small (~50 lines of additional surface-specific logic). Tracking it as
a follow-up keeps the design-system goal intact.

### FU103 — Interview save-and-quit banner uses a bespoke class instead of the shared partial
Severity: minor
Source: src/engram/interview/templates/index.html:17–21
(`<section ... class="banner-status">{{ save_and_quit_banner }}</section>`);
src/engram/interview/templates/base.html:126–133 (defines `.banner-status`
locally); src/engram/web/templates/_status_banner.html (provides the
shared banner vocabulary)

The interview's empty-corpus banner and save-and-quit banner are rendered
with a surface-local `.banner-status` class instead of via
`_status_banner.html`. Functionally they look similar (both apply a
warn-toned background + left border), but the design-system goal is that
banner semantics live in `_status_banner.html` and the shared `.banner`
variants. As a result, a future change to "warn-styled banners across the
operator UI" has to touch interview/base.html separately.

Recommendation: replace the two `.banner-status` sections with
`{% with kind="warn", message=empty_corpus_banner_text %}{% include "_status_banner.html" %}{% endwith %}` (and likewise for save-and-quit).
Then drop the `.banner-status` rule from interview/base.html. Equivalent
visual treatment, one less surface-local class.

### FU104 — Interview `body_extra` retains a duplicate copy-command handler
Severity: trivial
Source: src/engram/interview/templates/base.html:198–225 (`document.querySelectorAll('[data-copy-command]').forEach(...)` and htmx busy toggling); src/engram/web/static/keyboard.js:80–86

The shared keyboard.js is loaded by the interview (per
`keyboard_static_url="/shared-static/keyboard.js"`). It already binds a
click delegator for `[data-copy-command]` that writes to the clipboard.
The inline interview `body_extra` script then walks every
`[data-copy-command]` at DOMContentLoaded and binds *another* click
handler that also writes to the clipboard. Both fire on each click. The
write itself is idempotent (clipboard is replaced with the same text), so
the user-visible effect is correct. But the handlers are not free:

- A future change to the shared handler's behavior (e.g., adding a
  "copied" affordance, an error path, or analytics — though we don't do
  analytics here) won't be observed by the interview because the inline
  handler runs first and short-circuits the visual feedback.
- The reverse is also true: a future tweak in `body_extra` won't reach
  the bench.

The htmx `beforeRequest` / `afterRequest` aria-busy toggling in the same
script is genuinely surface-specific and isn't covered by the shared
keyboard.js — that part should either move into the shared keyboard.js
(if both surfaces want it) or stay surface-local.

Recommendation: drop the `[data-copy-command]` forEach loop from
interview `body_extra`; leave the htmx busy toggling. Three-line fix.

### FU105 — `chrome.DEFAULT_SURFACE_TABS` is dead code at render time
Severity: trivial
Source: src/engram/web/chrome.py:28–38; src/engram/web/templates/_surface_tabs.html

`DEFAULT_SURFACE_TABS` declares the canonical tab vocabulary (label, href,
future, tooltip) in Python, but the template renders three hard-coded
`<a>` / `<span>` elements with literal text and its own
`interview_url|default(...)` / `bench_url|default(...)` fallbacks. The
Python constant is referenced nowhere outside its own module.

Recommendation: either iterate the constant from the template (pass
`surface_tabs=DEFAULT_SURFACE_TABS` into context and `{% for tab in surface_tabs %}`)
or delete the constant. The current state is a future-drift hazard:
someone will update the literal in chrome.py thinking it changes the UI,
and it won't.

## Positive notes carried forward from the originating round

These remain true and the repair lane preserved them; recording so
synthesis doesn't undo them.

- The two-click rationale flow (interview question.html) remains clean:
  hidden `<input type="hidden" name="verdict">`, JS toggles the rationale
  area on click of a two-click verdict, focus jumps to textarea,
  Shift+Enter submits. The dispatcher is now in `_question_script.html`
  but the contract is intact.
- `accesskey="n"` on `unsupported` and `accesskey="u"` on `unsure` are
  preserved per handoff §4.2; the `data-key` attributes mirror them.
- Bench strong-decision disabling on `candidate_malformed` /
  `candidate_missing` / `prior_missing` is correct with the same literal
  tooltip on both buttons; `metadata_only` sessions also disable all four
  decision buttons.
- Advisory chip + disclosure sentence still render on every question
  page; the bench segment-detail page now ALSO carries the
  "does not mutate" disclaimer (F006).
- Status-chip color/border treatment for `proposed` and `ready` uses
  warn-muted, not ok — §6.2 honored.
- The interview surface still respects the predicate-intent +
  subject-kind warning visibility requirement from RFC 0028 (intent line
  muted, warning is a banner block); the DB-route repair ensures the
  test for this affordance is now green per `REPAIR_FOLLOWUP_EVIDENCE.md`.
- htmx fragments preserve the `<main id="main">` swap target and the
  `data-live-status` attribute. `_question_main.html` re-establishes
  `<main id="main">` on partial swaps so the shared keyboard.js
  focus-restoration still fires.
- No-CDN/external-asset invariant continues to hold per the substrate
  test (`test_shared_resources_have_no_external_asset_references` in
  `tests/test_web_ui_shared.py`) and per the followup evidence's
  "checked 27 shared/interview/bench template/static resources; no
  external asset markers found" line.

## What changed in this round vs. the prior tainted round

The tainted follow-up review (`REVIEW_followup_ergonomics_claude.md`)
carried every F-finding forward at original severity because it operated
without source access. With source access:

- F001, F003, F005, F006, F007, F009, F011, F012, F014, F016, F019 are
  resolved.
- F002 is partially resolved (the bench-side is fixed; the
  interview-side is broken in a more confident way — see FU101).
- F004 is partially resolved (interview consumes the shared dispatcher;
  bench still duplicates it).
- F008, F010, F013, F015 remain as carry-forward minor items (no defect,
  but no improvement either — should be tracked).
- F017, F018 remain as carry-forward trivial items.
- FU101–FU105 are net-new findings surfaced by reading the current
  source.

The FU001–FU005 findings in the prior tainted round were policy /
process observations about the repair workflow, not new UI defects;
they no longer apply now that this corrected pass has happened and the
DB-route repair has landed.

## Suggested verdict

`accept_with_findings`.

The substrate wiring contract is met. The first-time operator who lands
on either index page now sees a consistent shared chrome (brand line,
surface tabs, audit footer, future-slot card, scratch-local disclaimer
on bench, advisory disclaimer on interview, and a single `?` help button
that opens a real `role="dialog"` modal with decision glosses and
shortcuts). The remaining ergonomics gap — interview → bench is a 404 —
is small and has a five-line fix; tracking it as a focused follow-up
rather than another review cycle is the right move.

Follow-up items to track (none merge-blocking):

- FU101 (major-ish) — interview needs `ENGRAM_INTERVIEW_BENCH_URL`-style
  env var and disabled-span degradation when unset. Update
  `test_index_renders_no_open_sessions` accordingly.
- FU102 (minor) — consolidate the bench keyboard dispatcher onto the
  shared one + a small bench-only enhancement layer for queue filtering.
- FU103 (minor) — replace interview's `.banner-status` sections with
  `_status_banner.html` includes.
- FU104 (trivial) — drop the duplicate `[data-copy-command]` handler from
  interview `body_extra`; keep the htmx busy toggling.
- FU105 (trivial) — either consume `chrome.DEFAULT_SURFACE_TABS` from
  `_surface_tabs.html` or remove the constant.
- F008, F010, F013, F015 (minor) — original density / scan-order / metric
  parity / next-in-queue polish items, still open.
- F017, F018 (trivial) — original tooltip-literal redundancy and
  commit-vs-rationale visual cue, still open.

End of corrected ergonomics review.
