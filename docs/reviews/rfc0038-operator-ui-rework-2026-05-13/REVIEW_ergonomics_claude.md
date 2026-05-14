# RFC 0038 Operator UI Rework — Ergonomics Design Review (claude)

author: operator [self-declared: rfc0038-review-ergonomics]

Status: review
Date: 2026-05-13
RFC refs: RFC-0038
Spec refs: ENGRAM_UI_REWORK_HANDOFF.md, Spec 0027, RFC 0027, RFC 0028, RFC 0029
Decision refs: D044, D069, D074, D080
Posture: custom:ergonomics_design (operator ergonomics, decision cost, scan order,
keyboard flow, responsive behavior, warning comprehension, design-system fit)

## Scope and method

The handoff explicitly carves out "ergonomics design" as a fourth review lane
alongside privacy, correctness, and operator-contract reviews (RFC 0038 §
"Review Requirements"). This pass restricts itself to that lane: I read the
implementation templates and dispatchers, the shared `src/engram/web/`
package, and the design contract in `ENGRAM_UI_REWORK_HANDOFF.md`. I did not
read other lane reviews, integration evidence, or operator status reports.

Files examined:

- `src/engram/web/templates/_app_shell.html`
- `src/engram/web/templates/_audit_footer.html`
- `src/engram/web/templates/_surface_tabs.html`
- `src/engram/web/templates/_help_modal.html`
- `src/engram/web/templates/_status_chip.html`
- `src/engram/web/templates/_status_banner.html`
- `src/engram/web/templates/_error_banner.html`
- `src/engram/web/templates/_future_slot.html`
- `src/engram/web/templates/_cli_command_card.html`
- `src/engram/web/static/keyboard.js`
- `src/engram/web/chrome.py`
- `src/engram/web/status.py`
- `src/engram/interview/templates/base.html`
- `src/engram/interview/templates/index.html`
- `src/engram/interview/templates/question.html`
- `src/engram/interview/templates/_question_main.html`
- `src/engram/interview/templates/_evidence_excerpt.html`
- `src/engram/bench_review/templates/base.html`
- `src/engram/bench_review/templates/index.html`
- `src/engram/bench_review/templates/segments.html`
- `src/engram/bench_review/templates/segment.html`
- `src/engram/bench_review/templates/summary.html`
- `src/engram/bench_review/templates/excerpt.html`
- `src/engram/bench_review/static/keyboard.js`

## Verdict summary

`needs_revision`. The implementation lands most of the truthful-status, no-CDN,
two-click rationale, and disabled-strong-decision contracts faithfully. But
the operator ergonomics goal — "a single visual system tuned for reading
derived artifacts" with a "single shared chrome" (handoff §1, §3.1) — is not
met. Three independent chrome implementations have shipped: the shared
`src/engram/web/` package the RFC mandates, the interview's inline
`interview/templates/base.html`, and the bench's inline
`bench_review/templates/base.html`. The shared package is wired *into* neither
surface. That fork produces concrete UX defects (broken cross-surface
navigation, a silently inert "Copy command" button on the bench summary, a
help affordance that is a modal in one surface and a `<details>` toggle in
the other, three duplicated keyboard dispatchers, and missing future-slot
cards), drift risk for every future copy change, and a design-system-fit gap
versus the handoff. The findings below are ordered by severity.

## Findings

### F001 — Shared chrome substrate exists but neither surface uses it
Severity: major
Source: src/engram/web/templates/_app_shell.html; src/engram/interview/templates/base.html:1; src/engram/bench_review/templates/base.html:1; ENGRAM_UI_REWORK_HANDOFF.md § 3.1 ("A single shared chrome lives in `src/engram/web/`"); RFC 0038 § "Required Implementation Slices" item 1

The handoff calls for a single shared chrome under `src/engram/web/` that
both surfaces mount inside. Both `_app_shell.html` and its companions
(`_surface_tabs.html`, `_audit_footer.html`, `_help_modal.html`,
`_status_chip.html`, `_status_banner.html`, `_error_banner.html`,
`_future_slot.html`, `_cli_command_card.html`) are present and faithful to
the spec. None of them are extended or included by the interview or bench
templates. The interview's `base.html` (interview/templates/base.html:1)
declares its own `<!doctype html>`, its own duplicate copy of the
`--color-*`, `--space-*`, and `--type-*` design tokens, its own
`#help-modal`, its own audit footer copy, and its own inline keyboard
dispatcher. The bench `base.html` does the same with a third copy of tokens,
a `<details id="help-panel">` instead of a modal, and a different audit
footer template variable (`bind_host`/`bind_port` vs. interview's hard-coded
default `127.0.0.1:8765`). The substrate Python helpers — `chrome.py`,
`status.py`, `origin.py`, `tier.py`, `assets.py` — are also unreferenced from
the rendered DOM as far as the templates show.

