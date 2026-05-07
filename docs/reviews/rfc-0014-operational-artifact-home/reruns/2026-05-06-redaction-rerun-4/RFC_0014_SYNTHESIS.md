<a id="review-0030"></a>
# RFC 0014 Spec Handoff Synthesis

Review ID: REVIEW-0030
Status: synthesis
Date: 2026-05-06
RFC refs:
  - RFC-0013
  - RFC-0014
Decision refs:
  - D060
Phase refs:
  - none

author: synthesizer-claude-opus-002

Date: 2026-05-06
Source ledger: `docs/reviews/rfc-0014-operational-artifact-home/findings-ledger.md`
(as provided in this work packet)
Source RFC: `docs/rfcs/0014-operational-artifact-home.md`
Source spec: `docs/process/operational-artifact-home-spec.md`
Prior synthesis: attempt 1 by `synthesizer-claude-opus-001`, returned
`needs_revision` by `reviewer-codex-gpt-5.5-002`.

This synthesis evaluates the RFC 0014 spec handoff package against three model
reviews and incorporates the final-review revision findings (FR001-FR003). It
does not represent independent review and does not request owner disposition;
it consolidates ledgered findings into a recommended package disposition with
an explicit post-revision acceptance gate.

## Review Inputs

- `reviewer-claude-opus-001`: verdict `accept_with_findings`. Flagged seven
  contract-tightening items, including one major clarification on loop-scope vs
  root-scope precedence for flat legacy markers.
- `reviewer-codex-gpt-5.5-001`: verdict `accept_with_findings`. Flagged three
  contract-tightening items on human-checkpoint evidence machine-checkability,
  D060 path hygiene enforcement level, and timezone-aware `created_at`.
- `reviewer-gemini-3.1-pro-preview-001`: verdict `accept`. Reported no
  blocking findings.
- `reviewer-codex-gpt-5.5-002` (final review of attempt 1): verdict
  `needs_revision`. Raised three revision findings on package readiness gating
  (FR001), runner validation claim strength (FR002), and the scope of the
  flat-legacy cross-loop supersession exception (FR003).

All three independent reviewers agreed that the package cleanly separates
operational state from review feedback, preserves RFC 0013 marker semantics,
tightens private-content handling, and draws a defensible `agent_runner`
boundary.

## Finding Disposition Table

| Finding ID | Title | Priority | Disposition |
| --- | --- | --- | --- |
| RFC0014-F001 | Loop-scope precedence is ambiguous for flat legacy markers | Major | accepted with modification |
| RFC0014-F002 | RFC sketch and spec use inconsistent report filenames | Minor | accepted with modification |
| RFC0014-F003 | Repair verification report and marker stems differ | Minor | accepted |
| RFC0014-F004 | Migration lacks initial audit of existing flat legacy blockers | Minor | accepted |
| RFC0014-F005 | Marker handling of non-`none` `corpus_content_included` values | Minor | accepted with modification |
| RFC0014-F006 | `supersedes` semantics for non-`ready` markers unspecified | Minor | accepted |
| RFC0014-F007 | Spec acceptance criteria narrow malformed front-matter failure | Minor | accepted |
| RFC0014-F008 | Human-checkpoint owner-decision evidence not machine-checkable | Medium | accepted |
| RFC0014-F009 | D060 path hygiene enforcement level is inconsistent | Medium-low | accepted |
| RFC0014-F010 | `created_at` ordering should require timezone-aware timestamps | Low | accepted |

### Disposition Notes

- **F001 (accepted with modification, addressing FR003):** The spec must
  declare exact-path supersession of a front-matterless flat legacy marker as a
  narrow, explicit exception to the loop-id-scoped precedence rule, and only for
  front-matterless flat legacy blockers whose normalized repository path is
  their sole stable identity. The general rule that "a ready marker in one
  `<area>/<loop_id>` must not resolve a blocked marker from another loop"
  remains in force for all schema-bearing markers. The exception text must
  state explicitly that it does not generalize to schema-bearing cross-loop
  supersession. The superseding ready marker's `linked_report` is the binding
  redacted evidence regardless of which loop directory emitted it. Status
  output should attribute the supersession to the loop that emitted the ready
  marker without implying that loop owns the legacy blocker, and without
  implying any broader cross-loop supersession capability.
- **F002 (accepted with modification):** Keep the RFC sketch as proposal
  history. Add one explicit pointer line under the sketch's `reports/` block
  noting that report filename shape is governed by the spec's Canonical Layout,
  not the sketch. Do not retroactively rewrite the sketch's report list.
