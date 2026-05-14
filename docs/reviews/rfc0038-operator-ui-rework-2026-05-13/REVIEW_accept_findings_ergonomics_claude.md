---
schema_version: "striatum.finding.v1"
artifact_kind: "finding"
verdict_intent: "accept"
severity: "low"
---

author: operator [self-declared: rfc0038-accept-findings-ergonomics-review]

# RFC 0038 Operator UI Rework — Accept-with-Findings Ergonomics Review (claude)

Status: review
Date: 2026-05-13
RFC refs: RFC-0038
Spec refs: ENGRAM_UI_REWORK_HANDOFF.md, Spec 0027, RFC 0027, RFC 0028, RFC 0029
Decision refs: D044, D069, D074, D080, D081
Posture: custom:ergonomics_dx (first-time-user discoverability, decision cost,
scan order, keyboard flow, banner/status semantics, design-system fit)
Round: fresh-context review of the accept-with-findings follow-ups
Prior corrected round: docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_corrected_ergonomics_claude.md
Evidence packet: docs/reviews/rfc0038-operator-ui-rework-2026-05-13/ACCEPT_FINDINGS_EVIDENCE.md

## Scope and method

This is a fresh-context ergonomics pass over the accept-with-findings repair
lane: interview navigation (`ACCEPT_FINDINGS_INTERVIEW_HANDOFF.md`), bench
keyboard cleanup (`ACCEPT_FINDINGS_BENCH_HANDOFF.md`), and shared chrome dead
code cleanup (`ACCEPT_FINDINGS_SHARED_HANDOFF.md`). Verdict criterion from the
work-packet review policy: "verdict acceptance means the affordances are
discoverable and consistent."

Files re-examined against the corrected round's open findings (FU101–FU105
and the carry-forward F-items):

- `src/engram/interview/web.py`, `src/engram/interview/templates/{base,index,question,_question_content,_question_main,_question_script,_evidence_excerpt}.html`
- `src/engram/bench_review/web.py`, `src/engram/bench_review/templates/{base,index,segments,segment,summary,excerpt}.html`,
  `src/engram/bench_review/static/queue_filter.js`
- `src/engram/web/{chrome,assets,origin,status,tier}.py`,
  `src/engram/web/templates/{_app_shell,_surface_tabs,_audit_footer,_help_modal,_status_banner,_cli_command_card,_future_slot}.html`,
  `src/engram/web/static/keyboard.js`
- `tests/test_web_ui_shared.py`, `tests/test_interview_web.py`,
  `tests/test_bench_review.py`

## Verdict summary

`accept`.

The five net-new ergonomics findings from the corrected round (FU101 major,
FU102–FU104 minor/trivial, FU105 trivial) are demonstrably resolved against
the current source, and the F017 dead-literal redundancy is collaterally
resolved by the same cleanup. Tests now mechanically pin each fix in place
(`test_chrome_does_not_define_parallel_surface_tab_defaults`,
`test_index_renders_no_open_sessions` asserting the configured cross-port
bench URL and `banner-status not in body`,
`test_bench_loads_shared_keyboard_and_queue_filter_enhancement` proving the
shared dispatcher carries copy/help bindings while `queue_filter.js` carries
only queue-filter behavior, `test_interview_bench_url_resolver_defaults_and_overrides`,
`test_index_uses_configured_bench_url`).

The first-time operator landing on either index page now sees:

- a consistent shared chrome (brand line, surface tabs, audit footer, `?`
  help button) that is a single source of truth (`_app_shell.html`);
- cross-surface tabs that actually navigate in both directions on default
  cross-port URLs (`http://127.0.0.1:8765/` and
  `http://127.0.0.1:8770/segments?remaining=1&reviewable=1`), overridable
  by symmetric env vars;
- one shared keyboard dispatcher (`/shared-static/keyboard.js`) handling
  `data-key`, `data-help-open`, `data-copy-command`, plus a tiny
  bench-only enhancement (`queue_filter.js`) for `/`-focus + tbody filter;
- shared status banners (`_status_banner.html`) for both empty-corpus and
  save-and-quit messages on the interview surface, replacing the previous
  `.banner-status` bespoke class;
- no duplicate `[data-copy-command]` handler — the interview `body_extra`
  retains only the surface-specific htmx busy-state toggle.

The previously dead `chrome.DEFAULT_SURFACE_TABS` constant is removed; its
removal also collapses the duplicate `title="Phase 4: not yet built"` literal
to a single canonical location in `_surface_tabs.html`.

