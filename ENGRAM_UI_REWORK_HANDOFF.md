# Engram Operator UI — Implementation-Ready Redesign Handoff

| Field | Value |
|-------|-------|
| Title | Engram Operator UI Rework |
| Status | proposal (implementation-ready) |
| Date | 2026-05-13 |
| Scope | Phase 3 follow-on gold-set interview (RFC 0027 / D080) + Phase 3 bench triage workbench (RFC 0029); leaves extension hooks for Phase 4 (`PHASE-0004`) and future RFC 0044 tenant work |
| Source RFCs | RFC 0021, RFC 0027, Spec 0027, RFC 0028, RFC 0029 |
| Decision refs | D016, D020, D025, D044, D052, D069, D074, D078, D079, D080, D081 |
| Stack | FastAPI + Jinja2 + htmx + vendored static assets, sync `def` routes, `uvicorn --workers 1`, loopback-only |
| Files target | `src/engram/interview/web.py`, `src/engram/interview/templates/`, `src/engram/interview/static/`, `src/engram/interview/render.py`, `src/engram/bench_review/web.py`, `src/engram/bench_review/templates/`, `src/engram/bench_review/static/`, `src/engram/web/` (new shared substrate; small) |

---

## 1. Design Intent

Engram's operator surface is a **local memory-governance workbench**, not a
product showcase. The redesign treats the interview UI and the bench-review UI
as two routes inside a single visual system tuned for reading derived
artifacts, comparing prior to candidate evidence, and recording an audit
trail. Every screen is dense by default, side-by-side where comparison
improves review quality, and explicit about what it is asserting. The
operator is the only consumer; the UI's only purpose is to make the next
correct decision cheaper to reach.

**Claims the UI must not make.** This is the truthful posture the design
encodes everywhere:

1. The UI never asserts that a derived claim, belief, entity, audit, or
   benchmark candidate is canonical without an explicit `accepted` /
   `promoted` review state and a visible provenance chain. The default
   visual treatment of all derived content is *candidate / under review*.
2. The UI never implies that a gold-label verdict mutates belief status
   (D044), gates extraction or consolidation (D069), or otherwise feeds
   production state. Verdicts are framed as advisory eval inputs.
3. The UI never implies that a bench-review decision changes claim,
   belief, audit, or raw evidence rows. Decisions are framed as
   scratch-local review evidence (RFC 0029).
4. The UI never implies that a run-level bench recommendation is a Striatum
   gate or an operational authorization under D074. The label "recommended
   for owner gate" is the strongest assertion permitted.
5. The UI never implies Phase 4 full-corpus execution, entity
   canonicalization, `current_beliefs` materialization, or promotion to
   pinned state is authorized. Phase 4 surfaces appear as *future / backlog*
   slots only.
6. The UI never implies cloud, telemetry, hosted auth, CDN egress, or
   tenant-aware ingestion (RFC 0044 is queued only).
7. The UI never collapses `unsupported`, `unsure`, `stale`, `false`,
   `redacted`, `unavailable`, and `failed` into a single visual class.
   Refusal of false precision (HUMAN_REQUIREMENTS § P7) is part of the
   visual contract.

---

## 2. Primary User Flows

The redesign is built around eight load-bearing operator flows. Each flow
is owned by a named screen in §4 and a named component in §5.

1. **Open or resume a gold-label interview session.** Operator lands on
   `/`, scans open sessions with progress, either resumes a partially
   answered session (single click → `/sessions/{id}` redirects to the next
   unanswered `q/{idx}`) or starts a new session (form: `n`, `seed`).
   Empty-corpus path renders a diagnostic banner with an actionable
   `engram phase4 refresh-current-beliefs` hint instead of crashing or
   redirecting silently.
2. **Review one claim or belief with cited evidence.** Operator reads the
   header (kind, id, stability, conf band, recency, status), the predicate
   intent line, the cited evidence excerpts (3-row cap with disclosure),
   and rules. `true`/`skip` commit in one click. `false`/`stale`/
   `unsupported`/`unsure` reveal a verdict-specific rationale before
   committing.
3. **Triage unsupported / stale / unsure / false verdicts with rationale.**
   Verdict-specific rationale prompts (RFC 0028 widened `false` label),
   inline subject-kind warnings, and a one-line predicate intent strip.
4. **Inspect predicate intent, subject-kind hints, and warning states.**
   Predicate `intent: <description> (<subject_kind_hint>)` always renders
   on its own line below the subject—predicate—object triple. An advisory
   warning chip renders inline when `subject_kind_warning` is non-empty
   (`fetch_target_display` already returns this; the template surfaces it
   visibly).
5. **Save and resume an unfinished session.** "Save and quit" leaves the
   session open, discards in-progress rationale (CLI parity), prints a
   resume command. Reopening the session URL resumes at the next
   unanswered idx.
6. **Review benchmark segment queues and candidate / prior deltas.**
   Bench workbench lists segments per queue (Needs review, Zeroed, Newly
   nonzero, Count changed, Predicate mix changed, High drops, Provenance,
   Schema/parse, Follow-up, Regressions, Excluded blockers, Accepted,
   Unchanged, All). Segment detail shows prior-vs-candidate counts,
   redaction state, dropped reasons, segment excerpt (tier-gated), and
   prior/candidate claim cards side-by-side.
7. **Mark benchmark decisions and inspect readiness without promoting.**
   Strong decisions (`accept_candidate_change`,
   `flag_candidate_regression`) are disabled visually and in the route
   when data state is in `STRONG_DECISION_DISABLED_STATES`
   (`candidate_malformed`, `candidate_missing`, `prior_missing`).
   `needs_followup` and `exclude_from_review` remain available. Readiness
   is rendered as a state chip (`blocked` / `review_incomplete` /
   `ready_for_owner_gate_recommendation` / `…_recorded`), never as
   "promotion authorized."
8. **Export or hand off review evidence through CLI-owned paths.** Web
   never exposes export, history, coverage dashboard, active-learning
   toggle, or `--include-superseded`/`--ignore-cooldown`. Every export
   surface in the UI is a *help card* that prints the exact CLI command
   (Spec 0027 § Out of scope; RFC 0029 § CLI Commands). The pattern is
   `Export is a CLI-owned action: copy and run <command>` with a
   one-click clipboard affordance.

---

## 3. Information Architecture

### 3.1 Top-level layout regions (both surfaces share the chrome)

A single shared chrome lives in `src/engram/web/` (new — see §8). Each
surface mounts inside it.

```
┌─────────────────────────────────────────────────────────────────┐
│ App header                                                       │
│   ▌Engram local · <surface>                  [help] [shortcuts] │   ← row 1, 40px
│                                                                  │
│   Interview · Bench review · (Entities — future)                 │   ← row 2, 36px (nav)
├─────────────────────────────────────────────────────────────────┤
│ Surface main                                                     │   ← flex 1
│                                                                  │
│   (screen-specific content; see §4)                              │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│ Audit footer                                                     │   ← 28px
│   local-only · loopback · no network egress · <build sha>        │
└─────────────────────────────────────────────────────────────────┘
```

- **App header** is two rows on desktop. Row 1 is brand + surface label +
  affordance buttons. Row 2 is a horizontal tab strip with the surface
  list. Active tab is underlined (not pill, not background-filled).
- **Audit footer** is a single line always-visible. It is *not* marketing
  copy — it reads `local-only · loopback · no network egress` with the
  resolved bind address and the install SHA. It exists because every
  screen carries an unrevisable assertion about how the system is running.
- **Surface main** is content; screen-specific. The interview surface uses
  a single-column reading column (max 880px wide centered). The bench
  surface uses a two-pane queue + detail layout on desktop, stacked on
  narrow.

### 3.2 First viewport on desktop

| Surface | First viewport must show |
|---------|--------------------------|
| Interview `/` | App chrome, open-sessions list (with progress and abandon affordance), new-session form, empty-corpus diagnostic slot |
| Interview `/sessions/{id}/q/{idx}` | App chrome, question header line (idx/total, kind, id, stability, conf, status), predicate intent strip + warning chip, first 3 evidence excerpts, question line, verdict button row, strata strip |
| Bench `/` | App chrome, run metadata panel (artifact ids, prior/candidate version triple, queue fingerprint), readiness chip, top counts (decided/remaining/follow-up/regressions/excluded), top tag chips, primary resume button |
| Bench `/segments` | App chrome, queue filter row, segment table with: id, state, tags, prior count, candidate count, decision; first 15 rows on a 13" laptop |
| Bench `/segments/{id}` | App chrome, segment header, state instruction banner, prior/candidate count grid, prior-claims column, candidate-claims column (side-by-side on desktop), decision form, next-in-queue link |

### 3.3 Narrow-screen collapse

The redesign is responsive but does **not** attempt parity with desktop
expert workflows on mobile (per Design Constraints in the prompt). On
widths < 900px:

- Header row 2 (surface tabs) collapses into a `<details>` strip; the
  active surface label remains visible in row 1.
- Bench `/segments/{id}` collapses prior/candidate columns into stacked
  sections in that order; the decision form moves below them.
- Interview evidence excerpts wrap; "show full message" remains
  click-target ≥ 44px.
- Verdict button row wraps to two rows on widths < 640px (preserving
  the same accesskey letters); the rationale textarea expands to full
  width.
- Strata strip wraps; the help modal becomes full-screen on widths
  < 480px.

### 3.4 Future Phase 4 / entity-review extension points

The redesign anticipates Phase 4 and RFC 0044 without claiming either is
available. Slots are visible but inert:

- **Surface tabs** include `Entities (future)` rendered with a
  `data-future="true"` attribute, a `not-allowed` cursor, a tooltip
  `Phase 4: not yet built`, and no `href` (renders as `<span role="link"
  aria-disabled="true">`).
- **Bench-review run panel** carries a *"This decision is scratch-local;
  Phase 4 promotion is gated"* persistent note next to the readiness
  chip. The note text is anchored to D044 / D069 / D074 references when
  the operator hovers.
- **Interview help modal** ends with a single line: *"Promotion,
  acceptance, and entity canonicalization arrive in Phase 4. The
  interview surface never flips a belief status."* This is the literal
  copy; do not soften it.
- A new shared template `_future_slot.html` (see §5) renders a labeled
  disabled card. Phase 4 work replaces the card body without changing
  the IA.

---

## 4. Screen Specifications

Conventions for every screen below:

- *Route* identifies the verb/path. htmx swap modes are named explicitly.
- *Visible data* lists every field the template reads.
- *Controls* lists every input/button and what it submits.
- *Empty / loading / error / disabled states* are required slots; the
  template must render the named state class when the data shape
  warrants it.
- *Labels (user-facing)* are quoted verbatim. Do not paraphrase.

### 4.1 Interview · `/` (Open sessions + new session)

- **Route:** `GET /` → `index.html`; not Origin-checked (read-only).
- **Purpose:** Resume work; start work; surface the empty-corpus
  diagnostic.
- **Visible data:** open sessions list (`session_id`, `n_targets`,
  `n_answered`, `age`), an optional `empty_corpus_banner`, an optional
  `save_and_quit_banner` (carried via `?banner=…` from a save-and-quit
  redirect).
- **Controls:**
  - Per row: `<a href="/sessions/{id}">{K}/{N} answered, opened {age}</a>`
  - Per row: `<form method="post" action="/sessions/{id}/abandon">
    <button>Abandon</button></form>`
  - New-session form: `n` (number, min=1, default=10), `seed` (number,
    optional). Submit button label: `Start session`.
- **Empty state (no open sessions):**
  - Render `<p class="muted">No open sessions.</p>` inside the open-sessions
    section. The new-session form remains the primary call to action.
- **Empty-corpus banner (after POST `/sessions` returns no targets):**
  - Banner copy: `No targets matched. The candidate pool may be empty,
    every target may be on cooldown, or current_beliefs has not been
    refreshed.`
  - Hint card: `Refresh current beliefs:` followed by a
    `<code>engram phase4 refresh-current-beliefs</code>` with a
    clipboard-copy affordance.
- **Loading state:** not applicable; this is a synchronous render.
- **Error state:** any 5xx renders the standard error banner via the
  shared `_error_banner.html` partial (see §5). No silent failure.
- **Disabled state:** new-session submit button is disabled while htmx is
  in flight (`htmx:beforeRequest` / `htmx:afterRequest` toggles
  `aria-busy` and `disabled`).
- **htmx behavior:** the new-session form posts as a plain `<form>` (no
  `hx-post`); the redirect-to-`/q/1` pattern debounces duplicate
  submissions (Spec 0027 F025). The abandon form is also plain.

### 4.2 Interview · `/sessions/{session_id}/q/{idx}` (Question)

- **Route:** `GET /sessions/{id}/q/{idx}` → `question.html` (full page on
  direct GET; `<main>` fragment on htmx swap). 1-indexed `idx`; route
  translates to 0-indexed table key.
- **Purpose:** Render one target with enough context to rule honestly.
- **Visible data (in DOM order):**
  - `header_line` — from `format_header(sampled, idx, total)`.
  - `version_triple` — small muted line below header. Format:
    `extraction={prompt}/{model}  consolidation={prompt}/{model}
    profile={request_profile}`. Renders en-dashes (`—`) when fields are
    NULL.
  - `summary_lines` — from `format_summary_line(display)`. Lines:
    `subject -[predicate]-> object`,
    `  intent: <predicate_doc> (<subject_kind_hint>)`,
    `  [warning] <subject_kind_warning>` (only when non-empty).
  - `evidence_dates_line` — from `format_evidence_dates(display)`.
  - `error_banner` — present only on a verdict trigger-rejection (see
    Verdict POST).
  - `evidence_section` — first `EVIDENCE_ROWS_SHOWN=3` excerpts as
    `_evidence_excerpt.html`; `show all N rows` disclosure if more.
  - `context_panel` — empty by default; populated by
    `/sessions/{id}/messages/{message_id}/context` swap.
  - `question_line` — from `pick_question(sampled, display)`.
  - `verdict_form` — see Controls.
  - `rationale_area` — hidden by default; revealed for two-click
    verdicts.
  - `save_and_quit` button (plain `<form>` to `/save-and-quit`).
  - `status_line` — `data-live-status="Question {idx} of {total}"` so
    `htmx:afterSwap` can update `#live-region`. Visible copy:
    `{n_answered}/{total} answered — closing this tab is safe; verdicts
    are saved as you commit them.`
  - `strata_strip` — `_strata_strip.html`, alphabetical by
    `stability_class`.
- **Controls (verdict row, order is load-bearing):**
  - `[ ✓ true · t ]` — single-click commit, `type="submit"`, accesskey
    `t`, `class="v-true"`, `aria-label` from
    `gold_label_verdict_vocabulary.verdict='true'.gloss`.
  - `[ ✗ false · f ]` — two-click; first click reveals
    `#rationale-area`, second click submits.
  - `[ ⌛ stale · s ]` — two-click.
  - `[ ⚠ unsupported · n ]` — two-click. Letter is `n` (NOT `u`); the
    `u` slot belongs to `unsure`.
  - `[ ? unsure · u ]` — two-click. Empty rationale is permitted (RFC
    0021 § Verdict glossary — `unsure` accepts no-rule notes).
  - `[ » skip · k ]` — single-click commit; cooldown-free.
  - Rationale prompts (label-only; the textarea is plain `name="rationale"`):
    - `false`: `what's wrong? (e.g., wrong predicate, wrong subject,
      different object value, predicate doesn't apply) >`
    - `stale`: `when did it change? >`
    - `unsupported`: `what's missing from the evidence? >`
    - `unsure`: `note (Enter to skip) >`
- **Empty state (no evidence rows on target):**
  - Render `<p class="muted">(no evidence rows)</p>` inside
    `#evidence-section`. Do not hide the section; visible absence is
    itself information.
- **Loading state (htmx in flight):**
  - Form has `aria-busy="true"`; verdict buttons get
    `disabled` toggled by `htmx:beforeRequest`/`htmx:afterRequest`.
- **Error state (trigger rejection / unknown verdict):**
  - `error_banner` slot renders `<div id="error-banner" role="alert"
    class="banner-error">target was not labeled; details: {exc}</div>`
    above evidence. The session stays open; the question is re-rendered.
- **Disabled state (resume after close):**
  - When `_require_open_session(...)` returns `completed_at IS NOT NULL`,
    the route returns 409 with body
    `{"error":"session_closed","session_id":"..."}`. This is a JSON
    envelope on a server error; no HTML state needed.
- **htmx behavior:**
  - Verdict form: `hx-post="/sessions/{id}/q/{idx}/verdict"
    hx-target="#main" hx-swap="outerHTML"`. Response carries
    `HX-Redirect: /sessions/{id}/q/{idx+1}` on success, or to `/` after
    the final commit (handled inside the same guarded POST).
  - Show full message: `hx-get="/sessions/{id}/messages/{message_id}"
    hx-target="closest .evidence-row" hx-swap="outerHTML"`.
  - Show all evidence: `hx-get=".../evidence/all"
    hx-target="#evidence-section" hx-swap="innerHTML"`.
  - Context window: `hx-get=".../messages/{message_id}/context?before=2&after=2"
    hx-target="#context-panel" hx-swap="innerHTML"`.
- **Route-level rules (reaffirmed from Spec 0027 § Privacy posture):**
  - Tier 1 ceiling enforced before render. Target tier > 1 or any
    rendered evidence row tier > 1 → 403.
  - URL is 1-indexed; out-of-range returns 404 with envelope.