- **F003 (accepted):** Rename `reports/05_REPAIR_VERIFICATION.md` to
  `reports/05_REPAIR_VERIFIED.md` to align stems and the RFC 0013
  `repair_verified` marker family.
- **F004 (accepted):** Add a migration step between current steps 4 and 5:
  inventory all existing flat legacy `.blocked.md` and `.human_checkpoint.md`
  markers under `docs/reviews/phase3/postbuild/markers/` before legacy-root
  scanning becomes gate-active. Each entry resolves to either a schema-bearing
  ready marker with exact-path `supersedes` plus redacted resolution report, or
  to an explicit owner-acknowledged still-blocking record.
- **F005 (accepted with modification):** Add an explicit sentence to the Marker
  Schema section: any value of `corpus_content_included` other than `none` on a
  marker file fails closed as a privately contaminated marker, even if the
  value is `owner_approved` (which remains valid only on tracked prose reports
  per RFC 0013 Section 3). This makes precedence rule 8's "privately
  contaminated" branch concrete for markers.
- **F006 (accepted):** State explicitly that `supersedes` on `blocked` or
  `human_checkpoint` markers is permitted for provenance threading within the
  same `(issue_id, family)`, but does not by itself resolve any earlier blocked
  or checkpoint marker. Only a later `ready` marker with exact-path
  `supersedes` resolves a blocker; chains of blocked or checkpoint markers
  remain blocking until such a ready marker arrives.
- **F007 (accepted):** Replace the spec acceptance criterion that mentions only
  `created_at` failure with: "malformed or invalid marker front matter,
  including invalid or missing `created_at`, fails closed." This realigns the
  spec's acceptance bullet with the RFC's broader statement and with the Marker
  Schema's parseable-front-matter requirement.
- **F008 (accepted):** Choose a deterministic validation policy. Recommended:
  for a ready marker that supersedes a `human_checkpoint`, require its
  `linked_report` to exist and to carry a small machine-readable field
  (`owner_decision: recorded` plus an `owner_decision_evidence:
  <repository-relative-path>` pointer to the redacted owner-decision artifact
  under `docs/reviews/.../decisions/` or equivalent). If the evidence path is
  absent or the decision field is missing, the checkpoint stays blocked. This
  removes the worst inference burden from a downstream implementation prompt.
- **F009 (accepted):** Promote the Artifact Rules path-hygiene sentence from
  `should` to `must` for both markers and committed prose reports under
  `docs/operations/`. Make explicit that any tracked operational artifact
  containing a hardcoded home-directory absolute path is rejected by validation,
  not merely flagged in review.
- **F010 (accepted):** Tighten the Marker Schema and precedence rules to
  require RFC 3339 / ISO-8601 timestamps with an explicit `Z` or numeric
  offset. Naive timestamps without timezone information fail closed as
  malformed `created_at`, fold under F007's tightened acceptance bullet, and
  remain consistent with the narrowly scoped flat-legacy exception from F001.

There are no rejected or deferred findings. F001 closes a real policy hole; the
rest are contract-tightening items concentrated in the spec rather than the
RFC.

## Final Review Findings (Attempt 1)

These findings come from `reviewer-codex-gpt-5.5-002` reviewing the prior
synthesis attempt. They are addressed in this revision and are listed here
explicitly so the change is traceable.

- **FR001 (accepted, addressed below in Package Readiness):** The package
  readiness language now states an explicit owner/RFC acceptance or equivalent
  project-decision gate before any implementation prompt updates the runbook or
  scripts.
- **FR002 (accepted, addressed below in Runner Validation Observations):**
  Runner validation observations are softened to state only what the provided
  status, doctor, and `git status` snapshots evidence, with stronger claims
  flagged as "not evidenced in this packet."
- **FR003 (accepted, addressed in F001 disposition above and in Proposed
  Canonical Doc Changes):** The cross-loop supersession allowance is explicitly
  narrowed to a front-matterless flat legacy exception, and the spec text must
  preserve the loop-id-scoped rule for all schema-bearing markers.

## Package Readiness

Recommendation: **revise package, then route through a post-revision acceptance
gate before any implementation handoff**.

