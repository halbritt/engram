# RFC 0021 Gold-Set Interview Curation Review — gemini
author: reviewer-gemini-3.1-pro-preview-001

Status: review
Date: 2026-05-08
RFC refs: RFC-0021
Decision refs: D016, D019, D032, D040, D044, D069, F010, O008
Phase refs: PHASE-0003

Lane focus: operator UX of the interview loop, fatigue/cooldown defaults,
privacy-tier handling on export, and whether the verdict vocabulary maps
to how a human actually rules. The findings below are written from the
perspective of a single user sitting at a terminal trying to author and
re-author a personal gold set against their own memory layer.

## Findings

### F001 — Export `--privacy-tier-max` default is a privacy-leak hazard
Severity: blocking
Source: `docs/rfcs/0021-gold-set-interview-curation.md:200-203`
(`engram interview export` block); `HUMAN_REQUIREMENTS.md:607-616`
(privacy-tier model: Tier 1 = "only me, only on this machine"; beliefs
default to Tier 1).
Rationale: The RFC says "default tier ceiling matches the user's working
tier" but neither RFC 0021, HUMAN_REQUIREMENTS, nor BUILD_PHASES defines
"working tier" anywhere. There is no `engram config working-tier` command
in the proposed CLI surface, no row in any migration tracking it, and no
session-level knob. If an operator runs `engram interview export --format
jsonl > labels.jsonl` without `--privacy-tier-max`, the implementation
will fall back to *some* default — and a sloppy implementer will
reasonably read "matches the user's working tier" as "the highest tier
present in `gold_labels`," which is the opposite of fail-closed.
HUMAN_REQUIREMENTS § privacy-tier says beliefs **default** to Tier 1 with
explicit promotion only; the analogous default for export must be Tier 1
ceiling, not "whatever the user is currently looking at." The RFC must
either (a) hard-code default ceiling = 1 and require an explicit higher
value on the command line (with a confirmation prompt above some
threshold), or (b) define "working tier" with a concrete storage
location, default value (1), and how it is set. The current language
permits the export command to silently emit Tier 4 / Tier 5 rows on
first use.

### F002 — `unsupported` and `false` will collapse in practice; the prompt does not differentiate them
Severity: major
Source: `docs/rfcs/0021-gold-set-interview-curation.md:128-130`
(verdict CHECK constraint); `:99-104, :219-253` (worked example prompt
shows only `[t]rue / [f]alse / [s]tale / [unsure] / [skip]` — `unsupported`
is in the schema enum but is **absent from the rendered prompt**).
Rationale: The RFC proposes six verdict states but the worked example
only shows five at the prompt level. A user staring at the prompt
"Is this currently true?" with options `t / f / s / unsure / skip` will
never produce `unsupported` — that requires a different question shape
("Does the cited evidence actually support this paraphrase?"). Even if
`unsupported` is exposed, the conceptual gap between "this fact is
wrong" (`false`) and "the cited evidence does not support this fact"
(`unsupported`) is a distinction labellers in the human-eval literature
routinely fail to maintain. The RFC needs to either (a) drop
`unsupported` from V1 and rely on rationale text plus a follow-up
re-render of the evidence excerpt, or (b) split the question into two
turns ("is the paraphrase accurate?" then "is the underlying fact true?")
so the verdict the user produces actually maps to the verdict column.
Mixing these in one column behind one prompt produces noisy training
signal that Step 9 evals cannot discriminate.

### F003 — No mid-session abort path; fixed `[N/M]` counter does not scale
Severity: major
Source: `docs/rfcs/0021-gold-set-interview-curation.md:97-104`
(worked example header); `:194-202` (CLI subcommands —
`start | resume | history | export`, no abort).
Rationale: The worked example shows `[1/10]` and the longer worked
example uses `--n 5`. Neither the CLI subcommand list nor the
prompt-level interaction shows what happens at `[37/50]` when the user
hits Ctrl-C, walks away, or types `q`. The `resume` subcommand implies
session state is persisted, but does it commit the in-flight question?
Does `skip` advance the cursor or hold it? Is a SIGINT mid-rationale a
durable verdict-skip or a dropped row? For a 50-question session — which
is the typical batch implied by ROADMAP Step 5's "25–50 entries" target
— the operator must be able to (a) save and quit cleanly, (b) abandon
without committing the current turn, and (c) see remaining queue length
without re-running `start`. The RFC needs an explicit `quit`/`abort`
keystroke at the prompt, an explicit answer to "what happens to the
half-typed rationale on Ctrl-C," and a `status` subcommand
(or `history --pending`) so the user can find an unfinished session
without remembering the session ID. Without this, real sessions over
30 questions will produce torn state and the user will lose trust in
the loop after the first interruption.

