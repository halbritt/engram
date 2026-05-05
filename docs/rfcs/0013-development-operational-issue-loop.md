# RFC 0013: Development Operational Issue Loop

Status: accepted
Date: 2026-05-05
Context: D059, D061, RFC 0011, `docs/process/multi-agent-review-loop.md`,
`docs/process/project-judgment.md`,
`docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`

This RFC proposes a repeatable loop for operational issues found while building,
reviewing, and running bounded development pipelines. It is process
architecture, not product architecture. It does not relax Engram's local-first
constraint: no user data leaves the machine unless explicitly requested.

## Problem

Phase 3 exposed two different classes of development failure:

- A build/startup failure where a migration filename was recorded as applied but
  the live schema did not match the code's expectations.
- A bounded post-build runtime failure where one large segment returned invalid
  JSON, yet the orchestrator initially consolidated the rest of that
  conversation.

Both failures were recoverable, but the first response depended too much on
coordinator memory. The project needs a file-backed issue loop that says when to
stop, what to record, who reviews the fix, what stays out of tracked artifacts,
and what must be true before a bounded run can expand.

## Goals

- Make runtime-development failures visible in durable redacted artifacts, not
  chat memory.
- Prevent a blocked bounded run from being accidentally treated as a successful
  gate.
- Preserve raw evidence and keep derived-state repairs auditable.
- Allow bounded development to continue after a localized failure when doing so
  does not hide or compound the failure.
- Require adversarial review for changes to operational policy, data repair
  posture, or run expansion gates.

## Non-Goals

- This RFC does not define product behavior for end users.
- This RFC does not introduce hosted services, external telemetry, or cloud
  persistence.
- This RFC does not authorize full-corpus Phase 3 runs. Full-corpus runs remain
  human checkpoints.
- This RFC does not define a general incident-response process for a deployed
  service. Engram is local-first and currently in development.
- This RFC does not authorize raw corpus content in committed operational
  artifacts.

## Proposal

### 1. Use an issue loop whenever bounded development finds a stop condition

A bounded run enters the operational issue loop when any of these happen:

- a command exits nonzero;
- migration or schema preflight fails;
- local infrastructure needed by the run is unavailable or unhealthy;
- a stage reports failed work inside the selected scope;
- an orchestrator would advance downstream work from incomplete upstream
  evidence;
- a model/runtime failure creates unusable structured output after retries;
- derived-state repair, quarantine, or rebuild is needed;
- the coordinator finds a mismatch between marker state and actual files,
  commands, or database state.

The first response is to stop expansion. Later bounded steps in the same run may
continue only if the failure is isolated and continuing will not mark the failed
scope as complete, promote partial downstream state, or overwrite diagnostics.

At most one operational issue loop should be active per area unless each loop has
a distinct run id and marker directory.

### 2. Classify each issue before fixing it

Use these issue classes in reports and marker front matter:

| Class | Meaning | Default action |
| --- | --- | --- |
| `schema_or_migration_drift` | DB identity, checksum, table, trigger, index, or vocabulary mismatch | Stop all runtime work until fixed and reviewed |
| `infrastructure_or_environment_failure` | PostgreSQL, pgvector, disk, memory, local inference server, or accelerator failure | Stop run; verify local dependencies before rerun |
| `orchestration_bug` | CLI/script/marker sequencing allowed an unsafe transition | Patch orchestration and add tests before rerun |
| `data_repair_needed` | Derived tables need requeue, rebuild, close, or reviewed deletion | Raw evidence remains immutable; repair must be auditable |
| `downstream_partial_state` | Downstream derived rows were produced from incomplete upstream evidence | Repair or enforce quarantine before any ready marker |
| `upstream_runtime_failure` | Extractor, segmenter, embedder, or local model call failed inside the selected scope | Block expansion; downstream scope must be skipped or marked failed |
| `prompt_or_model_contract_failure` | Model returned invalid JSON, wrong object channel, missing required keys, or unsafe claims | Record redacted diagnostics; decide prompt/runtime/schema fix before expansion |
| `review_process_gap` | Re-review, marker, ledger, or human checkpoint did not fire | Fix the process artifact/script before relying on it again |

Reports may use more than one class. The most restrictive default action wins.
The `gate` field in marker front matter records the winning action.

### 3. Keep committed operational artifacts redacted

Default reports and markers live in the repo and may later be pushed. Therefore
they must not contain raw or lightly paraphrased user corpus content.

Committed operational artifacts may include:

- command names and bounded arguments;
- row counts, rates, checksums, IDs, timestamps, and status values;
- error classes and redacted error summaries;
- table names, column names, function names, and migration filenames;
- paths inside the repository.

Committed operational artifacts must not include:

- raw message text, segment text, prompt payloads, or model completion payloads;
- claim or belief object values extracted from the private corpus;
- person names, project names, exact conversation titles, or prose summaries
  derived from private corpus content;
