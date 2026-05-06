# Operational Artifact Home Spec

Status: draft implementation spec
Date: 2026-05-06
author: coordinator-codex-gpt-5.5-001
Source RFC: `docs/rfcs/0014-operational-artifact-home.md`
Source reviews: `docs/reviews/rfc-0014-operational-artifact-home/`

This spec turns RFC 0014 review findings into explicit implementation choices.
It is a handoff artifact, not an accepted architecture decision by itself. It
becomes binding only when promoted into the decision log, build phases, phase
runbook, or an accepted implementation prompt.

## Purpose

Engram needs a committed home for redacted development operational artifacts
that is distinct from model review feedback and distinct from ignored local
diagnostics. RFC 0014 proposed that separation, but review found that the RFC
still contained unresolved layout choices. This spec makes those choices
explicit so a later implementation or final disposition is not left to infer
them.

## Explicit Choices

S001: Use `docs/operations/` as the tracked root for committed, redacted
operational artifacts.
Rationale: `docs/operations/` is clear and avoids confusion with ignored
`logs/operational/`; shorter `docs/ops/` is less readable, and
`docs/operational/` is too close to the diagnostics path.

S002: Use phase-scoped area names. Phase 3 post-build work uses
`docs/operations/phase3-postbuild/<loop_id>/`.
Rationale: The legacy RFC 0013 path is already phase-oriented, and a single
area string gives scripts a deterministic mapping during migration.

S003: Keep reports and markers separate. Reports are prose under `reports/`;
gate state lives only under `markers/`.
Rationale: Reports and markers have different consumers, redaction surfaces,
and validation requirements.

S004: Do not require per-loop `README.md` files.
Rationale: A loop README creates another artifact contract without adding
required machine-readable state. A future root index can be added separately.

S005: Keep multi-agent reviews under `docs/reviews/`.
Rationale: Review feedback, synthesis, and final-review artifacts are not
operational gate markers.

S006: Preserve RFC 0013 marker front matter.
Rationale: The path changes, but `issue_id`, `family`, `gate`,
`linked_report`, `supersedes`, and privacy fields stay compatible.

S007: During transition, compute marker state across new and legacy roots as
one logical marker set.
Rationale: This preserves old blocked/human-checkpoint provenance without
making old paths permanently block migration.

S008: Supersede RFC 0013's future path guidance instead of rewriting RFC 0013
history.
Rationale: Accepted RFCs remain point-in-time records. A deprecation
cross-reference is acceptable; retroactive inline rewriting is not.

S009: Treat `agent_runner` SQLite as live workflow state; repository markers
are durable artifacts only.
Rationale: RFC 0014 is useful as a validation fixture, but it must not teach
the generic runner that marker files are queue truth.

## Canonical Layout

New committed operational loops use this shape:

```text
docs/operations/<area>/<loop_id>/
  reports/
    01_RUN_REPORT.md
    02_REPAIR_PLAN.md
    05_REPAIR_VERIFICATION.md
  markers/
    01_RUN.blocked.md
    02_REPAIR_PLAN.ready.md
    03_REVIEW_<model_slug>.ready.md
    04_SYNTHESIS.ready.md
    05_REPAIR_VERIFIED.ready.md
```

For Phase 3 post-build work:

```text
docs/operations/phase3-postbuild/<YYYYMMDD>_<run_slug>/
```

Reports are human-readable redacted prose. Reports do not carry
`.<state>.md` suffixes and are not read by scripts as gate state.

Markers are the only committed files that carry operational gate state.
Automation must read the `markers/` subtree for `blocked`, `ready`, and
`human_checkpoint` status.

Review artifacts stay under `docs/reviews/`, for example:

```text
docs/reviews/phase3/RFC_0014_OPERATIONAL_ARTIFACT_HOME_REVIEW_<model_slug>_2026_05_05.md
```

Untracked local-only diagnostics remain under ignored paths such as:

```text
logs/operational/<YYYYMMDD>_<run_slug>/
```

## Artifact Rules

Committed operational artifacts under `docs/operations/` inherit RFC 0013's
privacy and redaction rules.

Allowed content includes command names, bounded arguments, row counts, IDs,
timestamps, status values, error classes, table/column/function names, and
repository-relative paths.

Forbidden content without explicit owner approval includes raw message text,
segment text, prompt payloads, model completion payloads, extracted
claim/belief values, private names, exact conversation titles, corpus-derived
prose summaries, machine-specific absolute paths, and home-directory names.

Markers should never contain private corpus content unless the owner explicitly
approves a tracked-artifact exception. In that exceptional case, front matter
must set:

```yaml
corpus_content_included: owner_approved
```

The normal value is:

```yaml
corpus_content_included: none
```

D060 path hygiene applies. Tracked documentation and artifacts should use
repository-relative paths, environment variables, or generalized `~/` paths
instead of hardcoded home-directory absolute paths.

## Marker Schema

RFC 0014 preserves RFC 0013 marker front matter. The path changes; the schema
does not.