The carry-forward minor/trivial polish items (F008/F010/F013/F015/F018) are
explicitly out of scope per `ACCEPT_FINDINGS_EVIDENCE.md` § "Residual Risk"
and remain open. That honesty matters; this verdict accepts the substrate
state with those items recorded for routine UI polish.

## FU finding dispositions

### FU101 — Interview → bench cross-surface tab was a guaranteed 404
Disposition: **resolved.**

- `src/engram/interview/web.py:113–126` defines `_resolve_bench_review_url`
  reading `ENGRAM_INTERVIEW_BENCH_URL` (env var) with module-level default
  `http://127.0.0.1:8770/segments?remaining=1&reviewable=1`. This mirrors
  the bench's `ENGRAM_BENCH_REVIEW_INTERVIEW_URL` pattern.
- `interview/web.py:740–752`: `create_app(..., bench_url=BENCH_REVIEW_URL)`
  stores the resolved URL on `app.state.engram_bench_url`.
- `interview/web.py:278–306`: `_base_context` puts the URL into
  `bench_url`, and `_app_shell.html` → `_surface_tabs.html` renders it as
  a real `<a href>` on the Bench review tab.
- Tests: `tests/test_interview_web.py:312–333`
  (`test_index_renders_no_open_sessions`) now asserts
  `href="http://127.0.0.1:8770/segments?remaining=1&amp;reviewable=1">Bench review</a>`
  on the rendered body. `test_index_uses_configured_bench_url` (lines
  336–349) covers the app-factory override path.
  `test_interview_bench_url_resolver_defaults_and_overrides` (lines
  938–948) pins the env-var resolver.

A first-time operator on the interview surface can now click the Bench
review tab and reach the bench surface running on the default port without
ever editing config. The asymmetry that produced the 404 is gone.

### FU102 — Bench duplicated the keyboard dispatcher
Disposition: **resolved.**