Operator-visible consequences:

- The two surfaces look related but feel separate. Header height, tab style
  (underline on interview vs. pill on bench's local nav), and help affordance
  (modal vs. `<details>` toggle) all differ. Design-system fit fails.
- Token drift is now a live risk: a future tweak to `--color-warn` must be
  applied to three files; missing one produces a partially restyled UI.
- The shared `_status_chip.html`, `_status_banner.html`, `_error_banner.html`,
  `_future_slot.html`, and `_cli_command_card.html` partials are dead code
  unless wired in. Both surfaces re-implement chip-like spans inline (e.g.,
  `question.html`'s advisory chip and `index.html`'s ad-hoc "cli-command-card"
  div on the empty-corpus banner).

Recommendation: either (a) make the interview and bench `base.html` files
extend `_app_shell.html` (block-overriding `main` / `head_extra` / `body_extra`)
and include `_help_modal.html`, `_audit_footer.html`, `_surface_tabs.html`;
or (b) remove the shared substrate templates and accept the duplication
explicitly in the RFC. The current "shared exists, nothing uses it" state is
the worst of both worlds and contradicts the RFC's mandate.

### F002 — Cross-surface tab affordance is broken
Severity: major
Source: src/engram/interview/templates/base.html:353–357; src/engram/bench_review/templates/base.html:160–170; ENGRAM_UI_REWORK_HANDOFF.md § 3.1 (surface tab row: "Interview · Bench review · (Entities — future)")

The handoff specifies a shared two-row header where Row 2 is a tab strip
listing every operator surface; the active surface is underlined and the
others are clickable. The shared `_surface_tabs.html` implements this
correctly: `Interview`, `Bench review`, `Entities (future)`, with the
bench link pointing at `/segments?remaining=1&reviewable=1`.

The interview `base.html` instead renders Bench review as a *disabled* span:
```html
<span role="link" aria-disabled="true" title="Bench review runs in its own
  local server">Bench review</span>
```
The bench `base.html` has no cross-surface tab row at all — its `<nav>` is
local-only (`Run` / `Queue` / `Summary`) and never renders an Interview tab.
Result: an operator who clicks the "Bench review" tab inside the interview
surface gets nothing (no `href`); an operator inside bench review has no
visual cue that an interview surface exists in the same workbench.

The handoff anticipates that the two surfaces may bind to different ports
(both surfaces use `--workers 1` and bind loopback). That does not require
disabling cross-surface tabs — the audit footer already shows the active
bind. A reasonable resolution is to have the tabs link to a known
configurable URL (an env var or session-passed URL) and degrade to a
disabled span only when no URL is configured. Today's behavior is the
strictly-worst case: both surfaces hard-code the "you can't get there from
here" outcome.

### F003 — "Copy command" button on bench summary is silently inert
Severity: major
Source: src/engram/bench_review/templates/summary.html:33–38; src/engram/bench_review/static/keyboard.js (no copy handler); ENGRAM_UI_REWORK_HANDOFF.md § 4.14 (export panel) and § 2 flow 8 ("one-click clipboard affordance")

The bench summary renders an Export handoff panel with:
```html
<p><code>engram phase3 bench-review export --review-db PATH --output …</code></p>
<button type="button">Copy command</button>
```
The button has no `data-copy-command` attribute, no `id`, and no `data-action`.
The bench's `keyboard.js` does not register a click listener for copy
behavior (it only handles `/`, `?`, `Escape`, `a`, `r`, `u`, `x`). Clicking
the button does nothing. There is no error feedback. The button looks like
a one-click affordance but is a façade.

By contrast, the interview's inline script *does* wire `data-copy-command`
buttons (`interview/templates/base.html:411–418`). The interview index
template uses that attribute on its empty-corpus banner copy. The bench did
not adopt the same wiring.

This is one of the clearest examples of the harm caused by F001: the shared
`_cli_command_card.html` partial has a working `data-copy-command` button.
If the bench summary used the partial, this defect would not exist. Today
the operator sees a clickable button, presses it, sees no feedback, has to
discover (by trial) that they have to select-and-copy by hand. That is a
trust-eroding ergonomic failure on an explicit "make the CLI handoff easy"
path.

### F004 — Three independent keyboard dispatchers
Severity: major
Source: src/engram/web/static/keyboard.js (unused); src/engram/interview/templates/base.html:391–465 (inline); src/engram/bench_review/static/keyboard.js; ENGRAM_UI_REWORK_HANDOFF.md § 5.1 ("`keyboard.js` … bare-key dispatcher") and § 10.5 ("the dispatcher is per-surface")

The shared dispatcher in `src/engram/web/static/keyboard.js` is elegant: it
binds to any element carrying a `data-key` attribute and respects
`INPUT`/`TEXTAREA`/`SELECT`/`contenteditable` for early-return. Nothing
includes that script. Instead:

- The interview `base.html` inlines its own dispatcher with a hard-coded
  `keyToSelector` map and its own `isTextEntry`/`elementForKey` logic. It
  also inlines `data-copy-command` handling and `htmx:beforeRequest` /
  `htmx:afterRequest` aria-busy toggling — none of which the bench gets.
- The bench `keyboard.js` has its own version with a different selector
  pattern (`button[name="decision"][value="..."]`) and its own
  `engramBenchEditableElementActive` check. It does not implement
  `aria-busy` toggling, `data-copy-command` copy, or accesskey
  passthrough.

Concrete ergonomic effects:

- The bench surface does not visibly disable buttons during the form POST
  → redirect window. The interview does (via the inline `htmx:beforeRequest`
  handler). On a slow machine the bench operator can double-click a decision.
- The bench surface's `?` key opens a `<details>` element in the page
  footer; the interview's `?` opens a centered modal. Both work, neither
  matches the handoff's "the bench inherits the same dispatcher from
  `src/engram/web/`" (§ 4.16).
- The handoff calls for the help-modal `aria-modal="true"` and `role="dialog"`
  attributes (acceptance check 9.6). The bench `<details>` element does not
  satisfy this: `<details>` is not a dialog. A screen-reader user opening
  bench `?` lands inside a disclosure, not a modal.

Recommendation: collapse to one dispatcher (the shared one) and have each
surface's `base.html` register its `data-key` mappings on the buttons it
renders. The shared dispatcher already supports this without per-surface
hard-coded maps.

### F005 — Help affordance on bench has no decision glosses, no state vocab, no shortcut table
Severity: major
Source: src/engram/bench_review/templates/base.html:177–181; ENGRAM_UI_REWORK_HANDOFF.md § 4.16 (Help / shortcuts modal contents)

The handoff says the bench help "Contents" includes decision glosses (the
four-row table from § 4.16), state vocabulary, a keyboard shortcut table,
and the scratch-local disclosure panel. The implementation collapses all of
this to two short paragraphs inside a `<details>` element:
```html
<details id="help-panel">
  <summary>Help</summary>
  <p>Engram runs entirely on your machine. No cloud service. …</p>
  <p>Decisions written here are scratch-local. They do not feed production
     extraction, consolidation, entity review, serving, or Striatum gate state.</p>
</details>
```
A bench operator who presses `?` learns nothing about what `a`, `r`, `u`,
`x`, `/` do. They cannot discover the decision glosses without trial. They
cannot look up what `candidate_zero` vs. `candidate_malformed` means without
hovering the chip and reading the tooltip. Operators in a triage workflow
will hit this within their first hour.

The shared `_help_modal.html` template supports `verdict_help_rows`,
`decision_help_rows`, and `shortcut_rows` blocks. It is unused.

### F006 — Bench segment detail does not render the "does not mutate" warning
Severity: major
Source: src/engram/bench_review/templates/segment.html (no banner); src/engram/bench_review/templates/index.html:3–5; src/engram/bench_review/templates/summary.html:3–5; ENGRAM_UI_REWORK_HANDOFF.md § 6.2 ("Run-decision surface must render the literal banner … move it from `summary.html` body into a persistent header position on `/` and `/summary`")

The persistent banner `Bench review decisions do not mutate production data
or bypass Phase 4 gates.` is rendered on `/` and `/summary` (correct per
§ 6.2). It is *not* rendered on `/segments/{id}`, which is the page where
the operator actually commits decisions. Operators who deep-link into a
segment (e.g., a queue notification or a saved URL) submit decisions
without seeing the disclaimer in the same viewport. That is the moment the
banner exists for. The handoff phrases this as a contract assertion the UI
must encode "everywhere"; the segment detail page is the strongest
operator-trust touchpoint and currently has the weakest disclaimer presence
(only the state-instruction banner above the metrics — which does not
mention promotion).

Recommendation: pull the banner from `index.html` and `summary.html` into a
single included partial (the shared `_status_banner.html` or a dedicated
partial) and include it from `segment.html` as well.

### F007 — Future-slot cards are absent from both surfaces
Severity: major
Source: src/engram/web/templates/_future_slot.html (unused); src/engram/interview/templates/index.html (no future slot); src/engram/bench_review/templates/index.html (no future slot); ENGRAM_UI_REWORK_HANDOFF.md § 3.4

The handoff specifies a `_future_slot.html` partial and calls out where it
must render: "Bench-review run panel carries a *'This decision is
scratch-local; Phase 4 promotion is gated'* persistent note next to the
readiness chip" (§ 3.4), and the interview help modal must end with the
literal Phase 4 disclosure line. The partial exists; it is not included
from any template I read. The interview surface tabs render the disabled
`Entities (future)` span (good), but neither index page renders a
future-slot card that names what's coming next.

The implication for operator comprehension is direct: a first-time user
sees a disabled tab in the header and no other indicator of why or when
that tab would be enabled. A future-slot card on either home page
(`Phase 4 / entities review — not yet built. Tracked in RFC 0021 / D044 /
D069 / D079.`) closes that loop. The asset is built; the rendering is
missing.

### F008 — Scan order on bench `/` buries the resume CTA
Severity: minor
Source: src/engram/bench_review/templates/index.html:1–43; ENGRAM_UI_REWORK_HANDOFF.md § 3.2 (Bench `/` first viewport: "primary resume button")

The handoff places the readiness chip and top counts above the fold, with
the *primary resume button* listed last in the first-viewport set. The
implementation orders the page banner → 5-metric grid → "Run readiness"
heading → readiness panel (where the Resume button lives, inside the
panel) → run-decision panel → "Run metadata" → "Review queues" tabs →
"States" → "Tags". On a 1280×800 viewport, the Resume button is roughly
two scroll-equivalents below the top: the operator scans through the
banner and metrics, then has to look *inside* a panel to find the resume
affordance. That is correct per the literal handoff (resume is in the
readiness panel) but slow for the most common operator action ("pick up
where I left off"). Consider hoisting the resume button to a sticky CTA
slot in the metrics grid or just below it, so it is visible without
scanning the readiness panel.

The same issue applies to the "Start review" empty-state label: it lives
inside the readiness panel rather than as a top-level call to action.

### F009 — Interview new-session form is cramped inline; labels and inputs share a row
Severity: minor
Source: src/engram/interview/templates/index.html:46–57; src/engram/interview/templates/base.html:137 (`form { display: inline; }`)

The new-session form is rendered with inline-flow form layout (no
explicit grid) and the base CSS sets `form { display: inline; }` so labels
and `<input type="number">` controls share a line. The line reads roughly:
```
Number of questions  [10]  Seed  [____]  [Start session]
```
That is acceptable on wide viewports. On 640px and narrower the styling
collapses unpredictably (no media query handles this form), and the input
field for `seed` is the same width as for `n` even though `seed` is
optional. A grid layout with `gap` and a 2-column label/input grid would
respect the handoff's "every row of sibling controls uses CSS grid" rule
(§ 7.1). Today this form is one of the few places that violates that rule.

Minor enough to be cosmetic, but it's the first interaction every new
session uses, so a small density fix has a high frequency × low cost
payoff.

### F010 — Bench segment detail metric row + bench `/` metrics use different metric counts
Severity: minor
Source: src/engram/bench_review/templates/index.html:13–19 (5 metrics: Decided / Remaining / Follow-up / Regressions / Excluded); src/engram/bench_review/templates/summary.html:7–12 (4 metrics: same minus Excluded)

The `/` page shows five top metrics; `/summary` shows four (drops
Excluded). The handoff specifies the four-metric scheme for `/summary` and
a five-metric scheme on `/`. Operators may glance between the two pages
and see the absence of "Excluded" as a count change rather than a layout
change. Add an explicit zero where applicable or keep the metric sets
identical between the two pages (a single shared partial works). A small
ergonomic friction at a comparison surface.

### F011 — Interview index uses an ad-hoc `cli-command-card` instead of the shared partial
Severity: minor
Source: src/engram/interview/templates/index.html:10–14; src/engram/web/templates/_cli_command_card.html

The empty-corpus banner renders a hand-written copy-command block:
```html
<div class="cli-command-card">
  <p class="muted">Refresh current beliefs:</p>
  <code>engram phase4 refresh-current-beliefs</code>
  <button type="button" class="button-link" data-copy-command="engram phase4 refresh-current-beliefs">copy</button>
</div>
```
Functionally fine (this one does have `data-copy-command`, unlike the bench
summary's button). But it does not use the shared `_cli_command_card.html`
partial, which means the visual treatment, ARIA label, and "copied!" state
will drift if either side changes. Drift will eventually produce two CLI
help cards that look slightly different on two surfaces, which is the
exact opposite of the design-system goal.

### F012 — Long IDs (UUIDs, queue fingerprints) can overflow in bench tables/metadata
Severity: minor
Source: src/engram/bench_review/templates/base.html:147 (`code { white-space: nowrap; }`); src/engram/bench_review/templates/index.html:48–53; src/engram/bench_review/templates/segments.html:26

The bench base sets `code { white-space: nowrap }` globally. Inside the
`.claim dd` rule, the handoff's pattern uses `overflow-wrap: anywhere` so
UUIDs in claim cards wrap correctly. The metadata list and the segments
table do not opt back into wrapping. On a 900-px wide viewport with a long
`queue_fingerprint`, the metadata-list `<dd><code>…</code></dd>` row will
push the page's intrinsic width past the viewport, producing a horizontal
scroll bar at the body level. The same happens in the segments table for
the `<td><code>{{ row.segment_id }}</code></td>` cell. Add
`overflow-wrap: anywhere` (or `word-break: break-all` for legacy
browsers) on `td code`, `dd code`, and `.metadata-list code`.

### F013 — Interview question advisory line + version triple + summary triple stack 5+ rows of metadata before evidence
Severity: minor
Source: src/engram/interview/templates/_question_main.html:2–32

A new operator's first viewport on `/sessions/{id}/q/{idx}` reads:

1. Question header line (`Q{idx}/{total} · …`)
2. Version-triple line (small, muted, ~80 chars)
3. Advisory chip + advisory disclosure sentence (~140 chars total)
4. Summary triple (subject → predicate → object)
5. Predicate-intent line
6. (conditional) Subject-kind warning banner
7. Evidence dates line
8. (conditional) Error banner
9. First evidence excerpt

That is 6–9 visual rows of context before evidence even appears. Most are
required by their respective RFCs (predicate intent, advisory disclosure,
version triple) so deleting any one is a contract change. But the version
triple in particular is invariant within a session — it doesn't change
between Q1 and Q10. Wrapping it in a `<details>` (closed by default)
inside the question header would save one row × every question for the
whole session without violating any contract. Same argument applies to
the advisory disclosure: it's identical across questions; a single
session-level banner (rendered once at session start, sticky) would
satisfy the §6.1 requirement ("at least once on the question page")
while saving line height on subsequent questions.

This is a density-tuning suggestion, not a defect, but it's the kind of
thing the handoff explicitly asks for ("dense by default", § 1).

### F014 — Interview `[Abandon]` button styling and copy is inconsistent with the rest of the UI
Severity: minor
Source: src/engram/interview/templates/index.html:35–37

The abandon button label is rendered as `[Abandon]` (literal square
brackets). No other button in the system carries decorative brackets
(Start session, Save and quit, Commit, copy, ✗ false, etc.). The brackets
appear to signal destructiveness, but the button has no danger-color
treatment and no confirm-style two-click flow. Either drop the brackets
and rely on visual weight, or upgrade the button to a danger-class
treatment that matches its destructive semantics. Mismatched signal is
worse than no signal.

### F015 — Bench segment detail has no explicit "Next in queue" affordance
Severity: minor
Source: src/engram/bench_review/templates/segment.html:130; ENGRAM_UI_REWORK_HANDOFF.md § 3.2 (Bench /segments/{id} first viewport: "next-in-queue link")

The handoff's first-viewport list includes a "next-in-queue link" for the
segment detail page. The implementation provides `Back to this queue` as
an `<a class="button">` and relies on the POST-decision route to redirect
to the next segment URL. An operator who wants to scan a segment, decide
*not* to act, and move on must click `Back to this queue` and then click
the next segment. A direct "Next in queue (no decision)" link would make
scan-without-commit a one-click action, matching the scan-density goal.

### F016 — Help button and "shortcuts" button on interview header are visually distinct but functionally identical
Severity: minor
Source: src/engram/interview/templates/base.html:349–351

The interview header renders two adjacent `.button-link` controls:
```html
<button type="button" class="button-link" data-action="help">help</button>
<button type="button" class="button-link" data-action="help">shortcuts</button>
```
Both fire the same handler (`openHelp`) bound on `data-action="help"`.
Two buttons that do the same thing is worse than one button that does
both: it implies a hidden distinction the operator can't find.
Recommend collapsing to one `Help · ?` affordance (the shared chrome
does this with a single `?` button).

### F017 — Disabled "Entities (future)" tab in interview header has different copy from shared substrate
Severity: trivial
Source: src/engram/interview/templates/base.html:356 (`title="Phase 4: not yet built"`); src/engram/web/templates/_surface_tabs.html:10 (`title="Phase 4: not yet built"`); src/engram/web/chrome.py:33–39 (default surface tabs: tooltip = `"Phase 4: not yet built"`)

These match today but exist as three independent literals. F001 covers the
underlying issue; flagged here so any fix updates the literal in one place.

### F018 — Inconsistent verdict button visual differentiation across rationale-required vs. single-click commits
Severity: trivial
Source: src/engram/interview/templates/base.html:179–184; src/engram/interview/templates/_question_main.html:72–101

The CSS uses `text-decoration: underline` styles to differentiate verdict
classes (solid, dotted, dashed). The single-click commits (`true`, `skip`)
use the same underline-thickness as the two-click commits (`false`,
`stale`, `unsupported`, `unsure`). The operator can't tell from the
button which verdict will commit immediately and which opens the
rationale textarea. A small visual cue (e.g., a "commit on click" badge
on single-click buttons, or a hover label) would reduce surprise. Minor;
the accesskey letters carry most of the load via muscle memory after a
few sessions.

### F019 — Audit footer port string drifts between interview and bench
Severity: trivial
Source: src/engram/interview/templates/base.html:469 (`{{ bind_address|default("127.0.0.1:8765") }}`); src/engram/bench_review/templates/base.html:176 (`{{ bind_host }}:{{ bind_port }}`); src/engram/web/chrome.py:43 (`audit_footer_copy(...)`)

The interview footer hard-codes a default of `127.0.0.1:8765` in the
template if the context variable is missing; the bench footer never falls
back. If the interview process binds a non-default port and the template
context is misconfigured, the audit footer will *display a lying address*.
The shared `chrome.audit_footer_copy(...)` helper handles this correctly
but is unused. The defensive value of an audit footer is the literal
truthfulness of its bind address; a stale default undermines the entire
"don't lie to the operator" contract.

## Positive notes (what the implementation gets right)

These are worth recording so synthesis doesn't undo them.

- The two-click rationale flow (interview question.html) is clean: a
  single hidden `<input type="hidden" name="verdict">`, JS toggles the
  rationale area on click, focus jumps to the textarea, Shift+Enter
  submits. No surprises.
- `accesskey="n"` on `unsupported` and `accesskey="u"` on `unsure` are
  preserved exactly per handoff § 4.2; the comment is even in the JS.
- Bench strong-decision disabling on `candidate_malformed` /
  `candidate_missing` / `prior_missing` is correct, includes the literal
  tooltip copy, and applies to both buttons.
- Advisory chip + disclosure sentence appears on every question render
  (§ 6.1 satisfied on the question page; F006 only flags the bench
  segment side).
- Status-chip color/border treatment for `proposed` and `ready` uses
  warn-muted, not ok — § 6.2 satisfied where the chip renders.
- The interview surface respects the predicate-intent + subject-kind
  warning visibility requirement from RFC 0028: intent line is muted, the
  warning is a banner-warn block.
- htmx fragments preserve `<main id="main">` and the `data-live-status`
  attribute, so the aria-live region updates on swap.

## Suggested verdict

`needs_revision`. The shared chrome F001 is the load-bearing fix; F002 /
F003 / F004 / F005 / F006 / F007 all dissolve when F001 is resolved
because they are each consequences of the substrate not being wired in.
F008–F019 are independent ergonomics nits that should be addressed during
the polish pass.

Pre-merge: F001–F007 should be resolved (the substrate is wired, the
inert button removed, the warning banner present on segment detail, the
bench help has decision/state/shortcut tables, future-slot cards render).
F008–F019 can land as follow-up polish but should be tracked in the
findings ledger so they aren't lost.
