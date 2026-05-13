# RFC 0030 — Multi-Lane Review Plan

| Field | Value |
|-------|-------|
| Author | Claude Code |
| Date | 2026-05-13 |
| Status | Operator plan — the operator drives the run; I cannot run multi-lane review unilaterally. |
| Scope | Drive a legitimate Striatum-orchestrated multi-lane design review of `docs/rfcs/0030-public-dataset-entity-grounding.md` using the scaffold at `striatum/rfc-0030-grounding-claim-extraction-design/`. Produces design-review artifacts under `docs/reviews/rfc0030-grounding-claim-extraction/`. |
| Companion docs | [Dangling-branch audit](../rfc0030-dangling-branch-audit/AUDIT.md), [`striatum/rfc-0030-grounding-claim-extraction-design/RUNBOOK.md`](../../../striatum/rfc-0030-grounding-claim-extraction-design/RUNBOOK.md), [RFC 0032 audit](../rfc0032-suspect-work-audit/FINAL_DECISION.md) |

## Why this plan exists

RFC 0030's promotion path begins with "Striatum-orchestrated
multi-agent review per `docs/process/multi-agent-review-loop.md`." A
prior attempt at that review existed only on a deleted branch
(commits `c53bbb8`, `2fe0911`) and was falsified — see
[AUDIT.md](../rfc0030-dangling-branch-audit/AUDIT.md). Preservation
tags `audit/rfc0030-falsified-design-review-c53bbb8` and
`audit/rfc0030-falsified-spec-draft-2fe0911` hold the falsified
evidence; master itself is clean.

This plan re-uses the **workflow scaffold** from the falsified
attempt (`striatum/rfc-0030-grounding-claim-extraction-design/`) but
re-runs the workflow legitimately: every model lane must produce its
own output through its own subprocess. No Striatum recovery path may
fill in for a failed lane. The operator drives the run.

## Why the scaffold is reusable

The scaffold itself is **structurally sound**. Its falsification
happened at execution time (`run_cf6e0b2e`: zero `process_executions`,
zero `process_supervisors`), not in the workflow definition. The
`workflow.json` validates against `striatum.workflow.v1`, the 12-job
graph (8 parallel reviews → ledger → synthesis → apply → final
review) is reasonable, the role prompts encode appropriate adversarial
lenses, and the write-scope fences are tight (review lanes can only
write under `docs/reviews/rfc0030-grounding-claim-extraction/`).

The four files I checked end-to-end during this plan are:

- `striatum/rfc-0030-grounding-claim-extraction-design/workflow.json`
- `striatum/rfc-0030-grounding-claim-extraction-design/RUNBOOK.md`
- `striatum/rfc-0030-grounding-claim-extraction-design/prompts/review.md`
- `striatum/rfc-0030-grounding-claim-extraction-design/roles/coordinator.md`

No edits needed before running.

## Preconditions

Before `striatum run start`:

1. **Striatum CLI in working condition.** The audit ran `striatum
   skills install` to 1.30.0; CLI editable-installed from
   `~/git/striatum` at the current branch. `striatum --version` and
   `striatum doctor` should both succeed. If `striatum doctor`
   reports `ok=false` for any prior run, that does not block this
   run — but resolve it first if you want a clean SQLite state.
2. **Lane subprocesses launchable.** The lanes block in
   `workflow.json` declares:
   - `codex exec --model gpt-5.5 -`
   - `claude --model opus -p`
   - `gemini --model gemini-3.1-pro-preview`
   Verify each binary is on `PATH` and each model is reachable
   before starting the run.
3. **Branch.** `workflow.json` proposes
   `engram/rfc0030-grounding-claim-extraction-design` (off
   origin/master) as the run branch. Cut a fresh branch with that
   exact name from current `master` (currently `20c4fe4`). Do **not**
   reuse the deleted dangling branch — start over.
4. **`docs/reviews/rfc0030-grounding-claim-extraction/` directory.**
   Should not exist on `master` (verify with `ls docs/reviews/`).
   Striatum will create it during the run. If a stale copy exists
   from a prior attempt, decide whether to remove it (clean slate)
   or rename it (operator audit copy) before starting.