New markers use this shape:

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
linked_report: docs/operations/<area>/<loop_id>/reports/01_RUN_REPORT.md
supersedes: docs/reviews/<legacy-area>/postbuild/markers/<loop_id>/01_RUN.blocked.md
corpus_content_included: none
---
```

During transition, `linked_report` and `supersedes` may point to either new
`docs/operations/...` paths or legacy RFC 0013 `docs/reviews/...` paths. All
paths in marker front matter must be repository-relative POSIX-style paths.

## Compatibility Semantics

During migration, scripts must treat new and legacy marker roots as one logical
marker set for a given operational loop.

For Phase 3 post-build migration, tooling scans both:

```text
docs/operations/phase3-postbuild/<loop_id>/markers/
docs/reviews/phase3/postbuild/markers/<loop_id>/
```

Existing flat legacy post-build markers under
`docs/reviews/phase3/postbuild/markers/` remain historical provenance. Tooling
may index them for audit, but new expansion gates should be represented by the
per-loop legacy or operations-root marker directories above.

Precedence rules:

1. Normalize every marker path as a repository-relative POSIX string.
2. Group markers by `(issue_id, family)` across both roots.
3. For each group, order markers by valid `created_at`, then by repository
   path. A marker missing `created_at` sorts before a marker with a valid
   timestamp.
4. A `ready` marker resolves an older `blocked` marker only when it shares the
   same `(issue_id, family)` and names the exact older repository-relative
   marker path in `supersedes`, even when the two markers live in different
   roots.
5. A `human_checkpoint` marker remains blocking until a later marker explicitly
   supersedes it and the linked report records the owner decision that resolved
   the checkpoint.
6. A newer unsuperseded `blocked` or `human_checkpoint` marker blocks
   expansion even if older ready markers exist.
7. If marker front matter is malformed, ambiguous, or contradictory, tooling
   must fail closed and surface a human checkpoint rather than assuming the loop
   is ready.

Precedence is computed within a loop id. A ready marker in one
`<area>/<loop_id>` must not resolve a blocked marker from another loop.

## Agent Runner Boundary

`agent_runner` uses SQLite under `.agent_runner/state.sqlite3` as live workflow
state. Repository files are durable provenance and commit-ready artifacts only.

RFC 0014 remains a useful `agent_runner` validation fixture for artifact
publication, review-only parallelism, write-scope enforcement, verdict
collection, redacted evidence export, and blocked-run introspection. It is not
a fixture for teaching `agent_runner` to infer queue truth from marker files.

If an `agent_runner` workflow publishes operational reports or markers under
`docs/operations/`, those files are still artifacts recorded through runner job
transitions. The runner state remains authoritative for claims, leases, job
states, blockers, and verdicts.

## Migration Work

If this spec is accepted for implementation:

1. Record that RFC 0014 supersedes RFC 0013's committed operational artifact
   path guidance for future artifacts.
2. Add at most a deprecation cross-reference to RFC 0013; do not rewrite it as
   though its historical text always pointed to `docs/operations/`.
3. Update `docs/process/phase-3-agent-runbook.md` so future committed
   operational reports and markers use `docs/operations/phase3-postbuild/`.
4. Update `scripts/phase3_tmux_agents.sh` so status and gate commands scan the
   new operations marker root and legacy RFC 0013 marker root as one logical
   marker set.
5. Preserve marker front matter unchanged. `linked_report` and `supersedes`
   may point to either new operations paths or legacy review-root paths during
   transition.
6. Preserve old markers as audit provenance. Do not delete, rename, or move
   existing artifacts unless the owner explicitly asks for history cleanup.
7. Optionally add `docs/operations/README.md` as a redacted index of active and
   historical operational loops. Scripts must not depend on this index.
8. Retire legacy-root scanning only after the owner confirms that no unresolved
   `blocked` or `human_checkpoint` marker remains in the legacy path and no
   active run depends on legacy marker provenance.

## Implementation Fixtures

An implementation prompt should include deterministic fixtures for:

- a legacy `blocked` marker plus new operations-root `ready` marker that
  supersedes it;
- a new operations-root `ready` marker plus newer legacy `blocked` marker that
  remains blocking;
- malformed or ambiguous marker front matter that fails closed;
- a marker with forbidden private-content fields or hardcoded home-directory
  path rejected by validation;
- `linked_report` pointing to a legacy report path and to a new operations-root
  report path;
- status output surfacing the newest blocking marker before older ready
  markers.

## Acceptance Criteria

The spec is implementation-ready when review confirms:

- the chosen path does not blur committed redacted artifacts with untracked
  private diagnostics;
- reports and markers are separate artifact families with separate consumers;
- RFC 0013 marker precedence works across the new operations root and legacy
  review-root marker path;
- old markers remain as audit provenance;
- scripts can read both new and legacy marker paths during transition;
- RFC 0013 marker front matter remains compatible;
- D060 path hygiene remains enforced;
- the `agent_runner` live-state boundary remains explicit.