- machine-specific absolute paths or home-directory names;
- local model responses except as redacted error classes/counts.

If private content is necessary to repair an issue, put it in an untracked
local-only artifact under an ignored diagnostics directory such as
`logs/operational/`, and link only to a redacted summary from tracked docs. A
tracked artifact may include private content only with explicit owner approval
and a marker front-matter field `corpus_content_included: owner_approved`.
Markers should never include private corpus content.

### 4. Required artifacts

Each operational issue loop writes artifacts in this order:

1. **Redacted run report** under `docs/reviews/<area>/`.
   Include command, bounds, exit code, canonical counts before/after, issue
   classes, redacted diagnostics, and whether raw evidence changed.
2. **Blocked marker** under that loop's marker directory.
   The marker must use `state: blocked` or `state: human_checkpoint` in
   front matter and must not be an empty sentinel.
3. **Repair plan or RFC update** when the fix changes process, architecture,
   run gates, or data-state policy.
4. **Review artifacts** under `docs/reviews/` for non-trivial changes, following
   `docs/process/multi-agent-review-loop.md`.
5. **Findings synthesis** that classifies review findings as accepted, accepted
   with modification, deferred, or rejected.
6. **Repair report and ready marker** only after accepted findings are applied
   and verification passes.

For Phase 3 post-build reports, canonical counts are:

- `claim_extractions`;
- `claims`;
- `beliefs`;
- `belief_audit`;
- `contradictions`;
- failed extractions;
- failed `consolidation_progress` rows in the selected scope.

Markers are audit provenance. Do not remove old markers to make the queue look
clean. Add new blocked/ready markers that describe the current state.

### 5. Marker schema and precedence

Operational markers use a per-loop directory:

```text
docs/reviews/<area>/postbuild/markers/<YYYYMMDD>_<run_slug>/
```

Use canonical filenames inside that directory:

- `01_RUN.<state>.md`
- `02_REPAIR_PLAN.<state>.md`
- `03_REVIEW_<model_slug>.<state>.md`
- `04_SYNTHESIS.<state>.md`
- `05_REPAIR_VERIFIED.<state>.md`

Existing flat post-build markers are legacy provenance and should not be
renamed unless an owner explicitly asks for a history rewrite.

Each operational marker starts with YAML front matter:

```yaml
---
loop: postbuild
issue_id: <YYYYMMDD_slug>
family: <run|repair_plan|review|synthesis|repair_verified>
scope: <phase-or-command-scope>
bound: <limit0|limit10|targeted|none>
state: blocked | ready | human_checkpoint
gate: blocked | ready_for_same_bound_rerun | ready_for_next_bound | human_checkpoint
classes: [upstream_runtime_failure]
created_at: <ISO-8601 timestamp>
linked_report: docs/reviews/...
supersedes: docs/reviews/.../previous.blocked.md
corpus_content_included: none
---
```

Scripts must compute the newest marker state per `issue_id` and `family`. A
newer `ready` marker resolves an older `blocked` marker only when it shares the
same `issue_id` and `family` and explicitly names the older marker in
`supersedes`. A newer `blocked` or `human_checkpoint` marker blocks expansion
even if older ready markers exist.

### 6. Review requirement

Use the multi-agent review loop for:

- new operational RFCs;
- changes to run-expansion gates;
- changes to derived-state repair/quarantine policy;
- changes that let a downstream phase proceed after upstream failure;
- changes that alter human checkpoints.

Default reviewers:

- broad consistency / local-first / missing-case reviewer;
- implementation and test reviewer;
- operations and model-runtime failure reviewer.

Same-model re-review semantics are governed by
`docs/process/phase-3-agent-runbook.md`: if a reviewer returns
`reject_for_revision`, the revised artifact needs a fresh re-review by that same
reviewer before implementation proceeds. A still-rejecting re-review is a human
checkpoint.

### 7. Verification ladder

A repair is not ready for a larger bounded run until it has passed the smallest
applicable ladder:

1. focused tests for the failed behavior;
2. full test suite when code changed;
3. live preflight that performs no model work;
4. no-work CLI gate such as `pipeline-3 --limit 0`;
5. targeted rerun of the specific failed entity when feasible, or the smallest
   bounded rerun that guarantees exercising the repaired behavior;
6. same-bound rerun when the original failure was bound-scoped;
7. a new redacted run report and marker.

If any ladder step fails, write or update a blocked marker and do not advance to
the next bound.

### 8. Derived-state repair rules

Raw evidence remains immutable. Suspected raw-evidence corruption is out of
scope for this loop and routes to a data RFC or explicit owner decision. This
loop may quarantine or repair derived state that depended on suspect raw rows;
it must not edit raw evidence. Privacy tier reclassification follows D023.