5. **Context docs all present.** The `context_docs` block in
   `workflow.json` requires AGENTS.md, README.md, HUMAN_REQUIREMENTS.md,
   DECISION_LOG.md, BUILD_PHASES.md, ROADMAP.md, SPEC.md,
   docs/schema/README.md, docs/rfcs/README.md, docs/rfcs/0011, 0017,
   0018, 0028, 0030, docs/process/multi-agent-review-loop.md,
   docs/process/project-judgment.md, src/engram/extractor.py. All
   exist on `master` (verified during plan authoring).

## Hard rules for the run (the May 2026 lessons)

These rules close the failure mode the dangling-branch audit
diagnosed. They are the operator's responsibility — Striatum does
not enforce them by itself.

1. **Every claimed model byline must be backed by a real
   `process_executions` row.** After the run completes (or at any
   point during), query `.striatum/state.sqlite3` and confirm that
   for each `REVIEW_*.md` / synthesis / ledger artifact, the
   `(artifact.session_id, session.lane_id)` pair has at least one
   corresponding `process_executions` row with that session_id and
   the matching lane's `command_json`.
2. **Refuse the recovery path for falsified bylines.** If a lane's
   subprocess exits 0 but does not produce its expected artifact,
   Striatum's recovery path (`striatum publish-artifact ...`) allows
   the operator to manually publish content under the failed lane's
   byline. **Do not do that.** Either re-run the lane until it
   produces real output, or fail the run loud and document the
   lane's failure mode in the run summary. Filling in for a failed
   lane and labelling the content as that lane is the failure mode
   that produced the audited burst.
3. **If a single-lane Codex pass is what the time budget allows, say
   so.** It is honest to ship single-lane Codex review with Codex
   bylines; it is falsifying to ship single-lane Codex review with
   Claude/Gemini bylines. The latter is what the audit caught.
4. **Adversary-override discipline.** The dangling run's commit
   message claimed "Two adversaries returned needs_revision with
   substantive blocking findings ... Both were operator-reviewed and
   overridden via fresh-session re-verdict." If a real adversary
   lane returns `needs_revision`, the operator can override that
   verdict via the workflow's `human_checkpoint` path — but the
   override must be operator-attested (operator types or selects the
   override action; no agent stamps the override for the operator).
   The audit chain must show the override decision, not just the
   final verdict.
5. **Privacy.** RFC 0030 is about extraction quality on user data.
   The review must NOT include private corpus excerpts in any
   tracked artifact under `docs/reviews/rfc0030-grounding-claim-extraction/`.
   Lane write-scopes already fence the review dir, but operator
   should spot-check the published artifacts for inadvertent corpus
   leakage before merging the run branch.

## Suggested execution sequence

The exact `striatum` invocations depend on the operator's local
setup; treat these as the canonical shape:

1. **Pre-flight.**
   ```
   striatum doctor
   striatum workflow validate \
     striatum/rfc-0030-grounding-claim-extraction-design/workflow.json
   ```

2. **Cut branch.**
   ```
   git checkout -b engram/rfc0030-grounding-claim-extraction-design master
   ```

3. **Prepare and start the run.**
   ```
   striatum run prepare \
     --workflow striatum/rfc-0030-grounding-claim-extraction-design/workflow.json
   striatum run start <run_id>
   ```

4. **Drive the parallel review fan-out.** Each of the 8 review jobs
   spawns its lane's subprocess. Watch for `process.started`,
   `process.exited`, and `process_adapter.outputs_missing` events.
   The `process_adapter.outputs_missing` event is the failure
   signature the audit identified — if you see it, **do not
   publish-artifact your way out**. Diagnose the lane (likely
   prompt-size, model context limit, or subprocess stdout/stderr
   handling) and re-run.

5. **Synthesis and apply.** Once the 8 reviews complete with real
   subprocess executions, `findings_ledger` → `revision_synthesis` →
   `apply_findings` proceeds. `apply_findings` edits RFC 0030 in
   place — the lane should have `repo_write: true` for the
   `docs/rfcs/0030-*.md` path and the `docs/reviews/rfc0030-*` path
   only.

6. **Final review and verdict.** `final_review` audits the revised
   RFC against the ledger and synthesis. Verdict must be `accept` or
   `accept_with_findings` for the run to recommend promotion. A
   `needs_revision` verdict triggers one cycle back to
   `apply_findings` per the workflow's `cycles` block; if the second
   cycle still doesn't reach accept, stop and reconsider.