The handoff is structurally sound. The three independent reviewers landed on
accept-grade verdicts and the architectural choices (S001-S011) are not
contested. However, ten accepted findings concentrate on the implementation
contract: machine-checkability of human-checkpoint resolution (F008),
fail-closed behavior for marker private-content values (F005), timezone
discipline (F010), the spec's malformed-front-matter acceptance bullet (F007),
path-hygiene enforcement level (F009), legacy migration audit (F004), the
narrowly scoped flat-legacy supersession exception (F001), and naming and
provenance details (F002, F003, F006).

Required sequence before implementation handoff:

1. **Spec revision pass** lands the deltas listed in the next section. RFC 0014
   itself stays in `proposal` status; the spec stays a draft handoff.
2. **Owner/RFC acceptance or equivalent project-decision gate.** RFC 0014 is
   currently a proposal and the spec is explicitly non-binding until promoted.
   Before any later implementation prompt edits `DECISION_LOG.md`, the phase 3
   runbook, or `scripts/phase3_tmux_agents.sh`, the revised package must
   receive explicit human acceptance (RFC promoted out of proposal) or an
   equivalent recorded project decision. An implementation agent must not treat
   the draft spec as accepted architecture.
3. **Decision-log and process-doc promotion** records the acceptance and
   supersession of RFC 0013's committed operational artifact path guidance.
4. **Implementation prompt** is generated only after steps 1-3.

Sending the package directly to an implementation prompt without the spec
revisions or without the acceptance gate would either require the implementing
agent to invent policy in gate-sensitive paths, or it would let a draft spec
silently become production architecture. The post-revision gate is the
authoritative check that the architectural choices have been accepted, not just
contract-tightened.

The proposal status of RFC 0014 itself does not need to change as part of the
spec revision job; status promotion is the role of the acceptance gate.

## Proposed Canonical Doc Changes Before Implementation Handoff

These are the deltas a follow-up spec-revision job should land. They are listed
here as proposed changes; this synthesis job does not write them.

In `docs/process/operational-artifact-home-spec.md`:

1. **Canonical Layout:** rename `reports/05_REPAIR_VERIFICATION.md` to
   `reports/05_REPAIR_VERIFIED.md` (F003).
2. **Marker Schema:** require RFC 3339 / ISO-8601 `created_at` with explicit
   `Z` or numeric offset; naive timestamps fail closed (F010). Add an explicit
   sentence: any `corpus_content_included` value other than `none` on a marker
   fails closed as privately contaminated; `owner_approved` is never valid on
   markers (F005). Document that `supersedes` on `blocked` or
   `human_checkpoint` markers is provenance-only and does not resolve earlier
   blockers (F006).
3. **Compatibility Semantics:** add a paragraph stating that exact-path
   supersession of a front-matterless flat legacy marker is a narrow exception
   to the loop-id-scoped precedence rule. The exception applies only to
   front-matterless flat legacy `.blocked.md` and `.human_checkpoint.md`
   markers under `docs/reviews/phase3/postbuild/markers/*.md` whose normalized
   repository path is their sole stable identity. For these markers, a later
   schema-bearing ready marker that names the exact flat path in `supersedes`
   may resolve the legacy blocker even if the ready marker lives in a different
   `<area>/<loop_id>`. Status output attributes the supersession to the loop
   that emitted the ready marker without reassigning ownership of the legacy
   blocker. The exception explicitly does not generalize to schema-bearing
   cross-loop supersession; for schema-bearing markers, the loop-id-scoped rule
   remains in force (F001, FR003).
4. **Compatibility Semantics, precedence rule 6:** require, for a ready marker
   that supersedes a `human_checkpoint`, that its `linked_report` exist and
   carry `owner_decision: recorded` plus `owner_decision_evidence:
   <repository-relative-path>` pointing to a redacted owner-decision artifact;
   missing or unparseable evidence keeps the checkpoint blocked (F008).
5. **Artifact Rules:** promote the path-hygiene sentence from `should` to
   `must`; explicitly state that hardcoded home-directory absolute paths in
   tracked operational markers and reports are rejected by validation (F009).
6. **Migration Work:** insert a step between current steps 4 and 5 requiring an
   upfront inventory of flat legacy `.blocked.md` and `.human_checkpoint.md`
   markers under `docs/reviews/phase3/postbuild/markers/` before legacy-root
   scanning becomes gate-active, with each entry either resolved by a
   schema-bearing ready marker plus redacted resolution report or recorded as
   intentionally still-blocking with owner acknowledgment (F004).
7. **Acceptance Criteria:** broaden the malformed-front-matter bullet to
   "malformed or invalid marker front matter, including invalid or missing
   `created_at`, fails closed" (F007).
