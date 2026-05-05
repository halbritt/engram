# RFC 0013 Review - claude_opus_4_7

Date: 2026-05-05
Reviewer: claude_opus_4_7
Verdict: accept_with_findings

The RFC is solid process architecture: it reaches into a real Phase 3 failure
class, names the gates that were missing, and stays inside the local-first
posture. The issues below are mostly about objectivity (gates that the RFC
itself can't decide), about a local-first regression introduced by Goal 1,
and about the gap between the policy in §8 and what the existing tmux script
actually enforces. Synthesis can pull most of these into the RFC; OQ4 and
F-LF1 should land in `DECISION_LOG.md`.

## Findings

### Major: F-LF1 — Diagnostics-as-evidence creates a slow local-first leak

**Affected:** Goal 1 ("Make runtime-development failures visible in durable
artifacts"); §3 item 1 ("Run report ... diagnostics"); §6 (run-report
narrative requirements); applied to
`docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`.

The post-build report already in tree contains user-corpus content captured
from a real conversation: a segment summary describing a personal project
("Air compressor project defined, bootstrap problem solved with nitrogen"),
specific extracted predicate values about a "shaft seal" / "stuffing box,"
and exact failure offsets that hint at message content. This is committed
to git. Per `docs/process/project-judgment.md`, "GitHub is remote persistence
by default" — so any `docs/reviews/phase3/...` artifact is, in practice,
egress.

The RFC's Non-Goals reaffirm "no hosted services, external telemetry, or
cloud persistence," but Goal 1 plus §3 actively pushes more user-derived
diagnostic prose into committed Markdown. Without a redaction policy, this
RFC's own success path can violate AGENTS.md's "no user data leaving the
machine unless explicitly requested."

**Proposed fix:** Add a §3 sub-rule and a Non-Goals reaffirmation that
operational run reports must (a) keep raw user content out of the committed
artifact (counts, IDs, kinds, error categories, NOT segment summaries or
predicate values), and (b) reference deeper diagnostics only by path under
an untracked or `.gitignore`'d local logs directory (e.g.
`logs/operational/<date>/<run>.json`). Add a check item to the verification
ladder: "no committed run report contains raw segment text, message
content, or predicate values from user data unless the owner has
explicitly approved." Promote this to `DECISION_LOG.md` as a binding
process decision.

### Major: F-OQ4 — Objective expansion gate is missing while gates are normative

**Affected:** §7 (Expansion gates); Open Question 4; "Applying This To
The Phase 3 Post-Build Failure" section.