### 4.3 Interview · `POST /sessions/{id}/q/{idx}/verdict`

- **Purpose:** Append-only commit of a gold label; advance to next
  question; complete session on the final verdict inside the same
  guarded POST (no mutating GET).
- **Origin allowlist:** required. Failure returns
  `403 {"error":"origin_mismatch", "expected":[...]}`.
- **Validation:** `verdict ∈ VERDICT_VALID`; `false`/`stale`/
  `unsupported` require a non-empty rationale (422
  `{"error":"rationale_required","verdict":"<verdict>"}`).
- **Behavior:**
  - Reconstruct `SampledTarget` from the materialized
    `gold_label_session_targets` row (version triple frozen at session
    creation).
  - Call `InterviewAgent.record_verdict(session_id, target, verdict,
    rationale=rationale or None)`. `evidence_excerpt` is **not**
    populated (Spec 0027 § Privacy posture — left NULL).
  - On `unanswered.empty()` after commit, `mark_session_completed` runs
    in the same transaction; redirect target is `/`.
  - On `GoldLabelStorageError` / `GoldLabelVerdictError`, rollback and
    re-render `question.html` with `error_banner` populated. Status
    code 200 (htmx-friendly) with header `HX-Reswap: outerHTML`.

### 4.4 Interview · `/sessions/{id}/messages/{message_id}`

- **Route:** `GET` → `_evidence_excerpt.html` rendered with `full=True`.
- **Purpose:** Show the un-truncated body of one cited message.
- **Visible data:** id, role, created_at, source_kind, conv_title, full
  content (no `EVIDENCE_EXCERPT_LIMIT` cut).
