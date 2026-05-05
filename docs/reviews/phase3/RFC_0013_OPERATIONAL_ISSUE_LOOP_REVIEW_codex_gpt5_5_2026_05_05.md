# RFC 0013 Review - codex_gpt5_5

Date: 2026-05-05
Reviewer: codex_gpt5_5
Verdict: reject_for_revision

## Findings

### High: Operational artifacts need an explicit corpus-content redaction gate

Affected sections: opening local-first statement, Proposal section 3
("Required artifacts"), Proposal section 8 ("Script and runbook
responsibilities"), and Acceptance Criteria.

The RFC correctly says it does not relax local-first, but it requires run
reports and markers under `docs/reviews/<area>/`, which are normal repo
artifacts. `docs/process/project-judgment.md` says GitHub is remote persistence
by default, so tracked review artifacts are a plausible path for user corpus
content to leave the machine. The existing Phase 3 post-build report already
shows how operational diagnostics can drift toward corpus summaries. A future
issue loop could easily capture raw snippets, model prompt/completion payloads,
claim objects, belief values, conversation titles, or local filesystem paths in
durable docs.

Proposed fix: add an "Artifact privacy rules" subsection before the required
artifact list. Default reports and markers should use IDs, counts, checksums,
error classes, and redacted diagnostics only. They should not include raw
message text, segment text, prompt/completion payloads, claim/belief object
values, person names from the corpus, exact conversation titles, or
machine-specific absolute paths. If content is truly needed to repair an issue,
require explicit owner approval and either an untracked local-only artifact or a
tracked redacted summary plus a marker field such as
`corpus_content_included: owner_approved`. Markers should never contain corpus
content. Add this checklist to the runbook and to any generated report/marker
templates before the next bounded run uses the loop.

### High: "Quarantined by progress state" is not an enforceable quarantine

Affected sections: Proposal section 6 ("Derived-state repair rules") and
"Applying This To The Phase 3 Post-Build Failure".

The RFC allows partial downstream rows to be "left in place but quarantined by
progress state." That is too weak as written. `consolidation_progress` is a
stage ledger; the live schema shows `claims`, `claim_extractions`, `beliefs`,
and `belief_audit` do not carry a quarantine linkage to that ledger. Unless
every future read path, rebuild path, review queue, `current_beliefs` view, and
`context_for` compiler explicitly consults failed progress rows, partial
beliefs remain active derived state. That undermines D060's purpose: avoiding
beliefs produced from incomplete conversation evidence.

Proposed fix: define a quarantine invariant: quarantined derived rows must not
feed downstream consolidation, rebuild inputs, review queues, current-belief
surfaces, retrieval, or context serving. If progress-state quarantine is kept,
the RFC needs exact query rules and acceptance tests proving every relevant
consumer excludes those scopes. Otherwise, require close/supersede/rebuild
repair before a ready marker. Also constrain deletion: do not delete audit or
diagnostic provenance rows such as `belief_audit`, `contradictions`, or
`claim_extractions` outside an explicitly documented and reviewed rebuild path.
Run reports should include exact selectors, before/after counts, and proof
queries for the repaired or quarantined state.

### Medium: Marker precedence is underspecified enough for stale ready markers to reopen a blocked lane

Affected sections: Proposal section 3 ("Required artifacts"), Proposal section
7 ("Expansion gates"), and Proposal section 8 ("Script and runbook
responsibilities").

The RFC correctly says not to delete historical markers, but the automation
rules still say panes should wait on `.ready.md` markers while treating
`.blocked.md` markers as terminal until a later ready marker exists. Without a
machine-readable marker family, scope, bound, timestamp, and supersession rule,
scripts can accidentally treat an old ready marker as sufficient even when a
newer blocked marker exists for the same lane. The existing Phase 3 marker
directory already has both blocked and ready markers for a same-model
re-review, so this is not hypothetical.

Proposed fix: promote Open Question 2 into a requirement. Add front matter or a
strict marker schema with `issue_id`, `family`, `scope`, `bound`, `state`,
`created_at`, `report`, and optional `supersedes`. Scripts should compute the
newest state per marker family and block if the newest state is `blocked` or
`human_checkpoint`. A later ready marker should explicitly reference the
blocked marker and repair report it supersedes. Acceptance criteria should
require `scripts/phase3_tmux_agents.sh status/next` or the successor automation
to implement this before the loop is relied on.

### Medium: Expansion acceptance limits and human checkpoints remain too open-ended

Affected sections: Proposal section 5 ("Verification ladder"), Proposal
section 7 ("Expansion gates"), "Applying This To The Phase 3 Post-Build
Failure", Open Question 4, and Acceptance Criteria.

`ready_for_next_bound` depends on diagnostics being "within accepted limits,"
but the RFC leaves those limits unresolved. It also says expansion past the
current `--limit 10` failure can proceed with targeted repair or explicit human
acceptance of residual risk, but that human checkpoint is only stated in the
Phase 3 example rather than in the general gate rules. This leaves room for a
coordinator to retroactively accept dropped-claim or parse-failure rates after
seeing a run result.

Proposed fix: define conservative default blockers before the next bounded
run: any nonzero command exit, failed extraction, downstream partial state,
unreviewed prompt/model contract failure, or unresolved review finding blocks
expansion. Per-bound run plans may set stricter or more specific thresholds,
but they must be written before execution. Require an owner checkpoint to
override an unresolved failure, retain visible partial state, change accepted
diagnostic limits, proceed after `--limit 50`, or start any corpus-specific or
full-corpus Phase 3 run.

## Non-Findings

- The RFC does not authorize hosted services, telemetry, cloud persistence, or
  a full-corpus Phase 3 run.
- The issue class taxonomy covers the D059 migration/schema drift failure and
  the D060 partial-consolidation failure.
- Requiring multi-agent review for operational RFCs, run-expansion gates,
  derived-state repair policy, and human-checkpoint changes is aligned with
  `docs/process/multi-agent-review-loop.md`.
- The default `--limit 0`, `--limit 10`, `--limit 50`, then owner-approved
  larger bounds sequence is directionally sound once marker precedence,
  artifact privacy, and diagnostic thresholds are pinned.

## Checks Run

- Read the required RFC, process, runbook, post-build report, and decision log.
- Read the canonical project documents required by `AGENTS.md`.
- Inspected existing Phase 3 post-build marker conventions.
- Ran `git status --short` before writing; the worktree already contained
  unrelated modified and untracked files.
- Confirmed the requested review file and marker file did not exist before
  writing.
- No tests run; this was a documentation and process review only.

## Files Read

- `AGENTS.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `docs/schema/README.md`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/process/multi-agent-review-loop.md`
- `docs/process/project-judgment.md`
- `docs/process/phase-3-agent-runbook.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_CHANGE_REVIEW_codex_gpt5_5_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_BUILD_REVIEW_codex_gpt5_5_2026_05_05.md`
- `docs/reviews/phase3/README.md`
- `docs/reviews/phase3/postbuild/markers/01_CHANGE_REVIEW_codex_gpt5_5.ready.md`
- `docs/reviews/phase3/postbuild/markers/02_CHANGE_REVIEW_FINDINGS_ADDRESSED.ready.md`
- `docs/reviews/phase3/postbuild/markers/03_LIMIT10_RUN.blocked.md`
- `docs/reviews/phase3/postbuild/markers/04_RFC0013_DRAFT.ready.md`
