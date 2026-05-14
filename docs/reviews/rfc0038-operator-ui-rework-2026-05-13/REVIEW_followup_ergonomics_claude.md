# RFC 0038 Operator UI Rework — Follow-up Ergonomics Design Review (claude)

author: operator [self-declared: rfc0038-followup-ergonomics-review]

Status: review
Date: 2026-05-13
RFC refs: RFC-0038
Spec refs: ENGRAM_UI_REWORK_HANDOFF.md, Spec 0027, RFC 0027, RFC 0028, RFC 0029
Decision refs: D044, D069, D074, D080
Posture: custom:ergonomics_dx (developer ergonomics + first-time-user discoverability,
decision cost, scan order, keyboard flow, responsive behavior, warning
comprehension, design-system fit)
Round: follow-up after repair lane
Prior round: docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_ergonomics_claude.md
Repair evidence under review: docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_EVIDENCE.md

## Scope and method

This follow-up review operates under a `document_only` access policy
(`cross_round` context): I am restricted to the inputs listed in the work
packet — the original ergonomics review, the correctness review, the repair
evidence, the RFC, the handoff, the multi-agent review-loop process doc, the
project-judgment doc, and CHANGELOG.md. I did not re-read source templates,
static files, or Python modules in this pass. The verdict therefore answers a
narrow question:

> Does the repair evidence + CHANGELOG demonstrate, on its face, that the
> first-round ergonomics findings F001–F019 are resolved sufficiently that a
> first-time operator would now find the affordances discoverable and
> consistent?

The previous round, with full source-file access, already enumerated the
ergonomic defects and ordered them by severity. The standard for accepting
the follow-up is whether the repair lane closes those gaps with evidence a
reviewer can verify from documents.

## Verdict summary