### F004 — Cooldown defaults defer too aggressively to "tune empirically"
Severity: major
Source: `docs/rfcs/0021-gold-set-interview-curation.md:163-164`
(cooldown: "A target answered in the last N days is suppressed"); 
`:338-340` (Open Question 6: "values to be tuned empirically once any
real usage data exists").
Rationale: The RFC ships v1 with no concrete cooldown defaults, but a v1
must commit to *some* number or the sampler will either re-show the same
five identity beliefs every session (no cooldown) or never re-ask any
target (infinite cooldown). The empirical-tuning posture is a hidden
gate: cooldown values cannot be "tuned" before the first session runs,
and the first session sets the operator's perception of whether the loop
is useful. Reasonable v1 defaults, justifiable from the stability_class
column already on `claims` / `beliefs`: identity ≈ 90 days, relationship
≈ 60 days, project_status ≈ 30 days, preference ≈ 30 days, goal ≈ 14
days, task ≈ 7 days, mood ≈ 3 days. Plus a global per-target floor of
"don't re-ask the same `(target_id, target_version_stamp)` within 24h
regardless." The RFC also needs to call out the failure mode where the
cooldown is per-`(target, verdict)` vs per-target-any-verdict
— Open Question 6 names both shapes but does not pick. Until a concrete
default lands, an implementer building the sampler has no anchor and
will pick something arbitrary.

### F005 — "Show me everything" override has no privacy floor
Severity: major
Source: `docs/rfcs/0021-gold-set-interview-curation.md:163-164`
("unless the user explicitly requests 'show me everything'").
Rationale: The cooldown override is described in prose but not in the
CLI surface (no `--all` or `--ignore-cooldown` flag is documented in
`:194-202`). More importantly, "show me everything" naturally extends to
"sample without strata weights" and "ignore the privacy ceiling," and
the RFC does not draw the line. A user blowing past their own cooldowns
to find a stale belief is fine; the same flag silently suppressing a
privacy-tier filter is a leak. The RFC should specify that cooldown
overrides do **not** also relax `privacy_tier` ceilings on the sampler,
and the override flag should be named for what it actually does
(`--ignore-cooldown`), not for an unbounded "show me everything"
posture.

### F006 — Worked-example prompt does not show fatigue mitigation; rationale field is uncapped free text
Severity: minor
Source: `docs/rfcs/0021-gold-set-interview-curation.md:219-253`
(5-question worked example); `:130` (`rationale TEXT NULL` — no length
cap).
Rationale: A 50-question session at the worked-example density (one
question + one rationale + 3-line evidence summary) is roughly 200 lines
of terminal output and 50 free-text rationale prompts. The free-text
rationale field has no character limit, no "press Enter to skip" hint
shown in the prompt (the worked example just shows blank rationales
implying Enter skips, but this is undocumented), and no end-of-session
review screen letting the user re-read what they committed. Operator UX
notes: (a) the prompt should explicitly say `[Enter to skip]` next to
"Optional rationale:", (b) sessions over 20 questions should print a
mid-session marker (e.g., `--- 25/50, take a break? [c]ontinue / [s]ave-and-quit ---`),
(c) the `rationale` column should soft-cap (e.g., 1024 chars) with a
warning at 80% so operators don't accidentally paste a multi-page
explanation that becomes useless to scan. None of this is structural,
but all of it is the difference between a CLI that is used and one that
is opened once.

### F007 — Active-learning "at scale" gate is undefined; no operator-visible signal
Severity: major
Source: `docs/rfcs/0021-gold-set-interview-curation.md:169-172`
("V1 sampler is the simplest version that respects strata + cooldowns;
the active-learning bias is wired but defaulted off until RFC 0018
reviewer output exists at scale.");
`:332-334` (Open Question 4: "RFC 0018 reviewer scores are the obvious
feed once present at scale").
Rationale: "At scale" is not defined. There is no row count, no coverage
ratio, no operator-facing indicator of when the bias should turn on, and
no CLI flag (`engram interview status --active-learning-readiness`?) to
let the operator see the threshold approaching. This is a hidden gate:
the active-learning code ships disabled, and absent an explicit
trigger condition, it will stay disabled forever because nobody will
remember to flip it. The RFC should commit to either (a) a concrete
threshold ("active-learning bias auto-enables when N reviewer rows exist
across at least K stability classes"), (b) an explicit operator command
to opt in (`engram interview sampler set-active-learning on`), with a
clear printed warning if reviewer-output coverage is below some floor,
or (c) move active-learning entirely out of v1 and into a follow-up RFC
so the v1 sampler is concretely shipping the simpler shape. Currently
the RFC promises a feature it cannot turn on.

### F008 — Session ID lifecycle is implicit in `sampler_strata_key`; no `gold_label_session` row
Severity: major
Source: `docs/rfcs/0021-gold-set-interview-curation.md:113-137`
(`gold_labels` schema — no `session_id` column);
`:131-133` (`sampler_strata_key JSONB` carries strata only);
`:194-202` (`engram interview resume [--session-id <id>]` —
the session ID exists at the CLI but has no schema home);
`:221` ("session: gl-sess-2026-05-07-00").
Rationale: The CLI surfaces a session ID and the worked example shows
one, but the schema has no column for it. The RFC implies it might be
folded into `sampler_strata_key` or `sampler_id`/`sampler_version`, but
strata keys are per-question and sampler ID is per-sampler-build. Where
does `gl-sess-2026-05-07-00` live? Without a `session_id UUID` column on
`gold_labels` (or a `gold_label_session` table for session-level
metadata: started_at, ended_at, n_requested, n_committed, sampler seed,
exit_kind in `{completed, ctrl_c, save_and_quit, abandoned}`), the
operator cannot answer questions like "did I finish that session from
last Tuesday?" or "which session produced these 12 verdicts?" The
`engram interview resume` command needs a place to look up state; the
RFC must either add a session-level table or explicitly add
`session_id` to `gold_labels` and document how `resume` reconstructs
queue state. F003's abort behavior depends on this.

### F009 — `prompt_text` in label rows risks tier-1 raw evidence leak via rendered evidence excerpts
Severity: major
Source: `docs/rfcs/0021-gold-set-interview-curation.md:125`
(`prompt_text TEXT NOT NULL`); `:181-184` (claim prompt: "Is this an
accurate paraphrase ... + a 1-line evidence excerpt
(privacy-tier-respecting)"); `:265-267` ("No raw evidence text is
required in the label row; the `prompt_text` column contains the
rendered question, which the user has by definition seen.").
Rationale: For claim questions the RFC explicitly says the prompt
includes "a 1-line evidence excerpt (privacy-tier-respecting)" —
meaning the rendered `prompt_text` for a Tier 1 (only-me) belief may
contain a literal slice of raw message text. That slice ends up
persisted in `gold_labels.prompt_text` with `privacy_tier` carried from
the target. The "user has by definition seen it" justification is fine
for storage *on the user's machine*, but the export path
(`engram interview export`) carries `prompt_text` out alongside the
verdict, and F001 already shows the export tier ceiling is undefined.
Combined: a sloppy export default plus a `prompt_text` containing raw
evidence excerpts means a single `engram interview export` invocation
can leak Tier 1 raw fragments. Fixes: (a) `prompt_text` must be the
*template* render, not the evidence excerpt — store evidence excerpts
in a separate column or omit them entirely for Tier 1 targets, (b) the
export path must redact or omit `prompt_text` above the requested tier
ceiling, (c) belief questions per `:182-184` ("no raw quotes by
default") have the right shape; the RFC should make the same rule apply
to claim questions.

### F010 — `skip` is structurally ambiguous: "I don't know" or "ask me later"?
Severity: minor
Source: `docs/rfcs/0021-gold-set-interview-curation.md:128-129`
(verdict enum); `:163-164` (cooldown text — does not specify whether
`skip` triggers cooldown).
Rationale: A user pressing `skip` could mean "this question is too hard
to answer right now, ask me again next session" or "I will never have a
useful answer for this, stop showing it." `unsure` and `skip` overlap on
the first interpretation. Without a rule, the cooldown policy will
treat `skip` like any other verdict and suppress the target for N days,
which is the opposite of "ask me later." Suggested resolution: `skip`
does **not** trigger cooldown (the next session re-asks); `unsure` does
trigger cooldown but at a shorter horizon than a definite verdict; the
prompt label changes from `[skip]` to `[skip - ask later]` so the user's
mental model matches the sampler's behavior. Also: an explicit
`never_ask` verdict (or a separate `gold_label_blocklist` table) would
let the user kill noise — but that is v1.5, not blocking.

## Open questions

- **Working-tier definition.** What is the source of truth for "the
  user's working tier" cited in `:200-203`? Is there an `engram config`
  command, an env var, or a row in some settings table? The RFC must
  ground this before the export default can be specified (relates to
  F001).
- **Session-state schema.** Does `gold_labels` carry `session_id`
  directly, or is there a separate `gold_label_session` table? Either
  works, but the RFC currently picks neither (F008).
- **Mid-session abort semantics.** If the operator hits Ctrl-C
  mid-rationale, does the half-typed rationale commit, drop, or block
  resume until handled? Spec is silent (F003).
- **Cooldown shape.** Per-`(target, verdict)` or per-`(target, any
  verdict)`? Open Question 6 in the RFC names both; v1 must pick one
  (F004).
- **Active-learning trigger.** What concrete signal flips the
  active-learning bias from off to on? Without one, the feature ships
  dead (F007).
- **Verdict-prompt mapping.** Should `unsupported` be exposed via a
  separate question shape, or removed from v1? The current single-prompt
  rendering will collapse it into `false` (F002).
- **Export redaction.** Does `engram interview export` redact
  `prompt_text` above the tier ceiling, or just filter rows? The RFC
  does not say (F009).
- **`skip` and cooldown.** Confirm whether `skip` triggers cooldown
  suppression. The current cooldown wording does not distinguish (F010).

verdict: needs_revision