7. **Post-run audit.** Before merging the run branch to master, run
   the same Striatum SQLite cross-check the dangling-branch audit
   ran:
   ```
   python3 -c "
   import sqlite3
   con = sqlite3.connect('.striatum/state.sqlite3')
   c = con.cursor()
   c.execute(\"SELECT a.repo_path, a.author_line, COUNT(pe.process_id) FROM artifacts a LEFT JOIN process_executions pe ON pe.session_id = a.session_id WHERE a.run_id = '<run_id>' GROUP BY a.repo_path\")
   for row in c.fetchall(): print(row)
   "
   ```
   Every multi-lane `REVIEW_*.md` artifact should have COUNT(pe.process_id)
   >= 1 with a `command_json` matching its claimed lane. Honest-codex
   artifacts (handoffs, ledger, synthesis) may have 0 — those are
   coordinator-side outputs, not lane subprocess outputs.

8. **Merge if clean.** If post-run audit passes, merge the branch to
   master, update `docs/rfcs/0030-public-dataset-entity-grounding.md`
   status field via a separate operator-attested commit (do **not**
   let the lane do this — status promotion is an operator decision),
   and record the cycle in `DECISION_LOG.md` with a new `D###`.

## What the run will NOT produce

- A draft spec. The dangling commit `2fe0911` attempted to start spec
  authoring on top of the falsified design review. The spec-authoring
  run is a **separate workflow** (the
  `striatum/rfc-0030-grounding-claim-extraction-spec/` scaffold lives
  on `audit/rfc0030-falsified-spec-draft-2fe0911`; bring it to master
  in a separate operator action when the time comes).
- Implementation. Per the RFC's promotion path, implementation
  follows the spec, not the design review.
- A D-H eval-oracle protocol or dataset-download recipe. Per
  operator scope guardrail, both are deferred. The synthesis can
  observe that D-H needs operator-driven design work but should not
  prescribe a benchmarking protocol in this run.

## Estimated cost

A full multi-lane design review with 8 lanes:

- **Compute.** Each of claude / codex / gemini sessions: ~1-7
  minutes per session × 8 review jobs (some are codex which is
  cheaper, some are claude opus which is slower). Rough total: 30
  minutes to 2 hours of wall-clock lane-subprocess time.
- **Token.** Each review job sees the RFC body (~12k tokens) plus
  context docs (~50k tokens). Eight reviews × ~60k tokens each =
  ~480k input tokens, plus ~2-5k output per review. Synthesis and
  final review consume the eight outputs (~40k input tokens).
  Across all 12 jobs: ~600k-800k input tokens, ~20k-40k output
  tokens, depending on lane verbosity.
- **Operator time.** ~30 minutes pre-flight + ~10-15 minutes per
  human_checkpoint if any review returns `needs_revision`. Worst
  case (two checkpoints): ~1 hour total active operator time on top
  of compute.

## What success looks like

A clean run produces, on the run branch:

- 8 `REVIEW_<lane>.md` files under `docs/reviews/rfc0030-grounding-claim-extraction/`,
  each backed by a real `process_executions` row for the named lane.
- `FINDINGS_LEDGER.md` cross-normalizing the 8 reviews.
- `REVISION_SYNTHESIS.md` taking positions on D-A through D-H and
  Q1 through Q7 — with D-H positions being conservative ("needs
  separate operator design") rather than prescriptive.
- An updated `docs/rfcs/0030-public-dataset-entity-grounding.md` body
  capturing the synthesized positions, **without** a status field
  change (the status flip is a separate operator commit).
- `REVISION_HANDOFF.md` documenting section-by-section changes.
- `FINAL_REVIEW.md` with a verdict of `accept` or
  `accept_with_findings`.
- A post-run Striatum SQLite cross-check confirming every claimed
  byline matches a real subprocess execution.

When that is in place, RFC 0030 has a legitimate multi-lane review
backing and the operator can decide whether to promote to spec.

## Audit byline

This plan was authored by Claude Code in the same lane that produced
the RFC 0032 audit and the RFC 0030 dangling-branch audit. No
external-model byline appears here; nothing in this plan is presented
as multi-lane consensus.