Derived rows may be requeued, superseded, closed, or rebuilt if the repair is
recorded. Deletion is not a default repair path:

- do not delete `beliefs`, `belief_audit`, `contradictions`, or
  `claim_extractions` during development issue loops;
- use transition APIs, close/supersede/rebuild flows, or explicit requeue paths;
- any other derived-row deletion requires a named repair plan, multi-agent
  review, exact `WHERE` selector, pre/post counts, and owner approval.

For conversation-scoped pipelines, downstream consolidation must not mark a
conversation complete when any active upstream segment in that conversation has
failed extraction for the selected prompt/model. The downstream stage should be
skipped or marked failed for that scope, and the command should exit nonzero.

Progress-ledger state alone is not an enforceable quarantine for active derived
rows. A ready marker requires proof that affected partial downstream rows either:

- cannot feed downstream consolidation, review queues, current-belief surfaces,
  retrieval, or context serving because all relevant consumers exclude the
  failed scope; or
- were repaired through close/supersede/rebuild/requeue paths with proof
  queries and before/after counts.

If neither is true, the loop remains `blocked` or `human_checkpoint`.

### 9. Expansion gates

Bounded run expansion uses explicit gates:

- `blocked`: do not expand; a failure or unresolved finding exists.
- `ready_for_same_bound_rerun`: fixed enough to rerun the same bound.
- `ready_for_next_bound`: same bound rerun passed and diagnostics are within
  the limits below.
- `human_checkpoint`: coordinator cannot decide alone.

Default blockers for `ready_for_next_bound`:

- command exit code is nonzero;
- any extraction or downstream stage failed inside the selected scope;
- any prompt/model contract failure occurred inside the selected scope;
- any downstream partial state remains unrepaired or unenforced by query rules;
- dropped-claim rate is above 10% of inserted plus dropped claims;
- an accepted review finding remains unapplied;
- a rejecting same-model re-review has not returned a ready marker.

Per-bound run plans may define stricter thresholds before execution. They may
not loosen these defaults without owner approval.

Owner checkpoint is required to:

- override an unresolved failure;
- retain visible partial derived state;
- change accepted diagnostic limits;
- proceed after `--limit 50`;
- start a corpus-specific or full-corpus Phase 3 run;
- include private corpus content in tracked artifacts.

The default Phase 3 post-build ladder is:

1. `--limit 0`;
2. targeted rerun of any previously failing scope;
3. `--limit 10`;
4. `--limit 50`;
5. larger corpus-specific bounds only after owner approval;
6. full corpus only after owner approval.

### 10. Script and runbook responsibilities

Automation should encode the gate, not merely document it. Before this RFC can
be relied on for Phase 3 post-build expansion:

- tmux/status automation must discover operational markers in the post-build
  marker tree;
- status output must surface the newest blocked or human-checkpoint marker
  before older ready markers;
- next-step output must refuse expansion when the newest marker for a loop is
  `blocked` or `human_checkpoint`;
- bounded run panes must print the exact command and expected report/marker
  paths;
- no script may remove historical markers as a way to resume.

If automation has not yet been updated, the runbook must state that RFC 0013 is
a target policy and that the coordinator must manually enforce the gates.

## Applying This To The Phase 3 Post-Build Failure

The `--limit 10` run is classified as:

- `upstream_runtime_failure`;
- `prompt_or_model_contract_failure`;
- `orchestration_bug`;
- `downstream_partial_state`.

The immediate repair was D061: skip consolidation for a conversation when any
segment extraction fails. The larger unresolved issue is how to reduce or repair
large-segment extractor JSON failure. Expansion past `--limit 10` remains
blocked until that path has a targeted repair or an explicit human acceptance of
the residual risk for further bounded testing.

The partial downstream rows from the first `--limit 10` run are not considered
ready merely because the progress ledger marks the conversation failed. They
remain a blocked post-build state until repaired or covered by enforceable query
exclusion.

## Open Questions

1. Should the project add a dedicated `docs/reviews/operations/` area, or keep
   operational artifacts under the active phase directory?
2. Should derived-state quarantine eventually have a first-class DB status, or
   are repair/rebuild paths sufficient during development?
3. Should the initial 10% dropped-claim threshold vary by stability class or
   predicate family after more bounded runs?

## Acceptance Criteria

- Multi-agent review completed on 2026-05-05.
- Accepted review findings were synthesized and applied.
- The rejecting Codex reviewer performed same-model re-review and accepted the
  revised RFC.
- Binding process decision D062 was promoted to `DECISION_LOG.md`.
- `docs/process/phase-3-agent-runbook.md` was updated with the accepted
  post-build operational issue loop.
- `scripts/phase3_tmux_agents.sh` now surfaces post-build blocked and
  human-checkpoint markers in `status` and blocks `next` while they remain.
- The next Phase 3 bounded run must use a redacted report, machine-readable
  marker, and the accepted gates.