- `src/engram/bench_review/web.py:105`:
  `keyboard_static_url="/shared-static/keyboard.js"` (was
  `/static/keyboard.js` pointing at the bench's own clone).
- `bench_review/web.py:114–118` mounts `/shared-static` from
  `engram.web.assets.static_dir()`.
- `src/engram/bench_review/static/keyboard.js` is removed; the directory
  now contains only `htmx.min.js` and the new `queue_filter.js`.
- `src/engram/bench_review/static/queue_filter.js` is a 43-line bench-only
  enhancement that handles two things and only two things: `/` focuses
  `#queue-filter`, and the input event filters `tbody tr` by needle.
- Bench's `base.html:7` includes `queue_filter.js`; the shared keyboard
  script is loaded via the shell-level `<script
  src="{{ keyboard_static_url|default('/static/keyboard.js') }}" defer>`
  in `_app_shell.html:287`.
- Tests: `tests/test_bench_review.py:336–338` asserts both scripts load
  and that the bench's old `/static/keyboard.js` is gone.
  `test_bench_loads_shared_keyboard_and_queue_filter_enhancement`
  (lines 352–368) proves the shared dispatcher carries
  `[data-copy-command]` and `data-help-open` bindings while
  `queue_filter.js` carries neither — i.e., real consolidation, not a
  cosmetic rename.

The shared/enhancement split is the right shape for design-system drift:
a future change to copy-command or help-modal behavior reaches the bench
automatically.

### FU103 — Interview banners used a bespoke `.banner-status` class
Disposition: **resolved.**

- `src/engram/interview/templates/index.html:6–25`: both the empty-corpus
  banner and the save-and-quit banner now use
  `{% include "_status_banner.html" %}` with `kind="warn"`.
- The empty-corpus banner additionally pairs the shared status banner
  with `_cli_command_card.html` for the `engram phase4
  refresh-current-beliefs` command, which gets a real copy button via the
  shared keyboard.js.
- `src/engram/interview/templates/base.html` no longer defines a
  `.banner-status` rule (the previous local-CSS block is gone; the only
  remaining banner-shaped rule is the inline `.banner-warn` padding
  override at lines 126–128, which is style polish on top of the shared
  `.banner-warn` declared in `_app_shell.html:173`).
- Test: `tests/test_interview_web.py:333` asserts `"banner-status" not in
  body`, mechanically locking the bespoke class out.

### FU104 — Interview `body_extra` retained a duplicate copy-command handler
Disposition: **resolved.**

- `src/engram/interview/templates/base.html:192–213` `body_extra` now
  contains only the htmx busy-state toggle
  (`htmx:beforeRequest`/`htmx:afterRequest` aria-busy + button disable).
  The previous `document.querySelectorAll('[data-copy-command]').forEach
  (...)` block is gone.
- The shared `keyboard.js` is the sole binder for copy-command clicks.
- Implication: a future change to the shared copy-command behavior
  (e.g., a refined "copied" affordance) will now reach the interview
  surface automatically.

### FU105 — `chrome.DEFAULT_SURFACE_TABS` was dead code at render time
Disposition: **resolved.**

- `src/engram/web/chrome.py` is reduced to `LOCAL_ONLY_HELP_COPY`,
  `PHASE4_FUTURE_COPY`, `AUDIT_EGRESS_STATUS`, and `audit_footer_copy`.
  The `DEFAULT_SURFACE_TABS` constant and the `SurfaceTab` dataclass are
  removed.
- The single source of truth for the surface-tabs vocabulary is now
  `_surface_tabs.html`.
- Test: `tests/test_web_ui_shared.py:123–125`
  (`test_chrome_does_not_define_parallel_surface_tab_defaults`)
  mechanically pins the removal.

### F017 — `title="Phase 4: not yet built"` literal redundancy
Disposition: **collaterally resolved.**

- With `DEFAULT_SURFACE_TABS` removed (per FU105), the literal exists in
  only `_surface_tabs.html:10`. There is no parallel Python copy to drift
  against.

## Carry-forward F-items (status unchanged, honestly tracked)

The accept-with-findings handoffs explicitly scoped these out per
`ACCEPT_FINDINGS_EVIDENCE.md` § "Residual Risk." Confirmed unchanged in
the source:

- **F008 — Bench index resume CTA buried below metrics.**
  `bench_review/templates/index.html:13–43` still renders the metric grid
  first, then `<h2>Run readiness</h2>` plus the panel containing the
  resume `<a class="button">`. Open polish item.
- **F010 — Bench index vs summary metric set parity (5 vs 4).**
  `index.html:13–19` has five metrics including Excluded;
  `summary.html:7–12` has four (no Excluded). Open polish item.
- **F013 — Interview question stacks 6+ rows of metadata before evidence.**
  `_question_content.html:1–32` unchanged. Open density suggestion.
- **F015 — Bench segment detail has only "Back to this queue."**
  `segment.html:133` still emits only the back link; no "Next in queue
  (no decision)" affordance. Open polish item.
- **F018 — Commit-on-click vs rationale-required visual cue.**
  `_question_content.html:70–101` still relies on icon + colored
  underline. No explicit "commit on click" badge. Open polish suggestion.

## Net-new ergonomics observations from this round

These are minor / trivial first-time-user nits the fresh scan surfaced;
none are blockers and none invalidate the substrate. Filed so synthesis
can choose to track them as polish follow-ups.

### N201 — Save-and-quit uses `kind="warn"` but the message is informational
Severity: trivial
Source: `src/engram/interview/templates/index.html:19–25`;
`src/engram/interview/web.py:1162–1166`.

The empty-corpus banner is genuinely warn-toned (operator must refresh
current_beliefs or open issue persists). The save-and-quit banner reads
"Saved and quit. Resume with: engram phase3 interview resume
--session-id <UUID>" — that is a success/info confirmation, not a
warning. Rendering it with `kind="warn"` makes the visual treatment
(yellow left-border, warm background) read as "something needs your
attention" on first sight. The shared `_status_banner.html` partial
supports `kind="info"` / `kind="ok"`; flipping this one to `"ok"` (or
`"info"`) would match the semantics. Trivial fix; not blocking.

### N202 — Save-and-quit copy embeds a CLI command but skips `_cli_command_card`
Severity: trivial
Source: `src/engram/interview/web.py:1162–1166`;
`src/engram/interview/templates/index.html:19–25`.

The empty-corpus banner pairs `_status_banner.html` with
`_cli_command_card.html` so the operator can copy `engram phase4
refresh-current-beliefs` with one click. The save-and-quit banner
concatenates the resume command into the banner sentence ("Resume with:
engram phase3 interview resume --session-id <UUID>"), which means the
operator who saved-and-quit has to manually select-and-copy a long
command containing a UUID. This is a pre-existing pattern, not a
regression from this round, but the new shared-banner work is the
natural place to fold it into the same `_status_banner` +
`_cli_command_card` shape the empty-corpus banner uses. Trivial polish.

### N203 — Cross-surface URL defaults are silently "good enough" with no degraded state
Severity: trivial
Source: `src/engram/interview/web.py:113–126`;
`src/engram/bench_review/web.py:31`;
`src/engram/web/templates/_surface_tabs.html:2–5`.

The corrected ergonomics review's FU101 recommendation suggested "degrade
to an `is-disabled` span when no URL is configured." Both surfaces now
always emit a real `<a>` link, falling back to default cross-port URLs.
Pragmatically this is correct for the local-first single-operator case —
both surfaces typically run on their default ports, so the link works
out of the box without env-var setup. The trade-off: if the *other*
surface is not running, the click yields a browser-level connection
refused rather than a friendly disabled affordance. This is strictly
better than the prior 404-on-own-port behavior, and matching the
disabled-span pattern would require process-discovery beyond the
local-first posture's scope. Recording as an explicit design choice, not
a finding.

### N204 — Asymmetric env-var names for cross-surface URLs
Severity: trivial
Source: `interview/web.py:115` (`ENGRAM_INTERVIEW_BENCH_URL`);
`bench_review/web.py:31` (`ENGRAM_BENCH_REVIEW_INTERVIEW_URL`).

The two override env vars use different naming conventions:
`ENGRAM_INTERVIEW_BENCH_URL` (interview → bench) and
`ENGRAM_BENCH_REVIEW_INTERVIEW_URL` (bench → interview, the longer form
includes "REVIEW"). An operator following the obvious mirror pattern
("set both env vars for cross-surface URLs") has to discover the exact
names independently. The bench's `BENCH_REVIEW_` prefix is consistent
with its package name; interview's is shorter. Naming consistency is a
documentation concern, not a defect. If a follow-up consolidates the
docs section that describes both, recording both names together would
suffice.

## Positive notes preserved by this round

- The `_question_main.html` htmx fragment re-includes
  `_question_script.html` after each swap, so the two-click rationale
  flow (false / stale / unsupported / unsure) still rebinds correctly on
  partial swap.
- `accesskey="t/f/s/n/u/k"` and `data-key` annotations on verdict
  buttons are preserved; the shared keyboard dispatcher reads `data-key`
  from the same elements.
- Bench's `strong_disabled` rendering (regression / accept disabled with
  state-aware tooltip) and `metadata_only` disabling are unchanged.
- The "does not mutate" disclaimer renders on bench index, segment
  detail, and summary pages (`_status_banner.html` with
  `kind="warn"` + `message=bench_disclaimer`).
- The no-CDN / no-external-asset invariant continues to hold per
  `tests/test_web_ui_shared.py::test_shared_resources_have_no_external_asset_references`
  and per the evidence's "checked 27 shared/interview/bench
  template/static resources; no external asset references found" line.
- Audit footer renders the configured loopback bind address on both
  surfaces; `test_create_app_uses_configured_bind_address`
  (`tests/test_interview_web.py:352–365`) pins it for the interview side.

## What this round leaves open (matches evidence packet exactly)

The accept-with-findings evidence (`ACCEPT_FINDINGS_EVIDENCE.md` §
"Residual Risk") names the items intentionally out of scope:

- bench index CTA placement (F008)
- bench index vs summary metric parity (F010)
- interview metadata density (F013)
- bench segment "next in queue" affordance (F015)
- commit-on-click vs rationale-required visual cue (F018)

Plus the trivial nits from this round:

- N201 — save-and-quit banner `kind` semantics
- N202 — save-and-quit CLI in banner copy vs `_cli_command_card`
- N203 — cross-surface tab degradation policy
- N204 — env-var naming symmetry

None of these are merge-blockers. They are routine UI polish that should
land as small focused PRs against the now-stable shared substrate.

## Suggested verdict

`accept`.

The corrected round's `accept_with_findings` was driven primarily by FU101
(an interview-side tab that confidently led to a 404 on the operator's own
port). FU101 is resolved with symmetric env-var resolution, sensible
defaults, app-state plumbing, and three pinned tests. The remaining FU
findings (FU102–FU105 plus F017) are also resolved, with mechanical test
coverage for each. The carry-forward F-items remain open and tracked. The
substrate is consistent, the cross-surface affordance works in both
directions for a first-time operator on default ports, and the shared
chrome + shared keyboard dispatcher are now the single source of truth.

End of accept-with-findings ergonomics review.