`needs_revision`. The repair evidence is materially silent on the ergonomics
findings raised in the prior round. It documents repair of three correctness
blockers (FastAPI response-annotation app start, `httpx` dependency
declaration, ruff lint/format) and reports one residual DB-route test
failure. It contains no entry, no command, no acceptance assertion, and no
narrative addressing any of F001–F019 — including F001 (shared chrome
substrate not wired into either surface), which is the load-bearing finding
on which F002–F007 explicitly depend. Correctness finding C003 — which
overlaps F001 on substance ("shared web substrate is packaged but not
integrated") — is likewise not listed as repaired in the evidence document.

A repair lane can legitimately defer ergonomics fixes if it says so. This one
does not say so. The originating verdict from the prior round therefore
still stands, and a follow-up that "freshly re-reviews the repaired UI" must
report that the surface is unchanged from an ergonomics posture until
documentary evidence to the contrary exists.

## Findings

Findings carry forward the F-prefix from the prior round. New findings in
this round use the FU- prefix (follow-up). Severity classes match the prior
round's conventions.

### FU001 — Repair evidence does not address any ergonomics finding
Severity: major
Source: docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REPAIR_EVIDENCE.md;
docs/reviews/rfc0038-operator-ui-rework-2026-05-13/REVIEW_ergonomics_claude.md

The repair evidence's "Finding Status From Focused Evidence" section
enumerates only correctness findings (C001, C002, C005) and a generic
"shared substrate/static checks pass" line that asserts package resources
exist and templates parse — neither of which speaks to wiring. The
ergonomics findings F001–F019 are not mentioned by identifier, by short
description, or by file. There is no follow-up acceptance criterion in the
evidence (e.g., "interview base.html now extends `_app_shell.html`",
"bench summary now uses `_cli_command_card.html`", "bench `<details>`
help collapsed into the shared modal"). The handoff and the prior review
were explicit that the shared chrome is mandatory: handoff §3.1, RFC 0038
"Required Implementation Slices" item 1, and review finding F001 all name
this contract. The repair evidence does not show that contract met.

Recommendation: the repair (or a follow-up repair workflow) must publish
focused evidence per ergonomics finding — at minimum F001–F007 — naming the
templates touched, the partials now included, and the affirmative DOM /
import-graph assertions that prove wiring (for example, a test that asserts
`_app_shell.html` markers appear in both surfaces' rendered HTML, and that
no inline duplicate of the design-token CSS remains).

### FU002 — Correctness finding C003 (shared substrate not integrated) is
not listed as repaired
Severity: major
Source: REPAIR_EVIDENCE.md ("Finding Status From Focused Evidence");
REVIEW_correctness_codex.md C003

The correctness review's C003 says exactly what ergonomics F001 said: the
substrate is packaged but the surfaces still use independent `base.html`
files with duplicated CSS, header, footer, and help logic. The repair
evidence reports C001 "appears repaired," C002 "partially repaired," and
C005 "appears repaired" — but C003 is not in the status list at all. Either
the repair lane addressed C003/F001 and forgot to record it, or it did not
address it; from documents, only the second interpretation is supported.

This is structurally important: a cross-review with two lanes (correctness
and ergonomics) raising the same root issue is a strong signal that the
issue is load-bearing. Failing to record its repair status undermines the
trust the multi-agent review loop is designed to build. Per
`docs/process/multi-agent-review-loop.md` § Procedure step 3, the
originating agent classifies findings as accepted / accepted with
modification / deferred / rejected. The repair evidence is the synthesis
substrate for that step; an unclassified major finding cannot be treated as
closed.

Recommendation: the repair-evidence document (or a synthesis doc) should
explicitly classify C003 and each of F001–F019 as accepted / accepted with
modification / deferred / rejected and link to the commit or test that
demonstrates the disposition. Without that, the follow-up reviewer has
nothing to verify.

### FU003 — Repair-evidence "fail" verdict is not paired with an ergonomics
disposition
Severity: major
Source: REPAIR_EVIDENCE.md ("Verdict: fail"); REPAIR_EVIDENCE.md ("Residual Risk")

The repair evidence's overall verdict is `fail`, with the residual risk
limited to one DB-route test (`test_question_renders_predicate_intent_and_warning`)
and the venv `httpx` workaround. A `fail` verdict on a repair pass that
preceded an ergonomics re-review compounds the problem: the operator-facing
ergonomic surface cannot be re-evaluated with confidence while the repair
pass itself reports incompleteness, and an ergonomics-only re-review cannot
salvage a UI surface that has not yet finished its correctness repair.

The handoff specifies ergonomics-relevant acceptance checks that depend on
route-level behavior — for example, `test_question_renders_predicate_intent_and_warning`
(§9.1) is the very test that confirms the visible predicate-intent and
subject-kind warning chrome. While that one test failure is technically a
correctness blocker (DB trigger violation in the test fixture), it is also
the route-level acceptance assertion for the F018-adjacent advisory
visibility goal. A reviewer asked to accept the ergonomics posture cannot
do so when the precise route test for one of the ergonomic affordances is
red.

Recommendation: do not run an ergonomics follow-up re-review until either
(a) the repair lane completes with `pass`, or (b) the repair lane
explicitly partitions itself into "correctness done" and "ergonomics
deferred to repair workflow X" so the follow-up review can scope to the
correctness portion. The current workflow scheduled this ergonomics
re-review before the repair completed — a process gap, not a UI defect.

### FU004 — No documented disposition for F008–F019 (minor / trivial polish)
Severity: minor
Source: REPAIR_EVIDENCE.md; REVIEW_ergonomics_claude.md §§ F008–F019

The original ergonomics review made clear that F008–F019 are independent
polish items that could land as follow-up work but should be tracked. The
repair evidence does not track them. Twelve minor / trivial polish items
exist with no recorded disposition. Per the project-judgment doc
("Rejected and deferred findings stay recorded; they are provenance, not
waste"), these need an explicit deferral entry or a disposition row before
they evaporate.

Recommendation: append a "Deferred ergonomics polish" section to the
repair evidence or open a focused follow-up Striatum workflow that takes
F008–F019 as an explicit input set. Either is acceptable; silence is not.

### FU005 — Project-judgment "make state visible" rule is under-served
Severity: minor
Source: docs/process/project-judgment.md ("Attention Traps" / "State belongs in files");
REPAIR_EVIDENCE.md

`project-judgment.md` says: state belongs in files, not in memory; do not
let several ready prompts live only as a remembered queue. The current
follow-up ergonomics review packet exists; that is good. But the inputs do
not include any artifact that classifies the 19 ergonomics findings as
accepted / deferred / rejected, and the repair evidence does not stand in
for that classification. A reader who picks up this workflow cold cannot
tell — from the inputs alone — which of the 19 findings the team intends
to fix in this cycle and which are deferred. That is a workflow-ergonomics
gap (developer ergonomics of the review loop itself), separate from the UI
surface.

Recommendation: produce a `SYNTHESIS_ergonomics_claude.md` companion in
this review folder that classifies F001–F019 per
`multi-agent-review-loop.md` step 3 and links to the commit / test that
demonstrates each disposition. The follow-up review folder
(`striatum/rfc-0038-operator-ui-rework-followup-2026-05-13/`) is the right
place to drive that, but the synthesis artifact belongs under
`docs/reviews/`.

## Findings carried forward without verdict change

Each of F001–F019 from the prior round is carried forward at its original
severity until documentary evidence to the contrary exists. The list below
restates only the identifier, severity, and the short title so a future
synthesizer can use this document as a checklist. Full discussion remains
in `REVIEW_ergonomics_claude.md`.

- F001 (major) — Shared chrome substrate exists but neither surface uses it.
- F002 (major) — Cross-surface tab affordance is broken.
- F003 (major) — Bench summary "Copy command" button is silently inert.
- F004 (major) — Three independent keyboard dispatchers.
- F005 (major) — Bench help has no decision glosses, no state vocab, no
  shortcut table.
- F006 (major) — Bench segment detail does not render the "does not mutate"
  warning.
- F007 (major) — Future-slot cards are absent from both surfaces.
- F008 (minor) — Scan order on bench `/` buries the resume CTA.
- F009 (minor) — Interview new-session form is cramped inline.
- F010 (minor) — Bench segment-detail vs. `/` metric sets differ (5 vs. 4).
- F011 (minor) — Interview index uses an ad-hoc `cli-command-card` instead of
  the shared partial.
- F012 (minor) — Long IDs (UUIDs, queue fingerprints) can overflow in bench
  tables/metadata.
- F013 (minor) — Interview question stacks 6–9 rows of metadata before
  evidence; version triple and advisory line are session-invariant.
- F014 (minor) — `[Abandon]` button has decorative brackets and no danger
  treatment; mismatched signal.
- F015 (minor) — Bench segment detail has no explicit "Next in queue"
  affordance.
- F016 (minor) — Help and "shortcuts" buttons on interview header are
  functionally identical.
- F017 (trivial) — Disabled "Entities (future)" tab has different copy
  literals in three places.
- F018 (trivial) — Single-click and two-click verdict buttons are visually
  indistinguishable.
- F019 (trivial) — Audit footer port-string default drifts between interview
  and bench; chrome.audit_footer_copy(...) helper unused.

If the repair lane has touched any of these and the documentary record is
just missing, this list should make it easy to record dispositions in one
pass.

## Positive notes

These remain true from the prior round and the repair evidence does not
appear to regress them; recording them so synthesis preserves the wins.

- The two-click rationale flow contract (interview question.html) was
  clean and the repair evidence shows focused interview/route tests pass
  (with skips when the test DB is absent). No documented regression.
- Origin/Sec-Fetch guards and the Tier 1 ceiling helpers were extracted
  into `engram.web.origin` and `engram.web.tier`. The fact that those
  helpers exist (per the handoff and CHANGELOG entries) is a substrate
  win even if F001's wiring gap means the helpers are not yet consumed
  by both surfaces.
- The no-CDN / no-external-asset invariant continues to hold per the
  repair evidence's "no-CDN/static resource scan" line ("checked 26
  shared/interview/bench template/static resources; no external asset
  markers found").
- Focused ruff check / format / shared template parse all pass.

## Suggested verdict

`needs_revision`.

Pre-merge required (carryover from prior round, still uncovered by
documentary evidence):

- F001 wired (substrate consumed by both surfaces), and the wiring
  recorded by a route-level assertion.
- F002 cross-surface nav links rendered with explicit "configured / not
  configured" handling.
- F003 bench summary copy-command button either wired through the shared
  partial or removed.
- F004 keyboard dispatcher consolidated to the shared `engram.web` script.
- F005 bench help expanded to match handoff §4.16 (decision glosses, state
  vocab, shortcut table, scratch-local panel).
- F006 "does not mutate" banner present on `/segments/{id}`.
- F007 future-slot cards rendered on both index pages.
- C003 recorded as repaired (or deferred with an open follow-up) in the
  repair evidence or a synthesis document.
- The DB-route test in REPAIR_EVIDENCE.md must pass before an ergonomics
  re-review is meaningful.

Pre-merge recommended (FU findings from this round):

- FU001/FU002 — repair evidence updated to classify F001–F019 and C003.
- FU003 — sequence: do not run an ergonomics re-review while the repair
  pass reports `fail`.
- FU004 — explicit deferral entry for F008–F019, or a focused follow-up
  workflow that consumes them.
- FU005 — produce `SYNTHESIS_ergonomics_claude.md` per
  multi-agent-review-loop.md step 3.

Followable-after-merge (no merge blocker):

- F008–F019 polish items, as a single tracked pass.

## Scope reminders

- This review's verdict is on the *ergonomics posture*. It is intentionally
  silent on privacy, security, and operator-truthfulness postures, which
  have their own lanes.
- I did not edit any implementation file in this round.
- The originating ergonomics review remains the canonical defect list; this
  follow-up only updates dispositions and adds workflow-ergonomics findings
  in the FU range.

End of follow-up review.
