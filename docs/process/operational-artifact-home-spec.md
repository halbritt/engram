# Operational Artifact Home Spec

Status: accepted implementation spec
Date: 2026-05-06
Revised: 2026-05-06 after P004 package checkpoint
Accepted: 2026-05-06 by owner for Phase 3 implementation
author: coordinator-codex-gpt-5.5-001
Source RFC: `docs/rfcs/0014-operational-artifact-home.md`
Source reviews: `docs/reviews/rfc-0014-operational-artifact-home/`

This spec turns RFC 0014 review findings into explicit implementation choices.
Owner acceptance on 2026-05-06 promotes these choices into the Phase 3 runbook
and script implementation scope. Binding project history is recorded in
`DECISION_LOG.md`; this spec remains the detailed handoff contract.

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

S010: Keep legacy flat blocked and human-checkpoint markers gate-active during
the migration.
Rationale: Existing flat files under `docs/reviews/phase3/postbuild/markers/`
are imperfect historical artifacts, but treating them as audit-only would
silently clear old blockers.

S011: Markers are stricter than prose reports for private content.
Rationale: Markers are small machine-readable gate records and should never
carry private corpus content, even with owner approval. Private repair evidence
belongs in ignored diagnostics, with only redacted summaries in tracked docs.

## Canonical Layout

New committed operational loops use this shape:

```text
docs/operations/<area>/<loop_id>/
  reports/
    01_RUN_REPORT.md
    02_REPAIR_PLAN.md
    05_REPAIR_VERIFIED.md
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

Committed operational artifacts under `docs/operations/` follow RFC 0013
Section 3 privacy and redaction rules unchanged. That section is authoritative
for the allow list, forbid list, ignored-diagnostics routing, and tracked
artifact owner-approval exception.

Markers are stricter than prose reports. A marker must never contain private
corpus content, even when the owner has approved private detail for a repair.
If private content is needed, it goes in ignored local diagnostics such as
`logs/operational/`; the tracked report may link only to a redacted summary.

For markers, the required value is always:

```yaml
corpus_content_included: none
```

The `owner_approved` exception from RFC 0013 remains available only for
tracked prose artifacts that explicitly need it and record the owner approval
as RFC 0013 requires. It is not valid for marker files.

D060 path hygiene applies. Tracked documentation and artifacts must use
repository-relative paths, environment variables, or generalized `~/` paths
instead of hardcoded home-directory absolute paths such as `/home/<user>/...`,
`/Users/<user>/...`, or the current user's `$HOME` path. Marker front matter is
stricter: marker paths must be repository-relative POSIX-style paths.

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
created_at: <RFC3339 timestamp with Z or +/-HH:MM offset>
linked_report: docs/operations/<area>/<loop_id>/reports/01_RUN_REPORT.md
supersedes: docs/reviews/<legacy-area>/postbuild/markers/<loop_id>/01_RUN.blocked.md
corpus_content_included: none
---
```

During transition, `linked_report` and `supersedes` may point to either new
`docs/operations/...` paths or legacy RFC 0013 `docs/reviews/...` paths. All
paths in marker front matter must be repository-relative POSIX-style paths.

New and per-loop migrated markers must have parseable front matter with these
required scalar fields: `loop`, `issue_id`, `family`, `scope`, `bound`,
`state`, `gate`, `classes`, `created_at`, `linked_report`, and
`corpus_content_included`. `supersedes` is required when a marker resolves a
prior blocker or checkpoint; it is otherwise optional. Missing, duplicate, or
invalid required fields are schema failures.

`loop` must be `postbuild`. `state` must be one of `blocked`, `ready`, or
`human_checkpoint`. `gate` must be a blocked, ready, or human-checkpoint gate
identifier. `created_at` must be timezone-aware RFC3339/ISO-8601 with either
`Z` or a numeric offset such as `+00:00`; naive timestamps are invalid.
`corpus_content_included` must be exactly `none`.

Missing or invalid front matter in new or per-loop migrated markers blocks as
a human checkpoint until corrected or explicitly superseded. Front-matterless
flat legacy markers are handled by the special legacy rules below; they are
not a template for new markers.

## Compatibility Semantics

During migration, scripts must treat new and legacy marker roots as one logical
marker set for a given operational loop.

For Phase 3 post-build migration, tooling scans all of:

```text
docs/operations/phase3-postbuild/<loop_id>/markers/
docs/reviews/phase3/postbuild/markers/<loop_id>/
docs/reviews/phase3/postbuild/markers/*.md
```

Existing flat legacy post-build markers under
`docs/reviews/phase3/postbuild/markers/*.md` remain historical provenance and
gate inputs. New expansion gates should be represented by the per-loop legacy
or operations-root marker directories above, but tooling must not ignore a flat
legacy `.blocked.md` or `.human_checkpoint.md` file merely because it predates
the RFC 0013 front-matter schema.