- **Controls:** none.
- **States:**
  - 403 + envelope when `privacy_tier > TIER_CEILING` (1).
  - 404 + envelope when the message isn't reachable from the session
    (i.e., not in any materialized target's evidence id list).
- **htmx behavior:** swap target is the existing `.evidence-row`,
  `hx-swap="outerHTML"`. Collapsing back into a truncated row is done
  by a client-side toggle inside the rendered partial (re-link to the
  truncated render via a `hx-get="…/messages/{id}?truncate=1"` would be
  a v1.1 nicety; v1 simply leaves the expanded row in place).

### 4.5 Interview · `/sessions/{id}/messages/{message_id}/context`

- **Route:** `GET` with `before=<int>` and `after=<int>` query params.
- **Purpose:** Show cited message + `before` predecessors + `after`
  successors from the same conversation (`sequence_index` window).
- **Visible data:** for each row in the window: id, role, created_at,
  content (excerpted at `EVIDENCE_EXCERPT_LIMIT`), source_kind.
- **Controls:** none on the response (the requesting `<a>` lives on the
  question page).
- **States:**
  - 422 if `before + after > CONTEXT_BEFORE_AFTER_CAP` (20).
  - 422 if `before < 0` or `after < 0`.
  - 403 if any row in the window has `tier > 1` (max-tier carry; the
    whole response is denied, not silently filtered).
  - 404 if `message_id` is not reachable from the session.
- **htmx behavior:** swap target `#context-panel`, `innerHTML`.

### 4.6 Interview · `/sessions/{id}/q/{idx}/evidence/all`

- **Route:** `GET` → list of `_evidence_excerpt.html` partials.
- **Purpose:** Disclosure for the 3-row cap. Renders every cited evidence
  excerpt for the current target.
- **States:**
  - 403 if target tier > 1 or any evidence-row tier > 1.
  - 404 if target row is missing.
- **htmx behavior:** swap target `#evidence-section`, `innerHTML`.

### 4.7 Interview · `/sessions/{id}/save-and-quit`

- **Route:** `POST` → `303 → /?banner=…`.
- **Purpose:** Leave the session open; print the resume command.
- **Banner copy on redirect:** `Saved and quit. Resume with: engram
  phase3 interview resume --session-id <uuid>`. Banner is carried via
  query string and rendered inside the index page's
  `save_and_quit_banner` slot.

### 4.8 Interview · `/sessions/{id}/complete` and `/sessions/{id}/abandon`

- **`/complete`:** `POST` → guarded `mark_session_completed`, `303 → /`.
  Reserved; the final-question verdict path completes inline.
- **`/abandon`:** `POST` → `mark_session_completed` with
  `operator_note='abandoned via web'`, `303 → /`.

### 4.9 Bench · `/` (Run dashboard)

- **Route:** `GET /` → `index.html`.
- **Purpose:** Show run metadata, readiness state, queue counts; primary
  resume action.
- **Visible data:**
  - `session` row: `run_id`, `public_candidate_artifact_id` (when
    populated by the loader; today the live schema exposes `run_id`),
    prior version triple, candidate version triple,
    `queue_fingerprint`, `prior_comparison_mode`, `reviewer_label`.
  - `summary`: `total`, `decided`, `remaining`, `by_decision`
    (`accept_candidate_change`, `flag_candidate_regression`,
    `needs_followup`, `exclude_from_review`), `by_state`
    (`complete`, `candidate_zero`, `candidate_redacted`,
    `candidate_missing`, `candidate_malformed`, `prior_missing`),
    `by_tag` (risk tags).
  - `readiness` chip: derived from RFC 0029 § Recommendation readiness
    matrix.
  - `run_decision_label` (when present).
- **Controls:**
  - Primary resume button: links to the *first* of `Regressions`,
    `Follow-up`, `Excluded blockers`, `Needs review` queue with rows;
    otherwise links to `/summary`.
  - Run-decision recap card (read-only; the form lives at `/summary`).
- **Empty states:**
  - `total == 0`: render `<p class="muted">No segments loaded. Start the
    workbench with --run/--slice/--segments.</p>` and disable the
    primary resume button.
  - `decided == 0`: render the "Resume" button labeled `Start review`.
- **Disabled state:** when `metadata_only=1` is loaded (Spec 0029 §
  Data availability), every segment-level affordance is replaced with a
  banner: `Metadata-only session — segment verdict controls are disabled
  until candidate segment records are provided.`

### 4.10 Bench · `/segments` (Queue list)

- **Route:** `GET /segments?state=&tag=&decision=&remaining=&reviewable=`.
- **Purpose:** Browse and filter the queue.
- **Visible data (table columns):** `Segment` (UUID), `State`,
  `Tags` (badges), `Prior` (claim count or `n/a`), `Candidate` (claim
  count or `n/a`), `Decision` (decision token or `undecided`).
- **Controls:**
  - Filter row: queue tabs (Needs review, Zeroed, Newly nonzero, Count
    changed, Predicate mix changed, High drops, Provenance, Schema /
    parse, Follow-up, Regressions, Excluded blockers, Accepted,
    Unchanged, All). Each is a link with the appropriate query string.
  - Free-text filter input (`q=`): client-side filter over visible
    rows (no new route in v1).
- **Empty state:** `<p class="muted">No segments in <queue>.</p>`.
- **Disabled state:** in metadata-only mode, the row links remain
  active but the segment detail page renders the disabled banner.

### 4.11 Bench · `/segments/{segment_id}` (Segment review)

- **Route:** `GET /segments/{id}?state=&tag=&decision=&remaining=&reviewable=`.
- **Purpose:** Render one segment, side-by-side prior vs candidate,
  decide.
- **Layout:** two-column on desktop (≥ 1100px). Left column is *Prior
  claims*; right column is *Candidate claims*. Below both: the decision
  form. Above both: counts grid + state instruction banner.
- **Visible data:**
  - Header: `<code>{segment_id}</code>` and the data-state instruction
    banner (copy from `state_instruction(row.data_state)`).
  - Counts grid: `Prior claims`, `Candidate claims`, `Prior dropped`,
    `Candidate dropped` (each as a `<div class="metric">` with
    big-number treatment; `n/a` when null).
  - Tag chips: every tag in `tags`.
  - Detail banner: `detail.error` rendered as
    `<div class="banner-error">Detail load failed: …</div>` when
    present.
  - Segment excerpt panel: `detail.summary_text` (if any) and
    `detail.segment_excerpt`. Truncation note when
    `detail.excerpt_truncated`. Privacy banner when
    `detail.privacy_tier > 1` (text hidden).
  - Prior claims column: list of `<article class="claim">` cards.
    Visible per card: predicate, stability badge, subject text (or
    `[redacted]`), object display (or `[redacted]`), confidence
    (formatted `%.2f`), evidence count, claim id (code).
  - Candidate claims column: same shape; metadata fields when only
    redacted candidate info is present (object kind, object present,
    subject text present, rationale present).
  - Dropped reasons: rendered as a third row of cards below the
    columns (`detail.candidate_detail_note` and any structured
    drop-reason rows).
- **Controls:**
  - Rationale textarea: `<textarea name="rationale">` with the label
    `Review note (no excerpts, no claim text)`. v1 max length surfaced
    in the help: `ENGRAM_BENCH_REVIEW_RATIONALE_MAX_CHARS` (default
    500). Long input over the cap is rejected at the storage layer
    with a 400 banner; the UI also enforces a visible counter.
  - Hidden carry inputs for the next-segment query suffix
    (`next_state`, `next_tag`, `next_decision`, `next_remaining`,
    `next_reviewable`).
  - Decision buttons (order is load-bearing):
    - `[ Accept candidate change ]` — `decision=accept_candidate_change`.
      Disabled (`disabled` attribute + visible class) when
      `strong_disabled=True` (`data_state ∈
      STRONG_DECISION_DISABLED_STATES`). Disabled-state copy on tooltip:
      `Strong decisions are not available in <data_state>; resolve the
      artifact first.`
    - `[ Flag candidate regression ]` —
      `decision=flag_candidate_regression`. Same disabled rule.
    - `[ Needs follow-up ]` — `decision=needs_followup`. Always enabled.
    - `[ Exclude from review ]` — `decision=exclude_from_review`.
      Always enabled. Tooltip when row has risk tags:
      `Excluding a risky row leaves it visible in blocker queues;
      consider Flag candidate regression instead.` (Not a hard block;
      the operator may proceed.)
  - `[ Back to this queue ]` link that carries the active filter.
- **Special label per data state (rendered inside the strong-action
  buttons when `data_state == candidate_zero`):**
  - `Accept candidate change` → label becomes `Accept zero claims`.
  - `Flag candidate regression` → label becomes
    `Flag zero-claim regression`.
- **Empty / loading / error / disabled states:**
  - Empty prior claims: `<div class="warning">No prior claims were
    found for this segment and prior version tuple.</div>` (current
    template copy; preserve.)
  - Empty candidate claims: `<div class="muted">No candidate claims
    available.</div>` (when the candidate is `complete` but emitted
    zero, the data state already drives the warning banner).
  - Loading state: not applicable on direct GET; on a POST decision
    redirect there is no in-page swap.
  - Error: detail.error or trigger banner.
  - Disabled: strong decisions per above.

### 4.12 Bench · `POST /segments/{segment_id}/decision`

- **Origin allowlist:** required (current implementation uses the
  loopback host + Sec-Fetch-Site check). Failure returns 403.
- **Validation:** `decision ∈ SEGMENT_DECISIONS`. Strong-decision
  attempts against disabled states return 400 with
  `{"error":"strong decision disabled for state"}` envelope.
- **Behavior:** `record_segment_decision`; on
  `BenchReviewStorageError`, render 400 with detail message.
- **Redirect target:** the next segment URL inside the active filter
  context. If no row remains, redirect to `/segments?remaining=1&reviewable=1`.

### 4.13 Bench · `/segments/{segment_id}/excerpt`

- **Route:** `GET` → `excerpt.html` (new partial; currently exists per
  `_resource_dir("templates")` lookup).
- **Purpose:** Disclosure target for segment text expansion. Tier 1
  enforced at the route layer (max-carry for multi-message windows when
  applicable).

### 4.14 Bench · `/summary`

- **Route:** `GET /summary`.
- **Purpose:** Run-level decision + small numeric overview.
- **Visible data:** the four metrics (`decided`, `remaining`,
  `needs_followup`, `flag_candidate_regression`); rationale textarea;
  current decision (if any).
- **Controls:** rationale textarea; three submit buttons
  (`safe_to_promote`, `blocked_by_regressions`, `needs_more_review`).
- **State:** the warning banner is mandatory and reads exactly:
  `Bench review decisions do not mutate production data or bypass Phase
  4 gates.` Do not soften this copy.

### 4.15 Bench · `POST /run-decision`

- **Origin allowlist:** required.
- **Validation:** `decision ∈ RUN_DECISIONS`.
- **Behavior:** `record_run_decision`; redirect to `/summary`.

### 4.16 Help / shortcuts (modal, both surfaces)

- **Trigger:** `?` opens, `Esc` closes (interview already implements
  this; bench inherits the same dispatcher from `src/engram/web/`).
- **Contents (interview):** verdict glosses sourced verbatim from
  `gold_label_verdict_vocabulary`, keyboard shortcut table, the literal
  Phase-4 disclosure line from §3.4.
- **Contents (bench):** decision glosses (table below), state vocab,
  keyboard shortcut table, and a panel:
  - *"Decisions written here are scratch-local. They do not feed
    production extraction, consolidation, audits, or serving. Promotion
    is an owner / coordinator action through the normal gate artifact
    (D074)."*

---

## 5. Component Inventory

The names below are concrete template / Python helper names. Build or
refactor toward them; do not invent parallel components.

### 5.1 Shared chrome (new package `src/engram/web/`)

| Component | File | Inputs | States |
|-----------|------|--------|--------|
| `app_shell` | `src/engram/web/templates/_app_shell.html` | `surface` (`"interview"`/`"bench"`/`"future"`), `surface_label`, `bind_address`, `build_sha` | none |
| `surface_tabs` | `src/engram/web/templates/_surface_tabs.html` | active surface, future-slot tooltip text | active / inactive / disabled-future |
| `audit_footer` | `src/engram/web/templates/_audit_footer.html` | `bind_address`, `build_sha`, `egress_status` (always `"none"`) | none |
| `help_modal` | `src/engram/web/templates/_help_modal.html` | `verdict_help_rows` *or* `decision_help_rows`, `shortcut_rows`, `disclosure_lines` | open / closed |
| `error_banner` | `src/engram/web/templates/_error_banner.html` | `message` | hidden / visible / `role="alert"` |
| `status_banner` | `src/engram/web/templates/_status_banner.html` | `message`, `kind` (`info`/`warn`/`danger`/`ok`) | by `kind` |
| `cli_command_card` | `src/engram/web/templates/_cli_command_card.html` | `command` (str), `description` | normal / copied |
| `future_slot` | `src/engram/web/templates/_future_slot.html` | `title`, `subtitle`, `references` | always disabled, labeled `future / backlog` |
| `origin_check` | `src/engram/web/origin.py` | request, allowed hosts, bound port | success / 403 |
| `tier_ceiling` | `src/engram/web/tier.py` | tier, ceiling, optional message_id | success / 403 |
| `keyboard.js` | `src/engram/web/static/keyboard.js` | bare-key dispatcher | listens; ignored inside INPUT/TEXTAREA except Esc |

Shared substrate must not import `engram.interview.*` or
`engram.bench_review.*` business logic — only the web helpers move. The
extraction stays small (RFC 0029 § Relationship To RFC 0027).

### 5.2 Interview components

| Component | File | Inputs | Notes |
|-----------|------|--------|-------|
| `session_card` | `src/engram/interview/templates/_session_card.html` | session row (`session_id`, `n_answered`, `n_targets`, `age`) | row of `/sessions/{id}` link + `Abandon` form |
| `new_session_form` | `_new_session_form.html` | defaults (`n=10`, `seed=None`) | plain `<form method=post action=/sessions>` |
| `verdict_button` | `_verdict_button.html` | `verdict`, `gloss`, `accesskey`, `icon`, `commit_mode` (`single`/`two-click`), `disabled?` | renders icon + label + sup accesskey; single-click → `type=submit`, two-click → `type=button` |
| `rationale_editor` | `_rationale_editor.html` | `prompt_text`, `verdict_in_progress`, `required`, `max_chars` | hidden by default; revealed on two-click; ARIA-described by prompt span |
| `evidence_excerpt` | `_evidence_excerpt.html` (exists) | `excerpt` dict, `full` bool, `session_id` | header line + body + `show full message` link |
| `evidence_section` | `_evidence_section.html` | list of excerpts, total, disclosure_url | wraps disclosure link |
| `context_panel` | `_context_panel.html` | rendered rows from `/messages/{id}/context` | empty by default |
| `provenance_row` | `_provenance_row.html` | version triple dict | one-liner muted text; renders `—` for NULL fields |
| `predicate_intent_line` | `_predicate_intent_line.html` | `predicate_doc`, `subject_kind_hint` | renders `intent: <doc> (<hint>)`; empty when both blank |
| `subject_kind_warning` | `_subject_kind_warning.html` | warning text | renders `[warning] <text>` with `class="banner-warn"` |
| `strata_strip` | `_strata_strip.html` (exists) | strata rows | one-liner footer |
| `status_chip` | `_status_chip.html` | `status` (see §6 vocabulary), `kind` | small pill; semantic color via `data-status` |
| `keyboard_help_table` | shared | `verdict_help_rows` | inside the help modal |

### 5.3 Bench-review components

| Component | File | Inputs | Notes |
|-----------|------|--------|-------|
| `run_metadata_panel` | `_run_metadata_panel.html` | session row | renders run_id, prior/candidate triples, queue_fingerprint, comparison mode, reviewer label |
| `readiness_chip` | `_readiness_chip.html` | readiness (`blocked`/`review_incomplete`/`ready_for_owner_gate_recommendation`/`promotion_recommendation_recorded`/`rejection_recommendation_recorded`) | colored chip; warning tooltip on `ready_*` ("scratch-local; not a gate") |
| `queue_filters` | `_queue_filters.html` | active queue, available queues, free-text filter value | links carry `?state=…&tag=…&remaining=…&reviewable=…` |
| `segment_table` | `segments.html` (exists; refactor) | items list | columns: segment, state, tags, prior, candidate, decision |
| `counts_grid` | `_counts_grid.html` | metric dicts | a flex/grid of `<div class="metric">` |
| `state_instruction_banner` | `_state_instruction_banner.html` | `data_state`, `instruction` | colored by state |
| `claim_card` | `_claim_card.html` | claim dict, `mode` (`prior`/`candidate_full`/`candidate_redacted`) | renders different field sets per mode (see §4.11) |
| `prior_vs_candidate` | `_prior_vs_candidate.html` | prior claims, candidate claims | two-column flex on desktop |
| `decision_form` | `_decision_form.html` | row, strong_disabled, decision options, next_context | renders the 4 buttons with disabled handling |
| `rationale_editor` (bench) | `_rationale_editor.html` (shared) | `placeholder`, `max_chars=500` | same component as interview; used with `name="rationale"` |
| `excerpt_panel` | `excerpt.html` (exists) | row, instruction, detail | tier-gated body |
| `run_decision_form` | `_run_decision_form.html` | summary, options | hard-coded "does not mutate" banner above the buttons |
| `cli_handoff_panel` | shared `_cli_command_card.html` | `Export this review:` + `engram phase3 bench-review export …` | exists only as a help card; no inline export route |

### 5.4 Validation hooks (Python, not templates)

- `engram.web.origin.require_origin(request, *, host, port)` — single
  enforcement point. Bench's current `_origin_check` collapses into this.
- `engram.web.tier.require_tier_ceiling(tier, *, ceiling=1, message_id=None)`
  — single helper for tier 403 envelopes.
- `engram.web.audit.no_consolidator_imports()` — assertion used by tests
  (a one-line `assert "engram.consolidator" not in sys.modules` is *not*
  the test; the test introspects `engram.interview.web.__dict__` and
  `engram.bench_review.web.__dict__` for any reference to
  `engram.consolidator.transitions` — see §9.6).

---

## 6. Truthfulness And State Rules

All copy below is *user-facing*. Do not paraphrase. Implementations must
render the *exact* status token and copy when surfacing the state. The
chip color is a semantic token (§7.5), not a hex.

| Status token | Surface(s) | Copy (chip) | Long-form copy | Color token | Notes |
|--------------|------------|-------------|----------------|-------------|-------|
| `accepted` | Phase 4 future / belief review (not yet built) | `Accepted` | `Reviewed and accepted as canonical.` | `--color-ok-strong` | Renders **only** inside `_future_slot`; D044 forbids the interview UI from emitting this for gold-label flips. |
| `candidate` | Beliefs, claims, entities | `Candidate` | `Derived; not yet reviewed.` | `--color-info` | Default visual treatment of every derived row. |
| `provisional` | Beliefs | `Provisional` | `Auto-consolidated; awaiting review.` | `--color-info-muted` | Used in Phase 4 surfaces (future slot). |
| `proposed` | Bench-review run recommendation | `Proposed` | `Operator recorded a non-authoritative recommendation.` | `--color-warn-muted` | Never `accepted`; copy must say "recommendation." |
| `reviewed` | Interview, bench | `Reviewed` | `An operator has ruled on this row.` | `--color-fg-muted` | Generic affirmative-but-advisory state. |
| `advisory` | Gold labels (always) | `Advisory` | `Advisory eval input; does not change belief status (D044).` | `--color-info` | Render in every gold-label summary line. |
| `blocked` | Bench readiness | `Blocked` | `One or more hard blockers prevent recommendation.` | `--color-danger` | RFC 0029 readiness state. |
| `stale` | Beliefs (future), gold-label verdict | `Stale` | `Was true at evidence time; no longer true.` | `--color-warn` | Verdict label only in interview; future surface on beliefs. |
| `unsupported` | Gold-label verdict | `Unsupported` | `Evidence does not establish the claim, regardless of world truth.` | `--color-warn-muted` | Verdict, not a belief state. |
| `unsure` | Gold-label verdict | `Unsure` | `Operator could not rule.` | `--color-fg-muted` | Counts toward cooldown. |
| `redacted` | Evidence, bench candidate | `Redacted` | `Structured fields preserved; text intentionally absent.` | `--color-fg-muted` (with hatched chip pattern) | Distinct visual from `unavailable`. |
| `unavailable` | Bench data state | `Unavailable` | `Candidate / prior record missing for this segment.` | `--color-fg-muted` (with diagonal-stroke chip) | `candidate_missing` / `prior_missing`. |
| `failed` | Bench data state | `Failed` | `Candidate record failed schema or parse validation.` | `--color-danger` | `candidate_malformed`. |
| `future / backlog` | Phase 4 slots, RFC 0044 hints | `Future / backlog` | `Not yet implemented. Tracked in <RFC ref>.` | `--color-fg-muted` (with `[scheduled]` icon) | Used in `_future_slot.html`; never colored as `ok`. |

### 6.1 Interview-specific rules (D044 / D069)

- The interview UI **must not** render `accept` / `reject` / `promote` /
  `pin` controls anywhere. The `_future_slot.html` may *mention* that
  acceptance will arrive in Phase 4; it may not render a button shaped
  like an accept.
- Every gold-label summary row must carry the literal "Advisory eval
  input; does not change belief status." line at least once on the
  question page. The current implementation already buries this in the
  help modal; the redesign moves it onto the question page as a single
  muted status line below `version_triple`. Acceptable copy: `Verdict is
  an advisory eval input. It does not flip belief status (D044) or gate
  extraction / consolidation (D069).`

### 6.2 Bench-specific rules (D074)

- Strong decisions (`accept_candidate_change`,
  `flag_candidate_regression`) **must** render disabled when
  `data_state ∈ {candidate_malformed, candidate_missing, prior_missing}`.
  The disabled-state tooltip text reads: `Strong decisions disabled
  while <data_state>. Resolve the artifact (regenerate / disambiguate)
  to enable.`
- Run-decision surface must render the literal banner: `Bench review
  decisions do not mutate production data or bypass Phase 4 gates.`
  Implementation already has this; move it from `summary.html` body
  into a persistent header position on `/` and `/summary`.
- Recommendation readiness chip must never use the `ok` color when
  state is `proposed` / `recommend_promote`. The strongest color it
  may take is `--color-warn-muted` (yellow-tan) with the literal copy
  `Scratch-local recommendation; not a gate.`

### 6.3 Local-only / no-cloud assurance copy

These are the literal, operationally-true lines to render. Do not
soften, do not market, do not garnish.

- **Audit footer (every page):** `local-only · loopback bind:
  127.0.0.1:<port> · no network egress.`
- **Help modal:** `Engram runs entirely on your machine. No cloud
  service. No telemetry. No CDN. The browser fetches assets from this
  process only.`
- **Bench-review summary banner:** `Bench review decisions do not
  mutate production data or bypass Phase 4 gates.`
- **Interview help modal:** `Verdicts are an advisory eval input.
  They do not flip belief status (D044) or gate extraction or
  consolidation (D069).`
- **Future-slot card:** `Phase 4 work is not yet built. Tracked in
  RFC 0021 / D044 / D069 / D079.`

These lines are *not* marketing. They are circuit-breakers for the
operator's trust model. Do not adopt brand voice; adopt manifest voice.

---

## 7. Visual System

The system is restrained but deliberately not one-note. Avoid the
forbidden directions (dominant purple, beige/tan, dark slate/blue,
brown/orange). Lean cool neutral with a teal accent and a discrete
warm-amber attention color.

### 7.1 Density and layout grid

- Container max width 1180px. Center on desktop.
- Base font size 15px; lh 1.45. Reading column on interview narrowed to
  ~880px.
- Layout uses CSS grid (`display: grid` + `gap`) for every row of
  sibling controls and metric tiles; no per-element margins for
  spacing. (Frontend coding guideline.)
- 12-column implicit grid; bench segment detail uses
  `grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)` for the
  prior/candidate columns on desktop; collapses to single column under
  900px.

### 7.2 Typography scale

| Token | Size | Weight | Line height | Usage |
|-------|------|--------|-------------|-------|
| `--type-display` | 22px | 600 | 1.25 | Page H1 (rarely used; surface labels live in header) |
| `--type-heading` | 18px | 600 | 1.3 | Section H2 (segment id, sessions block) |
| `--type-subheading` | 15px | 600 | 1.3 | Claim card titles, group labels |
| `--type-body` | 15px | 400 | 1.45 | Body text |
| `--type-meta` | 13px | 400 | 1.4 | Provenance line, version triple, footer |
| `--type-mono` | 13px | 400 | 1.45 | UUIDs, command snippets, code (`SF Mono`, `Menlo`, `Consolas`, monospace fallback) |

Font stack: `-apple-system, "Segoe UI", system-ui, sans-serif`. No web
fonts; no Google Fonts. This is a local-only system.

### 7.3 Spacing scale

`--space-0: 0; --space-1: 4px; --space-2: 8px; --space-3: 12px;
--space-4: 16px; --space-5: 24px; --space-6: 32px; --space-7: 48px;
--space-8: 64px;`

Apply via `gap` (flex/grid) and template-side `padding`. Never via ad-hoc
margins on individual children.

### 7.4 Icon usage

Inline glyphs only; no icon-font dependency, no SVG library.

- `✓ true`, `✗ false`, `⌛ stale`, `⚠ unsupported`, `? unsure`,
  `» skip` — interview verdicts.
- `⊕ accept candidate change`, `⊖ flag candidate regression`,
  `… needs follow-up`, `↷ exclude from review` — bench decisions.
- `🔒 redacted`, `∅ unavailable`, `! failed`, `◷ stale`, `※ advisory`,
  `← future/backlog` — status chips.

Icons render as `<span class="icon" aria-hidden="true">`; the textual
verdict / decision name always accompanies the icon (WCAG 1.4.1). Do
not rely on icons alone.

### 7.5 Color tokens (semantic)

Hex values are reference defaults. Implementations must declare them as
custom properties on `:root` and reference them by name.

| Token | Default hex | Use |
|-------|-------------|-----|
| `--color-surface` | `#ffffff` | App background |
| `--color-surface-muted` | `#f3f5f4` | Card and section backgrounds |
| `--color-surface-sunken` | `#e9ecea` | Inactive / future-slot panels |
| `--color-border` | `#d4dad6` | All borders and dividers |
| `--color-border-strong` | `#9aa19c` | Active form controls |
| `--color-fg` | `#16201c` | Body text |
| `--color-fg-muted` | `#5a615c` | Secondary text / muted metadata |
| `--color-accent` | `#0f6e69` | Active nav, links, primary interactive |
| `--color-accent-soft` | `#dff1ee` | Active-tab underline tint / hover wash |
| `--color-ok` | `#13733e` | True verdicts, accepted state |
| `--color-ok-soft` | `#e2f2e8` | True button background hover |
| `--color-warn` | `#8a5b00` | Stale verdicts, follow-up |
| `--color-warn-soft` | `#fbf1d8` | Status banners |
| `--color-warn-muted` | `#bda369` | Unsupported chip |
| `--color-danger` | `#a8341c` | False verdicts, regressions, blocked |
| `--color-danger-soft` | `#fbe6e0` | Error banner backgrounds |
| `--color-info` | `#395e8f` | Advisory chip, candidate state |
| `--color-info-soft` | `#e3ebf6` | Hover tint |
| `--color-focus` | `#0f6e69` | Outline color (matches accent) |

Forbidden directions are *not* expressed as forbidden hex; they are
forbidden as dominant themes. Do not use purple as primary, do not
build a beige/cream surface palette, do not use slate-blue as a body
background, do not use brown/orange except in the narrow `--color-warn`
attention slot.

### 7.6 Tables and lists

- Bench segment table uses zebra-free rows (single border per row,
  `--color-border`); header row uses `font-weight: 600` and a 2px
  bottom border. No alternating background.
- Lists of evidence excerpts are vertical `<article>` cards with a 3px
  left border in `--color-border` (warning / advisory cards switch the
  border color via semantic token).

### 7.7 Evidence / diff treatment

- Evidence excerpts always render with a visible `header` row carrying
  date, role, source kind, and conversation title (when present). The
  body is preserved-whitespace (`white-space: pre-wrap`).
- Prior-vs-candidate comparison renders as two columns side-by-side.
  No inline diff highlighting in v1; the operator reads each card and
  decides. Per-field highlights (e.g., predicate badge color) may
  indicate differences, but no per-character diff colorization.
- Truncated text always indicates truncation: `…` suffix and a "show
  full message" affordance.

### 7.8 Form controls

- Inputs and textareas have `--space-2` vertical padding,
  `--color-border` borders, focus outline `--color-focus`.
- Buttons are `--space-2` vertical / `--space-3` horizontal padding.
  Verdict and decision buttons have `min-width: 9rem` so the row stays
  scannable.
- Disabled buttons retain shape, lose color (`opacity: 0.5`), get
  `cursor: not-allowed`, and carry an explanatory tooltip via the
  `title` attribute.

### 7.9 Color semantics summary

| Concept | Token |
|---------|-------|
| Affirmative action (commit, accept) | `--color-ok` |
| Negative action (reject, flag, danger) | `--color-danger` |
| Attention / awaiting / advisory | `--color-warn` or `--color-warn-muted` |
| Reference / informational / candidate | `--color-info` |
| Disabled / unavailable / future | `--color-fg-muted` / `--color-surface-sunken` |

---

## 8. Implementation Map

| Change | File / module | Class | RFC / Spec gate |
|--------|---------------|-------|------------------|
| Extract shared chrome (`_app_shell.html`, surface tabs, audit footer, help modal, error banner, CLI command card, future slot, keyboard.js) | new `src/engram/web/` package: `web/__init__.py`, `web/templates/*.html`, `web/static/keyboard.js`, `web/origin.py`, `web/tier.py` | Template / CSS / front-end-only **plus** small Python helpers extracted from existing `interview/web.py::_origin_check` and `bench_review/web.py::_origin_check` | Permitted by RFC 0029 § Relationship To RFC 0027. Keep the package small; no business logic imports. |
| New tokens stylesheet (single inline `<style>` block in `_app_shell.html`) | `src/engram/web/templates/_app_shell.html` | CSS-only | none |
| Vendored htmx already at `src/engram/interview/static/htmx.min.js`; add a sibling copy at `src/engram/bench_review/static/htmx.min.js` (already present) | both | static asset | F004 |
| Interview index — empty corpus banner, CLI command card, abandon affordance retained | `src/engram/interview/templates/index.html` | Template-only | Spec 0027 F029 |
| Interview question — render `predicate_intent_line`, surface `subject_kind_warning` visibly, render the advisory disclosure line below `version_triple` | `src/engram/interview/templates/question.html`, `src/engram/interview/render.py::format_summary_line` (already populates the data) | Template-only; renderer already returns the field | RFC 0028 §2 |
| Interview help modal — explicit Phase 4 disclosure and D044/D069 line | `src/engram/web/templates/_help_modal.html` | Template-only | D044 / D069 |
| Two-click rationale flow — preserve current htmx pattern; refactor verdict-button rendering into `_verdict_button.html` | `src/engram/interview/templates/question.html` + new partial | Template / front-end-only | Spec 0027 § Verdict commit flow |
| Bench `/` redesign — readiness chip, persistent "does not mutate" banner, primary resume button | `src/engram/bench_review/templates/index.html`, new `_readiness_chip.html`, new `_run_metadata_panel.html` | Template-only **plus** readiness computation helper | RFC 0029 § Recommendation readiness |
| Readiness computation — `bench_review.classify.compute_readiness(summary)` (NEW) | `src/engram/bench_review/classify.py` | Python (pure function over `storage.summary(...)` output) | RFC 0029 |
| Bench `/segments/{id}` redesign — `prior_vs_candidate` layout, decision form with strong-disabled tooltip, dropped reasons block | `src/engram/bench_review/templates/segment.html`, new partials `_claim_card.html`, `_prior_vs_candidate.html`, `_decision_form.html`, `_state_instruction_banner.html`, `_counts_grid.html` | Template-only | RFC 0029 |
| Bench `/summary` — move "does not mutate" banner to top, keep CLI handoff card for export | `src/engram/bench_review/templates/summary.html`, new shared `_cli_command_card.html` | Template-only | RFC 0029 § Redacted Export Contract |
| Status-chip vocabulary — single template + token CSS | `src/engram/web/templates/_status_chip.html` | Template-only | §6 |
| Future slot for `Entities` tab | `src/engram/web/templates/_future_slot.html` | Template-only | §3.4 / D069 |
| `Sec-Fetch-Site: same-origin` enforcement collapse — unify between interview and bench through `engram.web.origin.require_origin(...)` | `engram.web.origin`, `engram.interview.web.create_app`, `engram.bench_review.web.create_app` | Python refactor (preserves behavior; net delete) | Spec 0027 § Origin allowlist; RFC 0029 § Privacy posture |
| Tier 1 ceiling helper — collapse into `engram.web.tier.require_tier_ceiling(...)` | `engram.web.tier`, `engram.interview.web._check_tier_1`, `engram.bench_review.web._check_tier_1` (not currently present; bench enforces via storage) | Python refactor | RFC 0027 / RFC 0029 |
| CLI handoff for bench `export` / interview `export` / `history` / `coverage` | `_cli_command_card.html` rendered inline on summary pages | Template-only | Spec 0027 § Out of scope; RFC 0029 § CLI Commands |
| Phase 4 entity surface | `src/engram/entities/web.py` *(future / RFC-required)* | Future / backlog only | PHASE-0004 / D044 / D069 |
| RFC 0044 tenant scope marker | none in v1; if a banner is needed, render via `_future_slot.html` with a labeled `RFC 0044` reference | Template-only / future | RFC 0044 |
| Predicate-intent surfacing (already implemented in `render.py` per RFC 0028); the redesign promotes the warning to a visible chip | `src/engram/interview/templates/question.html` | Template-only | RFC 0028 |

### 8.1 Boundary-preservation rules (must hold under refactor)

- `engram.interview.web` and `engram.bench_review.web` **must not**
  import from each other.
- Neither `engram.interview.web` nor `engram.bench_review.web` may
  import from `engram.consolidator.transitions`. The shared `web`
  package may not import from either.
- `engram.web` may not import from `engram.interview.*` business logic
  (sampler, storage, agent, render). It may only import from
  `psycopg`, `fastapi`, `starlette`, `jinja2`, and from itself.

### 8.2 Items that are RFC-required (not implement-immediately)

- A non-loopback bind story (RFC 0022 / token auth follow-on). Surface
  this as a future-slot card on the help modal and in the audit footer
  copy ("loopback bind only; non-loopback requires future RFC").
- Higher-tier rendering env var
  (`ENGRAM_GOLD_INTERVIEW_RENDER_TIER_MAX`). Reserved name; v1
  hard-codes Tier 1. UI footer mentions the ceiling on hover of a
  status chip.
- Phase 4 entity / belief review queue — design lives here but the
  routes and template bodies remain `_future_slot.html` placeholders.
- `Entities` tab disclosure copy must include the RFC reference for
  the tracked future work.

---

## 9. Acceptance Checks For Codex

Every line below should produce one test. Tests are grouped by file; new
tests are flagged `(new)`. Existing files are extended.

### 9.1 Route tests — interview

- `test_index_renders_no_open_sessions` (existing) — GET `/` shows
  zero open sessions and the new-session form.
- `test_index_renders_save_and_quit_banner` *(new)* — GET `/?banner=…`
  surfaces the banner inside `_status_banner.html`.
- `test_index_renders_empty_corpus_banner` *(new — extend)* — after
  POST `/sessions` with an empty sample, GET `/` shows the
  `engram phase4 refresh-current-beliefs` CLI command card.
- `test_index_renders_phase4_future_slot` *(new)* — GET `/` shows the
  disabled `Entities (future)` tab.
- `test_question_renders_predicate_intent_and_warning` *(new)* — GET
  `/sessions/{id}/q/{idx}` with a fixture target whose
  `subject_kind_hint='persons only'` and subject `Hobnob` renders the
  `intent:` line and the `[warning]` line; HTML contains the literal
  copy `looks like a place/business`.
- `test_question_renders_advisory_disclosure_line` *(new)* — GET
  `/sessions/{id}/q/{idx}` renders the literal copy `Verdict is an
  advisory eval input. It does not flip belief status (D044) or gate
  extraction / consolidation (D069).`
- `test_question_renders_version_triple_line` *(new)* — GET renders the
  muted `extraction=…  consolidation=…  profile=…` line.
- `test_verdict_true_single_click_round_trip` (existing) — POST verdict
  `true` produces one `gold_labels` row and `HX-Redirect`.
- `test_verdict_unsupported_letter_is_n_not_u` *(new)* — page DOM
  exposes `accesskey="n"` on the unsupported button and `accesskey="u"`
  on the unsure button.
- `test_verdict_false_rationale_label` *(new)* — DOM contains the
  literal `what's wrong?` prompt text.
- `test_verdict_rationale_required_returns_422` *(new)* — POST `false`
  with empty rationale → 422 `{"error":"rationale_required",...}`.
- `test_messages_tier_ceiling_envelope_shape` *(new — extend)* — verify
  envelope `{"error":"privacy_tier_ceiling","tier":N,"ceiling":1,
  "message_id":"..."}` shape.
- `test_messages_context_max_tier_carry` *(new — extend)* — already
  required; add an assertion that the response is 403 (not a filtered
  partial body).
- `test_origin_mismatch_blocks_post_save_and_quit` *(new — extend)* —
  every POST route refuses bad Origin.
- `test_save_and_quit_redirects_with_banner_query` *(new)* — verifies
  `Location: /?banner=Saved%20and%20quit...`.
- `test_static_htmx_is_local` *(new — extend)* — page HTML has no
  reference to `unpkg.com`, `cdn.jsdelivr.net`, `cdnjs.cloudflare.com`,
  `googleapis.com`, or `googletagmanager.com`.
- `test_no_promotion_affordance_in_html` *(new)* — page HTML for every
  interview route contains zero substrings: `Accept`, `Promote`,
  `Reject`, `Pin`. (Case-insensitive; substring match.)

### 9.2 Route tests — bench review

- `test_index_renders_run_metadata` *(new — extend)* — DOM contains
  `run_id`, prior version, candidate version, queue fingerprint copy.
- `test_index_renders_does_not_mutate_banner` *(new)* — literal copy
  `Bench review decisions do not mutate production data or bypass
  Phase 4 gates.` appears on `/` and `/summary`.
- `test_index_readiness_chip_for_blocked_state` *(new)* — fixture with
  one regression renders the `Blocked` chip.
- `test_index_readiness_chip_for_ready_state` *(new)* — fixture with
  zero blockers renders the `Ready (recommendation, not gate)` chip;
  the chip color is not `--color-ok`.
- `test_segments_list_renders_queue_filter_tabs` *(new — extend)* —
  every queue link is rendered with the right query string.
- `test_segment_strong_decision_disabled_for_malformed` *(new)* —
  fixture row at `data_state='candidate_malformed'`: both
  `[Accept candidate change]` and `[Flag candidate regression]` are
  rendered with `disabled` attribute and the literal tooltip text.
- `test_post_segment_decision_strong_rejected_for_malformed` (existing)
  — already covered by `strong_disabled` 400 path; keep.
- `test_post_segment_decision_rationale_too_long_400` *(new)* — fixture
  rationale over `RATIONALE_MAX_CHARS` → 400 banner; the route does
  not crash.
- `test_run_decision_post_redirects_to_summary` (existing) — keep.
- `test_origin_mismatch_blocks_post_run_decision` *(new — extend)* —
  bench POST routes refuse bad Origin.
- `test_bench_summary_carries_cli_export_command_card` *(new)* — the
  template includes the literal `engram phase3 bench-review export`
  command string and a "copy" button.
- `test_no_promotion_affordance_in_html` *(new)* — same shape as
  interview test: no `Accept`, `Promote`, `Reject`, `Pin` substring
  on any bench HTML response, except inside the help-modal disclosure
  text where the words `not yet promoted` and `promote` appear inside
  the future-slot description (whitelisted phrasing).

### 9.3 htmx fragment checks

- `test_question_outerHTML_swap_returns_main` *(new — extend)* — POST
  verdict with `HX-Request: true` returns either `HX-Redirect` or a
  `<main id="main">` fragment, never a full HTML document body.
- `test_evidence_all_returns_innerHTML_fragment` *(new — extend)* — GET
  `/q/{idx}/evidence/all` returns concatenated `_evidence_excerpt.html`
  partials with no `<html>` envelope.
- `test_message_context_returns_innerHTML_fragment` *(new — extend)* —
  GET context returns partial HTML without `<html>`/`<body>`.

### 9.4 Responsive screenshot checks

These run in CI under headless Chromium with the test client serving
fixtures.

- `test_screenshot_interview_question_desktop_1280` *(new)* — viewport
  1280 × 800. Asserts a single-column reading layout with verdict row
  rendered horizontally on one line.
- `test_screenshot_interview_question_tablet_900` *(new)* — viewport
  900 × 1200. Asserts verdict row wraps to two rows.
- `test_screenshot_bench_segment_desktop_1280` *(new)* — viewport
  1280 × 800. Asserts the prior/candidate columns render side-by-side
  (two `<article class="claim">` columns visible above the fold).
- `test_screenshot_bench_segment_narrow_700` *(new)* — viewport
  700 × 1100. Asserts the prior/candidate columns render stacked.
- Screenshots are compared by structural assertions (DOM-pixel boxes),
  not pixel-perfect equality.

### 9.5 Warning text assertions

- `test_audit_footer_copy` *(new)* — every page renders the audit
  footer literal: `local-only · loopback bind: 127.0.0.1:<port> · no
  network egress.`
- `test_advisory_disclosure_copy_on_interview_question` *(new)* — see
  9.1.
- `test_bench_summary_does_not_mutate_copy` *(new)* — see 9.2.
- `test_future_slot_copy` *(new)* — every page that renders a future
  slot includes the literal `Phase 4 work is not yet built. Tracked in
  RFC 0021 / D044 / D069 / D079.`
- `test_state_chip_unsupported_copy` *(new)* — `unsupported` chip on a
  gold-label history view renders the long-form copy: `Evidence does
  not establish the claim, regardless of world truth.`

### 9.6 Keyboard / accessibility checks

- `test_keyboard_dispatcher_ignores_keys_in_textarea` *(new — DOM
  inspection)* — the dispatcher script's listener function literally
  contains the early-return check on
  `document.activeElement.tagName in {INPUT, TEXTAREA}`.
- `test_help_modal_focus_returns_to_trigger_on_close` *(new, manual
  acceptance)* — declared as a manual smoke; v1 automated check
  verifies the `aria-modal="true"` and `role="dialog"` attributes are
  present.
- `test_aria_live_region_present_on_question_and_segment` *(new —
  extend interview test)* — both surfaces include
  `<div id="live-region" aria-live="polite">`.
- `test_focus_moves_to_h2_on_htmx_swap` *(new)* — verifies the
  `htmx:afterSwap` listener attempts `document.querySelector('h2[tabindex="-1"]').focus()`.
- `test_verdict_buttons_have_aria_label_from_vocabulary` *(new —
  extend)* — every verdict button's `aria-label` matches the gloss
  string from `gold_label_verdict_vocabulary`.
- `test_decision_buttons_have_text_and_icon_not_color_only` *(new)* —
  each bench decision button contains both the icon and the textual
  decision name; WCAG 1.4.1 is satisfied.
- `test_disabled_buttons_have_tooltip_title` *(new)* — disabled strong
  decisions have a non-empty `title` attribute carrying the literal
  tooltip copy in §4.11.

### 9.7 No-CDN / local-only / no-network checks

- `test_no_cdn_substrings_on_any_rendered_page` *(new)* — iterate every
  registered route GET; assert response body does not contain `http://`
  or `https://` referencing any external host. Loopback URLs and
  `mailto:` are allowed; `data:` URIs are allowed.
- `test_static_htmx_served_from_wheel` (existing) — keep.
- `test_no_outbound_socket_in_corpus_reading_process` *(new — smoke,
  integration)* — start the FastAPI app under a deny-by-default
  egress wrapper (e.g., `pytest-socket --disable-socket`,
  allowing 127.0.0.1) and assert every test in the suite passes.
- `test_no_external_font_imports` *(new)* — the inline `<style>` in
  `_app_shell.html` contains zero `@import` rules and zero
  `font-face: url(http...)` references.

### 9.8 Overclaim / unsupported status text checks

- `test_no_promotion_or_acceptance_in_interview_dom` *(new)* — see
  §9.1 last item; cover every interview route.
- `test_bench_recommendation_chip_never_uses_ok_color` *(new)* —
  inspect the CSS computed style (jsdom) of the readiness chip when
  state is `promotion_recommendation_recorded`; assert
  `getComputedStyle(...).color` is not the `--color-ok` token's hex.
- `test_future_slot_is_inert` *(new)* — verifies `<span
  data-future="true" aria-disabled="true">`; no `href` attribute.
- `test_bench_summary_warning_banner_is_persistent` *(new)* — the
  `does not mutate production data` banner is rendered on every visit
  to `/summary`, regardless of state.

### 9.9 Import-graph / D044-D069 invariants

- `test_consolidator_transitions_unimportable_from_interview_web`
  (existing) — keep.
- `test_consolidator_transitions_unimportable_from_bench_web` *(new)* —
  same shape: import the module graph and assert nothing in
  `engram.bench_review.web.__dict__` resolves to anything in
  `engram.consolidator.*`.
- `test_engram_web_does_not_import_business_logic` *(new)* — assert
  the shared `engram.web` package does not import `engram.interview`,
  `engram.bench_review`, `engram.consolidator`, `engram.extractor`,
  or `engram.segmenter`.

### 9.10 New tests vs extensions — summary

- **Existing tests to extend:** `tests/test_interview_web.py`,
  `tests/test_bench_review.py`, `tests/test_interview_render.py`.
- **New test files:**
  - `tests/test_web_shared_chrome.py` — covers the shared chrome
    (`_app_shell.html`, `_audit_footer.html`, `_help_modal.html`,
    `_future_slot.html`, `_cli_command_card.html`).
  - `tests/test_web_origin_helper.py` — covers
    `engram.web.origin.require_origin` directly.
  - `tests/test_web_tier_helper.py` — covers
    `engram.web.tier.require_tier_ceiling` directly.
  - `tests/test_responsive_screenshots.py` *(new — opt-in via
    `--screenshots` pytest flag; not run by default)* — boots the
    test client, renders both surfaces, captures DOM layout boxes for
    the four viewport sizes in §9.4.
  - `tests/test_no_overclaim_copy.py` *(new)* — pure-text invariants:
    no `Accept` / `Promote` / `Reject` / `Pin` on any user-facing
    page (with allowlist for future-slot disclosure phrasing).

---

## 10. Open Questions

Only questions that *block implementation* go here. Reasonable defaults
already taken are labeled `assumption`.

1. **Shared `engram.web` package — does extracting `_origin_check` and
   `_check_tier_1` into a shared module land before or after the visual
   rework?** *Assumption:* land it first (a small Python refactor with
   no behavior change), then rebuild templates against the shared
   chrome. The chrome itself depends on the shared package existing,
   so this is an ordering question, not a scope question.
2. **Where does the readiness chip get its label set?** RFC 0029 §
   Recommendation readiness defines five states but the live storage
   schema currently exposes `summary.run_decision_label` only at the
   `safe_to_promote`/`blocked_by_regressions`/`needs_more_review`
   level. Computing the full RFC 0029 readiness state requires a new
   pure helper `bench_review.classify.compute_readiness(summary)`.
   This is a *Python addition* with no schema work and no production
   ingest; the helper consumes `storage.summary(...)` output and the
   `STRONG_DECISION_DISABLED_STATES` set. *Assumption:* add the helper
   in the same change as the bench `/` redesign.
3. **CLI handoff cards — should they be rendered inline at every
   appropriate exit point, or only inside the help modal?** *Assumption:*
   inline at the obvious exit points (interview save-and-quit banner;
   bench `/summary` export panel; bench `/` empty-corpus banner) and
   also inside the help modal as a reference.
4. **Visible Phase 4 / Entities tab — is "render the tab as a disabled
   future slot" the right framing, or should the tab simply not
   render until Phase 4 lands?** *Assumption:* render the disabled
   slot. The IA carries an explicit "what's coming" signal that
   matches HUMAN_REQUIREMENTS' "gaps as data" principle.
5. **CLI keyboard letter conflicts at the operator layer.** Today the
   bench surface has no keyboard dispatcher in the rendered HTML; the
   interview surface uses `t/f/s/n/u/k/q/?/Esc`. The redesign adds the
   bench keyboard map (`a/r/u/x/o/c/j/k/?/Esc` per RFC 0029 § Screen
   Design). The `u` letter collides with the interview's `unsure`.
   *Assumption:* the keyboards live on different surfaces and never
   share a page; the dispatcher is per-surface. Document the surface
   distinction inside the help modal so an operator who jumps between
   surfaces does not learn a wrong binding.
6. **Status chip vocabulary — does Codex want a single new template
   `_status_chip.html` with a `kind` switch, or one partial per chip?**
   *Assumption:* one template with a `kind` parameter and a `data-status`
   attribute that maps to a CSS class. Twelve chips, twelve classes;
   no Jinja conditional explosion.
7. **`unsupported` letter binding is `n`, but bench's "needs follow-up"
   letter is `u`.** Per §10.5 these never share a page; resolved.
8. **Tier ceiling for the bench excerpt route is currently enforced via
   `excerpt.html` rendering the privacy-tier warning, but the route
   itself does not 403 when `detail.privacy_tier > 1`.** *Assumption:*
   the redesign upgrades this to a 403 with the standard envelope
   matching the interview surface, so route-level enforcement is
   consistent across both UIs. If Codex wants this to stay rendered as
   a banner (not 403), say so before implementation — it is the only
   active divergence between the two surfaces' tier story.
9. **`Sec-Fetch-Site` enforcement — interview requires `same-origin`
   strictly; bench tolerates `same-origin`/`same-site`/`none` (per
   current code). The unified `require_origin` helper must pick one
   policy.** *Assumption:* tighten bench to match interview
   (`same-origin` only). This is *not* a no-op: tests must be updated
   to send the header. Confirm before implementation. If the bench
   has external local launchers that submit forms without the header,
   the tightening must be deferred behind a separate RFC.

---

End of handoff.
