# RFC 0014: Operational Artifact Home

Status: proposal
Date: 2026-05-05
Spec handoff: `docs/process/operational-artifact-home-spec.md` on 2026-05-06
Context: D060, D062, D063, RFC 0013,
`docs/process/multi-agent-review-loop.md`,
`docs/process/phase-3-agent-runbook.md`

This RFC proposes a clearer home for development operational artifacts. It is
for later review. It does not move existing files and does not change the
current RFC 0013 gate until accepted.

The 2026-05-06 dogfood review showed that this RFC was still a proposal sketch:
the layout choices needed to become explicit in a spec before implementation or
final human disposition. The review-derived spec handoff is
`docs/process/operational-artifact-home-spec.md`. That spec resolves the open
layout questions for review and implementation planning, but it does not by
itself accept this RFC or move any files.

## Problem

RFC 0013 currently stores committed operational reports under
`docs/reviews/<area>/` and operational markers under
`docs/reviews/<area>/postbuild/markers/`. That was convenient because the
multi-agent review loop already uses `docs/reviews/`, but it also overloads the
meaning of "review":

- model review feedback,
- synthesis artifacts,
- operational run reports,
- blocked/ready markers,
- repair reports.

This makes it harder to answer simple coordination questions such as "what
operational loops are active?" or "which bounded runs are blocked?" without
searching through review artifacts. It also led to confusion about whether an
`operations` area had been agreed to.

## Goals

- Separate operational run state from model review feedback.
- Preserve RFC 0013's privacy and redaction rules.
- Preserve marker provenance: old markers are not deleted to make queues look
  clean.
- Keep multi-agent reviews under `docs/reviews/`.
- Make future automation simpler by giving operational loops one stable root.

## Non-Goals

- This RFC does not authorize moving existing artifacts before review.
- This RFC does not change the local-first/no-egress constraint.
- This RFC does not authorize raw corpus content in committed operational
  artifacts.
- This RFC does not replace `logs/operational/` for untracked local-only
  diagnostics.
- This RFC does not change Phase 3 expansion gates by itself.
- This RFC does not make repository markers an `agent_runner` control plane.

## Proposal Sketch

Use a tracked operations root for committed, redacted operational artifacts:

```text
docs/operations/
```

Use this layout:

```text
docs/operations/<area>/<loop_id>/
  README.md
  reports/
    01_RUN.blocked.md
    02_REPAIR_PLAN.ready.md
    05_REPAIR_VERIFIED.ready.md
  markers/
    01_RUN.blocked.md
    02_REPAIR_PLAN.ready.md
    03_REVIEW_<model_slug>.ready.md
    04_SYNTHESIS.ready.md
    05_REPAIR_VERIFIED.ready.md
```

For Phase 3 post-build work, the equivalent path would be:

```text
docs/operations/phase3-postbuild/<YYYYMMDD>_<run_slug>/
```

Review artifacts remain under `docs/reviews/`, for example:

```text
docs/reviews/phase3/RFC_0014_OPERATIONAL_ARTIFACT_HOME_REVIEW_<model_slug>_2026_05_05.md
```

Untracked local-only diagnostics remain under ignored paths such as:

```text
logs/operational/<YYYYMMDD>_<run_slug>/
```

This section is the original proposal sketch, not the final implementation
contract. The spec handoff records the chosen root, loop layout, marker
compatibility semantics, and `agent_runner` boundary.

## Artifact Rules

Committed operational artifacts under `docs/operations/` follow the same
redaction rules as RFC 0013:

- allowed: command names, bounded arguments, row counts, IDs, timestamps, status
  values, error classes, table/column/function names, and repository-relative
  paths;
- forbidden without explicit owner approval: raw message text, segment text,
  prompt payloads, model completion payloads, extracted claim/belief values,
  private names, exact conversation titles, corpus-derived prose summaries,
  machine-specific absolute paths, and home-directory names.

Markers should never contain private corpus content.

## Migration Plan If Accepted

1. Promote a concrete spec for the operational artifact home. The 2026-05-06
   handoff spec is `docs/process/operational-artifact-home-spec.md`.
2. Record that accepted RFC 0014 supersedes RFC 0013's committed operational
   artifact path guidance for future artifacts. Do not rewrite RFC 0013 as
   though its historical text always pointed to `docs/operations/`; at most,
   add a deprecation cross-reference.
3. Update `docs/process/phase-3-agent-runbook.md`.
4. Update `scripts/phase3_tmux_agents.sh` to read blocked/ready markers from
   the new operations root and legacy RFC 0013 marker roots as one logical
   marker set.
5. Preserve marker front matter and cross-root `supersedes` semantics from
   RFC 0013.
6. Optionally add a historical index entry in `docs/operations/README.md`
   linking to legacy RFC 0013-era artifacts.
7. Do not rewrite or move existing artifacts unless the owner explicitly asks
   for that history cleanup.

## Open Questions

The initial RFC left these questions open. The spec handoff resolves them so
they can be reviewed as explicit choices rather than inferred during
implementation.

- Should the root be `docs/operations/`, `docs/ops/`, or
  `docs/operational/`?
- Should reports and markers be separate files, or should one marker file carry
  enough front matter to serve as the report index?
- Should every loop have a `README.md`, or is the marker/report pair enough?
- Should the operation area be phase-scoped (`phase3-postbuild`) or
  process-scoped (`postbuild/phase3`)?

## Acceptance Criteria

This RFC is accepted only after review confirms:

- the chosen path does not blur committed redacted artifacts with untracked
  private diagnostics;
- the marker precedence rules from RFC 0013 still work;
- old markers remain as audit provenance;
- scripts can read both the new operations path and legacy RFC 0013 markers
  during transition;
- D060 path hygiene remains enforced;
- the spec handoff has resolved open layout choices explicitly.