Flat legacy marker rules:

1. A flat legacy marker with parseable front matter participates in the normal
   `(issue_id, family)` precedence rules.
2. A flat legacy `.blocked.md` or `.human_checkpoint.md` marker without
   parseable front matter is a root-scoped Phase 3 post-build blocker.
3. Tooling must not infer `(issue_id, family)` from a front-matterless flat
   filename. It may show a best-effort display label from the filename, but the
   marker's normalized repository path is its only stable identity.
4. A front-matterless flat blocker is resolved only by a later `ready` marker
   whose `supersedes` field names the exact flat marker path and whose linked
   redacted report explains why that historical blocker is obsolete.
5. A front-matterless flat ready marker is audit provenance only. It does not
   resolve a blocked or human-checkpoint marker unless it has parseable front
   matter and satisfies the normal supersession rules.

Precedence rules:

1. Normalize every marker path as a repository-relative POSIX string.
2. Group schema-bearing markers by `(issue_id, family)` across all scanned
   roots.
3. For schema-bearing markers, `created_at` is required and must be a valid
   timezone-aware RFC3339/ISO-8601 timestamp with `Z` or a numeric offset.
   Missing, naive, or invalid `created_at` is not an ordering hint; it is a
   malformed marker and blocks as a human checkpoint.
4. For each valid group, order markers by `created_at`, then by repository path.
   File modification time may be used only for display ordering of
   front-matterless flat legacy markers, not for resolving schema-bearing
   precedence.
5. A `ready` marker resolves an older `blocked` marker only when it shares the
   same `(issue_id, family)` and names the exact older repository-relative
   marker path in `supersedes`, even when the two markers live in different
   roots.
6. A `human_checkpoint` marker remains blocking until a later `ready` marker
   explicitly supersedes it by exact repository-relative path and records
   `owner_decision: recorded` plus `owner_decision_evidence:
   <repo-relative path>` for the owner decision that resolved the checkpoint.
   Timestamp order, matching filenames, a generic ready marker, or a bare
   `linked_report`/`linked_decision` value are not enough to clear a human
   checkpoint.
7. A newer unsuperseded `blocked` or `human_checkpoint` marker blocks
   expansion even if older ready markers exist.
8. If schema-bearing marker front matter is malformed, missing required fields,
   ambiguous, contradictory, or privately contaminated, tooling must fail
   closed and surface a human checkpoint rather than assuming the loop is ready.

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
   new operations marker root, legacy RFC 0013 per-loop marker root, and flat
   legacy marker files as one logical marker set.
5. Preserve marker front matter unchanged. `linked_report` and `supersedes`
   may point to either new operations paths or legacy review-root paths during
   transition.
6. Preserve old markers as audit provenance. Do not delete, rename, or move
   existing artifacts unless the owner explicitly asks for history cleanup.
7. Optionally add `docs/operations/README.md` as a redacted index of active and
   historical operational loops. Scripts must not depend on this index.
8. Retire legacy-root scanning only after the owner confirms that no unresolved
   `blocked` or `human_checkpoint` marker remains in the per-loop or flat
   legacy paths and no active run depends on legacy marker provenance.

## Implementation Fixtures

An implementation prompt should include deterministic fixtures for:

- a legacy `blocked` marker plus new operations-root `ready` marker that
  supersedes it;
- a front-matterless flat legacy `.blocked.md` marker that remains gate-active
  until a later ready marker supersedes its exact path;
- a new operations-root `ready` marker plus newer legacy `blocked` marker that
  remains blocking;
- malformed, ambiguous, missing, invalid, or naive marker front matter that
  fails closed;
- a marker with forbidden private-content fields, `corpus_content_included:
  owner_approved`, or hardcoded home-directory path rejected by validation;
- a `human_checkpoint` marker that remains blocking until exact-path
  supersession plus explicit `owner_decision: recorded` and
  `owner_decision_evidence` front matter;
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
  per-loop and flat review-root marker paths;
- old markers remain as audit provenance;
- scripts can read operations-root, per-loop legacy, and flat legacy marker
  paths during transition;
- RFC 0013 marker front matter remains compatible;
- flat legacy blocked and human-checkpoint markers remain gate-active until
  explicitly superseded by exact path;
- marker files reject private corpus content absolutely;
- human-checkpoint markers require exact-path supersession and explicit
  owner-decision evidence;
- malformed or invalid marker front matter, including missing, invalid, or
  naive `created_at`, fails closed;
- D060 path hygiene remains enforced;
- the `agent_runner` live-state boundary remains explicit.