8. **Implementation Fixtures:** add fixtures for (a) a front-matterless flat
   legacy blocker superseded by a ready marker that lives in a different loop,
   exercising the narrow exception only (F001, FR003); (b) a schema-bearing
   blocker in one loop that is **not** resolved by a ready marker in a different
   loop, asserting the loop-id-scoped rule still holds; (c) a ready marker that
   lacks `owner_decision_evidence` and therefore fails to resolve a
   `human_checkpoint` (F008); (d) a marker with `corpus_content_included:
   owner_approved` rejected by validation (F005); (e) a marker with a naive
   (offset-less) `created_at` rejected as malformed (F010).

In `docs/rfcs/0014-operational-artifact-home.md`:

1. **Proposal Sketch:** add a single line under the `reports/` block stating
   that report filename shape is governed by the spec's Canonical Layout, not
   the sketch (F002). Do not rewrite the sketch's report list.
2. No other RFC body changes are required by these findings; the RFC remains a
   proposal/history record and continues to cede implementation detail to the
   spec.

`DECISION_LOG.md`, `BUILD_PHASES.md`, the phase 3 runbook, and
`scripts/phase3_tmux_agents.sh` should not be touched until both the spec
revisions above land **and** the post-revision acceptance gate has recorded
human acceptance or equivalent project decision. None of the findings request
changes to those artifacts during the spec revision pass itself.

## Runner Validation Observations

These observations are about the agent_runner validation workflow that produced
this synthesis job, not about RFC 0014 content. They are reported separately so
they do not contaminate the RFC disposition. Per FR002, claims are now
restricted to what the provided status, doctor, and `git status` snapshots
evidence; stronger claims are flagged as not evidenced in this packet.

What the snapshots evidence:

- **Runner currently healthy.** The runner doctor snapshot returned `ok: true`
  with no `problems`, and the runner status snapshot shows the current run in
  `running` state with the prior synthesis job marked `completed`, the active
  synthesis (this attempt) `running`, the downstream final-review job `blocked`
  on synthesis, and no `human_checkpoints`, `claimable_jobs`, `next_actions`,
  `latest_non_accepting_review_verdicts`, or `open_blockers`. That is
  consistent with a currently healthy runner with no surfaced operational
  blockers at this snapshot time.
- **No new repository writes from this validation branch.** The provided
  `git status` snapshot lists only untracked paths under
  `docs/reviews/phase3/...` and
  `docs/reviews/rfc-0014-operational-artifact-home/reruns/...` that predate
  this synthesis attempt. No tracked-file modifications are reported, which is
  consistent with read-only generation having occurred so far on the validation
  branch.
- **Byline propagation.** The expected `author:` byline
  (`synthesizer-claude-opus-002`) was passed through the work packet for
  attempt 2 and is reproduced verbatim near the top of this artifact, matching
  RFC 0013 artifact-byline expectations.
- **Findings ledger sufficiency.** The ledger plus the three independent
  underlying reviews and the FR001-FR003 final-review findings provided enough
  material to dispose of every finding without follow-up review questions. The
  ledger's `Relationship` field correctly flagged where the Gemini "no
  findings" verdict mildly conflicts with the Claude and Codex detail-level
  findings; that conflict is a granularity disagreement, not a substantive
  contradiction, and synthesis treats the more detailed reviews as
  authoritative for contract tightening.

What the snapshots do **not** evidence (flagged per FR002):

- **Read-only execution by the synthesis runtime.** Status, doctor, and
  `git status` snapshots show no writes have surfaced as defects or repository
  changes, but they do not directly prove that the synthesis process refrained
  from invoking write tools. Job logs or tool-call traces would be needed to
  confirm that stronger claim; those are not in the packet.
- **Absence of queue-truth coupling.** Spec choice S009 and the Agent Runner
  Boundary section describe the intended boundary, and the runner status
  snapshot does not show this synthesis depending on marker reads as live
  workflow state, but the snapshots do not on their own prove that no
  marker-as-queue-truth coupling occurred during generation. That is consistent
  with the spec's intent but not directly evidenced here.
- **Scope discipline beyond "no tracked-file diffs surfaced."** The packet's
  instruction not to update RFC 0014, `DECISION_LOG.md`, or process docs during
  synthesis is consistent with the clean tracked status, but the snapshots
  alone do not exhaustively prove no out-of-scope edits were attempted; they
  only show none landed.

No runner-side defects are evidenced in the supplied status, doctor, or
`git status` snapshots. Stronger statements about runner behavior would require
evidence not provided in this packet.