§7 names `ready_for_next_bound` as a normative gate ("same bound rerun
passed and diagnostics are within accepted limits") and the RFC defines
the Phase 3 post-build ladder as authoritative (`--limit 10` → `--limit
50` → ...). But OQ4 admits the RFC has no threshold for parse failure or
dropped-claim rate that distinguishes "exit zero, expand" from "exit zero,
hold." The actual `--limit 10` slice exited nonzero with one parse failure,
which makes the gate easy *this time*. The harder shape — a clean exit
with elevated parse/drop noise — is exactly when the gate is needed, and
the RFC ships without it.

The current run had 22 dropped claims out of ~118 ingested + 22 dropped
across 17 segments. That number, with no threshold, is a coordinator
judgment call hidden inside a process artifact that exists to remove
coordinator judgment calls.

**Proposed fix:** Resolve OQ4 inside this RFC, even with a deliberately
conservative initial value. A workable starting contract:
`ready_for_next_bound` requires `failed_extractions == 0` AND `dropped_claim
rate over inserted+dropped <= 10%` AND no `consolidator` row marked failed
on the bounded scope; anything else routes to `human_checkpoint`. Promote
the threshold to `DECISION_LOG.md` so it can be tightened by review rather
than drifting in chat. If the threshold cannot be set today, the RFC
should explicitly mark `--limit 50` as a `human_checkpoint` until OQ4
resolves, instead of leaving the gate aspirational.

### Major: F-DEL — Section 6 deletion path is too permissive for derived state

**Affected:** §6 ("Derived-state repair rules"), third bullet:
"deleted only if the table is explicitly derived, deletion is part of a
documented repair path, and raw evidence is untouched."

This sentence is the only path in the RFC that authorizes destructive
DML against derived rows, and it is gated on "documented" without saying
*by whom*, *when reviewed*, or *with what audit*. D052 / D053 invest
heavily in transition-API + audit pairing for `beliefs`; allowing free-form
`DELETE FROM derived_table` when "derived" and "documented" suffices
quietly contradicts that posture. It also doesn't require pre/post counts
or a structural-equivalence check (cf. D055 for rebuilds).

**Proposed fix:** Tighten §6 third bullet to require:

1. an RFC update or named repair plan in `docs/reviews/`,
2. multi-agent review (per §4) before the DELETE runs,
3. the run report records pre-DELETE row counts, the WHERE filter, and
   post-DELETE counts,
4. for `beliefs` and `belief_audit`, deletion is forbidden in development
   mode; supersede/close via the transition API instead.

### Major: F-SCRIPT — §8 is aspirational; current automation does not enforce the gate

**Affected:** §8 ("Script and runbook responsibilities"); acceptance
criterion 5 ("the next Phase 3 bounded run uses the accepted markers and
gates").

`scripts/phase3_tmux_agents.sh` watches `docs/reviews/phase3/markers/`
only and has no awareness of the new `postbuild/markers/` subdirectory or
of `.blocked.md` semantics. It does not treat blocked markers as
terminal. The `status`/`next` commands have no rule about surfacing the
newest blocked marker. So §8 is currently a description of what someone
must build, not a description of what is true.

This matters because §3 item 2 ("Blocked marker") and §7 (gate names) are
load-bearing only if automation respects them. If the script keeps
launching the next pane regardless of `.blocked.md`, the issue loop
collapses to coordinator memory — exactly the failure mode this RFC
exists to prevent.

**Proposed fix:** Make script update a hard requirement of acceptance
criterion 4 or add it as criterion 6:

> `scripts/phase3_tmux_agents.sh` is updated to (a) discover markers
> recursively under `docs/reviews/phase3/`, (b) treat any `.blocked.md`
> as terminal for that step until a strictly later `.ready.md` marker
> appears, (c) `status` lists the newest blocked marker before listing
> ready markers, and (d) the script's behavior is covered by a focused
> test or smoke fixture.

Alternatively, the RFC should explicitly mark §8 as "target state, not
current state" so future readers do not mistake it for a description of
deployed automation.

### Major: F-LADDER — Verification ladder doesn't require exercising the failed scope

**Affected:** §5 ("Verification ladder"), step 5 ("the smallest bounded
rerun that can exercise the repaired behavior").

For the recorded incident, D060's repair (skip consolidation when
extraction fails) is exercised by *any* run where extraction fails. The
unresolved problem — large-segment JSON parse failure — is what the
ladder must actually re-hit before expansion. As written, "smallest
bounded rerun that can exercise the repaired behavior" allows
`--limit 10` against a different scope that happens to skip the failing
conversation, ticking the box without confronting the residual risk.

**Proposed fix:** Strengthen step 5 to require, when feasible, that the
rerun explicitly target the previously failing scope (here:
`pipeline-3 --conversations <failed_conversation_id>` or equivalent
limit/seek mechanism), and that the report record whether the previously
failing case is now passing, still failing, or skipped by repair. Add a
ladder step 4.5: "if the original failure was a model/runtime failure on
a specific input, rerun against that input and record outcome before
broadening the bound."

### Moderate: F-MARKER — Postbuild marker filename convention is undefined

**Affected:** §3 ("Required artifacts"); intersection with the runbook's
`docs/reviews/phase3/markers/` ordinal scheme.

The build-phase markers use a strict ordinal prefix (`01_SPEC_DRAFT...`,
`08_BUILD_COMPLETE...`) and the script knows that order. The new
postbuild markers under `docs/reviews/phase3/postbuild/markers/` already
mix concerns: `01_CHANGE_REVIEW_codex_gpt5_5.ready.md`,
`03_LIMIT10_RUN.blocked.md`, `04_RFC0013_DRAFT.ready.md`,
`05_RFC0013_REVIEW_<model>.ready.md`. The RFC neither defines this
ordinal scheme nor explains how a future operational issue (next loop
iteration) renumbers without clobbering. If the next blocked run is
loop-iteration #2, do markers continue from `06_...` forever, or restart?
What happens when two loops overlap?

**Proposed fix:** Add a §3 subsection that defines the postbuild marker
scheme. Concrete suggestion: scope each issue loop under a dated subdir
(`postbuild/markers/<YYYY-MM-DD>_<slug>/01_RUN.blocked.md`), and define
five canonical filenames per loop (`01_RUN.<state>.md`,
`02_REPAIR_PLAN.<state>.md`, `03_REVIEW_<model>.<state>.md`,
`04_SYNTHESIS.<state>.md`, `05_REPAIR_VERIFIED.<state>.md`). Otherwise
the "audit provenance" claim in §3's closing paragraph is undermined by
ad-hoc numbering.

### Moderate: F-FRONTMATTER — OQ2 is the same shape as F-SCRIPT and should be resolved together

**Affected:** Open Question 2; §8.

If §8 says automation should encode the gate and §3 says markers are
audit provenance, then automation must classify markers without prose
parsing — i.e., front matter is required, not optional. Punting OQ2
while normalizing automation behavior in §8 leaves a gap: scripts
inevitably end up grepping headlines or filenames, which is brittle.

**Proposed fix:** Resolve OQ2 in this RFC. Mandate a small machine-
readable header on every operational marker:

```yaml
---
loop: postbuild
state: blocked | ready | human_checkpoint
gate: blocked | ready_for_same_bound_rerun | ready_for_next_bound | human_checkpoint
classes: [upstream_runtime_failure, ...]
linked_report: docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md
---
```

Pair this fix with F-SCRIPT so the script's `status`/`next` reads the
header, not the prose.

### Moderate: F-RAW — RFC is silent on raw-evidence repair

**Affected:** §6, "Raw evidence remains immutable."

The RFC repeats the immutability claim but doesn't address what to do
when the failure *is* in raw evidence (parser bug producing corrupt
`messages.content`, ingestion writing wrong `source_kind`, etc.). D023
covers the privacy reclassification path via `captures`. No analog is
defined for general parser-bug repair. Leaving this implicit invites a
future operational loop to reach for `UPDATE messages` because the RFC
didn't say the path forward.

**Proposed fix:** Add a §6 subsection: "Raw-evidence corruption is
out of scope for this loop. Suspected raw-evidence bugs route to a
data RFC, not to the operational loop. The operational loop may quarantine
derived state that depended on the corrupt raw rows; it must not edit raw
rows. Tier reclassification follows D023 (`captures` of type
`reclassification`)."

### Moderate: F-CRIT — Acceptance criterion 5 is self-referential

**Affected:** Acceptance Criteria, item 5 ("The next Phase 3 bounded run
uses the accepted markers and gates").

A bounded run after acceptance using markers and gates does not retro-
actively validate the RFC; it just demonstrates compliance. The criterion
is also untestable from the RFC's own surface — there is no automated
check that "uses the accepted markers and gates" is true.

**Proposed fix:** Replace with a falsifiable criterion: "Within 14 days
of acceptance, an operational issue or a clean run produces the full
artifact set in §3 (run report, marker, optional repair plan, repair
report) under the new postbuild scheme, and a brief retro entry in
`DECISION_LOG.md` records whether the loop fired correctly or needed an
amendment."

### Moderate: F-TAXONOMY — Class taxonomy overlap is acknowledged but its tool impact is not

**Affected:** §2 ("Classify each issue before fixing it"); applied
classification at the end of the RFC (limit-10 mapped to four classes).

The RFC says "Reports may use more than one class" without addressing
what tooling does with that. If §8 wants `status` to surface the newest
blocked marker first, multi-class markers complicate severity ordering.
For example, a loop tagged `schema_or_migration_drift` (default: stop
all runtime work) AND `prompt_or_model_contract_failure` (default:
record diagnostics) — which "Default action" wins?

**Proposed fix:** Add a §2 rule: "When multiple classes apply, the
highest-severity default action wins, in this order:
`schema_or_migration_drift` > `orchestration_bug` > `data_repair_needed`
> `downstream_partial_state` > `upstream_runtime_failure` >
`prompt_or_model_contract_failure` > `review_process_gap`. The marker's
front-matter `gate` reflects the winning action."

### Moderate: F-REVIEW-DUP — Re-review semantics duplicate and may diverge from the runbook

**Affected:** §4 ("Review requirement"), final paragraph; runbook §"Marker
Contract" (re-review behavior, blocked re-review as human checkpoint).

The runbook already specifies what happens when a re-review still
rejects: that case is a human checkpoint and downstream tmux jobs stay
blocked. The RFC restates the rule briefly but doesn't reference the
runbook, and over time these can drift. Two sources of truth on
re-review behavior is a maintenance trap.

**Proposed fix:** §4 should reference
`docs/process/phase-3-agent-runbook.md`'s re-review rule rather than
restating it, or restate it verbatim and add a "Source of truth:" pointer
back to the runbook.

### Minor: F-COUNTS — "Counts before/after" doesn't say which counts

**Affected:** §3 item 1.

"Counts before/after, failure class, diagnostics" is the only schema for
run reports. It doesn't enumerate which tables (`claim_extractions`,
`claims`, `beliefs`, `belief_audit`, `contradictions`,
`failed extractions`, `consolidation_progress` failed rows). The
limit-10 report happens to enumerate all of these, but a future report
could land with just `claims` count drift and pass the RFC's bar.

**Proposed fix:** Specify the canonical count list per phase. For Phase
3 post-build: the six counts in the limit-10 report plus
`consolidation_progress` failed rows. Phase-2-flavored loops will need a
different list; define it when the loop first runs there.

### Minor: F-CONCURRENCY — Concurrent loops in same area are undefined

**Affected:** §1; §3.

If two operators (or one operator with two tmux sessions) trigger
operational loops in the same area on overlapping days, marker filenames
collide. F-MARKER's dated-subdir scheme would also resolve this, but it
is worth calling out explicitly: the RFC should say "one active loop per
area at a time" or define isolation by run-id.

**Proposed fix:** Add a §1 invariant: "At most one active operational
issue loop per area at a time. A second loop in the same area waits or
inherits the first loop's run-id." If the F-MARKER suggestion lands, this
falls out for free via `<YYYY-MM-DD>_<slug>` directories.

### Minor: F-NIT — "diagnostics within accepted limits" lacks an anchor

**Affected:** §7, definition of `ready_for_next_bound`.

Without F-OQ4 resolved or pointed to a doc, "accepted limits" reads as a
phrase that lets any operator declare success. Once F-OQ4 lands, §7
should reference it directly: "diagnostics within the limits set in
DECISION_LOG D0XX (parse-failure / dropped-claim thresholds)."

**Proposed fix:** When OQ4 lands, edit §7's gate definition to cite the
decision id.

## Non-Findings

Items considered and deliberately not flagged:

- **Goals/Non-Goals scope.** The Non-Goals correctly exclude end-user
  product behavior, hosted services, full-corpus authorization, and a
  general incident process. That bounds scope tightly and is right.
- **Three-tier separation respected.** The RFC keeps raw evidence
  immutable and locates all repair on derived projections; this aligns
  with D002, D003, D027, D052.
- **D060 application is correct.** The RFC accurately classifies the
  limit-10 incident as covering four classes, which exposes the
  taxonomy-overlap concern (F-TAXONOMY) but does not misclassify.
- **Marker/audit provenance principle.** "Do not remove old markers to
  make the queue look clean" is the right invariant.
- **Verification ladder ordering.** Steps 1→6 are a sane progression
  apart from F-LADDER on step 5.
- **Review requirement coverage in §4.** Triggers (new RFCs, changes
  to gates / repair / quarantine / human checkpoints) are well chosen;
  only F-REVIEW-DUP separates this from full pass.

## Checks Run

- Read the RFC top-to-bottom and cross-checked Goals → Non-Goals →
  Proposal → Acceptance Criteria for self-consistency.
- Cross-referenced §1 stop conditions against the limit-10 run report's
  actual failure shape.
- Cross-referenced §6 derived-state rules against D002, D023, D027,
  D048–D055 to look for posture conflicts.
- Cross-referenced §4 re-review rule against
  `docs/process/phase-3-agent-runbook.md`'s "Marker Contract" section.
- Inspected `scripts/phase3_tmux_agents.sh` to verify §8's claims about
  what scripts should do are not already true (they aren't —
  `MARKERS_DIR=docs/reviews/phase3/markers`, no `.blocked.md` handling,
  no recursion into `postbuild/markers/`).
- Listed `docs/reviews/phase3/postbuild/markers/` to compare existing
  marker filenames against the RFC's marker contract.
- Read AGENTS.md and `docs/process/project-judgment.md` for the
  local-first / no-egress contract; combined with the limit-10 report's
  inclusion of user-derived prose to surface F-LF1.
- Did not run any tests or migrations; review-only.

## Files Read

- `AGENTS.md`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/process/multi-agent-review-loop.md`
- `docs/process/project-judgment.md`
- `docs/process/phase-3-agent-runbook.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`
- `DECISION_LOG.md`
- `docs/reviews/phase3/postbuild/markers/03_LIMIT10_RUN.blocked.md`
- `docs/reviews/phase3/postbuild/markers/04_RFC0013_DRAFT.ready.md`
- `scripts/phase3_tmux_agents.sh` (header + marker logic only)
